"""USB/serial peripheral visibility — the Local Peripherals tab.

Deliberately reuses Home Assistant core's own USB discovery data
(`homeassistant.components.usb`) instead of adding host-level device
access to the optional HA SOC Probe add-on. Unlike real host port
scanning (probe.py), which is structurally impossible from inside Home
Assistant's own container even on Home Assistant OS, serial-device
visibility is NOT — this is exactly the same data core's own USB
discovery already uses to auto-detect a Zigbee/Z-Wave USB stick, so a
regular integration reaching for the same real API is the honest,
simplest way to get it. No add-on, no extra container privileges.

Scope is therefore the same as core's USB discovery: *serial* USB
devices (anything that shows up as /dev/ttyUSB*//dev/ttyACM*, i.e.
whatever `pyserial`'s `comports()` reports). It does not enumerate
non-serial USB peripherals (storage, HID, hubs, ...) — nothing in Home
Assistant core provides that data today, and this module does not
invent it.

Empty results are genuinely ambiguous here (unlike probe.py, which can
tell "not on Supervisor" apart from "on Supervisor, nothing installed"):
an empty list can mean no serial devices exist, or that this install's
container simply doesn't have /dev access to see them (e.g. a Container
install without the device passed through). There is no reliable way to
tell those apart from inside Python, so this module doesn't pretend to —
see the frontend's empty-state copy for how that's worded honestly.

Cross-integration reads are narrowed to an allowlist (work plan item
SEC-4). When matching a device path to the integration that uses it,
only the locator-shaped keys in const.INTEGRATION_LOCATOR_KEYS are read
out of another integration's config entry, recursing into nested dicts
only under those keys. Credentials and every other field another
integration stores are deliberately never read; a device path that only
appears inside, say, a stored password does not produce a match, and
that is correct. Nothing read here is persisted or returned beyond the
entry id, domain, and title of a matching entry.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterator, Mapping
from itertools import chain
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import INTEGRATION_LOCATOR_KEYS
from .store import HaSocData

# Set form of the const.py allowlist for O(1) membership checks while
# walking every config entry on the system.
_LOCATOR_KEY_SET: frozenset[str] = frozenset(INTEGRATION_LOCATOR_KEYS)


def iter_locator_strings(mapping: Any) -> Iterator[str]:
    """Yield every string stored under an allowlisted locator key of a
    config entry's data or options mapping.

    This is the single place HA SOC reads values out of ANOTHER
    integration's config entry (work plan item SEC-4; entity_remap.py
    imports this same helper for its config-entry fallback). Only the
    keys in const.INTEGRATION_LOCATOR_KEYS are read, and nested dicts
    are descended only when they sit under one of those keys, with the
    allowlist applied again at every level. Credentials and every other
    field another integration stores are deliberately never read, so
    they can never end up in a search haystack, a log line, or a result
    payload. Non-string scalars (ports stored as integers, booleans) are
    skipped: every needle matched against these values is a path or an
    entity_id, which is always a string.
    """
    if not isinstance(mapping, Mapping):
        return
    for key, value in mapping.items():
        if key in _LOCATOR_KEY_SET:
            yield from _locator_leaf_strings(value)


def _locator_leaf_strings(value: Any) -> Iterator[str]:
    """Strings inside a value that sits under an allowlisted locator key.

    Lists are walked item by item; a nested dict gets the allowlist
    applied again (a dict under "device" may hold a "path", but it may
    just as well hold fields this module has no business reading).
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _locator_leaf_strings(item)
    elif isinstance(value, Mapping):
        yield from iter_locator_strings(value)


def _device_key(vid: str | None, pid: str | None, serial_number: str | None, resolved_device: str) -> str:
    """Stable identity across reboots for a real USB device — a
    /dev/ttyUSB0-style path can be reassigned to a different physical
    device on replug/reboot, but vendor/product/serial together reliably
    identify the same unit. Home Assistant's scan_serial_ports() can also
    return native/platform serial ports with no USB vendor/product at all
    (SerialDevice, as opposed to USBDevice — a real HA core distinction,
    not this module's invention); those have no such stable triple, so
    resolved_device is the best available fallback — honestly weaker,
    since a native port's device node isn't guaranteed stable either, but
    the identity concept degrading gracefully to "the path" for a device
    class with genuinely less identifying information available.
    """
    if vid is not None and pid is not None:
        return f"{vid}:{pid}:{serial_number or 'noserial'}"
    return f"native:{resolved_device}"


def _path_mentioned(needle: str, value: str) -> bool:
    """Whether ``value`` mentions the device path ``needle`` as a whole
    path token, not a prefix of a longer one (work plan item 4.13):
    ``/dev/ttyUSB1`` must never match a value holding ``/dev/ttyUSB10``.
    The match is anchored by requiring the character after the path (if
    any) to be a non-path-token character - end of string, a separator
    like ``:`` or a space, or a quote - never an alphanumeric or the
    ``._-`` characters that continue a device node name. The needle
    itself always starts with ``/``, so the leading boundary is the
    slash already present in any longer containing string.
    """
    return re.search(re.escape(needle) + r"(?![A-Za-z0-9._-])", value) is not None


