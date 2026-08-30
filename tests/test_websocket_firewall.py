"""Tests for the ha_soc/firewall/* WebSocket commands.

Since decision D-4 the ENTIRE firewall command set is owner-only, status
included, regardless of access_level, and decision D-5 adds the owner-only
discard_pending escape hatch for an add-on gone silent mid-test. Both
gates are pinned here alongside the original command behavior.
"""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc.const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    DOMAIN,
    FIREWALL_TEST_DISCARDED_UNREPORTED,
)
from custom_components.ha_soc.websocket_api import (
    ws_firewall_cancel,
    ws_firewall_confirm,
    ws_firewall_discard_pending,
    ws_firewall_reset_pairing,
    ws_firewall_status,
    ws_firewall_test,
)

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": None}]


def _connection(*, owner: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=owner, id="u1" if owner else "admin2")
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


async def test_firewall_all_commands_owner_only(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """D-4: every firewall command, status included, refuses a non-owner
    admin EVEN when access_level has been opened to owner_and_admins;
    require_owner deliberately ignores access_level."""
    entry.runtime_data.store.async_update_settings(
        access_level=ACCESS_LEVEL_OWNER_AND_ADMINS
    )
    for handler, msg in (
        (ws_firewall_status, {"id": 1, "type": "ha_soc/firewall/status"}),
        (
            ws_firewall_test,
            {"id": 2, "type": "ha_soc/firewall/test", "rules": RULES, "backup_acknowledged": True},
        ),
        (ws_firewall_confirm, {"id": 3, "type": "ha_soc/firewall/confirm", "test_id": "t1"}),
        (ws_firewall_cancel, {"id": 4, "type": "ha_soc/firewall/cancel", "test_id": "t1"}),
        (ws_firewall_discard_pending, {"id": 5, "type": "ha_soc/firewall/discard_pending"}),
        (ws_firewall_reset_pairing, {"id": 6, "type": "ha_soc/firewall/reset_pairing"}),
    ):
        connection = _connection(owner=False)
        with pytest.raises(Unauthorized):
            handler(hass, connection, msg)
        connection.send_result.assert_not_called()
    # And nothing above left any firewall state behind.
    assert entry.runtime_data.store.data["firewall"]["pending"] is None


async def test_firewall_discard_pending_is_owner_only_and_audited(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """D-5: only the owner can discard, only after the countdown lapsed,
    and every discard leaves both a history entry (discarded_unreported,
    resolved_by the owner) and a firewall_pending_discarded audit record."""
    runtime = entry.runtime_data
    # Keep audit records in the buffer for assertion instead of flushing
    # to disk (the firewall_ prefix would otherwise flush immediately).
    runtime.audit._async_schedule_flush = lambda: None

    # Nothing pending yet: the owner's discard is refused as no_pending_test.
    connection = _connection()
    ws_firewall_discard_pending(hass, connection, {"id": 1, "type": "ha_soc/firewall/discard_pending"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "firewall_discard_rejected"
    assert connection.send_error.call_args[0][2] == "no_pending_test"

    # Propose a test whose window is still open: discard is refused, the
    # slot stays occupied, because a merely-late report may still arrive.
    owner = _connection()
    ws_firewall_test(hass, owner, {"id": 2, "rules": RULES, "backup_acknowledged": True})
    await hass.async_block_till_done()
    test_id = owner.send_result.call_args[0][1]["test_id"]

    connection = _connection()
    ws_firewall_discard_pending(hass, connection, {"id": 3, "type": "ha_soc/firewall/discard_pending"})
    await hass.async_block_till_done()
    assert connection.send_error.call_args[0][2] == "window_not_lapsed"
    assert runtime.store.data["firewall"]["pending"]["test_id"] == test_id

    # Lapse the countdown, then prove the owner-only gate before discarding.
    runtime.store.data["firewall"]["pending"]["expires_at"] = "2020-01-01T00:00:00+00:00"
    with pytest.raises(Unauthorized):
        ws_firewall_discard_pending(
            hass, _connection(owner=False), {"id": 4, "type": "ha_soc/firewall/discard_pending"}
        )
    assert runtime.store.data["firewall"]["pending"] is not None

    connection = _connection()
    ws_firewall_discard_pending(hass, connection, {"id": 5, "type": "ha_soc/firewall/discard_pending"})
    await hass.async_block_till_done()
    connection.send_error.assert_not_called()
    connection.send_result.assert_called_once_with(5, {"ok": True})

    fw = runtime.store.data["firewall"]
    assert fw["pending"] is None
    assert len(fw["history"]) == 1
    archived = fw["history"][0]
    assert archived["test_id"] == test_id
    assert archived["status"] == FIREWALL_TEST_DISCARDED_UNREPORTED
    assert archived["resolved_by"] == "u1"

    records = [
        record
        for record in runtime.audit._buffer
        if record["category"] == "firewall_pending_discarded"
    ]
    assert len(records) == 1
    assert records[0]["user_id"] == "u1"
    assert records[0]["detail"]["test_id"] == test_id
    # The record names what the test looked like when the owner gave up:
    # the lapsed window had already relabeled it expired_unreported.
    assert records[0]["detail"]["previous_status"] == "expired_unreported"
