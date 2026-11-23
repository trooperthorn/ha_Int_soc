"""Tests for inventory.py: the cycle merge, identity rules, bounds, the
new-device detection rule, and the owner-only inventory commands.

The merge tests replay cycle sequences through the pure ``merge_cycle``
function with a fixed clock. The service and WebSocket tests follow
test_netscan.py's Supervisor-context and owner-only patterns.
"""
from datetime import datetime, timedelta, timezone
from itertools import count
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DETECTION_OPEN, DETECTION_RESOLVED, DOMAIN
from custom_components.ha_soc.detections import (
    RULE_NETWORK_DEVICE_BURST,
    RULE_NETWORK_DEVICE_NEW,
    network_device_detection_id,
)

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

PROBE_SECRET = "unit-test-probe-secret"
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
CYCLE = timedelta(minutes=5)
MAC_A = "00:11:22:33:44:55"
MAC_B = "00:11:22:33:44:66"
# Bit 1 of the first octet set: a locally administered (randomized) address.
MAC_PRIVATE = "da:11:22:33:44:77"


def _ids():
    counter = count(1)
    return lambda: f"d_{next(counter):04d}"


def _merge(state, hosts, now, **kwargs):
    kwargs.setdefault("new_id", state.setdefault("_test_ids", _ids()))
    return inv.merge_cycle(state, hosts, now, **kwargs)


def _state():
    return inv.empty_state()


# --------------------------------------------------------------------------
# Pure merge: identity
# --------------------------------------------------------------------------


def test_mac_kind_reads_the_locally_administered_bit():
    assert inv.mac_kind(MAC_A) == "global"
    assert inv.mac_kind(MAC_PRIVATE) == "local"


def test_first_cycle_creates_a_baseline_record():
    state = _state()
    outcome = _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    assert outcome.created == ["d_0001"]
    device = state["devices"]["d_0001"]
    assert device["identity"] == "mac"
    assert device["macs"] == [MAC_A]
    assert device["mac_kind"] == "global"
    assert device["verdict"] == "unacknowledged"
    assert device["baseline"] is True
    assert device["addresses"][0]["ip"] == "192.0.2.10"
    assert device["sources"] == ["probe_arp"]


def test_same_mac_at_a_new_address_is_the_same_record():
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    outcome = _merge(state, [{"ip": "192.0.2.99", "mac": MAC_A}], T0 + CYCLE)
    assert outcome.created == []
    assert len(state["devices"]) == 1
    device = state["devices"]["d_0001"]
    assert [a["ip"] for a in device["addresses"]] == ["192.0.2.99", "192.0.2.10"]
    assert [e["kind"] for e in state["events"]] == ["created", "address_changed"]


def test_a_different_mac_at_a_known_address_is_a_different_record():
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    outcome = _merge(state, [{"ip": "192.0.2.10", "mac": MAC_B}], T0 + CYCLE)
    assert len(outcome.created) == 1
    assert len(state["devices"]) == 2


def test_device_after_the_learning_window_is_not_baseline():
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    _merge(state, [{"ip": "192.0.2.11", "mac": MAC_B}], T0 + timedelta(hours=25))
    assert state["devices"]["d_0001"]["baseline"] is True
    assert state["devices"]["d_0002"]["baseline"] is False


def test_private_mac_is_marked_and_gets_no_vendor():
    state = _state()
    _merge(state, [{"ip": "192.0.2.20", "mac": MAC_PRIVATE, "vendor": "Example Corp"}], T0)
    device = state["devices"]["d_0001"]
    assert device["mac_kind"] == "local"
    assert device["vendor"] is None


def test_host_without_mac_waits_one_cycle_then_is_recorded_by_address():
    state = _state()
    first = _merge(state, [{"ip": "192.0.2.30", "open_ports": [{"port": 80}]}], T0)
    assert first.created == []
    assert state["pending"] == {"192.0.2.30": T0.isoformat()}
    second = _merge(state, [{"ip": "192.0.2.30", "open_ports": [{"port": 80}]}], T0 + CYCLE)
    assert second.created == ["d_0001"]
    device = state["devices"]["d_0001"]
    assert device["identity"] == "address"
    assert device["macs"] == []
    assert state["pending"] == {}


