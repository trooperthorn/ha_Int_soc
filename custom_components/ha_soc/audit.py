"""Append-only, hash-chained audit log for HA SOC.

It listens only to bus events, one dispatcher signal, and log records core
already emits; it never touches ``state_changed`` or a ``MATCH_ALL`` listener.
What is captured, inferred, and out of scope is documented in docs/design.md
and docs/security.md.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from functools import partial
import hashlib
import json
import logging
import os
import re
from collections import deque
from typing import Any, Callable

from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_SERVICE,
    ATTR_SERVICE_DATA,
    EVENT_CALL_SERVICE,
    EVENT_CORE_CONFIG_UPDATE,
    EVENT_HOMEASSISTANT_STOP,
    EVENT_PANELS_UPDATED,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import AUDIT_STORAGE_SUBDIR, REDACTED_PLACEHOLDER, SECRET_SETTING_KEYS
from .store import HaSocData

# Literal fallbacks are what core actually fires; an import failure must not break setup.
try:
    from homeassistant.auth import (
        EVENT_USER_ADDED,
        EVENT_USER_REMOVED,
        EVENT_USER_UPDATED,
    )
except ImportError:  # pragma: no cover - older/newer core layout fallback
    EVENT_USER_ADDED = "user_added"
    EVENT_USER_UPDATED = "user_updated"
    EVENT_USER_REMOVED = "user_removed"

# Duplicated rather than imported from users.py so this module stays independently testable.
try:
    from homeassistant.auth.const import (
        TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        TOKEN_TYPE_SYSTEM,
    )
except ImportError:  # pragma: no cover - older/newer core layout fallback
    try:
        from homeassistant.auth.models import (
            TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
            TOKEN_TYPE_SYSTEM,
        )
    except ImportError:
        TOKEN_TYPE_SYSTEM = "system"
        TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN = "long_lived_access_token"

try:
    from homeassistant.helpers.area_registry import EVENT_AREA_REGISTRY_UPDATED
    from homeassistant.helpers.category_registry import (
        EVENT_CATEGORY_REGISTRY_UPDATED,
    )
    from homeassistant.helpers.device_registry import EVENT_DEVICE_REGISTRY_UPDATED
    from homeassistant.helpers.floor_registry import EVENT_FLOOR_REGISTRY_UPDATED
    from homeassistant.helpers.label_registry import EVENT_LABEL_REGISTRY_UPDATED
except ImportError:  # pragma: no cover - older/newer core layout fallback
    EVENT_AREA_REGISTRY_UPDATED = "area_registry_updated"
    EVENT_CATEGORY_REGISTRY_UPDATED = "category_registry_updated"
    EVENT_DEVICE_REGISTRY_UPDATED = "device_registry_updated"
    EVENT_FLOOR_REGISTRY_UPDATED = "floor_registry_updated"
    EVENT_LABEL_REGISTRY_UPDATED = "label_registry_updated"

# Config entries have no bus event; SignalType subclasses str, so the literal reaches the same slot.
try:
    from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED
except ImportError:  # pragma: no cover - older/newer core layout fallback
    SIGNAL_CONFIG_ENTRY_CHANGED = "config_entry_changed"

# These contextvars are the only ambient "who did this" signal; a missing import degrades to none.
try:
    from homeassistant.components.websocket_api import current_connection
except ImportError:  # pragma: no cover - older/newer core layout fallback
    current_connection = None  # type: ignore[assignment]
try:
    from homeassistant.helpers.http import current_request
except ImportError:  # pragma: no cover - older/newer core layout fallback
    current_request = None  # type: ignore[assignment]
try:
    from homeassistant.components.http.const import KEY_HASS_USER
except ImportError:  # pragma: no cover - older/newer core layout fallback
    KEY_HASS_USER = "hass_user"

_LOGGER = logging.getLogger(__name__)

Unsub = Callable[[], None]

_FLUSH_INTERVAL = timedelta(seconds=30)
_POLL_INTERVAL = timedelta(seconds=30)

_CHAIN_HEAD_FILENAME = "chain_head.json"
# Group 2 is the segment index (absent = 0), used only to list files in written order.
_FILENAME_RE = re.compile(r"^audit-(\d{4}-\d{2}-\d{2})(?:\.(\d+))?\.jsonl$")
_GENESIS_PREV_HASH = ""

# Per-segment roll size within one day; see docs/operations.md.
_SEGMENT_MAX_BYTES = 32 * 1024 * 1024

_DEFAULT_QUERY_LOOKBACK = timedelta(days=7)

# Exact key match, case-insensitive, any depth: "token_id" stays visible, "token" does not.
_REDACTED_SERVICE_DATA_KEYS = frozenset(
    {
        "password",
        "token",
        "code",
        "api_key",
        "apikey",
        "secret",
        "pin",
        "passphrase",
        "access_token",
        "refresh_token",
        "client_secret",
        "authorization",
        # The Probe pairing secret rides in service_data of every Probe service call.
        "probe_secret",
    }
)
# What a notification said is personal; only that one was sent is audited.
_REDACTED_MESSAGE_DOMAINS = frozenset({"notify", "tts", "persistent_notification"})

# Flushed immediately instead of on the 30 s timer; public so tests can assert the set.
IMMEDIATE_FLUSH_CATEGORIES = frozenset(
    {
        "user_added",
        "user_updated",
        "user_removed",
        "soc_config_change",
        "detection_status_changed",
        "probe_auth_rejected",
        "audit_chain_reset",
        "privileged_read",
        "external_audit_chain_break",
        "external_audit_rejected",
        "programming_session",
    }
)
IMMEDIATE_FLUSH_PREFIXES = ("firewall_",)

# Public: health.py's audit_ban_logger_silenced check reads it.
BAN_LOGGER_NAME = "homeassistant.components.http.ban"
# Current core logs the ban warning preformatted with no args; this regex is the live path.
_BAN_MESSAGE_RE = re.compile(r"from\s+(?P<host>\S+)\s+\((?P<addr>[^)]+)\)")


def _normalize_entity_ids(value: Any) -> list[str]:
    """Normalize a service_data['entity_id']-shaped value to a list of str."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value]
    return [str(value)]


