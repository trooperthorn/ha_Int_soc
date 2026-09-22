"""Shared sync helper for small, hot, private JSON files under <config>/ha_soc/.

Not the HA Store helper: Store is versioned config storage meant for
occasional saves (it schedules a debounced write and keeps a migration
path). The resource watchdog ring and the crash-forensics heartbeat write
on every sample/interval (as often as every 10-60s) and only ever need the
latest value with no migration history, so a plain tmp-file + os.replace
(same pattern audit.py uses for its chain head) is lighter and avoids
teaching Store's version machinery about a file that is pure runtime
telemetry, not configuration.
"""
from __future__ import annotations

import contextlib
import json
import os
from typing import Any


def sync_write_json_atomic(path: str, payload: Any) -> None:
    """Write ``payload`` as JSON to ``path``, atomically, mode 0600.

    Sync; the caller must run this in an executor. The temp file is created
    with os.open so the mode is pinned at creation (open() honors the
    umask); os.replace preserves that mode on the real file.
    """
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    tmp_path = f"{path}.tmp"
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(tmp_path)
        raise
    os.replace(tmp_path, path)


def sync_read_json(path: str) -> Any | None:
    """Read a JSON file written by ``sync_write_json_atomic``.

    Sync; the caller must run this in an executor. Returns None for a
    missing or unreadable/corrupt file rather than raising: every caller
    of this helper treats "no prior state" and "unreadable state" the
    same way (start fresh).
    """
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None
