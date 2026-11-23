"""Tests for phase 4 of the network inventory: the Probe's presence signals,
presence segments, the Watch action, and the gone-and-back detection.
"""
import asyncio
import importlib.util
import io
import socket
import sys
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DETECTION_OPEN, DETECTION_RESOLVED, DOMAIN
from custom_components.ha_soc.detections import RULE_NETWORK_DEVICE_DOWN
from custom_components.ha_soc.netscan import NETSCAN_HOST_SCHEMA

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

PROBE_SECRET = "unit-test-probe-secret"
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
CYCLE = timedelta(minutes=5)
MAC_A = "00:11:22:33:44:55"
MAC_B = "00:11:22:33:44:66"
MAC_PRIVATE = "da:11:22:33:44:77"
IP_A = "192.0.2.10"
IP_B = "192.0.2.11"
PROBE_NETSCAN = (
    Path(__file__).parents[1] / "ha_soc_probe" / "rootfs" / "usr" / "lib" / "ha_soc" / "netscan.py"
)


# --------------------------------------------------------------------------
# The Probe's own scanner
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def probe_netscan():
    pytest.importorskip("fcntl", reason="the Probe scanner is Linux only")
    sys.path.insert(0, str(PROBE_NETSCAN.parent))
    try:
        spec = importlib.util.spec_from_file_location("ha_soc_probe_netscan_presence", PROBE_NETSCAN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROBE_NETSCAN.parent))
    return module


ARP_TABLE = """IP address       HW type     Flags       HW address            Mask     Device
192.0.2.10       0x1         0x2         00:11:22:33:44:55     *        eth0
192.0.2.11       0x1         0x0         00:00:00:00:00:00     *        eth0
192.0.2.12       0x1         0x0         00:11:22:33:44:66     *        eth0
192.0.2.13       0x1         0x6         00:11:22:33:44:77     *        eth0
not-an-address   0x1         0x2         00:11:22:33:44:88     *        eth0
"""


def test_probe_reads_only_complete_arp_entries(probe_netscan, monkeypatch):
    monkeypatch.setattr(probe_netscan, "open", lambda *a, **k: io.StringIO(ARP_TABLE), raising=False)
    assert probe_netscan._read_arp_complete() == {
        "192.0.2.10": "00:11:22:33:44:55",
        "192.0.2.13": "00:11:22:33:44:77",
    }


def _closed_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _cycle_against_loopback(probe_netscan, monkeypatch, *, presence, arp_after=None):
    async def _serve(_reader, writer):
        writer.close()

    server = await asyncio.start_server(_serve, "127.0.0.1", 0)
    open_port = server.sockets[0].getsockname()[1]
    monkeypatch.setattr(probe_netscan, "_read_arp_table", dict)
    monkeypatch.setattr(probe_netscan, "_local_ipv4_networks", list)
    monkeypatch.setattr(probe_netscan, "_sweep_targets", lambda networks, arp: ["127.0.0.1"])
    monkeypatch.setattr(probe_netscan, "_read_arp_complete", lambda: dict(arp_after or {}))
    monkeypatch.setattr(probe_netscan, "ARP_SETTLE_SECONDS", 0)
    return open_port, probe_netscan._run_cycle, server


@pytest.mark.usefixtures("socket_enabled")
async def test_probe_reports_a_refused_connection_as_an_answer(probe_netscan, monkeypatch):
    open_port, run_cycle, server = await _cycle_against_loopback(
        probe_netscan, monkeypatch, presence=True, arp_after={"127.0.0.1": MAC_A, "192.0.2.50": MAC_B}
    )
    try:
        refused_only = await run_cycle([_closed_port()], 4, None, True)
        both = await run_cycle([open_port, _closed_port()], 4, None, True)
    finally:
        server.close()
        await server.wait_closed()

    loopback = next(h for h in refused_only if h["ip"] == "127.0.0.1")
    assert loopback["open_ports"] == []
    assert loopback["responded"] is True
    assert loopback["arp_after_sweep"] is True
    assert loopback["mac"] == MAC_A
    assert 0 <= loopback["rtt_ms"] < 750
    # A host that only shows in the post-sweep ARP table is listed, without "responded".
    arp_only = next(h for h in refused_only if h["ip"] == "192.0.2.50")
    assert arp_only == {"ip": "192.0.2.50", "open_ports": [], "arp_after_sweep": True, "mac": MAC_B}

    loopback = next(h for h in both if h["ip"] == "127.0.0.1")
    assert [p["port"] for p in loopback["open_ports"]] == [open_port]
    assert "_rtt_ms" not in loopback["open_ports"][0]
    for host in both:
        NETSCAN_HOST_SCHEMA(host)


