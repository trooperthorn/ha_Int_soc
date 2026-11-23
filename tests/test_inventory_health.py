"""Tests for phase 5 of the network inventory: duplicate address, devices dropping
together, steady restarts and a slower gateway, plus the Probe's default-route read.
"""
import importlib.util
import io
import sys
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.detections import RULE_NETWORK_DUPLICATE_ADDRESS
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
CYCLE = timedelta(minutes=5)
GATEWAY_IP = "192.0.2.1"
PROBE_NETSCAN = (
    Path(__file__).parents[1] / "ha_soc_probe" / "rootfs" / "usr" / "lib" / "ha_soc" / "netscan.py"
)


def _mac(index: int) -> str:
    return f"00:11:22:33:{index // 256:02x}:{index % 256:02x}"


def _host(index: int, *, ip=None, present=True, rtt=None):
    host = {"ip": ip or f"192.0.2.{10 + index}", "mac": _mac(index), "open_ports": []}
    if present:
        host["arp_after_sweep"] = True
    if rtt is not None:
        host.update(responded=True, rtt_ms=rtt)
    return host


class _Replay:
    def __init__(self):
        self.state = inv.empty_state()
        self.now = T0
        ids = count(1)
        self._new_id = lambda: f"d_{next(ids):04d}"

    def cycle(self, hosts, *, gap=CYCLE, **kwargs):
        inv.merge_cycle(self.state, hosts, self.now, new_id=self._new_id, presence=True, **kwargs)
        self.now += gap

    def events(self, kind):
        return [e for e in self.state["events"] if e["kind"] == kind]


# --------------------------------------------------------------------------
# The Probe's default route
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def probe_netscan():
    pytest.importorskip("fcntl", reason="the Probe scanner is Linux only")
    sys.path.insert(0, str(PROBE_NETSCAN.parent))
    try:
        spec = importlib.util.spec_from_file_location("ha_soc_probe_netscan_health", PROBE_NETSCAN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROBE_NETSCAN.parent))
    return module


# Captured from a Linux host on 2026-11-23; `ip route` on it read "default via 172.27.128.1".
ROUTE_TABLE = (
    "Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT\n"
    "docker0\t000011AC\t00000000\t0001\t0\t0\t0\t0000FFFF\t0\t0\t0\n"
    "eth0\t00000000\t01801BAC\t0003\t0\t0\t0\t00000000\t0\t0\t0\n"
    "eth0\t00801BAC\t00000000\t0001\t0\t0\t0\t00F0FFFF\t0\t0\t0\n"
)


def test_probe_reads_the_default_gateway(probe_netscan, monkeypatch):
    monkeypatch.setattr(probe_netscan, "open", lambda *a, **k: io.StringIO(ROUTE_TABLE), raising=False)
    assert probe_netscan._default_gateway() == "172.27.128.1"


@pytest.mark.parametrize(
    "table",
    [
        "Iface\tDestination\tGateway\tFlags\n",
        "Iface\tDestination\tGateway\tFlags\neth0\t00000000\t00000000\t0001\n",
        "Iface\tDestination\tGateway\tFlags\neth0\t00000000\tnothex!!\t0003\n",
    ],
)
def test_probe_reports_no_gateway_when_there_is_none(probe_netscan, monkeypatch, table):
    monkeypatch.setattr(probe_netscan, "open", lambda *a, **k: io.StringIO(table), raising=False)
    assert probe_netscan._default_gateway() is None


# --------------------------------------------------------------------------
# Duplicate address
# --------------------------------------------------------------------------


def test_one_change_of_holder_is_a_lease_moving_on():
    replay = _Replay()
    replay.cycle([_host(1, ip="192.0.2.50")])
    replay.cycle([_host(2, ip="192.0.2.50")])
    replay.cycle([_host(2, ip="192.0.2.50")])
    assert replay.events("duplicate_address") == []


def test_two_devices_swapping_an_address_are_reported_once_per_hour():
    replay = _Replay()
    for turn in range(8):
        replay.cycle([_host(1 + turn % 2, ip="192.0.2.50")])
    events = replay.events("duplicate_address")
    assert len(events) == 1
    event = events[0]
    assert event["alert"] is True
    assert {event["device_id"], event["other_device_id"]} == {"d_0001", "d_0002"}
    assert event["flips"] == 3

    replay.now += timedelta(hours=2)
    for turn in range(4):
        replay.cycle([_host(1 + turn % 2, ip="192.0.2.50")])
    assert len(replay.events("duplicate_address")) == 2


def test_slow_swaps_outside_the_window_are_not_reported():
    replay = _Replay()
    for turn in range(8):
        replay.cycle([_host(1 + turn % 2, ip="192.0.2.50")], gap=timedelta(minutes=40))
    assert replay.events("duplicate_address") == []


