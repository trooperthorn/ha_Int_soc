"""Pi-hole v6 direct-to-instance read-only client (DNS security visibility).

Read-only except the auth session itself: it logs in, reads state, and logs
out; it never toggles blocking, edits a group, or reassigns a client (API
shapes and auth flow: docs/protocol.md).
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

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.util.dt as dt_util

from .const import (
    CONF_PIHOLE_API_KEY,
    CONF_PIHOLE_HOST,
    CONF_PIHOLE_IOT_CIDR,
    CONF_PIHOLE_VERIFY_SSL,
    DEFAULT_PIHOLE_VERIFY_SSL,
    PIHOLE_API_PATH,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
_OVERVIEW_TIMEOUT_SECONDS = 30
_MAX_BODY_BYTES = 4 * 1024 * 1024
# Display limits, not security bounds.
_TOP_DOMAINS_COUNT = 15
_RECENT_BLOCKED_COUNT = 15


class PiHoleError(Exception):
    """Any failure talking to Pi-hole, surfaced as a reachable=False overview
    with a human-readable reason."""


def _first(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


@dataclass(frozen=True, repr=False)
class _Conn:
    """A resolved connection to one Pi-hole instance plus the session id for
    this one snapshot; short-lived, never held between panel refreshes."""

    host: str
    verify_ssl: bool
    sid: str

    def __repr__(self) -> str:
        return f"_Conn(host={self.host!r}, verify_ssl={self.verify_ssl!r}, sid='[redacted]')"

    @property
    def origin(self) -> str:
        host = self.host.strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        parsed = urlparse(host)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def base_url(self) -> str:
        return f"{self.origin}{PIHOLE_API_PATH}"


def _validate_host(host: str) -> None:
    """Same shape of check as unifi._validate_host: only http/https, no
    smuggled userinfo, a real hostname present."""
    candidate = host if "://" in host else f"https://{host}"
    try:
        parsed = urlparse(candidate)
    except ValueError as err:
        raise PiHoleError(f"The configured Pi-hole host is not a valid URL: {err}") from err
    if "://" in host and parsed.scheme not in ("http", "https"):
        raise PiHoleError(
            f"The configured Pi-hole host uses the unsupported scheme "
            f"{parsed.scheme!r}; only http and https are allowed."
        )
    if parsed.username is not None or parsed.password is not None:
        raise PiHoleError(
            "The configured Pi-hole host contains a username/password part; "
            "remove it and configure the app password instead."
        )
    if not parsed.hostname:
        raise PiHoleError("The configured Pi-hole host has no host name.")


def _origin_and_path(host: str) -> tuple[str, str]:
    host = host.strip().rstrip("/")
    if "://" not in host:
        host = f"https://{host}"
    parsed = urlparse(host)
    return f"{parsed.scheme}://{parsed.netloc}", f"{parsed.scheme}://{parsed.netloc}{PIHOLE_API_PATH}"


async def _authenticate(
    hass: HomeAssistant, host: str, password: str, verify_ssl: bool
) -> _Conn:
    """Log in and return a _Conn carrying the session id. Raises PiHoleError
    with a friendly reason on any transport/HTTP/decode/auth failure."""
    _, base_url = _origin_and_path(host)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.post(
                f"{base_url}/auth",
                json={"password": password},
                allow_redirects=False,
            ) as resp:
                if 300 <= resp.status < 400:
                    raise PiHoleError(
                        "Pi-hole returned an unexpected redirect; refusing to follow it."
                    )
                declared_length = getattr(resp, "content_length", None)
                if declared_length is not None and declared_length > _MAX_BODY_BYTES:
                    raise PiHoleError("The Pi-hole response is too large to process.")
                raw = await resp.content.read(_MAX_BODY_BYTES + 1)
                if len(raw) > _MAX_BODY_BYTES:
                    raise PiHoleError("The Pi-hole response is too large to process.")
                try:
                    payload = json.loads(raw)
                except ValueError as err:
                    raise PiHoleError(
                        "Pi-hole returned an unexpected (non-JSON) response."
                    ) from err
                if resp.status == 401:
                    raise PiHoleError("Authentication failed — check the app password.")
                if not (200 <= resp.status < 300):
                    raise PiHoleError(f"Pi-hole returned HTTP {resp.status}.")
    except PiHoleError:
        raise
    except asyncio.TimeoutError as err:
        raise PiHoleError("Timed out reaching Pi-hole.") from err
    except aiohttp.ClientError as err:
        raise PiHoleError(f"Could not reach Pi-hole: {err}") from err

    session_obj = payload.get("session") if isinstance(payload, dict) else None
    if not isinstance(session_obj, dict) or not session_obj.get("valid"):
        message = (
            session_obj.get("message") if isinstance(session_obj, dict) else None
        ) or "Authentication rejected."
        raise PiHoleError(f"Authentication failed — {message}")
    sid = session_obj.get("sid")
    if not sid:
        raise PiHoleError(
            "Pi-hole accepted the password but returned no session id "
            "(2FA may be enabled — not supported here)."
        )
    return _Conn(host=host, verify_ssl=verify_ssl, sid=str(sid))


async def _logout(hass: HomeAssistant, conn: _Conn) -> None:
    """Best-effort session teardown; never raises."""
    try:
        session = async_get_clientsession(hass, verify_ssl=conn.verify_ssl)
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            await session.delete(
                f"{conn.base_url}/auth",
                headers={"X-FTL-SID": conn.sid},
                allow_redirects=False,
            )
    except Exception:  # noqa: BLE001 - logout is cleanup, never fatal
        _LOGGER.debug("Pi-hole session logout failed (non-fatal)", exc_info=True)


async def _get(hass: HomeAssistant, conn: _Conn, path: str) -> Any:
    """One authenticated GET, hardened like unifi._get: redirects are never
    followed, and the body is bounded by both the declared Content-Length
    and the actual read."""
    session = async_get_clientsession(hass, verify_ssl=conn.verify_ssl)
    url = f"{conn.base_url}{path}"
    headers = {"X-FTL-SID": conn.sid, "Accept": "application/json"}
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(url, headers=headers, allow_redirects=False) as resp:
                if 300 <= resp.status < 400:
                    raise PiHoleError(
                        "Pi-hole returned an unexpected redirect; refusing to follow it."
                    )
                if resp.status in (401, 403):
                    raise PiHoleError("Pi-hole session was rejected or expired.")
                if resp.status == 404:
                    raise PiHoleError(f"Endpoint not found ({path}).")
                resp.raise_for_status()
                declared_length = getattr(resp, "content_length", None)
                if declared_length is not None and declared_length > _MAX_BODY_BYTES:
                    raise PiHoleError("The Pi-hole response is too large to process.")
                raw = await resp.content.read(_MAX_BODY_BYTES + 1)
                if len(raw) > _MAX_BODY_BYTES:
                    raise PiHoleError("The Pi-hole response is too large to process.")
                return json.loads(raw)
    except PiHoleError:
        raise
    except asyncio.TimeoutError as err:
        raise PiHoleError("Timed out reaching Pi-hole.") from err
    except aiohttp.ClientError as err:
        raise PiHoleError(f"Could not reach Pi-hole: {err}") from err
    except ValueError as err:
        raise PiHoleError("Pi-hole returned an unexpected (non-JSON) response.") from err


def _normalize_group(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": raw.get("id"),
        "name": _first(raw, "name"),
        "enabled": bool(raw.get("enabled")) if raw.get("enabled") is not None else None,
        "comment": raw.get("comment"),
    }


def _normalize_client(raw: dict[str, Any], group_names: dict[Any, str]) -> dict[str, Any]:
    group_ids = raw.get("groups") if isinstance(raw.get("groups"), list) else []
    return {
        "client": raw.get("client"),
        "name": raw.get("name"),
        "comment": raw.get("comment"),
        "group_ids": group_ids,
        # A client carrying only group 0 (Pi-hole's Default) has no dedicated group.
        "group_names": [group_names.get(gid, str(gid)) for gid in group_ids],
        "default_group_only": group_ids == [0],
    }


def _client_matches_cidr(client_id: str, cidr: str) -> bool:
    """Whether a Pi-hole client identifier (an IP, or a CIDR of its own)
    falls inside the configured IoT subnet; MAC, hostname, and interface
    identifiers never match."""
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False
    try:
        if "/" in client_id:
            candidate = ipaddress.ip_network(client_id, strict=False)
            return candidate.subnet_of(network) or candidate == network
        return ipaddress.ip_address(client_id) in network
    except ValueError:
        return False


async def async_pihole_overview(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Network Security tab's Pi-hole section renders. Never
    raises: a connection problem comes back as reachable=False with a
    human-readable ``error``.
    """
    result: dict[str, Any] = {
        "configured": False,
        "reachable": False,
        "error": None,
        "blocking_enabled": None,
        "summary": None,
        "groups": [],
        "clients": [],
        "iot_cidr": (store.settings.get(CONF_PIHOLE_IOT_CIDR) or "").strip() or None,
        "iot_clients_scoped": None,
        "top_blocked_domains": [],
        "recent_blocked": [],
        "generated_at": dt_util.utcnow().isoformat(),
    }

    s = store.settings
    host = (s.get(CONF_PIHOLE_HOST) or "").strip()
    password = (await secrets.async_get(CONF_PIHOLE_API_KEY) or "").strip()
    if not host or not password:
        return result
    result["configured"] = True

    try:
        _validate_host(host)
    except PiHoleError as err:
        result["error"] = str(err)
        return result

    verify_ssl = bool(s.get(CONF_PIHOLE_VERIFY_SSL, DEFAULT_PIHOLE_VERIFY_SSL))
    conn: _Conn | None = None
    try:
        async with asyncio.timeout(_OVERVIEW_TIMEOUT_SECONDS):
            conn = await _authenticate(hass, host, password, verify_ssl)

            blocking = await _get(hass, conn, "/dns/blocking")
            blocking_field = blocking.get("blocking") if isinstance(blocking, dict) else None
            if isinstance(blocking_field, str):
                result["blocking_enabled"] = blocking_field == "enabled"
            elif isinstance(blocking_field, bool):
                # VERIFY: some builds may send a boolean instead of the documented string.
                result["blocking_enabled"] = blocking_field
            else:
                result["blocking_enabled"] = None

            summary = await _get(hass, conn, "/stats/summary")
            queries = summary.get("queries") if isinstance(summary, dict) else None
            if isinstance(queries, dict):
                result["summary"] = {
                    "total": queries.get("total"),
                    "blocked": queries.get("blocked"),
                    "percent_blocked": queries.get("percent_blocked"),
                    "unique_domains": queries.get("unique_domains"),
                }

            groups_payload = await _get(hass, conn, "/groups")
            groups_raw = (
                groups_payload.get("groups")
                if isinstance(groups_payload, dict)
                else groups_payload
            )
            groups = [_normalize_group(g) for g in groups_raw or [] if isinstance(g, dict)]
            result["groups"] = groups
            group_names = {g["id"]: g["name"] or str(g["id"]) for g in groups if g["id"] is not None}

            clients_payload = await _get(hass, conn, "/clients")
            clients_raw = (
                clients_payload.get("clients")
                if isinstance(clients_payload, dict)
                else clients_payload
            )
            clients = [
                _normalize_client(c, group_names) for c in clients_raw or [] if isinstance(c, dict)
            ]
            result["clients"] = clients

            iot_cidr = result["iot_cidr"]
            if iot_cidr:
                iot_clients = [
                    c for c in clients if c["client"] and _client_matches_cidr(c["client"], iot_cidr)
                ]
                # No matching client entry means the subnet falls through to Default: not scoped.
                result["iot_clients_scoped"] = bool(iot_clients) and all(
                    not c["default_group_only"] for c in iot_clients
                )

            top = await _get(
                hass, conn, f"/stats/top_domains?blocked=true&count={_TOP_DOMAINS_COUNT}"
            )
            domains = top.get("domains") if isinstance(top, dict) else None
            if isinstance(domains, list):
                result["top_blocked_domains"] = [
                    {"domain": d.get("domain"), "count": d.get("count")}
                    for d in domains
                    if isinstance(d, dict) and d.get("domain")
                ]

            recent = await _get(
                hass, conn, f"/stats/recent_blocked?count={_RECENT_BLOCKED_COUNT}"
            )
            blocked_list = recent.get("blocked") if isinstance(recent, dict) else None
            if isinstance(blocked_list, list):
                result["recent_blocked"] = [str(d) for d in blocked_list if d]

            result["reachable"] = True
    except PiHoleError as err:
        result["error"] = str(err)
    except asyncio.TimeoutError:
        result["error"] = (
            f"The Pi-hole snapshot did not complete within "
            f"{_OVERVIEW_TIMEOUT_SECONDS} seconds; partial data shown."
        )
    except Exception as err:  # noqa: BLE001 - never let the panel see a raw trace
        _LOGGER.exception("Unexpected Pi-hole error")
        result["error"] = f"Unexpected error: {err}"
    finally:
        if conn is not None:
            await _logout(hass, conn)

    return result
