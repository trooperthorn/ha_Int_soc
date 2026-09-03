"""Home Assistant's own crash artifact — home-assistant.log.fault.

Python's faulthandler module (enabled by homeassistant/__main__.py for the
entire process lifetime, writing to this exact filename in the config
directory) only writes here when the process receives a fatal signal —
SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE — a genuine low-level crash, never
a normal Python exception (those already show up in the regular log /
system_log, which is what logs-view's main table already covers).

__main__.py deletes the file if it's empty after a clean shutdown, but a
session that actually crashes never reaches that cleanup code — the fatal
signal kills the process right where faulthandler caught it. So a
non-empty file here means at least one crash happened, and — since the
file is reopened in append mode on every subsequent start — it keeps
growing across restarts until someone clears it by hand. This module only
ever reads it; it never truncates or deletes anything on the user's
behalf.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

FAULT_LOG_FILENAME = "home-assistant.log.fault"

# Advisory glance, not a full log viewer — a crash dump carries one stack
# per thread and can be large, especially after several incidents have
# accumulated. The tail is what answers "did this crash, and how" — older
# history in the same file is still there on disk for anyone who needs it.
_MAX_READ_BYTES = 64 * 1024


async def async_fault_log_overview(hass: HomeAssistant) -> dict[str, Any]:
    """Everything the Logs tab needs to show this file honestly."""
    path = hass.config.path(FAULT_LOG_FILENAME)

    def _read() -> dict[str, Any]:
        try:
            stat = os.stat(path)
        except OSError:
            return {
                "exists": False,
                "content": None,
                "size_bytes": 0,
                "modified_at": None,
                "truncated": False,
            }

        truncated = False
        with open(path, "rb") as f:
            if stat.st_size > _MAX_READ_BYTES:
                f.seek(-_MAX_READ_BYTES, os.SEEK_END)
                truncated = True
            raw = f.read()

        return {
            "exists": True,
            "content": raw.decode("utf-8", errors="replace"),
            "size_bytes": stat.st_size,
            "modified_at": dt_util.utc_from_timestamp(stat.st_mtime).isoformat(),
            "truncated": truncated,
        }

    return await hass.async_add_executor_job(_read)


# ---------------------------------------------------------------------------
# Container (add-on / Core / Supervisor / host) logs, via Supervisor's
# journald gateway. Transport choice and its two quirks (no Range header,
# ANSI stripping) are in docs/OPERATIONS-NOTES.md.
# ---------------------------------------------------------------------------

_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAX_CONTAINER_LOG_BYTES = 128 * 1024
_LOG_FETCH_TIMEOUT = 30

# Fixed system targets (Supervisor journald paths that always exist on a
# Supervisor install). Add-on targets are "addon:<slug>", validated against
# the live add-on list so a slug can never traverse the path.
_SYSTEM_LOG_PATHS = {
    "core": "/core/logs",
    "supervisor": "/supervisor/logs",
    "host": "/host/logs",
}


def _addons_by_slug(hass: HomeAssistant) -> dict[str, str]:
    """{slug: name} for installed add-ons, from the hassio cache (free)."""
    try:
        from homeassistant.components.hassio import get_supervisor_info
    except Exception:  # noqa: BLE001
        return {}
    info = get_supervisor_info(hass) or {}
    return {
        str(a["slug"]): str(a.get("name") or a["slug"])
        for a in info.get("addons", [])
        if a.get("slug")
    }


async def async_container_log_targets(hass: HomeAssistant) -> dict[str, Any]:
    """The selector contents for the Logs tab: system targets plus every
    installed add-on. available=False on a non-Supervisor install."""
    if "hassio" not in hass.config.components:
        return {"available": False, "targets": []}
    targets = [
        {"id": "core", "name": "Home Assistant Core"},
        {"id": "supervisor", "name": "Supervisor"},
        {"id": "host", "name": "Host (full journal)"},
    ]
    targets.extend(
        {"id": f"addon:{slug}", "name": name}
        for slug, name in sorted(_addons_by_slug(hass).items(), key=lambda kv: kv[1].lower())
    )
    return {"available": True, "targets": targets}


async def async_fetch_container_log(hass: HomeAssistant, target: str) -> dict[str, Any]:
    """One container's current log text, ANSI-stripped and tail-capped.
    Never raises: a failure comes back as available=False with a reason."""
    result: dict[str, Any] = {
        "available": False,
        "target": target,
        "content": None,
        "truncated": False,
        "error": None,
        "fetched_at": dt_util.utcnow().isoformat(),
    }
    if "hassio" not in hass.config.components:
        result["error"] = "Container logs need a Supervisor-based install."
        return result

    if target in _SYSTEM_LOG_PATHS:
        path = _SYSTEM_LOG_PATHS[target]
    elif target.startswith("addon:"):
        slug = target.removeprefix("addon:")
        # The slug is interpolated into a Supervisor URL - only ever accept
        # one that the Supervisor itself reports as installed.
        if slug not in _addons_by_slug(hass):
            result["error"] = f"Unknown add-on slug: {slug}"
            return result
        path = f"/addons/{slug}/logs"
    else:
        result["error"] = f"Unknown log target: {target}"
        return result

    try:
        from homeassistant.components.hassio.const import DATA_COMPONENT

        hassio = hass.data[DATA_COMPONENT]
        text = await hassio.send_command(
            path, method="get", return_text=True, timeout=_LOG_FETCH_TIMEOUT
        )
    except Exception as err:  # noqa: BLE001 - surfaced, never raised to the panel
        _LOGGER.warning("Container log fetch for %s failed: %s", target, err)
        result["error"] = f"Could not fetch logs: {err}"
        return result

    if not isinstance(text, str):
        result["error"] = "Supervisor returned an unexpected (non-text) response."
        return result

    text = _ANSI_SGR_RE.sub("", text)
    raw = text.encode("utf-8", errors="replace")
    if len(raw) > _MAX_CONTAINER_LOG_BYTES:
        # Keep the tail: the newest lines answer "what just happened". Cut on
        # a line boundary so the first visible line isn't a torn fragment.
        tail = raw[-_MAX_CONTAINER_LOG_BYTES:]
        newline = tail.find(b"\n")
        if newline != -1:
            tail = tail[newline + 1 :]
        text = tail.decode("utf-8", errors="replace")
        result["truncated"] = True

    result["available"] = True
    result["content"] = text
    return result
