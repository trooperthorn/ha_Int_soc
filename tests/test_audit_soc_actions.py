"""HA SOC's own actions land in its own audit chain (work item 1.4, D-14).

Calls the WS handler sync wrappers directly against a fake connection
(the test_settings_ws.py approach) with the collaborators the handlers
delegate to mocked out, because what is under test is the audit record
each command writes - its category and its detail fields - not the
underlying permissions/logs/users machinery, which has its own tests.

Immediate flushing (work item 1.7) is disabled per test by no-op'ing the
scheduler, so every record stays in the in-memory buffer where it can be
asserted on without touching the shared on-disk audit directory; the
flush behavior itself is covered by
test_audit.test_high_value_records_flush_immediately.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import (
    DOMAIN,
    FIREWALL_TEST_CONFIRMED,
    FIREWALL_TEST_TESTING,
)
from custom_components.ha_soc.websocket_api import (
    ws_detections_set_status,
    ws_logs_container,
    ws_logs_fault,
    ws_permissions_dashboard_flags_set,
    ws_permissions_sidebar_push,
    ws_users_detail,
)


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


def _records(runtime, category: str, **detail_match: Any) -> list[dict[str, Any]]:
    return [
        record
        for record in runtime.audit._buffer
        if record["category"] == category
        and all(record["detail"].get(k) == v for k, v in detail_match.items())
    ]


async def test_audit_covers_soc_own_actions(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """One chain record per command, carrying the fields item 1.4 names."""
    runtime = entry.runtime_data
    # Keep records in the buffer for assertion (see module docstring).
    runtime.audit._async_schedule_flush = lambda: None
    connection = _connection()

    # ha_soc/detections/set_status -> detection_status_changed, and the
    # detection record itself gains status_by/status_at/previous_status.
    runtime.store.data["detections"]["det1"] = {
        "id": "det1",
        "rule_id": "brute_force_ip",
        "status": "open",
    }
    ws_detections_set_status(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/detections/set_status", "detection_id": "det1", "status": "ack"},
    )
    await hass.async_block_till_done()
    detection = runtime.store.data["detections"]["det1"]
    assert detection["status"] == "ack"
    assert detection["previous_status"] == "open"
    assert detection["status_by"] == "owner1"
    assert detection["status_at"] is not None
    records = _records(runtime, "detection_status_changed")
    assert len(records) == 1
    assert records[0]["user_id"] == "owner1"
    assert records[0]["detail"] == {
        "detection_id": "det1",
        "rule_id": "brute_force_ip",
        "old_status": "open",
        "new_status": "ack",
    }

    # ha_soc/permissions/dashboard_flags/set -> lovelace_change with the
    # flags actually sent.
    runtime.permissions.async_set_dashboard_flags = AsyncMock(return_value=(True, None))
    ws_permissions_dashboard_flags_set(
        hass,
        connection,
        {
            "id": 2,
            "type": "ha_soc/permissions/dashboard_flags/set",
            "dashboard_id": "db1",
            "require_admin": True,
        },
    )
    await hass.async_block_till_done()
    records = _records(runtime, "lovelace_change", action="dashboard_flags_set")
    assert len(records) == 1
    assert records[0]["user_id"] == "owner1"
    assert records[0]["detail"]["dashboard_id"] == "db1"
    assert records[0]["detail"]["flags"] == {"require_admin": True}

    # ha_soc/permissions/sidebar/push -> lovelace_change with the hidden
    # paths and the target user.
    runtime.permissions.async_push_sidebar_policy = AsyncMock(return_value=(True, None))
    ws_permissions_sidebar_push(
        hass,
        connection,
        {
            "id": 3,
            "type": "ha_soc/permissions/sidebar/push",
            "user_id": "target-user",
            "hidden_dashboard_paths": ["lovelace-cams"],
        },
    )
    await hass.async_block_till_done()
    records = _records(runtime, "lovelace_change", action="sidebar_push")
    assert len(records) == 1
    assert records[0]["detail"]["target_user_id"] == "target-user"
    assert records[0]["detail"]["hidden_dashboard_paths"] == ["lovelace-cams"]

    # ha_soc/logs/container -> privileged_read with the bare add-on slug.
    with patch(
        "custom_components.ha_soc.logs.async_fetch_container_log",
        AsyncMock(return_value={"target": "addon:local_probe", "content": ""}),
    ):
        ws_logs_container(
            hass,
            connection,
            {"id": 4, "type": "ha_soc/logs/container", "target": "addon:local_probe"},
        )
        await hass.async_block_till_done()
    records = _records(runtime, "privileged_read", read="container_log")
    assert len(records) == 1
    assert records[0]["user_id"] == "owner1"
    assert records[0]["detail"]["target"] == "local_probe"

    # ha_soc/logs/fault -> privileged_read against core's crash log.
    with patch(
        "custom_components.ha_soc.logs.async_fault_log_overview",
        AsyncMock(return_value={"exists": False}),
    ):
        ws_logs_fault(hass, connection, {"id": 5, "type": "ha_soc/logs/fault"})
        await hass.async_block_till_done()
    records = _records(runtime, "privileged_read", read="fault_log")
    assert len(records) == 1
    assert records[0]["detail"]["target"] == "core"

    # ha_soc/users/detail -> privileged_read naming the target user id
    # (the detail includes that user's token list).
    runtime.users.async_get_user_detail = AsyncMock(return_value={"id": "u9"})
    ws_users_detail(
        hass, connection, {"id": 6, "type": "ha_soc/users/detail", "user_id": "u9"}
    )
    await hass.async_block_till_done()
    records = _records(runtime, "privileged_read", read="user_detail")
    assert len(records) == 1
    assert records[0]["detail"]["target"] == "u9"

    # The add-on's resolution report -> firewall_resolved with
    # actor_source addon, test id, final status, and the reported rule
    # count, written by the one function that archives tests.
    runtime.store.data["firewall"]["pending"] = {
        "test_id": "t1",
        "proposed_rules": [{"action": "allow", "proto": "tcp", "port": 22}],
        "status": FIREWALL_TEST_TESTING,
        "requested_by": "owner1",
        "requested_at": "2026-08-30T00:00:00+00:00",
        "applied_at": "2026-08-30T00:00:01+00:00",
        "expires_at": "2026-08-30T00:01:00+00:00",
        "window_seconds": 45,
    }
    await firewall.async_report_from_addon(
        hass,
        runtime.store,
        known_rules=[{"action": "allow", "proto": "tcp", "port": 22}],
        resolved_test_id="t1",
        resolved_status=FIREWALL_TEST_CONFIRMED,
    )
    records = _records(runtime, "firewall_resolved")
    assert len(records) == 1
    assert records[0]["user_id"] is None
    assert records[0]["detail"] == {
        "actor_source": "addon",
        "test_id": "t1",
        "status": FIREWALL_TEST_CONFIRMED,
        # None on a clean resolution; carries the add-on's bounded failure
        # reason (backup_failed, per-family apply failure) when one was
        # reported (work item 2.4 and the carried protocol item).
        "reason": None,
        "reported_rule_count": 1,
    }


async def test_detection_set_status_unknown_id_is_error_and_unaudited(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """No mutation happened, so no success and no fictional audit record."""
    runtime = entry.runtime_data
    runtime.audit._async_schedule_flush = lambda: None
    connection = _connection()

    ws_detections_set_status(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/detections/set_status", "detection_id": "nope", "status": "ack"},
    )
    await hass.async_block_till_done()

    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "not_found"
    assert _records(runtime, "detection_status_changed") == []
