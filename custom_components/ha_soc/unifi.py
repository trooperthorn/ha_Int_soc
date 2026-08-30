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

from . import unifi_core
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
# Network Devices are enriched from the per-device detail endpoint
# (/devices/{id}) for bandwidth / last-seen / firmware-updatable, which the
# list endpoint doesn't carry. Cap the N+1 fan-out for a huge install.
_MAX_DEVICE_DETAILS = 50
# Candidate ACL / firewall endpoints, tried in order (see _fetch_acl_rules).
# The Integration API surface varies by controller version, so we probe
# rather than assume. All are relative to /sites/{siteId}/.
_ACL_ENDPOINT_SUFFIXES = (
    "acl-rules",
    "firewall/rules",
    "firewall-rules",
    "firewall-policies",
    "traffic-rules",
)

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
    def origin(self) -> str:
        # Scheme+authority only (no path) — the base for a browser-facing
        # console URL like https://192.168.30.2/protect/dashboard/... . host
        # may be "10.0.0.1", "10.0.0.1:443", or "https://10.0.0.1".
        host = self.host.strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        parsed = urlparse(host)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def base_url(self) -> str:
        # The API base: origin + the app's hardcoded integration path. The
        # path is a constant appended here, never taken from user input.
        return f"{self.origin}{self.base_path}"


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
    # The Integration client object exposes IPv6 as a list (ipv6Addresses);
    # older/other shapes use a single string. Prefer a real v6-looking value.
    # VERIFY: IPv6 field name/shape.
    value = _first(
        raw, "ipv6", "ipv6Address", "ipAddressV6", "ipv6_address", "ipv6Addresses"
    )
    if isinstance(value, list):
        for v in value:
            if isinstance(v, str) and ":" in v:
                return v
        return str(value[0]) if value else None
    return str(value) if value else None


def _bandwidth_of(raw: dict[str, Any]) -> dict[str, int] | None:
    """Cumulative rx/tx bytes for a client/device. The Integration API nests
    counters under ``statistics`` (and a device's under statistics.uplink),
    so we search the top level and those containers. VERIFY: byte-counter
    field names differ across surfaces."""
    containers: list[dict[str, Any]] = [raw]
    for key in ("statistics", "stats", "uplink"):
        node = raw.get(key)
        if isinstance(node, dict):
            containers.append(node)
            nested_uplink = node.get("uplink")
            if isinstance(nested_uplink, dict):
                containers.append(nested_uplink)

    for c in containers:
        rx = _first(c, "rxBytes", "rx_bytes", "wired-rx_bytes", "rx")
        tx = _first(c, "txBytes", "tx_bytes", "wired-tx_bytes", "tx")
        if rx is None and tx is None:
            continue
        try:
            rx_i = int(rx) if rx is not None else 0
            tx_i = int(tx) if tx is not None else 0
        except (TypeError, ValueError):
            continue
        return {"rx_bytes": rx_i, "tx_bytes": tx_i, "total_bytes": rx_i + tx_i}
    return None


def _client_ssid(raw: dict[str, Any], broadcast_map: dict[str, str]) -> str | None:
    """Resolve a client's SSID. A wireless client carries either the SSID name
    directly, or a reference to a WiFi broadcast whose name lives in the
    /wifi/broadcasts collection — join through broadcast_map for the latter.
    VERIFY: the client->broadcast reference key."""
    direct = _first(raw, "ssid", "essid", "wifiNetworkName", "networkName", "network_name")
    if direct:
        return str(direct)
    if broadcast_map:
        ref = _first(
            raw,
            "wifiBroadcastId",
            "broadcastId",
            "wlanId",
            "wifiNetworkId",
            "wlanConfId",
            "wlanconf_id",
        )
        if ref is not None:
            name = broadcast_map.get(str(ref))
            if name:
                return name
    return None


