"""Append-only, hash-chained audit log for HA SOC.

This module is the closest thing HA SOC has to a security camera pointed at
Home Assistant's own auth/service/registry surface. It is intentionally
narrow: it only listens to bus events, one dispatcher signal, and log
records that Home Assistant core already emits, and it never touches
``state_changed`` or a ``MATCH_ALL`` listener. What follows is an honest
accounting of what is actually captured, what is inferred/best-effort, and
what is structurally impossible from inside an integration - overclaiming
any of this in a security product is worse than not having the feature.

Captured directly (one bus event or dispatcher signal per record):

- ``service_call`` - every ``call_service`` event. This fires *before*
  permission checks and *before* the service actually runs, so it records
  an attempted call, not its outcome or even whether it was authorized.
  Obviously-sensitive ``service_data`` keys (``password``, ``token``,
  ``code``, and ``message`` for ``notify``/``tts`` domains) are redacted to
  ``"[redacted]"`` before anything touches disk. Core merges a call's
  target block into ``service_data``, so non-entity targets (``area_id``,
  ``device_id``, ``label_id``, ``floor_id``) are extracted into
  ``detail["targets"]`` alongside the top-level ``entity_ids``.
- ``user_added`` / ``user_updated`` / ``user_removed`` - the three
  ``homeassistant.auth`` lifecycle events. SEMANTICS NOTE: ``user_id`` on
  these records is the best-effort ACTING user (the admin who made the
  change, recovered as described under "Actor attribution" below), and the
  user who was added/updated/removed is ``detail["target_user_id"]``.
  Earlier releases stored the subject in ``user_id``, which made the
  panel's per-user filter conflate "acted" with "was acted upon".
- ``lovelace_change`` - ``lovelace_updated`` (a dashboard's config was
  saved).
- ``entity_registry_change`` / ``device_registry_change`` /
  ``area_registry_change`` / ``floor_registry_change`` /
  ``label_registry_change`` / ``category_registry_change`` - the six
  ``*_registry_updated`` bus events. For ``update`` actions core puts the
  OLD values of the changed fields in ``changes``, never the new ones, so
  a rename records only the previous name; the new value must be read from
  the registry itself.
- ``config_entry_change`` - integration config entries added, removed, or
  updated (including enable/disable). Core exposes this only as the
  ``config_entry_changed`` dispatcher signal, not a bus event, so there is
  no Event and no Context here at all; actor attribution is ambient-only.
- ``core_config_change`` - ``core_config_updated`` (location, name, unit
  system, timezone, URLs). Core also fires this event twice during startup
  with an empty payload; those fires carry no configuration change and are
  skipped as noise.
- ``dashboard_panels_change`` - ``panels_updated``. The event payload is
  empty, so this is a tripwire only: it records that the frontend panel
  set changed (a dashboard was created or deleted, a panel registered or
  removed), not which panel or by how much.

Actor attribution (``detail["actor_source"]`` on records that use it):

Nearly every mutation event above is fired by core WITHOUT a Context, so
``event.context.user_id`` is ``None`` even when an admin clicked the
button in the UI or an agent issued the WebSocket command. Records that go
through ``_resolve_actor`` label how the actor was recovered:

- ``event_context`` - ``event.context.user_id`` was populated by core.
  This is the only AUTHORITATIVE source.
- ``ws_connection`` - the ``websocket_api.current_connection`` contextvar
  identified the WebSocket connection whose command handler this listener
  ran inside. Correlational, not authoritative: a contextvar snapshot can
  leak into unrelated work scheduled downstream of a request, so read it
  as "this change happened during this user's session", not as proof that
  this user made the change.
- ``http_request`` - the same idea via ``helpers.http.current_request``,
  which covers the REST config views (automation/script/scene editors,
  core config). Correlational, same caveat.
- ``system`` - no ambient signal at all; the change came from core itself,
  an integration, or a code path that dropped the context.

- ``session_seen`` - a synthetic record emitted once per refresh token per
  runtime, the first time a WebSocket connection is observed through the
  contextvar above. It exists because long-lived access token bearer usage
  is otherwise invisible (see below); it marks the first OBSERVED activity
  of a session, not its login time, and its absence does not mean the
  session does not exist.

Best-effort / inferred (no bus event exists for these - confirmed against
the installed core source - so they are reconstructed indirectly):

- ``login_fail`` - a ``logging.Handler`` attached to
  ``homeassistant.components.http.ban`` catches the WARNING it logs for
  every invalid-auth request. This is IP-only. Home Assistant's ban
  middleware never logs the attempted username anywhere, so
  ``attempted_user`` is always ``None`` here - this module will not
  fabricate one.
- ``login_ok`` - polled every 30s by diffing each user's refresh tokens
  against a snapshot from the previous poll. A brand-new normal/webhook
  token, or an existing token whose ``last_used_at`` advanced, is logged as
  ``login_ok``. A token refresh looks identical to a fresh interactive
  login through this API, so this is best read as "this user's session was
  active", not "this user just typed a password".
- ``token_created`` - same poll loop; a brand-new
  ``long_lived_access_token`` id. For long-lived tokens this is the ONLY
  signal the poll will ever produce: core updates ``last_used_at`` and
  ``last_used_ip`` only on the ``/auth/token`` grant path, which a bearer
  request with a long-lived token never touches, so after creation the
  poll is permanently blind to that token's activity. The ``session_seen``
  record above is the best available substitute for WebSocket sessions.

Out of scope / structurally impossible from here:

- The AUTHORITATIVE acting user behind registry, dashboard, and config
  mutations. Core fires every ``*_registry_updated`` event, the lovelace
  events, the user lifecycle events, and ``core_config_updated`` without
  threading the caller's Context through, so ``context.user_id`` is always
  ``None`` there and nothing an integration can subscribe to carries the
  actor. The contextvar correlation described above is the ceiling;
  anything stronger requires a change in core itself.
- The content delta of an automation, script, or scene edit. The REST
  config views write the submitted YAML/JSON straight to storage and fire
  nothing but a context-less reload service call, and an integration
  cannot see the request body, so only the fact of a reload is observable.
- Which script was reloaded. Core has no ``script_reloaded`` event, and
  the script config view calls ``script.reload`` with no id in the service
  data, so a script edit is indistinguishable from any other script edit.
- Config-only updates to helpers (``input_boolean``, ``input_number``,
  ``counter``, ``timer``, ``schedule``, and friends) and lovelace resource
  add/remove. The storage collections behind both emit no bus event; their
  in-process change listeners are reachable only through per-integration
  ``hass.data`` keys that are not a stable API, so this module
  deliberately does not hook them. Helper create/delete still surfaces
  indirectly as ``entity_registry_change``, and renaming a helper's entity
  does too; changing a helper's min/max/step/icon fires nothing at all.
- Whether a request bearing a long-lived access token succeeded. Token
  validation in core is a pure callback with no side effects, no event,
  and no log line; only failures are observable (through the ban logger,
  as ``login_fail``).
- The username behind a failed login attempt - Home Assistant does not
  record it anywhere an integration can reach.
- Permission-denied errors raised inside a service call or over the
  WebSocket/REST API. The Unauthorized error is raised and returned to the
  client; there is no bus event and no dedicated logger for it.
- True tamper-*proof* storage. ``async_verify_chain`` proves the on-disk
  hash chain is internally consistent, i.e. nothing in these files was
  edited without recomputing every hash after it. It cannot prove the
  files were never touched: anything with the same filesystem access that
  reaches ``.storage/`` (an SSH/Terminal add-on, Samba, the File Editor
  add-on, root on the host) can rewrite ``chain_head.json`` and every
  record's hash to match. That makes this tamper-*evident*, not
  tamper-proof. Real integrity guarantees require exporting the chain off
  this box (e.g. to a remote syslog/SIEM) as it is written, which is out of
  scope for this module.

Storage: newline-delimited JSON, one file per UTC calendar day
(``audit-YYYY-MM-DD.jsonl``) under ``.storage/<AUDIT_STORAGE_SUBDIR>/``,
plus a tiny ``chain_head.json`` sidecar so the hash chain survives a
restart. Records are only ever appended; nothing is rewritten in place.
All file I/O runs in the executor - never on the event loop.
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

# The literal event-type strings are what core actually fires; importing the
# matching constant is a nicety, not a requirement, so failure to import
# falls back to the (stable) literal rather than breaking setup.
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

# Same story for the refresh-token type constants used by the login/token
# poll loop - duplicated here (rather than imported from users.py) so this
# module stays independently testable, matching the rest of HA SOC's module
# boundaries.
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

# The five registries beyond the entity registry each fire their own
# "<name>_registry_updated" bus event (homeassistant/helpers/*_registry.py).
# As above, the literal strings are what core actually fires, so an import
# failure falls back to the stable literal instead of breaking setup.
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

# Config entries have no bus event at all; core announces add/remove/update
# only on this dispatcher signal. SignalType subclasses str, so the literal
# fallback still reaches the same dispatcher slot.
try:
    from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED
except ImportError:  # pragma: no cover - older/newer core layout fallback
    SIGNAL_CONFIG_ENTRY_CHANGED = "config_entry_changed"

# Ambient actor recovery (see _resolve_actor for the honesty caveats). Core
# fires nearly every mutation event without a Context, so these two
# contextvars are the only signal an integration can read for "who did
# this". An import failure degrades to no ambient recovery, never to a
# broken setup.
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
# A day's records live in audit-YYYY-MM-DD.jsonl, plus numbered segments
# audit-YYYY-MM-DD.1.jsonl, .2.jsonl, ... once the current file crosses
# _SEGMENT_MAX_BYTES within a single day. Group 2 is the segment index
# (absent = 0), used only to keep files in written order when listing.
_FILENAME_RE = re.compile(r"^audit-(\d{4}-\d{2}-\d{2})(?:\.(\d+))?\.jsonl$")
_GENESIS_PREV_HASH = ""

# Roll a day's audit file to a new segment once it exceeds this size, so a
# single very high-volume day can't grow one file past the retention size
# cap before the next UTC-day rotation. 32 MB keeps individual files small
# enough to read/verify quickly while staying well under the default cap.
_SEGMENT_MAX_BYTES = 32 * 1024 * 1024

_DEFAULT_QUERY_LOOKBACK = timedelta(days=7)

_REDACTED_SERVICE_DATA_KEYS = frozenset({"password", "token", "code"})
_REDACTED_MESSAGE_DOMAINS = frozenset({"notify", "tts"})

_BAN_LOGGER_NAME = "homeassistant.components.http.ban"
# On core 2026.2, http/ban.py builds the invalid-auth warning as a fully
# formatted f-string ("Login attempt or request with invalid authentication
# from <host> (<addr>). Requested URL: ...") and logs it with NO args, so
# record.args is empty and this regex on the formatted message is what
# actually extracts the address. The structured-args branch in _extract_ip
# is kept only as a compatibility path in case core ever goes back to
# passing (remote_host, remote_addr) as logging args.
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


def _redact_service_data(domain: str | None, service_data: Any) -> dict[str, Any]:
    """Return a copy of service_data with obviously sensitive keys masked."""
    if not isinstance(service_data, dict):
        return {}
    redacted: dict[str, Any] = {}
    for key, value in service_data.items():
        if key in _REDACTED_SERVICE_DATA_KEYS:
            redacted[key] = "[redacted]"
        elif key == "message" and domain in _REDACTED_MESSAGE_DOMAINS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted


def _redact_secrets_deep(value: Any) -> Any:
    """Recursively mask any dict value stored under a known secret key.

    Applied to every ``detail`` payload inside ``async_log`` itself, not
    at individual call sites, so a credential-shaped setting (e.g.
    ``nvd_api_key``, ``github_token``) can never reach the append-only,
    long-retention audit files verbatim, no matter which code path logged
    it or how deeply it's nested (settings changes log under
    ``detail["changes"][<key>]``). This is the shared enforcement point the
    red-team review asked for; per-call-site redaction is not relied on.
    """
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

    This is the *only* place a failed login is observable at all from an
    integration - core has no bus event for it. It only ever carries an IP;
    the attempted username is never logged anywhere by core, so it is never
    fabricated here.

    ``emit()`` can be called from a worker thread that is not the event
    loop, so it must do the absolute minimum work here (parse a string) and
    hand off to the loop via ``call_soon_threadsafe``. It must never call
    async code directly and must never raise - a misbehaving logging
    handler can wreck whatever thread happens to be logging through it.
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
        # A (remote_host, remote_addr) args tuple is used when present, but
        # on current core the message arrives preformatted with no args, so
        # the regex below is the branch that actually runs (see the comment
        # at _BAN_MESSAGE_RE).
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
    """Captures, hash-chains, and stores HA SOC's security-relevant events.

    See the module docstring for exactly what is captured, what is
    best-effort, and what is out of scope. Nothing here touches
    ``state_changed`` or a ``MATCH_ALL`` listener.
    """

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self._store = store
        self._dir_path = hass.config.path(".storage", AUDIT_STORAGE_SUBDIR)

        self._buffer: deque[dict[str, Any]] = deque()
        self._flush_lock = asyncio.Lock()
        self._seq = 0
        self._prev_hash = _GENESIS_PREV_HASH

        self._unsubs: list[Unsub] = []
        self._cancel_flush_timer: Unsub | None = None
        self._cancel_poll_timer: Unsub | None = None
        self._ban_handler: _FailedLoginLogHandler | None = None

        # (last_used_at, last_used_ip) snapshot, keyed by refresh_token.id,
        # used by the login/token-creation poll loop.
        self._token_snapshot: dict[str, tuple[datetime | None, str | None]] = {}
        self._first_poll_done = False

        # Refresh-token ids whose WebSocket connection has already produced a
        # session_seen record this runtime. Deliberately not persisted:
        # after a restart the first observed activity of each still-live
        # session is announced once more, which is cheap and errs toward
        # visibility rather than silence.
        self._seen_ws_token_ids: set[str] = set()

    # -- Lifecycle ----------------------------------------------------------

    async def async_start(self) -> None:
        """Create storage, load the chain head, and start capturing."""
        await self.hass.async_add_executor_job(self._sync_ensure_dir)
        await self.hass.async_add_executor_job(self._sync_load_chain_head)

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
        # The other five registries share one handler, parameterized with the
        # record category and the payload key that names the changed item.
        # functools.partial is safe here: HassJob unwraps partials before
        # checking for the @callback marker, so these still dispatch inline
        # on the event loop like a plain @callback listener.
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
        # Config entries announce changes on a dispatcher signal, not the
        # bus; async_dispatcher_connect returns an unsubscribe callable just
        # like async_listen does.
        self._unsubs.append(
            async_dispatcher_connect(
                self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._handle_config_entry_changed
            )
        )
        self._unsubs.append(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, self._async_flush
            )
        )

        self._ban_handler = _FailedLoginLogHandler(self.hass, self._on_failed_login)
        logging.getLogger(_BAN_LOGGER_NAME).addHandler(self._ban_handler)

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
            logging.getLogger(_BAN_LOGGER_NAME).removeHandler(self._ban_handler)
            self._ban_handler = None

        await self._async_flush()

    # -- Actor recovery -------------------------------------------------

    @callback
    def _resolve_actor(self, event: Event) -> tuple[str | None, str]:
        """Best-effort acting user for an event, plus how it was recovered.

        Returns ``(user_id, source)`` where source is one of
        ``event_context``, ``ws_connection``, ``http_request``, or
        ``system``. Only ``event_context`` is authoritative. The contextvar
        sources are correlational (see the module docstring), and
        ``system`` means there was no signal at all.
        """
        user_id = event.context.user_id
        if user_id is not None:
            return user_id, "event_context"
        return self._resolve_actor_ambient()

    @callback
    def _resolve_actor_ambient(self) -> tuple[str | None, str]:
        """Ambient-only actor recovery, for signals that carry no Event.

        This works only because @callback listeners run inline in the same
        asyncio context as the WebSocket command or HTTP request whose
        handler caused the mutation, and coroutine listeners inherit a copy
        of that context when their task is created during the fire. A
        contextvar snapshot can leak into unrelated work scheduled
        downstream of a request, so a hit here is correlation with the
        active session, never proof of who acted.
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
        """Emit one synthetic session_seen record per refresh token.

        Core updates a token's ``last_used_at`` only on the ``/auth/token``
        grant path, which a long-lived access token bearer never touches,
        so the token poll loop is permanently blind to a LLAT session. The
        first time any audited change correlates to a WebSocket connection
        this runtime, record that the session exists at all. The caveat is
        stored in the record itself so an export stays honest on its own.
        """
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

    # -- Event handlers -------------------------------------------------

    @callback
    def _handle_call_service(self, event: Event) -> None:
        # Fires before permission checks and before the service runs - this
        # is an attempted call, not a confirmed outcome. See module
        # docstring; do not let a future edit here imply otherwise.
        #
        # No ambient fallback here on purpose: call_service is the one
        # event where core threads the caller's real Context through, and
        # applying contextvar recovery to the None case would mostly
        # re-attribute automation-driven calls to whichever user's session
        # happened to be upstream, which is exactly the overclaim this
        # module refuses to make.
        domain = event.data.get(ATTR_DOMAIN)
        service = event.data.get(ATTR_SERVICE)
        service_data = event.data.get(ATTR_SERVICE_DATA)
        if not isinstance(service_data, dict):
            service_data = {}
        entity_ids = _normalize_entity_ids(service_data.get("entity_id"))
        detail = _redact_service_data(domain, service_data)
        # Core merges a call's target block into service_data before firing
        # the event, so area/device/label/floor targets arrive as plain
        # keys here. Normalize them into detail["targets"] so an
        # area-targeted call does not audit as if it touched nothing (its
        # entity_ids list is empty).
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
        # event.data["user_id"] names the user being added/updated (the
        # SUBJECT), not whoever performed the change: core fires these
        # events with no Context at all. The acting admin is recovered
        # ambiently; the auth events fire inline in the acting admin's
        # WebSocket command task, and this coroutine listener's task is
        # created during that fire with a copy of the task's contextvars,
        # so ws_connection recovery usually works here. The copied context
        # survives awaits, but the actor is resolved before the first await
        # anyway so the ordering is obvious.
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
        # The removed user is already gone by the time this fires, so there
        # is no name left to resolve. As with the other user lifecycle
        # events, event.data["user_id"] is the SUBJECT; the actor is
        # recovered ambiently.
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
    def _handle_lovelace_updated(self, event: Event) -> None:
        # Core fires lovelace_updated without a Context, so the actor is
        # recovered ambiently (a dashboard save arrives over the WebSocket,
        # so ws_connection recovery usually works).
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
        # Core puts the OLD values of the changed fields in "changes"; the
        # new values are not in the event and must be read from the
        # registry itself.
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

        All five fire the same shape of event, differing only in the key
        that names the changed item. Like the entity registry, core fires
        them without a Context, so the actor is recovered ambiently. Note
        that "changes" (present on update actions only) carries the OLD
        values of the changed fields, never the new ones; that is core
        behavior, not a choice made here. The device registry (like the
        entity registry) also fires in bulk during integration setup and
        teardown; those fires resolve to actor_source "system", which is
        how an operator separates them from interactive edits.
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

        This arrives on the config_entry_changed dispatcher signal, not the
        bus, so there is no Event and no Context here at all; only ambient
        recovery is possible. ``change`` is core's ConfigEntryChange
        StrEnum (added/removed/updated).
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
        # Core fires core_config_updated twice during startup with an empty
        # payload (once entering the starting state, once entering
        # running). Those fires carry no configuration change, so they are
        # skipped rather than logged as noise. A real update passes the
        # changed keys and their NEW values as the event data.
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
        # Tripwire only. panels_updated fires with an EMPTY payload whenever
        # the frontend panel set changes (a dashboard created or deleted,
        # any panel registered or removed), and core has no per-dashboard
        # CRUD event to subscribe to instead. The honest record is
        # therefore "the panel set changed", plus a best-effort actor.
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

        There is no bus event for either a successful login or a new
        long-lived access token - confirmed against core's dev branch, so
        this polls every 30s and diffs against the previous poll's
        snapshot. See module docstring for the precision caveats on
        ``login_ok``.
        """
        try:
            users = await self.hass.auth.async_get_users()
        except Exception:  # noqa: BLE001 - never let the poll loop die
            _LOGGER.exception("HA SOC audit log: failed polling users/tokens")
            return

        new_snapshot: dict[str, tuple[datetime | None, str | None]] = {}
        events: list[tuple[str, str | None, str | None]] = []

        for user in users:
            for token in user.refresh_tokens.values():
                if token.token_type == TOKEN_TYPE_SYSTEM:
                    continue
                previous = self._token_snapshot.get(token.id)
                new_snapshot[token.id] = (token.last_used_at, token.last_used_ip)

                if not self._first_poll_done:
                    # Seed only - avoid a burst of fake "new login" entries
                    # for every already-existing session at HA restart.
                    continue

                if previous is None:
                    if token.token_type == TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN:
                        events.append(("token_created", user.id, token.last_used_ip))
                    else:
                        events.append(("login_ok", user.id, token.last_used_ip))
                else:
                    prev_last_used_at, _prev_ip = previous
                    if (
                        token.last_used_at is not None
                        and token.last_used_at != prev_last_used_at
                    ):
                        events.append(("login_ok", user.id, token.last_used_ip))

        self._token_snapshot = new_snapshot
        self._first_poll_done = True

        for category, user_id, ip in events:
            self.async_log(category, user_id=user_id, ip=ip)

    # -- Public logging API ---------------------------------------------

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
    ) -> None:
        """Append a normalized record to the in-memory buffer. No I/O here.

        Event-loop only (bus listeners, the token poll, and the ban log
        handler's threadsafe handoff all call this from the loop) - it must
        stay a plain, synchronous, non-blocking callback.
        """
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
            "detail": _redact_secrets_deep(detail) if detail is not None else {},
        }
        self._buffer.append(record)

    # -- Flush / hash chain -----------------------------------------------

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
            await self.hass.async_add_executor_job(self._sync_flush, records)

    # -- Executor-only I/O ------------------------------------------------

    def _sync_ensure_dir(self) -> None:
        os.makedirs(self._dir_path, exist_ok=True)

    def _sync_load_chain_head(self) -> None:
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._prev_hash = data.get("prev_hash", _GENESIS_PREV_HASH)
                self._seq = int(data.get("seq", 0))
                return
            except (OSError, ValueError, TypeError):
                _LOGGER.warning(
                    "HA SOC audit log: could not read %s, starting a fresh chain",
                    path,
                    exc_info=True,
                )
        self._prev_hash = _GENESIS_PREV_HASH
        self._seq = 0

    def _sync_write_chain_head(self) -> None:
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        tmp_path = f"{path}.tmp"
        payload = {"prev_hash": self._prev_hash, "seq": self._seq}
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            os.replace(tmp_path, path)
        except OSError:
            _LOGGER.warning(
                "HA SOC audit log: failed writing %s", path, exc_info=True
            )

    def _sync_flush(self, records: list[dict[str, Any]]) -> None:
        try:
            os.makedirs(self._dir_path, exist_ok=True)
            if records:
                by_day: dict[str, list[str]] = {}
                for record in records:
                    day = record["ts"][:10]
                    by_day.setdefault(day, []).append(
                        json.dumps(record, sort_keys=True)
                    )
                for day, lines in by_day.items():
                    file_path = self._sync_target_day_file(day)
                    with open(file_path, "a", encoding="utf-8") as handle:
                        handle.write("\n".join(lines) + "\n")
                self._sync_write_chain_head()
            self._sync_apply_retention()
        except OSError:
            _LOGGER.exception("HA SOC audit log: flush to disk failed")

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

        kept: list[tuple[date, str, int]] = []
        for file_date, path in entries:
            if file_date < cutoff:
                try:
                    os.remove(path)
                except OSError:
                    _LOGGER.warning(
                        "HA SOC audit log: failed removing expired file %s",
                        path,
                        exc_info=True,
                    )
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            kept.append((file_date, path, size))

        max_bytes = self._store.settings["audit_max_bytes"]
        total_size = sum(entry[2] for entry in kept)
        # kept is oldest-first; never delete the last remaining file, even
        # if that alone exceeds the cap - losing the entire log is worse
        # than briefly going over budget.
        while total_size > max_bytes and len(kept) > 1:
            _file_date, path, size = kept.pop(0)
            try:
                os.remove(path)
                total_size -= size
            except OSError:
                _LOGGER.warning(
                    "HA SOC audit log: failed removing %s while enforcing size cap",
                    path,
                    exc_info=True,
                )

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

    # -- Query --------------------------------------------------------------

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
        # Flush first so a change made seconds ago is visible immediately;
        # _sync_query reads only what is on disk, and without this the
        # panel would lag up to _FLUSH_INTERVAL behind reality.
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

    # -- Chain verification ---------------------------------------------

    async def async_verify_chain(self) -> dict[str, Any]:
        """Recompute the hash chain from the first record and check it.

        This proves the on-disk log is internally consistent - i.e. every
        record's hash still matches ``prev_hash`` plus its own content, all
        the way from the first record ever written. It does NOT prove the
        files were never tampered with: anyone who can reach ``.storage/``
        with the same filesystem access this integration has (an SSH/
        Terminal add-on, Samba, the File Editor add-on, root on the host)
        can rewrite every hash to be self-consistent again. Tamper-evident,
        not tamper-proof - real integrity needs an off-box export, which is
        out of scope for this module.
        """
        # Flush first so the check covers everything logged so far and the
        # records-checked count matches what the query view shows. The
        # chain-head checkpoint is only written on flush, so this also
        # keeps the completeness check consistent with the buffer.
        await self._async_flush()
        return await self.hass.async_add_executor_job(self._sync_verify_chain)

    def _sync_verify_chain(self) -> dict[str, Any]:
        prev_hash = _GENESIS_PREV_HASH
        checked = 0
        last_seq = 0

        for _file_date, path in self._sync_list_day_files():
            for line in self._read_jsonl(path):
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    return {
                        "ok": False,
                        "records_checked": checked,
                        "first_break_seq": None,
                        "reason": "corrupt_record",
                    }

                checked += 1
                seq = record.get("seq")
                stored_hash = record.get("hash")

                if record.get("prev_hash") != prev_hash:
                    return {
                        "ok": False,
                        "records_checked": checked,
                        "first_break_seq": seq,
                        "reason": "hash_mismatch",
                    }

                payload = {k: v for k, v in record.items() if k != "hash"}
                recomputed = hashlib.sha256(
                    (prev_hash + json.dumps(payload, sort_keys=True)).encode("utf-8")
                ).hexdigest()

                if recomputed != stored_hash:
                    return {
                        "ok": False,
                        "records_checked": checked,
                        "first_break_seq": seq,
                        "reason": "hash_mismatch",
                    }

                prev_hash = stored_hash
                if isinstance(seq, int):
                    last_seq = seq

        # Completeness check, not just consistency: the internal chain above
        # can walk to a clean end even if the newest records were deleted
        # off the tail (nothing on disk points *forward* to an unwritten
        # record). Cross-check the last record actually seen against the
        # separately-stored chain-head checkpoint. If the checkpoint is
        # ahead of what's on disk, the tail was truncated/removed since the
        # last flush - the cheapest way to hide one's own recent actions,
        # and invisible to a consistency-only check. This still can't catch
        # an attacker who rewrites BOTH the log and chain_head.json (that
        # needs an off-box anchor - see async_verify_chain's docstring), but
        # it closes the plain-truncation gap.
        head_seq, head_hash = self._sync_read_chain_head_checkpoint()
        if head_seq is not None and (last_seq < head_seq or prev_hash != head_hash):
            return {
                "ok": False,
                "records_checked": checked,
                "first_break_seq": None,
                "reason": "tail_truncated",
                "checkpoint_seq": head_seq,
                "last_on_disk_seq": last_seq,
            }

        return {
            "ok": True,
            "records_checked": checked,
            "first_break_seq": None,
            "reason": None,
        }

    def _sync_read_chain_head_checkpoint(self) -> tuple[int | None, str]:
        """Read the persisted chain head (seq, prev_hash) straight from disk,
        independent of the in-memory head, for the completeness check above.
        Returns (None, "") when no checkpoint exists yet (fresh install).
        """
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        if not os.path.exists(path):
            return (None, "")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return (int(data.get("seq", 0)), data.get("prev_hash", _GENESIS_PREV_HASH))
        except (OSError, ValueError, TypeError):
            return (None, "")
