"""Technitium DNS Server direct-to-instance read-only client (DNS security
visibility).

A parallel, independently-configurable source alongside pihole.py — not a
replacement; either, both, or neither may be configured (see
docs/decisions.md). Auth is a stateless per-request API token appended as a
query parameter (Technitium's token model), so unlike Pi-hole's session-
cookie flow there is no login/logout pair and no per-snapshot connection
object to tear down; API shapes: docs/protocol.md.

UNVERIFIED: implemented against the well-known Technitium v10+ API shape
(endpoint names/params below) rather than a live fetch of the upstream
APIDOCS.md in this session. Re-verify against
https://github.com/TechnitiumSoftware/DnsServer/blob/master/APIDOCS.md
before relying on exact field names in production.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlparse

import aiohttp
import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_TECHNITIUM_API_TOKEN,
    CONF_TECHNITIUM_HOST,
    CONF_TECHNITIUM_VERIFY_SSL,
    DEFAULT_TECHNITIUM_VERIFY_SSL,
    TECHNITIUM_API_PATH,
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
_MAX_ZONES = 25
_STATS_TYPE = "LastHour"


class TechnitiumError(Exception):
    """Any failure talking to Technitium, surfaced as a reachable=False
    overview with a human-readable reason."""


@dataclass(frozen=True, repr=False)
class _Conn:
    """A resolved connection to one Technitium instance plus the API token.
    Stateless (no session lifecycle), but kept as a small object for parity
    with pihole.py's clarity and to keep the token out of stray reprs/logs."""

    host: str
    verify_ssl: bool
    token: str

    def __repr__(self) -> str:
        return f"_Conn(host={self.host!r}, verify_ssl={self.verify_ssl!r}, token='[redacted]')"

    @property
    def origin(self) -> str:
        host = self.host.strip().rstrip("/")
        if "://" not in host:
            host = f"https://{host}"
        parsed = urlparse(host)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def base_url(self) -> str:
        return f"{self.origin}{TECHNITIUM_API_PATH}"


def _validate_host(host: str) -> None:
    """Same shape of check as pihole._validate_host: only http/https, no
    smuggled userinfo, a real hostname present."""
    candidate = host if "://" in host else f"https://{host}"
    try:
        parsed = urlparse(candidate)
    except ValueError as err:
        raise TechnitiumError(f"The configured Technitium host is not a valid URL: {err}") from err
    if "://" in host and parsed.scheme not in ("http", "https"):
        raise TechnitiumError(
            f"The configured Technitium host uses the unsupported scheme "
            f"{parsed.scheme!r}; only http and https are allowed."
        )
    if parsed.username is not None or parsed.password is not None:
        raise TechnitiumError(
            "The configured Technitium host contains a username/password part; "
            "remove it and configure the API token instead."
        )
    if not parsed.hostname:
        raise TechnitiumError("The configured Technitium host has no host name.")


async def _get(hass: HomeAssistant, conn: _Conn, path: str, params: str = "") -> Any:
    """One authenticated GET, hardened like pihole._get: redirects are never
    followed, and the body is bounded by both the declared Content-Length and
    the actual read. The token rides as a query parameter (Technitium's auth
    model) rather than a header/cookie."""
    session = async_get_clientsession(hass, verify_ssl=conn.verify_ssl)
    sep = "&" if "?" in path else "?"
    url = f"{conn.base_url}{path}{sep}token={quote(conn.token, safe='')}{params}"
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(url, allow_redirects=False) as resp:
                if 300 <= resp.status < 400:
                    raise TechnitiumError(
                        "Technitium returned an unexpected redirect; refusing to follow it."
                    )
                if resp.status in (401, 403):
                    raise TechnitiumError("Technitium rejected the API token.")
                if resp.status == 404:
                    raise TechnitiumError(f"Endpoint not found ({path}).")
                resp.raise_for_status()
                declared_length = getattr(resp, "content_length", None)
                if declared_length is not None and declared_length > _MAX_BODY_BYTES:
                    raise TechnitiumError("The Technitium response is too large to process.")
                raw = await resp.content.read(_MAX_BODY_BYTES + 1)
                if len(raw) > _MAX_BODY_BYTES:
                    raise TechnitiumError("The Technitium response is too large to process.")
                payload = json.loads(raw)
    except TechnitiumError:
        raise
    except asyncio.TimeoutError as err:
        raise TechnitiumError("Timed out reaching Technitium.") from err
    except aiohttp.ClientError as err:
        raise TechnitiumError(f"Could not reach Technitium: {err}") from err
    except ValueError as err:
        raise TechnitiumError("Technitium returned an unexpected (non-JSON) response.") from err

    # Technitium's own API-level failure shape: {"status": "error", ...}.
    if isinstance(payload, dict) and payload.get("status") == "error":
        message = payload.get("errorMessage") or payload.get("message") or "request failed"
        raise TechnitiumError(f"Technitium API error: {message}")
    return payload


def _normalize_zone(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": raw.get("name"),
        "type": raw.get("type"),
        "disabled": bool(raw.get("disabled")) if raw.get("disabled") is not None else None,
    }