@pytest.mark.usefixtures("socket_enabled")
async def test_probe_keeps_the_old_report_shape_without_presence(probe_netscan, monkeypatch):
    open_port, run_cycle, server = await _cycle_against_loopback(
        probe_netscan, monkeypatch, presence=False, arp_after={"127.0.0.1": MAC_A}
    )
    try:
        refused_only = await run_cycle([_closed_port()], 4, None, False)
        opened = await run_cycle([open_port], 4, None, False)
    finally:
        server.close()
        await server.wait_closed()
    assert refused_only == []
    assert opened == [{"ip": "127.0.0.1", "open_ports": [{"port": open_port}]}]


def test_probe_accepts_list_parsing(probe_netscan):
    assert probe_netscan._parse_accepts(None) == set()
    assert probe_netscan._parse_accepts("not json") == set()
    assert probe_netscan._parse_accepts('{"presence": true}') == set()
    assert probe_netscan._parse_accepts('["presence", 7, "future"]') == {"presence", "future"}


def test_schema_bounds_the_presence_fields():
    NETSCAN_HOST_SCHEMA({"ip": IP_A, "responded": True, "arp_after_sweep": False, "rtt_ms": 1.4})
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"ip": IP_A, "rtt_ms": -1})
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"ip": IP_A, "responded": "yes"})


# --------------------------------------------------------------------------
# Pure merge: presence
# --------------------------------------------------------------------------


class _Replay:
    """Two devices, A and B. B answers on every cycle so that a cycle is always judged."""

    def __init__(self, down_cycles=3):
        self.state = inv.empty_state()
        self.now = T0
        self.down_cycles = down_cycles
        ids = count(1)
        self._new_id = lambda: f"d_{next(ids):04d}"

    def cycle(self, a=True, *, b=True, presence=True, rtt=None, gap=CYCLE):
        hosts = []
        if a is not None:
            host = {"ip": IP_A, "mac": MAC_A, "open_ports": []}
            if a:
                host["arp_after_sweep"] = True
            if rtt is not None:
                host.update(responded=True, rtt_ms=rtt)
            hosts.append(host)
        if b:
            hosts.append({"ip": IP_B, "mac": MAC_B, "open_ports": [], "arp_after_sweep": True})
        inv.merge_cycle(
            self.state,
            hosts,
            self.now,
            new_id=self._new_id,
            presence=presence,
            down_cycles=self.down_cycles,
        )
        self.now += gap

    @property
    def a(self):
        return self.state["devices"]["d_0001"]

    def events(self):
        return [e for e in self.state["events"] if e["kind"] in inv.PRESENCE_EVENT_KINDS]


def test_presence_is_one_segment_while_a_device_keeps_answering():
    replay = _Replay()
    for _ in range(4):
        replay.cycle(rtt=2.5)
    assert replay.a["presence"] == [
        {"from": T0.isoformat(), "to": (T0 + 3 * CYCLE).isoformat()}
    ]
    assert replay.a["missed_cycles"] == 0
    assert replay.a["rtt_ms"] == 2.5


def test_one_missed_cycle_does_not_split_the_segment_and_a_long_gap_does():
    replay = _Replay()
    replay.cycle()
    replay.cycle(a=False)
    replay.cycle()
    assert len(replay.a["presence"]) == 1
    for _ in range(3):
        replay.cycle(a=False)
    assert replay.a["missed_cycles"] == 3
    replay.cycle()
    assert len(replay.a["presence"]) == 2


def test_a_stale_arp_listing_is_not_presence():
    replay = _Replay()
    replay.cycle()
    replay.cycle(a=False)  # listed from the pre-sweep table, no signal this cycle
    assert replay.a["missed_cycles"] == 1
    replay.cycle(a=None)  # not listed at all
    assert replay.a["missed_cycles"] == 2