def _normalize_client(
    raw: dict[str, Any],
    endpoints: dict[str, dict[str, Any]],
    broadcast_map: dict[str, str] | None = None,
    now_ts: int | None = None,
) -> dict[str, Any]:
    broadcast_map = broadcast_map or {}
    name = _first(raw, "name", "hostname", "displayName", "alias", "note")
    ipv4 = _first(raw, "ipAddress", "ip", "ipv4", "lastIp", "last_ip", "fixed_ip")
    ipv6 = _ipv6_of(raw)
    mac = _first(raw, "macAddress", "mac")
    # VERIFY: VLAN — a first-class field on some firmwares, nested under
    # `access` on others; may otherwise only be derivable from the network.
    vlan = _first(raw, "vlan", "vlanId", "networkVlanId", "vlan_id")
    if vlan is None:
        access = raw.get("access")
        if isinstance(access, dict):
            vlan = _first(access, "vlanId", "vlan")
    ssid = _client_ssid(raw, broadcast_map)
    conn_type = str(_first(raw, "type", "connectionType", default="")).upper()
    wired = conn_type == "WIRED" or (
        conn_type != "WIRELESS"
        and not ssid
        and bool(_first(raw, "wired", "isWired", default=False))
    )
    # Uptime: an explicit seconds field if present, otherwise derived from the
    # association timestamp (connectedAt), which is what the Integration API
    # actually returns for a client.
    uptime = _first(raw, "uptime", "uptimeSeconds", "uptime_seconds")
    try:
        uptime = int(uptime) if uptime is not None else None
    except (TypeError, ValueError):
        uptime = None
    if uptime is None:
        connected = _as_epoch(
            _first(raw, "connectedAt", "connected_at", "associationTime", "assocTime")
        )
        if connected is not None and now_ts is not None and now_ts >= connected:
            uptime = now_ts - connected
    last_seen = _as_epoch(
        _first(raw, "lastSeen", "last_seen", "lastConnectionAt", "connectedAt", "connected_at")
    )
    return {
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ipv4": str(ipv4) if ipv4 else None,
        "ipv6": ipv6,
        "mac": str(mac).lower() if mac else None,
        "vlan": vlan,
        "ssid": ssid,
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

    # Firmware-updatable — a real boolean the device (detail) object carries.
    # VERIFY: firmwareUpdatable field name / nesting.
    fw_updatable = _first(raw, "firmwareUpdatable", "updateAvailable", "update_available")
    if fw_updatable is None:
        fw = raw.get("firmware")
        if isinstance(fw, dict):
            fw_updatable = _first(fw, "updatable", "updateAvailable")
    firmware_updatable = bool(fw_updatable) if fw_updatable is not None else None

    # last-seen / heartbeat comes from the per-device detail endpoint; look in
    # the common top-level names and under statistics.
    last_seen = _as_epoch(
        _first(raw, "lastSeen", "last_seen", "lastHeartbeatAt", "startupTimestamp")
    )
    if last_seen is None:
        stats = raw.get("statistics")
        if isinstance(stats, dict):
            last_seen = _as_epoch(_first(stats, "lastHeartbeatAt", "lastSeen"))

    return {
        # IPv6 intentionally dropped from the devices table (not in the API);
        # Uptime replaced by firmware_updatable per the feature request.
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ipv4": str(ipv4) if ipv4 else None,
        "ipv6": ipv6,  # retained in payload; the table no longer renders it
        "mac": str(mac).lower() if mac else None,
        "vlan": _first(raw, "vlan", "vlanId"),
        "ssid": None,
        "wired": True,
        "firmware_updatable": firmware_updatable,
        "bandwidth": _bandwidth_of(raw),
        "last_seen": last_seen,
        "model": str(model) if model else None,
        "state": state,
        "integration_match": _match_endpoint(
            endpoints, str(ipv4) if ipv4 else None, ipv6
        ),
    }


_GATEWAY_TOKENS = (
    "gateway",
    "udm",
    "uxg",
    "usg",
    "ugw",
    "ucg",
    "udr",
    "uxr",
    "dream",
    "console",
)


def _is_gateway(raw: dict[str, Any]) -> bool:
    # A device is the gateway if its role/type says so, or its model/name
    # contains a known gateway marker. Kept broad because the model line-up
    # changes often (UDM/UXG/UCG/UDR/…).
    role = str(_first(raw, "type", "deviceType", "role", default="")).lower()
    if role in ("gateway", "console", "ugw"):
        return True
    blob = " ".join(
        str(_first(raw, k, default="")).lower()
        for k in ("type", "model", "shortname", "name", "deviceType", "role")
    )
    return any(tok in blob for tok in _GATEWAY_TOKENS)


def _wan_candidate_nodes(gateway: dict[str, Any]) -> list[dict[str, Any]]:
    """Every nested object on a gateway device that might carry WAN stats,
    across the shapes seen in the wild: top-level uplink/wan objects, an
    `interfaces` object (dict) with wan/ports, port arrays, and statistics."""
    nodes: list[dict[str, Any]] = []

    def _add_named_dicts(container: dict[str, Any]) -> None:
        for key in ("uplink", "wan1", "wan", "internet", "wan2"):
            node = container.get(key)
            if isinstance(node, dict):
                nodes.append(node)

    _add_named_dicts(gateway)

    stats = gateway.get("statistics")
    if isinstance(stats, dict):
        _add_named_dicts(stats)
        nodes.append(stats)

    # `interfaces` may be a dict (interfaces.wan / interfaces.ports) or a list.
    interfaces = gateway.get("interfaces")
    if isinstance(interfaces, dict):
        _add_named_dicts(interfaces)
        for v in interfaces.values():
            if isinstance(v, list):
                nodes.extend(_wan_ports(v))
    for arr_key in ("ports", "interfaces", "portTable"):
        arr = gateway.get(arr_key)
        if isinstance(arr, list):
            nodes.extend(_wan_ports(arr))

    return nodes


def _wan_ports(arr: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for port in arr:
        if not isinstance(port, dict):
            continue
        pname = str(_first(port, "name", "ifname", "port_idx", "connector", default="")).lower()
        if "wan" in pname or bool(_first(port, "is_uplink", "isUplink", "uplink", default=False)):
            out.append(port)
    return out


def _derive_wan(gateway: dict[str, Any] | None) -> dict[str, Any]:
    """WAN status + throughput from the gateway device, best-effort. Every
    field degrades to None (UI: "—") when the console doesn't expose it.

    VERIFY: the exact WAN-port/uplink shape on the Integration API device
    object is the single most uncertain mapping in this file. This walks every
    plausible nesting (uplink/wan objects, statistics, interfaces dict/list,
    port arrays) and takes the first that yields rate/state/ip values.
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

    for node in _wan_candidate_nodes(gateway):
        rx = _rate(node, "rxRateBps", "rx_bytes-r", "rx_rate", "rxRate", "rxBps", "download")
        tx = _rate(node, "txRateBps", "tx_bytes-r", "tx_rate", "txRate", "txBps", "upload")
        up = _first(node, "up", "enable", "enabled", "isUp", "plugged", "connected")
        ip = _first(node, "ip", "ipAddress", "wan_ip", "wanIp")
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


async def _fetch_broadcast_map(
    hass: HomeAssistant, conn: _Conn, site_id: str
) -> dict[str, str]:
    """{broadcast_id: ssid_name} from /wifi/broadcasts, for the client SSID
    join and the 'Clients per SSID' card. Best-effort — {} on any failure."""
    try:
        rows = await _get_paginated(hass, conn, f"/sites/{site_id}/wifi/broadcasts")
    except (UniFiError, Exception):  # noqa: BLE001
        return {}
    out: dict[str, str] = {}
    for b in rows:
        bid = _first(b, "id", "_id")
        name = _first(b, "name", "ssid", "ssidName")
        if bid and name:
            out[str(bid)] = str(name)
    return out


async def _fetch_device_details(
    hass: HomeAssistant, conn: _Conn, site_id: str, devices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Enrich each device with its /devices/{id} detail (bandwidth, last-seen,
    firmware-updatable), which the list endpoint doesn't carry. Each detail
    fetch is independent and non-fatal — a device whose detail fails keeps its
    list-level data. Bounded by _MAX_DEVICE_DETAILS."""

    async def _one(dev: dict[str, Any]) -> dict[str, Any]:
        did = _first(dev, "id", "_id", "deviceId")
        if not did:
            return dev
        try:
            detail = await _get(hass, conn, f"/sites/{site_id}/devices/{did}")
        except (UniFiError, Exception):  # noqa: BLE001
            return dev
        if isinstance(detail, dict):
            inner = detail.get("data")
            if isinstance(inner, dict):
                detail = inner
            if isinstance(detail, dict):
                merged = dict(dev)
                merged.update(detail)  # detail wins
                return merged
        return dev

    head = devices[:_MAX_DEVICE_DETAILS]
    enriched = await asyncio.gather(*[_one(d) for d in head])
    return list(enriched) + devices[_MAX_DEVICE_DETAILS:]


async def _fetch_network_map(
    hass: HomeAssistant, conn: _Conn, site_id: str
) -> dict[str, str]:
    """{network_id: display_name} so an ACL rule that references networks by
    id can be shown by name. Best-effort — {} if the endpoint is absent."""
    for suffix in ("networks", "network-confs"):
        try:
            rows = await _get_paginated(hass, conn, f"/sites/{site_id}/{suffix}")
        except (UniFiError, Exception):  # noqa: BLE001
            continue
        out: dict[str, str] = {}
        for n in rows:
            nid = _first(n, "id", "_id")
            name = _first(n, "name", "displayName")
            vlan = _first(n, "vlan", "vlanId")
            if nid and name:
                out[str(nid)] = f"{name}" + (f" (VLAN {vlan})" if vlan not in (None, "") else "")
        if out:
            return out
    return {}


def _normalize_acl_rule(
    raw: dict[str, Any], index: int, network_map: dict[str, str]
) -> dict[str, Any]:
    """One ACL / firewall rule, order-preserving. VERIFY: field names vary by
    controller version — this reads the common ones and falls back to the
    payload position for order."""
    order = _first(raw, "ruleIndex", "index", "order", "ruleOrder", "sequence")
    try:
        order = int(order) if order is not None else index
    except (TypeError, ValueError):
        order = index

    # Which networks the rule applies to — resolved to names where possible.
    net_refs: list[Any] = []
    for key in (
        "networkIds",
        "networks",
        "targetNetworkIds",
        "appliesTo",
        "networkId",
        "network",
        "vlanIds",
        "vlans",
    ):
        v = raw.get(key)
        if isinstance(v, list):
            net_refs.extend(v)
        elif v not in (None, ""):
            net_refs.append(v)
    networks: list[str] = []
    for ref in net_refs:
        if isinstance(ref, dict):
            rid = _first(ref, "id", "_id")
            rname = _first(ref, "name", "displayName")
            networks.append(network_map.get(str(rid), str(rname) if rname else str(rid)))
        else:
            networks.append(network_map.get(str(ref), str(ref)))
    # Dedupe, preserve order.
    networks = list(dict.fromkeys(networks))

    enabled = _first(raw, "enabled", "isEnabled")
    return {
        "order": order,
        "id": str(_first(raw, "id", "_id", default="")) or None,
        "name": str(_first(raw, "name", "description", "displayName", default="")) or None,
        "action": (str(_first(raw, "action", "policy", "ruleAction", default="")) or None),
        "enabled": bool(enabled) if enabled is not None else None,
        "direction": str(_first(raw, "direction", "ruleset", "matchDirection", default="")) or None,
        "protocol": str(_first(raw, "protocol", "protocolMatch", default="")) or None,
        "source": str(_first(raw, "source", "src", "sourceZone", default="")) or None,
        "destination": str(_first(raw, "destination", "dst", "destinationZone", default="")) or None,
        "networks": networks,
    }


async def _fetch_acl_rules(
    hass: HomeAssistant, conn: _Conn, site_id: str, network_map: dict[str, str]
) -> dict[str, Any]:
    """Probe the candidate ACL/firewall endpoints and return the first that
    responds, order-preserved. If none respond, `available` is False with the
    list of endpoints tried — an honest 'this controller's API doesn't expose
    it' for the security audit, never a fabricated ruleset."""
    result: dict[str, Any] = {
        "available": False,
        "error": None,
        "endpoint": None,
        "endpoints_tried": list(_ACL_ENDPOINT_SUFFIXES),
        "rules": [],
    }
    last_err: str | None = None
    for suffix in _ACL_ENDPOINT_SUFFIXES:
        try:
            rows = await _get_paginated(hass, conn, f"/sites/{site_id}/{suffix}")
        except UniFiError as err:
            last_err = str(err)
            continue
        except Exception as err:  # noqa: BLE001
            last_err = f"Unexpected error: {err}"
            continue
        result["available"] = True
        result["endpoint"] = suffix
        rules = [_normalize_acl_rule(r, i, network_map) for i, r in enumerate(rows)]
        rules.sort(key=lambda r: r["order"])
        result["rules"] = rules
        return result
    result["error"] = last_err or "No known ACL/firewall endpoint responded."
    return result


async def async_network_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the Network tab renders in one snapshot: status, WAN, the
    clients table, the network-devices table, and the ACL-rules audit report,
    plus a compact Protect status. Never raises: a connection problem comes
    back as reachable=False with a human-readable ``error``.

    Two data sources feed the snapshot. The direct X-API-KEY Integration API
    is fetched first and always wins where it produced a value; afterwards
    the core ``unifi`` integration's in-memory state (when the user runs it)
    fills whatever the API left blank, and stands in entirely when the API is
    unconfigured or down.
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
        "acl": {"available": False, "error": None, "endpoint": None, "endpoints_tried": [], "rules": []},
        "failing_endpoint_count": 0,
        "generated_at": dt_util.utcnow().isoformat(),
        "protect": await async_protect_status(hass, store),
    }

    endpoints = _integration_endpoints(hass)
    now_ts = int(dt_util.utcnow().timestamp())

    # The core snapshot is taken up front so the API path can borrow its WLAN
    # and network name maps as endpoint fallbacks, and the rows it produced
    # can be enriched afterwards.
    core_snap = _core_network_snapshot(hass)

    conn = _network_conn(store)
    if conn is not None:
        result["configured"] = True
        await _fill_network_from_api(hass, conn, result, endpoints, now_ts, core_snap)

    _apply_core_network_data(result, core_snap, endpoints, now_ts)
    return result


async def _fill_network_from_api(
    hass: HomeAssistant,
    conn: _Conn,
    result: dict[str, Any],
    endpoints: dict[str, dict[str, Any]],
    now_ts: int,
    core_snap: dict[str, Any] | None,
) -> None:
    """The direct-to-console fetch path, mutating ``result`` in place. Kept
    separate from the overview assembly so the core in-memory enrichment can
    run whether or not this path succeeded."""
    try:
        site_id = await _resolve_site_id(hass, conn)
        result["site_id"] = site_id
        clients_raw = await _get_paginated(hass, conn, f"/sites/{site_id}/clients")
        devices_raw = await _get_paginated(hass, conn, f"/sites/{site_id}/devices")
    except UniFiError as err:
        result["error"] = str(err)
        return
    except Exception as err:  # noqa: BLE001 - never let the panel see a raw trace
        _LOGGER.exception("Unexpected UniFi Network error")
        result["error"] = f"Unexpected error: {err}"
        return

    # SSID names live in /wifi/broadcasts; enrich devices from their detail
    # endpoint; resolve network names for the ACL report. All best-effort,
    # and when a console endpoint returns nothing the same map is built from
    # the core unifi integration's in-memory WLAN / VLAN inventory instead.
    broadcast_map = await _fetch_broadcast_map(hass, conn, site_id)
    if not broadcast_map and core_snap is not None:
        broadcast_map = unifi_core.wlan_ssid_map(core_snap)
    devices_raw = await _fetch_device_details(hass, conn, site_id, devices_raw)
    network_map = await _fetch_network_map(hass, conn, site_id)
    if not network_map and core_snap is not None:
        network_map = unifi_core.network_name_map(core_snap["networks"])
    result["acl"] = await _fetch_acl_rules(hass, conn, site_id, network_map)

    clients = [_normalize_client(r, endpoints, broadcast_map, now_ts) for r in clients_raw]
    devices = [_normalize_device(r, endpoints) for r in devices_raw]

    gateway = next((d for d in devices_raw if _is_gateway(d)), None)
    wan = _derive_wan(gateway)

    gateway_online = None
    if gateway is not None:
        gstate = str(_first(gateway, "state", "status", default="")).upper()
        if gstate in ("OFFLINE", "DISCONNECTED", "0", "PENDING_ADOPTION"):
            gateway_online = False
        else:
            # A gateway that's present in the devices list and not explicitly
            # offline is treated as online, so "Internet" resolves to
            # Connected (best-effort) instead of Unknown when the console
            # doesn't expose an explicit WAN up/down flag.
            gateway_online = True

    result.update(
        {
            "reachable": True,
            "status": "online" if gateway_online in (True, None) else "offline",
            "internet_connected": wan["up"] if wan["up"] is not None else gateway_online,
            "wan": wan,
            "clients": clients,
            "devices": devices,
        }
    )
    _recompute_client_stats(result)


def _recompute_client_stats(result: dict[str, Any]) -> None:
    """Aggregates derived from the client rows (counts, the per-SSID card,
    the failing-integration banner count). Recomputed after core enrichment
    as well, because enrichment can add rows or resolve SSIDs that move
    clients between buckets."""
    clients = result["clients"]
    wireless = [c for c in clients if not c["wired"]]
    per_ssid: dict[str, int] = {}
    for c in wireless:
        ssid = c["ssid"] or "(unknown SSID)"
        per_ssid[ssid] = per_ssid.get(ssid, 0) + 1
    result.update(
        {
            "wireless_client_count": len(wireless),
            "wired_client_count": len(clients) - len(wireless),
            "total_client_count": len(clients),
            "clients_per_ssid": sorted(
                ({"ssid": k, "count": v} for k, v in per_ssid.items()),
                key=lambda x: x["count"],
                reverse=True,
            ),
            "failing_endpoint_count": sum(
                1
                for c in clients
                if c["integration_match"] and c["integration_match"]["failing"]
            ),
        }
    )


# ---------------------------------------------------------------------------
# Enrichment from the core `unifi` integration's in-memory state
# ---------------------------------------------------------------------------


def _core_network_snapshot(hass: HomeAssistant) -> dict[str, Any] | None:
    """The core unifi in-memory snapshot, or None when the core integration
    is not loaded or anything about reading it went wrong. The guard exists
    so a private-API shape change can never take the Network tab down."""
    try:
        snap = unifi_core.network_snapshot(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Core unifi snapshot unavailable", exc_info=True)
        return None
    return snap if snap.get("available") else None


def _apply_core_network_data(
    result: dict[str, Any],
    snap: dict[str, Any] | None,
    endpoints: dict[str, dict[str, Any]],
    now_ts: int,
) -> None:
    """Fill the overview's blanks from the core unifi integration. Direct-API
    values always win; core memory only fills what is empty, and supplies the
    rows outright when the API produced none. Failure-isolated: any surprise
    in the core data leaves the API-only payload as it was."""
    if snap is None:
        return
    try:
        _enrich_clients_from_core(result, snap, endpoints, now_ts)
        _enrich_devices_from_core(result, snap, endpoints)
        _enrich_wan_from_core(result, snap)
        _recompute_client_stats(result)
        # Rows built or completed from core memory are real data even when
        # the direct API is unconfigured or unreachable, so the panel is told
        # it has something to render. Any API error string stays in the
        # payload for honesty.
        if result["clients"] or result["devices"]:
            result["configured"] = True
            result["reachable"] = True
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Core unifi enrichment failed", exc_info=True)


def _enrich_clients_from_core(
    result: dict[str, Any],
    snap: dict[str, Any],
    endpoints: dict[str, dict[str, Any]],
    now_ts: int,
) -> None:
    core_clients: dict[str, dict[str, Any]] = snap["clients"]
    if not core_clients:
        return
    networks = snap["networks"]
    if result["clients"]:
        for row in result["clients"]:
            cc = core_clients.get(unifi_core.normalize_mac(row.get("mac")) or "")
            if cc is not None:
                _fill_client_row_from_core(row, cc, networks, now_ts)
    else:
        result["clients"] = [
            _client_row_from_core(cc, networks, endpoints, now_ts)
            for cc in core_clients.values()
        ]


def _fill_client_row_from_core(
    row: dict[str, Any],
    cc: dict[str, Any],
    networks: list[dict[str, Any]],
    now_ts: int,
) -> None:
    """Fill one API client row's blanks from its core in-memory twin. A value
    the direct API already produced is never overwritten. Bandwidth is the
    exception in spirit only: the Integration API never returns it, so core
    memory is its primary source rather than a fallback."""
    if row.get("ssid") in (None, "") and cc.get("essid"):
        row["ssid"] = str(cc["essid"])
    if row.get("vlan") in (None, ""):
        vlan = unifi_core.resolve_client_vlan(cc, networks)
        if vlan not in (None, ""):
            row["vlan"] = vlan
    if row.get("uptime") is None:
        row["uptime"] = unifi_core.uptime_to_seconds(cc.get("uptime"), now_ts)
    if row.get("last_seen") is None and cc.get("last_seen") is not None:
        row["last_seen"] = cc["last_seen"]
    if row.get("bandwidth") is None:
        row["bandwidth"] = unifi_core.client_bandwidth(cc)


def _client_row_from_core(
    cc: dict[str, Any],
    networks: list[dict[str, Any]],
    endpoints: dict[str, dict[str, Any]],
    now_ts: int,
) -> dict[str, Any]:
    """A full client row assembled from core in-memory data and pushed
    through the same _normalize_client pipeline the direct API uses, so both
    sources produce an identical shape. ``origin`` marks the provenance."""
    raw: dict[str, Any] = {
        "name": cc.get("name"),
        "hostname": cc.get("hostname"),
        "ip": cc.get("ip"),
        "mac": cc.get("mac"),
        "essid": cc.get("essid"),
        "type": "WIRED" if cc.get("is_wired") else "WIRELESS",
        "vlan": unifi_core.resolve_client_vlan(cc, networks),
        "uptime": unifi_core.uptime_to_seconds(cc.get("uptime"), now_ts),
        "last_seen": cc.get("last_seen"),
    }
    row = _normalize_client(raw, endpoints, {}, now_ts)
    row["bandwidth"] = unifi_core.client_bandwidth(cc)
    row["origin"] = unifi_core.NETWORK_ORIGIN
    return row


def _enrich_devices_from_core(
    result: dict[str, Any],
    snap: dict[str, Any],
    endpoints: dict[str, dict[str, Any]],
) -> None:
    core_devices: dict[str, dict[str, Any]] = snap["devices"]
    if not core_devices:
        return
    if result["devices"]:
        for row in result["devices"]:
            cd = core_devices.get(unifi_core.normalize_mac(row.get("mac")) or "")
            if cd is not None:
                _fill_device_row_from_core(row, cd)
    else:
        result["devices"] = [
            _device_row_from_core(cd, endpoints) for cd in core_devices.values()
        ]


def _fill_device_row_from_core(row: dict[str, Any], cd: dict[str, Any]) -> None:
    if row.get("state") in (None, "") and cd.get("state"):
        row["state"] = str(cd["state"]).upper()
    if row.get("last_seen") is None and cd.get("last_seen") is not None:
        row["last_seen"] = cd["last_seen"]
    if row.get("firmware_updatable") is None and cd.get("upgradable") is not None:
        row["firmware_updatable"] = bool(cd["upgradable"])
    if row.get("model") in (None, "") and cd.get("model"):
        row["model"] = str(cd["model"])
    if row.get("bandwidth") is None:
        row["bandwidth"] = unifi_core.device_bandwidth(cd)


def _device_row_from_core(
    cd: dict[str, Any], endpoints: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """A full device row from core in-memory data, through _normalize_device
    for shape parity with the API path."""
    raw: dict[str, Any] = {
        "name": cd.get("name"),
        "model": cd.get("model"),
        "ip": cd.get("ip"),
        "mac": cd.get("mac"),
        "state": cd.get("state"),
        "updateAvailable": cd.get("upgradable"),
        "last_seen": cd.get("last_seen"),
    }
    uplink = cd.get("uplink") or {}
    if uplink.get("rx_bytes") is not None or uplink.get("tx_bytes") is not None:
        raw["uplink"] = {
            "rx_bytes": uplink.get("rx_bytes"),
            "tx_bytes": uplink.get("tx_bytes"),
        }
    row = _normalize_device(raw, endpoints)
    row["origin"] = unifi_core.NETWORK_ORIGIN
    return row


def _enrich_wan_from_core(result: dict[str, Any], snap: dict[str, Any]) -> None:
    """Resolve "Internet - Unknown" and "WAN Bandwidth - Unknown" from the
    gateway device the core integration tracks. Only blanks are filled; the
    direct API's own WAN readings always win."""
    gateway = snap.get("gateway")
    if not gateway:
        return
    core_wan = unifi_core.wan_from_gateway(gateway)
    wan = result["wan"]
    for key in ("port", "up", "rx_rate_bps", "tx_rate_bps", "ip"):
        if wan.get(key) is None and core_wan.get(key) is not None:
            wan[key] = core_wan[key]
    # availability is additive: the direct API has no equivalent reading and
    # the frontend ignores payload keys it does not render, so surfacing the
    # controller's own WAN-probe percentage costs nothing.
    if wan.get("availability") is None and core_wan.get("availability") is not None:
        wan["availability"] = core_wan["availability"]
    if result.get("internet_connected") is None:
        if core_wan.get("internet") is not None:
            result["internet_connected"] = core_wan["internet"]
        elif wan.get("up") is not None:
            result["internet_connected"] = wan["up"]
    if result.get("status") == "unknown" and gateway.get("state"):
        offline = str(gateway["state"]).upper() in unifi_core.OFFLINE_DEVICE_STATES
        result["status"] = "offline" if offline else "online"


def _is_online_state(value: Any) -> bool:
    return str(value).upper() in ("CONNECTED", "ONLINE", "TRUE", "1")


def _normalize_camera(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """One Protect device row. The ``id`` is deliberately surfaced so the UI
    can deep-link to the console: {origin}/protect/dashboard/devices/{id}."""
    cam_id = _first(raw, "id", "_id", "deviceId")
    name = _first(raw, "name", "displayName", "modelKey", "model")
    ip = _first(raw, "host", "ip", "ipAddress", "lastSeenIp", "address")
    mac = _first(raw, "mac", "macAddress")

    # VERIFY: isRecording. Protect exposes a boolean on some firmwares and a
    # recordingSettings.mode ("always"/"detections"/"never") on others.
    is_recording: bool | None = None
    rec = _first(raw, "isRecording", "recording")
    if rec is not None:
        is_recording = bool(rec)
    else:
        mode = None
        rs = raw.get("recordingSettings")
        if isinstance(rs, dict):
            mode = _first(rs, "mode")
        if mode is not None:
            is_recording = str(mode).lower() not in ("never", "off", "disabled")

    last_ring = _as_epoch(_first(raw, "lastRing", "last_ring"))

    # VERIFY: channels shape. Each channel typically carries a name and/or a
    # width/height; we surface short labels + a count for the table cell.
    channels: list[str] = []
    channels_raw = raw.get("channels")
    if isinstance(channels_raw, list):
        for ch in channels_raw:
            if not isinstance(ch, dict):
                continue
            label = _first(ch, "name")
            w, h = _first(ch, "width"), _first(ch, "height")
            if not label and w and h:
                label = f"{w}x{h}"
            channels.append(str(label) if label else "channel")

    state = str(_first(raw, "state", "status", default="")).upper() or None
    connected = _first(raw, "isConnected", "connected")
    online = _is_online_state(state) if state else (bool(connected) if connected is not None else None)

    return {
        "id": str(cam_id) if cam_id else None,
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ip": str(ip) if ip else None,
        "mac": str(mac).lower() if mac else None,
        "is_recording": is_recording,
        "last_ring": last_ring,
        "channels": channels,
        "channel_count": len(channels),
        "state": state,
        "online": online,
        # Browser-facing deep link into the Protect console for this device.
        "link": f"{origin}/protect/dashboard/devices/{cam_id}" if cam_id else None,
    }


def _normalize_event(raw: dict[str, Any], origin: str) -> dict[str, Any]:
    """One Protect event / AI smart-detection row."""
    ev_id = _first(raw, "id", "_id")
    etype = _first(raw, "type", "eventType")

    sdt = raw.get("smartDetectTypes")
    if sdt is None:
        sdt = raw.get("smart_detect_types")
    if sdt is None:
        sdt = []
    elif not isinstance(sdt, list):
        sdt = [sdt]
    sdt = [str(s) for s in sdt]

    score = _first(raw, "score", "confidence")
    try:
        score = int(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    start = _as_epoch(_first(raw, "start", "startTime", "timestamp"))
    end = _as_epoch(_first(raw, "end", "endTime"))
    duration = (end - start) if (start is not None and end is not None and end >= start) else None

    camera_id = _first(raw, "camera", "cameraId", "device", "deviceId")

    # thumbnail may be a full URL, or an id/token that needs an authenticated
    # fetch (so it can't be embedded cross-origin). When it's just a token we
    # link to the event's camera page on the console instead of showing a
    # broken <img>.
    thumbnail = _first(raw, "thumbnail", "thumbnailId", "heatmap")
    thumb_link = None
    if thumbnail:
        if str(thumbnail).startswith("http"):
            thumb_link = str(thumbnail)
        elif camera_id and origin:
            thumb_link = f"{origin}/protect/dashboard/devices/{camera_id}"

    # licensePlate can be a bare string, or nested under metadata.
    plate = None
    meta = raw.get("metadata")
    if isinstance(meta, dict):
        lp = meta.get("licensePlate") or meta.get("license_plate")
        if isinstance(lp, dict):
            plate = _first(lp, "name", "value", "plate")
        elif lp:
            plate = str(lp)
    if not plate:
        plate = _first(raw, "licensePlate", "license_plate")

    return {
        "id": str(ev_id) if ev_id else None,
        "type": str(etype) if etype else None,
        "smart_detect_types": sdt,
        "score": score,
        "start": start,
        "end": end,
        "duration": duration,
        "thumbnail": bool(thumbnail),
        "thumbnail_link": thumb_link,
        "license_plate": str(plate) if plate else None,
        "camera": str(camera_id) if camera_id else None,
    }


async def async_protect_status(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """UniFi Protect status for the Network tab: reachable + camera counts,
    the full devices table (with console deep-links), and recent events / AI
    smart detections. Best-effort, never raises; a failure comes back as
    reachable=False with a reason, and the events call failing on its own
    still returns the cameras.

    Like the Network overview, the direct X-API-KEY readings win, and the
    core ``unifiprotect`` integration's in-memory bootstrap fills whatever
    they left blank, most importantly the recent events that many Protect
    firmwares refuse to serve over REST."""
    out: dict[str, Any] = {
        "configured": False,
        "reachable": False,
        "error": None,
        "host": None,
        "camera_count": 0,
        "cameras_online": 0,
        "cameras": [],
        "events": [],
        "events_error": None,
    }
    conn = _protect_conn(store)
    if conn is not None:
        out["configured"] = True
        out["host"] = conn.origin
        await _fill_protect_from_api(hass, conn, out)
    _apply_core_protect_data(hass, out)
    return out


async def _fill_protect_from_api(
    hass: HomeAssistant, conn: _Conn, out: dict[str, Any]
) -> None:
    """The direct-to-console Protect fetch path, mutating ``out`` in place.
    Kept separate so the core in-memory enrichment can run whether or not
    this path succeeded."""
    try:
        # VERIFY: Protect Integration API camera collection path.
        payload = await _get_paginated(hass, conn, "/cameras")
    except UniFiError as err:
        out["error"] = str(err)
        return
    except Exception as err:  # noqa: BLE001
        _LOGGER.exception("Unexpected UniFi Protect error")
        out["error"] = f"Unexpected error: {err}"
        return

    cameras = [_normalize_camera(c, conn.origin) for c in payload]
    out.update(
        {
            "reachable": True,
            "camera_count": len(cameras),
            "cameras_online": sum(1 for c in cameras if c["online"]),
            "cameras": cameras,
        }
    )

    # Events are a separate, non-fatal call. The Protect Integration API
    # doesn't guarantee a REST events list — on many firmwares events are
    # delivered over a websocket subscription (/subscribe/events) rather than
    # a GET, so /events returns 404. Probe the candidate REST paths and, if
    # none respond, explain that honestly instead of showing a raw error.
    now = dt_util.utcnow()
    end_ms = int(now.timestamp() * 1000)
    start_ms = end_ms - 24 * 3600 * 1000  # last 24h
    # VERIFY: events REST path + time-window param names.
    event_paths = (
        f"/events?start={start_ms}&end={end_ms}",
        f"/events?startTime={start_ms}&endTime={end_ms}",
        f"/detections?start={start_ms}&end={end_ms}",
        f"/alarms?start={start_ms}&end={end_ms}",
    )
    tried_bases: list[str] = []
    got: list[dict[str, Any]] | None = None
    saw_non_404 = False
    for path in event_paths:
        base = path.split("?", 1)[0]
        if base not in tried_bases:
            tried_bases.append(base)
        try:
            got = await _get_paginated(hass, conn, path)
            break
        except UniFiError as err:
            if "not found" not in str(err).lower():
                saw_non_404 = True
                out["events_error"] = str(err)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Unexpected UniFi Protect events error")
            saw_non_404 = True
            out["events_error"] = f"Unexpected error: {err}"

    if got is not None:
        events = [_normalize_event(e, conn.origin) for e in got]
        events.sort(key=lambda e: e["start"] or 0, reverse=True)
        out["events"] = events
        out["events_error"] = None
    elif not saw_non_404:
        out["events_error"] = (
            "This Protect Integration API doesn't expose a REST events list "
            f"(tried: {', '.join(tried_bases)}). On this API version events are "
            "delivered over a websocket subscription, which a read-only snapshot "
            "can't consume."
        )


# ---------------------------------------------------------------------------
# Enrichment from the core `unifiprotect` integration's in-memory bootstrap
# ---------------------------------------------------------------------------


def _apply_core_protect_data(hass: HomeAssistant, out: dict[str, Any]) -> None:
    """Fill the Protect status from the core unifiprotect integration's
    in-memory bootstrap: camera details the REST probe missed, and the recent
    events the REST /events endpoint refuses to serve on many firmwares.
    Failure-isolated the same way the Network enrichment is: any surprise in
    the private core objects leaves the API-only payload untouched."""
    try:
        snap = unifi_core.protect_snapshot(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Core unifiprotect snapshot unavailable", exc_info=True)
        return
    if not snap.get("available"):
        return
    try:
        origin = out.get("host") or snap.get("origin") or ""
        if out["cameras"]:
            by_id = {c["id"]: c for c in out["cameras"] if c.get("id")}
            by_mac = {
                unifi_core.normalize_mac(c.get("mac")): c
                for c in out["cameras"]
                if c.get("mac")
            }
            for cam in snap["cameras"]:
                row = by_id.get(cam["id"]) or by_mac.get(cam.get("mac"))
                if row is not None:
                    _fill_camera_row_from_core(row, cam, origin)
        else:
            out["cameras"] = [_camera_row_from_core(c, origin) for c in snap["cameras"]]
        out["camera_count"] = len(out["cameras"])
        out["cameras_online"] = sum(1 for c in out["cameras"] if c["online"])

        if not out["events"]:
            now_ts = int(dt_util.utcnow().timestamp())
            cutoff = now_ts - 24 * 3600
            # The panel's events card is captioned "last 24h", so the
            # bootstrap's recent-events buffer is filtered to that window.
            events = [
                _event_row_from_core(e, origin)
                for e in snap["events"]
                if e.get("start") is not None and e["start"] >= cutoff
            ]
            events.sort(key=lambda e: e["start"] or 0, reverse=True)
            out["events"] = events
            # The core bootstrap is now the events source, so a message about
            # the REST probe failing would be stale and misleading.
            out["events_error"] = None

        # Data straight out of core memory is real even when the direct API
        # is unconfigured or down, so the panel is told it can render it.
        if out["cameras"] or out["events"]:
            out["configured"] = True
            out["reachable"] = True
            if not out.get("host") and snap.get("origin"):
                out["host"] = snap["origin"]
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Core unifiprotect enrichment failed", exc_info=True)


def _camera_row_from_core(cam: dict[str, Any], origin: str) -> dict[str, Any]:
    """A full camera row from the core bootstrap, through _normalize_camera
    for shape parity with the API path."""
    row = _normalize_camera(cam, origin)
    if not origin:
        # Without a known console origin the deep link would be relative and
        # point at the Home Assistant host instead of the Protect console.
        row["link"] = None
    row["origin"] = unifi_core.PROTECT_ORIGIN
    return row


def _fill_camera_row_from_core(
    row: dict[str, Any], cam: dict[str, Any], origin: str
) -> None:
    """Fill one REST camera row's blanks from its bootstrap twin. The
    bootstrap dict is normalized through the same pipeline first so the fill
    values arrive in payload form, then only genuinely missing fields are
    taken from it; REST values always win."""
    core_row = _camera_row_from_core(cam, origin)
    for key in ("ip", "is_recording", "last_ring", "state", "online"):
        if row.get(key) is None and core_row.get(key) is not None:
            row[key] = core_row[key]
    if not row.get("channels") and core_row.get("channels"):
        row["channels"] = core_row["channels"]
        row["channel_count"] = core_row["channel_count"]
    if row.get("name") in (None, "unknown") and core_row.get("name") not in (None, "unknown"):
        row["name"] = core_row["name"]


def _event_row_from_core(event: dict[str, Any], origin: str) -> dict[str, Any]:
    """One event row from the core bootstrap, through _normalize_event. The
    normalizer is fed the camera id because the console deep link needs it;
    the payload's camera field is then swapped to the resolved camera name,
    which is what a human reading the events table needs."""
    row = _normalize_event(event, origin)
    if not origin:
        row["thumbnail_link"] = None
    if event.get("camera_name"):
        row["camera"] = str(event["camera_name"])
    row["origin"] = unifi_core.PROTECT_ORIGIN
    return row
