"""Read-only snapshots of the core ``unifi`` / ``unifiprotect`` integrations.

When the user already runs Home Assistant's own UniFi Network and UniFi
Protect integrations, those integrations hold a websocket-fresh copy of the
controller state in memory (clients, devices, WLANs, the Protect bootstrap).
This module copies the fields HA SOC needs out of that in-memory state into
plain dicts, so unifi.py can fill the gaps the direct X-API-KEY Integration
API leaves blank (SSID, VLAN, uptime, bandwidth, WAN health, Protect events).

Design constraints, and why they are absolute:

* ``aiounifi`` and ``uiprotect`` are installed on a box only because the core
  integrations are configured there. Importing either library here (or any
  ``homeassistant.components.unifi*`` / ``unifiprotect*`` module, which import
  those libraries at top level) would crash HA SOC on every install without
  them. So this module never imports them: it duck-types every object with
  ``getattr`` and hardcodes the ``"unifi"`` / ``"unifiprotect"`` domain
  strings.
* ``ConfigEntry.runtime_data`` is deleted on unload, so it is only ever read
  via ``getattr(entry, "runtime_data", None)`` on entries that are LOADED
  (``async_loaded_entries`` filters to those).
* Everything here is read-only. No handler ``.update()``, no mutating call,
  no I/O of any kind; the owning integrations keep the state fresh over their
  own websockets.
* Secrets never cross this boundary. Instead of copying ``.raw`` wholesale
  and redacting, each snapshot copies an explicit whitelist of fields, so
  ``x_passphrase``, ``x_authkey``, serials, tokens, and the rest of the
  ``x_*`` family cannot leak into a panel payload by accident.
* Every access is failure-isolated per entry: this is private core API with
  no stability contract, so a shape change in a future HA release degrades to
  "no enrichment" instead of breaking the panel.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Hardcoded on purpose: importing these constants from the core components
# would import aiounifi/uiprotect transitively (see module docstring).
CORE_NETWORK_DOMAIN = "unifi"
CORE_PROTECT_DOMAIN = "unifiprotect"

# Row-origin markers so the payload is honest about where a row came from
# when it was built entirely from core in-memory data rather than the
# direct Integration API.
NETWORK_ORIGIN = "core_unifi"
PROTECT_ORIGIN = "core_unifiprotect"

# hass.data key holding the core unifi integration's registry of MACs that
# are known to be wireless. It survives the controller's "wired bug" where a
# wireless client is momentarily reported as wired.
_WIRELESS_CLIENTS_KEY = "unifi_wireless_clients"

# The aiounifi client/device "uptime" field is sometimes a duration in
# seconds and sometimes an epoch start timestamp; core unifi disambiguates
# with this same threshold (anything at or above it is an epoch).
_EPOCH_THRESHOLD = 1_000_000_000

_HEX_DIGITS = frozenset("0123456789abcdef")

# DeviceState enum names that mean "this device is not reachable right now".
# The names come from the aiounifi DeviceState IntEnum.
OFFLINE_DEVICE_STATES = frozenset({"DISCONNECTED", "HEARTBEAT_MISSED", "ISOLATED"})


def normalize_mac(value: Any) -> str | None:
    """Lowercase colon-separated MAC, or None. UniFi Network reports MACs as
    ``aa:bb:cc:dd:ee:ff`` while Protect reports them uppercase without
    separators, so both sides are normalized to one form before any join."""
    if value in (None, ""):
        return None
    text = str(value).strip().lower().replace(":", "").replace("-", "")
    if len(text) == 12 and all(c in _HEX_DIGITS for c in text):
        return ":".join(text[i : i + 2] for i in range(0, 12, 2))
    cleaned = str(value).strip().lower()
    return cleaned or None


def uptime_to_seconds(value: Any, now_ts: int) -> int | None:
    """Uptime in seconds from the controller's ambiguous uptime field. Below
    the epoch threshold the value already is a duration; at or above it, it
    is the moment the client came up, so the duration is now minus then."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if v < 0:
        return None
    if v < _EPOCH_THRESHOLD:
        return v
    return max(0, now_ts - v)


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _to_epoch(value: Any) -> int | None:
    """Epoch seconds from an int/float or a datetime-like object (anything
    with a callable ``timestamp()``). Protect hands out datetimes; Network
    hands out epoch ints."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    ts = getattr(value, "timestamp", None)
    if callable(ts):
        try:
            return int(ts())
        except (TypeError, ValueError, OverflowError, OSError):
            return None
    return None


def _enum_str(value: Any) -> str | None:
    """String form of an enum-ish value: prefer ``.value`` (uiprotect string
    enums), fall back to ``.name`` (aiounifi IntEnums), else str()."""
    if value is None:
        return None
    inner = getattr(value, "value", None)
    if isinstance(inner, str):
        return inner
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    return str(value)


def _loaded_runtime_data(hass: HomeAssistant, domain: str) -> list[Any]:
    """runtime_data of every LOADED config entry for a domain. getattr with a
    None default is mandatory here because runtime_data is deleted (not set
    to None) when an entry unloads."""
    out: list[Any] = []
    try:
        entries = hass.config_entries.async_loaded_entries(domain)
    except Exception:  # noqa: BLE001 - enrichment must never break the panel
        _LOGGER.debug("Could not list loaded %s entries", domain, exc_info=True)
        return out
    for entry in entries:
        runtime = getattr(entry, "runtime_data", None)
        if runtime is not None:
            out.append(runtime)
    return out


def _handler_values(handler: Any) -> list[Any]:
    """Materialized values of an aiounifi handler container. These containers
    are not dicts (no ``.keys()``, no ``len()``); ``.values()`` is the
    supported way in."""
    values = getattr(handler, "values", None)
    if not callable(values):
        return []
    try:
        return list(values())
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not iterate a core UniFi handler", exc_info=True)
        return []


def _wireless_macs(hass: HomeAssistant) -> frozenset[str]:
    """Normalized MACs the core unifi integration knows to be wireless."""
    try:
        holder = hass.data.get(_WIRELESS_CLIENTS_KEY)
    except Exception:  # noqa: BLE001
        return frozenset()
    macs = getattr(holder, "wireless_clients", None)
    if not macs:
        return frozenset()
    out: set[str] = set()
    try:
        for mac in macs:
            norm = normalize_mac(mac)
            if norm:
                out.add(norm)
    except Exception:  # noqa: BLE001
        return frozenset()
    return frozenset(out)


# ---------------------------------------------------------------------------
# UniFi Network snapshot
# ---------------------------------------------------------------------------


def _snapshot_client(client: Any, wireless: frozenset[str]) -> dict[str, Any] | None:
    """One aiounifi Client copied to a plain whitelisted dict. Reads go
    through the library's properties where they exist (they absorb the
    hyphenated raw key names like ``rx_bytes-r``); ``vlan``, ``network`` and
    ``network_id`` have no property and are raw-only."""
    mac = normalize_mac(getattr(client, "mac", None))
    if mac is None:
        return None
    raw = getattr(client, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    is_wired = bool(getattr(client, "is_wired", False))
    # The wireless-clients registry outranks the is_wired flag because it
    # survives the controller's wired bug (a wireless client briefly
    # reported as wired would otherwise lose its SSID and rate keys).
    if mac in wireless:
        is_wired = False
    return {
        "mac": mac,
        "name": getattr(client, "name", None),
        "hostname": getattr(client, "hostname", None),
        "ip": getattr(client, "ip", None),
        "essid": getattr(client, "essid", None),
        "is_wired": is_wired,
        "vlan": raw.get("vlan"),
        "network": raw.get("network"),
        "network_id": raw.get("network_id"),
        "uptime": getattr(client, "uptime", None),
        "last_seen": _to_epoch(getattr(client, "last_seen", None)),
        "rx_bytes_r": getattr(client, "rx_bytes_r", None),
        "tx_bytes_r": getattr(client, "tx_bytes_r", None),
        "wired_rx_bytes_r": getattr(client, "wired_rx_bytes_r", None),
        "wired_tx_bytes_r": getattr(client, "wired_tx_bytes_r", None),
    }


def _snapshot_uplink(device: Any) -> dict[str, Any]:
    """Whitelisted copy of a device's uplink dict. On a gateway this is the
    WAN interface: ``ip`` is the WAN IP and the ``*_r`` counters are live
    bytes-per-second rates."""
    uplink = getattr(device, "uplink", None)
    if not isinstance(uplink, dict):
        return {}
    out: dict[str, Any] = {}
    for key in (
        "name",
        "type",
        "up",
        "ip",
        "speed",
        "max_speed",
        "rx_bytes",
        "tx_bytes",
        "rx_bytes_r",
        "tx_bytes_r",
    ):
        if key in uplink:
            out[key] = uplink[key]
    return out


def _snapshot_uptime_stats(device: Any) -> dict[str, Any]:
    """WAN/WAN2 monitor stats, keeping only the probe fields HA SOC reads.
    ``availability`` is the WAN-up signal core itself never surfaces."""
    stats = getattr(device, "uptime_stats", None)
    if not isinstance(stats, dict):
        return {}
    out: dict[str, Any] = {}
    for wan_key in ("WAN", "WAN2"):
        node = stats.get(wan_key)
        monitors = node.get("monitors") if isinstance(node, dict) else None
        if not isinstance(monitors, list):
            continue
        kept = []
        for monitor in monitors:
            if not isinstance(monitor, dict):
                continue
            kept.append(
                {
                    "target": monitor.get("target"),
                    "type": monitor.get("type"),
                    "availability": monitor.get("availability"),
                    "latency_average": monitor.get("latency_average"),
                }
            )
        if kept:
            out[wan_key] = {"monitors": kept}
    return out


def _snapshot_networks(device: Any) -> list[dict[str, Any]]:
    """Per-VLAN inventory from the gateway's raw network_table."""
    raw = getattr(device, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    table = raw.get("network_table")
    if not isinstance(table, list):
        return []
    out: list[dict[str, Any]] = []
    for net in table:
        if not isinstance(net, dict):
            continue
        out.append(
            {
                "id": net.get("_id"),  # VERIFY: network_table row id key.
                "name": net.get("name"),
                "vlan": net.get("vlan"),  # VERIFY: numeric VLAN id key.
                "vlan_enabled": net.get("vlan_enabled"),
                "ip_subnet": net.get("ip_subnet"),
                "purpose": net.get("purpose"),
                "is_guest": net.get("is_guest"),
                "enabled": net.get("enabled"),
                "num_sta": net.get("num_sta"),
            }
        )
    return out


def _snapshot_device(device: Any) -> dict[str, Any] | None:
    """One aiounifi Device copied to a plain whitelisted dict. ``serial`` and
    ``x_*`` keys are deliberately absent (see the redaction note up top)."""
    mac = normalize_mac(getattr(device, "mac", None))
    if mac is None:
        return None
    raw = getattr(device, "raw", None)
    raw = raw if isinstance(raw, dict) else {}
    state = _enum_str(getattr(device, "state", None))
    entry: dict[str, Any] = {
        "mac": mac,
        "name": getattr(device, "name", None),
        "model": getattr(device, "model", None),
        "type": getattr(device, "type", None),
        "ip": getattr(device, "ip", None),
        "version": getattr(device, "version", None),
        "state": state,
        "last_seen": _to_epoch(getattr(device, "last_seen", None)),
        "upgradable": getattr(device, "upgradable", None),
        "internet": raw.get("internet"),
        "uplink": _snapshot_uplink(device),
        "uptime_stats": _snapshot_uptime_stats(device),
        "network_table": _snapshot_networks(device),
    }
    return entry


def _snapshot_wlans(api: Any) -> list[dict[str, Any]]:
    """SSID inventory from hub.api.wlans. Only id/name/enabled are copied;
    a Wlan object also carries x_passphrase, which must never leave core
    memory, and the whitelist guarantees it cannot."""
    out: list[dict[str, Any]] = []
    for wlan in _handler_values(getattr(api, "wlans", None)):
        wlan_id = getattr(wlan, "id", None)
        name = getattr(wlan, "name", None)
        if not name:
            continue
        out.append(
            {
                "id": str(wlan_id) if wlan_id is not None else None,
                "name": str(name),
                "enabled": getattr(wlan, "enabled", None),
            }
        )
    return out


def network_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Plain-dict snapshot of every loaded core unifi entry, merged. Never
    raises; an install without the core integration comes back with
    ``available`` False and empty collections."""
    snap: dict[str, Any] = {
        "available": False,
        "clients": {},
        "devices": {},
        "gateway": None,
        "wlans": [],
        "networks": [],
    }
    wireless = _wireless_macs(hass)
    for hub in _loaded_runtime_data(hass, CORE_NETWORK_DOMAIN):
        api = getattr(hub, "api", None)
        if api is None:
            continue
        try:
            for client in _handler_values(getattr(api, "clients", None)):
                entry = _snapshot_client(client, wireless)
                if entry is not None:
                    snap["clients"][entry["mac"]] = entry
            for device in _handler_values(getattr(api, "devices", None)):
                entry = _snapshot_device(device)
                if entry is None:
                    continue
                snap["devices"][entry["mac"]] = entry
                # The gateway is the device that owns WAN state: uptime_stats
                # and network_table exist only on it, which is a stronger
                # signal than parsing model names.
                if snap["gateway"] is None and (
                    entry["uptime_stats"] or entry["network_table"]
                ):
                    snap["gateway"] = entry
            snap["wlans"].extend(_snapshot_wlans(api))
            snap["available"] = True
        except Exception:  # noqa: BLE001 - a shape change must not break the panel
            _LOGGER.debug("Core unifi snapshot failed for one entry", exc_info=True)
    if snap["gateway"] is not None:
        snap["networks"] = snap["gateway"].get("network_table") or []
    return snap


def resolve_client_vlan(client: dict[str, Any], networks: list[dict[str, Any]]) -> Any:
    """A client's VLAN: the raw ``vlan`` value when the controller sent one,
    otherwise resolved through the gateway's network_table by the client's
    network id or network name. When the table has no numeric VLAN either,
    the network name is returned because a named network is still far more
    useful in the table than a blank cell."""
    vlan = client.get("vlan")
    if vlan not in (None, ""):
        return vlan
    net_id = client.get("network_id")
    net_name = client.get("network")
    for net in networks:
        if (net_id and net.get("id") == net_id) or (
            net_name and net.get("name") == net_name
        ):
            net_vlan = net.get("vlan")
            if net_vlan not in (None, ""):
                return net_vlan
            return net.get("name")
    return net_name if net_name not in (None, "") else None


def client_bandwidth(client: dict[str, Any]) -> dict[str, int] | None:
    """Live throughput for a client in the payload's bandwidth shape. The
    controller splits the rate counters by connection type (``rx_bytes-r``
    for wireless, ``wired-rx_bytes-r`` for wired), so the client's own type
    picks the pair; the other pair is a fallback because a client caught by
    the wired bug reports the wrong type and would otherwise show blank.
    The values are bytes per second surfaced through the existing
    rx_bytes/tx_bytes keys, which the direct API never filled at all."""
    if client.get("is_wired"):
        pairs = (
            ("wired_rx_bytes_r", "wired_tx_bytes_r"),
            ("rx_bytes_r", "tx_bytes_r"),
        )
    else:
        pairs = (
            ("rx_bytes_r", "tx_bytes_r"),
            ("wired_rx_bytes_r", "wired_tx_bytes_r"),
        )
    for rx_key, tx_key in pairs:
        rx, tx = client.get(rx_key), client.get(tx_key)
        if rx is None and tx is None:
            continue
        try:
            rx_i = int(rx or 0)
            tx_i = int(tx or 0)
        except (TypeError, ValueError):
            continue
        return {"rx_bytes": rx_i, "tx_bytes": tx_i, "total_bytes": rx_i + tx_i}
    return None


def device_bandwidth(device: dict[str, Any]) -> dict[str, int] | None:
    """Cumulative uplink byte counters for an infrastructure device, matching
    the semantics the direct API's device-detail endpoint uses for the same
    payload field."""
    uplink = device.get("uplink") or {}
    rx = _to_int(uplink.get("rx_bytes"))
    tx = _to_int(uplink.get("tx_bytes"))
    if rx is None and tx is None:
        return None
    rx_i = rx or 0
    tx_i = tx or 0
    return {"rx_bytes": rx_i, "tx_bytes": tx_i, "total_bytes": rx_i + tx_i}


def wan_from_gateway(gateway: dict[str, Any]) -> dict[str, Any]:
    """WAN health derived from a snapshot gateway dict, in the same key
    vocabulary as unifi.py's _derive_wan plus ``availability`` (a percent
    from the controller's own WAN probes, the best up/down signal it has)
    and ``internet`` (the controller's own internet-reachability verdict)."""
    out: dict[str, Any] = {
        "port": None,
        "up": None,
        "rx_rate_bps": None,
        "tx_rate_bps": None,
        "ip": None,
        "availability": None,
        "internet": None,
    }
    uplink = gateway.get("uplink") or {}
    name = uplink.get("name")
    out["port"] = str(name) if name else None
    ip = uplink.get("ip")
    out["ip"] = str(ip) if ip else None
    out["rx_rate_bps"] = _to_int(uplink.get("rx_bytes_r"))
    out["tx_rate_bps"] = _to_int(uplink.get("tx_bytes_r"))

    internet = gateway.get("internet")
    if isinstance(internet, bool):
        out["internet"] = internet

    availability: float | None = None
    stats = gateway.get("uptime_stats") or {}
    for wan_key in ("WAN", "WAN2"):
        node = stats.get(wan_key)
        monitors = node.get("monitors") if isinstance(node, dict) else None
        if not monitors:
            continue
        for monitor in monitors:
            value = monitor.get("availability")
            if isinstance(value, (int, float)) and (
                availability is None or value > availability
            ):
                availability = float(value)
        # WAN2 is only consulted when the primary WAN reported no monitors,
        # so a dead-but-probed primary link is not masked by a backup link.
        break
    out["availability"] = availability

    up = uplink.get("up")
    if up is None and out["internet"] is not None:
        up = out["internet"]
    if up is None and availability is not None:
        up = availability > 0
    out["up"] = bool(up) if up is not None else None
    return out


def wlan_ssid_map(snapshot: dict[str, Any]) -> dict[str, str]:
    """{wlan_id: ssid_name} in the same shape as the /wifi/broadcasts map, so
    it can stand in for that endpoint when it returns nothing."""
    out: dict[str, str] = {}
    for wlan in snapshot.get("wlans") or []:
        wlan_id, name = wlan.get("id"), wlan.get("name")
        if wlan_id and name:
            out[str(wlan_id)] = str(name)
    return out


def network_name_map(networks: list[dict[str, Any]]) -> dict[str, str]:
    """{network_id: "Name (VLAN x)"} in the same display format unifi.py's
    _fetch_network_map produces, for ACL-rule network name resolution."""
    out: dict[str, str] = {}
    for net in networks:
        net_id, name = net.get("id"), net.get("name")
        if not net_id or not name:
            continue
        vlan = net.get("vlan")
        label = f"{name}" + (f" (VLAN {vlan})" if vlan not in (None, "") else "")
        out[str(net_id)] = label
    return out


# ---------------------------------------------------------------------------
# UniFi Protect snapshot
# ---------------------------------------------------------------------------


def _snapshot_camera(camera: Any) -> dict[str, Any] | None:
    """One uiprotect Camera copied to a plain dict, keyed with the same
    candidate names unifi.py's _normalize_camera already reads so the one
    normalization pipeline serves both data sources."""
    cam_id = getattr(camera, "id", None)
    if not cam_id:
        return None
    host = getattr(camera, "host", None)
    state = _enum_str(getattr(camera, "state", None))
    entry: dict[str, Any] = {
        "id": str(cam_id),
        "name": getattr(camera, "name", None) or getattr(camera, "display_name", None),
        "host": str(host) if host else None,
        "mac": normalize_mac(getattr(camera, "mac", None)),
        "state": state,
        "isConnected": getattr(camera, "is_connected", None),
        "isRecording": getattr(camera, "is_recording", None),
        "lastRing": _to_epoch(getattr(camera, "last_ring", None)),
    }
    recording = getattr(camera, "recording_settings", None)
    mode = _enum_str(getattr(recording, "mode", None))
    if mode:
        entry["recordingSettings"] = {"mode": mode}
    channels: list[dict[str, Any]] = []
    for channel in getattr(camera, "channels", None) or []:
        channels.append(
            {
                "name": getattr(channel, "name", None),
                "width": getattr(channel, "width", None),
                "height": getattr(channel, "height", None),
            }
        )
    entry["channels"] = channels
    return entry


def _event_license_plate(event: Any) -> str | None:
    """A recognized plate string from the event metadata. Protect lands the
    LPR match in detected_thumbnails[].group.matched_name."""
    metadata = getattr(event, "metadata", None)
    thumbnails = getattr(metadata, "detected_thumbnails", None)
    if not thumbnails:
        return None
    for thumb in thumbnails:
        group = getattr(thumb, "group", None)
        matched = getattr(group, "matched_name", None)
        if matched:
            return str(matched)
    return None


def _snapshot_event(event: Any) -> dict[str, Any] | None:
    """One uiprotect Event copied to a dict shaped for _normalize_event.
    ``camera`` carries the camera id (the console deep link needs it) and
    ``camera_name`` the resolved display name for the payload."""
    event_id = getattr(event, "id", None)
    if not event_id:
        return None
    detect_types = [
        _enum_str(t) for t in (getattr(event, "smart_detect_types", None) or [])
    ]
    camera_name = None
    try:
        # event.camera is a resolver property joining back into the
        # bootstrap; it is wrapped because a dangling camera id inside a
        # third-party object must not sink the whole snapshot.
        camera = getattr(event, "camera", None)
        camera_name = getattr(camera, "name", None) or getattr(
            camera, "display_name", None
        )
    except Exception:  # noqa: BLE001
        camera_name = None
    entry: dict[str, Any] = {
        "id": str(event_id),
        "type": _enum_str(getattr(event, "type", None)),
        "smartDetectTypes": [t for t in detect_types if t],
        "score": getattr(event, "score", None),
        "start": _to_epoch(getattr(event, "start", None)),
        "end": _to_epoch(getattr(event, "end", None)),
        "camera": getattr(event, "camera_id", None),
        "camera_name": str(camera_name) if camera_name else None,
        "thumbnail": getattr(event, "thumbnail_id", None),
    }
    plate = _event_license_plate(event)
    if plate:
        entry["metadata"] = {"licensePlate": {"name": plate}}
    return entry


def protect_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Plain-dict snapshot of every loaded core unifiprotect entry, merged.
    Never raises; ``available`` is False when the core integration is not
    loaded so callers can tell "no data" from "no source"."""
    snap: dict[str, Any] = {
        "available": False,
        "origin": None,
        "cameras": [],
        "events": [],
    }
    seen_cameras: set[str] = set()
    seen_events: set[str] = set()
    for data in _loaded_runtime_data(hass, CORE_PROTECT_DOMAIN):
        api = getattr(data, "api", None)
        bootstrap = getattr(api, "bootstrap", None)
        if bootstrap is None:
            continue
        try:
            cameras = getattr(bootstrap, "cameras", None)
            if isinstance(cameras, dict):
                for camera in cameras.values():
                    entry = _snapshot_camera(camera)
                    if entry is not None and entry["id"] not in seen_cameras:
                        seen_cameras.add(entry["id"])
                        snap["cameras"].append(entry)
            events = getattr(bootstrap, "events", None)
            if isinstance(events, dict):
                for event in events.values():
                    entry = _snapshot_event(event)
                    if entry is not None and entry["id"] not in seen_events:
                        seen_events.add(entry["id"])
                        snap["events"].append(entry)
            if snap["origin"] is None:
                base_url = getattr(api, "base_url", None)
                snap["origin"] = str(base_url).rstrip("/") if base_url else None
            snap["available"] = True
        except Exception:  # noqa: BLE001 - a shape change must not break the panel
            _LOGGER.debug("Core unifiprotect snapshot failed for one entry", exc_info=True)
    return snap