def _redact_service_data(
    domain: str | None, service: str | None, value: Any
) -> Any:
    """Recursively mask credential-shaped keys in a detail payload.

    Values are replaced even when empty so the log never reveals whether a
    credential field was filled in. Rules are in docs/security.md.
    """
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, val in value.items():
            key_lower = key.lower() if isinstance(key, str) else None
            if key_lower in _REDACTED_SERVICE_DATA_KEYS:
                redacted[key] = REDACTED_PLACEHOLDER
            elif (
                key_lower in ("message", "title")
                and service is not None
                and domain in _REDACTED_MESSAGE_DOMAINS
            ):
                redacted[key] = REDACTED_PLACEHOLDER
            elif key_lower == "payload" and domain == "mqtt" and service == "publish":
                redacted[key] = REDACTED_PLACEHOLDER
            else:
                redacted[key] = _redact_service_data(domain, service, val)
        return redacted
    if isinstance(value, list):
        return [_redact_service_data(domain, service, item) for item in value]
    return value


def _redact_secrets_deep(value: Any) -> Any:
    """Recursively mask any dict value stored under a known secret key."""
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_PLACEHOLDER
                if key in SECRET_SETTING_KEYS and val not in (None, "")
                else _redact_secrets_deep(val)
            )
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact_secrets_deep(item) for item in value]
    return value


class _FailedLoginLogHandler(logging.Handler):
    """Turns http.ban's invalid-auth warnings into login_fail audit records.

    ``emit()`` may run on a worker thread: parse only, hand off through
    ``call_soon_threadsafe``, never call async code, never raise.
    """

    def __init__(self, hass: HomeAssistant, on_failed_login: Callable[[str], None]) -> None:
        super().__init__(level=logging.WARNING)
        self._hass = hass
        self._on_failed_login = on_failed_login

    def emit(self, record: logging.LogRecord) -> None:
        try:
            if record.levelno < logging.WARNING:
                return
            ip = self._extract_ip(record)
            if not ip:
                return
            self._hass.loop.call_soon_threadsafe(self._on_failed_login, ip)
        except Exception:  # noqa: BLE001 - a logging handler must never raise
            pass

    @staticmethod
    def _extract_ip(record: logging.LogRecord) -> str | None:
        args = record.args
        # The args tuple is a compatibility path; current core sends a preformatted message.
        if isinstance(args, tuple) and len(args) >= 2 and args[1]:
            return str(args[1])
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - defensive, see class docstring
            return None
        match = _BAN_MESSAGE_RE.search(message)
        if match:
            return match.group("addr")
        return None


