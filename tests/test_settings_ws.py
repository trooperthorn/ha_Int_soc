"""Tests for ha_soc/settings/get and ha_soc/settings/set.

Calls the sync wrappers directly against a fake connection (same approach
as test_access_control.py) rather than a full websocket_api HTTP
roundtrip. What needs proving here is that /set actually mutates the live
store, routes secret values into the private secret store (SEC-1), and
leaves entry.options alone (SEC-2), not the generic auth plumbing already
covered by test_access_control.py.
"""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN, SYSLOG_FORMAT_CEF
from custom_components.ha_soc.websocket_api import ws_settings_get, ws_settings_set


def _connection() -> MagicMock:
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


async def test_get_returns_live_settings(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_settings_get(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["scanner_enabled"] is True
    assert result["access_level"] == "owner_only"


async def test_set_updates_store_and_leaves_entry_options_empty(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The pre-SEC-2 build mirrored every save into entry.options; the
    mirror is gone, so a save changes the live store and nothing else."""
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/settings/set", "scanner_enabled": False, "evidence_retention_days": 400},
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["scanner_enabled"] is False
    assert entry.runtime_data.store.settings["evidence_retention_days"] == 400
    assert entry.options == {}

    result = connection.send_result.call_args[0][1]
    assert result["scanner_enabled"] is False


async def test_syslog_format_is_selectable_and_reported(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/settings/set",
            "syslog_format": SYSLOG_FORMAT_CEF,
        },
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["syslog_format"] == SYSLOG_FORMAT_CEF
    result = connection.send_result.call_args[0][1]
    assert result["syslog_format"] == SYSLOG_FORMAT_CEF
    assert result["syslog_status"]["format"] == SYSLOG_FORMAT_CEF


async def test_set_with_no_changes_is_a_no_op_read(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    before = dict(entry.runtime_data.store.settings)

    ws_settings_set(hass, connection, {"id": 1, "type": "ha_soc/settings/set"})
    await hass.async_block_till_done()

    # The live store is untouched...
    assert entry.runtime_data.store.settings == before
    # ...and the returned view is the masked form (secrets never sent raw).
    result = connection.send_result.call_args[0][1]
    assert result["nvd_api_key"] in ("", "[redacted]")
    assert result["nvd_api_key_set"] is False
    assert result["github_token_set"] is False


async def test_get_and_set_are_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    from homeassistant.exceptions import Unauthorized

    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")

    with pytest.raises(Unauthorized):
        ws_settings_get(hass, non_owner, {"id": 1})
    with pytest.raises(Unauthorized):
        ws_settings_set(hass, non_owner, {"id": 2, "type": "ha_soc/settings/set", "scanner_enabled": False})


async def test_secret_masking_and_passthrough(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    # Set a real secret value: it lands in the private secret store, never
    # in the settings dict (SEC-1).
    ws_settings_set(
        hass, connection, {"id": 1, "type": "ha_soc/settings/set", "nvd_api_key": "SECRET123"}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") == "SECRET123"
    assert "nvd_api_key" not in entry.runtime_data.store.settings

    # Reading back never returns the raw value.
    ws_settings_get(hass, connection, {"id": 2})
    await hass.async_block_till_done()
    got = connection.send_result.call_args[0][1]
    assert got["nvd_api_key"] == "[redacted]"
    assert got["nvd_api_key_set"] is True

    # Sending the placeholder back is treated as "unchanged", not an overwrite.
    ws_settings_set(
        hass, connection, {"id": 3, "type": "ha_soc/settings/set", "nvd_api_key": "[redacted]"}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") == "SECRET123"

    # An empty string clears the secret, and the flag reads false again.
    ws_settings_set(
        hass, connection, {"id": 4, "type": "ha_soc/settings/set", "nvd_api_key": ""}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") is None
    got = connection.send_result.call_args[0][1]
    assert got["nvd_api_key"] == ""
    assert got["nvd_api_key_set"] is False
