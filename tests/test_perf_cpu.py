"""Setup time, scan cost and audit query cost: the regression tests for the October audit's
optimisation findings OPT-4, OPT-5 and OPT-6.

The 70-entry fixture is tests/perf_env.py. The figures measured before the change are in
docs/decisions.md (2026-10-08, slice s12); the tests assert the bounds the change must keep,
which leave room for a loaded test machine.
"""
from __future__ import annotations

import asyncio
import os
import tracemalloc
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import homeassistant.util.dt as dt_util
from homeassistant import loader
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import scanner as scanner_mod
from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.scanner import IntegrationScanner
from custom_components.ha_soc.store import HaSocData

from .perf_env import (
    LoopLag,
    build_env,
    custom_domain,
    expose_custom_integrations,
    forget_custom_integrations,
    now,
    write_custom_integrations,
)

# Private config directory per test: the fixture writes 25 integrations into it.
ISOLATED_CONFIG_DIR = True

# Bounds the change must keep. The setup time is wall time with a wide margin (about 0.15 s
# measured); the 50 ms bound is the most CPU the loop thread spends in one callback.
SETUP_SECONDS_LIMIT = 1.0
STALL_SECONDS_LIMIT = 0.05


async def _install_fixture(hass) -> str:
    config_dir = hass.config.config_dir
    await build_env(hass, config_dir)
    expose_custom_integrations(hass, config_dir)
    # Only HA SOC's own setup is timed: its dependencies are loaded first.
    for dependency in ("http", "panel_custom", "websocket_api", "persistent_notification", "frontend"):
        await async_setup_component(hass, dependency, {})
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
    return config_dir


async def test_setup_time_and_loop_stall_on_70_entry_fixture(hass) -> None:
    """OPT-5 and OPT-6: setup returns in well under a second and no stall passes 50 ms,
    while the misconfiguration sweep and the first scan run in the background."""
    config_dir = await _install_fixture(hass)
    try:
        entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        entry.add_to_hass(hass)

        lag = LoopLag()
        lag.start()
        started = now()
        assert await hass.config_entries.async_setup(entry.entry_id)
        setup_seconds = now() - started
        await hass.async_block_till_done()
        sweep = getattr(entry.runtime_data.health, "_sweep_task", None)
        if sweep is not None:
            await asyncio.wait({sweep})
        stall = await lag.stop()
        print(
            f"PERF setup {setup_seconds * 1000:.0f} ms, longest event loop stall {stall * 1000:.0f} ms, "
            f"longest single callback {lag.max_callback * 1000:.0f} ms of CPU"
        )

        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        assert setup_seconds < SETUP_SECONDS_LIMIT
        assert lag.max_callback < STALL_SECONDS_LIMIT
    finally:
        forget_custom_integrations(config_dir)


async def test_health_start_does_not_wait_for_the_sweep(hass) -> None:
    """The sweep is a background task: async_start returns first, a caller during it shares
    its result, and stopping cancels it."""
    store = HaSocData(hass)
    await store.async_load()
    health = IntegrationHealth(hass, store)
    release = asyncio.Event()
    calls = 0

    async def slow_check(_self):
        nonlocal calls
        calls += 1
        await release.wait()
        return []

    with patch.object(IntegrationHealth, "_check_http_insecure", slow_check):
        await health.async_start()
        try:
            # Setup is over and the sweep has been started but has not finished.
            assert health._sweep_task is not None and not health._sweep_task.done()
            assert health.misconfig_sweep_ran is False
            waiter = asyncio.ensure_future(health.async_run_misconfig_checks())
            await asyncio.sleep(0)
            release.set()
            await waiter
            await health._sweep_task
            assert calls == 1, "a second caller shared the running sweep instead of starting another"
            assert health.misconfig_sweep_ran is True
        finally:
            release.set()
            await health.async_stop()


async def test_health_stop_cancels_a_running_sweep(hass) -> None:
    store = HaSocData(hass)
    await store.async_load()
    health = IntegrationHealth(hass, store)
    started = asyncio.Event()

    async def hang(_self):
        started.set()
        await asyncio.Event().wait()

    with patch.object(IntegrationHealth, "_check_http_insecure", hang):
        await health.async_start()
        task = health._sweep_task
        try:
            await asyncio.wait_for(started.wait(), 2)
        finally:
            await health.async_stop()
        await asyncio.wait({task})
        assert task.cancelled()
    assert health._sweep_task is None


async def test_attribution_maps_load_manifests_in_one_gathered_call(hass) -> None:
    """OPT-5: one async_get_integrations call for all the domains, not one await per domain."""
    for domain in ("cust00", "cust01", "cust02"):
        MockConfigEntry(domain=domain, data={}).add_to_hass(hass)
    store = HaSocData(hass)
    await store.async_load()
    health = IntegrationHealth(hass, store)
    with patch(
        "custom_components.ha_soc.health.async_get_integrations", AsyncMock(return_value={})
    ) as gathered:
        await health._async_refresh_attribution_maps()
    assert gathered.await_count == 1
    assert set(gathered.await_args.args[1]) == {"cust00", "cust01", "cust02"}