def test_pending_host_that_skips_a_cycle_starts_over():
    state = _state()
    _merge(state, [{"ip": "192.0.2.30"}], T0)
    _merge(state, [], T0 + CYCLE)
    assert state["pending"] == {}
    outcome = _merge(state, [{"ip": "192.0.2.30"}], T0 + 2 * CYCLE)
    assert outcome.created == []


def test_address_keyed_record_is_rekeyed_when_its_mac_arrives():
    state = _state()
    _merge(state, [{"ip": "192.0.2.30"}], T0)
    _merge(state, [{"ip": "192.0.2.30"}], T0 + CYCLE)
    outcome = _merge(state, [{"ip": "192.0.2.30", "mac": MAC_A}], T0 + 2 * CYCLE)
    assert outcome.created == []
    assert len(state["devices"]) == 1
    device = state["devices"]["d_0001"]
    assert device["identity"] == "mac"
    assert device["macs"] == [MAC_A]
    assert state["events"][-1]["kind"] == "rekeyed_to_mac"


def test_known_device_seen_without_mac_updates_last_seen_only():
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    outcome = _merge(state, [{"ip": "192.0.2.10"}], T0 + CYCLE)
    assert outcome.created == []
    assert state["pending"] == {}
    assert state["devices"]["d_0001"]["last_seen"] == (T0 + CYCLE).isoformat()


# --------------------------------------------------------------------------
# Pure merge: ports, names, bounds
# --------------------------------------------------------------------------


def test_ports_keep_first_seen_and_age_out():
    state = _state()
    host = {
        "ip": "192.0.2.10",
        "mac": MAC_A,
        "open_ports": [{"port": 22, "service_guess": "ssh", "service_confidence": "high"}],
    }
    _merge(state, [host], T0)
    _merge(state, [host], T0 + CYCLE)
    port = state["devices"]["d_0001"]["ports"]["22"]
    assert port["first_seen"] == T0.isoformat()
    assert port["last_seen"] == (T0 + CYCLE).isoformat()
    assert port["service"] == "ssh"
    later = T0 + timedelta(days=inv.PORT_RETENTION_DAYS + 1)
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], later)
    assert state["devices"]["d_0001"]["ports"] == {}


def test_registry_name_is_recorded_with_its_source():
    state = _state()

    def registry(mac):
        return {"name": "Hallway NAS", "device_id": "abc"} if mac == MAC_A else None

    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0, registry=registry)
    device = state["devices"]["d_0001"]
    assert device["names"] == [{"value": "Hallway NAS", "source": "ha_registry", "ts": T0.isoformat()}]
    assert device["ha_device_id"] == "abc"
    assert inv.best_name(device) == {"value": "Hallway NAS", "source": "ha_registry"}
    device["label"] = "NAS"
    assert inv.best_name(device) == {"value": "NAS", "source": "label"}


def test_untouched_record_is_pruned_after_retention_and_touched_ones_are_kept():
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}, {"ip": "192.0.2.11", "mac": MAC_B}], T0)
    state["devices"]["d_0002"]["verdict"] = "acknowledged"
    _merge(state, [], T0 + timedelta(days=31))
    assert list(state["devices"]) == ["d_0002"]
    assert state["events"][-1] == {
        "ts": (T0 + timedelta(days=31)).isoformat(),
        "device_id": "d_0001",
        "kind": "pruned",
        "reason": "retention",
    }


def test_cap_evicts_the_oldest_untouched_record(monkeypatch):
    monkeypatch.setattr(inv, "MAX_DEVICES", 2)
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    _merge(state, [{"ip": "192.0.2.11", "mac": MAC_B}], T0 + CYCLE)
    _merge(state, [{"ip": "192.0.2.12", "mac": "00:11:22:33:44:77"}], T0 + 2 * CYCLE)
    assert sorted(state["devices"]) == ["d_0002", "d_0003"]
    assert state["meta"]["cap_reached_at"] == (T0 + 2 * CYCLE).isoformat()


def test_cap_refuses_a_new_record_when_every_record_is_the_owners(monkeypatch):
    monkeypatch.setattr(inv, "MAX_DEVICES", 1)
    state = _state()
    _merge(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0)
    state["devices"]["d_0001"]["verdict"] = "acknowledged"
    outcome = _merge(state, [{"ip": "192.0.2.11", "mac": MAC_B}], T0 + CYCLE)
    assert outcome.created == []
    assert list(state["devices"]) == ["d_0001"]
    assert state["meta"]["cap_reached_at"] is not None


