"""Tests for the dedicated private secret store (work items SEC-1 to SEC-3).

What is pinned here, in plain terms:

- The secret store is a separate, private (0o600) Store file, not a corner
  of the general ha_soc.storage file.
- Settings never contain a secret value again: not in the live dict, not
  in the saved file, not on the settings wire (which still carries the
  placeholder-plus-"<key>_set" shape the frontend expects).
- entry.options stays empty forever: the mirror is gone (SEC-2), a legacy
  mirror is scrubbed exactly once at setup, and a settings save writes
  nothing back into it.
- The one-time migration drains legacy plaintext copies (settings values
  and the firewall pairing secret) into the secret store and rewrites the
  old store without them.
"""
import json

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    DOMAIN,
    REDACTED_PLACEHOLDER,
    SECRET_SETTING_KEYS,
    STORAGE_KEY,
)
from custom_components.ha_soc.secrets_store import (
    ALLOWED_SECRET_KEYS,
    PROBE_PAIRING_SECRET_KEY,
    SECRET_STORAGE_KEY,
    HaSocSecretStore,
    async_migrate_legacy_secrets,
)
from custom_components.ha_soc.store import HaSocData


def _owner_connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner1")
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


# -- SEC-1: the store itself --------------------------------------------------


async def test_secret_store_is_private_and_separate(hass: HomeAssistant) -> None:
    """The underlying Store must be private (0o600 on write), atomic, and a
    different file than the general ha_soc.storage store."""
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()

    inner = secrets._store
    assert inner._private is True
    assert inner._atomic_writes is True
    assert inner.key == SECRET_STORAGE_KEY
    assert inner.key != STORAGE_KEY

    # A value round-trips through the private file only.
    await secrets.async_set("nvd_api_key", "NVDSECRET")
    assert await secrets.async_get("nvd_api_key") == "NVDSECRET"

    # A second instance reads the persisted file back.
    reloaded = HaSocSecretStore(hass)
    await reloaded.async_load()
    assert await reloaded.async_get("nvd_api_key") == "NVDSECRET"

    # None and "" both clear.
    await secrets.async_set("nvd_api_key", "")
    assert await secrets.async_get("nvd_api_key") is None
    await secrets.async_set("nvd_api_key", "X")
    await secrets.async_set("nvd_api_key", None)
    assert await secrets.async_get("nvd_api_key") is None


async def test_secret_store_repr_names_keys_never_values(hass: HomeAssistant) -> None:
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    await secrets.async_set("github_token", "ghp_SUPERSECRET")

    shown = repr(secrets)
    assert "ghp_SUPERSECRET" not in shown
    assert "github_token" in shown


async def test_secret_store_rejects_unknown_keys(hass: HomeAssistant) -> None:
    """Only SECRET_SETTING_KEYS plus the probe pairing secret may live here;
    anything else is a programming error, not silently stored."""
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()

    assert PROBE_PAIRING_SECRET_KEY in ALLOWED_SECRET_KEYS
    assert SECRET_SETTING_KEYS <= ALLOWED_SECRET_KEYS

    with pytest.raises(ValueError):
        await secrets.async_set("not_a_secret_key", "x")
    with pytest.raises(ValueError):
        await secrets.async_get("not_a_secret_key")


# -- SEC-1: settings carry no secret values ----------------------------------


async def test_settings_never_contain_secret_values(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict
) -> None:
    """After a settings save that includes secrets, no secret value exists
    in the live settings dict, in the persisted general store, or on the
    settings wire; the wire still carries placeholder plus <key>_set."""
    from custom_components.ha_soc.websocket_api import ws_settings_set

    runtime = entry.runtime_data
    connection = _owner_connection()
    ws_settings_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/settings/set",
            "nvd_api_key": "NVD-VALUE",
            "github_token": "ghp_VALUE",
            "unifi_network_api_key": "UNIFI-N-VALUE",
            "unifi_protect_api_key": "UNIFI-P-VALUE",
            "scanner_enabled": False,
        },
    )
    await hass.async_block_till_done()

    # Live settings dict: no secret key present at all.
    for key in SECRET_SETTING_KEYS:
        assert key not in runtime.store.settings

    # Secret store holds the values.
    assert await runtime.secrets.async_get("nvd_api_key") == "NVD-VALUE"
    assert await runtime.secrets.async_get("github_token") == "ghp_VALUE"

    # Persisted general store never sees the values.
    await runtime.store.async_save_now()
    general_blob = json.dumps(hass_storage[STORAGE_KEY])
    for value in ("NVD-VALUE", "ghp_VALUE", "UNIFI-N-VALUE", "UNIFI-P-VALUE"):
        assert value not in general_blob
    # The private file is the one that holds them.
    secret_blob = json.dumps(hass_storage[SECRET_STORAGE_KEY])
    assert "NVD-VALUE" in secret_blob

    # Wire shape unchanged: placeholder plus companion boolean, raw value
    # never present.
    result = connection.send_result.call_args[0][1]
    assert result["nvd_api_key"] == REDACTED_PLACEHOLDER
    assert result["nvd_api_key_set"] is True
    assert result["github_token"] == REDACTED_PLACEHOLDER
    assert result["github_token_set"] is True
    assert "NVD-VALUE" not in json.dumps(result)

    # The non-secret change went through the normal settings path.
    assert runtime.store.settings["scanner_enabled"] is False


