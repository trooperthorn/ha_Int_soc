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

import os
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

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
