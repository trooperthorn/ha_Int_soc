"""Container Resource Watchdog: catch and contain a runaway container.

Two layers: the watchdog here (supported Supervisor APIs) and owner-set
Docker hard caps applied by the Probe add-on. See docs/RESOURCE-WATCHDOG.md.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import timedelta
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .atomic_json import sync_read_json, sync_write_json_atomic
from .const import (
    DETECTION_ACK,
    DETECTION_OPEN,
    DETECTION_RESOLVED,
    SEVERITY_HIGH,
    SIGNAL_UPDATE,
    WATCHDOG_ACTION_ALERT,
    WATCHDOG_ACTION_RESTART,
    WATCHDOG_ACTION_STOP,
    WATCHDOG_ACTIONS,
    WATCHDOG_MAX_ACTIONS_PER_HOUR,
)
from .containers import async_container_resources
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_HISTORY_SAMPLES = 60

# Enforced on the WS schema and re-checked by the Probe before any Docker URL is built.
ADDON_SLUG_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,63}$"

# The Supervisor is asked for container stats no more often than this, unless the watchdog
# interval is shorter. One sample is shared by the watchdog and the Observe push.
STATS_MIN_INTERVAL_SECONDS = 180
# The history ring is written to flash at most this often, plus once when the entry stops.
HISTORY_SAVE_INTERVAL_SECONDS = 600

HISTORY_FILENAME = "watchdog_history.json"
# crash_forensics.py copies this file aside as watchdog_history.prev.json
# BEFORE this module's first save of a new boot, so a bundle collected on
# an unclean stop can show the ring as it stood before this boot started
# overwriting it. See crash_forensics.py's module docstring.
HISTORY_PREV_FILENAME = "watchdog_history.prev.json"


def async_installed_addon_slugs(hass: HomeAssistant) -> set[str] | None:
    """Slugs of the add-ons the Supervisor reports as installed, or None on a
    non-Supervisor install (no answer, as opposed to an empty set)."""
    from homeassistant.helpers.hassio import is_hassio

    from .logs import _addons_by_slug

    if not is_hassio(hass):
        return None
    return set(_addons_by_slug(hass))


def _iso_now() -> str:
    return dt_util.utcnow().isoformat()


class ResourceWatchdog:
    """Periodic per-container resource evaluation + response."""

    def __init__(self, hass: HomeAssistant, store: HaSocData, audit) -> None:
        self.hass = hass
        self.store = store
        self.audit = audit
        self._unsub = None
        # slug -> consecutive samples over threshold
        self._breach_counts: dict[str, int] = {}
        # slug -> start time of the breach episode in progress. An episode runs from the
        # first trip until a sample shows the container back under its limits.
        self._episodes: dict[str, str] = {}
        # slug -> deque of {"ts", "cpu_percent", "memory_percent", "memory_usage"}
        self._history: dict[str, deque] = {}
        # slug -> list of monotonic timestamps of enforcement actions taken
        self._action_times: dict[str, list[float]] = {}
        # slug -> short human string describing the last watchdog outcome
        self._last_outcome: dict[str, str] = {}
        self._history_path = hass.config.path("ha_soc", HISTORY_FILENAME)
        self._history_dirty = False
        self._history_last_write: str | None = None
        # Monotonic time of the last history write attempt. Starts at boot so the first write
        # comes one interval after startup, not at the first sample.
        self._history_saved_at = time.monotonic()
        # The latest successful sample and its monotonic time, shared with the Observe push.
        self.last_overview: dict[str, Any] | None = None
        self.last_overview_at: float | None = None
        # last_overview_at of the sample the watchdog last evaluated, so a sample taken for
        # the push is evaluated once and never twice.
        self._evaluated_at: float | None = None
        self._sample_lock = asyncio.Lock()

    def _sync_load_history(self) -> dict[str, Any] | None:
        """Copy this boot's starting ring to the .prev file, then load it.

        The copy happens before anything in this boot can have written a
        newer sample, so a bundle collected for THIS boot's unclean-stop
        (which can only be about the boot that just ended) reads the ring
        as it stood at the end of the previous boot, not this boot's own
        (still nearly-empty) history.
        """
        raw = sync_read_json(self._history_path)
        if isinstance(raw, dict):
            sync_write_json_atomic(
                self.hass.config.path("ha_soc", HISTORY_PREV_FILENAME), raw
            )
        return raw

    async def async_load_history(self) -> None:
        """Load the persisted ring before the first sample, so a restart
        does not lose the last hour of history the crash-forensics suspect
        ranking depends on. Called once from async_setup_entry.
        """
        raw = await self.hass.async_add_executor_job(self._sync_load_history)
        if not isinstance(raw, dict):
            return
        for slug, samples in raw.items():
            if not isinstance(samples, list):
                continue
            history = self._history.setdefault(slug, deque(maxlen=_HISTORY_SAMPLES))
            history.extend(samples[-_HISTORY_SAMPLES:])

    def _sync_save_history(self) -> None:
        payload = {slug: list(samples) for slug, samples in self._history.items()}
        sync_write_json_atomic(self._history_path, payload)

    async def _async_maybe_save_history(self, *, force: bool = False) -> None:
        """Persist the ring at most once per HISTORY_SAVE_INTERVAL_SECONDS, and only
        when it changed (a config-only pass with no containers touches nothing).

        The ring changes every sample, so writing it each time rewrote the same file
        dozens of times an hour. A crash loses at most the last interval of samples;
        the previous boot's ring is kept in the .prev file for the crash bundle.
        """
        if not self._history_dirty:
            return
        now = time.monotonic()
        if not force and now - self._history_saved_at < HISTORY_SAVE_INTERVAL_SECONDS:
            return
        self._history_dirty = False
        self._history_saved_at = now
        await self.hass.async_add_executor_job(self._sync_save_history)
        self._history_last_write = _iso_now()

    async def async_flush_history(self) -> None:
        """Write the ring now if it changed. Called when the entry stops."""
        await self._async_maybe_save_history(force=True)

    def _prune_history(self, installed: set[str]) -> None:
        """Forget the history of add-ons that are no longer installed.

        Core and the Supervisor are always in the overview and a stopped add-on stays
        in it, so only an uninstall removes a slug.
        """
        for slug in [s for s in self._history if s not in installed]:
            del self._history[slug]
            self._breach_counts.pop(slug, None)
            self._last_outcome.pop(slug, None)
            self._history_dirty = True

    @property
    def config(self) -> dict[str, Any]:
        return self.store.data["resource_watchdog"]

    def _interval_seconds(self) -> int:
        interval = int(self.config.get("interval_seconds") or 60)
        return max(30, min(3600, interval))

    def sample_gap(self) -> float:
        """Shortest time between two Supervisor stats passes, in seconds.

        Three minutes, or the watchdog interval when the watchdog is on and that is
        shorter. The watchdog and the Observe push share one sample under this gap.
        """
        if self.config.get("enabled"):
            return float(min(STATS_MIN_INTERVAL_SECONDS, self._interval_seconds()))
        return float(STATS_MIN_INTERVAL_SECONDS)

    async def async_shared_overview(self, max_age: float | None = None) -> dict[str, Any] | None:
        """The container overview, sampled at most once per ``max_age`` seconds.

        ``max_age`` defaults to ``sample_gap()``. Concurrent callers wait for the one
        in-flight sample instead of asking the Supervisor again. None when the
        Supervisor is unavailable.
        """
        gap = self.sample_gap() if max_age is None else max_age
        async with self._sample_lock:
            if (
                self.last_overview is not None
                and self.last_overview_at is not None
                and time.monotonic() - self.last_overview_at < gap
            ):
                return self.last_overview
            overview = await async_container_resources(self.hass)
            if not overview.get("available"):
                return None
            self._remember_overview(overview)
            return overview

    def _remember_overview(self, overview: dict[str, Any]) -> None:
        self.last_overview = overview
        self.last_overview_at = time.monotonic()

    @callback
    def async_start(self) -> None:
        """(Re)arm the sampling timer to match the stored config."""
        self.async_stop()
        if not self.config.get("enabled"):
            return
        interval = self._interval_seconds()
        self._unsub = async_track_time_interval(
            self.hass, self._async_sample, timedelta(seconds=interval)
        )
        _LOGGER.debug("Resource watchdog armed (every %ss)", interval)

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    def _limits_for(self, slug: str, kind: str) -> tuple[int | None, int | None, str]:
        """(cpu_threshold, memory_threshold, action) for one container.

        Core/Supervisor are clamped to alert-only here; configuration cannot override it.
        """
        cfg = self.config
        override = (cfg.get("overrides") or {}).get(slug) or {}
        if override.get("enabled") is False:
            return None, None, WATCHDOG_ACTION_ALERT
        cpu = override.get("cpu_percent", cfg.get("default_cpu_percent"))
        mem = override.get("memory_percent", cfg.get("default_memory_percent"))
        action = override.get("action") or cfg.get("default_action") or WATCHDOG_ACTION_ALERT
        if action not in WATCHDOG_ACTIONS:
            action = WATCHDOG_ACTION_ALERT
        if kind != "addon":
            action = WATCHDOG_ACTION_ALERT
        return (
            int(cpu) if cpu is not None else None,
            int(mem) if mem is not None else None,
            action,
        )

    def _action_budget_left(self, slug: str) -> bool:
        now = time.monotonic()
        times = [t for t in self._action_times.get(slug, []) if now - t < 3600]
        self._action_times[slug] = times
        return len(times) < WATCHDOG_MAX_ACTIONS_PER_HOUR

    async def _async_sample(self, _now=None) -> None:
        try:
            # Half a gap of tolerance: a sample the push took just before this tick is reused.
            overview = await self.async_shared_overview(self.sample_gap() / 2)
            if overview is not None and self.last_overview_at != self._evaluated_at:
                await self._async_evaluate(overview)
        except Exception:
            _LOGGER.exception("Resource watchdog sample failed")

    async def async_run_once(self) -> None:
        """One sampling pass that always asks the Supervisor. Public for tests and the
        WS refresh path; the timer goes through the shared sample instead."""
        async with self._sample_lock:
            overview = await async_container_resources(self.hass)
            if not overview.get("available"):
                return
            # Kept so the Observe push reuses this sample instead of asking the Supervisor again.
            self._remember_overview(overview)
        await self._async_evaluate(overview)

    async def _async_evaluate(self, overview: dict[str, Any]) -> None:
        """Record history for, and apply the thresholds to, one sample."""
        self._evaluated_at = self.last_overview_at

        sustained = max(1, int(self.config.get("sustained_samples") or 3))
        changed = False

        for container in overview["containers"]:
            slug = container.get("slug")
            if not slug:
                continue
            history = self._history.setdefault(slug, deque(maxlen=_HISTORY_SAMPLES))
            history.append(
                {
                    "ts": _iso_now(),
                    "cpu_percent": container.get("cpu_percent"),
                    "memory_percent": container.get("memory_percent"),
                    "memory_usage": container.get("memory_usage"),
                }
            )
            self._history_dirty = True

            # A stopped add-on can't breach anything; clear its counter.
            if container.get("kind") == "addon" and container.get("state") != "started":
                self._breach_counts.pop(slug, None)
                changed |= self._end_episode(slug)
                continue

            cpu_limit, mem_limit, action = self._limits_for(slug, container.get("kind"))
            cpu = container.get("cpu_percent")
            mem = container.get("memory_percent")
            over_cpu = cpu_limit is not None and isinstance(cpu, (int, float)) and cpu >= cpu_limit
            over_mem = mem_limit is not None and isinstance(mem, (int, float)) and mem >= mem_limit

            if not (over_cpu or over_mem):
                self._breach_counts.pop(slug, None)
                changed |= self._end_episode(slug)
                continue

            count = self._breach_counts.get(slug, 0) + 1
            self._breach_counts[slug] = count
            if count < sustained:
                continue

            # Reset so a persisting breach re-trips only after another full sustained window.
            self._breach_counts[slug] = 0
            await self._async_trip(container, action, over_cpu, over_mem, cpu, mem)
            changed = True

        # A container that vanished from the overview can no longer be breaching. The open
        # detections in the store count too: an episode that began before a restart is in the
        # store but not in _episodes.
        seen = {c.get("slug") for c in overview["containers"]}
        for slug in self._open_breach_slugs() - seen:
            self._breach_counts.pop(slug, None)
            changed |= self._end_episode(slug)

        # Uninstalled add-ons leave the ring. A truncated overview omits installed add-ons, so
        # it cannot say which are gone.
        if not overview.get("truncated"):
            self._prune_history(seen)

        await self._async_maybe_save_history()

        if changed:
            async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_dashboard")

    def _open_breach_slugs(self) -> set[str]:
        """Slugs with a watchdog detection still open or acknowledged, plus open episodes."""
        slugs = set(self._episodes)
        for detection in self.store.data["detections"].values():
            if (
                detection.get("rule_id") == "container_resource_breach"
                and detection.get("status") in (DETECTION_OPEN, DETECTION_ACK)
            ):
                slug = (detection.get("detail") or {}).get("slug")
                if isinstance(slug, str) and slug:
                    slugs.add(slug)
        return slugs

    def _end_episode(self, slug: str) -> bool:
        """Close the breach episode for `slug` and resolve its open detection.

        Returns True when a detection changed. The stored detection decides, not the
        in-memory episode table: the table is empty after a restart, and a breach that was
        open when Home Assistant stopped would otherwise stay open for good and keep the
        Observe breach gauge above 0.
        """
        self._episodes.pop(slug, None)
        detection = self.store.data["detections"].get(f"watchdog_{slug}")
        if detection is None or detection.get("status") not in (DETECTION_OPEN, DETECTION_ACK):
            return False
        self.store.async_set_detection_status(
            f"watchdog_{slug}", DETECTION_RESOLVED, at=_iso_now()
        )
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_detections")
        return True

    async def _async_trip(
        self,
        container: dict[str, Any],
        action: str,
        over_cpu: bool,
        over_mem: bool,
        cpu: Any,
        mem: Any,
    ) -> None:
        slug = container["slug"]
        name = container.get("name") or slug
        what = " and ".join(
            part
            for part, hit in (
                (f"CPU {cpu:.0f}%" if isinstance(cpu, (int, float)) else "CPU", over_cpu),
                (f"memory {mem:.0f}%" if isinstance(mem, (int, float)) else "memory", over_mem),
            )
            if hit
        )

        # Enforcement budget: re-breaching right after each action is a loop; downgrade to alert.
        looped = False
        if action != WATCHDOG_ACTION_ALERT and not self._action_budget_left(slug):
            action = WATCHDOG_ACTION_ALERT
            looped = True

        outcome = "alerted"
        if action in (WATCHDOG_ACTION_RESTART, WATCHDOG_ACTION_STOP):
            outcome = await self._async_enforce(slug, action)
            self._action_times.setdefault(slug, []).append(time.monotonic())

        self._last_outcome[slug] = (
            f"{_iso_now()}: sustained {what} — {outcome}"
            + (" (action budget exhausted — restart loop suspected, downgraded to alert)" if looped else "")
        )

        detection_id = f"watchdog_{slug}"
        now_iso = _iso_now()
        existing = self.store.data["detections"].get(detection_id)
        recurrence = (existing.get("recurrence_count", 0) + 1) if existing else 1
        # A re-trip inside one continuous breach keeps the episode start, so Observe sees
        # one log record for the whole episode; a trip after recovery starts a new one.
        if slug not in self._episodes and existing is not None and existing.get("status") in (
            DETECTION_OPEN,
            DETECTION_ACK,
        ):
            # The breach was already open when this boot began: it is the same episode.
            stored_start = (existing.get("detail") or {}).get("episode_start")
            if isinstance(stored_start, str) and stored_start:
                self._episodes[slug] = stored_start
        new_episode = slug not in self._episodes
        episode_start = now_iso if new_episode else self._episodes[slug]
        self._episodes[slug] = episode_start
        self.store.async_upsert_detection(
            detection_id,
            {
                "id": detection_id,
                "rule_id": "container_resource_breach",
                "severity": SEVERITY_HIGH,
                "user_id": None,
                "ip": None,
                "ts": existing.get("ts", now_iso) if existing else now_iso,
                "last_seen": now_iso,
                "status": DETECTION_OPEN,
                "recurrence_count": recurrence,
                "title": f"Container '{name}' sustained {what}",
                "detail": {
                    "slug": slug,
                    "kind": container.get("kind"),
                    "cpu_percent": cpu,
                    "memory_percent": mem,
                    "action_taken": outcome,
                    "restart_loop_suspected": looped,
                    "episode_start": episode_start,
                },
            },
        )
        if new_episode:
            # The analyst-state rule in the store keeps a resolved row resolved, which is
            # right inside an episode but wrong for a fresh one.
            self.store.data["detections"][detection_id]["status"] = DETECTION_OPEN
        persistent_notification.async_create(
            self.hass,
            f"**{name}** sustained {what} over its watchdog threshold — {outcome}."
            + (
                "\n\n⚠ It keeps breaching right after each action — this looks like a "
                "restart loop; the watchdog has downgraded it to alert-only for now."
                if looped
                else ""
            ),
            title="HA SOC Resource Watchdog",
            notification_id=f"ha_soc_watchdog_{slug}",
        )
        self.audit.async_log(
            "watchdog_triggered",
            user_id=None,
            detail={
                "slug": slug,
                "breach": what,
                "action": action,
                "outcome": outcome,
                "restart_loop_suspected": looped,
            },
        )
        async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_detections")

    async def _async_enforce(self, slug: str, action: str) -> str:
        """Restart/stop an ADD-ON via the Supervisor API (kind guard is
        upstream in _limits_for). Returns a human-readable outcome."""
        try:
            from homeassistant.components.hassio import get_supervisor_client

            client = get_supervisor_client(self.hass)
            if action == WATCHDOG_ACTION_RESTART:
                await client.addons.restart_addon(slug)
                return "add-on restarted"
            await client.addons.stop_addon(slug)
            return "add-on stopped"
        except Exception as err:  # noqa: BLE001 - report, never crash the loop
            _LOGGER.warning("Watchdog could not %s add-on %s: %s", action, slug, err)
            return f"{action} FAILED: {err}"

    def status(self) -> dict[str, Any]:
        return {
            "config": {
                k: v
                for k, v in self.config.items()
                # hard_limit_state is reported per-container below.
                if k != "hard_limit_state"
            },
            "hard_limit_state": self.config.get("hard_limit_state") or {},
            "running": self._unsub is not None,
            "history_file": self._history_path,
            "history_last_write": self._history_last_write,
            "containers": {
                slug: {
                    "breach_count": self._breach_counts.get(slug, 0),
                    "last_outcome": self._last_outcome.get(slug),
                    "history": list(self._history.get(slug) or []),
                }
                for slug in set(self._history) | set(self._last_outcome)
            },
        }


def async_resource_limits_for_probe(store: HaSocData) -> dict[str, Any] | None:
    """The hard-caps block attached to every firewall-poll response, or None
    when no caps are configured (an older Probe simply ignores the key)."""
    limits = store.data["resource_watchdog"].get("hard_limits") or {}
    active = {
        slug: {
            "memory_mb": entry.get("memory_mb"),
            "cpus": entry.get("cpus"),
        }
        for slug, entry in limits.items()
        if entry and (entry.get("memory_mb") or entry.get("cpus"))
    }
    return {"limits": active} if active else None


def async_store_limit_report(store: HaSocData, report: dict[str, Any] | None) -> None:
    """Persist the Probe's report of what caps are actually applied."""
    if not isinstance(report, dict):
        return
    state = store.data["resource_watchdog"].setdefault("hard_limit_state", {})
    at = _iso_now()
    for slug, entry in report.items():
        if not isinstance(entry, dict):
            continue
        state[str(slug)] = {
            "status": str(entry.get("status") or "unknown"),
            "detail": (str(entry.get("detail")) if entry.get("detail") else None),
            "at": at,
        }
    store.async_schedule_save()
