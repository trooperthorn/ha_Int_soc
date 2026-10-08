"""Optional push of Home Assistant system detail to Observe over OTLP JSON.

Off by default. When the owner enables it in the options flow, a timer collects a snapshot
of data HA SOC already holds (otlp_mapper.py turns it into OTLP), queues the two requests
and sends them to Observe's POST /v1/metrics and /v1/logs on Home Assistant's shared
aiohttp session. See docs/design.md, "Observe push".

Delivery rules:
- The queue is bounded (MAX_QUEUE payloads and MAX_QUEUE_BYTES of compressed body) and in
  memory only. It is kept across an options reload (the carry-over in hass.data) when the
  destination is unchanged. When it fills up the queued metric payloads are merged into one
  that keeps the newest point per series per interval (compact_metrics), so a long outage
  loses resolution instead of its oldest hours. Only when merging cannot make room is the
  oldest payload dropped, counted and logged as a warning.
- A log record is queued once. Keys already queued or already accepted are left out of the
  next payload, so an outage does not repeat every record in every payload.
- A payload keeps one Idempotency-Key for its whole life, so a retry after a lost response
  is recognised by Observe instead of stored twice.
- Retry-After is honoured. Without it a failed send backs off exponentially. Waiting is a
  stored "not before" time checked on the next tick, never a sleep.
- 401 and 403 raise a Repairs issue and drop that payload; any accepted push removes it.
  Other 4xx answers mean the payload itself is wrong, so it is dropped and counted. After
  REJECT_THRESHOLD of them in a row sending backs off exponentially and a Repairs issue
  names the status; any accepted push clears both.
- A 200 answer with a partialSuccess rejection of log records keeps those records unsent for
  one more try on the next cycle; a second rejection gives up and reports it.
- The ingest key is only ever placed in the Authorization header. It is removed from every
  log line and never appears in diagnostics or the status dict.
"""
from __future__ import annotations

import asyncio
import gzip
import ipaddress
import json
import logging
import re
import ssl
import time
import uuid
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import aiohttp
import homeassistant.helpers.issue_registry as ir
import homeassistant.util.dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval

from . import otlp_mapper
from .const import (
    CONF_OBSERVE_CA_PEM,
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_FINGERPRINT,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DEFAULT_OBSERVE_ENABLED,
    DEFAULT_OBSERVE_INTERVAL,
    MAX_OBSERVE_INTERVAL,
    MIN_OBSERVE_INTERVAL,
    REDACTED_PLACEHOLDER,
)
from .repairs import (
    async_create_observe_key_issue,
    async_create_observe_rejected_issue,
    async_delete_observe_key_issue,
    async_delete_observe_rejected_issue,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

INGEST_KEY_PREFIX = "wpi_"
MAX_INGEST_KEY_LENGTH = 256
MAX_HOST_NAME_LENGTH = 253

MAX_QUEUE = 60
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRY_AFTER_SECONDS = 3600
BACKOFF_BASE_SECONDS = 10
BACKOFF_MAX_SECONDS = 900
# A rejected key is probed again no sooner than this, so a wrong key is not hammered.
AUTH_BACKOFF_SECONDS = 300
# Consecutive payload rejections (4xx other than 401/403/408/429) before the push backs off and
# raises a Repairs issue. Fewer than this are treated as one bad payload and just dropped.
REJECT_THRESHOLD = 3
# Container samples younger than this are taken from the resource watchdog.
WATCHDOG_SAMPLE_MAX_AGE_SECONDS = 90
# With the watchdog off the push fetches container stats itself, and no more often than the
# watchdog would sample (its configured interval, clamped the way the watchdog clamps it).
DEFAULT_FETCH_INTERVAL_SECONDS = 60
# Crash bundles and the Supervisor resolution state change rarely; refreshed this often.
SLOW_REFRESH_SECONDS = 600
SUPERVISOR_TIMEOUT_SECONDS = 10
RESPONSE_READ_LIMIT = 65536
MESSAGE_LIMIT = 200
SENT_KEYS_LIMIT = 5000  # The oldest accepted keys are forgotten first, one at a time.
# Memory bound of the queue: payload count and total compressed body size.
MAX_QUEUE_BYTES = 4 * 1024 * 1024
# A merged metrics payload stays well under Observe's 1 MiB request cap, which Observe checks
# on the gzipped body and on the plain JSON. A merge is split into several payloads so that
# none holds more than the mapper's per-request point limit or more plain JSON than this.
MAX_MERGED_BYTES = 512 * 1024
MAX_MERGED_PLAIN_BYTES = 900 * 1024
MAX_MERGED_POINTS = otlp_mapper.MAX_POINTS
# Merged metric payloads keep the newest point per series per interval of this many seconds;
# the interval doubles until the result fits, up to the last one.
COMPACT_INTERVALS_SECONDS = (300, 600, 1200, 2400, 3600)
# The carry-over of a stopped pusher lives in hass.data under this key, by config entry id.
DATA_QUEUE_CARRY = "ha_soc_observe_queue_carry"
MAX_CA_PEM_LENGTH = 65536
MAX_CA_CERTIFICATES = 10

ERROR_INVALID_URL = "invalid_url"
ERROR_INSECURE_URL = "insecure_url"
ERROR_KEY_REQUIRED = "key_required"
ERROR_KEY_REQUIRED_FOR_URL = "key_required_for_url_change"
ERROR_KEY_REQUIRED_FOR_TRUST = "key_required_for_trust_change"
ERROR_INVALID_KEY = "invalid_key"
ERROR_INVALID_HOST_NAME = "invalid_host_name"
ERROR_INVALID_INTERVAL = "invalid_interval"
ERROR_INVALID_CA = "invalid_ca"
ERROR_INVALID_FINGERPRINT = "invalid_fingerprint"
ERROR_TRUST_CONFLICT = "trust_conflict"


# ---------------------------------------------------------------------------
# Validation (used by the options flow and again when the push starts)
# ---------------------------------------------------------------------------


_RFC1918_NETWORKS = tuple(
    ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
# Carrier-grade NAT space, which Tailscale hands out (100.64.0.0/10); see docs/decisions.md.
_SHARED_NETWORK = ipaddress.ip_network("100.64.0.0/10")
_ULA_NETWORK = ipaddress.ip_network("fc00::/7")
_BROADCAST_NETS = (ipaddress.ip_network("240.0.0.0/4"), ipaddress.ip_network("0.0.0.0/8"))


def _is_private_host(host: str) -> bool:
    """True for localhost and for IP literals on a local network.

    Accepted: RFC1918, IPv6 unique local (fc00::/7), loopback and link-local (169.254.0.0/16,
    fe80::/10) and the shared address space 100.64.0.0/10 that Tailscale uses; see
    docs/decisions.md. Everything else is refused, including the unspecified address,
    240.0.0.0/4, broadcast and 6to4 or other IPv6 forms that embed an IPv4 address. A DNS
    name is never accepted for plain http because it can resolve anywhere.
    """
    if host.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        # IPv4-mapped (::ffff:a.b.c.d) is judged as the IPv4 address it carries. Every other
        # transition form (6to4 2002::/16, Teredo, NAT64, IPv4-compatible) can route to a
        # public host, so only native fc00::/7, fe80::/10 and ::1 pass.
        if address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        else:
            return address.is_loopback or address.is_link_local or address in _ULA_NETWORK
    if address.is_unspecified or address.is_multicast or any(address in net for net in _BROADCAST_NETS):
        return False
    return (
        any(address in net for net in _RFC1918_NETWORKS)
        or address in _SHARED_NETWORK
        or address.is_loopback
        or address.is_link_local
    )


def validate_url(raw: Any) -> tuple[str | None, str | None]:
    """(normalised base URL, None) or (None, error key).

    https is accepted for any host; http only for a private address. User info, a query
    and a fragment are refused so a secret can never ride along in the URL.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        return None, ERROR_INVALID_URL
    try:
        parts = urlsplit(text)
        host = parts.hostname
        parts.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError:
        return None, ERROR_INVALID_URL
    if parts.scheme not in ("http", "https") or not host:
        return None, ERROR_INVALID_URL
    if parts.username or parts.password or parts.query or parts.fragment:
        return None, ERROR_INVALID_URL
    if parts.scheme == "http" and not _is_private_host(host):
        return None, ERROR_INSECURE_URL
    return text.rstrip("/"), None


def validate_host_name(raw: Any) -> str | None:
    """The trimmed host name, or None when it is empty, too long or has odd characters."""
    text = raw.strip() if isinstance(raw, str) else ""
    if not text or len(text) > MAX_HOST_NAME_LENGTH:
        return None
    if not text.isascii() or not text.isprintable() or any(c.isspace() for c in text):
        return None
    return text


def validate_ingest_key(raw: Any) -> str | None:
    text = raw.strip() if isinstance(raw, str) else ""
    if not text.startswith(INGEST_KEY_PREFIX) or len(text) > MAX_INGEST_KEY_LENGTH:
        return None
    if not text.isascii() or not text.isprintable() or any(c.isspace() for c in text):
        return None
    return text


_PEM_BLOCK = re.compile(
    r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\s]+?-----END CERTIFICATE-----"
)
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")


def validate_ca_pem(raw: Any) -> tuple[str | None, str | None]:
    """(normalised PEM, None), (None, None) when blank, or (None, error key).

    Accepts one to MAX_CA_CERTIFICATES certificates in PEM form and keeps only those blocks.
    Text that contains a private key is refused, so a pasted key file is never stored.
    """
    text = raw.strip() if isinstance(raw, str) else ""
    if not text:
        return None, None
    if len(text) > MAX_CA_PEM_LENGTH:
        return None, ERROR_INVALID_CA
    blocks = [re.sub(r"\s+", "", b) for b in _PEM_BLOCK.findall(text)]
    if not 1 <= len(blocks) <= MAX_CA_CERTIFICATES or "PRIVATEKEY" in text.upper().replace(" ", ""):
        return None, ERROR_INVALID_CA
    normalised: list[str] = []
    for block in blocks:
        body = block[len("-----BEGINCERTIFICATE-----") : -len("-----ENDCERTIFICATE-----")]
        lines = [body[i : i + 64] for i in range(0, len(body), 64)]
        pem = "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"
        try:
            ssl.PEM_cert_to_DER_cert(pem)
        except ValueError:
            return None, ERROR_INVALID_CA
        normalised.append(pem)
    return "".join(normalised), None


def validate_fingerprint(raw: Any) -> tuple[str | None, str | None]:
    """(lower-case hex SHA-256, None), (None, None) when blank, or (None, error key).

    Colons, spaces and an optional "sha256:" prefix are accepted, as printed by openssl.
    """
    text = raw.strip().lower() if isinstance(raw, str) else ""
    if not text:
        return None, None
    text = text.removeprefix("sha256:").replace(":", "").replace(" ", "")
    if not _FINGERPRINT.fullmatch(text):
        return None, ERROR_INVALID_FINGERPRINT
    return text, None


def build_trust(ca_pem: str | None, fingerprint: str | None) -> Any:
    """The ``ssl`` argument for the Observe requests, or None for the default trust.

    A pasted CA replaces the system store for this connection: only a chain that ends in it
    is accepted, and the host name is still checked. A fingerprint pins the one certificate
    the server presents. Blocking (parses certificates); call from an executor job.
    Raises ssl.SSLError or ValueError for a CA that cannot be loaded.
    """
    if fingerprint:
        return aiohttp.Fingerprint(bytes.fromhex(fingerprint))
    if ca_pem:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(cadata=ca_pem)
        return context
    return None


_UNSET: Any = object()


def validate_options(
    user_input: dict[str, Any],
    *,
    key_already_set: bool,
    stored_url: Any = _UNSET,
    stored_ca_pem: Any = _UNSET,
    stored_fingerprint: Any = _UNSET,
) -> tuple[dict[str, str], dict[str, Any], str | None]:
    """Check one options-flow submission.

    Returns (errors by field, settings changes, new ingest key or None). The key is blank
    when the existing one is kept. Fields are only required when the push is enabled, but
    anything that is filled in must be valid either way.

    When ``stored_url`` is given and a stored key exists, pointing the push at a different
    URL requires the key to be typed again, so a blank field can never send the stored key
    to a new destination. The same holds when a CA or a fingerprint is newly set or changed
    (pass ``stored_ca_pem`` and ``stored_fingerprint``): trust that no longer checks the chain
    or the name could otherwise send the stored key to a server the submitter chose.
    """
    errors: dict[str, str] = {}
    enabled = bool(user_input.get(CONF_OBSERVE_ENABLED, DEFAULT_OBSERVE_ENABLED))

    url_raw = (user_input.get(CONF_OBSERVE_URL) or "").strip()
    url: str | None = None
    if url_raw or enabled:
        url, url_error = validate_url(url_raw)
        if url_error:
            errors[CONF_OBSERVE_URL] = url_error

    host_raw = (user_input.get(CONF_OBSERVE_HOST_NAME) or "").strip()
    host_name: str | None = None
    if host_raw or enabled:
        host_name = validate_host_name(host_raw)
        if host_name is None:
            errors[CONF_OBSERVE_HOST_NAME] = ERROR_INVALID_HOST_NAME

    key_raw = (user_input.get(CONF_OBSERVE_INGEST_KEY) or "").strip()
    new_key: str | None = None
    if key_raw:
        new_key = validate_ingest_key(key_raw)
        if new_key is None:
            errors[CONF_OBSERVE_INGEST_KEY] = ERROR_INVALID_KEY
    elif enabled and not key_already_set:
        errors[CONF_OBSERVE_INGEST_KEY] = ERROR_KEY_REQUIRED
    elif (
        key_already_set
        and stored_url is not _UNSET
        and CONF_OBSERVE_URL not in errors
        and url is not None
        and url != (stored_url or None)
    ):
        errors[CONF_OBSERVE_INGEST_KEY] = ERROR_KEY_REQUIRED_FOR_URL

    interval = user_input.get(CONF_OBSERVE_INTERVAL, DEFAULT_OBSERVE_INTERVAL)
    try:
        interval = int(interval)
    except (TypeError, ValueError):
        interval = None
    if interval is None or not MIN_OBSERVE_INTERVAL <= interval <= MAX_OBSERVE_INTERVAL:
        errors[CONF_OBSERVE_INTERVAL] = ERROR_INVALID_INTERVAL

    ca_pem, ca_error = validate_ca_pem(user_input.get(CONF_OBSERVE_CA_PEM))
    if ca_error:
        errors[CONF_OBSERVE_CA_PEM] = ca_error
    fingerprint, fingerprint_error = validate_fingerprint(user_input.get(CONF_OBSERVE_FINGERPRINT))
    if fingerprint_error:
        errors[CONF_OBSERVE_FINGERPRINT] = fingerprint_error
    if ca_pem and fingerprint:
        errors[CONF_OBSERVE_FINGERPRINT] = ERROR_TRUST_CONFLICT
    if (
        key_already_set
        and not key_raw
        and CONF_OBSERVE_INGEST_KEY not in errors
        and stored_ca_pem is not _UNSET
        and stored_fingerprint is not _UNSET
        and not (ca_error or fingerprint_error)
        and (
            (ca_pem and ca_pem != (stored_ca_pem or None))
            or (fingerprint and fingerprint != (stored_fingerprint or None))
        )
    ):
        errors[CONF_OBSERVE_INGEST_KEY] = ERROR_KEY_REQUIRED_FOR_TRUST

    changes = {
        CONF_OBSERVE_ENABLED: enabled,
        CONF_OBSERVE_URL: url,
        CONF_OBSERVE_HOST_NAME: host_name,
        CONF_OBSERVE_INTERVAL: interval,
        CONF_OBSERVE_CA_PEM: ca_pem,
        CONF_OBSERVE_FINGERPRINT: fingerprint,
    }
    return errors, changes, new_key


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------


class SnapshotCollector:
    """Gathers the snapshot dict otlp_mapper expects, from data HA SOC already holds.

    A part that cannot be collected is left out, which the mapper reads as "not collected".
    """

    def __init__(
        self,
        hass: HomeAssistant,
        store: HaSocData,
        *,
        health: Any,
        watchdog: Any,
        crash_forensics: Any,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.hass = hass
        self._store = store
        self._health = health
        self._watchdog = watchdog
        self._crash = crash_forensics
        self._clock = clock
        self._slow: dict[str, Any] = {}
        self._slow_at: float | None = None
        self._fetched: dict[str, Any] | None = None
        self._fetched_at: float | None = None

    async def async_collect(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        containers = await self._containers()
        if containers is not None:
            snapshot["containers"] = containers
        snapshot["detections"] = list(self._store.data["detections"].values())
        try:
            snapshot["integration_overview"] = await self._health.async_integration_overview()
        except Exception:  # noqa: BLE001 - one part failing must not stop the push
            _LOGGER.debug("Observe push: integration overview unavailable", exc_info=True)
        snapshot["repairs"] = self._repairs()
        finding, checked = self._backup()
        snapshot["backup_finding"] = finding
        snapshot["backup_checked"] = checked
        snapshot["backup_unreadable"] = getattr(self._health, "backup_unreadable", None)
        snapshot.update(await self._slow_parts())
        return snapshot

    async def _containers(self) -> dict[str, Any] | None:
        sampled_at = getattr(self._watchdog, "last_overview_at", None)
        overview = getattr(self._watchdog, "last_overview", None)
        if (
            overview is not None
            and sampled_at is not None
            and self._clock() - sampled_at < WATCHDOG_SAMPLE_MAX_AGE_SECONDS
        ):
            return overview
        now = self._clock()
        if self._fetched_at is not None and now - self._fetched_at < self._fetch_interval():
            return self._fetched
        from .containers import async_container_resources

        fresh = await async_container_resources(self.hass)
        self._fetched = fresh if fresh.get("available") else None
        self._fetched_at = now
        return self._fetched

    def _fetch_interval(self) -> int:
        try:
            raw = self._store.data["resource_watchdog"].get("interval_seconds")
            interval = int(raw or DEFAULT_FETCH_INTERVAL_SECONDS)
        except (KeyError, TypeError, ValueError):
            interval = DEFAULT_FETCH_INTERVAL_SECONDS
        return max(30, min(3600, interval))

    def _repairs(self) -> list[dict[str, Any]]:
        return [
            {
                "domain": issue.domain,
                "issue_id": issue.issue_id,
                "severity": str(issue.severity) if issue.severity else None,
            }
            for issue in ir.async_get(self.hass).issues.values()
            if issue.active and issue.dismissed_version is None
        ]

    def _backup(self) -> tuple[dict[str, Any] | None, bool]:
        row = self._store.data["misconfig_findings"].get("misconfig:backup_unprotected")
        open_finding = row if row and row.get("status") in ("new", "confirmed") else None
        checked = bool(getattr(self._health, "misconfig_sweep_ran", False))
        return open_finding, checked

    async def _slow_parts(self) -> dict[str, Any]:
        now = self._clock()
        if self._slow_at is not None and now - self._slow_at < SLOW_REFRESH_SECONDS:
            return self._slow
        parts: dict[str, Any] = {}
        try:
            parts["crash_bundles"] = await self.hass.async_add_executor_job(
                self._crash.sync_list_bundles
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Observe push: crash bundle list unavailable", exc_info=True)
        resolution = await self._resolution()
        if resolution is not None:
            parts["resolution"] = resolution
        self._slow, self._slow_at = parts, now
        return parts

    async def _resolution(self) -> dict[str, Any] | None:
        if "hassio" not in self.hass.config.components:
            return None
        try:
            from homeassistant.components.hassio.const import DATA_COMPONENT

            raw = await asyncio.wait_for(
                self.hass.data[DATA_COMPONENT].send_command(
                    "/resolution/info",
                    method="get",
                    return_text=False,
                    timeout=SUPERVISOR_TIMEOUT_SECONDS,
                ),
                timeout=SUPERVISOR_TIMEOUT_SECONDS,
            )
        except Exception:  # noqa: BLE001 - Supervisor calls are best effort
            _LOGGER.debug("Observe push: resolution info unavailable", exc_info=True)
            return None
        return raw if isinstance(raw, dict) else None


# ---------------------------------------------------------------------------
# Sender
# ---------------------------------------------------------------------------


@dataclass
class _Payload:
    signal: str  # "metrics" or "logs"
    body: bytes  # gzip-compressed OTLP JSON
    idempotency_key: str
    dedup_keys: frozenset[str] = field(default_factory=frozenset)
    rejected: int = 0  # Items Observe reported in a partialSuccess answer to this payload.
    compacted: bool = False  # Built by merging queued metric payloads.


@dataclass(frozen=True)
class ObserveConfig:
    url: str
    key: str = field(repr=False)
    host_name: str
    interval_seconds: int
    ca_pem: str | None = None
    fingerprint: str | None = None


@dataclass
class _Carry:
    """What a stopped pusher leaves for the next one of the same config entry (a reload)."""

    url: str
    host_name: str
    queue: deque[_Payload]
    sent_log_keys: dict[str, None]
    partial_retried: set[str]
    integration_series: set[tuple[str, str]]
    # A transient failure's wait (Retry-After or backoff) survives the reload; 0 when none.
    retry_at: float = 0.0
    failures: int = 0


# Send outcomes.
_OK, _DROP, _AUTH, _RETRY = "ok", "drop", "auth", "retry"


def _dedup_keys(request: dict[str, Any]) -> frozenset[str]:
    keys: set[str] = set()
    for resource in request.get("resourceLogs", []):
        for scope in resource.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                for attr in record.get("attributes", []):
                    if attr.get("key") == "observe.dedup_key":
                        value = attr.get("value", {}).get("stringValue")
                        if value:
                            keys.add(value)
    return frozenset(keys)


def _encode(request: dict[str, Any]) -> bytes:
    return gzip.compress(json.dumps(request, separators=(",", ":")).encode("utf-8"), mtime=0)


def _log_key(record: dict[str, Any]) -> str | None:
    for attr in record.get("attributes", []):
        if attr.get("key") == "observe.dedup_key":
            return attr.get("value", {}).get("stringValue") or None
    return None


def _only_logs(request: dict[str, Any], wanted: set[str] | frozenset[str]) -> dict[str, Any]:
    """The logs request cut down to the records that carry no key or a key in ``wanted``."""
    resources = []
    for resource in request.get("resourceLogs", []):
        scopes = []
        for scope in resource.get("scopeLogs", []):
            records = [
                r for r in scope.get("logRecords", []) if (k := _log_key(r)) is None or k in wanted
            ]
            if records:
                scopes.append({**scope, "logRecords": records})
        resources.append({**resource, "scopeLogs": scopes})
    return {**request, "resourceLogs": resources}


def _series_id(scope: str, metric: dict[str, Any], point: dict[str, Any]) -> str:
    attributes = sorted(json.dumps(a, sort_keys=True) for a in point.get("attributes", []))
    return json.dumps([scope, metric.get("name"), metric.get("unit"), attributes])


_Entry = tuple[int, str, str, str, dict[str, Any]]  # stamp, scope, metric name, unit, point


def _newest_per_interval(requests: list[dict[str, Any]], interval_seconds: int) -> list[_Entry]:
    """The newest point of every series in every interval, oldest first."""
    width = interval_seconds * 1_000_000_000
    kept: dict[str, _Entry] = {}
    for request in requests:
        for resource in request.get("resourceMetrics", []):
            for scope in resource.get("scopeMetrics", []):
                scope_name = (scope.get("scope") or {}).get("name", "")
                for metric in scope.get("metrics", []):
                    for point in (metric.get("gauge") or {}).get("dataPoints", []):
                        stamp = int(point.get("timeUnixNano", 0))
                        key = f"{_series_id(scope_name, metric, point)}|{stamp // width}"
                        if key not in kept or kept[key][0] <= stamp:
                            kept[key] = (
                                stamp, scope_name, metric.get("name", ""), metric.get("unit", ""), point
                            )
    return sorted(kept.values(), key=lambda v: v[0])


def _assemble(resource: dict[str, Any], entries: list[_Entry]) -> dict[str, Any]:
    scopes: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = {}
    for _stamp, scope_name, name, unit, point in entries:
        scopes.setdefault(scope_name, {}).setdefault((name, unit), []).append(point)
    return {
        "resourceMetrics": [
            {
                "resource": resource,
                "scopeMetrics": [
                    {
                        "scope": {"name": scope_name},
                        "metrics": [
                            {"name": name, "unit": unit, "gauge": {"dataPoints": points}}
                            for (name, unit), points in metrics.items()
                        ],
                    }
                    for scope_name, metrics in scopes.items()
                ],
            }
        ]
    }


def compact_metrics(requests: list[dict[str, Any]], interval_seconds: int) -> dict[str, Any]:
    """Merge metrics requests into one that keeps the newest point per series per interval.

    A series is a scope, metric name, unit and attribute set. Points are bucketed by their own
    timestamp, so a payload that was already merged is merged again without drift. The
    resource of the newest request is used. All points are gauges (otlp_mapper). The result
    is not limited in size; the queue uses compact_metrics_requests, which splits it.
    """
    resource = requests[-1]["resourceMetrics"][0]["resource"]
    return _assemble(resource, _newest_per_interval(requests, interval_seconds))


def _split_to_fit(resource: dict[str, Any], entries: list[_Entry]) -> list[dict[str, Any]]:
    """Cut time-ordered entries into requests within Observe's per-request limits.

    Each request holds at most MAX_MERGED_POINTS points and at most MAX_MERGED_PLAIN_BYTES of
    plain JSON; a request over the plain size is halved until it fits (or holds one point).
    """
    out: list[dict[str, Any]] = []
    pending = [
        entries[i : i + MAX_MERGED_POINTS] for i in range(0, len(entries), MAX_MERGED_POINTS)
    ]
    while pending:
        chunk = pending.pop(0)
        request = _assemble(resource, chunk)
        plain = len(json.dumps(request, separators=(",", ":")).encode("utf-8"))
        if plain > MAX_MERGED_PLAIN_BYTES and len(chunk) > 1:
            half = len(chunk) // 2
            pending[:0] = [chunk[:half], chunk[half:]]
            continue
        out.append(request)
    return out


def compact_metrics_requests(
    requests: list[dict[str, Any]], interval_seconds: int
) -> list[dict[str, Any]]:
    """compact_metrics, split into requests that each stay inside Observe's limits.

    The requests are in time order. A long outage on a large install can hold more points
    than one request may carry, so the result loses resolution but never a whole outage to a
    refused request.
    """
    resource = requests[-1]["resourceMetrics"][0]["resource"]
    return _split_to_fit(resource, _newest_per_interval(requests, interval_seconds))


def _compact_bodies(bodies: list[bytes], interval_seconds: int) -> list[bytes]:
    requests = [json.loads(gzip.decompress(body)) for body in bodies]
    return [_encode(r) for r in compact_metrics_requests(requests, interval_seconds)]


class ObservePusher:
    """Owns the timer, the bounded queue and the delivery rules."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HaSocData,
        secrets: HaSocSecretStore,
        collector: Callable[[], Awaitable[dict[str, Any]]],
        *,
        wall: Callable[[], float] = time.time,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.hass = hass
        self._store = store
        self._secrets = secrets
        self._collector = collector
        self._wall = wall
        self._clock = clock
        self._config: ObserveConfig | None = None
        self._identity: otlp_mapper.Identity | None = None
        self._entry: ConfigEntry | None = None
        self._unsub: Callable[[], None] | None = None
        self._queue: deque[_Payload] = deque()
        self._lock = asyncio.Lock()
        self._retry_at = 0.0
        self._failures = 0
        self._sent_log_keys: dict[str, None] = {}
        # Log keys whose payload Observe partly rejected once; a second rejection gives up.
        self._partial_retried: set[str] = set()
        # The (domain, category) integration error series sent so far, to zero a recovered one.
        self._integration_series: set[tuple[str, str]] = set()
        self._auth_rejected = False
        self._reject_streak = 0
        self._rejected_issue = False
        # The ``ssl`` argument of the requests: None (default trust), a context or a fingerprint.
        self._trust: Any = None
        # Counters reported by status; none of them hold a secret.
        self.compactions = 0
        self.dropped_overflow = 0
        self.dropped_rejected = 0
        self.rejected_items = 0
        self.abandoned_log_payloads = 0
        self.sent_ok = 0
        self.last_success: str | None = None
        self.last_status: int | str | None = None

    def __repr__(self) -> str:
        return f"<ObservePusher active={self._config is not None}>"

    # -- configuration ------------------------------------------------------

    async def _async_load_config(self) -> ObserveConfig | None:
        settings = self._store.settings
        if not settings.get(CONF_OBSERVE_ENABLED, DEFAULT_OBSERVE_ENABLED):
            return None
        url, url_error = validate_url(settings.get(CONF_OBSERVE_URL))
        host_name = validate_host_name(settings.get(CONF_OBSERVE_HOST_NAME))
        key = validate_ingest_key(await self._secrets.async_get(CONF_OBSERVE_INGEST_KEY))
        interval = settings.get(CONF_OBSERVE_INTERVAL, DEFAULT_OBSERVE_INTERVAL)
        if url is None or host_name is None or key is None or not isinstance(interval, int):
            _LOGGER.warning(
                "Observe push is enabled but its settings are incomplete or invalid "
                "(%s); nothing is sent. Fix them in the HA SOC options.",
                url_error or "URL, host name, key or interval",
            )
            return None
        interval = max(MIN_OBSERVE_INTERVAL, min(MAX_OBSERVE_INTERVAL, interval))
        ca_pem, ca_error = validate_ca_pem(settings.get(CONF_OBSERVE_CA_PEM))
        fingerprint, fingerprint_error = validate_fingerprint(
            settings.get(CONF_OBSERVE_FINGERPRINT)
        )
        if ca_error or fingerprint_error or (ca_pem and fingerprint):
            _LOGGER.warning(
                "Observe push is enabled but its certificate trust settings are invalid; "
                "nothing is sent. Fix them in the HA SOC options."
            )
            return None
        return ObserveConfig(
            url=url,
            key=key,
            host_name=host_name,
            interval_seconds=interval,
            ca_pem=ca_pem,
            fingerprint=fingerprint,
        )

    async def async_start(self, entry: ConfigEntry) -> None:
        """Arm the timer when the push is enabled and configured; otherwise do nothing."""
        self.async_stop()
        self._entry = entry
        config = await self._async_load_config()
        if config is None:
            self._discard_carry(entry)
            async_delete_observe_key_issue(self.hass)
            return
        try:
            self._trust = await self.hass.async_add_executor_job(
                build_trust, config.ca_pem, config.fingerprint
            )
        except (ssl.SSLError, ValueError):
            _LOGGER.warning(
                "Observe push could not load the configured CA certificate; nothing is sent. "
                "Fix it in the HA SOC options."
            )
            self._discard_carry(entry)
            return
        self._config = config
        self._adopt_carry(entry, config)
        self._identity = await self._async_identity(config.host_name)
        self._unsub = async_track_time_interval(
            self.hass, self._async_timer, timedelta(seconds=config.interval_seconds)
        )
        entry.async_create_task(
            self.hass, self.async_push_once(), "HA SOC Observe initial push"
        )
        _LOGGER.info("Observe push enabled (every %s seconds)", config.interval_seconds)

    def _carry_store(self) -> dict[str, _Carry]:
        return self.hass.data.setdefault(DATA_QUEUE_CARRY, {})

    def _discard_carry(self, entry: ConfigEntry) -> None:
        carry = self._carry_store().pop(entry.entry_id, None)
        if carry is not None and carry.queue:
            _LOGGER.info("Observe push discarded %d queued payload(s)", len(carry.queue))

    def _adopt_carry(self, entry: ConfigEntry, config: ObserveConfig) -> None:
        """Take over the queue a stopped pusher left, if the destination is unchanged.

        A reload (the options flow, or a restart of the integration) builds a new pusher. The
        queue and the sent-key memory go with it unless the URL or host name changed, because
        queued payloads name the old host and were meant for the old server.
        """
        carry = self._carry_store().pop(entry.entry_id, None)
        if carry is None:
            return
        if (carry.url, carry.host_name) != (config.url, config.host_name):
            if carry.queue:
                _LOGGER.warning(
                    "Observe push dropped %d queued payload(s) because the URL or host name changed",
                    len(carry.queue),
                )
            return
        self._queue = carry.queue
        self._sent_log_keys = carry.sent_log_keys
        self._partial_retried = carry.partial_retried
        self._integration_series = carry.integration_series
        self._retry_at = carry.retry_at
        self._failures = carry.failures
        if carry.queue:
            _LOGGER.info("Observe push kept %d queued payload(s) across the reload", len(carry.queue))

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._config is not None and self._entry is not None:
            self._carry_store()[self._entry.entry_id] = _Carry(
                url=self._config.url,
                host_name=self._config.host_name,
                queue=self._queue,
                sent_log_keys=self._sent_log_keys,
                partial_retried=self._partial_retried,
                integration_series=self._integration_series,
                # A rejected key is retried at once after a reload: the owner may have fixed it.
                retry_at=0.0 if self._auth_rejected or not self._failures else self._retry_at,
                failures=0 if self._auth_rejected else self._failures,
            )
        self._config = None
        self._queue = deque()
        self._sent_log_keys = {}
        self._partial_retried = set()
        self._integration_series = set()
        self._trust = None
        self._retry_at = 0.0
        self._failures = 0
        self._auth_rejected = False
        self._reject_streak = 0
        self._rejected_issue = False
        async_delete_observe_rejected_issue(self.hass)

    async def _async_identity(self, host_name: str) -> otlp_mapper.Identity:
        from homeassistant.helpers import instance_id
        from homeassistant.helpers.system_info import async_get_system_info

        try:
            instance = await instance_id.async_get(self.hass)
            installation = (await async_get_system_info(self.hass)).get("installation_type", "")
        except Exception:  # noqa: BLE001 - identity extras are optional
            instance, installation = "", ""
        return otlp_mapper.Identity(
            host_name=host_name,
            instance_id=instance,
            version=HA_VERSION,
            installation_type=str(installation or ""),
        )

    @property
    def status(self) -> dict[str, Any]:
        """Counters and state for diagnostics. Never holds the key, URL or host name."""
        return {
            "active": self._config is not None,
            "interval_seconds": self._config.interval_seconds if self._config else None,
            "queue_length": len(self._queue),
            "queue_limit": MAX_QUEUE,
            "queue_bytes": sum(len(p.body) for p in self._queue),
            "queue_bytes_limit": MAX_QUEUE_BYTES,
            "compactions": self.compactions,
            "sent_ok": self.sent_ok,
            "dropped_overflow": self.dropped_overflow,
            "dropped_rejected": self.dropped_rejected,
            "rejected_items": self.rejected_items,
            "abandoned_log_payloads": self.abandoned_log_payloads,
            "auth_rejected": self._auth_rejected,
            "rejected_streak": self._reject_streak,
            "last_success": self.last_success,
            "last_status": self.last_status,
        }

    # -- one cycle ------------------------------------------------------------

    @callback
    def _async_timer(self, _now: Any) -> None:
        if self._entry is None:
            return
        self._entry.async_create_task(
            self.hass, self.async_push_once(), "HA SOC Observe push"
        )

    async def async_push_once(self) -> None:
        """Collect, queue and send. Never raises; a tick that overlaps a running one is skipped."""
        if self._config is None or self._lock.locked():
            return
        async with self._lock:
            try:
                await self._async_collect_and_enqueue()
                await self._async_drain()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - the timer must keep running
                # No traceback: a collector or mapper error message could carry the key.
                _LOGGER.error(
                    "Observe push cycle failed (%s): %s",
                    type(err).__name__,
                    self._redact(str(err)),
                )

    async def _async_collect_and_enqueue(self) -> None:
        assert self._identity is not None
        snapshot = await self._collector()
        now = self._wall()
        dropped_by_mapper: dict[str, int] = {}
        metrics = otlp_mapper.build_metrics(
            self._identity, snapshot, now, dropped_by_mapper, self._integration_series
        )
        logs = otlp_mapper.build_logs(self._identity, snapshot, now, dropped_by_mapper)
        if dropped_by_mapper:
            _LOGGER.warning(
                "Observe push left out rows beyond Observe's limits: %s",
                ", ".join(f"{kind}={count}" for kind, count in sorted(dropped_by_mapper.items())),
            )
        items: list[_Payload] = []
        if otlp_mapper.has_points(metrics):
            items.append(await self._async_payload("metrics", metrics))
        if otlp_mapper.has_records(logs):
            keys = _dedup_keys(logs)
            # A record is queued once: keys Observe already accepted and keys waiting in the
            # queue are left out, so an outage does not repeat every record in every payload.
            # A record without a key cannot be told apart and is always sent.
            fresh = keys.difference(self._sent_log_keys) - self._queued_log_keys()
            if not keys or fresh:
                if keys and fresh != keys:
                    logs = _only_logs(logs, fresh)
                payload = await self._async_payload("logs", logs)
                payload.dedup_keys = frozenset(fresh)
                items.append(payload)
        self._queue.extend(items)
        overflow = await self._async_enforce_bounds()
        if overflow:
            self.dropped_overflow += overflow
            _LOGGER.warning(
                "Observe push queue is full (%d payloads); dropped the %d oldest, "
                "%d dropped since start",
                MAX_QUEUE,
                overflow,
                self.dropped_overflow,
            )

    def _queued_log_keys(self) -> set[str]:
        keys: set[str] = set()
        for payload in self._queue:
            keys |= payload.dedup_keys
        return keys

    def _over_bound(self) -> bool:
        return len(self._queue) > MAX_QUEUE or sum(len(p.body) for p in self._queue) > MAX_QUEUE_BYTES

    async def _async_enforce_bounds(self) -> int:
        """Keep the queue inside its memory bound; returns how many payloads were dropped.

        The first resort is merging the queued metric payloads (see compact_metrics), which
        keeps the whole outage at a coarser resolution. The head of the queue is left alone
        because it may have been sent once already and must keep its Idempotency-Key. Only
        when merging cannot make room is the oldest payload dropped.
        """
        if not self._over_bound():
            return 0
        for interval in COMPACT_INTERVALS_SECONDS:
            if not await self._async_compact(interval):
                break
            if self._size_ok():
                # Whatever excess is left is payload count, which a wider interval cannot help.
                break
        dropped = 0
        while self._over_bound() and len(self._queue) > 1:
            # The oldest payload goes first, but a merged payload holds hours of metrics, so
            # it is only dropped when nothing else is left to drop.
            for index, payload in enumerate(self._queue):
                if not payload.compacted:
                    del self._queue[index]
                    break
            else:
                self._queue.popleft()
            dropped += 1
        return dropped

    def _size_ok(self) -> bool:
        return sum(len(p.body) for p in self._queue) <= MAX_QUEUE_BYTES and not any(
            p.compacted and len(p.body) > MAX_MERGED_BYTES for p in self._queue
        )

    async def _async_compact(self, interval: int) -> bool:
        """Merge every queued metrics payload but the head; True when anything changed.

        The merge may come out as several payloads (see compact_metrics_requests), placed where
        the first merged payload was.
        """
        indexes = [i for i, p in enumerate(self._queue) if i > 0 and p.signal == "metrics"]
        picked = set(indexes)
        if not indexes:
            return False
        bodies = [self._queue[i].body for i in indexes]
        merged_bodies = await self.hass.async_add_executor_job(_compact_bodies, bodies, interval)
        merged = [
            _Payload("metrics", body, uuid.uuid4().hex, compacted=True) for body in merged_bodies
        ]
        first = indexes[0]
        rebuilt: deque[_Payload] = deque()
        for i, payload in enumerate(self._queue):
            if i == first:
                rebuilt.extend(merged)
            elif i not in picked:
                rebuilt.append(payload)
        self._queue = rebuilt
        self.compactions += 1
        return True

    async def _async_payload(self, signal: str, request: dict[str, Any]) -> _Payload:
        body = await self.hass.async_add_executor_job(_encode, request)
        return _Payload(signal=signal, body=body, idempotency_key=uuid.uuid4().hex)

    async def _async_drain(self) -> None:
        while self._queue:
            if self._clock() < self._retry_at:
                return
            item = self._queue[0]
            outcome, delay = await self._async_send(item)
            if outcome in (_OK, _DROP, _AUTH) and self._queue and self._queue[0] is item:
                self._queue.popleft()
            if outcome == _OK:
                self._failures = 0
                self._reject_streak = 0
                self._retry_at = 0.0
                self.sent_ok += 1
                self.last_success = dt_util.utcnow().isoformat()
                self._note_log_keys(item)
                if self._auth_rejected:
                    self._auth_rejected = False
                    async_delete_observe_key_issue(self.hass)
                if self._rejected_issue:
                    self._rejected_issue = False
                    async_delete_observe_rejected_issue(self.hass)
            elif outcome == _DROP:
                self.dropped_rejected += 1
                self._reject_streak += 1
                if self._reject_streak >= REJECT_THRESHOLD:
                    self._rejected_issue = True
                    async_create_observe_rejected_issue(self.hass, int(self.last_status or 0))
                    self._retry_at = self._clock() + min(
                        BACKOFF_BASE_SECONDS * 2 ** (self._reject_streak - REJECT_THRESHOLD),
                        BACKOFF_MAX_SECONDS,
                    )
                    return
            elif outcome == _AUTH:
                self.dropped_rejected += 1
                self._auth_rejected = True
                async_create_observe_key_issue(self.hass)
                self._retry_at = self._clock() + AUTH_BACKOFF_SECONDS
                return
            else:
                self._failures += 1
                self._retry_at = self._clock() + (
                    delay
                    if delay is not None
                    else min(BACKOFF_BASE_SECONDS * 2 ** (self._failures - 1), BACKOFF_MAX_SECONDS)
                )
                return

    def _note_log_keys(self, item: _Payload) -> None:
        """Remember which log records Observe has taken, once a logs payload was accepted.

        Observe's answer does not say which records of a partial rejection were refused, so
        the keys of such a payload are left unsent: the next cycle builds the same records
        again, Observe skips the ones it already holds by dedup key, and the refused ones get
        a second try. A key rejected a second time is given up on, marked sent so it is not
        retried for ever, and reported.
        """
        keys = item.dedup_keys
        if item.signal == "logs" and item.rejected:
            given_up = keys & self._partial_retried
            if given_up:
                self.abandoned_log_payloads += 1
                _LOGGER.error(
                    "Observe rejected log records again on the retry; giving up on %d record "
                    "key(s), %d rejected in this answer",
                    len(given_up),
                    item.rejected,
                )
                self._partial_retried = (self._partial_retried - given_up) | (keys - given_up)
                keys = given_up
            else:
                self._partial_retried |= keys
                return
        else:
            self._partial_retried -= keys
        self._sent_log_keys.update(dict.fromkeys(sorted(keys)))
        while len(self._sent_log_keys) > SENT_KEYS_LIMIT:
            del self._sent_log_keys[next(iter(self._sent_log_keys))]

    # -- one request ----------------------------------------------------------

    def _redact(self, text: str) -> str:
        text = text[:MESSAGE_LIMIT]
        key = self._config.key if self._config else None
        return text.replace(key, REDACTED_PLACEHOLDER) if key else text

    def _retry_after(self, header: str | None) -> float | None:
        if not header:
            return None
        header = header.strip()
        if header.isdigit():
            seconds = float(header)
        else:
            try:
                seconds = (parsedate_to_datetime(header) - dt_util.utcnow()).total_seconds()
            except (TypeError, ValueError):
                return None
        return max(0.0, min(seconds, MAX_RETRY_AFTER_SECONDS))

    async def _async_send(self, item: _Payload) -> tuple[str, float | None]:
        assert self._config is not None
        config = self._config
        session = async_get_clientsession(self.hass)
        headers = {
            "Authorization": f"Bearer {config.key}",
            "Content-Type": "application/json",
            "Content-Encoding": "gzip",
            "Idempotency-Key": item.idempotency_key,
        }
        options: dict[str, Any] = {} if self._trust is None else {"ssl": self._trust}
        try:
            async with session.post(
                f"{config.url}/v1/{item.signal}",
                data=item.body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
                allow_redirects=False,
                **options,
            ) as response:
                status = response.status
                retry_after = self._retry_after(response.headers.get("Retry-After"))
                body = await response.content.read(RESPONSE_READ_LIMIT)
        except (aiohttp.ClientError, TimeoutError) as err:
            self.last_status = type(err).__name__
            _LOGGER.warning(
                "Observe push of %s failed (%s); it will be retried",
                item.signal,
                self._redact(type(err).__name__),
            )
            return _RETRY, None

        self.last_status = status
        if status == 200:
            item.rejected = self._note_partial_success(item.signal, body)
            return _OK, None
        if status in (401, 403):
            _LOGGER.warning(
                "Observe refused the ingest key or host name (HTTP %s); see Repairs", status
            )
            return _AUTH, None
        if status in (408, 429) or status >= 500:
            _LOGGER.warning(
                "Observe answered HTTP %s to a %s push; retrying later", status, item.signal
            )
            return _RETRY, retry_after
        reason = " (payload too large)" if status == 413 else ""
        _LOGGER.warning(
            "Observe refused a %s push with HTTP %s%s; that payload was dropped",
            item.signal,
            status,
            reason,
        )
        return _DROP, None

    def _note_partial_success(self, signal: str, body: bytes) -> int:
        """Log a partialSuccess answer and return how many items Observe rejected."""
        if not body:
            return 0
        try:
            partial = json.loads(body).get("partialSuccess") or {}
        except (ValueError, AttributeError):
            return 0
        raw = partial.get("rejectedDataPoints", partial.get("rejectedLogRecords", 0))
        try:
            rejected = int(raw or 0)
        except (TypeError, ValueError):
            rejected = 0
        message = str(partial.get("errorMessage") or "")
        if rejected or message:
            self.rejected_items += rejected
            _LOGGER.warning(
                "Observe accepted a %s push but rejected %d item(s): %s",
                signal,
                rejected,
                self._redact(message) or "no reason given",
            )
        return rejected