# -- SEC-2: entry.options stays empty -----------------------------------------


async def test_entry_options_stay_empty(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A settings save must leave entry.options empty: the mirror is gone."""
    from custom_components.ha_soc.websocket_api import ws_settings_set

    assert entry.options == {}

    connection = _owner_connection()
    ws_settings_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/settings/set",
            "scanner_enabled": False,
            "nvd_api_key": "NVD-VALUE",
        },
    )
    await hass.async_block_till_done()

    assert entry.options == {}


async def test_legacy_entry_options_scrubbed_once(hass: HomeAssistant) -> None:
    """An install upgrading from a mirroring build carries settings (secret
    values included) in entry.options; setup rewrites it to {} once."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        title="HA SOC",
        options={"scanner_enabled": True, "nvd_api_key": "LEGACY-MIRROR-VALUE"},
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.options == {}

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


# -- SEC-1: the one-time migration --------------------------------------------


async def test_migration_moves_settings_secrets_out_of_old_store(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """Legacy secret values in the settings blob move into the secret store
    and the old store is rewritten without them, exactly once."""
    store = HaSocData(hass)
    await store.async_load()
    # Simulate an old on-disk blob: the merge in async_load keeps unknown
    # settings keys, which is exactly how a pre-SEC-1 install arrives here.
    store.data["settings"]["nvd_api_key"] = "OLD-NVD"
    store.data["settings"]["github_token"] = "OLD-GH"
    await store.async_save_now()
    assert "OLD-NVD" in json.dumps(hass_storage[STORAGE_KEY])

    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    moved = await async_migrate_legacy_secrets(secrets, store)

    assert sorted(moved) == ["github_token", "nvd_api_key"]
    assert await secrets.async_get("nvd_api_key") == "OLD-NVD"
    assert await secrets.async_get("github_token") == "OLD-GH"

    # The old store was rewritten immediately, without the values.
    old_blob = json.dumps(hass_storage[STORAGE_KEY])
    assert "OLD-NVD" not in old_blob
    assert "OLD-GH" not in old_blob
    # And they live in the private file instead.
    assert "OLD-NVD" in json.dumps(hass_storage[SECRET_STORAGE_KEY])

    # Second run: nothing left to move.
    assert await async_migrate_legacy_secrets(secrets, store) == []


async def test_migration_moves_firewall_pairing_secret(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """The legacy firewall addon_secret moves to PROBE_PAIRING_SECRET_KEY,
    the old key is gone from the firewall dict, and verification still
    accepts the same secret afterwards (pinning survived the move)."""
    from custom_components.ha_soc.firewall import async_verify_or_pin_secret

    store = HaSocData(hass)
    await store.async_load()
    store.data["firewall"]["addon_secret"] = "legacy-pin"
    await store.async_save_now()

    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    moved = await async_migrate_legacy_secrets(secrets, store)

    assert moved == [PROBE_PAIRING_SECRET_KEY]
    assert "addon_secret" not in store.data["firewall"]
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) == "legacy-pin"
    assert "legacy-pin" not in json.dumps(hass_storage[STORAGE_KEY])

    # The migrated pin still authenticates the add-on, and a forgery still
    # fails: nothing about the pairing semantics changed, only the home.
    assert await async_verify_or_pin_secret(secrets, "legacy-pin") is True
    assert await async_verify_or_pin_secret(secrets, "forged") is False


async def test_migration_runs_end_to_end_through_setup(
    hass: HomeAssistant, hass_storage: dict
) -> None:
    """Full-setup variant: a pre-SEC-1 storage blob on disk is drained on
    the first setup, and the runtime's secret store serves the values."""
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 0,
        "key": STORAGE_KEY,
        "data": {
            "settings": {"nvd_api_key": "DISK-NVD", "scanner_enabled": True},
            "firewall": {
                "known_rules": None,
                "known_rules_reported_at": None,
                "pending": None,
                "history": [],
                "addon_secret": "disk-pin",
            },
        },
    }

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    runtime = config_entry.runtime_data
    assert await runtime.secrets.async_get("nvd_api_key") == "DISK-NVD"
    assert (
        await runtime.secrets.async_get(PROBE_PAIRING_SECRET_KEY) == "disk-pin"
    )
    assert "nvd_api_key" not in runtime.store.settings
    assert "addon_secret" not in runtime.store.data["firewall"]

    # The rewritten old store on "disk" carries neither value.
    old_blob = json.dumps(hass_storage[STORAGE_KEY])
    assert "DISK-NVD" not in old_blob
    assert "disk-pin" not in old_blob

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
