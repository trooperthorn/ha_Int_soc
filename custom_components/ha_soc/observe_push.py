"""Optional push of Home Assistant system detail to Observe over OTLP JSON.

Off by default. When the owner enables it in the options flow, a timer collects a snapshot
of data HA SOC already holds (otlp_mapper.py turns it into OTLP), queues the two requests
and sends them to Observe's POST /v1/metrics and /v1/logs on Home Assistant's shared
aiohttp session. See docs/design.md, "Observe push".

Delivery rules:
- The queue is bounded and in memory only. When it is full the oldest payload is dropped
  and counted, and the drop is logged as a warning.
- A payload keeps one Idempotency-Key for its whole life, so a retry after a lost response
  is recognised by Observe instead of stored twice.
- Retry-After is honoured. Without it a failed send backs off exponentially. Waiting is a
  stored "not before" time checked on the next tick, never a sleep.
- 401 and 403 raise a Repairs issue and drop that payload; any accepted push removes it.
  Other 4xx answers mean the payload itself is wrong, so it is dropped and counted.
- The ingest key is only ever placed in the Authorization header. It is removed from every
  log line and never appears in diagnostics or the status dict.
"""
from __future__ import annotations

import asyncio
import gzip
import ipaddress
import json
import logging
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
    CONF_OBSERVE_ENABLED,
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
from .repairs import async_create_observe_key_issue, async_delete_observe_key_issue
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
# Container samples younger than this are taken from the resource watchdog.
WATCHDOG_SAMPLE_MAX_AGE_SECONDS = 90
# Crash bundles and the Supervisor resolution state change rarely; refreshed this often.
SLOW_REFRESH_SECONDS = 600
SUPERVISOR_TIMEOUT_SECONDS = 10
RESPONSE_READ_LIMIT = 65536
MESSAGE_LIMIT = 200
SENT_KEYS_LIMIT = 5000

ERROR_INVALID_URL = "invalid_url"
ERROR_INSECURE_URL = "insecure_url"
ERROR_KEY_REQUIRED = "key_required"
ERROR_INVALID_KEY = "invalid_key"
ERROR_INVALID_HOST_NAME = "invalid_host_name"
ERROR_INVALID_INTERVAL = "invalid_interval"


# ---------------------------------------------------------------------------
# Validation (used by the options flow and again when the push starts)
# ---------------------------------------------------------------------------


def _is_private_host(host: str) -> bool:
    """True for localhost and for IP literals in a private, loopback or link-local range.

    A DNS name is never accepted for plain http because it can resolve anywhere.
    """
    if host.lower() == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


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


def validate_options(
    user_input: dict[str, Any], *, key_already_set: bool
) -> tuple[dict[str, str], dict[str, Any], str | None]:
    """Check one options-flow submission.

    Returns (errors by field, settings changes, new ingest key or None). The key is blank
    when the existing one is kept. Fields are only required when the push is enabled, but
    anything that is filled in must be valid either way.
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

    interval = user_input.get(CONF_OBSERVE_INTERVAL, DEFAULT_OBSERVE_INTERVAL)
    try:
        interval = int(interval)
    except (TypeError, ValueError):
        interval = None
    if interval is None or not MIN_OBSERVE_INTERVAL <= interval <= MAX_OBSERVE_INTERVAL:
        errors[CONF_OBSERVE_INTERVAL] = ERROR_INVALID_INTERVAL

    changes = {
        CONF_OBSERVE_ENABLED: enabled,
        CONF_OBSERVE_URL: url,
        CONF_OBSERVE_HOST_NAME: host_name,
        CONF_OBSERVE_INTERVAL: interval,
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
        from .containers import async_container_resources

        fresh = await async_container_resources(self.hass)
        return fresh if fresh.get("available") else None

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


@dataclass(frozen=True)
class ObserveConfig:
    url: str
    key: str = field(repr=False)
    host_name: str
    interval_seconds: int


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
        self._sent_log_keys: set[str] = set()
        self._auth_rejected = False
        # Counters reported by status; none of them hold a secret.
        self.dropped_overflow = 0
        self.dropped_rejected = 0
        self.rejected_items = 0
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
        return ObserveConfig(url=url, key=key, host_name=host_name, interval_seconds=interval)

    async def async_start(self, entry: ConfigEntry) -> None:
        """Arm the timer when the push is enabled and configured; otherwise do nothing."""
        self.async_stop()
        self._entry = entry
        config = await self._async_load_config()
        if config is None:
            async_delete_observe_key_issue(self.hass)
            return
        self._config = config
        self._identity = await self._async_identity(config.host_name)
        self._unsub = async_track_time_interval(
            self.hass, self._async_timer, timedelta(seconds=config.interval_seconds)
        )
        entry.async_create_task(
            self.hass, self.async_push_once(), "HA SOC Observe initial push"
        )
        _LOGGER.info("Observe push enabled (every %s seconds)", config.interval_seconds)

    @callback
    def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        self._config = None
        self._queue.clear()
        self._retry_at = 0.0
        self._failures = 0
        self._auth_rejected = False

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
            "sent_ok": self.sent_ok,
            "dropped_overflow": self.dropped_overflow,
            "dropped_rejected": self.dropped_rejected,
            "rejected_items": self.rejected_items,
            "auth_rejected": self._auth_rejected,
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
            except Exception:  # noqa: BLE001 - the timer must keep running
                _LOGGER.exception("Observe push cycle failed")

    async def _async_collect_and_enqueue(self) -> None:
        assert self._identity is not None
        snapshot = await self._collector()
        now = self._wall()
        dropped_by_mapper: dict[str, int] = {}
        metrics = otlp_mapper.build_metrics(self._identity, snapshot, now, dropped_by_mapper)
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
            # Logs are keyed in Observe, so a request whose records were all accepted before
            # carries nothing new. Queued-but-unsent keys are not tracked; Observe de-duplicates.
            if not keys or not keys <= self._sent_log_keys:
                payload = await self._async_payload("logs", logs)
                payload.dedup_keys = keys
                items.append(payload)
        overflow = 0
        for payload in items:
            self._queue.append(payload)
            while len(self._queue) > MAX_QUEUE:
                self._queue.popleft()
                overflow += 1
        if overflow:
            self.dropped_overflow += overflow
            _LOGGER.warning(
                "Observe push queue is full (%d payloads); dropped the %d oldest, "
                "%d dropped since start",
                MAX_QUEUE,
                overflow,
                self.dropped_overflow,
            )

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
                self._retry_at = 0.0
                self.sent_ok += 1
                self.last_success = dt_util.utcnow().isoformat()
                self._sent_log_keys |= item.dedup_keys
                if len(self._sent_log_keys) > SENT_KEYS_LIMIT:
                    self._sent_log_keys = set(item.dedup_keys)
                if self._auth_rejected:
                    self._auth_rejected = False
                    async_delete_observe_key_issue(self.hass)
            elif outcome == _DROP:
                self.dropped_rejected += 1
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
        try:
            async with session.post(
                f"{config.url}/v1/{item.signal}",
                data=item.body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS),
                allow_redirects=False,
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
            self._note_partial_success(item.signal, body)
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

    def _note_partial_success(self, signal: str, body: bytes) -> None:
        if not body:
            return
        try:
            partial = json.loads(body).get("partialSuccess") or {}
        except (ValueError, AttributeError):
            return
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