def test_cycle_without_presence_signals_is_not_judged():
    replay = _Replay()
    replay.cycle(presence=False)
    replay.cycle(a=False, presence=False)
    assert "presence" not in replay.a
    assert "missed_cycles" not in replay.a


def test_cycle_in_which_nothing_answered_is_not_judged():
    replay = _Replay()
    replay.cycle()
    replay.a["watched"] = True
    for _ in range(5):
        replay.cycle(a=False, b=False)
    assert replay.a["missed_cycles"] == 0
    assert replay.events() == []
    assert replay.state["meta"]["presence_skipped_at"] is not None


def test_watched_device_goes_down_after_the_threshold_and_comes_back_once():
    replay = _Replay(down_cycles=3)
    replay.cycle()
    replay.a["watched"] = True
    replay.cycle(a=False)
    replay.cycle(a=False)
    assert replay.events() == []
    replay.cycle(a=False)
    down_at = (replay.now - CYCLE).isoformat()
    assert [(e["kind"], e["alert"]) for e in replay.events()] == [("device_down", True)]
    assert replay.a["down_since"] == down_at
    replay.cycle(a=False)
    assert len(replay.events()) == 1

    replay.cycle()
    back = replay.events()[-1]
    assert (back["kind"], back["alert"], back["down_since"]) == ("device_back", True, down_at)
    assert back["minutes_away"] == 10
    assert "down_since" not in replay.a
    replay.cycle()
    assert len(replay.events()) == 2


def test_unwatched_device_never_goes_down():
    replay = _Replay(down_cycles=2)
    replay.cycle()
    for _ in range(6):
        replay.cycle(a=False)
    assert replay.events() == []
    assert replay.a["missed_cycles"] == 6


def test_device_only_the_controller_reports_is_not_judged():
    replay = _Replay()
    inv.merge_unifi_clients(
        replay.state, [{"mac": MAC_PRIVATE, "ipv4": "198.51.100.5", "name": "phone"}], T0,
        new_id=replay._new_id,
    )
    replay.cycle(a=None)
    replay.cycle(a=None)
    unifi_only = next(d for d in replay.state["devices"].values() if d["macs"] == [MAC_PRIVATE])
    assert "missed_cycles" not in unifi_only


def test_presence_segments_are_bounded(monkeypatch):
    monkeypatch.setattr(inv, "MAX_PRESENCE_SEGMENTS", 3)
    replay = _Replay()
    for _ in range(6):
        replay.cycle(gap=timedelta(hours=1))
    assert len(replay.a["presence"]) == 3
    replay.now += timedelta(days=40)
    replay.cycle()
    assert len(replay.a["presence"]) == 1


# --------------------------------------------------------------------------
# Ingest, the Watch command and the detection
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


async def test_presence_is_judged_only_when_the_probe_reports_the_capability(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    context = Context(user_id=supervisor_user.id)
    host = {"ip": IP_A, "mac": MAC_A, "arp_after_sweep": True, "responded": True, "rtt_ms": 3}

    async def _ingest(capabilities):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {"netscan_result": [host], "netscan_capabilities": capabilities, "probe_secret": PROBE_SECRET},
            blocking=True,
            context=context,
        )

    await _ingest({"tcp_connect": True})
    device = next(iter(supervisor_entry.runtime_data.inventory.state["devices"].values()))
    assert "presence" not in device

    await _ingest({"tcp_connect": True, "presence": True})
    assert len(device["presence"]) == 1
    assert device["rtt_ms"] == 3.0

    response = await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=context,
    )
    assert response["accepts"] == ["presence"]


async def _entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _owner_connection(hass: HomeAssistant, *, owner=True):
    connection = MagicMock()
    connection.user.is_owner = owner
    connection.user.is_admin = True
    connection.user.id = "owner-id"
    return connection


async def test_set_watch_requires_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_set_watch

    await _entry(hass)
    with pytest.raises(Unauthorized):
        ws_inventory_set_watch(
            hass, _owner_connection(hass, owner=False), {"id": 1, "device_id": "d_x", "watched": True}
        )


