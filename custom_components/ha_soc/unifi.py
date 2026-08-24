"""UniFi Network / Protect — direct-to-console read-only client.

The user supplies a local controller host and a local API key (UniFi OS →
Settings → Control Plane → Integrations → API Key), and HA SOC talks to the
console directly over the LAN with an ``X-API-KEY`` header — no cloud, no
extra add-on, no second integration in the middle. This backs the panel's
Network tab.

Everything here is READ-ONLY: it lists clients, network devices, and derives
a WAN/internet status. It never mutates controller state.

## Why the field mapping is defensive

Ubiquiti ships two overlapping local surfaces and their field names differ:

  * the official **Integration API** under ``/proxy/network/integration/v1``
    (camelCase: ``ipAddress``, ``macAddress``, ``connectedAt`` …), and
  * the older private **controller API** under ``/proxy/network/api/s/{site}``
    (snake_case: ``ip``, ``mac``, ``last_seen``, ``essid``, ``vlan`` …).

This build targets the Integration API (the supported one), but the exact
per-field shape of that API's client/device objects could not be verified
against a live controller from this environment. So every normalized field
is resolved from a *list* of candidate keys spanning both surfaces via
:func:`_first`, and anything genuinely absent degrades to ``None`` (rendered
"—" in the UI) rather than being guessed. Keys marked ``# VERIFY`` below are
the ones most likely to need confirmation against a real console — search
this file for that marker. A security tool that shows an honest "—" beats
one that shows a confidently wrong VLAN or IP.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import aiohttp

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.util.dt as dt_util

from .const import (
    CONF_UNIFI_NETWORK_API_KEY,
    CONF_UNIFI_NETWORK_HOST,
    CONF_UNIFI_NETWORK_VERIFY_SSL,
    CONF_UNIFI_PROTECT_API_KEY,
    CONF_UNIFI_PROTECT_HOST,
    CONF_UNIFI_PROTECT_VERIFY_SSL,
    DEFAULT_UNIFI_VERIFY_SSL,
    UNIFI_NETWORK_API_PATH,
    UNIFI_PROTECT_API_PATH,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
# Safety bounds on pagination so a hostile or huge controller can't make one
# refresh loop forever or return an unbounded payload to the panel.
_PAGE_LIMIT = 200
_MAX_PAGES = 15

# Config-entry keys that commonly hold a device host or IP. Matched against
# UniFi client/device IPs so a failing integration whose endpoint shows up on
# the network can be flagged (see _integration_endpoints).
_HOST_KEYS = (
    "host",
    "hostname",
    "ip_address",
    "ipaddress",
    "ip",
    "address",
    "server",
    "url",
    "base_url",
    "api_url",
)

# ConfigEntryState values that mean the integration is currently NOT working.
# A UniFi client whose IP matches one of these is the "an integration IP is
# failing" signal the Network tab exists to surface.
_FAILING_STATES = frozenset(
    {
        ConfigEntryState.SETUP_ERROR,
        ConfigEntryState.SETUP_RETRY,
        ConfigEntryState.MIGRATION_ERROR,
        ConfigEntryState.FAILED_UNLOAD,
    }
)


class UniFiError(Exception):
    """Any failure talking to a UniFi console — surfaced to the UI as a
    reachable=False overview with a human-readable reason, never a raw stack."""


def _first(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """First present, non-empty value among candidate keys. This is the whole
    reason the module tolerates the Integration-API-vs-legacy field drift:
    each normalized field lists every name it's known by across both surfaces
    and takes whichever the controller actually returned."""
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


@dataclass(frozen=True)
class _Conn:
    """A resolved connection to one UniFi app (Network or Protect)."""

    host: str
    api_key: str
    verify_ssl: bool
    base_path: str

    @property
    def base_url(self) -> str:
        # host may be "10.0.0.1", "10.0.0.1:443", or "https://10.0.0.1".
        # Normalize to a scheme+host origin; the api path is a hardcoded
        # constant appended here, never taken from user input.
        host = self.host.strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        return f"{host}{self.base_path}"


def _network_conn(store: HaSocData) -> _Conn | None:
    s = store.settings
    host = (s.get(CONF_UNIFI_NETWORK_HOST) or "").strip()
    key = (s.get(CONF_UNIFI_NETWORK_API_KEY) or "").strip()
    if not host or not key:
        return None
    return _Conn(
        host=host,
        api_key=key,
        verify_ssl=bool(s.get(CONF_UNIFI_NETWORK_VERIFY_SSL, DEFAULT_UNIFI_VERIFY_SSL)),
        base_path=UNIFI_NETWORK_API_PATH,
    )


def _protect_conn(store: HaSocData) -> _Conn | None:
    s = store.settings
    host = (s.get(CONF_UNIFI_PROTECT_HOST) or "").strip()
    key = (s.get(CONF_UNIFI_PROTECT_API_KEY) or "").strip()
    if not host or not key:
        return None
    return _Conn(
        host=host,
        api_key=key,
        verify_ssl=bool(s.get(CONF_UNIFI_PROTECT_VERIFY_SSL, DEFAULT_UNIFI_VERIFY_SSL)),
        base_path=UNIFI_PROTECT_API_PATH,
    )


async def _get(hass: HomeAssistant, conn: _Conn, path: str) -> Any:
    """One authenticated GET. Raises UniFiError with a friendly reason on any
    transport/HTTP/decode failure — the caller turns that into reachable=False."""
    session = async_get_clientsession(hass, verify_ssl=conn.verify_ssl)
    url = f"{conn.base_url}{path}"
    headers = {"X-API-KEY": conn.api_key, "Accept": "application/json"}
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(url, headers=headers) as resp:
                if resp.status in (401, 403):
                    raise UniFiError("Authentication failed — check the API key.")
                if resp.status == 404:
                    raise UniFiError(f"Endpoint not found ({path}).")
                resp.raise_for_status()
                return await resp.json(content_type=None)
    except UniFiError:
        raise
    except asyncio.TimeoutError as err:
        raise UniFiError("Timed out reaching the UniFi console.") from err
    except aiohttp.ClientError as err:
        raise UniFiError(f"Could not reach the UniFi console: {err}") from err
    except ValueError as err:  # bad/again-not-JSON body
        raise UniFiError("The console returned an unexpected (non-JSON) response.") from err


def _rows(payload: Any) -> list[dict[str, Any]]:
    """Pull the list of records out of a controller response, tolerating the
    two shapes seen in the wild: a bare list, or {"data": [...]} (Integration
    API paginated envelope)."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [r for r in data if isinstance(r, dict)]
    return []


