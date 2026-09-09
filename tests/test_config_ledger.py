"""Tests for config_ledger.py and the ha_soc/unifi_ledger/* commands.

Three properties carry this feature. A snapshot must hash the same when the
controller returns the same configuration in a different order, or every poll
reports drift and the report becomes noise. A partial fetch must never become
a baseline or a drift report, because an ACL collection that failed to load
looks exactly like every rule having been deleted. And accepting a baseline
must refuse a snapshot that no longer describes the controller.
"""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc import config_ledger as cl
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import (
    ws_unifi_ledger_accept,
    ws_unifi_ledger_get,
)


def _overview(**over):
    """A complete network overview, in the shape unifi.async_network_overview returns."""
    base = {
        "configured": True,
        "error": None,
        "site_id": "site-1",
        "application_version": "10.4.57",
        "devices": [
            {
                "mac": "aa:bb:cc:00:00:01",
                "name": "Pro Max",
                "model": "USW-Pro-Max",
                "configuration_id": "cfg-1",
                "provisioned_at": "2026-09-01T00:00:00Z",
                "adopted_at": "2026-01-01T00:00:00Z",
            },
            {
                "mac": "aa:bb:cc:00:00:02",
                "name": "Hydro UDB",
                "model": "UDB",
                "configuration_id": "cfg-2",
                "provisioned_at": "2026-09-01T00:00:00Z",
                "adopted_at": "2026-01-01T00:00:00Z",
            },
        ],
        "acl": {
            "available": True,
            "error": None,
            "rules": [
                {
                    "id": "acl-1",
                    "name": "IoT to Gateway",
                    "enabled": True,
                    "action": "ALLOW",
                    "source": {"networks": ["IoT"], "ports": []},
                    "destination": {"networks": ["Default"], "ports": [53, 8080]},
                }
            ],
            "ordering": ["acl-1"],
        },
        "firewall_policies": {
            "available": True,
            "error": None,
            "zones": [
                {"id": "z-1", "name": "Internal", "networks": ["Default"]},
                {"id": "z-2", "name": "IoT", "networks": ["IoT"]},
            ],
            "rules": [
                {
                    "id": "fw-1",
                    "name": "Block IoT to Internal",
                    "enabled": True,
                    "action": "BLOCK",
                    "allow_return_traffic": None,
                    "ip_version": "IPV4",
                    "protocol": "all",
                    "connection_state_filter": None,
                    "scheduled": False,
                    "origin": "USER_DEFINED",
                    "source": {"zone": "IoT", "networks": ["IoT"], "ports": []},
                    "destination": {"zone": "Internal", "networks": ["Default"], "ports": []},
                    "ports": [],
                }
            ],
            "ordering": {"before_system_defined": ["fw-1"], "after_system_defined": []},
        },
    }
    base.update(over)
    return base


def _connection(is_owner: bool = True, is_admin: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner, id="owner1")
    return connection


async def _call(hass: HomeAssistant, handler, connection: MagicMock, msg: dict) -> MagicMock:
    """Run an @async_response command wrapper and wait for its reply."""
    connection.reset_mock()
    handler(hass, connection, msg)
    for _ in range(200):
        await hass.async_block_till_done()
        if connection.send_result.called or connection.send_error.called:
            await hass.async_block_till_done()
            return connection
        await asyncio.sleep(0.01)
    raise AssertionError(f"no reply to {msg['type']}")


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> str:
    """Give each test its own config dir.

    The harness's config dir lives inside site-packages and survives between
    runs, so the audit chain one test writes is still on disk for the next
    one, and a count of records becomes a count of every record this file has
    ever written.
    """
    hass.config.config_dir = str(tmp_path)
    return str(tmp_path)


@pytest.fixture
async def entry(hass: HomeAssistant, isolated_config_dir: str) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def patched_overview(monkeypatch):
    """Replace the controller fetch; the ledger's job is the comparison."""
    state = {"overview": _overview()}

    async def _fake(hass, store, secrets):
        return state["overview"]

    monkeypatch.setattr("custom_components.ha_soc.unifi.async_network_overview", _fake)
    return state


# --- canonical form --------------------------------------------------------


def test_snapshot_digest_is_stable_under_reordering() -> None:
    """The API does not promise an order. If the digest followed the order the
    controller happened to return, every poll would report drift."""
    a = cl.build_snapshot(_overview())
    shuffled = _overview()
    shuffled["devices"] = list(reversed(shuffled["devices"]))
    shuffled["firewall_policies"] = dict(shuffled["firewall_policies"])
    shuffled["firewall_policies"]["zones"] = list(reversed(shuffled["firewall_policies"]["zones"]))
    b = cl.build_snapshot(shuffled)
    assert a["digest"] == b["digest"]


def test_snapshot_excludes_volatile_fields() -> None:
    """A baseline that moves on its own teaches the reader to ignore it."""
    noisy = _overview()
    noisy["devices"] = [dict(d, last_seen=1234567, bandwidth={"rx": 5}) for d in noisy["devices"]]
    assert cl.build_snapshot(noisy)["digest"] == cl.build_snapshot(_overview())["digest"]