def test_event_ring_is_bounded(monkeypatch):
    monkeypatch.setattr(inv, "MAX_EVENTS", 3)
    state = _state()
    for index in range(6):
        _merge(state, [{"ip": f"192.0.2.{10 + index}", "mac": MAC_A}], T0 + index * CYCLE)
    assert len(state["events"]) == 3


# --------------------------------------------------------------------------
# Probe ingest feeds the inventory
# --------------------------------------------------------------------------


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


async def _ingest(hass: HomeAssistant, supervisor_user, hosts) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"netscan_result": hosts, "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=supervisor_user.id),
    )


async def test_ingest_merges_the_cycle_and_reads_the_device_registry(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    other = MockConfigEntry(domain="test", data={})
    other.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, MAC_A)},
        name="Hallway NAS",
    )
    await _ingest(hass, supervisor_user, [{"ip": "192.0.2.10", "mac": MAC_A.upper()}])

    overview = supervisor_entry.runtime_data.inventory.overview()
    assert overview["counts"] == {"unacknowledged": 1, "acknowledged": 0, "ignored": 0}
    device = overview["devices"][0]
    assert device["macs"] == [MAC_A]
    assert device["display_name"] == {"value": "Hallway NAS", "source": "ha_registry"}
    assert device["baseline"] is True


async def test_inventory_survives_a_reload(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    await _ingest(hass, supervisor_user, [{"ip": "192.0.2.10", "mac": MAC_A}])
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        assert await hass.config_entries.async_reload(supervisor_entry.entry_id)
        await hass.async_block_till_done()
    devices = supervisor_entry.runtime_data.inventory.state["devices"]
    assert [d["macs"] for d in devices.values()] == [[MAC_A]]


# --------------------------------------------------------------------------
# Detection rule
# --------------------------------------------------------------------------


async def _entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _network_detections(runtime):
    return [
        d
        for d in runtime.store.data["detections"].values()
        if d["rule_id"] in (RULE_NETWORK_DEVICE_NEW, RULE_NETWORK_DEVICE_BURST)
    ]


async def test_baseline_devices_raise_nothing(hass: HomeAssistant) -> None:
    runtime = (await _entry(hass)).runtime_data
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}])
    await runtime.detections.async_run_pass()
    assert _network_detections(runtime) == []


async def test_device_after_learning_raises_one_detection_without_addresses(
    hass: HomeAssistant,
) -> None:
    runtime = (await _entry(hass)).runtime_data
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}], learning_hours=0)
    await runtime.detections.async_run_pass()
    await runtime.detections.async_run_pass()

    detections = _network_detections(runtime)
    assert len(detections) == 1
    detection = detections[0]
    device_id = next(iter(runtime.inventory.state["devices"]))
    assert detection["id"] == network_device_detection_id(device_id)
    assert detection["status"] == DETECTION_OPEN
    assert detection["recurrence_count"] == 1
    assert detection["ip"] is None
    # The inventory is owner-only; a detection row is not.
    serialized = str(detection)
    assert MAC_A not in serialized
    assert "192.0.2.10" not in serialized


async def test_more_new_devices_than_the_threshold_collapse_into_a_burst(
    hass: HomeAssistant,
) -> None:
    runtime = (await _entry(hass)).runtime_data
    runtime.store.settings["detection_thresholds"] = {RULE_NETWORK_DEVICE_NEW: {"burst_devices": 3}}
    now = datetime(2026, 11, 1, 12, 10, tzinfo=timezone.utc)
    hosts = [{"ip": f"192.0.2.{n}", "mac": f"00:11:22:33:44:{n:02x}"} for n in range(10, 15)]
    with patch("custom_components.ha_soc.detections.dt_util.utcnow", return_value=now):
        runtime.inventory.async_merge_cycle(hosts, learning_hours=0, now=now)
        await runtime.detections.async_run_pass()

    detections = _network_detections(runtime)
    individual = [d for d in detections if d["rule_id"] == RULE_NETWORK_DEVICE_NEW]
    bursts = [d for d in detections if d["rule_id"] == RULE_NETWORK_DEVICE_BURST]
    assert len(individual) == 3
    assert len(bursts) == 1
    assert bursts[0]["severity"] == "high"
    assert bursts[0]["detail"]["count"] == 5
    assert len(bursts[0]["detail"]["collapsed_device_ids"]) == 2


