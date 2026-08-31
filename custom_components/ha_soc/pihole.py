"""Pi-hole v6 — direct-to-instance read-only client (DNS security visibility).

The user runs UniFi's own DNS such that only the IoT network's clients have
their DNS forwarded to Pi-hole (every other network resolves elsewhere), so
Pi-hole's own view of "who queried what" is effectively the IoT network's
view. HA SOC talks to Pi-hole directly over the LAN with its own local
credential — no cloud, no core Home Assistant Pi-hole integration required
(core's ``pi_hole`` only exposes an on/off switch and a handful of coarse
sensors; it has no query log, group, or client-scoping surface at all, so
this module is a real API client rather than an enrichment layer the way
unifi_core.py rides on core's own state).

Everything here is READ-ONLY except the auth session itself: it logs in,
reads state, and logs the session back out. It never toggles blocking,
edits a group, or reassigns a client.

## Why the field/path mapping is defensive

The API path prefixes, auth flow, and field names below were verified
against pi-hole/FTL's own published OpenAPI spec (the same one the local
``http://pi.hole/api/docs`` the user pointed at serves, generated from that
project's source — ``src/api/docs/content/specs/*.yaml`` on GitHub), not
guessed. That environment could not reach ``http://pi.hole`` itself (it is
only resolvable on the user's own LAN), so every shape below should still
be treated as the best available evidence, not a live-verified fact — the
same posture unifi.py takes toward the UniFi Integration API. Keys marked
``# VERIFY`` are the ones most likely to drift across a Pi-hole version;
an unrecognized shape degrades to ``None`` (rendered "—") rather than a
guess, exactly like unifi.py's own field resolution.

## Auth flow

  POST {base_url}/auth  {"password": <app password>}  ->
    {"session": {"valid": bool, "sid": str|None, "csrf": str|None,
                 "validity": int, "message": str, "totp": bool}}

The returned ``sid`` rides on the ``X-FTL-SID`` header on every subsequent
call (FTL's documented ``x_header_sid`` security scheme — sid can also
travel as a query param, a cookie, or a plain ``sid`` header, but the
custom header is the one that can never leak into a proxy access log the
way a query param would). A session is created fresh for each overview
snapshot and explicitly logged out (``DELETE {base_url}/auth``) before this
module returns, mirroring unifi.py's SEC-3 posture of never holding a live
credential in memory between panel refreshes — a Pi-hole session is cheap
to create, so there is no reason to keep one alive longer than one fetch.
If Pi-hole has no password configured (an open local API), it is not
supported here: the app password is a hard requirement, matching how the
Network tab treats an unconfigured UniFi API key.
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
# How many rows to ask for from top_domains / recent_blocked — a home Pi-hole
# instance's own UI defaults are in this range; this is a display limit, not
# a security bound.
_TOP_DOMAINS_COUNT = 15
_RECENT_BLOCKED_COUNT = 15


class PiHoleError(Exception):
    """Any failure talking to Pi-hole — surfaced to the UI as a
    reachable=False overview with a human-readable reason, never a raw
    stack."""


def _first(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


@dataclass(frozen=True, repr=False)
class _Conn:
    """A resolved connection to one Pi-hole instance, plus the session id
    obtained for this one snapshot. Short-lived by design (mirrors
    unifi._Conn / work item SEC-3): built fresh inside
    async_pihole_overview from the secret store's value at that moment,
    logged in, used, logged out, and dropped — never held between panel
    refreshes."""

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
    """Best-effort session teardown. Never raises: a failed logout just
    means the session expires on Pi-hole's own timer instead."""
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
        # "Default" (group 0) is Pi-hole's own always-present group; a
        # client carrying ONLY [0] has no dedicated group of its own, which
        # is exactly the "not scoped" signal network_security.py looks for.
        "group_names": [group_names.get(gid, str(gid)) for gid in group_ids],
        "default_group_only": group_ids == [0],
    }


def _client_matches_cidr(client_id: str, cidr: str) -> bool:
    """Whether a Pi-hole client identifier (an IP, or a CIDR of its own)
    falls inside the configured IoT subnet. A client identified by MAC,
    hostname, or interface (":eth0") never matches an IP-shaped CIDR check
    and is simply excluded rather than guessed at."""
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
    """Everything the Network Security tab's Pi-hole section renders: DNS
    blocking on/off, the query summary, group/client inventory (to check
    whether the IoT subnet has a dedicated scoped group rather than sharing
    Pi-hole's global Default group), and a short sample of recently blocked
    and top domains. Never raises: a connection problem comes back as
    reachable=False with a human-readable ``error``.
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
                # VERIFY: some builds report a plain boolean "blocking" field
                # instead of the documented enabled/disabled string; tolerate
                # both rather than guessing which one a given build sends.
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
                # No matching client entry at all means Pi-hole has never
                # been told about this subnet specifically — every device on
                # it is falling through to the global Default group, which
                # is the "not scoped" case regardless of whether any single
                # entry says so explicitly.
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