def test_devices_are_keyed_on_mac() -> None:
    snapshot = cl.build_snapshot(_overview())
    assert [row["id"] for row in snapshot["sections"]["devices"]] == [
        "aa:bb:cc:00:00:01",
        "aa:bb:cc:00:00:02",
    ]


def test_taken_at_does_not_enter_the_digest() -> None:
    a = cl.build_snapshot(_overview())
    b = cl.build_snapshot(_overview())
    assert a["taken_at"] != b["taken_at"] or a["digest"] == b["digest"]
    assert a["digest"] == b["digest"]


# --- refusing to compare an incomplete fetch -------------------------------


@pytest.mark.parametrize(
    ("over", "fragment"),
    [
        ({"configured": False}, "not configured"),
        ({"error": "timed out"}, "timed out"),
        ({"acl": {"available": False, "rules": [], "ordering": None}}, "ACL rules"),
        (
            {"firewall_policies": {"available": False, "rules": [], "zones": [], "ordering": None}},
            "Firewall policies",
        ),
    ],
)
def test_incomplete_snapshots_are_refused(over: dict, fragment: str) -> None:
    complete, reason = cl.snapshot_is_complete(_overview(**over))
    assert complete is False
    assert fragment in reason


def test_a_complete_snapshot_is_accepted() -> None:
    assert cl.snapshot_is_complete(_overview()) == (True, None)


# --- diffing ---------------------------------------------------------------


def test_no_change_is_no_drift() -> None:
    base = cl.build_snapshot(_overview())
    assert cl.diff_snapshots(base, cl.build_snapshot(_overview()))["total"] == 0


def test_a_renamed_rule_is_a_change_not_a_delete_and_add() -> None:
    base = cl.build_snapshot(_overview())
    changed = _overview()
    changed["firewall_policies"]["rules"][0]["name"] = "Block IoT to LAN"
    drift = cl.diff_snapshots(base, cl.build_snapshot(changed))

    section = drift["sections"]["firewall_policies"]
    assert section["added"] == []
    assert section["removed"] == []
    assert section["changed"][0]["changes"] == [
        {"field": "name", "from": "Block IoT to Internal", "to": "Block IoT to LAN"}
    ]


def test_a_disabled_rule_is_detected() -> None:
    base = cl.build_snapshot(_overview())
    changed = _overview()
    changed["firewall_policies"]["rules"][0]["enabled"] = False
    drift = cl.diff_snapshots(base, cl.build_snapshot(changed))
    assert drift["total"] == 1
    assert {"field": "enabled", "from": True, "to": False} in drift["sections"][
        "firewall_policies"
    ]["changed"][0]["changes"]


def test_a_removed_device_is_detected() -> None:
    base = cl.build_snapshot(_overview())
    changed = _overview()
    changed["devices"] = changed["devices"][:1]
    drift = cl.diff_snapshots(base, cl.build_snapshot(changed))
    assert [row["id"] for row in drift["sections"]["devices"]["removed"]] == [
        "aa:bb:cc:00:00:02"
    ]


def test_reordering_rules_is_drift_with_no_row_changed() -> None:
    """A reorder changes which rule wins while every rule stays identical."""
    base = cl.build_snapshot(_overview())
    changed = _overview()
    changed["firewall_policies"]["ordering"] = {
        "before_system_defined": [],
        "after_system_defined": ["fw-1"],
    }
    drift = cl.diff_snapshots(base, cl.build_snapshot(changed))

    section = drift["sections"]["firewall_policies"]
    assert section["ordering_changed"] is True
    assert section["changed"] == []
    assert drift["total"] == 1


# --- findings --------------------------------------------------------------


def test_no_baseline_is_an_info_finding() -> None:
    findings = cl.build_findings({"available": True, "baseline": None})
    assert [f["severity"] for f in findings] == ["info"]
    assert findings[0]["id"] == "unifi_baseline_absent"


def test_drift_is_one_medium_finding_per_section() -> None:
    base = cl.build_snapshot(_overview())
    changed = _overview()
    changed["firewall_policies"]["rules"][0]["enabled"] = False
    changed["devices"] = changed["devices"][:1]
    drift = cl.diff_snapshots(base, cl.build_snapshot(changed))

    findings = cl.build_findings(
        {
            "available": True,
            "baseline": {"accepted_at": "2026-09-01T00:00:00+00:00"},
            "drift": drift,
        }
    )
    assert {f["id"] for f in findings} == {
        "unifi_drift_firewall_policies",
        "unifi_drift_devices",
    }
    assert {f["severity"] for f in findings} == {"medium"}


def test_an_unreadable_controller_produces_no_findings() -> None:
    assert cl.build_findings({"available": False, "error": "timed out"}) == []


# --- the WebSocket surface -------------------------------------------------


