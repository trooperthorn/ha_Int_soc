"""Home Assistant's own crash artifact, home-assistant.log.fault, read-only."""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

FAULT_LOG_FILENAME = "home-assistant.log.fault"

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


_ANSI_SGR_RE = re.compile(r"\x1b\[[0-9;]*m")
_MAX_CONTAINER_LOG_BYTES = 128 * 1024
_LOG_FETCH_TIMEOUT = 30

# Supervisor log endpoints, current boot. A previous boot is the same path
# with "/boots/<offset>" inserted after the "logs" segment (Supervisor API:
# /host/logs/boots/-1, /core/logs/boots/-1, /addons/<slug>/logs/boots/-1).
# "kernel" is the host journal restricted to the kernel identifier: the
# only place a hardware fault, an OOM kill, or a watchdog reset shows up.
_SYSTEM_LOG_PATHS = {
    "core": "/core/logs",
    "supervisor": "/supervisor/logs",
    "host": "/host/logs",
    "kernel": "/host/logs",
}
_KERNEL_IDENTIFIER = "kernel"

# The Supervisor tails 100 lines unless told otherwise; the panel's 128 KB
# tail-cap is the real ceiling, so ask for enough lines to reach it.
_LOG_FETCH_LINES = 2000
# journalctl keeps at most a handful of boots on HAOS; anything older is
# rejected before it reaches a Supervisor URL.
_MIN_BOOT_OFFSET = -20


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
        {"id": "kernel", "name": "Host kernel (dmesg)"},
    ]
    targets.extend(
        {"id": f"addon:{slug}", "name": name}
        for slug, name in sorted(_addons_by_slug(hass).items(), key=lambda kv: kv[1].lower())
    )
    return {"available": True, "targets": targets}


async def async_list_boots(hass: HomeAssistant) -> dict[str, Any]:
    """The boot offsets the host journal still holds, newest first: 0 is the
    running boot, -1 the one before it. What the Logs tab needs to offer a
    previous boot's log, which is where the evidence for an unclean stop
    lives (docs/CRASH-FORENSICS.md). Never raises."""
    result: dict[str, Any] = {"available": False, "boots": [0], "error": None}
    if "hassio" not in hass.config.components:
        result["error"] = "Boot history needs a Supervisor-based install."
        return result
    try:
        from homeassistant.components.hassio.const import DATA_COMPONENT

        hassio = hass.data[DATA_COMPONENT]
        raw = await hassio.send_command(
            "/host/logs/boots", method="get", return_text=False, timeout=_LOG_FETCH_TIMEOUT
        )
    except Exception as err:  # noqa: BLE001 - surfaced, never raised to the panel
        _LOGGER.warning("Boot list fetch failed: %s", err)
        result["error"] = f"Could not list boots: {err}"
        return result

    # send_command returns the response envelope on some Core versions and
    # the bare data on others; accept both.
    boots = raw.get("boots") if isinstance(raw, dict) else None
    if boots is None and isinstance(raw, dict):
        boots = (raw.get("data") or {}).get("boots")
    offsets: list[int] = []
    for key in (boots or {}):
        try:
            offset = int(key)
        except (TypeError, ValueError):
            continue
        if _MIN_BOOT_OFFSET <= offset <= 0:
            offsets.append(offset)
    if 0 not in offsets:
        offsets.append(0)
    result["available"] = True
    result["boots"] = sorted(set(offsets), reverse=True)
    return result


def _boot_path(base: str, boot: int) -> str:
    """Insert the Supervisor's boot selector after the "logs" segment."""
    if boot == 0:
        return base
    head, sep, tail = base.partition("/logs")
    return f"{head}{sep}/boots/{boot}{tail}"


async def async_fetch_container_log(
    hass: HomeAssistant, target: str, boot: int = 0
) -> dict[str, Any]:
    """One container's log text, ANSI-stripped and tail-capped. boot=0 is
    the running boot; a negative offset selects an earlier boot the host
    journal still holds. Never raises: a failure comes back as
    available=False with a reason."""
    result: dict[str, Any] = {
        "available": False,
        "target": target,
        "boot": boot,
        "content": None,
        "truncated": False,
        "error": None,
        "fetched_at": dt_util.utcnow().isoformat(),
    }
    if "hassio" not in hass.config.components:
        result["error"] = "Container logs need a Supervisor-based install."
        return result

    if not isinstance(boot, int) or isinstance(boot, bool) or not _MIN_BOOT_OFFSET <= boot <= 0:
        result["error"] = f"Boot offset must be between {_MIN_BOOT_OFFSET} and 0, got {boot!r}"
        return result

    if target in _SYSTEM_LOG_PATHS:
        path = _boot_path(_SYSTEM_LOG_PATHS[target], boot)
        if target == "kernel":
            path = f"{path}/identifiers/{_KERNEL_IDENTIFIER}"
    elif target.startswith("addon:"):
        slug = target.removeprefix("addon:")
        # The slug is interpolated into a Supervisor URL; accept only a slug the Supervisor reports installed.
        if slug not in _addons_by_slug(hass):
            result["error"] = f"Unknown add-on slug: {slug}"
            return result
        path = _boot_path(f"/addons/{slug}/logs", boot)
    else:
        result["error"] = f"Unknown log target: {target}"
        return result

    try:
        from homeassistant.components.hassio.const import DATA_COMPONENT

        hassio = hass.data[DATA_COMPONENT]
        text = await hassio.send_command(
            path,
            method="get",
            return_text=True,
            timeout=_LOG_FETCH_TIMEOUT,
            params={"lines": str(_LOG_FETCH_LINES)},
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
        # Cut on a line boundary so the first visible line is not a torn fragment.
        tail = raw[-_MAX_CONTAINER_LOG_BYTES:]
        newline = tail.find(b"\n")
        if newline != -1:
            tail = tail[newline + 1 :]
        text = tail.decode("utf-8", errors="replace")
        result["truncated"] = True

    result["available"] = True
    result["content"] = text
    return result