async def test_set_watch_is_audited_and_refuses_a_randomized_mac(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_inventory_set_watch

    runtime = (await _entry(hass)).runtime_data
    runtime.inventory.async_merge_cycle(
        [{"ip": IP_A, "mac": MAC_A}, {"ip": IP_B, "mac": MAC_PRIVATE}]
    )
    by_mac = {d["macs"][0]: d for d in runtime.inventory.state["devices"].values()}
    connection = _owner_connection(hass)

    with patch.object(runtime.audit, "async_log") as audit_log:
        ws_inventory_set_watch(
            hass, connection, {"id": 1, "device_id": by_mac[MAC_A]["id"], "watched": True}
        )
        ws_inventory_set_watch(
            hass, connection, {"id": 2, "device_id": by_mac[MAC_PRIVATE]["id"], "watched": True}
        )
        ws_inventory_set_watch(hass, connection, {"id": 3, "device_id": "d_missing", "watched": True})
        await hass.async_block_till_done()

    assert by_mac[MAC_A]["watched"] is True
    assert by_mac[MAC_PRIVATE]["watched"] is False
    connection.send_result.assert_called_once_with(1, {"ok": True})
    assert [call.args[1] for call in connection.send_error.call_args_list] == ["not_supported", "not_found"]
    audit_log.assert_called_once_with(
        "inventory_watch_changed",
        user_id="owner-id",
        detail={"device_id": by_mac[MAC_A]["id"], "watched": True},
    )


async def test_down_raises_a_low_detection_that_closes_itself_when_the_device_is_back(
    hass: HomeAssistant,
) -> None:
    runtime = (await _entry(hass)).runtime_data
    inventory = runtime.inventory
    here = {"ip": IP_A, "mac": MAC_A, "arp_after_sweep": True}
    other = {"ip": IP_B, "mac": MAC_B, "arp_after_sweep": True}
    now = datetime.now(timezone.utc) - timedelta(hours=1)

    def _cycle(hosts):
        nonlocal now
        inventory.async_merge_cycle(hosts, presence=True, down_cycles=2, now=now)
        now += CYCLE

    _cycle([here, other])
    device = next(d for d in inventory.state["devices"].values() if d["macs"] == [MAC_A])
    inventory.async_set_watch(device["id"], True, at=now.isoformat())
    _cycle([other])
    _cycle([other])
    await runtime.detections.async_run_pass()

    downs = [d for d in runtime.store.data["detections"].values() if d["rule_id"] == RULE_NETWORK_DEVICE_DOWN]
    assert [(d["severity"], d["status"]) for d in downs] == [("low", DETECTION_OPEN)]
    assert set(downs[0]["detail"]) == {"device_id", "changed_at"}
    assert MAC_A not in repr(downs[0]) and IP_A not in repr(downs[0])

    _cycle([here, other])
    await runtime.detections.async_run_pass()
    await runtime.detections.async_run_pass()
    assert downs[0]["status"] == DETECTION_RESOLVED
    assert downs[0]["detail"]["minutes_away"] == 5
    assert len([d for d in runtime.store.data["detections"].values() if d["rule_id"] == RULE_NETWORK_DEVICE_DOWN]) == 1


async def test_unwatching_clears_the_down_state_and_raises_nothing(hass: HomeAssistant) -> None:
    runtime = (await _entry(hass)).runtime_data
    inventory = runtime.inventory
    other = {"ip": IP_B, "mac": MAC_B, "arp_after_sweep": True}
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    inventory.async_merge_cycle(
        [{"ip": IP_A, "mac": MAC_A, "arp_after_sweep": True}, other], presence=True, now=now
    )
    device = next(d for d in inventory.state["devices"].values() if d["macs"] == [MAC_A])
    inventory.async_set_watch(device["id"], True, at=now.isoformat())
    for index in range(1, 4):
        inventory.async_merge_cycle([other], presence=True, now=now + index * CYCLE)
    assert device["down_since"]
    inventory.async_set_watch(device["id"], False, at=(now + 4 * CYCLE).isoformat())
    assert "down_since" not in device
    await runtime.detections.async_run_pass()
    assert [d for d in runtime.store.data["detections"].values() if d["rule_id"] == RULE_NETWORK_DEVICE_DOWN] == []