async def test_get_requires_admin(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    with pytest.raises(Unauthorized):
        ws_unifi_ledger_get(
            hass, _connection(is_owner=False, is_admin=False), {"id": 1, "type": "ha_soc/unifi_ledger/get"}
        )


async def test_accept_is_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    with pytest.raises(Unauthorized):
        ws_unifi_ledger_accept(
            hass,
            _connection(is_owner=False, is_admin=True),
            {"id": 1, "type": "ha_soc/unifi_ledger/accept", "digest": "0" * 64},
        )


async def test_get_reports_no_baseline_and_writes_nothing(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    connection = await _call(
        hass, ws_unifi_ledger_get, _connection(), {"id": 1, "type": "ha_soc/unifi_ledger/get"}
    )
    state = connection.send_result.call_args[0][1]
    assert state["available"] is True
    assert state["baseline"] is None
    assert state["current"]["application_version"] == "10.4.57"
    # Reading is not observing: only the periodic pass writes history.
    assert (entry.runtime_data.store.data.get("unifi_ledger") or {}).get("history") == []


async def test_accept_then_drift_round_trip(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    connection = await _call(
        hass, ws_unifi_ledger_get, _connection(), {"id": 1, "type": "ha_soc/unifi_ledger/get"}
    )
    digest = connection.send_result.call_args[0][1]["current"]["digest"]

    await _call(
        hass,
        ws_unifi_ledger_accept,
        _connection(),
        {"id": 2, "type": "ha_soc/unifi_ledger/accept", "digest": digest},
    )
    assert entry.runtime_data.store.data["unifi_ledger"]["baseline"]["digest"] == digest

    patched_overview["overview"]["firewall_policies"]["rules"][0]["enabled"] = False
    connection = await _call(
        hass, ws_unifi_ledger_get, _connection(), {"id": 3, "type": "ha_soc/unifi_ledger/get"}
    )
    state = connection.send_result.call_args[0][1]
    assert state["drift"]["total"] == 1
    assert "unifi_drift_firewall_policies" in {f["id"] for f in state["findings"]}


async def test_accept_refuses_a_stale_digest(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    """The digest the panel showed must still describe the controller."""
    connection = await _call(
        hass,
        ws_unifi_ledger_accept,
        _connection(),
        {"id": 1, "type": "ha_soc/unifi_ledger/accept", "digest": "a" * 64},
    )
    assert connection.send_error.call_args[0][1] == "stale_snapshot"
    assert (entry.runtime_data.store.data.get("unifi_ledger") or {}).get("baseline") is None


async def test_accept_refuses_when_the_controller_is_unreadable(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    patched_overview["overview"] = _overview(error="timed out")
    connection = await _call(
        hass,
        ws_unifi_ledger_accept,
        _connection(),
        {"id": 1, "type": "ha_soc/unifi_ledger/accept", "digest": "a" * 64},
    )
    assert connection.send_error.call_args[0][1] == "not_available"


# --- recording -------------------------------------------------------------


async def test_record_drift_writes_once_per_digest(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    runtime = entry.runtime_data
    state = await cl.async_ledger_state(hass, runtime.store, runtime.secrets)
    cl.accept_baseline(runtime.store, runtime.audit, state["current"], user_id="owner1")

    patched_overview["overview"]["acl"]["rules"][0]["enabled"] = False
    drifted = await cl.async_ledger_state(hass, runtime.store, runtime.secrets)

    assert cl.record_drift(runtime.store, runtime.audit, drifted) is True
    # The same drift on the next pass is the same state, not a new transition.
    assert cl.record_drift(runtime.store, runtime.audit, drifted) is False
    assert len(runtime.store.data["unifi_ledger"]["history"]) == 1
    await hass.async_block_till_done()

    records = await runtime.audit.async_query(category=cl.AUDIT_CATEGORY_DRIFT, limit=10)
    assert records
    assert records[0]["detail"]["sections"] == {"acl_rules": 1}


async def test_accepting_a_baseline_clears_history_and_audits(
    hass: HomeAssistant, entry: MockConfigEntry, patched_overview
) -> None:
    runtime = entry.runtime_data
    state = await cl.async_ledger_state(hass, runtime.store, runtime.secrets)
    cl.accept_baseline(runtime.store, runtime.audit, state["current"], user_id="owner1")

    patched_overview["overview"]["acl"]["rules"][0]["enabled"] = False
    drifted = await cl.async_ledger_state(hass, runtime.store, runtime.secrets)
    cl.record_drift(runtime.store, runtime.audit, drifted)
    assert runtime.store.data["unifi_ledger"]["history"]

    # History measured against the old baseline does not survive a new one.
    accepted = cl.accept_baseline(
        runtime.store, runtime.audit, drifted["current"], user_id="owner1"
    )
    assert runtime.store.data["unifi_ledger"]["history"] == []
    assert accepted["digest"] == drifted["current"]["digest"]
    await hass.async_block_till_done()

    records = await runtime.audit.async_query(category=cl.AUDIT_CATEGORY_BASELINE, limit=10)
    assert len(records) == 2
    assert records[0]["detail"]["previous_digest"] == state["current"]["digest"]
