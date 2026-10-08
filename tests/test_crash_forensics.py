"""Tests for crash_forensics.py: unclean-stop detection, bundle collection
against a faked Supervisor, classification, suspect ranking, retention,
size cap, and the WS surface's tier gates and file whitelist.
"""
import os
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import homeassistant.helpers.issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc.atomic_json import sync_read_json, sync_write_json_atomic
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.crash_forensics import (
    BUNDLE_ID_RE,
    CrashForensics,
    classify_journal_tail,
    _rank_suspects,
)
from custom_components.ha_soc.websocket_api import (
    ws_crash_forensics_bundle,
    ws_crash_forensics_collect_now,
    ws_crash_forensics_status,
)

# Private config directory per test; see tests/conftest.py. These tests read back
# the state files they write, which other xdist workers overwrite in the shared one.
ISOLATED_CONFIG_DIR = True

CLEAN_TAIL = "Sep 22 15:31:40 home systemd[1]: Stopping ...\nSep 22 15:31:44 home systemd[1]: Reached target Reboot.\n"
PANIC_TAIL = "Sep 22 15:31:40 home kernel: Kernel panic - not syncing: VFS\n"
SILENT_TAIL = "Sep 22 15:31:40 home homeassistant[1]: some ordinary line\n"


@pytest.fixture(autouse=True)
def _clean_ha_soc_dir(hass: HomeAssistant):
    """hass.config.path resolves to a fixed, non-per-test directory in this
    harness (not a fresh tmp_path), so bundles written by one test are
    still on disk for the next one unless cleared here. This matters for
    this module specifically: the retention test intentionally litters
    fake bundle directories."""
    path = hass.config.path("ha_soc")
    shutil.rmtree(path, ignore_errors=True)
    yield
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
async def entry(hass: HomeAssistant, _clean_ha_soc_dir) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _connection(owner: bool = True):
    connection = MagicMock()
    connection.user = MagicMock(id="user1", is_owner=owner, is_admin=True)
    return connection


class _FakeHassio:
    """Stands in for hass.data[DATA_COMPONENT], same boundary tests/test_logs_container.py fakes."""

    def __init__(self, responses: dict[str, object]):
        self.responses = responses
        self.calls: list[str] = []

    async def send_command(self, path, method="get", return_text=False, timeout=None, params=None):
        self.calls.append(path)
        for prefix, value in self.responses.items():
            if path.startswith(prefix):
                if isinstance(value, Exception):
                    raise value
                return value
        return "" if return_text else {}


def _install_fake_supervisor(hass: HomeAssistant, responses: dict[str, object]) -> _FakeHassio:
    from homeassistant.components.hassio.const import DATA_COMPONENT

    hass.config.components.add("hassio")
    fake = _FakeHassio(responses)
    hass.data[DATA_COMPONENT] = fake
    return fake


# -- classification -----------------------------------------------------


@pytest.mark.parametrize(
    "tail,expected",
    [
        (CLEAN_TAIL, "clean_reboot"),
        (PANIC_TAIL, "kernel_fault"),
        (SILENT_TAIL, "silent_stop"),
    ],
)
def test_classify_journal_tail(tail, expected):
    assert classify_journal_tail(tail) == expected


# -- suspect ranking (pure function, synthetic inputs) -------------------