def _normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
    rdata = raw.get("rData") if isinstance(raw.get("rData"), dict) else {}
    return {
        "name": raw.get("name"),
        "type": raw.get("type"),
        "ttl": raw.get("ttl"),
        "disabled": bool(raw.get("disabled")) if raw.get("disabled") is not None else None,
        "data": rdata,
    }


async def async_technitium_overview(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Network Security tab's Technitium section renders.
    Never raises: a connection problem comes back as reachable=False with a
    human-readable ``error``.
    """
    result: dict[str, Any] = {
        "configured": False,
        "reachable": False,
        "error": None,
        "blocking_enabled": None,
        "summary": None,
        "zones": [],
        "records": {},
        "top_blocked_domains": [],
        "recent_blocked": [],
        "generated_at": dt_util.utcnow().isoformat(),
    }

    s = store.settings
    host = (s.get(CONF_TECHNITIUM_HOST) or "").strip()
    token = (await secrets.async_get(CONF_TECHNITIUM_API_TOKEN) or "").strip()
    if not host or not token:
        return result
    result["configured"] = True

    try:
        _validate_host(host)
    except TechnitiumError as err:
        result["error"] = str(err)
        return result

    verify_ssl = bool(s.get(CONF_TECHNITIUM_VERIFY_SSL, DEFAULT_TECHNITIUM_VERIFY_SSL))
    conn = _Conn(host=host, verify_ssl=verify_ssl, token=token)

    try:
        async with asyncio.timeout(_OVERVIEW_TIMEOUT_SECONDS):
            settings_payload = await _get(hass, conn, "/settings/get")
            response = settings_payload.get("response") if isinstance(settings_payload, dict) else None
            enable_blocking = response.get("enableBlocking") if isinstance(response, dict) else None
            result["blocking_enabled"] = enable_blocking if isinstance(enable_blocking, bool) else None

            stats_payload = await _get(hass, conn, "/dashboard/stats/get", f"&type={_STATS_TYPE}")
            stats = stats_payload.get("response") if isinstance(stats_payload, dict) else None
            stats_fields = stats.get("stats") if isinstance(stats, dict) else None
            if isinstance(stats_fields, dict):
                total = stats_fields.get("totalQueries")
                blocked = stats_fields.get("totalBlocked")
                percent_blocked = None
                if isinstance(total, (int, float)) and total and isinstance(blocked, (int, float)):
                    percent_blocked = round((blocked / total) * 100, 2)
                result["summary"] = {
                    "total": total,
                    "blocked": blocked,
                    "percent_blocked": percent_blocked,
                    "unique_domains": stats_fields.get("totalClients"),
                }
                top_domains = stats.get("topBlockedDomains") if isinstance(stats, dict) else None
                if isinstance(top_domains, list):
                    result["top_blocked_domains"] = [
                        {"domain": d.get("name"), "count": d.get("hits")}
                        for d in top_domains[:_TOP_DOMAINS_COUNT]
                        if isinstance(d, dict) and d.get("name")
                    ]

            zones_payload = await _get(hass, conn, "/zones/list")
            zones_response = zones_payload.get("response") if isinstance(zones_payload, dict) else None
            zones_raw = zones_response.get("zones") if isinstance(zones_response, dict) else None
            zones = [_normalize_zone(z) for z in zones_raw or [] if isinstance(z, dict)]
            result["zones"] = zones

            records: dict[str, list[dict[str, Any]]] = {}
            for zone in zones[:_MAX_ZONES]:
                zone_name = zone.get("name")
                if not zone_name:
                    continue
                records_payload = await _get(
                    hass, conn, "/zones/records/get", f"&zone={quote(str(zone_name), safe='')}"
                )
                records_response = (
                    records_payload.get("response") if isinstance(records_payload, dict) else None
                )
                records_raw = records_response.get("records") if isinstance(records_response, dict) else None
                records[zone_name] = [
                    _normalize_record(r) for r in records_raw or [] if isinstance(r, dict)
                ]
            result["records"] = records

            logs_payload = await _get(
                hass,
                conn,
                "/logs/query",
                f"&start=1&rows={_RECENT_BLOCKED_COUNT}&responseType=Blocked",
            )
            logs_response = logs_payload.get("response") if isinstance(logs_payload, dict) else None
            entries = logs_response.get("entries") if isinstance(logs_response, dict) else None
            if isinstance(entries, list):
                result["recent_blocked"] = [
                    str(e.get("qName")) for e in entries if isinstance(e, dict) and e.get("qName")
                ][:_RECENT_BLOCKED_COUNT]

            result["reachable"] = True
    except TechnitiumError as err:
        result["error"] = str(err)
    except asyncio.TimeoutError:
        result["error"] = (
            f"The Technitium snapshot did not complete within "
            f"{_OVERVIEW_TIMEOUT_SECONDS} seconds; partial data shown."
        )
    except Exception as err:
        _LOGGER.exception("Unexpected Technitium error")
        result["error"] = f"Unexpected error: {err}"

    return result
