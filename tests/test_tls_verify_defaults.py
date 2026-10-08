"""Certificate checking is on by default for UniFi, Pi-hole and Technitium.

A new install verifies; an install from before the change keeps what it had, and
a Repairs issue names every configured connection that skips the check.
"""
from __future__ import annotations

import homeassistant.helpers.issue_registry as ir
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    CONF_PIHOLE_VERIFY_SSL,
    CONF_TECHNITIUM_VERIFY_SSL,
    CONF_UNIFI_NETWORK_VERIFY_SSL,
    CONF_UNIFI_PROTECT_VERIFY_SSL,
    DOMAIN,
    STORAGE_KEY,
)
from custom_components.ha_soc.repairs import (
    TLS_VERIFY_DISABLED_ISSUE_ID,
    async_sync_tls_verify_issue,
)
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData, default_store_data
from custom_components.ha_soc.unifi import _network_conn

_VERIFY_KEYS = (
    CONF_UNIFI_NETWORK_VERIFY_SSL,
    CONF_UNIFI_PROTECT_VERIFY_SSL,
    CONF_PIHOLE_VERIFY_SSL,
    CONF_TECHNITIUM_VERIFY_SSL,
)


def _issue(hass: HomeAssistant):
    return ir.async_get(hass).async_get_issue(DOMAIN, TLS_VERIFY_DISABLED_ISSUE_ID)


def _seed(hass_storage, settings: dict) -> None:
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 0,
        "key": STORAGE_KEY,
        "data": {"settings": settings},
    }


def test_new_install_defaults_verify_on() -> None:
    settings = default_store_data()["settings"]
    for key in _VERIFY_KEYS:
        assert settings[key] is True, key


async def test_new_install_loads_with_verify_on(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    assert await store.async_load() is False
    for key in _VERIFY_KEYS:
        assert store.settings[key] is True, key
    async_sync_tls_verify_issue(hass, store.settings)
    assert _issue(hass) is None


async def test_unifi_connection_verifies_by_default(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()
    store.async_update_settings(unifi_network_host="10.0.0.1")
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    await secrets.async_set("unifi_network_api_key", "k")
    conn = await _network_conn(store, secrets)
    assert conn is not None
    assert conn.verify_ssl is True


async def test_existing_install_keeps_unverified_connections(
    hass: HomeAssistant, hass_storage
) -> None:
    # Saved before the flags were written for Technitium, and before the default changed.
    _seed(
        hass_storage,
        {
            "unifi_network_host": "10.0.0.1",
            "pihole_host": "10.0.0.2",
            "pihole_verify_ssl": False,
            "technitium_host": "10.0.0.3",
            "unifi_protect_host": "",
        },
    )
    store = HaSocData(hass)
    assert await store.async_load() is True
    assert store.settings["unifi_network_verify_ssl"] is False
    assert store.settings["pihole_verify_ssl"] is False
    assert store.settings["technitium_verify_ssl"] is False
    # No host, nothing to keep: the new default applies.
    assert store.settings["unifi_protect_verify_ssl"] is True


async def test_existing_install_with_verify_on_is_left_alone(
    hass: HomeAssistant, hass_storage
) -> None:
    _seed(hass_storage, {"pihole_host": "10.0.0.2", "pihole_verify_ssl": True})
    store = HaSocData(hass)
    await store.async_load()
    assert store.settings["pihole_verify_ssl"] is True
    async_sync_tls_verify_issue(hass, store.settings)
    assert _issue(hass) is None


async def test_old_install_with_verify_off_raises_one_issue(
    hass: HomeAssistant, hass_storage
) -> None:
    _seed(
        hass_storage,
        {
            "unifi_network_host": "10.0.0.1",
            "unifi_network_verify_ssl": False,
            "pihole_host": "10.0.0.2",
            "pihole_verify_ssl": False,
            "technitium_host": "10.0.0.3",
            "technitium_verify_ssl": True,
        },
    )
    store = HaSocData(hass)
    await store.async_load()

    async_sync_tls_verify_issue(hass, store.settings)
    async_sync_tls_verify_issue(hass, store.settings)

    issues = [
        issue
        for issue in ir.async_get(hass).issues.values()
        if issue.domain == DOMAIN and issue.translation_key == "tls_verification_disabled"
    ]
    assert len(issues) == 1
    assert issues[0].issue_id == TLS_VERIFY_DISABLED_ISSUE_ID
    assert issues[0].translation_placeholders == {"connections": "UniFi Network, Pi-hole"}


async def test_issue_clears_when_verification_is_turned_on(hass: HomeAssistant) -> None:
    settings = {"pihole_host": "10.0.0.2", "pihole_verify_ssl": False}
    async_sync_tls_verify_issue(hass, settings)
    assert _issue(hass) is not None
    settings["pihole_verify_ssl"] = True
    async_sync_tls_verify_issue(hass, settings)
    assert _issue(hass) is None


async def test_unconfigured_connection_raises_nothing(hass: HomeAssistant) -> None:
    async_sync_tls_verify_issue(
        hass, {"pihole_host": None, "pihole_verify_ssl": False, "technitium_host": ""}
    )
    assert _issue(hass) is None