async def test_acknowledged_device_raises_nothing(hass: HomeAssistant) -> None:
    runtime = (await _entry(hass)).runtime_data
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}], learning_hours=0)
    device_id = next(iter(runtime.inventory.state["devices"]))
    runtime.inventory.async_set_verdict(device_id, "acknowledged", by_user_id="owner", at="t")
    await runtime.detections.async_run_pass()
    assert _network_detections(runtime) == []


# --------------------------------------------------------------------------
# WebSocket commands: owner-only, audited
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("handler", "message"),
    [
        ("ws_inventory_list", {"id": 1}),
        ("ws_inventory_set_verdict", {"id": 1, "device_id": "d_x", "verdict": "acknowledged"}),
        ("ws_inventory_set_label", {"id": 1, "device_id": "d_x", "label": "x"}),
    ],
)
async def test_inventory_commands_require_owner(hass: HomeAssistant, handler, message) -> None:
    from custom_components.ha_soc import websocket_api

    await _entry(hass)
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=False)
    with pytest.raises(Unauthorized):
        getattr(websocket_api, handler)(hass, connection, message)


async def test_ws_inventory_list_returns_overview(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_list

    runtime = (await _entry(hass)).runtime_data
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}])
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")
    ws_inventory_list(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["netscan_enabled"] is False
    assert result["learning_hours"] == 24
    assert result["cap"] == inv.MAX_DEVICES
    assert result["devices"][0]["macs"] == [MAC_A]


async def test_acknowledging_resolves_the_detection_and_is_audited(
    hass: HomeAssistant, tmp_path
) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_set_verdict

    runtime = (await _entry(hass)).runtime_data
    runtime.audit._dir_path = str(tmp_path / "audit")
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}], learning_hours=0)
    await runtime.detections.async_run_pass()
    device_id = next(iter(runtime.inventory.state["devices"]))
    detection_id = network_device_detection_id(device_id)
    assert runtime.store.data["detections"][detection_id]["status"] == DETECTION_OPEN

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")
    ws_inventory_set_verdict(
        hass, connection, {"id": 1, "device_id": device_id, "verdict": "acknowledged"}
    )
    await hass.async_block_till_done()

    assert connection.send_result.call_args[0][1] == {
        "ok": True,
        "resolved_detection_id": detection_id,
    }
    assert runtime.inventory.state["devices"][device_id]["verdict"] == "acknowledged"
    assert runtime.store.data["detections"][detection_id]["status"] == DETECTION_RESOLVED
    records = await runtime.audit.async_query(category="inventory_verdict_changed", limit=5)
    assert records[0]["user_id"] == "owner-id"
    assert records[0]["detail"]["old_verdict"] == "unacknowledged"
    assert records[0]["detail"]["new_verdict"] == "acknowledged"


async def test_set_verdict_on_an_unknown_device_is_an_error(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_set_verdict

    await _entry(hass)
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")
    ws_inventory_set_verdict(hass, connection, {"id": 1, "device_id": "d_none", "verdict": "ignored"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once()
    connection.send_result.assert_not_called()


async def test_label_is_trimmed_cleared_and_kept_out_of_the_audit_record(
    hass: HomeAssistant, tmp_path
) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_set_label

    runtime = (await _entry(hass)).runtime_data
    runtime.audit._dir_path = str(tmp_path / "audit")
    runtime.inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}])
    device_id = next(iter(runtime.inventory.state["devices"]))
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")

    ws_inventory_set_label(hass, connection, {"id": 1, "device_id": device_id, "label": "  Printer  "})
    await hass.async_block_till_done()
    assert runtime.inventory.state["devices"][device_id]["label"] == "Printer"
    records = await runtime.audit.async_query(category="inventory_label_changed", limit=5)
    assert records[0]["detail"] == {"device_id": device_id, "label_set": True}

    ws_inventory_set_label(hass, connection, {"id": 2, "device_id": device_id, "label": None})
    await hass.async_block_till_done()
    assert runtime.inventory.state["devices"][device_id]["label"] is None
