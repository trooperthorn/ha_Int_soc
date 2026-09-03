"""USB/serial peripheral visibility for the Local Peripherals tab, built on core's own USB discovery data."""
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

_LOCATOR_KEY_SET: frozenset[str] = frozenset(INTEGRATION_LOCATOR_KEYS)


def iter_locator_strings(mapping: Any) -> Iterator[str]:
    """Yield every string stored under an allowlisted locator key of a
    config entry's data or options mapping.

    The single place HA SOC reads another integration's config entry; only
    const.INTEGRATION_LOCATOR_KEYS are read, see docs/security.md.
    """
    if not isinstance(mapping, Mapping):
        return
    for key, value in mapping.items():
        if key in _LOCATOR_KEY_SET:
            yield from _locator_leaf_strings(value)


def _locator_leaf_strings(value: Any) -> Iterator[str]:
    """Strings inside a value that sits under an allowlisted locator key."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _locator_leaf_strings(item)
    elif isinstance(value, Mapping):
        yield from iter_locator_strings(value)


def _device_key(vid: str | None, pid: str | None, serial_number: str | None, resolved_device: str) -> str:
    """Stable identity across reboots: vid:pid:serial for a USB device, the
    resolved path for a native serial port that has no USB descriptor."""
    if vid is not None and pid is not None:
        return f"{vid}:{pid}:{serial_number or 'noserial'}"
    return f"native:{resolved_device}"


def _path_mentioned(needle: str, value: str) -> bool:
    """Whether ``value`` mentions ``needle`` as a whole path token:
    ``/dev/ttyUSB1`` must never match a value holding ``/dev/ttyUSB10``."""
    return re.search(re.escape(needle) + r"(?![A-Za-z0-9._-])", value) is not None


def _assigned_integration(hass: HomeAssistant, *paths: str) -> dict[str, str] | None:
    """Best-effort match of a device path against every config entry's
    allowlisted locator keys. A miss does not prove the device is unused."""
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
        # usb is in default_config but not a hard dependency of the homeassistant package.
        return {"available": False, "devices": [], "total_count": 0, "unassigned_count": 0}

    def _scan_and_resolve() -> list[tuple[Any, str]]:
        """Scan and resolve in one executor job: realpath through /dev/serial/by-id is blocking I/O."""
        resolved: list[tuple[Any, str]] = []
        for device in scan_serial_ports():
            # resolved_device exists on current core (USBDevice/SerialDevice split); older cores need realpath.
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
        # Only USBDevice carries vid/pid; a SerialDevice (native port) has neither.
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