async def _get_paginated(hass: HomeAssistant, conn: _Conn, path: str) -> list[dict[str, Any]]:
    """Follow the Integration API's offset/limit pagination. Falls back to a
    single unpaginated response for surfaces that return a bare list."""
    out: list[dict[str, Any]] = []
    offset = 0
    for _ in range(_MAX_PAGES):
        sep = "&" if "?" in path else "?"
        payload = await _get(hass, conn, f"{path}{sep}offset={offset}&limit={_PAGE_LIMIT}")
        rows = _rows(payload)
        out.extend(rows)
        # A bare list (legacy) or a short page means there's no more to fetch.
        if not isinstance(payload, dict) or len(rows) < _PAGE_LIMIT:
            break
        offset += _PAGE_LIMIT
    return out


async def _resolve_site_id(hass: HomeAssistant, conn: _Conn) -> str:
    """First site's id. Most home installs have exactly one ("default")."""
    payload = await _get(hass, conn, "/sites")
    sites = _rows(payload)
    if not sites:
        raise UniFiError("The console reported no sites for this API key.")
    site = sites[0]
    # VERIFY: site identifier key. Integration API uses "id"; legacy uses
    # "name"/"_id". _first tolerates all three.
    site_id = _first(site, "id", "_id", "siteId", "name")
    if not site_id:
        raise UniFiError("Could not determine the UniFi site id.")
    return str(site_id)


# ---------------------------------------------------------------------------
# HA integration endpoint correlation
# ---------------------------------------------------------------------------


def _hosts_from_value(value: Any) -> list[str]:
    """Bare host/IP strings out of one config-entry value (a plain host, a
    host:port, or a full URL)."""
    if not isinstance(value, str) or not value.strip():
        return []
    v = value.strip()
    if "://" in v:
        parsed = urlparse(v)
        return [parsed.hostname.lower()] if parsed.hostname else []
    # Strip a trailing :port if present (but keep bare IPv6 out of scope —
    # matched separately below on the client's own ipv6 field).
    host = v.split("/", 1)[0]
    if host.count(":") == 1:  # host:port, not IPv6
        host = host.split(":", 1)[0]
    return [host.lower()] if host else []


