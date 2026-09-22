"""Crash forensics: notice a silent host/Core stop and collect the evidence
for it before the next boot's coredump churn rotates it out of the journal.

Background (see docs/CRASH-FORENSICS.md and the 2026-09-22 report in
~/workspace/ha-crash-2026-09-22 that this module implements section 3(b)
of): under Supervisor there is no /config/home-assistant.log (Core logs to
stdout -> Docker -> the host journal only), and home-assistant.log.fault
only gets content on a fatal *signal* in Core (SIGSEGV/SIGFPE/SIGABRT/
SIGBUS/SIGILL) -- it stays empty for an OOM kill, a host hang, or a power
cut, which is the failure mode this module targets. There is nothing on
the box that flags "the host just came back from an unplanned stop", so
this module builds that signal itself with a heartbeat file plus a
clean-stop marker, and uses the Supervisor's previous-boot journal
(GET /host/logs/boots/-1) to look at what happened before the gap.

Design choice: a heartbeat FILE rather than the Supervisor's own boot/
health flags (/resolution/info's `unhealthy`/`unsupported`, /host/info's
`boot_timestamp`). Those describe the CURRENT boot's state, not whether the
PREVIOUS boot ended cleanly -- there is no Supervisor-exposed "last boot
was unclean" flag to read (see docs/decisions.md, 2026-09-22). A file that
Core itself touches on a schedule, and only removes/replaces cleanly, is
the one thing this integration controls end to end.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
from datetime import timedelta
from typing import Any
from uuid import uuid4

import homeassistant.helpers.issue_registry as ir
import homeassistant.util.dt as dt_util
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .atomic_json import sync_read_json, sync_write_json_atomic
from .const import DOMAIN
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

SUBDIR = "ha_soc"
HEARTBEAT_FILENAME = "heartbeat.json"
LAST_STOP_FILENAME = "last_stop.json"
BUNDLE_PREFIX = "crash-"
BUNDLE_ID_RE = re.compile(r"^crash-[0-9TZ:+.-]+$")

MAX_BUNDLES = 10
MAX_BUNDLE_BYTES = 25 * 1024 * 1024
MAX_FILE_READ_BYTES = 4 * 1024 * 1024

SUPERVISOR_TIMEOUT = 30
JOURNAL_LINES = 5000
IDENTIFIER_LINES = 3000

# Best-guess identifier names; confirmed at collection time against
# /host/logs/identifiers and recorded in summary.json under
# "identifiers_used" (see the module docstring in logs.py:57-60 for the
# sibling log-fetch path this borrows the transport from). UNVERIFIED on
# HAOS 18.1+: the exact SYSLOG_IDENTIFIER Core's container uses.
GUESS_IDENTIFIERS = {
    "core": "homeassistant",
    "supervisor": "hassio_supervisor",
    "kernel": "kernel",
}

BUNDLE_FILES = (
    "host-journal-prev-boot.txt",
    "kernel.txt",
    "supervisor.txt",
    "core.txt",
    "host-info.json",
    "resolution-info.json",
    "supervisor-info.json",
    "os-info.json",
    "containers.json",
    "fault-log.txt",
    "watchdog-history.json",
    "summary.json",
)

_SHUTDOWN_MARKERS = ("Stopping", "Reached target Reboot", "Power-Off")
_PANIC_MARKERS = ("Kernel panic", "BUG:", "Hardware Error", "mce:")
_LOGGER_LINE_RE = re.compile(
    r"\[(?P<logger>(?:homeassistant|custom_components)[\w.]*)\]"
)
_TIMESTAMP_PREFIX_RE = re.compile(r"^(\S+ \S+)")
_EXIT_CODE_OOM = {137, 139, 134, 132}


def _iso_now() -> str:
    return dt_util.utcnow().isoformat()


def _parse(ts: str | None):
    if not ts:
        return None
    return dt_util.parse_datetime(ts)


def classify_journal_tail(text: str) -> str:
    """clean_reboot / kernel_fault / silent_stop, per the taxonomy in
    section 1 of the crash-forensics report (cases 7 vs 8 vs a normal
    reboot)."""
    for line in reversed(text.splitlines()[-200:]):
        if any(marker in line for marker in _PANIC_MARKERS):
            return "kernel_fault"
    for marker in _SHUTDOWN_MARKERS:
        if marker in text:
            return "clean_reboot"
    return "silent_stop"


def _last_loggers(core_text: str, limit: int = 5) -> list[dict[str, str]]:
    """Last distinct loggers to log before silence, oldest kept first is
    not what we want here: walk from the end, keep first-seen (most
    recent) per logger name."""
    seen: dict[str, str] = {}
    for line in reversed(core_text.splitlines()):
        match = _LOGGER_LINE_RE.search(line)
        if not match:
            continue
        logger_name = match.group("logger")
        if logger_name in seen:
            continue
        ts_match = _TIMESTAMP_PREFIX_RE.match(line)
        seen[logger_name] = ts_match.group(1) if ts_match else ""
        if len(seen) >= limit:
            break
    return [{"logger": name, "ts": ts} for name, ts in seen.items()]


def _rank_suspects(
    *,
    gap_seconds: float | None,
    classification: str,
    containers: list[dict[str, Any]] | None,
    watchdog_history: dict[str, list[dict[str, Any]]] | None,
    heartbeat_ts,
    core_text: str,
    kernel_text: str,
) -> list[dict[str, Any]]:
    suspects: list[dict[str, Any]] = []

    if gap_seconds is not None:
        suspects.append(
            {
                "kind": "unclean_stop_window",
                "subject": "host",
                "evidence": f"gap of {gap_seconds:.0f}s between last heartbeat and next boot",
                "file": "summary.json",
            }
        )

    suspects.append(
        {
            "kind": "journal_classification",
            "subject": "previous boot journal tail",
            "evidence": classification,
            "file": "host-journal-prev-boot.txt",
        }
    )

    for container in containers or []:
        exit_code = container.get("exit_code") or container.get("ExitCode")
        oom = container.get("oom_killed") or container.get("OOMKilled")
        if oom or exit_code in _EXIT_CODE_OOM:
            suspects.append(
                {
                    "kind": "container_exit",
                    "subject": container.get("name") or container.get("slug") or "unknown",
                    "evidence": f"exit_code={exit_code} oom_killed={bool(oom)}",
                    "file": "containers.json",
                }
            )

    for slug, samples in (watchdog_history or {}).items():
        window = [s for s in samples if _before_heartbeat(s, heartbeat_ts)][-15:]
        if len(window) < 2:
            continue
        cpu_vals = [s.get("cpu_percent") for s in window if isinstance(s.get("cpu_percent"), (int, float))]
        mem_vals = [s.get("memory_percent") for s in window if isinstance(s.get("memory_percent"), (int, float))]
        for label, vals, limit in (("cpu", cpu_vals, 85), ("memory", mem_vals, 85)):
            if len(vals) < 2:
                continue
            rising = vals[-1] > vals[0]
            peak = max(vals)
            if rising or peak >= limit:
                suspects.append(
                    {
                        "kind": f"resource_trend_{label}",
                        "subject": slug,
                        "evidence": f"peak {label}={peak:.0f} over last {len(vals)} samples before the heartbeat",
                        "file": "watchdog-history.json",
                    }
                )

    for logger_entry in _last_loggers(core_text):
        suspects.append(
            {
                "kind": "last_logger",
                "subject": logger_entry["logger"],
                "evidence": f"last logged at {logger_entry['ts']}" if logger_entry["ts"] else "last to log",
                "file": "core.txt",
            }
        )

    # Prefer the name in parentheses systemd-coredump reports ("Process N
    # (name) dumped core"); fall back to whatever traps: names directly.
    coredump_paren_re = re.compile(r"\((\S+)\)")
    coredump_traps_re = re.compile(r"traps:\s*(\S+)", re.IGNORECASE)
    for line in kernel_text.splitlines():
        if "systemd-coredump" in line or "traps:" in line:
            match = coredump_paren_re.search(line) or coredump_traps_re.search(line)
            name = match.group(1) if match else line.strip()
            if "chromium" in name.lower() or "hci0" in line.lower():
                continue
            suspects.append(
                {
                    "kind": "coredump",
                    "subject": name,
                    "evidence": line.strip()[:200],
                    "file": "kernel.txt",
                }
            )

    noise_chromium = kernel_text.count("traps: chromium")
    noise_bt = kernel_text.count("Bluetooth: hci0")
    if noise_chromium or noise_bt:
        suspects.append(
            {
                "kind": "noise",
                "subject": "known non-causal noise",
                "evidence": f"traps: chromium x{noise_chromium}, Bluetooth: hci0 x{noise_bt}",
                "file": "kernel.txt",
            }
        )

    for i, suspect in enumerate(suspects, start=1):
        suspect["rank"] = i
    return suspects


def _before_heartbeat(sample: dict[str, Any], heartbeat_ts) -> bool:
    if heartbeat_ts is None:
        return True
    ts = _parse(sample.get("ts"))
    return ts is None or ts <= heartbeat_ts


class CrashForensics:
    """Heartbeat + clean-stop marker + unclean-stop collector."""

    def __init__(self, hass: HomeAssistant, store: HaSocData, audit, watchdog) -> None:
        self.hass = hass
        self.store = store
        self.audit = audit
        self.watchdog = watchdog
        self._unsub_interval = None
        self._unsub_stop = None
        self._unsub_started = None
        self._boot_id = str(uuid4())
        self._config_dir = hass.config.path(SUBDIR)
        self._heartbeat_path = os.path.join(self._config_dir, HEARTBEAT_FILENAME)
        self._last_stop_path = os.path.join(self._config_dir, LAST_STOP_FILENAME)
        self.last_check: dict[str, Any] | None = None
        self._core_started: str | None = None

    @property
    def _settings(self) -> dict[str, Any]:
        return self.store.settings

    def async_start(self, entry) -> None:
        if not self._settings.get("crash_forensics_enabled", True):
            return
        interval = int(self._settings.get("heartbeat_interval_seconds") or 30)
        interval = max(10, min(300, interval))

        entry.async_on_unload(
            self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._async_on_stop)
        )
        self._unsub_interval = async_track_time_interval(
            self.hass, self._async_write_heartbeat, timedelta(seconds=interval)
        )
        entry.async_on_unload(self._async_stop_interval)
        # Write immediately so a fast restart still gets a fresh heartbeat
        # rather than waiting a full interval.
        entry.async_create_task(
            self.hass, self._async_write_heartbeat(), "HA SOC crash forensics initial heartbeat"
        )
        entry.async_on_unload(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._async_on_started
            )
        )

    @callback
    def _async_stop_interval(self) -> None:
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None

    def _sync_write_heartbeat(self) -> None:
        sync_write_json_atomic(
            self._heartbeat_path,
            {"ts": _iso_now(), "boot_id": self._boot_id, "core_started": self._core_started},
        )

    async def _async_write_heartbeat(self, _now=None) -> None:
        if self._core_started is None:
            self._core_started = _iso_now()
        try:
            await self.hass.async_add_executor_job(self._sync_write_heartbeat)
        except OSError:
            _LOGGER.warning("HA SOC crash forensics: could not write heartbeat", exc_info=True)

    async def _async_on_stop(self, _event: Event) -> None:
        def _write() -> None:
            sync_write_json_atomic(self._last_stop_path, {"ts": _iso_now(), "reason": "clean"})

        try:
            await self.hass.async_add_executor_job(_write)
        except OSError:
            _LOGGER.warning("HA SOC crash forensics: could not write the clean-stop marker", exc_info=True)

    async def _async_on_started(self, _event: Event) -> None:
        """Runs after EVENT_HOMEASSISTANT_STARTED, so hassio (needed for
        the Supervisor calls the collector makes) is loaded."""
        try:
            await self.async_check_and_collect()
        except Exception:
            _LOGGER.exception("HA SOC crash forensics: startup check failed")

    def _sync_read_prior_state(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        return (
            sync_read_json(self._heartbeat_path),
            sync_read_json(self._last_stop_path),
        )

    async def async_check_and_collect(self, *, force_dry_run: bool = False) -> dict[str, Any]:
        """Compare the previous boot's heartbeat/last-stop files. Collect a
        bundle when the stop looks unclean (or always, for the owner-only
        "collect now" dry run against the current boot)."""
        heartbeat, last_stop = await self.hass.async_add_executor_job(
            self._sync_read_prior_state
        )
        heartbeat_ts = _parse((heartbeat or {}).get("ts")) if heartbeat else None
        stop_ts = _parse((last_stop or {}).get("ts")) if last_stop else None

        unclean = force_dry_run or (
            heartbeat is not None and (last_stop is None or (heartbeat_ts and stop_ts and heartbeat_ts > stop_ts))
        )
        self.last_check = {
            "checked_at": _iso_now(),
            "heartbeat": heartbeat,
            "last_stop": last_stop,
            "unclean": unclean,
        }
        if not unclean:
            return self.last_check

        if not self._settings.get("crash_forensics_enabled", True) and not force_dry_run:
            return self.last_check

        boot = "0" if force_dry_run else "-1"
        try:
            bundle = await self.async_collect_bundle(
                heartbeat or {"ts": _iso_now()}, boot=boot, dry_run=force_dry_run
            )
            self.last_check["bundle"] = bundle
        except Exception:
            _LOGGER.exception("HA SOC crash forensics: bundle collection failed")
        return self.last_check

    # -- Supervisor calls, every one best-effort -------------------------

    async def _hassio_get(self, path: str, *, text: bool, lines: int | None = None) -> Any:
        from homeassistant.components.hassio.const import DATA_COMPONENT

        params = {"lines": str(lines)} if lines else None
        hassio = self.hass.data[DATA_COMPONENT]
        return await asyncio.wait_for(
            hassio.send_command(
                path, method="get", return_text=text, timeout=SUPERVISOR_TIMEOUT, params=params
            ),
            timeout=SUPERVISOR_TIMEOUT,
        )

    async def _best_effort(self, summary_errors: dict[str, str], key: str, coro) -> Any:
        try:
            return await coro
        except Exception as err:  # noqa: BLE001 - collection must not raise
            summary_errors[key] = str(err)
            return None

    async def _resolve_identifiers(self, summary_errors: dict[str, str]) -> dict[str, str]:
        """Best-effort match of kernel/supervisor/core identifiers against
        what /host/logs/identifiers actually reports; falls back to the
        UNVERIFIED guesses in GUESS_IDENTIFIERS on any failure."""
        raw = await self._best_effort(
            summary_errors, "identifiers", self._hassio_get("/host/logs/identifiers", text=False)
        )
        names: list[str] = []
        if isinstance(raw, dict):
            names = [str(n) for n in (raw.get("data", {}).get("identifiers") or raw.get("identifiers") or [])]
        elif isinstance(raw, list):
            names = [str(n) for n in raw]

        resolved = dict(GUESS_IDENTIFIERS)
        for kind, guess in GUESS_IDENTIFIERS.items():
            match = next((n for n in names if guess in n.lower()), None)
            if match:
                resolved[kind] = match
        return resolved

    async def async_collect_bundle(
        self, heartbeat: dict[str, Any], *, boot: str = "-1", dry_run: bool = False
    ) -> dict[str, Any]:
        summary_errors: dict[str, str] = {}
        bundle_id = f"{BUNDLE_PREFIX}{heartbeat.get('ts', _iso_now()).replace(':', '').replace('+', 'Z')}"
        bundle_dir = os.path.join(self._config_dir, bundle_id)

        identifiers = await self._resolve_identifiers(summary_errors)

        journal_prev = await self._best_effort(
            summary_errors, "host_journal",
            self._hassio_get(f"/host/logs/boots/{boot}", text=True, lines=JOURNAL_LINES),
        ) or ""
        kernel_text = await self._best_effort(
            summary_errors, "kernel_identifier",
            self._hassio_get(
                f"/host/logs/boots/{boot}/identifiers/{identifiers['kernel']}",
                text=True, lines=IDENTIFIER_LINES,
            ),
        ) or ""
        supervisor_text = await self._best_effort(
            summary_errors, "supervisor_identifier",
            self._hassio_get(
                f"/host/logs/boots/{boot}/identifiers/{identifiers['supervisor']}",
                text=True, lines=IDENTIFIER_LINES,
            ),
        ) or ""
        core_text = await self._best_effort(
            summary_errors, "core_identifier",
            self._hassio_get(
                f"/host/logs/boots/{boot}/identifiers/{identifiers['core']}",
                text=True, lines=IDENTIFIER_LINES,
            ),
        ) or ""
        host_info = await self._best_effort(
            summary_errors, "host_info", self._hassio_get("/host/info", text=False)
        ) or {}
        resolution_info = await self._best_effort(
            summary_errors, "resolution_info", self._hassio_get("/resolution/info", text=False)
        ) or {}
        supervisor_info = await self._best_effort(
            summary_errors, "supervisor_info", self._hassio_get("/supervisor/info", text=False)
        ) or {}
        os_info = await self._best_effort(
            summary_errors, "os_info", self._hassio_get("/os/info", text=False)
        ) or {}

        containers: Any = "unavailable"
        try:
            from .containers import async_container_resources

            overview = await async_container_resources(self.hass)
            containers = overview.get("containers", []) if overview.get("available") else "unavailable"
        except Exception as err:  # noqa: BLE001
            summary_errors["containers"] = str(err)

        fault_log_note = None
        fault_content = ""
        try:
            from .logs import async_fault_log_overview

            fault = await async_fault_log_overview(self.hass)
            if fault.get("exists") and fault.get("size_bytes"):
                fault_content = fault.get("content") or ""
            else:
                fault_log_note = (
                    "empty or missing, which is expected unless Core itself crashed on a fatal signal"
                )
        except Exception as err:  # noqa: BLE001
            summary_errors["fault_log"] = str(err)

        watchdog_history = await self.hass.async_add_executor_job(
            sync_read_json, os.path.join(self._config_dir, "watchdog_history.prev.json")
        ) or {}

        heartbeat_ts = _parse(heartbeat.get("ts"))
        boot_timestamp = host_info.get("data", host_info).get("boot_timestamp") if isinstance(host_info, dict) else None
        gap_seconds = None
        if heartbeat_ts and boot_timestamp:
            try:
                boot_dt = dt_util.utc_from_timestamp(float(boot_timestamp) / 1_000_000)
                gap_seconds = (boot_dt - heartbeat_ts).total_seconds()
            except (TypeError, ValueError):
                pass

        classification = classify_journal_tail(journal_prev)
        suspects = _rank_suspects(
            gap_seconds=gap_seconds,
            classification=classification,
            containers=containers if isinstance(containers, list) else None,
            watchdog_history=watchdog_history if isinstance(watchdog_history, dict) else None,
            heartbeat_ts=heartbeat_ts,
            core_text=core_text,
            kernel_text=kernel_text,
        )

        summary = {
            "bundle_id": bundle_id,
            "heartbeat": heartbeat,
            "boot": boot,
            "dry_run": dry_run,
            "identifiers_used": identifiers,
            "classification": classification,
            "gap_seconds": gap_seconds,
            "suspects": suspects,
            "errors": summary_errors,
            "generated_at": _iso_now(),
        }

        files = {
            "host-journal-prev-boot.txt": journal_prev,
            "kernel.txt": kernel_text,
            "supervisor.txt": supervisor_text,
            "core.txt": core_text,
            "host-info.json": host_info,
            "resolution-info.json": resolution_info,
            "supervisor-info.json": supervisor_info,
            "os-info.json": os_info,
            "containers.json": containers,
            "fault-log.txt": fault_content or (fault_log_note or ""),
            "watchdog-history.json": watchdog_history,
            "summary.json": summary,
        }

        await self.hass.async_add_executor_job(self._sync_write_bundle, bundle_dir, files)
        await self.hass.async_add_executor_job(self._sync_enforce_retention)

        self.audit.async_log(
            "crash_forensics",
            user_id=None,
            detail={"bundle_id": bundle_id, "path": bundle_dir, "classification": classification},
        )

        if not dry_run:
            await self._async_raise_repair(bundle_id, bundle_dir, summary)

        return summary

    def _sync_write_bundle(self, bundle_dir: str, files: dict[str, Any]) -> None:
        """Write every file, capping the BUNDLE's total size at
        MAX_BUNDLE_BYTES. summary.json is written last and never
        truncated (it is small and is the index other tooling reads
        first); every other file is truncated once the running total
        would exceed the cap."""
        os.makedirs(bundle_dir, exist_ok=True)
        summary = files.pop("summary.json", None)
        summary_bytes = len(json.dumps(summary).encode("utf-8")) if summary is not None else 0
        budget = max(0, MAX_BUNDLE_BYTES - summary_bytes)
        total = 0
        for name, content in files.items():
            path = os.path.join(bundle_dir, name)
            if isinstance(content, (dict, list)):
                data = json.dumps(content).encode("utf-8")
            else:
                text = content if isinstance(content, str) else str(content)
                data = text.encode("utf-8", errors="replace")
            remaining = max(0, budget - total)
            data = data[:remaining]
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            total += len(data)
        if summary is not None:
            sync_write_json_atomic(os.path.join(bundle_dir, "summary.json"), summary)

    def _sync_enforce_retention(self) -> None:
        try:
            entries = sorted(
                (
                    name
                    for name in os.listdir(self._config_dir)
                    if name.startswith(BUNDLE_PREFIX)
                    and os.path.isdir(os.path.join(self._config_dir, name))
                ),
            )
        except OSError:
            return
        while len(entries) > MAX_BUNDLES:
            oldest = entries.pop(0)
            shutil.rmtree(os.path.join(self._config_dir, oldest), ignore_errors=True)

    async def _async_raise_repair(
        self, bundle_id: str, bundle_dir: str, summary: dict[str, Any]
    ) -> None:
        top3 = summary["suspects"][:3]
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"unclean_stop_{bundle_id.removeprefix(BUNDLE_PREFIX)}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="unclean_stop",
            translation_placeholders={
                "bundle_path": bundle_dir,
                "classification": summary["classification"],
                "top_suspects": "; ".join(
                    f"{s['kind']}:{s['subject']}" for s in top3
                ) or "none identified",
                "gap_seconds": str(summary.get("gap_seconds") or "unknown"),
            },
        )

    # -- surfaces ----------------------------------------------------------

    def sync_list_bundles(self) -> list[dict[str, Any]]:
        bundles: list[dict[str, Any]] = []
        try:
            names = sorted(
                n for n in os.listdir(self._config_dir) if n.startswith(BUNDLE_PREFIX)
            )
        except OSError:
            return bundles
        for name in reversed(names):
            bundle_dir = os.path.join(self._config_dir, name)
            summary = sync_read_json(os.path.join(bundle_dir, "summary.json")) or {}
            size = 0
            for root, _dirs, files in os.walk(bundle_dir):
                for f in files:
                    with contextlib.suppress(OSError):
                        size += os.path.getsize(os.path.join(root, f))
            bundles.append(
                {
                    "id": name,
                    "ts": summary.get("heartbeat", {}).get("ts"),
                    "classification": summary.get("classification"),
                    "gap_seconds": summary.get("gap_seconds"),
                    "suspects": summary.get("suspects", [])[:3],
                    "size_bytes": size,
                    "path": bundle_dir,
                }
            )
        return bundles

    def sync_read_bundle_file(self, bundle_id: str, file_name: str) -> str | None:
        if not BUNDLE_ID_RE.match(bundle_id) or file_name not in BUNDLE_FILES:
            return None
        path = os.path.join(self._config_dir, bundle_id, file_name)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as handle:
            data = handle.read(MAX_FILE_READ_BYTES + 1)
        truncated = len(data) > MAX_FILE_READ_BYTES
        if truncated:
            data = data[:MAX_FILE_READ_BYTES]
        return data.decode("utf-8", errors="replace")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._settings.get("crash_forensics_enabled", True),
            "heartbeat_interval_seconds": self._settings.get("heartbeat_interval_seconds", 30),
            "last_check": self.last_check,
            "bundles": self.sync_list_bundles(),
        }
