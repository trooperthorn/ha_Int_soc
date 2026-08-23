"""Tests for the ha_soc/firewall/* WebSocket commands."""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import (
    ws_firewall_cancel,
    ws_firewall_confirm,
    ws_firewall_status,
    ws_firewall_test,
)

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": None}]


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="u1")
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_status_reports_no_pending_initially(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_firewall_status(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["pending"] is None
    assert result["known_rules"] is None
    assert result["history"] == []


async def test_test_without_ack_sends_error(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_firewall_test(hass, connection, {"id": 1, "rules": RULES, "backup_acknowledged": False})
    await hass.async_block_till_done()

    connection.send_error.assert_called_once()
    args = connection.send_error.call_args[0]
    assert args[0] == 1
    assert args[1] == "firewall_test_rejected"
    connection.send_result.assert_not_called()


async def test_test_happy_path_returns_pending_and_audits(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_firewall_test(hass, connection, {"id": 1, "rules": RULES, "backup_acknowledged": True})
    await hass.async_block_till_done()

    connection.send_error.assert_not_called()
    result = connection.send_result.call_args[0][1]
    assert result["status"] == "testing"
    assert result["proposed_rules"] == RULES

    runtime = entry.runtime_data
    assert runtime.store.data["firewall"]["pending"]["test_id"] == result["test_id"]


async def test_confirm_unknown_test_id_sends_error(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_firewall_confirm(hass, connection, {"id": 1, "test_id": "nope"})
    await hass.async_block_till_done()

    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "firewall_confirm_rejected"


async def test_confirm_and_cancel_round_trip(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_firewall_test(hass, connection, {"id": 1, "rules": RULES, "backup_acknowledged": True})
    await hass.async_block_till_done()
    pending = connection.send_result.call_args[0][1]
    test_id = pending["test_id"]

    connection2 = _connection()
    ws_firewall_confirm(hass, connection2, {"id": 2, "test_id": test_id})
    await hass.async_block_till_done()
    connection2.send_error.assert_not_called()
    connection2.send_result.assert_called_once_with(2, {"ok": True})

    runtime = entry.runtime_data
    assert runtime.store.data["firewall"]["pending"]["status"] == "confirmed"

    # Already confirmed — cancel should now be rejected, not silently accepted.
    connection3 = _connection()
    ws_firewall_cancel(hass, connection3, {"id": 3, "test_id": test_id})
    await hass.async_block_till_done()
    connection3.send_error.assert_called_once()
    assert connection3.send_error.call_args[0][1] == "firewall_cancel_rejected"