async def _scanner_with_entries(hass, domains):
    for domain in domains:
        MockConfigEntry(domain=domain, data={}).add_to_hass(hass)
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationScanner(hass, store), store


async def test_scanner_second_run_does_no_ast_work(hass) -> None:
    """OPT-6: a file whose modification time and size are unchanged is not parsed again."""
    config_dir = hass.config.config_dir
    write_custom_integrations(config_dir)
    expose_custom_integrations(hass, config_dir)
    try:
        domains = [custom_domain(i) for i in range(5)]
        scanner, _store = await _scanner_with_entries(hass, domains)
        real_parse = scanner_mod.ast.parse
        with patch.object(scanner_mod.ast, "parse", side_effect=real_parse) as parse:
            first = await scanner.async_scan_all()
            first_parses = parse.call_count
            parse.reset_mock()
            second = await scanner.async_scan_all()
            second_parses = parse.call_count
        print(f"PERF scan of 5 custom integrations: {first_parses} parses first run, {second_parses} second")
        assert first_parses == 5 * 15
        assert second_parses == 0
        assert second == first

        # A rewritten file is read again, and only that one.
        target = Path(config_dir) / "custom_components" / domains[0] / "mod3.py"
        target.write_text(target.read_text(encoding="utf-8") + "\nx = 1\n", encoding="utf-8")
        with patch.object(scanner_mod.ast, "parse", side_effect=real_parse) as parse:
            await scanner.async_scan_all()
        assert parse.call_count == 1
    finally:
        forget_custom_integrations(config_dir)


async def test_scanner_cache_keeps_findings_and_forgets_removed_files(hass) -> None:
    config_dir = hass.config.config_dir
    write_custom_integrations(config_dir)
    expose_custom_integrations(hass, config_dir)
    try:
        domain = custom_domain(0)
        scanner, store = await _scanner_with_entries(hass, [domain])
        bad = Path(config_dir) / "custom_components" / domain / "bad.py"
        bad.write_text("import requests\nrequests.get('https://x', verify=False)\n", encoding="utf-8")
        first = await scanner.async_scan_integration(domain)
        assert any(f["file"] == "bad.py" for f in first)
        second = await scanner.async_scan_integration(domain)
        assert [f["id"] for f in second] == [f["id"] for f in first]
        assert "bad.py" in scanner._scan_cache[domain]

        bad.unlink()
        await scanner.async_scan_integration(domain)
        assert "bad.py" not in scanner._scan_cache[domain]
        assert all(
            f["status"] == "resolved"
            for f in store.data["scanner_findings"].values()
            if f["file"] == "bad.py"
        )
    finally:
        forget_custom_integrations(config_dir)


async def test_scanner_skips_built_in_integrations(hass) -> None:
    """OPT-6: an integration shipped with Core is neither read nor listed, and findings an
    older version stored for it are resolved."""
    scanner, store = await _scanner_with_entries(hass, ["abode"])
    store.async_upsert_finding(
        "scanner_findings", "abode:old",
        {"id": "abode:old", "domain": "abode", "file": "x.py", "line": 1, "snippet": "",
         "pattern": "eval_exec_use", "cwe": "CWE-95", "confidence": "high", "severity": "high",
         "first_seen": "t", "last_seen": "t", "status": "new"},
    )
    with patch.object(scanner_mod, "_plan_scan") as plan:
        results = await scanner.async_scan_all()
        assert await scanner.async_scan_integration("abode") == []
    plan.assert_not_called()
    assert results == {"abode": []}
    old = store.data["scanner_findings"]["abode:old"]
    assert old["status"] == "resolved"
    assert old["resolved_reason"] == "built_in_not_scanned"
    assert "abode" not in store.data.get("scanner_coverage", {})


async def test_scan_of_25_custom_integrations_never_stalls_the_loop(hass) -> None:
    """OPT-6: the 25 custom integrations (375 modules) are scanned with no stall past 50 ms."""
    config_dir = hass.config.config_dir
    write_custom_integrations(config_dir)
    expose_custom_integrations(hass, config_dir)
    try:
        scanner, _store = await _scanner_with_entries(hass, [custom_domain(i) for i in range(25)])
        lag = LoopLag()
        lag.start()
        started = now()
        await scanner.async_scan_all()
        seconds = now() - started
        stall = await lag.stop()
        print(
            f"PERF scan of 25 custom integrations: {seconds:.2f} s, longest stall {stall * 1000:.0f} ms, "
            f"longest single callback {lag.max_callback * 1000:.0f} ms of CPU"
        )
        assert lag.max_callback < STALL_SECONDS_LIMIT
    finally:
        forget_custom_integrations(config_dir)


