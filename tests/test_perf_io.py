"""Supervisor calls and flash writes: the regression tests for the October audit's
optimisation findings (OPT-1, OPT-2, OPT-3, OPT-7).

Each test measures a count or a byte total, not a timing, and compares it with what the
same scenario cost before the change. The "before" figures are recorded in
docs/decisions.md (2026-10-08).
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.ha_soc import integration_security as isec
from custom_components.ha_soc import observe_push as op
from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.const import (
    STORAGE_KEY,
    SYSLOG_RING_KEY,
    SYSLOG_RING_SAVE_DELAY,
)
from custom_components.ha_soc.resource_watchdog import (
    HISTORY_SAVE_INTERVAL_SECONDS,
    STATS_MIN_INTERVAL_SECONDS,
    ResourceWatchdog,
)
from custom_components.ha_soc.store import HaSocData, default_store_data

# Private config directory per test: these tests read back the files they write.
ISOLATED_CONFIG_DIR = True

ADDONS = 30
# One pass over 30 started add-ons asks the Supervisor for 30 add-on stats plus Core and
# Supervisor. Before the change the Observe push did this once a minute with the watchdog off,
# and the watchdog did it once a minute with the watchdog on.
CALLS_PER_PASS = ADDONS + 2
BEFORE_CALLS_PER_MINUTE = CALLS_PER_PASS


def _stat() -> SimpleNamespace:
    return SimpleNamespace(
        cpu_percent=1.0,
        memory_usage=1,
        memory_limit=2,
        memory_percent=50.0,
        network_rx=1,
        network_tx=1,
        blk_read=1,
        blk_write=1,
    )


class _Supervisor:
    """A fake Supervisor client that counts every stats request."""

    def __init__(self) -> None:
        self.calls = 0
        self.client = MagicMock()
        self.client.addons.addon_stats = self._count
        self.client.homeassistant.stats = self._count
        self.client.supervisor.stats = self._count
        self.addons = [
            {"slug": f"a{i}", "name": f"A{i}", "state": "started"} for i in range(ADDONS)
        ]

    async def _count(self, *_args: Any) -> SimpleNamespace:
        self.calls += 1
        return _stat()

    def patches(self):
        return (
            patch(
                "homeassistant.components.hassio.get_supervisor_client",
                return_value=self.client,
            ),
            patch(
                "homeassistant.components.hassio.get_addons_list",
                side_effect=lambda _hass: list(self.addons),
            ),
        )


def _watchdog(hass: HomeAssistant, **config: Any) -> ResourceWatchdog:
    store = HaSocData(hass)
    store.data = default_store_data()
    store.data["resource_watchdog"].update(config)
    return ResourceWatchdog(hass, store, MagicMock())


def _collector(hass: HomeAssistant, watchdog: ResourceWatchdog) -> op.SnapshotCollector:
    health = MagicMock()
    health.async_integration_overview = AsyncMock(return_value={})
    collector = op.SnapshotCollector(
        hass,
        watchdog.store,
        health=health,
        watchdog=watchdog,
        crash_forensics=MagicMock(),
    )
    collector._slow_parts = AsyncMock(return_value={})  # type: ignore[method-assign]
    return collector


# --------------------------------------------------------------------------- OPT-1


async def test_watchdog_off_supervisor_calls_per_minute_at_most_a_third(
    hass: HomeAssistant, freezer
) -> None:
    """Watchdog off, 30 add-ons, the push collects every minute for half an hour."""
    hass.config.components.add("hassio")
    watchdog = _watchdog(hass, enabled=False)
    collector = _collector(hass, watchdog)
    supervisor = _Supervisor()
    minutes = 30
    patches = supervisor.patches()
    with patches[0], patches[1]:
        for _ in range(minutes):
            snapshot = await collector.async_collect()
            assert len(snapshot["containers"]["containers"]) == CALLS_PER_PASS
            freezer.tick(timedelta(seconds=60))
    before = BEFORE_CALLS_PER_MINUTE * minutes
    print(f"OPT-1 watchdog off: {supervisor.calls / minutes:.1f} calls/min (before {before / minutes:.1f})")
    assert supervisor.calls * 3 <= before


async def test_watchdog_on_push_and_watchdog_share_one_sample(
    hass: HomeAssistant, freezer
) -> None:
    """Watchdog every 60 s: the push, collecting a second later, adds no Supervisor calls."""
    hass.config.components.add("hassio")
    watchdog = _watchdog(hass, enabled=True, interval_seconds=60)
    collector = _collector(hass, watchdog)
    supervisor = _Supervisor()
    minutes = 10
    patches = supervisor.patches()
    with patches[0], patches[1]:
        for _ in range(minutes):
            await watchdog._async_sample()
            freezer.tick(timedelta(seconds=1))
            await collector.async_collect()
            freezer.tick(timedelta(seconds=59))
    assert supervisor.calls == minutes * CALLS_PER_PASS


async def test_push_that_samples_first_spares_the_watchdog_tick(
    hass: HomeAssistant, freezer
) -> None:
    """A sample the push took just before the watchdog tick is evaluated once, not refetched."""
    hass.config.components.add("hassio")
    watchdog = _watchdog(hass, enabled=True, interval_seconds=60)
    collector = _collector(hass, watchdog)
    supervisor = _Supervisor()
    patches = supervisor.patches()
    with patches[0], patches[1]:
        await collector.async_collect()
        freezer.tick(timedelta(seconds=61))
        await collector.async_collect()  # older than the 60 s gap, so it samples
        assert supervisor.calls == 2 * CALLS_PER_PASS
        await watchdog._async_sample()  # the tick right behind it reuses that sample
        assert supervisor.calls == 2 * CALLS_PER_PASS
        # The reused sample was still evaluated.
        assert len(watchdog._history["a0"]) == 1
        await watchdog._async_sample()  # nothing new to evaluate
        assert len(watchdog._history["a0"]) == 1


async def test_concurrent_callers_wait_for_one_sample(hass: HomeAssistant) -> None:
    hass.config.components.add("hassio")
    watchdog = _watchdog(hass, enabled=False)
    supervisor = _Supervisor()
    patches = supervisor.patches()
    with patches[0], patches[1]:
        results = await asyncio.gather(*(watchdog.async_shared_overview() for _ in range(5)))
    assert supervisor.calls == CALLS_PER_PASS
    assert all(result is results[0] for result in results)


@pytest.mark.parametrize(
    ("config", "gap"),
    [
        ({"enabled": False, "interval_seconds": 60}, STATS_MIN_INTERVAL_SECONDS),
        ({"enabled": True, "interval_seconds": 60}, 60),
        ({"enabled": True, "interval_seconds": 30}, 30),
        ({"enabled": True, "interval_seconds": 600}, STATS_MIN_INTERVAL_SECONDS),
        ({"enabled": True, "interval_seconds": 5}, 30),
    ],
)
async def test_sample_gap(hass: HomeAssistant, config: dict[str, Any], gap: int) -> None:
    assert _watchdog(hass, **config).sample_gap() == gap


# --------------------------------------------------------------------------- OPT-3


def _overview(slugs: list[str]) -> dict[str, Any]:
    return {
        "available": True,
        "reason": None,
        "truncated": 0,
        "generated_at": "x",
        "containers": [
            {
                "slug": slug,
                "name": slug,
                "kind": "addon",
                "state": "started",
                "cpu_percent": 1.0,
                "memory_percent": 2.0,
                "memory_usage": 3,
            }
            for slug in slugs
        ],
    }


async def test_history_bytes_written_per_hour_at_most_a_tenth(
    hass: HomeAssistant, freezer
) -> None:
    """Steady state (the ring is full), one sample a minute for an hour, 30 add-ons."""
    watchdog = _watchdog(hass, enabled=True)
    slugs = [f"a{i}" for i in range(ADDONS)]
    written: list[int] = []

    def _record(_path: str, payload: Any, **_kw: Any) -> None:
        written.append(len(json.dumps(payload)))

    with (
        patch("custom_components.ha_soc.resource_watchdog.sync_write_json_atomic", _record),
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(return_value=_overview(slugs)),
        ),
    ):
        # Fill the ring so every write is a full-size one.
        for _ in range(90):
            await watchdog.async_run_once()
            freezer.tick(timedelta(seconds=60))
        written.clear()
        # Before the change every sample wrote the whole ring.
        before = 0
        for _ in range(60):
            await watchdog.async_run_once()
            before += len(json.dumps({s: list(h) for s, h in watchdog._history.items()}))
            freezer.tick(timedelta(seconds=60))
    after = sum(written)
    print(f"OPT-3 history bytes per hour: before {before}, after {after} ({len(written)} writes)")
    assert after <= before / 10


async def test_history_is_written_when_the_entry_stops(hass: HomeAssistant) -> None:
    watchdog = _watchdog(hass, enabled=True)
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_container_resources",
        new=AsyncMock(return_value=_overview(["a0"])),
    ):
        await watchdog.async_run_once()
    path = hass.config.path("ha_soc", "watchdog_history.json")
    assert not os.path.exists(path)
    await watchdog.async_flush_history()
    with open(path, encoding="utf-8") as handle:
        assert len(json.load(handle)["a0"]) == 1


async def test_history_is_written_once_the_interval_has_passed(
    hass: HomeAssistant, freezer
) -> None:
    watchdog = _watchdog(hass, enabled=True)
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_container_resources",
        new=AsyncMock(return_value=_overview(["a0"])),
    ):
        await watchdog.async_run_once()
        assert watchdog.status()["history_last_write"] is None
        freezer.tick(timedelta(seconds=HISTORY_SAVE_INTERVAL_SECONDS))
        await watchdog.async_run_once()
    assert watchdog.status()["history_last_write"] is not None


async def test_history_of_uninstalled_add_ons_is_pruned(hass: HomeAssistant) -> None:
    watchdog = _watchdog(hass, enabled=True)
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_container_resources",
        new=AsyncMock(side_effect=[_overview(["gone", "kept"]), _overview(["kept"])]),
    ):
        await watchdog.async_run_once()
        assert set(watchdog._history) == {"gone", "kept"}
        await watchdog.async_run_once()
    assert set(watchdog._history) == {"kept"}
    assert "gone" not in watchdog.status()["containers"]
    await watchdog.async_flush_history()
    with open(hass.config.path("ha_soc", "watchdog_history.json"), encoding="utf-8") as handle:
        assert set(json.load(handle)) == {"kept"}


async def test_a_truncated_overview_does_not_prune(hass: HomeAssistant) -> None:
    """Add-ons past the sampling limit are missing from the overview but still installed."""
    watchdog = _watchdog(hass, enabled=True)
    truncated = {**_overview(["kept"]), "truncated": 4}
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_container_resources",
        new=AsyncMock(side_effect=[_overview(["kept", "beyond"]), truncated]),
    ):
        await watchdog.async_run_once()
        await watchdog.async_run_once()
    assert set(watchdog._history) == {"kept", "beyond"}


# --------------------------------------------------------------------------- OPT-2


async def _make_audit(hass: HomeAssistant, tmp_path: Any) -> AuditLog:
    store = HaSocData(hass)
    store.data = default_store_data()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    return audit


async def test_idle_flush_makes_no_directory_listing(hass: HomeAssistant, tmp_path: Any) -> None:
    audit = await _make_audit(hass, tmp_path)
    audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
    await audit._async_flush()

    listings: list[str] = []
    real_listdir, real_scandir = os.listdir, os.scandir

    def _listdir(*args: Any, **kwargs: Any):
        listings.append("listdir")
        return real_listdir(*args, **kwargs)

    def _scandir(*args: Any, **kwargs: Any):
        listings.append("scandir")
        return real_scandir(*args, **kwargs)

    jobs = AsyncMock()
    with (
        patch("os.listdir", _listdir),
        patch("os.scandir", _scandir),
        patch.object(audit.hass, "async_add_executor_job", jobs),
    ):
        for _ in range(10):
            await audit._async_flush()
    assert listings == []
    jobs.assert_not_called()


async def test_retention_runs_at_most_hourly(
    hass: HomeAssistant, tmp_path: Any, freezer
) -> None:
    audit = await _make_audit(hass, tmp_path)
    with patch.object(audit, "_sync_apply_retention", wraps=audit._sync_apply_retention) as spy:
        for _ in range(5):
            audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
            await audit._async_flush()
            freezer.tick(timedelta(seconds=30))
        assert spy.call_count == 1
        freezer.tick(timedelta(hours=1))
        audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
        await audit._async_flush()
        assert spy.call_count == 2


async def test_flush_finds_its_target_file_once_a_day(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    audit = await _make_audit(hass, tmp_path)
    with patch.object(
        audit, "_sync_find_target_day_file", wraps=audit._sync_find_target_day_file
    ) as spy:
        for _ in range(5):
            audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
            await audit._async_flush()
        assert spy.call_count == 1
    assert len(audit._sync_list_day_files()) == 1
    assert len(list(audit._read_jsonl(audit._sync_list_day_files()[0][1]))) == 5


async def test_target_file_cache_follows_the_audit_directory(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    audit = await _make_audit(hass, tmp_path)
    audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
    await audit._async_flush()
    audit._dir_path = str(tmp_path / "elsewhere")
    audit.async_log("service_call", user_id="u", domain="light", service="turn_on")
    await audit._async_flush()
    assert len(os.listdir(audit._dir_path)) >= 1
    assert any(name.startswith("audit-") for name in os.listdir(audit._dir_path))


def _write_integration(root: str, name: str, *, license_file: bool = False) -> str:
    path = os.path.join(root, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "manifest.json"), "w", encoding="utf-8") as handle:
        handle.write("{}")
    if license_file:
        with open(os.path.join(path, "LICENSE"), "w", encoding="utf-8") as handle:
            handle.write("x")
    return path


def _age(path: str, seconds: int = 3600) -> None:
    """Back-date a path, so the scan treats it as settled and caches it."""
    old = os.stat(path).st_mtime_ns - seconds * 1_000_000_000
    os.utime(path, ns=(old, old))


def _age_tree(root: str) -> None:
    for name in os.listdir(root):
        _age(os.path.join(root, name))
    _age(root)


def test_custom_components_scan_is_cached_by_mtime(tmp_path: Any) -> None:
    root = str(tmp_path / "custom_components")
    _write_integration(root, "alpha")
    _write_integration(root, "beta", license_file=True)
    _age_tree(root)
    isec._SCAN_CACHE.clear()

    first = isec._scan_custom_components_sync(root)
    assert first == (["alpha", "beta"], {"alpha": False, "beta": True})

    with patch.object(isec, "_license_present_sync") as probe:
        assert isec._scan_custom_components_sync(root) == first
        probe.assert_not_called()

    # A new integration changes the root's time.
    _write_integration(root, "gamma")
    _age_tree(root)
    assert isec._scan_custom_components_sync(root)[0] == ["alpha", "beta", "gamma"]

    # A license added inside an existing integration changes only that directory's time.
    with open(os.path.join(root, "alpha", "LICENSE"), "w", encoding="utf-8") as handle:
        handle.write("x")
    _age_tree(root)
    assert isec._scan_custom_components_sync(root)[1]["alpha"] is True

    # Removal.
    os.remove(os.path.join(root, "beta", "manifest.json"))
    _age_tree(root)
    assert isec._scan_custom_components_sync(root)[0] == ["alpha", "gamma"]


def test_custom_components_scan_does_not_cache_a_just_changed_directory(tmp_path: Any) -> None:
    """A change in the same clock tick as the scan could leave the time unchanged."""
    root = str(tmp_path / "custom_components")
    _write_integration(root, "alpha")
    isec._SCAN_CACHE.clear()
    isec._scan_custom_components_sync(root)
    assert root not in isec._SCAN_CACHE


def test_custom_components_scan_of_a_missing_directory(tmp_path: Any) -> None:
    root = str(tmp_path / "nope")
    isec._SCAN_CACHE[root] = ((0, ()), ["stale"], {"stale": True})
    assert isec._scan_custom_components_sync(root) == ([], {})
    assert root not in isec._SCAN_CACHE


# --------------------------------------------------------------------------- OPT-7


def _syslog_entries(count: int) -> list[dict[str, Any]]:
    return [
        {
            "ts": "2026-10-07T10:00:00+00:00",
            "host": "udm",
            "app": "kernel",
            "severity": 4,
            "message": f"line {i} " + "x" * 220,
        }
        for i in range(count)
    ]


async def _loaded_store(hass: HomeAssistant) -> HaSocData:
    store = HaSocData(hass)
    await store.async_load()
    return store


async def test_syslog_receive_does_not_grow_store_write_volume(
    hass: HomeAssistant, hass_storage: dict[str, Any], freezer
) -> None:
    store = await _loaded_store(hass)
    store.async_append_syslog_entries(_syslog_entries(2000))
    await store.async_save_now()
    main_before = hass_storage[STORAGE_KEY]
    main_bytes_with_ring = len(json.dumps({**store._main_payload(), "syslog_receiver_entries": store.data["syslog_receiver_entries"]}))
    main_bytes = len(json.dumps(store._main_payload()))
    print(f"OPT-7 main store bytes per save: before {main_bytes_with_ring}, after {main_bytes}")
    assert main_bytes * 10 < main_bytes_with_ring

    # An hour of syslog traffic, one batch a minute.
    for _ in range(60):
        store.async_append_syslog_entries(_syslog_entries(20))
        freezer.tick(timedelta(seconds=60))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert hass_storage[STORAGE_KEY] is main_before
    assert "syslog_receiver_entries" not in hass_storage[STORAGE_KEY]["data"]


async def test_syslog_ring_is_written_to_its_own_file_on_a_long_delay(
    hass: HomeAssistant, hass_storage: dict[str, Any], freezer
) -> None:
    store = await _loaded_store(hass)
    store.async_append_syslog_entries(_syslog_entries(5))
    freezer.tick(timedelta(seconds=SYSLOG_RING_SAVE_DELAY - 5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert SYSLOG_RING_KEY not in hass_storage
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert len(hass_storage[SYSLOG_RING_KEY]["data"]["entries"]) == 5


async def test_syslog_ring_survives_a_restart_and_flush_writes_it(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded_store(hass)
    store.async_append_syslog_entries(_syslog_entries(7))
    await store.async_flush()
    assert len(hass_storage[SYSLOG_RING_KEY]["data"]["entries"]) == 7

    restarted = await _loaded_store(hass)
    assert [e["message"][:6] for e in restarted.data["syslog_receiver_entries"]] == [
        f"line {i}" for i in range(7)
    ]
    # Nothing changed since, so a second flush does not write the ring again.
    written = hass_storage[SYSLOG_RING_KEY]
    await restarted.async_flush()
    assert hass_storage[SYSLOG_RING_KEY] is written


async def test_ring_left_in_the_old_store_is_moved_out(
    hass: HomeAssistant, hass_storage: dict[str, Any], freezer
) -> None:
    legacy = default_store_data()
    legacy["syslog_receiver_entries"] = _syslog_entries(3)
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 0,
        "key": STORAGE_KEY,
        "data": dict(legacy),
    }
    store = await _loaded_store(hass)
    assert len(store.data["syslog_receiver_entries"]) == 3

    freezer.tick(timedelta(seconds=SYSLOG_RING_SAVE_DELAY + 1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert "syslog_receiver_entries" not in hass_storage[STORAGE_KEY]["data"]
    assert len(hass_storage[SYSLOG_RING_KEY]["data"]["entries"]) == 3


async def test_main_store_save_still_carries_everything_else(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    store = await _loaded_store(hass)
    store.async_update_settings(audit_retention_days=12)
    store.async_append_syslog_entries(_syslog_entries(2))
    await store.async_save_now()
    saved = hass_storage[STORAGE_KEY]["data"]
    assert saved["settings"]["audit_retention_days"] == 12
    assert set(saved) == set(default_store_data()) - {"syslog_receiver_entries"}
    restarted = await _loaded_store(hass)
    assert restarted.data["settings"]["audit_retention_days"] == 12