def test_rank_suspects_from_core_log_and_watchdog_history():
    core_text = (
        "2026-09-22 15:30:00 WARNING [custom_components.ha_soc.probe] polling\n"
        "2026-09-22 15:30:05 INFO [homeassistant.components.unifi] update\n"
    )
    watchdog_history = {
        "music_assistant": [
            {"ts": "2026-09-22T15:20:00+00:00", "cpu_percent": 40, "memory_percent": 60},
            {"ts": "2026-09-22T15:25:00+00:00", "cpu_percent": 90, "memory_percent": 95},
        ]
    }
    from homeassistant.util import dt as dt_util

    suspects = _rank_suspects(
        gap_seconds=1200,
        classification="silent_stop",
        containers=[{"name": "ma", "exit_code": 137, "oom_killed": True}],
        watchdog_history=watchdog_history,
        heartbeat_ts=dt_util.parse_datetime("2026-09-22T15:31:00+00:00"),
        core_text=core_text,
        kernel_text="Sep 22 kernel: traps: chromium[123] trap invalid opcode\nSep 22 kernel: Bluetooth: hci0: Opcode failed\n",
    )
    kinds = [s["kind"] for s in suspects]
    assert "unclean_stop_window" in kinds
    assert "journal_classification" in kinds
    assert "container_exit" in kinds
    assert any(k.startswith("resource_trend") for k in kinds)
    assert "last_logger" in kinds
    assert "noise" in kinds
    # chromium/hci0 lines are noise, not named coredump suspects.
    assert "coredump" not in kinds
    # ranks are 1..N with no gaps
    assert [s["rank"] for s in suspects] == list(range(1, len(suspects) + 1))


def test_rank_suspects_names_a_non_chromium_coredump():
    suspects = _rank_suspects(
        gap_seconds=None,
        classification="silent_stop",
        containers=None,
        watchdog_history=None,
        heartbeat_ts=None,
        core_text="",
        kernel_text="Sep 22 kernel: systemd-coredump[99]: Process 55 (python3) dumped core\n",
    )
    coredumps = [s for s in suspects if s["kind"] == "coredump"]
    assert coredumps and "python3" in coredumps[0]["subject"]


# -- unclean vs clean detection ------------------------------------------


