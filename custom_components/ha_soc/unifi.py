"""UniFi Network / Protect direct-to-console read-only client.

Talks to the console over the LAN with an ``X-API-KEY`` header and backs
the panel's Network tab. Every normalized field is resolved from a list of
candidate keys via :func:`_first`, because the Integration API and the
legacy controller API name fields differently; anything absent degrades to
``None`` rather than a guess. See docs/UNIFI-LOCAL-API-CONTRACT.md.
"""
from __future__ import annotations

import asyncio
import ipaddress
import json
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
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
# Outer ceiling for the whole overview; per-request timeouts alone cannot bound the fan-out.
_OVERVIEW_TIMEOUT_SECONDS = 60
# Pagination bounds so a hostile or huge controller cannot loop a refresh forever.
_PAGE_LIMIT = 200
_MAX_PAGES = 15
# The declared Content-Length is checked first and the actual read is capped regardless.
_MAX_BODY_BYTES = 8 * 1024 * 1024
# Caps the per-device detail fan-out for a huge install.
_MAX_DEVICE_DETAILS = 50
# Local Integration API contract only; do not add private-controller fallback paths.
_ACL_ENDPOINT_SUFFIXES = ("acl-rules",)

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

_FAILING_STATES = frozenset(
    {
        ConfigEntryState.SETUP_ERROR,
        ConfigEntryState.SETUP_RETRY,
        ConfigEntryState.MIGRATION_ERROR,
        ConfigEntryState.FAILED_UNLOAD,
    }
)


class UniFiError(Exception):
    """Any failure talking to a UniFi console - surfaced to the UI as a
    reachable=False overview with a human-readable reason, never a raw stack."""