class AuditLog:
    """Captures, hash-chains, and stores HA SOC's security-relevant events."""

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self._store = store
        self._dir_path = hass.config.path(".storage", AUDIT_STORAGE_SUBDIR)

        self._buffer: deque[dict[str, Any]] = deque()
        self._flush_lock = asyncio.Lock()
        self._seq = 0
        self._prev_hash = _GENESIS_PREV_HASH
        # Retention anchor: newest expired record's seq/hash; None until retention deletes something.
        self._anchor: dict[str, Any] | None = None
        # Chain-reset marker {seq, hash, at, disk_head_seq}; every head rewrite must preserve it.
        self._reset: dict[str, Any] | None = None
        # Lets reset detection tell "directory wiped" from "head rolled back".
        self._head_file_found = False
        # One in-flight immediate flush covers a burst of records.
        self._flush_task: asyncio.Task[None] | None = None
        # Gates immediate flushing; flushing before the head loads would chain from genesis.
        self._head_loaded = False

        self._unsubs: list[Unsub] = []
        self._cancel_flush_timer: Unsub | None = None
        self._cancel_poll_timer: Unsub | None = None
        self._ban_handler: _FailedLoginLogHandler | None = None

        # (last_used_at, last_used_ip) snapshot, keyed by refresh_token.id,
        # used by the login/token-creation poll loop.
        self._token_snapshot: dict[str, tuple[datetime | None, str | None]] = {}
        self._first_poll_done = False

        # Token ids already given a session_seen record; not persisted, so a restart announces again.
        self._seen_ws_token_ids: set[str] = set()
        self._syslog_exporter: Any | None = None

    @callback
    def async_set_syslog_exporter(self, exporter: Any) -> None:
        """Attach the off-box sink without creating an import cycle."""
        self._syslog_exporter = exporter

    async def async_start(self) -> None:
        """Create storage, load the chain head, and start capturing."""
        await self.hass.async_add_executor_job(self._sync_ensure_dir)
        await self.hass.async_add_executor_job(self._sync_load_chain_head)
        # Must run after the head loads and before any listener logs, so the reset record is first.
        self._async_detect_chain_reset()

        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_CALL_SERVICE, self._handle_call_service)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_USER_ADDED, self._handle_user_added)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_USER_UPDATED, self._handle_user_updated)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(EVENT_USER_REMOVED, self._handle_user_removed)
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                "lovelace_updated", self._handle_lovelace_updated
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                "entity_registry_updated", self._handle_entity_registry_updated
            )
        )
        # HassJob unwraps partials before checking @callback, so these dispatch inline.
        for event_type, category, id_key in (
            (EVENT_DEVICE_REGISTRY_UPDATED, "device_registry_change", "device_id"),
            (EVENT_AREA_REGISTRY_UPDATED, "area_registry_change", "area_id"),
            (EVENT_FLOOR_REGISTRY_UPDATED, "floor_registry_change", "floor_id"),
            (EVENT_LABEL_REGISTRY_UPDATED, "label_registry_change", "label_id"),
            (
                EVENT_CATEGORY_REGISTRY_UPDATED,
                "category_registry_change",
                "category_id",
            ),
        ):
            self._unsubs.append(
                self.hass.bus.async_listen(
                    event_type,
                    partial(self._handle_registry_updated, category, id_key),
                )
            )
        self._unsubs.append(
            self.hass.bus.async_listen(
                EVENT_CORE_CONFIG_UPDATE, self._handle_core_config_updated
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                EVENT_PANELS_UPDATED, self._handle_panels_updated
            )
        )
        self._unsubs.append(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._handle_config_entry_changed
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                "elkm1.programming_started", partial(self._handle_programming_session, "started")
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen(
                "elkm1.programming_ended", partial(self._handle_programming_session, "ended")
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self._async_flush
            )
        )

        self._ban_handler = _FailedLoginLogHandler(self.hass, self._on_failed_login)
        logging.getLogger(BAN_LOGGER_NAME).addHandler(self._ban_handler)

        self._cancel_flush_timer = async_track_time_interval(
            self.hass, self._async_flush, _FLUSH_INTERVAL
        )
        self._cancel_poll_timer = async_track_time_interval(
            self.hass, self._async_poll_tokens, _POLL_INTERVAL
        )

    async def async_stop(self) -> None:
        """Reverse everything async_start registered, then flush once more."""
        if self._cancel_flush_timer is not None:
            self._cancel_flush_timer()
            self._cancel_flush_timer = None
        if self._cancel_poll_timer is not None:
            self._cancel_poll_timer()
            self._cancel_poll_timer = None

        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

        if self._ban_handler is not None:
            logging.getLogger(BAN_LOGGER_NAME).removeHandler(self._ban_handler)
            self._ban_handler = None

        await self._async_flush()

    @callback
    def _async_detect_chain_reset(self) -> None:
        """Compare the loaded on-disk head against the store's mirror.

        An on-disk head AHEAD of the mirror is normal: the mirror's save is
        debounced. Behind or absent means a wipe or rollback.
        """
        mirror = self._store.data.get("audit_head")
        if not isinstance(mirror, dict):
            return
        try:
            mirror_seq = int(mirror.get("seq"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return
        mirror_hash = mirror.get("hash")
        if mirror_seq <= 0 or not isinstance(mirror_hash, str) or not mirror_hash:
            return
        if self._seq >= mirror_seq:
            return

        disk_head: dict[str, Any] | None = None
        if self._head_file_found:
            disk_head = {"seq": self._seq, "prev_hash": self._prev_hash}
        _LOGGER.warning(
            "HA SOC audit log: the on-disk chain head (%s) is behind the "
            "store's mirror of the last flushed head (seq %d). The audit "
            "directory was wiped, replaced, or rolled back. Continuing the "
            "chain from the mirrored head and raising a Repairs issue.",
            "absent" if disk_head is None else f"seq {self._seq}",
            mirror_seq,
        )

        self._reset = {
            "seq": mirror_seq,
            "hash": mirror_hash,
            "at": dt_util.utcnow().isoformat(),
            "disk_head_seq": self._seq if self._head_file_found else None,
        }
        # Continue from the mirror so the reset record itself chains from the mirrored hash.
        self._seq = mirror_seq
        self._prev_hash = mirror_hash

        self.async_log(
            "audit_chain_reset",
            detail={
                "store_head": dict(mirror),
                "disk_head": disk_head,
                "actor_source": "system",
            },
        )

        # Lazy import keeps this module's import graph minimal.
        from .repairs import async_create_audit_chain_reset_issue

        async_create_audit_chain_reset_issue(
            self.hass,
            store_seq=mirror_seq,
            disk_seq=self._reset["disk_head_seq"],
        )

    @callback
    def _resolve_actor(self, event: Event) -> tuple[str | None, str]:
        """Best-effort acting user for an event, plus how it was recovered.

        Returns ``(user_id, source)``; only ``event_context`` is
        authoritative, the contextvar sources are correlational.
        """
        user_id = event.context.user_id
        if user_id is not None:
            return user_id, "event_context"
        return self._resolve_actor_ambient()

    @callback
    def _resolve_actor_ambient(self) -> tuple[str | None, str]:
        """Ambient-only actor recovery, for signals that carry no Event.

        A contextvar hit is correlation with the active session, never
        proof of who acted.
        """
        if current_connection is not None:
            conn = current_connection.get()
            if conn is not None:
                self._note_ws_session(conn)
                user = getattr(conn, "user", None)
                return getattr(user, "id", None), "ws_connection"
        if current_request is not None:
            request = current_request.get()
            if request is not None:
                user = request.get(KEY_HASS_USER)
                if user is not None:
                    return user.id, "http_request"
        return None, "system"

    @callback
    def _note_ws_session(self, conn: Any) -> None:
        """Emit one synthetic session_seen record per refresh token."""
        token_id = getattr(conn, "refresh_token_id", None)
        if token_id is None or token_id in self._seen_ws_token_ids:
            return
        self._seen_ws_token_ids.add(token_id)
        user = getattr(conn, "user", None)
        self.async_log(
            "session_seen",
            user_id=getattr(user, "id", None),
            detail={
                "refresh_token_id": token_id,
                "note": (
                    "first audited activity observed for this WebSocket "
                    "session this runtime; long-lived access token bearer "
                    "usage is otherwise invisible to this module, so the "
                    "absence of a session_seen record does not mean the "
                    "absence of a session"
                ),
            },
        )

    @callback
    def _handle_call_service(self, event: Event) -> None:
        # An attempted call, not an outcome. No ambient fallback: this event carries the real Context.
        domain = event.data.get(ATTR_DOMAIN)
        service = event.data.get(ATTR_SERVICE)
        service_data = event.data.get(ATTR_SERVICE_DATA)
        if not isinstance(service_data, dict):
            service_data = {}
        entity_ids = _normalize_entity_ids(service_data.get("entity_id"))
        # No redaction here: async_log is the single redaction chokepoint.
        detail = dict(service_data)
        # Core merges the target block into service_data; non-entity targets go to detail["targets"].
        targets = {
            key: _normalize_entity_ids(service_data.get(key))
            for key in ("area_id", "device_id", "label_id", "floor_id")
            if service_data.get(key) is not None
        }
        if targets:
            detail["targets"] = targets
        context = event.context
        self.async_log(
            "service_call",
            user_id=context.user_id,
            domain=domain,
            service=service,
            entity_ids=entity_ids,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail=detail,
        )

    async def _handle_user_added(self, event: Event) -> None:
        await self._async_log_user_lifecycle("user_added", event)

    async def _handle_user_updated(self, event: Event) -> None:
        await self._async_log_user_lifecycle("user_updated", event)

    async def _async_log_user_lifecycle(self, category: str, event: Event) -> None:
        # event.data["user_id"] is the SUBJECT; the actor is recovered ambiently before the first await.
        actor_id, source = self._resolve_actor(event)
        target_user_id = event.data.get("user_id")
        name = await self._async_resolve_user_name(target_user_id)
        self.async_log(
            category,
            user_id=actor_id,
            detail={
                "target_user_id": target_user_id,
                "target_name": name,
                "actor_source": source,
            },
        )

    @callback
    def _handle_user_removed(self, event: Event) -> None:
        # The user is already gone, so no name to resolve; event.data["user_id"] is the SUBJECT.
        actor_id, source = self._resolve_actor(event)
        self.async_log(
            "user_removed",
            user_id=actor_id,
            detail={
                "target_user_id": event.data.get("user_id"),
                "actor_source": source,
            },
        )

    async def _async_resolve_user_name(self, user_id: str | None) -> str | None:
        if user_id is None:
            return None
        try:
            user = await self.hass.auth.async_get_user(user_id)
        except Exception:  # noqa: BLE001 - best-effort enrichment only
            return None
        return user.name if user is not None else None

    @callback
    @callback
    def _handle_programming_session(self, phase: str, event: Event) -> None:
        """A panel programming session the elkm1 integration reported.

        The event carries the tool's claim (source, user, purpose) and whether
        the panel's own status matched it; an unattributed session is the
        one worth reading.
        """
        data = dict(event.data)
        user = data.get("user") or None
        self.async_log(
            "programming_session",
            user_id=user,
            context_id=event.context.id,
            detail={
                "phase": phase,
                "source": data.get("source"),
                "purpose": data.get("purpose"),
                "attributed": bool(data.get("attributed")),
                "rp_seen": bool(data.get("rp_seen")),
                "started": data.get("started"),
                "ended": data.get("ended"),
            },
        )

    def _handle_lovelace_updated(self, event: Event) -> None:
        # No Context on lovelace_updated; the actor is recovered ambiently.
        user_id, source = self._resolve_actor(event)
        context = event.context
        self.async_log(
            "lovelace_change",
            user_id=user_id,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"url_path": event.data.get("url_path"), "actor_source": source},
        )

    @callback
    def _handle_entity_registry_updated(self, event: Event) -> None:
        action = event.data.get("action")
        entity_id = event.data.get("entity_id")
        # "changes" holds the OLD values; new values must be read from the registry itself.
        changes = event.data.get("changes") or {}
        user_id, source = self._resolve_actor(event)
        context = event.context
        self.async_log(
            "entity_registry_change",
            user_id=user_id,
            entity_ids=[entity_id] if entity_id else [],
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"action": action, "changes": changes, "actor_source": source},
        )

    @callback
    def _handle_registry_updated(
        self, category: str, id_key: str, event: Event
    ) -> None:
        """Shared handler for the device/area/floor/label/category registries.

        "changes" carries the OLD values of the changed fields, never the
        new ones.
        """
        user_id, source = self._resolve_actor(event)
        context = event.context
        self.async_log(
            category,
            user_id=user_id,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={
                "action": event.data.get("action"),
                id_key: event.data.get(id_key),
                "changes": event.data.get("changes") or {},
                "actor_source": source,
            },
        )

    @callback
    def _handle_config_entry_changed(self, change: Any, entry: Any) -> None:
        """Log a config entry being added, removed, or updated.

        Dispatcher signal, so no Event and no Context; ``change`` is core's
        ConfigEntryChange StrEnum.
        """
        user_id, source = self._resolve_actor_ambient()
        disabled_by = getattr(entry, "disabled_by", None)
        self.async_log(
            "config_entry_change",
            user_id=user_id,
            domain=getattr(entry, "domain", None),
            detail={
                "change": str(change),
                "entry_id": getattr(entry, "entry_id", None),
                "title": getattr(entry, "title", None),
                "disabled_by": str(disabled_by) if disabled_by is not None else None,
                "actor_source": source,
            },
        )

    @callback
    def _handle_core_config_updated(self, event: Event) -> None:
        # Startup fires this twice with an empty payload; skip those.
        if not event.data:
            return
        user_id, source = self._resolve_actor(event)
        context = event.context
        self.async_log(
            "core_config_change",
            user_id=user_id,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"changes": dict(event.data), "actor_source": source},
        )

    @callback
    def _handle_panels_updated(self, event: Event) -> None:
        # Tripwire only: the payload is empty and core has no per-dashboard CRUD event.
        user_id, source = self._resolve_actor(event)
        context = event.context
        self.async_log(
            "dashboard_panels_change",
            user_id=user_id,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"actor_source": source},
        )

    def _on_failed_login(self, ip: str) -> None:
        """Runs on the event loop, scheduled via call_soon_threadsafe."""
        self.async_log("login_fail", ip=ip)

    async def _async_poll_tokens(self, _now: Any = None) -> None:
        """Infer login_ok / token_created from refresh-token activity.

        No bus event exists for either, so this diffs against the previous
        poll's snapshot.
        """
        try:
            users = await self.hass.auth.async_get_users()
        except Exception:  # noqa: BLE001 - never let the poll loop die
            _LOGGER.exception("HA SOC audit log: failed polling users/tokens")
            return

        new_snapshot: dict[str, tuple[datetime | None, str | None]] = {}
        events: list[tuple[str, str | None, str | None, dict[str, Any] | None]] = []

        for user in users:
            for token in user.refresh_tokens.values():
                if token.token_type == TOKEN_TYPE_SYSTEM:
                    continue
                previous = self._token_snapshot.get(token.id)
                new_snapshot[token.id] = (token.last_used_at, token.last_used_ip)

                if not self._first_poll_done:
                    # Seed only: no fake logins for pre-existing sessions at restart.
                    continue

                # detail.new_token tells a new token from an advanced last_used_at; detections.py relies on it.
                if previous is None:
                    if token.token_type == TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN:
                        events.append(("token_created", user.id, token.last_used_ip, None))
                    else:
                        events.append(
                            ("login_ok", user.id, token.last_used_ip, {"new_token": True})
                        )
                else:
                    prev_last_used_at, _prev_ip = previous
                    if (
                        token.last_used_at is not None
                        and token.last_used_at != prev_last_used_at
                    ):
                        events.append(
                            ("login_ok", user.id, token.last_used_ip, {"new_token": False})
                        )

        self._token_snapshot = new_snapshot
        self._first_poll_done = True

        for category, user_id, ip, detail in events:
            self.async_log(category, user_id=user_id, ip=ip, detail=detail)

    def async_log(
        self,
        category: str,
        *,
        user_id: str | None = None,
        domain: str | None = None,
        service: str | None = None,
        entity_ids: list[str] | None = None,
        context_id: str | None = None,
        context_parent_id: str | None = None,
        ip: str | None = None,
        attempted_user: str | None = None,
        detail: dict[str, Any] | None = None,
        flush: bool = False,
    ) -> None:
        """Append a normalized record to the in-memory buffer. No I/O here.

        Event-loop only; must stay a synchronous, non-blocking callback.
        This is the single redaction chokepoint for every detail payload.
        ``flush=True`` forces an immediate flush; high-value categories get
        one regardless.
        """
        if detail is not None:
            detail_value = _redact_secrets_deep(
                _redact_service_data(domain, service, detail)
            )
        else:
            detail_value = {}
        record = {
            "ts": dt_util.utcnow().isoformat(),
            "user_id": user_id,
            "category": category,
            "domain": domain,
            "service": service,
            "entity_ids": list(entity_ids) if entity_ids else [],
            "context_id": context_id,
            "context_parent_id": context_parent_id,
            "ip": ip,
            "attempted_user": attempted_user,
            "detail": detail_value,
        }
        self._buffer.append(record)
        if (
            flush
            or category in IMMEDIATE_FLUSH_CATEGORIES
            or category.startswith(IMMEDIATE_FLUSH_PREFIXES)
        ):
            self._async_schedule_flush()

    @callback
    def _async_schedule_flush(self) -> None:
        """Schedule one immediate flush task.

        eager_start=False keeps async_log non-blocking. No-op until the
        chain head has been loaded.
        """
        if not self._head_loaded:
            return
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._flush_task = self.hass.async_create_task(
            self._async_flush(), eager_start=False
        )

    def _drain_and_prepare(self) -> list[dict[str, Any]]:
        """Pop everything currently buffered and assign seq/prev_hash/hash.

        Synchronous and event-loop-only (no I/O) so the chain's seq/
        prev_hash mutation never races with a concurrent flush.
        """
        prepared: list[dict[str, Any]] = []
        while self._buffer:
            record = self._buffer.popleft()
            self._seq += 1
            record["seq"] = self._seq
            record["prev_hash"] = self._prev_hash
            canonical = json.dumps(record, sort_keys=True)
            record_hash = hashlib.sha256(
                (self._prev_hash + canonical).encode("utf-8")
            ).hexdigest()
            record["hash"] = record_hash
            self._prev_hash = record_hash
            prepared.append(record)
        return prepared

    async def _async_flush(self, _now: Any = None) -> None:
        async with self._flush_lock:
            records = self._drain_and_prepare()
            flushed_ok = await self.hass.async_add_executor_job(
                self._sync_flush, records
            )
            if flushed_ok and records:
                if self._syslog_exporter is not None:
                    self._syslog_exporter.async_enqueue(records)
                # Mirror on the loop after the executor returns; only a successful flush advances it.
                self._store.async_set_audit_head(
                    {
                        "seq": self._seq,
                        "hash": self._prev_hash,
                        "at": dt_util.utcnow().isoformat(),
                    }
                )

    def _sync_ensure_dir(self) -> None:
        """Create the audit directory 0o700 and tighten what already exists.

        makedirs' mode is umask-subject and ignored for an existing
        directory, so the explicit chmod is the guarantee.
        """
        os.makedirs(self._dir_path, mode=0o700, exist_ok=True)
        try:
            os.chmod(self._dir_path, 0o700)
        except OSError:
            _LOGGER.warning(
                "HA SOC audit log: could not chmod %s to 0o700",
                self._dir_path,
                exc_info=True,
            )
        tightened: list[str] = []
        try:
            names = os.listdir(self._dir_path)
        except OSError:
            return
        for name in names:
            path = os.path.join(self._dir_path, name)
            try:
                if not os.path.isfile(path):
                    continue
                # Group or other bits set means another uid could read it.
                if os.stat(path).st_mode & 0o077:
                    os.chmod(path, 0o600)
                    tightened.append(name)
            except OSError:
                _LOGGER.warning(
                    "HA SOC audit log: could not chmod %s to 0o600",
                    path,
                    exc_info=True,
                )
        if tightened:
            _LOGGER.info(
                "HA SOC audit log: tightened %d pre-existing audit file(s) "
                "to mode 0o600: %s",
                len(tightened),
                ", ".join(sorted(tightened)),
            )

    @staticmethod
    def _sync_open_private(path: str, flags: int):
        """Open ``path`` through os.open with creation mode 0o600.

        A plain open() honors the umask; os.open pins the mode at creation.
        """
        fd = os.open(path, flags, 0o600)
        return os.fdopen(fd, "w", encoding="utf-8")

    def _sync_load_chain_head(self) -> None:
        # Whatever this concludes is the real starting point, so immediate flushing is now safe.
        self._head_loaded = True
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        self._head_file_found = os.path.exists(path)
        if self._head_file_found:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._prev_hash = data.get("prev_hash", _GENESIS_PREV_HASH)
                self._seq = int(data.get("seq", 0))
                # The anchor must be restored or the next head rewrite would drop it.
                anchor = data.get("anchor")
                self._anchor = anchor if isinstance(anchor, dict) else None
                # Dropping the reset marker would make a wiped chain verify clean again.
                reset = data.get("reset")
                self._reset = reset if isinstance(reset, dict) else None
                return
            except (OSError, ValueError, TypeError):
                _LOGGER.warning(
                    "HA SOC audit log: could not read %s, starting a fresh chain",
                    path,
                    exc_info=True,
                )
                self._head_file_found = False
        self._prev_hash = _GENESIS_PREV_HASH
        self._seq = 0
        self._anchor = None
        self._reset = None

    def _sync_write_chain_head(self) -> None:
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        tmp_path = f"{path}.tmp"
        payload: dict[str, Any] = {"prev_hash": self._prev_hash, "seq": self._seq}
        # Every head rewrite must carry the anchor and reset marker forward.
        if self._anchor is not None:
            payload["anchor"] = self._anchor
        if self._reset is not None:
            payload["reset"] = self._reset
        try:
            # The temp file is born 0o600; os.replace preserves that mode on the real head.
            with self._sync_open_private(
                tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            ) as handle:
                json.dump(payload, handle)
            os.replace(tmp_path, path)
        except OSError:
            _LOGGER.warning(
                "HA SOC audit log: failed writing %s", path, exc_info=True
            )

    def _sync_flush(self, records: list[dict[str, Any]]) -> bool:
        """Append prepared records and maintain the head.

        Returns whether the write succeeded, so the caller only advances
        the store's head mirror over records that reached disk.
        """
        try:
            os.makedirs(self._dir_path, mode=0o700, exist_ok=True)
            if records:
                by_day: dict[str, list[str]] = {}
                for record in records:
                    day = record["ts"][:10]
                    by_day.setdefault(day, []).append(
                        json.dumps(record, sort_keys=True)
                    )
                for day, lines in by_day.items():
                    file_path = self._sync_target_day_file(day)
                    # O_APPEND with mode 0o600: a brand-new day file is born private.
                    fd = os.open(
                        file_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
                    )
                    with os.fdopen(fd, "a", encoding="utf-8") as handle:
                        handle.write("\n".join(lines) + "\n")
                self._sync_write_chain_head()
            self._sync_apply_retention()
        except OSError:
            _LOGGER.exception("HA SOC audit log: flush to disk failed")
            return False
        return True

    def _sync_list_day_files(self) -> list[tuple[date, str]]:
        if not os.path.isdir(self._dir_path):
            return []
        found: list[tuple[date, int, str]] = []
        for name in os.listdir(self._dir_path):
            match = _FILENAME_RE.match(name)
            if not match:
                continue
            try:
                file_date = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            segment = int(match.group(2)) if match.group(2) else 0
            found.append((file_date, segment, os.path.join(self._dir_path, name)))
        # (date, segment) order == write order, so chain verification walks
        # records in the same sequence they were appended.
        found.sort(key=lambda entry: (entry[0], entry[1]))
        return [(file_date, path) for file_date, _segment, path in found]

    def _sync_target_day_file(self, day: str) -> str:
        """The file the next append for ``day`` should go to, rolling to a
        fresh segment when the current one has crossed _SEGMENT_MAX_BYTES.
        """
        base = os.path.join(self._dir_path, f"audit-{day}.jsonl")
        segments: list[tuple[int, str]] = []
        for name in os.listdir(self._dir_path) if os.path.isdir(self._dir_path) else []:
            match = _FILENAME_RE.match(name)
            if not match or match.group(1) != day:
                continue
            segments.append((int(match.group(2)) if match.group(2) else 0, name))
        if not segments:
            return base
        highest_seg, highest_name = max(segments, key=lambda entry: entry[0])
        highest_path = os.path.join(self._dir_path, highest_name)
        try:
            if os.path.getsize(highest_path) < _SEGMENT_MAX_BYTES:
                return highest_path
        except OSError:
            return highest_path
        return os.path.join(self._dir_path, f"audit-{day}.{highest_seg + 1}.jsonl")

    def _sync_apply_retention(self) -> None:
        entries = self._sync_list_day_files()
        if not entries:
            return

        retention_days = self._store.settings["audit_retention_days"]
        cutoff = dt_util.utcnow().date() - timedelta(days=retention_days)

        # Capture each removed file's tail (seq, hash) first; the highest becomes the retention anchor.
        best_tail: tuple[int, str] | None = None
        expired_through: date | None = None
        deleted_any = False

        def _note_deleted(file_date: date, tail: tuple[int, str] | None) -> None:
            nonlocal best_tail, expired_through, deleted_any
            deleted_any = True
            if expired_through is None or file_date > expired_through:
                expired_through = file_date
            if tail is not None and (best_tail is None or tail[0] > best_tail[0]):
                best_tail = tail

        kept: list[tuple[date, str, int]] = []
        for file_date, path in entries:
            if file_date < cutoff:
                tail = self._sync_read_tail_seq_hash(path)
                try:
                    os.remove(path)
                except OSError:
                    _LOGGER.warning(
                        "HA SOC audit log: failed removing expired file %s",
                        path,
                        exc_info=True,
                    )
                    continue
                _note_deleted(file_date, tail)
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            kept.append((file_date, path, size))

        max_bytes = self._store.settings["audit_max_bytes"]
        total_size = sum(entry[2] for entry in kept)
        # kept is oldest-first; never delete the last remaining file, even over the cap.
        while total_size > max_bytes and len(kept) > 1:
            file_date, path, size = kept.pop(0)
            tail = self._sync_read_tail_seq_hash(path)
            try:
                os.remove(path)
                total_size -= size
            except OSError:
                _LOGGER.warning(
                    "HA SOC audit log: failed removing %s while enforcing size cap",
                    path,
                    exc_info=True,
                )
                continue
            _note_deleted(file_date, tail)

        if not deleted_any:
            return
        if best_tail is None:
            # No parseable tail means nothing truthful to anchor on; leave any existing anchor.
            _LOGGER.warning(
                "HA SOC audit log: expired files had no parseable tail "
                "record; retention anchor not advanced"
            )
            return
        if self._anchor is not None:
            try:
                existing_seq = int(self._anchor.get("seq"))
            except (TypeError, ValueError):
                existing_seq = None
            # Keep the further-along anchor if the new one is somehow behind.
            if existing_seq is not None and existing_seq >= best_tail[0]:
                return
        self._anchor = {
            "seq": best_tail[0],
            "hash": best_tail[1],
            "expired_through": expired_through.isoformat()
            if expired_through is not None
            else None,
            "expired_at": dt_util.utcnow().isoformat(),
        }
        if self._reset is not None:
            try:
                reset_seq = int(self._reset.get("seq"))
            except (TypeError, ValueError):
                reset_seq = None
            # The reset point aged out of retention; keeping the marker would fail verification forever.
            if reset_seq is None or best_tail[0] >= reset_seq:
                _LOGGER.info(
                    "HA SOC audit log: the chain-reset point (seq %s) has "
                    "expired under retention; clearing the reset marker.",
                    reset_seq,
                )
                self._reset = None
        self._sync_write_chain_head()

    @staticmethod
    def _sync_read_tail_seq_hash(path: str) -> tuple[int, str] | None:
        """Return (seq, hash) of a day file's last non-empty line.

        Called on files retention is about to delete, so the chain can be
        re-anchored where the deleted prefix ended. Returns None when the
        file cannot be read or its tail is not a well-formed record; the
        caller treats that as "nothing truthful to anchor on".
        """
        last_line: str | None = None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        last_line = line
        except OSError:
            return None
        if last_line is None:
            return None
        try:
            record = json.loads(last_line)
        except (ValueError, TypeError):
            return None
        if not isinstance(record, dict):
            return None
        seq = record.get("seq")
        record_hash = record.get("hash")
        if not isinstance(seq, int) or not isinstance(record_hash, str) or not record_hash:
            return None
        return (seq, record_hash)

    @staticmethod
    def _read_jsonl(path: str):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        yield line
        except OSError:
            return

    async def async_query(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        user_id: str | None = None,
        category: str | None = None,
        ip: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Return matching records, newest first, truncated to ``limit``.

        ``since``/``until`` are aware UTC datetimes (as returned by
        ``dt_util.utcnow()``). Defaults to the last 7 days if ``since`` is
        not given.
        """
        # Flush first: _sync_query reads only disk, and the panel must not lag up to _FLUSH_INTERVAL.
        await self._async_flush()
        return await self.hass.async_add_executor_job(
            self._sync_query, since, until, user_id, category, ip, limit
        )

    def _sync_query(
        self,
        since: datetime | None,
        until: datetime | None,
        user_id: str | None,
        category: str | None,
        ip: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        until_dt = until or dt_util.utcnow()
        since_dt = since or (until_dt - _DEFAULT_QUERY_LOOKBACK)

        results: list[dict[str, Any]] = []
        for file_date, path in self._sync_list_day_files():
            if file_date < since_dt.date() or file_date > until_dt.date():
                continue
            for line in self._read_jsonl(path):
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    continue

                record_dt = dt_util.parse_datetime(record.get("ts", ""))
                if record_dt is not None and (
                    record_dt < since_dt or record_dt > until_dt
                ):
                    continue
                if user_id is not None and record.get("user_id") != user_id:
                    continue
                if category is not None and record.get("category") != category:
                    continue
                if ip is not None and record.get("ip") != ip:
                    continue

                results.append(record)

        results.sort(key=lambda record: record.get("seq", 0), reverse=True)
        return results[:limit]

    async def async_category_stats(self) -> dict[str, Any]:
        """Per-category record counts and byte shares for the newest day.

        Only the newest day's file(s) are scanned; flushes first so
        buffered records are counted.
        """
        await self._async_flush()
        return await self.hass.async_add_executor_job(self._sync_category_stats)

    def _sync_category_stats(self) -> dict[str, Any]:
        entries = self._sync_list_day_files()
        if not entries:
            return {
                "day": None,
                "files": 0,
                "total_records": 0,
                "total_bytes": 0,
                "categories": [],
            }
        newest_day = entries[-1][0]
        paths = [path for file_date, path in entries if file_date == newest_day]

        records: dict[str, int] = {}
        sizes: dict[str, int] = {}
        total_records = 0
        total_bytes = 0
        for path in paths:
            # Read as bytes so byte shares reflect what is on disk, not decoded characters.
            try:
                with open(path, "rb") as handle:
                    for raw_line in handle:
                        line = raw_line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except (ValueError, TypeError):
                            category = "unparseable"
                        else:
                            category = (
                                record.get("category") if isinstance(record, dict) else None
                            ) or "unknown"
                        size = len(raw_line)
                        records[category] = records.get(category, 0) + 1
                        sizes[category] = sizes.get(category, 0) + size
                        total_records += 1
                        total_bytes += size
            except OSError:
                continue

        categories = [
            {
                "category": category,
                "records": records[category],
                "bytes": sizes[category],
                "byte_share": round(sizes[category] / total_bytes, 4)
                if total_bytes
                else 0.0,
            }
            for category in records
        ]
        categories.sort(key=lambda entry: entry["bytes"], reverse=True)
        return {
            "day": newest_day.isoformat(),
            "files": len(paths),
            "total_records": total_records,
            "total_bytes": total_bytes,
            "categories": categories,
        }

    async def async_verify_chain(self) -> dict[str, Any]:
        """Recompute the hash chain and check it end to end.

        Tamper-evident, not tamper-proof; result fields and the
        chain_reset verdict are described in docs/security.md.
        """
        # Flush first so the walk and the checkpoint both cover everything logged so far.
        await self._async_flush()
        return await self.hass.async_add_executor_job(self._sync_verify_chain)

    def _sync_verify_chain(self) -> dict[str, Any]:
        # Read from disk, not memory: verification judges what an attacker could have edited.
        anchor_seq, anchor_hash, expired_through = self._sync_read_chain_head_anchor()
        reset = self._sync_read_chain_head_reset()

        # Start from whichever discontinuity is further along: retention anchor or reset marker.
        start_seq, start_hash = anchor_seq, anchor_hash
        start_is_reset = False
        if reset is not None and (start_seq is None or reset[0] > start_seq):
            start_seq, start_hash = reset
            start_is_reset = True
        verified_from_seq = start_seq + 1 if start_seq is not None else 1

        prev_hash = start_hash if start_seq is not None else _GENESIS_PREV_HASH
        checked = 0
        # The missing prefix legitimately ends at the start seq, so expiry is not read as truncation.
        last_seq = start_seq if start_seq is not None else 0

        def _fail(
            reason: str, first_break_seq: int | None, **extra: Any
        ) -> dict[str, Any]:
            result: dict[str, Any] = {
                "ok": False,
                "records_checked": checked,
                "first_break_seq": first_break_seq,
                "reason": reason,
                "verified_from_seq": verified_from_seq,
                "expired_through": expired_through,
            }
            result.update(extra)
            return result

        # A start-point contradiction is reported under the contradicted marker's name.
        start_break_reason = "chain_reset" if start_is_reset else "anchor_inconsistent"

        # A checkpoint behind the store mirror means the directory was replaced or rolled back.
        mirror = self._store.data.get("audit_head")
        mirror_seq: int | None = None
        if isinstance(mirror, dict):
            try:
                mirror_seq = int(mirror.get("seq"))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                mirror_seq = None
        head_seq, head_hash = self._sync_read_chain_head_checkpoint()
        if mirror_seq is not None and (head_seq is None or head_seq < mirror_seq):
            return _fail(
                "chain_reset",
                None,
                store_head_seq=mirror_seq,
                checkpoint_seq=head_seq,
            )

        for _file_date, path in self._sync_list_day_files():
            for line in self._read_jsonl(path):
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    return _fail("corrupt_record", None)

                checked += 1
                seq = record.get("seq")
                stored_hash = record.get("hash")

                if start_seq is not None and isinstance(seq, int):
                    # No surviving record may sit at or before the start point.
                    if seq <= start_seq:
                        return _fail(start_break_reason, seq)
                    # The first surviving record must be the start point's direct successor.
                    if checked == 1 and seq != start_seq + 1:
                        return _fail(start_break_reason, seq)

                if record.get("prev_hash") != prev_hash:
                    return _fail("hash_mismatch", seq)

                payload = {k: v for k, v in record.items() if k != "hash"}
                recomputed = hashlib.sha256(
                    (prev_hash + json.dumps(payload, sort_keys=True)).encode("utf-8")
                ).hexdigest()

                if recomputed != stored_hash:
                    return _fail("hash_mismatch", seq)

                prev_hash = stored_hash
                if isinstance(seq, int):
                    last_seq = seq

        # Completeness check: a checkpoint ahead of disk means the tail was truncated.
        if head_seq is not None and (last_seq < head_seq or prev_hash != head_hash):
            return _fail(
                "tail_truncated",
                None,
                checkpoint_seq=head_seq,
                last_on_disk_seq=last_seq,
            )

        if reset is not None:
            # History before the reset is gone, so "ok" would claim an unbroken chain.
            return _fail("chain_reset", None, reset_seq=reset[0])

        return {
            "ok": True,
            "records_checked": checked,
            "first_break_seq": None,
            "reason": None,
            "verified_from_seq": verified_from_seq,
            "expired_through": expired_through,
        }

    def _sync_read_chain_head_file(self) -> dict[str, Any] | None:
        """Read chain_head.json straight from disk, ignoring the in-memory head.

        Returns None when the file is missing or unreadable.
        """
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError, TypeError):
            return None
        return data if isinstance(data, dict) else None

    def _sync_read_chain_head_checkpoint(self) -> tuple[int | None, str]:
        """The persisted chain head (seq, prev_hash).

        Returns (None, "") when no checkpoint exists or the file is unreadable.
        """
        data = self._sync_read_chain_head_file()
        if data is None:
            return (None, "")
        try:
            return (int(data.get("seq", 0)), data.get("prev_hash", _GENESIS_PREV_HASH))
        except (ValueError, TypeError):
            return (None, "")

    def _sync_read_chain_head_anchor(self) -> tuple[int | None, str, str | None]:
        """The persisted retention anchor as (seq, hash, expired_through).

        Returns (None, "", None) when absent or malformed; verification
        then starts at genesis and fails loudly if records did expire.
        """
        data = self._sync_read_chain_head_file()
        anchor = data.get("anchor") if data is not None else None
        if not isinstance(anchor, dict):
            return (None, "", None)
        try:
            seq = int(anchor["seq"])
            anchor_hash = anchor["hash"]
        except (KeyError, ValueError, TypeError):
            return (None, "", None)
        if not isinstance(anchor_hash, str) or not anchor_hash:
            return (None, "", None)
        expired_through = anchor.get("expired_through")
        return (
            seq,
            anchor_hash,
            expired_through if isinstance(expired_through, str) else None,
        )

    def _sync_read_chain_head_reset(self) -> tuple[int, str] | None:
        """The persisted chain-reset marker as (seq, hash), or None.

        A malformed marker reads as absent, which fails loudly at the walk
        rather than silently passing.
        """
        data = self._sync_read_chain_head_file()
        reset = data.get("reset") if data is not None else None
        if not isinstance(reset, dict):
            return None
        try:
            seq = int(reset["seq"])
            reset_hash = reset["hash"]
        except (KeyError, ValueError, TypeError):
            return None
        if not isinstance(reset_hash, str) or not reset_hash:
            return None
        return (seq, reset_hash)
