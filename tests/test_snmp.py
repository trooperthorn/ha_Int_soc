"""SNMPv3 control-plane and Probe policy tests."""
from pathlib import Path
from unittest.mock import patch

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant

from custom_components.ha_soc.const import (
    CONF_SNMP_AUTH_PASSPHRASE,
    CONF_SNMP_ENABLED,
    CONF_SNMP_LISTEN_ADDRESS,
    CONF_SNMP_PORT,
    CONF_SNMP_PRIV_PASSPHRASE,
    CONF_SNMP_USERNAME,
    DOMAIN,
)
from custom_components.ha_soc.snmp import (
    async_config_for_probe,
    snmp_ip_address,
    validate_enabled_config,
    validate_snmp_passphrase,
    validate_snmp_username,
)

PROBE_SECRET = "unit-test-snmp-probe-secret"
AUTH_PASS = "AuthPassphrase-2026!"
PRIV_PASS = "PrivPassphrase-2026!"


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


def test_snmp_validators_reject_weak_or_wildcard_values() -> None:
    assert snmp_ip_address("192.168.30.3") == "192.168.30.3"
    assert validate_snmp_username("solarwinds_sem") == "solarwinds_sem"
    assert validate_snmp_passphrase(AUTH_PASS) == AUTH_PASS
    for value in ("0.0.0.0", "::", "host.example.lan", "udp:127.0.0.1:161"):
        with pytest.raises(vol.Invalid):
            snmp_ip_address(value)
    with pytest.raises(vol.Invalid):
        validate_snmp_username("bad user")
    with pytest.raises(vol.Invalid):
        validate_snmp_passphrase("too-short")


def test_enabled_config_requires_distinct_complete_authpriv() -> None:
    settings = {
        CONF_SNMP_ENABLED: True,
        CONF_SNMP_LISTEN_ADDRESS: "192.168.30.3",
        CONF_SNMP_PORT: 161,
        CONF_SNMP_USERNAME: "solarwinds_sem",
    }
    with pytest.raises(vol.Invalid):
        validate_enabled_config(settings, {})
    with pytest.raises(vol.Invalid):
        validate_enabled_config(
            settings,
            {
                CONF_SNMP_AUTH_PASSPHRASE: AUTH_PASS,
                CONF_SNMP_PRIV_PASSPHRASE: AUTH_PASS,
            },
        )
    validate_enabled_config(
        settings,
        {
            CONF_SNMP_AUTH_PASSPHRASE: AUTH_PASS,
            CONF_SNMP_PRIV_PASSPHRASE: PRIV_PASS,
        },
    )


async def test_disabled_config_never_transmits_dormant_secrets(
    supervisor_entry: MockConfigEntry,
) -> None:
    runtime = supervisor_entry.runtime_data
    await runtime.secrets.async_set(CONF_SNMP_AUTH_PASSPHRASE, AUTH_PASS)
    await runtime.secrets.async_set(CONF_SNMP_PRIV_PASSPHRASE, PRIV_PASS)
    config = await async_config_for_probe(runtime.store.settings, runtime.secrets)
    assert config["enabled"] is False
    assert config["auth_passphrase"] is None
    assert config["priv_passphrase"] is None


async def test_probe_receives_credentials_only_on_generation_change(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    runtime.store.async_update_settings(
        **{
            CONF_SNMP_ENABLED: True,
            CONF_SNMP_LISTEN_ADDRESS: "192.168.30.3",
            CONF_SNMP_PORT: 161,
            CONF_SNMP_USERNAME: "solarwinds_sem",
        }
    )
    await runtime.secrets.async_set(CONF_SNMP_AUTH_PASSPHRASE, AUTH_PASS)
    await runtime.secrets.async_set(CONF_SNMP_PRIV_PASSPHRASE, PRIV_PASS)
    context = Context(user_id=supervisor_user.id)

    first = await hass.services.async_call(
        DOMAIN,
        "poll_snmp_config",
        {"generation": "", "probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=context,
    )
    assert first["enabled"] is True
    assert first["auth_protocol"] == "SHA-256"
    assert first["privacy_protocol"] == "AES-128"
    assert first["auth_passphrase"] == AUTH_PASS
    assert first["priv_passphrase"] == PRIV_PASS

    unchanged = await hass.services.async_call(
        DOMAIN,
        "poll_snmp_config",
        {"generation": first["generation"], "probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=context,
    )
    assert unchanged == {"enabled": True, "generation": first["generation"]}


async def test_snmp_status_ingest_is_bounded_and_non_secret(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "snmp_status": {
                "enabled": True,
                "running": True,
                "generation": "a" * 64,
                "listen_address": "192.168.30.3",
                "port": 161,
            },
            "probe_secret": PROBE_SECRET,
        },
        blocking=True,
        context=Context(user_id=supervisor_user.id),
    )
    status = supervisor_entry.runtime_data.store.data["snmp_status"]
    assert status["running"] is True
    assert status["reported_at"]
    assert "passphrase" not in repr(status)


def test_probe_policy_has_no_community_or_write_access() -> None:
    script = Path("ha_soc_probe/rootfs/etc/services.d/ha_soc_probe_snmp/run").read_text()
    assert "rouser ${username} priv -V haSocReadOnly" in script
    assert "SHA-256" in script
    assert 'createUser %s SHA-256 "%s" AES "%s"' in script
    assert "rwuser" not in script
    assert "rocommunity" not in script
    assert "rwcommunity" not in script
    assert "view haSocReadOnly included .1.3.6.1.2.1.25.2" in script
    assert "view haSocReadOnly included .1.3.6.1.2.1.25 " not in script
