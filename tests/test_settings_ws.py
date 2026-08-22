"""Tests for ha_soc/settings/get and ha_soc/settings/set.

Calls the sync wrappers directly against a fake connection (same approach
as test_access_control.py) rather than a full websocket_api HTTP roundtrip
— what needs proving here is that /set actually mutates the live store and
mirrors into entry.options, not the generic auth plumbing already covered
by test_access_control.py.
"""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
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


async def test_set_updates_store_and_mirrors_entry_options(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/settings/set", "scanner_enabled": False, "risk_learning_period_days": 21},
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["scanner_enabled"] is False
    assert entry.runtime_data.store.settings["risk_learning_period_days"] == 21
    assert entry.options["scanner_enabled"] is False
    assert entry.options["risk_learning_period_days"] == 21

    result = connection.send_result.call_args[0][1]
    assert result["scanner_enabled"] is False


async def test_set_with_no_changes_is_a_no_op_read(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    before = dict(entry.runtime_data.store.settings)

    ws_settings_set(hass, connection, {"id": 1, "type": "ha_soc/settings/set"})
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings == before
    result = connection.send_result.call_args[0][1]
    assert result == before