def test_tracked_addresses_are_bounded(monkeypatch):
    monkeypatch.setattr(inv, "MAX_TRACKED_ADDRESSES", 3)
    replay = _Replay()
    replay.cycle([_host(index) for index in range(6)])
    assert len(replay.state["meta"]["address_holders"]) == 3


async def test_duplicate_address_raises_a_high_detection_whatever_the_verdict(
    hass: HomeAssistant,
) -> None:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    runtime = config_entry.runtime_data
    now = datetime.now(timezone.utc) - timedelta(minutes=30)
    for turn in range(4):
        runtime.inventory.async_merge_cycle(
            [_host(1 + turn % 2, ip="192.0.2.50")], now=now + turn * CYCLE
        )
    await runtime.detections.async_run_pass()
    await runtime.detections.async_run_pass()

    found = [
        d for d in runtime.store.data["detections"].values()
        if d["rule_id"] == RULE_NETWORK_DUPLICATE_ADDRESS
    ]
    assert [d["severity"] for d in found] == ["high"]
    assert set(found[0]["detail"]) == {"device_id", "changed_at", "other_device_id"}
    assert "192.0.2.50" not in repr(found[0]) and _mac(1) not in repr(found[0])


# --------------------------------------------------------------------------
# Drop together and steady restarts
# --------------------------------------------------------------------------


def test_many_devices_dropping_in_one_cycle_is_recorded_and_forgotten_after_three_clean_cycles():
    replay = _Replay()
    everyone = [_host(index) for index in range(20)]
    survivors = everyone[:14]
    replay.cycle(everyone)
    replay.cycle(everyone)
    assert inv.drop_together(replay.state, min_devices=5, percent=10) is None

    replay.cycle(survivors)
    drop = inv.drop_together(replay.state, min_devices=5, percent=10)
    assert (drop["dropped"], drop["of"]) == (6, 20)
    assert inv.drop_together(replay.state, min_devices=7, percent=10) is None
    assert inv.drop_together(replay.state, min_devices=5, percent=40) is None

    replay.cycle(survivors)
    replay.cycle(survivors)
    assert inv.drop_together(replay.state, min_devices=5, percent=10) is not None
    replay.cycle(survivors)
    assert inv.drop_together(replay.state, min_devices=5, percent=10) is None


def test_randomized_macs_do_not_count_as_drops():
    replay = _Replay()
    phones = [{"ip": f"192.0.2.{100 + i}", "mac": f"da:11:22:33:44:{i:02x}", "arp_after_sweep": True} for i in range(8)]
    anchor = _host(1)
    replay.cycle([anchor, *phones])
    replay.cycle([anchor])
    assert replay.state["meta"]["drop_cycles"][-1] == {
        "at": (replay.now - CYCLE).isoformat(), "dropped": 0, "of": 1
    }
    assert all("drops" not in d for d in replay.state["devices"].values())


def test_device_that_keeps_dropping_is_a_steady_restart():
    replay = _Replay()
    anchor, flaky = _host(1), _host(2)
    for _ in range(5):
        replay.cycle([anchor, flaky])
        replay.cycle([anchor], gap=timedelta(minutes=25))
    rows = inv.steady_restarts(replay.state, replay.now, drops_per_day=5)
    assert [(r["device_id"], r["drops"]) for r in rows] == [("d_0002", 5)]
    assert inv.steady_restarts(replay.state, replay.now, drops_per_day=6) == []
    # A day later the drops have aged out.
    assert inv.steady_restarts(replay.state, replay.now + timedelta(days=1), drops_per_day=5) == []


def test_drops_too_far_apart_are_not_a_steady_restart():
    replay = _Replay()
    anchor, flaky = _host(1), _host(2)
    for index in range(5):
        replay.cycle([anchor, flaky])
        replay.cycle([anchor], gap=timedelta(hours=7 if index == 2 else 1))
    assert inv.steady_restarts(replay.state, replay.now, drops_per_day=5) == []


# --------------------------------------------------------------------------
# Slower gateway
# --------------------------------------------------------------------------


def _gateway_run(replay, baseline_ms, recent_ms, *, baseline_cycles=20, recent_cycles=3):
    for ms in [baseline_ms] * baseline_cycles + [recent_ms] * recent_cycles:
        replay.cycle([_host(1, ip=GATEWAY_IP, rtt=ms)], gateway_ip=GATEWAY_IP)


def test_gateway_is_tagged_and_keeps_a_bounded_history():
    replay = _Replay()
    _gateway_run(replay, 2.0, 2.0, baseline_cycles=200, recent_cycles=0)
    assert replay.state["meta"]["gateway_device_id"] == "d_0001"
    history = replay.state["devices"]["d_0001"]["rtt_history"]
    assert len(history) <= inv.MAX_RTT_SAMPLES
    assert history[-1][1] == 2.0