def _first(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """First present, non-empty value among candidate keys."""
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


@dataclass(frozen=True, repr=False)
class _Conn:
    """A resolved connection to one UniFi app (Network or Protect).

    Short-lived by design: built per snapshot and dropped. The generated
    dataclass repr would print api_key verbatim, hence the replacement below.
    """

    host: str
    api_key: str
    verify_ssl: bool
    base_path: str

    def __repr__(self) -> str:
        return (
            f"_Conn(host={self.host!r}, api_key='[redacted]', "
            f"verify_ssl={self.verify_ssl!r}, base_path={self.base_path!r})"
        )

    @property
    def origin(self) -> str:
        # Scheme+authority only; host may be "10.0.0.1", "10.0.0.1:443", or "https://10.0.0.1".
        host = self.host.strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        parsed = urlparse(host)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def base_url(self) -> str:
        # The path is a constant appended here, never taken from user input.
        return f"{self.origin}{self.base_path}"


def _validate_host(host: str) -> None:
    """Reject a configured host whose URL form carries anything beyond a
    scheme, address, and port. Raises UniFiError; a bare host or host:port
    passes untouched."""
    if "://" not in host:
        candidate = f"https://{host}"
    else:
        candidate = host
    try:
        parsed = urlparse(candidate)
    except ValueError as err:
        raise UniFiError(f"The configured UniFi host is not a valid URL: {err}") from err
    if "://" in host and parsed.scheme not in ("http", "https"):
        raise UniFiError(
            f"The configured UniFi host uses the unsupported scheme "
            f"{parsed.scheme!r}; only http and https are allowed."
        )
    if parsed.username is not None or parsed.password is not None:
        raise UniFiError(
            "The configured UniFi host contains a username/password part; "
            "remove it and configure the API key instead."
        )
    if not parsed.hostname:
        raise UniFiError("The configured UniFi host has no host name.")


async def _network_conn(store: HaSocData, secrets: HaSocSecretStore) -> _Conn | None:
    """Build a short-lived Network connection, fetching the API key from the
    private secret store at use time. None when unconfigured; raises
    UniFiError for a configured but invalid host."""
    s = store.settings
    host = (s.get(CONF_UNIFI_NETWORK_HOST) or "").strip()
    key = (await secrets.async_get(CONF_UNIFI_NETWORK_API_KEY) or "").strip()
    if not host or not key:
        return None
    _validate_host(host)
    return _Conn(
        host=host,
        api_key=key,
        verify_ssl=bool(s.get(CONF_UNIFI_NETWORK_VERIFY_SSL, DEFAULT_UNIFI_VERIFY_SSL)),
        base_path=UNIFI_NETWORK_API_PATH,
    )


async def _protect_conn(store: HaSocData, secrets: HaSocSecretStore) -> _Conn | None:
    """Build a short-lived Protect connection, fetching the API key from the
    private secret store at use time. None when unconfigured; raises
    UniFiError for a configured but invalid host."""
    s = store.settings
    host = (s.get(CONF_UNIFI_PROTECT_HOST) or "").strip()
    key = (await secrets.async_get(CONF_UNIFI_PROTECT_API_KEY) or "").strip()
    if not host or not key:
        return None
    _validate_host(host)
    return _Conn(
        host=host,
        api_key=key,
        verify_ssl=bool(s.get(CONF_UNIFI_PROTECT_VERIFY_SSL, DEFAULT_UNIFI_VERIFY_SSL)),
        base_path=UNIFI_PROTECT_API_PATH,
    )


async def _get(hass: HomeAssistant, conn: _Conn, path: str) -> Any:
    """One authenticated GET. Raises UniFiError with a friendly reason on any
    transport/HTTP/decode failure - the caller turns that into reachable=False.

    Redirects are never followed and the body is bounded to _MAX_BODY_BYTES."""
    session = async_get_clientsession(hass, verify_ssl=conn.verify_ssl)
    url = f"{conn.base_url}{path}"
    headers = {"X-API-KEY": conn.api_key, "Accept": "application/json"}
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(url, headers=headers, allow_redirects=False) as resp:
                if 300 <= resp.status < 400:
                    raise UniFiError(
                        "The console returned an unexpected redirect; refusing to follow it."
                    )
                if resp.status in (401, 403):
                    raise UniFiError("Authentication failed — check the API key.")
                if resp.status == 404:
                    raise UniFiError(f"Endpoint not found ({path}).")
                resp.raise_for_status()
                if (
                    resp.content_length is not None
                    and resp.content_length > _MAX_BODY_BYTES
                ):
                    raise UniFiError("The console response is too large to process.")
                raw = await resp.content.read(_MAX_BODY_BYTES + 1)
                if len(raw) > _MAX_BODY_BYTES:
                    raise UniFiError("The console response is too large to process.")
                return json.loads(raw)
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
    # Integration API uses "id"; legacy uses "name"/"_id".
    site_id = _first(site, "id", "_id", "siteId", "name")
    if not site_id:
        raise UniFiError("Could not determine the UniFi site id.")
    return str(site_id)


def _hosts_from_value(value: Any) -> list[str]:
    """Bare host/IP strings out of one config-entry value. Never raises:
    urlparse raises ValueError on malformed authorities, and another
    integration's garbage host field must degrade to "no hosts"."""
    if not isinstance(value, str) or not value.strip():
        return []
    v = value.strip()
    try:
        if "://" in v:
            parsed = urlparse(v)
            hostname = parsed.hostname
            return [hostname.lower()] if hostname else []
        # Strip a trailing :port; bare IPv6 is matched separately on the client's own ipv6 field.
        host = v.split("/", 1)[0]
        if host.count(":") == 1:  # host:port, not IPv6
            host = host.split(":", 1)[0]
        return [host.lower()] if host else []
    except ValueError:
        return []


def _integration_endpoints(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Index of ``host-string -> integration descriptor`` across every config
    entry, so a UniFi client/device whose IP matches can be annotated with
    that integration's live health.
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
            # A failing integration wins over a healthy one when two entries share a host.
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


def _as_epoch(value: Any) -> int | None:
    """Best-effort epoch-seconds from a numeric epoch (s or ms) or an ISO
    string. Returns None when it can't be parsed (the UI shows a dash)."""
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
    # ipv6Addresses is a list on the Integration client object; other shapes use a single string.
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
    """Cumulative rx/tx bytes for a client/device, searched at the top level
    and under the ``statistics`` containers."""
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
    """Resolve a client's SSID: carried directly, or joined through
    broadcast_map from the /wifi/broadcasts collection."""
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
    # VLAN is top-level on some firmwares and nested under `access` on others.
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
    # Fall back to connectedAt, which is what the Integration API actually returns for a client.
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

    fw_updatable = _first(raw, "firmwareUpdatable", "updateAvailable", "update_available")
    if fw_updatable is None:
        fw = raw.get("firmware")
        if isinstance(fw, dict):
            fw_updatable = _first(fw, "updatable", "updateAvailable")
    firmware_updatable = bool(fw_updatable) if fw_updatable is not None else None

    last_seen = _as_epoch(
        _first(raw, "lastSeen", "last_seen", "lastHeartbeatAt", "startupTimestamp")
    )
    if last_seen is None:
        stats = raw.get("statistics")
        if isinstance(stats, dict):
            last_seen = _as_epoch(_first(stats, "lastHeartbeatAt", "lastSeen"))

    return {
        "name": str(name) if name else (str(mac) if mac else "unknown"),
        "ipv4": str(ipv4) if ipv4 else None,
        "ipv6": ipv6,
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


def _gateway_by_role(raw: dict[str, Any]) -> bool:
    """The strong signal: the device's own role/type field says gateway."""
    role = str(_first(raw, "type", "deviceType", "role", default="")).lower()
    return role in ("gateway", "console", "ugw")


def _gateway_by_name_tokens(raw: dict[str, Any]) -> bool:
    """The weak fallback: a known gateway marker in the model/name blob. Runs
    only when no device declared the role."""
    blob = " ".join(
        str(_first(raw, k, default="")).lower()
        for k in ("type", "model", "shortname", "name", "deviceType", "role")
    )
    return any(tok in blob for tok in _GATEWAY_TOKENS)


def _is_gateway(raw: dict[str, Any]) -> bool:
    return _gateway_by_role(raw) or _gateway_by_name_tokens(raw)


def _select_gateway(devices_raw: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Choose THE gateway: a declared role wins; name tokens are consulted only when no device declares one."""
    for raw in devices_raw:
        if _gateway_by_role(raw):
            return raw
    for raw in devices_raw:
        if _gateway_by_name_tokens(raw):
            return raw
    return None


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
    field degrades to None when the console doesn't expose it.
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


async def _fetch_broadcast_map(
    hass: HomeAssistant, conn: _Conn, site_id: str
) -> dict[str, str]:
    """{broadcast_id: ssid_name} from /wifi/broadcasts. Best-effort - {} when
    the console cannot serve it. Only UniFiError is swallowed; anything else
    is a programming error that must surface."""
    try:
        rows = await _get_paginated(hass, conn, f"/sites/{site_id}/wifi/broadcasts")
    except UniFiError:
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
    """Enrich devices from the two documented per-device routes; each request
    is independent and non-fatal."""

    async def _one(dev: dict[str, Any]) -> dict[str, Any]:
        did = _first(dev, "id", "_id", "deviceId")
        if not did:
            return dev
        merged = dict(dev)
        try:
            detail = await _get(hass, conn, f"/sites/{site_id}/devices/{did}")
        except UniFiError:
            detail = None
        if isinstance(detail, dict):
            inner = detail.get("data")
            if isinstance(inner, dict):
                detail = inner
            if isinstance(detail, dict):
                merged.update(detail)  # detail wins

        try:
            statistics = await _get(
                hass,
                conn,
                f"/sites/{site_id}/devices/{did}/statistics/latest",
            )
        except UniFiError:
            statistics = None
        if isinstance(statistics, dict):
            inner = statistics.get("data")
            if isinstance(inner, dict):
                statistics = inner
            if isinstance(statistics, dict):
                merged["statistics"] = statistics
        return merged

    head = devices[:_MAX_DEVICE_DETAILS]
    enriched = await asyncio.gather(*[_one(d) for d in head])
    return list(enriched) + devices[_MAX_DEVICE_DETAILS:]


async def _fetch_network_map(
    hass: HomeAssistant, conn: _Conn, site_id: str
) -> dict[str, str]:
    """{network_id: display_name} so an ACL rule that references networks by
    id can be shown by name. Best-effort - {} if the endpoint is absent."""
    for suffix in ("networks",):
        try:
            rows = await _get_paginated(hass, conn, f"/sites/{site_id}/{suffix}")
        except UniFiError:
            # Only UniFiError is expected (absent endpoint); anything else is a bug that must surface upstream.
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


def _resolve_network_refs(refs: list[Any], network_map: dict[str, str]) -> list[str]:
    """Network id/name/object references resolved to display names via
    network_map (id -> "Name (VLAN x)"), falling back to the raw reference
    stringified when it isn't a known id. Dedupes, preserves order."""
    out: list[str] = []
    for ref in refs:
        if isinstance(ref, dict):
            rid = _first(ref, "id", "_id")
            rname = _first(ref, "name", "displayName")
            out.append(network_map.get(str(rid), str(rname) if rname else str(rid)))
        elif ref not in (None, ""):
            out.append(network_map.get(str(ref), str(ref)))
    return list(dict.fromkeys(out))


def _port_list(value: Any) -> list[int]:
    """A filter's port entries as a sorted list of ints. The verified spec
    sends plain ints; a string port or "start-end" range is tolerated
    defensively."""
    if not isinstance(value, list):
        return []
    out: set[int] = set()
    for item in value:
        if isinstance(item, bool):
            continue
        if isinstance(item, (int, float)):
            out.add(int(item))
        elif isinstance(item, str) and item.strip().isdigit():
            out.add(int(item))
        elif isinstance(item, str) and "-" in item:
            # Defensive only; the verified schema never sends this shape.
            lo, _, hi = item.partition("-")
            if lo.strip().isdigit() and hi.strip().isdigit():
                out.update(range(int(lo), int(hi) + 1))
    return sorted(out)


def _normalize_acl_filter(raw: Any, network_map: dict[str, str]) -> dict[str, Any]:
    """One side (source or destination) of an ACL rule.

    Reading all four possible fields unconditionally is correct: each type
    variant only ever populates its own. Never raises; a non-dict filter
    normalizes to an empty-but-shaped record."""
    if not isinstance(raw, dict):
        return {
            "match_type": None,
            "ip_or_subnets": [],
            "ports": [],
            "networks": [],
            "macs": [],
        }
    ip_or_subnets = raw.get("ipAddressesOrSubnets")
    macs = raw.get("macAddresses")
    return {
        "match_type": str(_first(raw, "type", "matchType", default="")) or None,
        "ip_or_subnets": [str(v) for v in ip_or_subnets] if isinstance(ip_or_subnets, list) else [],
        "ports": _port_list(raw.get("portFilter")),
        "networks": _resolve_network_refs(
            raw.get("networkIds") if isinstance(raw.get("networkIds"), list) else [], network_map
        ),
        "macs": [str(v) for v in macs] if isinstance(macs, list) else [],
    }


def _normalize_acl_rule(
    raw: dict[str, Any], index: int, network_map: dict[str, str]
) -> dict[str, Any]:
    """One ACL rule, order-preserving, matching the network_v10.4.57 OpenAPI
    spec; see docs/UNIFI-LOCAL-API-CONTRACT.md for the field semantics.
    """
    order = _first(raw, "index", "ruleIndex", "order", "ruleOrder", "sequence")
    try:
        order = int(order) if order is not None else index
    except (TypeError, ValueError):
        order = index

    rule_type = raw.get("type")  # "IPV4" | "MAC"

    source = _normalize_acl_filter(raw.get("sourceFilter"), network_map)
    destination = _normalize_acl_filter(raw.get("destinationFilter"), network_map)

    # Legacy flat source/destination strings carry no port/network detail but still earn a row.
    if raw.get("sourceFilter") is None:
        legacy_src = _first(raw, "source", "src", "sourceZone")
        if legacy_src:
            source["ip_or_subnets"] = [str(legacy_src)]
    if raw.get("destinationFilter") is None:
        legacy_dst = _first(raw, "destination", "dst", "destinationZone")
        if legacy_dst:
            destination["ip_or_subnets"] = [str(legacy_dst)]

    protocol_filter = raw.get("protocolFilter")
    if isinstance(protocol_filter, list) and protocol_filter:
        protocols = [str(p) for p in protocol_filter]
    else:
        legacy_proto = _first(raw, "protocol", "protocolMatch")
        protocols = [str(legacy_proto).upper()] if legacy_proto else []

    # MAC-type rules scope their network via the rule-level networkIdFilter, not a filter side.
    rule_network_refs: list[Any] = []
    v = raw.get("networkIdFilter")
    if v not in (None, ""):
        rule_network_refs.append(v)
    networks = list(
        dict.fromkeys(
            _resolve_network_refs(rule_network_refs, network_map)
            + source["networks"]
            + destination["networks"]
        )
    )
    ports = sorted(set(source["ports"]) | set(destination["ports"]))

    enabled = _first(raw, "enabled", "isEnabled")
    metadata = raw.get("metadata")
    origin = metadata.get("origin") if isinstance(metadata, dict) else None
    return {
        "order": order,
        "id": str(_first(raw, "id", "_id", default="")) or None,
        "name": str(_first(raw, "name", "description", "displayName", default="")) or None,
        "rule_type": str(rule_type) if rule_type else None,
        "action": (str(_first(raw, "action", "policy", "ruleAction", default="")) or None),
        "enabled": bool(enabled) if enabled is not None else None,
        "origin": origin,
        "custom": origin == "USER_DEFINED" if origin is not None else None,
        "protocols": protocols,
        "networks": networks,
        "ports": ports,
        "source": source,
        "destination": destination,
    }


async def _fetch_acl_rules(
    hass: HomeAssistant, conn: _Conn, site_id: str, network_map: dict[str, str]
) -> dict[str, Any]:
    """Probe the candidate ACL endpoints and return the first that responds;
    `available` False with the endpoints tried when none do, never a
    fabricated ruleset."""
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


def _normalize_ip_matching(item: dict[str, Any]) -> str | None:
    """One 'IP matching' entry (IP_ADDRESS / SUBNET / IP_ADDRESS_RANGE)."""
    t = item.get("type")
    if t in ("IP_ADDRESS", "SUBNET"):
        v = item.get("value")
        return str(v) if v not in (None, "") else None
    if t == "IP_ADDRESS_RANGE":
        start, stop = item.get("start"), item.get("stop")
        if start and stop:
            return f"{start}-{stop}"
    return None


def _normalize_port_matching(item: dict[str, Any]) -> str | None:
    """One 'Port matching' entry, kept as a string because it can be a range."""
    t = item.get("type")
    if t == "PORT_NUMBER":
        v = item.get("value")
        return str(v) if v is not None else None
    if t == "PORT_NUMBER_RANGE":
        start, stop = item.get("start"), item.get("stop")
        if start is not None and stop is not None:
            return f"{start}-{stop}"
    return None


def _normalize_firewall_port_filter(pf: Any) -> dict[str, Any]:
    """A Firewall Policy 'port filter', standalone or nested inside another
    filter. A TRAFFIC_MATCHING_LIST reference is surfaced as ``from_list``."""
    if not isinstance(pf, dict):
        return {"ports": [], "from_list": False}
    if pf.get("type") == "TRAFFIC_MATCHING_LIST":
        return {"ports": [], "from_list": True}
    items = pf.get("items") if isinstance(pf.get("items"), list) else []
    ports = [p for p in (_normalize_port_matching(i) for i in items if isinstance(i, dict)) if p]
    return {"ports": ports, "from_list": False}


def _normalize_firewall_protocol(scope: Any) -> dict[str, Any]:
    """{'ip_version': 'IPV4'|'IPV6'|'IPV4_AND_IPV6'|None,
    'protocol': readable string or None (None = matches all protocols)}."""
    if not isinstance(scope, dict):
        return {"ip_version": None, "protocol": None}
    ip_version = scope.get("ipVersion")
    pf = scope.get("protocolFilter")
    if not isinstance(pf, dict):
        return {"ip_version": ip_version, "protocol": None}
    ptype = pf.get("type")
    if ptype in ("NAMED_PROTOCOL", "PRESET"):
        # "name" is the readable protocol string for both NAMED_PROTOCOL and PRESET.
        name = pf.get("name")
        return {"ip_version": ip_version, "protocol": str(name) if name else None}
    if ptype == "PROTOCOL_NUMBER":
        num = pf.get("protocolNumber")
        return {"ip_version": ip_version, "protocol": f"protocol {num}" if num is not None else None}
    return {"ip_version": ip_version, "protocol": None}


def _normalize_firewall_traffic_filter(raw: Any, network_map: dict[str, str]) -> dict[str, Any]:
    """One side (source or destination) of a Firewall Policy's traffic filter.
    Unverified filter types are surfaced by ``filter_type`` alone. ``zone``
    is filled in by the caller from the enclosing object's zoneId."""
    filter_type = raw.get("type") if isinstance(raw, dict) else None
    networks: list[str] = []
    ip_or_subnets: list[str] = []
    macs: list[str] = []
    domains: list[str] = []
    applications: list[int] = []
    application_categories: list[int] = []
    match_opposite: bool | None = None

    if isinstance(raw, dict):
        net_filter = raw.get("networkFilter")
        if isinstance(net_filter, dict):
            ids = net_filter.get("networkIds")
            networks = _resolve_network_refs(ids if isinstance(ids, list) else [], network_map)
            match_opposite = net_filter.get("matchOpposite")

        ip_filter = raw.get("ipAddressFilter")
        if isinstance(ip_filter, dict):
            match_opposite = ip_filter.get("matchOpposite")
            items = ip_filter.get("items") if isinstance(ip_filter.get("items"), list) else []
            ip_or_subnets = [
                v for v in (_normalize_ip_matching(i) for i in items if isinstance(i, dict)) if v
            ]

        mac_filter = raw.get("macAddressFilter")
        if isinstance(mac_filter, dict):
            # The primary filter (filter_type == MAC_ADDRESS): a list.
            addrs = mac_filter.get("macAddresses")
            macs = [str(m) for m in addrs] if isinstance(addrs, list) else []
        elif isinstance(mac_filter, str):
            # An extra single-MAC constraint on a NETWORK/IP_ADDRESS/IPV6_IID filter, not the primary MAC filter.
            macs = [mac_filter]

        dom_filter = raw.get("domainFilter")
        if isinstance(dom_filter, dict) and isinstance(dom_filter.get("domains"), list):
            domains = [str(v) for v in dom_filter["domains"]]

        app_filter = raw.get("applicationFilter")
        if isinstance(app_filter, dict) and isinstance(app_filter.get("applicationIds"), list):
            applications = list(app_filter["applicationIds"])

        cat_filter = raw.get("applicationCategoryFilter")
        if isinstance(cat_filter, dict) and isinstance(cat_filter.get("applicationCategoryIds"), list):
            application_categories = list(cat_filter["applicationCategoryIds"])

    port_info = _normalize_firewall_port_filter(raw.get("portFilter") if isinstance(raw, dict) else None)

    return {
        "zone": None,  # filled in by the caller
        "filter_type": filter_type,
        "networks": networks,
        "ip_or_subnets": ip_or_subnets,
        "macs": macs,
        "domains": domains,
        "applications": applications,
        "application_categories": application_categories,
        "match_opposite": match_opposite,
        "ports": port_info["ports"],
        "ports_from_list": port_info["from_list"],
    }


def _normalize_firewall_policy(
    raw: dict[str, Any], index: int, network_map: dict[str, str], zone_name_map: dict[str, str]
) -> dict[str, Any]:
    """One Firewall Policy, order-preserving, matching the verified schema."""
    order = raw.get("index")
    try:
        order = int(order) if order is not None else index
    except (TypeError, ValueError):
        order = index

    action_obj = raw.get("action")
    action = action_obj.get("type") if isinstance(action_obj, dict) else None
    # ALLOW-only and required there; None for BLOCK/REJECT where the field does not apply.
    allow_return_traffic = (
        action_obj.get("allowReturnTraffic") if isinstance(action_obj, dict) and action == "ALLOW" else None
    )

    source_raw = raw.get("source") if isinstance(raw.get("source"), dict) else {}
    destination_raw = raw.get("destination") if isinstance(raw.get("destination"), dict) else {}
    source = _normalize_firewall_traffic_filter(source_raw.get("trafficFilter"), network_map)
    destination = _normalize_firewall_traffic_filter(destination_raw.get("trafficFilter"), network_map)
    source["zone"] = zone_name_map.get(str(source_raw.get("zoneId")))
    destination["zone"] = zone_name_map.get(str(destination_raw.get("zoneId")))

    proto = _normalize_firewall_protocol(raw.get("ipProtocolScope"))
    networks = list(dict.fromkeys(source["networks"] + destination["networks"]))

    def _port_sort_key(p: str) -> tuple[int, Any]:
        head = p.split("-", 1)[0]
        return (0, int(head)) if head.isdigit() else (1, p)

    ports = sorted(set(source["ports"]) | set(destination["ports"]), key=_port_sort_key)

    enabled = raw.get("enabled")
    metadata = raw.get("metadata")
    origin = metadata.get("origin") if isinstance(metadata, dict) else None
    return {
        "order": order,
        "id": str(raw.get("id") or "") or None,
        "name": str(raw.get("name") or "") or None,
        "description": raw.get("description"),
        "enabled": bool(enabled) if enabled is not None else None,
        "action": action,
        "allow_return_traffic": allow_return_traffic,
        "origin": origin,
        "custom": origin == "USER_DEFINED" if origin is not None else None,
        "logging_enabled": raw.get("loggingEnabled"),
        "ip_version": proto["ip_version"],
        "protocol": proto["protocol"],
        "connection_state_filter": raw.get("connectionStateFilter"),
        "scheduled": raw.get("schedule") is not None,
        "networks": networks,
        "ports": ports,
        "source": source,
        "destination": destination,
    }


async def _fetch_firewall_zones(
    hass: HomeAssistant, conn: _Conn, site_id: str, network_map: dict[str, str]
) -> list[dict[str, Any]]:
    """[{id, name, networks}], best-effort; [] if the endpoint is absent."""
    try:
        rows = await _get_paginated(hass, conn, f"/sites/{site_id}/firewall/zones")
    except UniFiError:
        return []
    out: list[dict[str, Any]] = []
    for z in rows:
        zid = z.get("id")
        if not zid:
            continue
        net_ids = z.get("networkIds")
        out.append(
            {
                "id": str(zid),
                "name": str(z.get("name") or zid),
                "networks": _resolve_network_refs(
                    net_ids if isinstance(net_ids, list) else [], network_map
                ),
            }
        )
    return out


async def _fetch_firewall_policies(
    hass: HomeAssistant, conn: _Conn, site_id: str, network_map: dict[str, str]
) -> dict[str, Any]:
    """Firewall Policies, a resource separate from ACL Rules. Never probes
    candidate paths: the endpoint is confirmed, so a failure here is real."""
    result: dict[str, Any] = {"available": False, "error": None, "rules": [], "zones": []}
    zones = await _fetch_firewall_zones(hass, conn, site_id, network_map)
    result["zones"] = zones
    zone_name_map = {z["id"]: z["name"] for z in zones}
    try:
        rows = await _get_paginated(hass, conn, f"/sites/{site_id}/firewall/policies")
    except UniFiError as err:
        result["error"] = str(err)
        return result
    except Exception as err:  # noqa: BLE001
        result["error"] = f"Unexpected error: {err}"
        return result
    rules = [_normalize_firewall_policy(r, i, network_map, zone_name_map) for i, r in enumerate(rows)]
    rules.sort(key=lambda r: r["order"])
    result["available"] = True
    result["rules"] = rules
    return result


def _ip_in_any(ip_str: str, candidates: list[str]) -> bool:
    """Whether ip_str matches any candidate exactly or falls inside a CIDR
    candidate. Never raises: a non-IP candidate is simply not a match."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for candidate in candidates:
        if candidate == ip_str:
            return True
        try:
            if ip in ipaddress.ip_network(candidate, strict=False):
                return True
        except ValueError:
            continue
    return False


def _server_ip_addresses(open_ports: list[dict[str, Any]]) -> list[str]:
    """The HA server's own real LAN IP(s) as reported by the Probe add-on;
    never 0.0.0.0 or loopback."""
    out: set[str] = set()
    for p in open_ports:
        addr = p.get("address")
        if not addr or addr in ("0.0.0.0", "::", "127.0.0.1", "::1"):
            continue
        out.add(str(addr))
    return sorted(out)


def _port_in_dest_list(port: Any, dest_ports: list[Any]) -> bool:
    """Whether ``port`` is matched by a destination's port list, which holds
    ints (ACL) or strings that may be a range (Firewall Policy)."""
    for entry in dest_ports:
        if isinstance(entry, bool):
            continue
        if isinstance(entry, int) and entry == port:
            return True
        if isinstance(entry, str):
            if "-" in entry:
                lo, _, hi = entry.partition("-")
                if lo.strip().isdigit() and hi.strip().isdigit() and int(lo) <= port <= int(hi):
                    return True
            elif entry.strip().isdigit() and int(entry) == port:
                return True
    return False


def correlate_server_ports_with_rules(
    open_ports: list[dict[str, Any]] | None,
    acl_rules: list[dict[str, Any]],
    firewall_policies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cross-reference the HA server's own listening ports (from the Probe
    add-on) against both UniFi rule sets, ACL Rules and Firewall Policies.

    Conservative: a rule covers a port only when its destination names the
    server by IP/CIDR and its port list is empty or includes the port;
    network-scoped rules are reported separately as "network_scoped", and
    "uncovered" never means reachable from everywhere.
    """
    server_ips = _server_ip_addresses(open_ports or [])
    if not server_ips:
        return {"available": False, "server_ips": [], "ports": []}

    rule_sets = [("ACL", r) for r in acl_rules] + [("Policy", r) for r in (firewall_policies or [])]
    enabled_rules = [(kind, r) for kind, r in rule_sets if r.get("enabled") is not False]
    out_ports: list[dict[str, Any]] = []
    for p in open_ports or []:
        addr = p.get("address")
        if not addr or addr in ("0.0.0.0", "::", "127.0.0.1", "::1"):
            continue
        port = p.get("port")
        matching: list[str] = []
        network_scoped: list[str] = []
        for kind, rule in enabled_rules:
            dest = rule.get("destination") or {}
            if dest.get("ports") and not _port_in_dest_list(port, dest["ports"]):
                continue
            rule_label = rule.get("name") or rule.get("id") or f"rule {rule.get('order')}"
            label = f"{kind}: {rule_label}"
            if dest.get("ip_or_subnets") and _ip_in_any(str(addr), dest["ip_or_subnets"]):
                matching.append(label)
            elif dest.get("networks"):
                network_scoped.append(label)
        out_ports.append(
            {
                "port": port,
                "proto": p.get("proto"),
                "address": addr,
                "process": p.get("process"),
                "covered_by": matching,
                "network_scoped_by": network_scoped,
                "status": "covered" if matching else ("network_scoped" if network_scoped else "uncovered"),
            }
        )
    return {"available": True, "server_ips": server_ips, "ports": out_ports}


async def async_network_overview(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Network tab renders in one snapshot: status, WAN, the
    clients table, the network-devices table, and the ACL-rules audit report,
    plus a compact Protect status. Never raises: a connection problem comes
    back as reachable=False with a human-readable ``error``.

    The direct API is fetched first and wins; the core ``unifi`` integration's
    in-memory state fills the blanks. The whole snapshot runs under
    _OVERVIEW_TIMEOUT_SECONDS and reports an error rather than raising.
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
        "firewall_policies": {"available": False, "error": None, "rules": [], "zones": []},
        "server_ports": {"available": False, "server_ips": [], "ports": []},
        "failing_endpoint_count": 0,
        "generated_at": dt_util.utcnow().isoformat(),
        "protect": {"configured": False, "reachable": False, "error": None},
    }

    try:
        async with asyncio.timeout(_OVERVIEW_TIMEOUT_SECONDS):
            result["protect"] = await async_protect_status(hass, store, secrets)

            endpoints = _integration_endpoints(hass)
            now_ts = int(dt_util.utcnow().timestamp())

            # Core snapshot first so the API path can borrow its WLAN and network maps as fallbacks.
            core_snap = _core_network_snapshot(hass)

            # The connection (and API key) lives only for this snapshot; an invalid host raises UniFiError.
            try:
                conn = await _network_conn(store, secrets)
            except UniFiError as err:
                result["configured"] = True
                result["error"] = str(err)
                conn = None
            if conn is not None:
                result["configured"] = True
                await _fill_network_from_api(hass, conn, result, endpoints, now_ts, core_snap)

            _apply_core_network_data(result, core_snap, endpoints, now_ts)

            host_probe = store.data.get("host_probe") or {}
            result["server_ports"] = correlate_server_ports_with_rules(
                host_probe.get("open_ports"),
                result["acl"]["rules"],
                result["firewall_policies"]["rules"],
            )
    except asyncio.TimeoutError:
        result["error"] = (
            f"The network snapshot did not complete within "
            f"{_OVERVIEW_TIMEOUT_SECONDS} seconds; partial data shown."
        )
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

    # All best-effort; when a console endpoint returns nothing the core unifi inventory fills the map.
    broadcast_map = await _fetch_broadcast_map(hass, conn, site_id)
    if not broadcast_map and core_snap is not None:
        broadcast_map = unifi_core.wlan_ssid_map(core_snap)
    devices_raw = await _fetch_device_details(hass, conn, site_id, devices_raw)
    network_map = await _fetch_network_map(hass, conn, site_id)
    if not network_map and core_snap is not None:
        network_map = unifi_core.network_name_map(core_snap["networks"])
    result["acl"] = await _fetch_acl_rules(hass, conn, site_id, network_map)
    result["firewall_policies"] = await _fetch_firewall_policies(hass, conn, site_id, network_map)

    clients = [_normalize_client(r, endpoints, broadcast_map, now_ts) for r in clients_raw]
    devices = [_normalize_device(r, endpoints) for r in devices_raw]

    gateway = _select_gateway(devices_raw)
    wan = _derive_wan(gateway)

    gateway_online = None
    if gateway is not None:
        gstate = str(_first(gateway, "state", "status", default="")).upper()
        if gstate in ("OFFLINE", "DISCONNECTED", "0", "PENDING_ADOPTION"):
            gateway_online = False
        else:
            # A listed gateway not explicitly offline counts as online when no WAN up/down flag is exposed.
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
        # Core-memory rows are real data even when the direct API is down; any API error string stays.
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
    # availability is additive: the direct API has no equivalent reading.
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

    # A boolean on some Protect firmwares, recordingSettings.mode on others.
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

    # A bare thumbnail token needs an authenticated fetch, so link to the camera page instead.
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


async def async_protect_status(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """UniFi Protect status for the Network tab: reachable + camera counts,
    the full devices table (with console deep-links), and recent events / AI
    smart detections. Best-effort, never raises; the events call failing on
    its own still returns the cameras. Direct readings win and the core
    ``unifiprotect`` bootstrap fills the blanks."""
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
    # Short-lived connection; an invalid host is a configuration error on the payload.
    try:
        conn = await _protect_conn(store, secrets)
    except UniFiError as err:
        out["configured"] = True
        out["error"] = str(err)
        conn = None
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
        # Protect 7.2.105 /cameras is an unpaginated array; never add offset/limit here.
        payload = _rows(await _get(hass, conn, "/cameras"))
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

    # Protect 7.2.105 has no historical REST events endpoint, only the WebSocket subscription.
    out["events_error"] = (
        "Protect 7.2.105 provides events through the /subscribe/events "
        "WebSocket, not a historical REST endpoint. Load Home Assistant's "
        "UniFi Protect integration to populate recent event history."
    )


def _apply_core_protect_data(hass: HomeAssistant, out: dict[str, Any]) -> None:
    """Fill the Protect status from the core unifiprotect integration's
    in-memory bootstrap: camera details the Local API left blank, and recent
    events retained from the official subscription stream.
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
            # The panel's events card is captioned "last 24h".
            events = [
                _event_row_from_core(e, origin)
                for e in snap["events"]
                if e.get("start") is not None and e["start"] >= cutoff
            ]
            events.sort(key=lambda e: e["start"] or 0, reverse=True)
            out["events"] = events
            # The core bootstrap is now the events source; the REST message would be stale.
            out["events_error"] = None

        # Core-memory data is real even when the direct API is unconfigured or down.
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
        # Without a console origin the deep link would point at the Home Assistant host.
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