RECORDS_PER_DAY = 20000
DAYS = 7
PEAK_MEMORY_LIMIT = 30 * 1024 * 1024


async def _audit_log(hass, tmp_path) -> AuditLog:
    store = HaSocData(hass)
    await store.async_load()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    audit._head_loaded = True
    os.makedirs(audit._dir_path)
    return audit


async def _audit_with_history(
    hass, tmp_path, days: int = DAYS, per_day: int = RECORDS_PER_DAY
) -> AuditLog:
    audit = await _audit_log(hass, tmp_path)
    base = dt_util.utcnow()
    for day in range(days, 0, -1):
        when = base - timedelta(days=day - 1, minutes=1)
        with patch("custom_components.ha_soc.audit.dt_util.utcnow", return_value=when):
            for i in range(per_day):
                audit.async_log(
                    "service_call", user_id="u1", domain="light", service="turn_on",
                    entity_ids=[f"light.x{i % 50}"],
                    detail={"entity_id": [f"light.x{i % 50}"], "brightness_pct": 40},
                )
            await audit._async_flush()
    return audit


async def test_audit_query_over_140000_records_is_cheap(hass, tmp_path) -> None:
    """OPT-4: the 200 newest rows of 140,000 records over 7 days with peak memory under 30 MB,
    and with no flush and no retention pass."""
    audit = await _audit_with_history(hass, tmp_path)
    total = DAYS * RECORDS_PER_DAY
    assert audit._seq == total

    with patch.object(AuditLog, "_async_flush", AsyncMock()) as flush, patch.object(
        AuditLog, "_sync_apply_retention"
    ) as retention:
        tracemalloc.start()
        try:
            started = now()
            rows = await audit.async_query(limit=200)
            seconds = now() - started
            _current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
    print(f"PERF audit query limit=200 of {total} records: {seconds:.2f} s, peak {peak / 1e6:.1f} MB")
    assert len(rows) == 200
    assert [r["seq"] for r in rows] == list(range(total, total - 200, -1))
    assert peak < PEAK_MEMORY_LIMIT
    flush.assert_not_called()
    retention.assert_not_called()


async def test_audit_query_filters_scan_back_far_enough(hass, tmp_path) -> None:
    audit = await _audit_with_history(hass, tmp_path, days=3, per_day=500)
    audit.async_log("login_failed", user_id="u2", ip="10.0.0.9")
    audit.async_log("login_failed", user_id="u3", ip="10.0.0.9")
    audit.async_log("login_ok", user_id="u2", ip="10.0.0.8")
    rows = await audit.async_query(category="login_failed", limit=10)
    assert [r["user_id"] for r in rows] == ["u3", "u2"]
    # A filter that matches only the oldest records is found across day files.
    only_old = await audit.async_query(user_id="u1", ip=None, limit=3)
    assert len(only_old) == 3
    assert only_old[0]["seq"] > only_old[1]["seq"] > only_old[2]["seq"]


async def test_audit_query_sees_unflushed_records_without_writing(hass, tmp_path) -> None:
    audit = await _audit_log(hass, tmp_path)
    audit.async_log("service_call", user_id="a", domain="light", service="on", entity_ids=[])
    await audit._async_flush()
    audit.async_log("service_call", user_id="b", domain="light", service="off", entity_ids=[])
    audit.async_log("service_call", user_id="c", domain="light", service="off", entity_ids=[])

    def disk_bytes() -> int:
        return sum(os.path.getsize(os.path.join(audit._dir_path, n)) for n in os.listdir(audit._dir_path))

    before = disk_bytes()
    rows = await audit.async_query()
    assert [r["user_id"] for r in rows] == ["c", "b", "a"]
    assert [r["seq"] for r in rows] == [3, 2, 1]
    assert disk_bytes() == before

    # Once written, the same records are returned once each.
    await audit._async_flush()
    rows = await audit.async_query()
    assert [r["seq"] for r in rows] == [3, 2, 1]
    assert (await audit.async_verify_chain())["ok"] is True


async def test_audit_reverse_reader_handles_block_edges(tmp_path) -> None:
    path = tmp_path / "f.jsonl"
    lines = [('{"seq": %d, "pad": "%s"}' % (i, "é" * (i % 7))).encode() for i in range(1, 4000)]
    path.write_bytes(b"\n".join(lines) + b"\n\n")
    with patch("custom_components.ha_soc.audit._REVERSE_READ_BLOCK", 97):
        got = list(AuditLog._read_jsonl_reversed(str(path)))
    assert got == list(reversed(lines))
    assert list(AuditLog._read_jsonl_reversed(str(tmp_path / "missing"))) == []