def test_slower_gateway_needs_both_the_factor_and_the_margin():
    replay = _Replay()
    _gateway_run(replay, 2.0, 9.0)
    last = replay.now - CYCLE
    assert inv.slower_gateway(replay.state, last, factor=3, min_ms=3) == {
        "device_id": "d_0001", "recent_ms": 9.0, "baseline_ms": 2.0,
    }
    assert inv.slower_gateway(replay.state, last, factor=5, min_ms=3) is None
    assert inv.slower_gateway(replay.state, last, factor=3, min_ms=10) is None

    quick = _Replay()
    _gateway_run(quick, 0.4, 1.6)
    assert inv.slower_gateway(quick.state, quick.now - CYCLE, factor=3, min_ms=3) is None


def test_slower_gateway_says_nothing_without_a_baseline_or_a_gateway():
    replay = _Replay()
    _gateway_run(replay, 2.0, 9.0, baseline_cycles=5)
    assert inv.slower_gateway(replay.state, replay.now - CYCLE, factor=3, min_ms=3) is None
    other = _Replay()
    other.cycle([_host(1, rtt=50.0)])
    assert inv.slower_gateway(other.state, other.now, factor=3, min_ms=3) is None


def test_a_different_device_at_the_gateway_address_starts_a_fresh_baseline():
    replay = _Replay()
    _gateway_run(replay, 2.0, 2.0, recent_cycles=0)
    replay.cycle([_host(2, ip=GATEWAY_IP, rtt=30.0)], gateway_ip=GATEWAY_IP)
    assert replay.state["meta"]["gateway_device_id"] == "d_0002"
    assert replay.state["devices"]["d_0002"]["rtt_history"] == [[(replay.now - CYCLE).isoformat(), 30.0]]


def test_an_invalid_gateway_address_is_ignored():
    replay = _Replay()
    replay.cycle([_host(1)], gateway_ip="not an address")
    assert replay.state["meta"]["gateway_ip"] is None


# --------------------------------------------------------------------------
# Health check
# --------------------------------------------------------------------------


class _Inventory:
    def __init__(self, state):
        self.state = state


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationHealth(hass, store)


async def test_health_check_is_quiet_on_a_healthy_or_absent_inventory(hass, health) -> None:
    assert await health._check_network_health() == []
    replay = _Replay()
    replay.cycle([_host(index) for index in range(10)])
    health.inventory = _Inventory(replay.state)
    assert await health._check_network_health() == []


async def test_health_check_reports_all_three_conditions_as_low_findings(hass, health) -> None:
    replay = _Replay()
    replay.now = datetime.now(timezone.utc) - timedelta(hours=4)
    crowd = [_host(index) for index in range(10, 30)]
    flaky = _host(2)
    for _ in range(5):
        replay.cycle([_host(1, ip=GATEWAY_IP, rtt=2.0), flaky, *crowd], gateway_ip=GATEWAY_IP)
        replay.cycle([_host(1, ip=GATEWAY_IP, rtt=2.0), *crowd], gateway_ip=GATEWAY_IP, gap=timedelta(minutes=20))
    for _ in range(8):
        replay.cycle([_host(1, ip=GATEWAY_IP, rtt=2.0), flaky, *crowd], gateway_ip=GATEWAY_IP)
    replay.now = datetime.now(timezone.utc) - timedelta(minutes=12)
    for _ in range(3):
        replay.cycle([_host(1, ip=GATEWAY_IP, rtt=40.0), flaky, *crowd[:10]], gateway_ip=GATEWAY_IP, gap=timedelta(minutes=4))
    health.inventory = _Inventory(replay.state)

    findings = await health._check_network_health()
    by_check = {f["check"]: f for f in findings}
    assert set(by_check) == {
        "network_drop_together", "network_steady_restarts", "network_slower_gateway",
    }
    assert {f["severity"] for f in findings} == {"low"}
    assert by_check["network_drop_together"]["detail"]["dropped"] == 10
    assert by_check["network_steady_restarts"]["detail"]["device_id"] == "d_0002"
    assert by_check["network_slower_gateway"]["detail"]["recent_ms"] == 40.0
    flat = repr(findings)
    assert GATEWAY_IP not in flat and _mac(2) not in flat
    registry = ir.async_get(hass)
    assert all(registry.async_get_issue(DOMAIN, f["id"]) is not None for f in findings)

    health.inventory = _Inventory(inv.empty_state())
    assert await health._check_network_health() == []
    assert all(registry.async_get_issue(DOMAIN, f["id"]) is None for f in findings)
