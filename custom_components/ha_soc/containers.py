"""Per-container CPU / memory resource usage, for spotting a container that's
starving or crashing the host.

On a Supervisor-based install (Home Assistant OS or Supervised) every add-on,
plus Home Assistant Core and the Supervisor itself, runs as its own Docker
container, and Supervisor exposes a live ``/stats`` for each: CPU %, memory
usage/limit/percent, and network/disk IO. A container pinned at ~100% memory
against its limit is the classic OOM-kill / restart-loop signal — exactly the
"which container is crashing my server" question this answers.

We fetch stats **on demand** via the Supervisor client rather than reading the
hassio integration's cached stats: that cache is only populated for add-ons
whose (default-disabled) stats sensor entities are enabled, so it's empty on a
typical install. Fetching here is bounded by a small concurrency semaphore and
capped add-on count so one refresh can't hammer Supervisor.

Read-only and best-effort: on a non-Supervisor install (Container/Core) there
are no per-container stats to read, and the result honestly says so
(``available: False``) instead of erroring.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

# A container at/above these is worth flagging when hunting a crash: sustained
# high CPU, or memory close to its limit (the OOM-kill precursor).
_HIGH_CPU_PERCENT = 85.0
_HIGH_MEMORY_PERCENT = 85.0

# Bound the on-demand fan-out so a big install can't spam Supervisor.
_MAX_ADDONS = 80
_CONCURRENCY = 6

# The ContainerStats fields (aiohasupervisor) — copied verbatim so a value the
# Supervisor doesn't return simply stays None (UI: "—").
_STAT_FIELDS = (
    "cpu_percent",
    "memory_usage",
    "memory_limit",
    "memory_percent",
    "network_rx",
    "network_tx",
    "blk_read",
    "blk_write",
)


def _stats_to_dict(stats: Any) -> dict[str, Any]:
    return {field: getattr(stats, field, None) for field in _STAT_FIELDS}


def _empty_stats() -> dict[str, Any]:
    return {field: None for field in _STAT_FIELDS}


def _flags_for(container: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    mem = container.get("memory_percent")
    cpu = container.get("cpu_percent")
    if isinstance(mem, (int, float)) and mem >= _HIGH_MEMORY_PERCENT:
        flags.append("high_memory")
    if isinstance(cpu, (int, float)) and cpu >= _HIGH_CPU_PERCENT:
        flags.append("high_cpu")
    # A stopped add-on isn't consuming resources, but a container that keeps
    # going stopped is itself the "crashing" symptom worth surfacing.
    if container.get("kind") == "addon" and container.get("state") not in ("started", None):
        flags.append("not_running")
    return flags


async def async_container_resources(hass: HomeAssistant) -> dict[str, Any]:
    """Live per-container resource usage. Never raises: an unavailable
    Supervisor comes back as available=False with a reason."""
    result: dict[str, Any] = {
        "available": False,
        "reason": None,
        "containers": [],
        "generated_at": dt_util.utcnow().isoformat(),
    }

    if "hassio" not in hass.config.components:
        result["reason"] = "not_supervisor"
        return result

    try:
        from homeassistant.components.hassio import (
            get_supervisor_client,
            get_supervisor_info,
        )
    except Exception:  # noqa: BLE001 - hassio internals not guaranteed stable
        result["reason"] = "hassio_unavailable"
        return result

    try:
        client = get_supervisor_client(hass)
    except Exception:  # noqa: BLE001
        client = None
    if client is None:
        result["reason"] = "no_supervisor_client"
        return result

    supervisor_info = get_supervisor_info(hass) or {}
    addons = (supervisor_info.get("addons") or [])[:_MAX_ADDONS]

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _addon_row(addon: dict[str, Any]) -> dict[str, Any]:
        slug = addon.get("slug")
        state = addon.get("state")
        row: dict[str, Any] = {
            "slug": slug,
            "name": addon.get("name") or slug or "unknown",
            "kind": "addon",
            "state": state,
            "version": addon.get("version"),
            "update_available": bool(addon.get("update_available")),
            **_empty_stats(),
        }
        # A stopped add-on has no live container to read stats from.
        if state == "started" and slug:
            async with sem:
                try:
                    row.update(_stats_to_dict(await client.addons.addon_stats(slug)))
                except Exception as err:  # noqa: BLE001
                    _LOGGER.debug("Could not fetch stats for add-on %s: %s", slug, err)
        return row

    async def _system_row(slug: str, name: str, kind: str, coro_factory) -> dict[str, Any]:
        row: dict[str, Any] = {
            "slug": slug,
            "name": name,
            "kind": kind,
            "state": "started",
            "version": None,
            "update_available": False,
            **_empty_stats(),
        }
        try:
            row.update(_stats_to_dict(await coro_factory()))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not fetch %s stats: %s", kind, err)
        return row

    tasks = [
        _system_row("core", "Home Assistant Core", "core", client.homeassistant.stats),
        _system_row("supervisor", "Supervisor", "supervisor", client.supervisor.stats),
        *[_addon_row(a) for a in addons],
    ]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    containers = [c for c in gathered if isinstance(c, dict)]

    for container in containers:
        container["flags"] = _flags_for(container)

    # Suspicious first (flagged), then by memory %, then CPU % — so a
    # container starving the host floats to the top.
    def _sort_key(c: dict[str, Any]) -> tuple[int, float, float]:
        mem = c.get("memory_percent") or 0
        cpu = c.get("cpu_percent") or 0
        return (0 if c["flags"] else 1, -float(mem), -float(cpu))

    containers.sort(key=_sort_key)

    result["available"] = True
    result["containers"] = containers
    return result
