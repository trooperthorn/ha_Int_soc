"""Container Resource Watchdog — catch and contain a runaway container.

The problem this solves: Supervisor exposes NO API to cap an add-on's CPU
or memory (verified against aiohasupervisor's full AddonsClient surface —
info/stats/options/security/start/stop/restart/rebuild/uninstall/stdin,
nothing that sets limits), so by default any add-on can eat the host until
the kernel OOM-kills something — often not the guilty container.

Two layers, matching what the platform actually allows:

1. **Watchdog (this module; fully supported APIs).** Samples per-container
   stats on an interval (reusing containers.async_container_resources) and
   tracks consecutive-breach counts per container against its threshold
   (per-container override, else the global default). Only a SUSTAINED
   breach — N consecutive samples — trips it, so a media scan spiking for
   one sample doesn't restart anything. On a trip it always records a
   detection + notification + audit entry, and then takes the container's
   configured action: ``alert`` (nothing further), ``restart``, or ``stop``
   via the real Supervisor API.

   Guard rails, deliberately not configurable:
   - Core and the Supervisor are NEVER auto-restarted/stopped — an
     automated response killing the thing that hosts the automation is a
     footgun; they are always alert-only regardless of configuration.
   - After WATCHDOG_MAX_ACTIONS_PER_HOUR enforcement actions on one
     container, that container is downgraded to alert-only for the rest of
     the hour: an add-on that re-breaches right after every restart is a
     restart LOOP, and looping it forever is worse than saying so.

2. **Hard caps (delivered here, applied by the Probe add-on).** Owner-set
   Docker limits (--memory / --cpus) per add-on, shipped to the Probe over
   the existing firewall poll channel and applied against the Docker
   socket. This is the explicit escape hatch the platform doesn't provide:
   it requires the Probe's Protection Mode to be DISABLED (root-equivalent
   access — the UI says so before anything is applied), and because
   Supervisor recreates containers on update/restart, the Probe re-applies
   the caps on a timer rather than assuming they stick. The Probe reports
   applied/denied state back through the normal ingest path; this module
   only stores intent and result, never touches Docker itself.

Everything runtime (breach counters, usage history ring buffers, action
timestamps) lives in memory only — it's diagnostic, and persisting a
time series through the debounced Store on every sample would churn it
for no configuration value.
"""
from __future__ import annotations

from collections import deque
from datetime import timedelta
import logging
import time
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import (
    DETECTION_OPEN,
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

# Ring-buffer depth per container: at the default 60s interval this is one
# hour of samples — enough to show a leak's growth curve in the panel.
_HISTORY_SAMPLES = 60


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
        # slug -> deque of {"ts", "cpu_percent", "memory_percent", "memory_usage"}
        self._history: dict[str, deque] = {}
        # slug -> list of monotonic timestamps of enforcement actions taken
        self._action_times: dict[str, list[float]] = {}
        # slug -> short human string describing the last watchdog outcome
        self._last_outcome: dict[str, str] = {}

    # -- lifecycle ---------------------------------------------------------

    @property
    def config(self) -> dict[str, Any]:
        return self.store.data["resource_watchdog"]

    @callback
    def async_start(self) -> None:
        """(Re)arm the sampling timer to match the stored config."""
        self.async_stop()
        if not self.config.get("enabled"):
            return
        interval = int(self.config.get("interval_seconds") or 60)
        interval = max(30, min(3600, interval))
        self._unsub = async_track_time_interval(
            self.hass, self._async_sample, timedelta(seconds=interval)
        )
        _LOGGER.debug("Resource watchdog armed (every %ss)", interval)

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    # -- configuration resolution -----------------------------------------

    def _limits_for(self, slug: str, kind: str) -> tuple[int | None, int | None, str]:
        """(cpu_threshold, memory_threshold, action) for one container.

        Core/Supervisor are clamped to alert-only here — the one rule the
        configuration cannot override (see module docstring).
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

    # -- sampling ----------------------------------------------------------

    async def _async_sample(self, _now=None) -> None:
        try:
            await self.async_run_once()
        except Exception:  # noqa: BLE001 - the sampling loop must never die
            _LOGGER.exception("Resource watchdog sample failed")

    async def async_run_once(self) -> None:
        """One sampling pass. Public for tests and the WS refresh path."""
        overview = await async_container_resources(self.hass)
        if not overview.get("available"):
            return

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

            # A stopped add-on can't breach anything; clear its counter.
            if container.get("kind") == "addon" and container.get("state") != "started":
                self._breach_counts.pop(slug, None)
                continue

            cpu_limit, mem_limit, action = self._limits_for(slug, container.get("kind"))
            cpu = container.get("cpu_percent")
            mem = container.get("memory_percent")
            over_cpu = cpu_limit is not None and isinstance(cpu, (int, float)) and cpu >= cpu_limit
            over_mem = mem_limit is not None and isinstance(mem, (int, float)) and mem >= mem_limit

            if not (over_cpu or over_mem):
                self._breach_counts.pop(slug, None)
                continue

            count = self._breach_counts.get(slug, 0) + 1
            self._breach_counts[slug] = count
            if count < sustained:
                continue

            # Sustained breach — trip. Reset the counter so a persisting
            # breach re-trips only after another full sustained window.
            self._breach_counts[slug] = 0
            await self._async_trip(container, action, over_cpu, over_mem, cpu, mem)
            changed = True

        if changed:
            async_dispatcher_send(self.hass, f"{SIGNAL_UPDATE}_dashboard")

    # -- response ----------------------------------------------------------

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

        # Enforcement budget: a container that keeps re-breaching right after
        # each action is a loop — downgrade to alert and say so.
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
                },
            },
        )
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

    # -- status for the panel ---------------------------------------------

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
            "containers": {
                slug: {
                    "breach_count": self._breach_counts.get(slug, 0),
                    "last_outcome": self._last_outcome.get(slug),
                    "history": list(self._history.get(slug) or []),
                }
                for slug in set(self._history) | set(self._last_outcome)
            },
        }


# ---------------------------------------------------------------------------
# Hard-cap plumbing (Core side): intent to the Probe, state back from it.
# ---------------------------------------------------------------------------


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
