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

from custom_components.ha_soc.atomic_json import sync_write_json_atomic
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
            "/host/info": {"boot_timestamp": 1_758_558_888_000_000},
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
    msg = {"id": 3, "id": "crash-nope", "file": "summary.json"}
    ws_crash_forensics_bundle(hass, connection, msg)
    await hass.async_block_till_done(wait_background_tasks=True)
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "not_found"