def _integration_endpoints(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Index of ``host-string -> integration descriptor`` across every config
    entry, so a UniFi client/device whose IP matches can be annotated with
    that integration's live health.

    This is the "I want to know when an integration IP fails" feature: an
    entry in a non-loaded state whose IP is an active client on the network
    is exactly the correlation an operator can't easily make by eye.
    """
    index: dict[str, dict[str, Any]] = {}
    for entry in hass.config_entries.async_entries():
        state = entry.state
        descriptor = {
            "domain": entry.domain,
            "title": entry.title,
            "entry_id": entry.entry_id,
            "state": state.value if hasattr(state, "value") else str(state),
            "healthy": state == ConfigEntryState.LOADED,
            "failing": state in _FAILING_STATES,
        }
        hosts: set[str] = set()
        for key in _HOST_KEYS:
            if key in entry.data:
                hosts.update(_hosts_from_value(entry.data[key]))
        for host in hosts:
            existing = index.get(host)
            # Prefer surfacing a failing integration over a healthy one when
            # two entries share a host (rare, but a failure must win).
            if existing is None or (descriptor["failing"] and not existing["failing"]):
                index[host] = descriptor
    return index


def _match_endpoint(
    endpoints: dict[str, dict[str, Any]], *candidates: str | None
) -> dict[str, Any] | None:
    """First integration whose host matches any of the client's identifiers
    (ipv4 / ipv6 / hostname), preferring a failing one."""
    hits: list[dict[str, Any]] = []
    for cand in candidates:
        if not cand:
            continue
        hit = endpoints.get(str(cand).lower())
        if hit:
            hits.append(hit)
    if not hits:
        return None
    for hit in hits:
        if hit["failing"]:
            return hit
    return hits[0]


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def _as_epoch(value: Any) -> int | None:
    """Best-effort epoch-seconds from a numeric epoch (s or ms) or an ISO
    string. Returns None when it can't be parsed — the UI shows "—"."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        v = int(value)
        # Heuristic: a 13-digit value is milliseconds.
        return v // 1000 if v > 10_000_000_000 else v
    if isinstance(value, str):
        try:
            parsed = dt_util.parse_datetime(value)
        except (ValueError, TypeError):
            parsed = None
        if parsed is not None:
            return int(parsed.timestamp())
        if value.isdigit():
            return int(value)
    return None


def _ipv6_of(raw: dict[str, Any]) -> str | None:
    # Legacy returns ipv6 as a list; Integration API (if present) as a string.
    # VERIFY: IPv6 field name/shape.
    value = _first(raw, "ipv6", "ipv6Address", "ipAddressV6", "ipv6_address")
    if isinstance(value, list):
        return str(value[0]) if value else None
    return str(value) if value else None


def _bandwidth_of(raw: dict[str, Any]) -> dict[str, int] | None:
    """Cumulative rx/tx bytes for a client/device, if the controller reports
    them. VERIFY: byte-counter field names differ across surfaces."""
    rx = _first(raw, "rxBytes", "rx_bytes", "wired-rx_bytes", "rx")
    tx = _first(raw, "txBytes", "tx_bytes", "wired-tx_bytes", "tx")
    if rx is None and tx is None:
        return None
    try:
        rx_i = int(rx) if rx is not None else 0
        tx_i = int(tx) if tx is not None else 0
    except (TypeError, ValueError):
        return None
    return {"rx_bytes": rx_i, "tx_bytes": tx_i, "total_bytes": rx_i + tx_i}


def _normalize_client(
    raw: dict[str, Any], endpoints: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    name = _first(raw, "name", "hostname", "displayName", "alias", "note")
    ipv4 = _first(raw, "ipAddress", "ip", "ipv4", "lastIp", "last_ip", "fixed_ip")
    ipv6 = _ipv6_of(raw)
    mac = _first(raw, "macAddress", "mac")
    # VERIFY: VLAN is the least certain field on the Integration API — it may
    # only be derivable from the client's network, not a first-class field.
    vlan = _first(raw, "vlan", "vlanId", "networkVlanId", "vlan_id")
    # VERIFY: SSID naming (essid legacy, ssid/networkName Integration API).
    ssid = _first(raw, "ssid", "essid", "wifiNetworkName", "networkName", "network_name")
    conn_type = str(_first(raw, "type", "connectionType", default="")).upper()
    wired = conn_type == "WIRED" or (
        conn_type != "WIRELESS"
        and not ssid
        and bool(_first(raw, "wired", "isWired", default=False))
    )
    uptime = _first(raw, "uptime", "uptimeSeconds", "uptime_seconds")
    try:
        uptime = int(uptime) if uptime is not None else None
    except (TypeError, ValueError):
        uptime = None
    last_seen = _as_epoch(
        _first(raw, "lastSeen", "last_seen", "lastConnectionAt", "connectedAt", "connected_at")
    )
    return {
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ipv4": str(ipv4) if ipv4 else None,
        "ipv6": ipv6,
        "mac": str(mac).lower() if mac else None,
        "vlan": vlan,
        "ssid": str(ssid) if ssid else None,
        "wired": wired,
        "uptime": uptime,
        "bandwidth": _bandwidth_of(raw),
        "last_seen": last_seen,
        "integration_match": _match_endpoint(
            endpoints,
            str(ipv4) if ipv4 else None,
            ipv6,
            str(name).lower() if name else None,
        ),
    }


def _normalize_device(
    raw: dict[str, Any], endpoints: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Network infrastructure device (gateway/switch/AP), normalized to the
    SAME columns as a client per the request, with device-only extras."""
    name = _first(raw, "name", "hostname", "displayName", "model")
    ipv4 = _first(raw, "ipAddress", "ip", "ipv4", "lastIp")
    ipv6 = _ipv6_of(raw)
    mac = _first(raw, "macAddress", "mac")
    model = _first(raw, "model", "modelName", "shortname")
    state = str(_first(raw, "state", "status", default="")).upper() or None
    uptime = _first(raw, "uptime", "uptimeSeconds")
    try:
        uptime = int(uptime) if uptime is not None else None
    except (TypeError, ValueError):
        uptime = None
    last_seen = _as_epoch(_first(raw, "lastSeen", "last_seen", "startupTimestamp"))
    return {
        # Same column set as a client row (VLAN/SSID are N/A for infra and
        # come through as None -> "—"), plus model/state for the device table.
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ipv4": str(ipv4) if ipv4 else None,
        "ipv6": ipv6,
        "mac": str(mac).lower() if mac else None,
        "vlan": _first(raw, "vlan", "vlanId"),
        "ssid": None,
        "wired": True,
        "uptime": uptime,
        "bandwidth": _bandwidth_of(raw),
        "last_seen": last_seen,
        "model": str(model) if model else None,
        "state": state,
        "integration_match": _match_endpoint(
            endpoints, str(ipv4) if ipv4 else None, ipv6
        ),
    }


def _is_gateway(raw: dict[str, Any]) -> bool:
    blob = " ".join(
        str(_first(raw, k, default="")).lower()
        for k in ("type", "model", "shortname", "name", "deviceType")
    )
    return any(tok in blob for tok in ("gateway", "udm", "uxg", "usg", "ugw", "dream"))


def _derive_wan(gateway: dict[str, Any] | None) -> dict[str, Any]:
    """WAN status + throughput from the gateway device, best-effort. Every
    field degrades to None (UI: "—") when the console doesn't expose it.

    VERIFY: the exact WAN-port/uplink shape on the Integration API device
    object is the single most uncertain mapping in this file. This walks the
    likely nesting (uplink, wan1, ports[].name==WAN) and stops at the first
    that yields rate/state values.
    """
    wan: dict[str, Any] = {
        "port": None,
        "up": None,
        "rx_rate_bps": None,
        "tx_rate_bps": None,
        "ip": None,
    }
    if not gateway:
        return wan

    def _rate(obj: dict[str, Any], *keys: str) -> int | None:
        val = _first(obj, *keys)
        try:
            return int(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    # Candidate nested objects that may carry WAN stats.
    candidates: list[dict[str, Any]] = []
    for key in ("uplink", "wan1", "wan", "internet"):
        node = gateway.get(key)
        if isinstance(node, dict):
            candidates.append(node)
    # A ports/interfaces array whose entry is named/flagged WAN.
    for arr_key in ("ports", "interfaces", "portTable"):
        arr = gateway.get(arr_key)
        if isinstance(arr, list):
            for port in arr:
                if not isinstance(port, dict):
                    continue
                pname = str(_first(port, "name", "ifname", "port_idx", default="")).lower()
                if "wan" in pname or bool(_first(port, "is_uplink", "isUplink", default=False)):
                    candidates.append(port)

    for node in candidates:
        rx = _rate(node, "rxRateBps", "rx_bytes-r", "rx_rate", "rxRate", "download")
        tx = _rate(node, "txRateBps", "tx_bytes-r", "tx_rate", "txRate", "upload")
        up = _first(node, "up", "enable", "isUp", "plugged")
        ip = _first(node, "ip", "ipAddress", "wan_ip")
        name = _first(node, "name", "ifname")
        if rx is not None or tx is not None or up is not None or ip is not None:
            wan.update(
                {
                    "port": str(name) if name else wan["port"],
                    "up": bool(up) if up is not None else wan["up"],
                    "rx_rate_bps": rx if rx is not None else wan["rx_rate_bps"],
                    "tx_rate_bps": tx if tx is not None else wan["tx_rate_bps"],
                    "ip": str(ip) if ip else wan["ip"],
                }
            )
            break
    return wan


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def async_network_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the Network tab renders in one snapshot: status, WAN, the
    clients table, and the network-devices table — plus a compact Protect
    status. Never raises: a connection problem comes back as
    reachable=False with a human-readable ``error``.
    """
    result: dict[str, Any] = {
        "configured": False,
        "reachable": False,
        "error": None,
        "site_id": None,
        "status": "unknown",
        "internet_connected": None,
        "wan": _derive_wan(None),
        "wireless_client_count": 0,
        "wired_client_count": 0,
        "total_client_count": 0,
        "clients_per_ssid": [],
        "clients": [],
        "devices": [],
        "failing_endpoint_count": 0,
        "generated_at": dt_util.utcnow().isoformat(),
        "protect": await async_protect_status(hass, store),
    }

    conn = _network_conn(store)
    if conn is None:
        return result
    result["configured"] = True

    endpoints = _integration_endpoints(hass)

    try:
        site_id = await _resolve_site_id(hass, conn)
        result["site_id"] = site_id
        clients_raw = await _get_paginated(hass, conn, f"/sites/{site_id}/clients")
        devices_raw = await _get_paginated(hass, conn, f"/sites/{site_id}/devices")
    except UniFiError as err:
        result["error"] = str(err)
        return result
    except Exception as err:  # noqa: BLE001 - never let the panel see a raw trace
        _LOGGER.exception("Unexpected UniFi Network error")
        result["error"] = f"Unexpected error: {err}"
        return result

    clients = [_normalize_client(r, endpoints) for r in clients_raw]
    devices = [_normalize_device(r, endpoints) for r in devices_raw]

    gateway = next((d for d in devices_raw if _is_gateway(d)), None)
    wan = _derive_wan(gateway)

    wireless = [c for c in clients if not c["wired"]]
    per_ssid: dict[str, int] = {}
    for c in wireless:
        ssid = c["ssid"] or "(unknown SSID)"
        per_ssid[ssid] = per_ssid.get(ssid, 0) + 1

    gateway_online = None
    if gateway is not None:
        gstate = str(_first(gateway, "state", "status", default="")).upper()
        gateway_online = gstate in ("ONLINE", "1", "CONNECTED") if gstate else None

    result.update(
        {
            "reachable": True,
            "status": "online" if gateway_online in (True, None) else "offline",
            "internet_connected": wan["up"] if wan["up"] is not None else gateway_online,
            "wan": wan,
            "wireless_client_count": len(wireless),
            "wired_client_count": len(clients) - len(wireless),
            "total_client_count": len(clients),
            "clients_per_ssid": sorted(
                ({"ssid": k, "count": v} for k, v in per_ssid.items()),
                key=lambda x: x["count"],
                reverse=True,
            ),
            "clients": clients,
            "devices": devices,
            "failing_endpoint_count": sum(
                1
                for c in clients
                if c["integration_match"] and c["integration_match"]["failing"]
            ),
        }
    )
    return result


async def async_protect_status(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Compact UniFi Protect status for the Network tab's Protect card:
    reachable + camera counts. Best-effort, never raises."""
    out: dict[str, Any] = {
        "configured": False,
        "reachable": False,
        "error": None,
        "camera_count": 0,
        "cameras_online": 0,
    }
    conn = _protect_conn(store)
    if conn is None:
        return out
    out["configured"] = True
    try:
        # VERIFY: Protect Integration API camera collection path.
        payload = await _get(hass, conn, "/cameras")
    except UniFiError as err:
        out["error"] = str(err)
        return out
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Unexpected UniFi Protect error")
        out["error"] = f"Unexpected error: {err}"
        return out

    cameras = _rows(payload)
    online = 0
    for cam in cameras:
        state = str(_first(cam, "state", "status", "isConnected", default="")).upper()
        if state in ("CONNECTED", "ONLINE", "TRUE", "1"):
            online += 1
    out.update(
        {"reachable": True, "camera_count": len(cameras), "cameras_online": online}
    )
    return out