def _assigned_integration(hass: HomeAssistant, *paths: str) -> dict[str, str] | None:
    """Best-effort match: does any config entry mention this device's path
    under an allowlisted locator key? There's no standardized field name
    for "which serial port am I using" across the many integrations that
    use one (zwave_js, deconz, insteon, rflink, ...), so this checks the
    path against every INTEGRATION_LOCATOR_KEYS value rather than
    guessing one field name per integration. Only those keys are read;
    credentials in other integrations' entries are deliberately never
    read (work plan item SEC-4), so a path that only appeared inside a
    stored password no longer matches, which is the correct outcome. The
    match is anchored on a path-token boundary (work plan item 4.13), so
    /dev/ttyUSB1 never claims the integration that owns /dev/ttyUSB10. A
    miss here doesn't prove a device is unused, only that this heuristic
    couldn't find it.
    """
    needles = [p for p in paths if p]
    if not needles:
        return None
    for entry in hass.config_entries.async_entries():
        for value in chain(
            iter_locator_strings(entry.data or {}), iter_locator_strings(entry.options or {})
        ):
            if any(_path_mentioned(needle, value) for needle in needles):
                return {"entry_id": entry.entry_id, "domain": entry.domain, "title": entry.title}
    return None


async def async_peripheral_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the Local Peripherals tab (and dashboard summary) need."""
    try:
        from homeassistant.components.usb import human_readable_device_name
        from homeassistant.components.usb.utils import scan_serial_ports
    except ImportError:
        # The `usb` component (and its aiousbwatcher/pyserial requirements)
        # is part of Home Assistant's default_config and loaded on
        # virtually every real install, but isn't a hard dependency of the
        # bare `homeassistant` package — fail honestly rather than crash
        # the dashboard/tab if it's genuinely absent.
        return {"available": False, "devices": [], "total_count": 0, "unassigned_count": 0}

    def _scan_and_resolve() -> list[tuple[Any, str]]:
        """Scan AND resolve inside one executor job (work plan item 4.13):
        os.path.realpath stats and readlinks through /dev/serial/by-id
        symlinks, blocking filesystem I/O that must never run on the
        event loop, and doing it here also collapses what would be one
        hop per device into a single job."""
        resolved: list[tuple[Any, str]] = []
        for device in scan_serial_ports():
            # resolved_device: present on the HA core version that added
            # the USBDevice/SerialDevice split (backed by the `serialx`
            # library), already the by-id-vs-realpath distinction this
            # module used to compute itself. Fall back to computing it the
            # old way - realpath of `.device` - on an older core that
            # doesn't have this field yet.
            resolved_device = getattr(device, "resolved_device", None)
            resolved.append(
                (
                    device,
                    resolved_device
                    if resolved_device is not None
                    else os.path.realpath(device.device),
                )
            )
        return resolved

    scanned = await hass.async_add_executor_job(_scan_and_resolve)
    ignored = store.data["peripheral_ignored"]

    devices: list[dict[str, Any]] = []
    for device, tty_path in scanned:
        # vid/pid: only USBDevice (a real USB device HA could attribute to
        # a vendor/product) has these — SerialDevice (native/platform
        # serial ports, no USB descriptor) doesn't, a real HA core
        # distinction as of the scan_serial_ports() version that
        # introduced it. getattr degrades this to None on either an older
        # HA core that predates the split (irrelevant there — every
        # object was USBDevice-shaped) or a genuine SerialDevice.
        vid = getattr(device, "vid", None)
        pid = getattr(device, "pid", None)
        by_id_path = device.device if device.device != tty_path else None
        key = _device_key(vid, pid, device.serial_number, tty_path)
        assigned = _assigned_integration(hass, tty_path, by_id_path or "")

        devices.append(
            {
                "key": key,
                "raw_name": human_readable_device_name(
                    device.device,
                    device.serial_number,
                    device.manufacturer,
                    device.description,
                    vid,
                    pid,
                ),
                "tty_path": tty_path,
                "by_id_path": by_id_path,
                "vid": vid,
                "pid": pid,
                "serial_number": device.serial_number,
                "assigned_integration": assigned,
                "ignored": key in ignored,
            }
        )

    unassigned_count = sum(1 for d in devices if d["assigned_integration"] is None and not d["ignored"])
    return {
        "available": True,
        "devices": devices,
        "total_count": len(devices),
        "unassigned_count": unassigned_count,
    }


def async_set_peripheral_ignored(
    store: HaSocData, key: str, ignored: bool, *, by_user_id: str | None, raw_name: str
) -> None:
    store.async_set_peripheral_ignored(
        key, ignored, by_user_id=by_user_id, raw_name=raw_name, at=dt_util.utcnow().isoformat()
    )
