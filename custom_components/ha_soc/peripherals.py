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
"""
from __future__ import annotations

import os
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .store import HaSocData


def _device_key(vid: str, pid: str, serial_number: str | None) -> str:
    """Stable identity across reboots — a /dev/ttyUSB0-style path can be
    reassigned to a different physical device on replug/reboot, but
    vendor/product/serial together reliably identify the same unit."""
    return f"{vid}:{pid}:{serial_number or 'noserial'}"


def _assigned_integration(hass: HomeAssistant, *paths: str) -> dict[str, str] | None:
    """Best-effort match: does any config entry's data/options mention this
    device's path? There's no standardized field name for "which serial
    port am I using" across the many integrations that use one (zwave_js,
    deconz, insteon, rflink, ...), so this checks for the path appearing
    anywhere in the entry's stored data rather than guessing field names
    per-integration. A miss here doesn't prove a device is unused — only
    that this heuristic couldn't find it.
    """
    needles = [p for p in paths if p]
    if not needles:
        return None
    for entry in hass.config_entries.async_entries():
        haystack = f"{entry.data}{entry.options}"
        if any(needle in haystack for needle in needles):
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

    usb_devices = await hass.async_add_executor_job(scan_serial_ports)
    ignored = store.data["peripheral_ignored"]

    devices: list[dict[str, Any]] = []
    for device in usb_devices:
        tty_path = os.path.realpath(device.device)
        by_id_path = device.device if device.device != tty_path else None
        key = _device_key(device.vid, device.pid, device.serial_number)
        assigned = _assigned_integration(hass, tty_path, by_id_path or "")

        devices.append(
            {
                "key": key,
                "raw_name": human_readable_device_name(
                    device.device,
                    device.serial_number,
                    device.manufacturer,
                    device.description,
                    device.vid,
                    device.pid,
                ),
                "tty_path": tty_path,
                "by_id_path": by_id_path,
                "vid": device.vid,
                "pid": device.pid,
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