async def test_unclean_detected_when_heartbeat_newer_than_stop(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    await hass.async_add_executor_job(
        sync_write_json_atomic,
        cf._heartbeat_path,
        {"ts": "2026-09-22T15:31:00+00:00", "boot_id": "b1", "core_started": "x"},
    )
    if os.path.exists(cf._last_stop_path):
        await hass.async_add_executor_job(os.remove, cf._last_stop_path)

    with patch.object(cf, "async_collect_bundle", new=AsyncMock(return_value={"suspects": []})):
        result = await cf.async_check_and_collect()
    assert result["unclean"] is True


async def test_heartbeat_from_this_run_is_not_evidence(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A heartbeat carrying this run's own boot_id was written by this run,
    so it says nothing about the previous one, even when it is newer than
    the stop marker."""
    cf: CrashForensics = entry.runtime_data.crash_forensics
    await hass.async_add_executor_job(
        sync_write_json_atomic, cf._last_stop_path,
        {"ts": "2026-09-27T19:41:58+00:00", "reason": "clean"},
    )
    await hass.async_add_executor_job(
        sync_write_json_atomic, cf._heartbeat_path,
        {"ts": "2026-09-27T19:43:30+00:00", "boot_id": cf._boot_id, "core_started": "x"},
    )
    with patch.object(cf, "async_collect_bundle", new=AsyncMock()) as collect:
        result = await cf.async_check_and_collect()
    assert result["unclean"] is False
    collect.assert_not_called()


async def test_prior_state_is_read_before_the_first_heartbeat(
    hass: HomeAssistant, _clean_ha_soc_dir
) -> None:
    """Setup snapshots the previous run's files before overwriting the
    heartbeat, and the startup check uses that snapshot."""
    ha_soc_dir = hass.config.path("ha_soc")
    os.makedirs(ha_soc_dir, exist_ok=True)
    await hass.async_add_executor_job(
        sync_write_json_atomic, os.path.join(ha_soc_dir, "heartbeat.json"),
        {"ts": "2026-09-27T19:43:30+00:00", "boot_id": "previous-run", "core_started": "x"},
    )
    await hass.async_add_executor_job(
        sync_write_json_atomic, os.path.join(ha_soc_dir, "last_stop.json"),
        {"ts": "2026-09-27T19:41:58+00:00", "reason": "clean"},
    )
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    cf: CrashForensics = config_entry.runtime_data.crash_forensics
    assert cf._prior_state is not None
    prior_heartbeat, prior_stop = cf._prior_state
    assert prior_heartbeat["boot_id"] == "previous-run"
    assert prior_stop["reason"] == "clean"
    on_disk = await hass.async_add_executor_job(
        sync_read_json, os.path.join(ha_soc_dir, "heartbeat.json")
    )
    assert on_disk["boot_id"] == cf._boot_id

    with patch.object(cf, "async_collect_bundle", new=AsyncMock()) as collect:
        result = await cf.async_check_and_collect(prior=cf._prior_state)
    assert result["unclean"] is True  # the previous run's heartbeat outlived its stop marker
    collect.assert_called_once()


async def test_clean_detected_when_stop_newer_than_heartbeat(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    await hass.async_add_executor_job(
        sync_write_json_atomic, cf._heartbeat_path,
        {"ts": "2026-09-22T15:00:00+00:00", "boot_id": "b1", "core_started": "x"},
    )
    await hass.async_add_executor_job(
        sync_write_json_atomic, cf._last_stop_path, {"ts": "2026-09-22T15:05:00+00:00", "reason": "clean"},
    )
    with patch.object(cf, "async_collect_bundle", new=AsyncMock()) as collect:
        result = await cf.async_check_and_collect()
    assert result["unclean"] is False
    collect.assert_not_called()


# -- collection against a faked Supervisor --------------------------------


async def test_collect_bundle_writes_files_and_raises_repair(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    _install_fake_supervisor(
        hass,
        {
            "/host/logs/identifiers": {"identifiers": ["homeassistant", "hassio_supervisor", "kernel"]},
            "/host/logs/boots/-1/identifiers/kernel": SILENT_TAIL,
            "/host/logs/boots/-1/identifiers/hassio_supervisor": "",
            "/host/logs/boots/-1/identifiers/homeassistant": "core log line\n",
            "/host/logs/boots/-1": SILENT_TAIL,
            # 2026-09-22T15:54:48Z, the host boot after the 15:31 heartbeat.
            "/host/info": {"boot_timestamp": 1_790_092_488_000_000},
            "/resolution/info": {},
            "/supervisor/info": {},
            "/os/info": {},
        },
    )
    with patch(
        "custom_components.ha_soc.containers.async_container_resources",
        new=AsyncMock(return_value={"available": False, "containers": []}),
    ):
        summary = await cf.async_collect_bundle({"ts": "2026-09-22T15:31:00+00:00"}, boot="-1")

    bundle_dir = os.path.join(cf._config_dir, summary["bundle_id"])
    assert os.path.isdir(bundle_dir)
    assert os.path.isfile(os.path.join(bundle_dir, "summary.json"))
    assert os.path.isfile(os.path.join(bundle_dir, "core.txt"))
    assert summary["classification"] == "silent_stop"

    registry = ir.async_get(hass)
    issue_id = f"unclean_stop_{summary['bundle_id'].removeprefix('crash-')}"
    assert (DOMAIN, issue_id) in registry.issues


async def test_core_restart_when_the_host_did_not_reboot(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """boot_timestamp earlier than the heartbeat: the host never rebooted,
    so the event is a Core restart and the journal comes from boots/0."""
    cf: CrashForensics = entry.runtime_data.crash_forensics
    # 2026-09-27T19:29:16Z, 854 s before the 19:43:30Z heartbeat.
    boot_timestamp_us = 1_790_537_356_000_000
    fake = _install_fake_supervisor(
        hass,
        {
            "/host/logs/identifiers": {"identifiers": ["homeassistant", "hassio_supervisor", "kernel"]},
            "/host/logs/boots/0": CLEAN_TAIL,
            "/host/logs/boots/-1": PANIC_TAIL,
            "/host/info": {"boot_timestamp": boot_timestamp_us},
        },
    )
    with patch(
        "custom_components.ha_soc.containers.async_container_resources",
        new=AsyncMock(return_value={"available": False, "containers": []}),
    ):
        summary = await cf.async_collect_bundle(
            {"ts": "2026-09-27T19:43:30+00:00", "boot_id": "previous-run"}, boot="-1"
        )
    assert summary["gap_seconds"] < 0
    assert summary["classification"] == "core_restart"
    assert summary["journal_boot"] == "0"
    assert any(c.startswith("/host/logs/boots/0") for c in fake.calls)
    assert not any(c.startswith("/host/logs/boots/-1") for c in fake.calls)
    window = summary["suspects"][0]
    assert window["kind"] == "unclean_stop_window" and window["subject"] == "core"
    assert "did not reboot" in window["evidence"]


async def test_supervisor_failures_are_recorded_not_raised(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    _install_fake_supervisor(hass, {"/host/logs": OSError("Supervisor unreachable")})
    with patch(
        "custom_components.ha_soc.containers.async_container_resources",
        new=AsyncMock(return_value={"available": False, "containers": []}),
    ):
        summary = await cf.async_collect_bundle({"ts": "2026-09-22T15:31:00+00:00"}, boot="-1")
    assert summary["errors"]  # something failed and was recorded, not raised


# -- retention and size cap ------------------------------------------------


async def test_retention_deletes_the_oldest_beyond_ten(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    os.makedirs(cf._config_dir, exist_ok=True)
    for i in range(11):
        os.makedirs(os.path.join(cf._config_dir, f"crash-2026092{i:02d}T000000Z"), exist_ok=True)
    await hass.async_add_executor_job(cf._sync_enforce_retention)
    remaining = sorted(n for n in os.listdir(cf._config_dir) if n.startswith("crash-"))
    assert len(remaining) == 10
    assert "crash-2026092000T000000Z" not in remaining


def test_bundle_write_caps_total_size(hass: HomeAssistant, entry: MockConfigEntry, tmp_path):
    cf: CrashForensics = entry.runtime_data.crash_forensics
    big = "x" * (30 * 1024 * 1024)
    bundle_dir = os.path.join(cf._config_dir, "crash-cap-test")
    cf._sync_write_bundle(bundle_dir, {"host-journal-prev-boot.txt": big, "summary.json": {"a": 1}})
    total = sum(
        os.path.getsize(os.path.join(bundle_dir, f))
        for f in os.listdir(bundle_dir)
    )
    from custom_components.ha_soc.crash_forensics import MAX_BUNDLE_BYTES

    assert total <= MAX_BUNDLE_BYTES


# -- bundle id / file whitelist --------------------------------------------


def test_bundle_id_pattern_rejects_traversal():
    assert BUNDLE_ID_RE.match("crash-20260922T153100Z")
    assert not BUNDLE_ID_RE.match("../../etc/passwd")
    assert not BUNDLE_ID_RE.match("crash-../evil")


def test_sync_read_bundle_file_rejects_bad_id_and_unknown_file(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    assert cf.sync_read_bundle_file("../etc/passwd", "summary.json") is None
    assert cf.sync_read_bundle_file("crash-20260922T153100Z", "../../etc/passwd") is None
    assert cf.sync_read_bundle_file("crash-20260922T153100Z", "not-a-real-file.txt") is None


# -- WS tier gates -----------------------------------------------------------


def test_ws_status_requires_soc_access(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = MagicMock()
    connection.user = MagicMock(id="user1", is_owner=False, is_admin=False)
    with pytest.raises(Unauthorized):
        ws_crash_forensics_status(hass, connection, {"id": 1})


def test_ws_collect_now_is_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = MagicMock()
    connection.user = MagicMock(id="user1", is_owner=False, is_admin=True)
    with pytest.raises(Unauthorized):
        ws_crash_forensics_collect_now(hass, connection, {"id": 1})


async def test_ws_bundle_returns_not_found_for_unknown_bundle(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection(owner=True)
    msg = {"id": 3, "bundle_id": "crash-nope", "file": "summary.json"}
    ws_crash_forensics_bundle(hass, connection, msg)
    await hass.async_block_till_done(wait_background_tasks=True)
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "not_found"


async def test_ws_bundle_returns_file_content(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The happy path, addressed by bundle_id (never "id", which the
    protocol reserves for the integer message id)."""
    cf: CrashForensics = entry.runtime_data.crash_forensics
    bundle_id = "crash-2026-09-27T194330.320249Z0000"
    await hass.async_add_executor_job(
        cf._sync_write_bundle, os.path.join(cf._config_dir, bundle_id), {"summary.json": {"a": 1}}
    )
    connection = _connection(owner=True)
    ws_crash_forensics_bundle(
        hass, connection, {"id": 4, "bundle_id": bundle_id, "file": "summary.json"}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    connection.send_error.assert_not_called()
    connection.send_result.assert_called_once()
    assert connection.send_result.call_args[0][0] == 4
    assert '"a": 1' in connection.send_result.call_args[0][1]["content"]


async def test_ws_status_lists_bundles(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    cf: CrashForensics = entry.runtime_data.crash_forensics
    bundle_id = "crash-2026-09-27T194330.320249Z0000"
    await hass.async_add_executor_job(
        cf._sync_write_bundle,
        os.path.join(cf._config_dir, bundle_id),
        {"summary.json": {"classification": "core_restart", "gap_seconds": -854.0, "suspects": []}},
    )
    connection = _connection(owner=True)
    ws_crash_forensics_status(hass, connection, {"id": 5})
    await hass.async_block_till_done(wait_background_tasks=True)
    connection.send_result.assert_called_once()
    status = connection.send_result.call_args[0][1]
    assert status["bundles"][0]["id"] == bundle_id
    assert status["bundles"][0]["classification"] == "core_restart"


async def test_heartbeat_tick_during_shutdown_still_classifies_as_clean(
    hass: HomeAssistant, entry: MockConfigEntry, freezer
) -> None:
    """Timers are not cancelled on the stop event, so a heartbeat tick can
    arrive after the clean-stop marker. It must not be written, or the next
    boot sees a heartbeat newer than the marker and calls the stop unclean."""
    from datetime import timedelta

    run1: CrashForensics = entry.runtime_data.crash_forensics
    await run1._async_write_heartbeat()
    freezer.tick(timedelta(seconds=300))
    await run1._async_on_stop(None)
    stop_marker = await hass.async_add_executor_job(sync_read_json, run1._last_stop_path)
    heartbeat_before = await hass.async_add_executor_job(sync_read_json, run1._heartbeat_path)

    freezer.tick(timedelta(seconds=12))
    await run1._async_write_heartbeat()
    heartbeat_after = await hass.async_add_executor_job(sync_read_json, run1._heartbeat_path)
    assert heartbeat_after == heartbeat_before
    assert heartbeat_after["ts"] < stop_marker["ts"]

    run2 = CrashForensics(hass, run1.store, MagicMock(), MagicMock())
    prior = await hass.async_add_executor_job(run2._sync_read_prior_state)
    with patch.object(run2, "async_collect_bundle", new=AsyncMock()) as collect:
        result = await run2.async_check_and_collect(prior=prior)
    assert result["unclean"] is False
    collect.assert_not_called()


async def test_heartbeat_in_flight_when_stop_arrives_is_ordered_before_the_marker(
    hass: HomeAssistant, entry: MockConfigEntry, freezer
) -> None:
    """A heartbeat write already running in the executor when the stop event
    fires must finish before the marker is written."""
    import asyncio
    import threading
    from datetime import timedelta

    run1: CrashForensics = entry.runtime_data.crash_forensics
    started = threading.Event()
    release = threading.Event()
    real_write = run1._sync_write_heartbeat

    def slow_write() -> None:
        started.set()
        release.wait(5)
        real_write()

    with patch.object(run1, "_sync_write_heartbeat", slow_write):
        beat = hass.async_create_task(run1._async_write_heartbeat())
        await hass.async_add_executor_job(started.wait, 5)
        freezer.tick(timedelta(seconds=5))
        stop = hass.async_create_task(run1._async_on_stop(None))
        await asyncio.sleep(0)
        release.set()
        await asyncio.gather(beat, stop)

    heartbeat = await hass.async_add_executor_job(sync_read_json, run1._heartbeat_path)
    marker = await hass.async_add_executor_job(sync_read_json, run1._last_stop_path)
    assert heartbeat["ts"] <= marker["ts"]
