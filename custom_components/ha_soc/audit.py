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
  Credential-shaped ``service_data`` keys (``password``, ``token``,
  ``code``, ``api_key``, ``apikey``, ``secret``, ``pin``, ``passphrase``,
  ``access_token``, ``refresh_token``, ``client_secret``,
  ``authorization``, matched case-insensitively and at any nesting depth
  inside dicts and lists), plus ``message``/``title`` for the ``notify``,
  ``tts``, and ``persistent_notification`` domains and ``payload`` for
  ``mqtt.publish``, are redacted to ``"[redacted]"`` before anything
  touches disk. That redaction runs inside ``async_log`` itself - one
  chokepoint every record passes through, never per-call-site (work item
  1.6). Core merges a call's target block into ``service_data``, so
  non-entity targets (``area_id``, ``device_id``, ``label_id``,
  ``floor_id``) are extracted into ``detail["targets"]`` alongside the
  top-level ``entity_ids``.
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

HA SOC's own actions (work item 1.4, D-14): beyond the core events above,
this project's own code calls ``async_log`` directly so the tool is in its
own chain - ``detection_status_changed`` and ``privileged_read`` from
websocket_api.py, ``firewall_resolved`` from firewall.py,
``probe_auth_rejected`` from probe.py, ``soc_config_change`` and the
user-management records from their handlers, and ``audit_chain_reset``
from this module itself (see the wipe-detection paragraph below).

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
  fabricate one. CONFIGURATION DEPENDENCY: this only works while the
  ``homeassistant.components.http.ban`` logger's effective level stays at
  WARNING or lower - raising it (via the ``logger:`` integration) stops
  the logger from emitting the record at all, and the attached handler
  never sees it, silently blinding failed-login auditing. health.py's
  ``audit_ban_logger_silenced`` check watches for exactly that.
- ``login_ok`` - polled every 30s by diffing each user's refresh tokens
  against a snapshot from the previous poll. A brand-new normal/webhook
  token, or an existing token whose ``last_used_at`` advanced, is logged as
  ``login_ok``. A token refresh looks identical to a fresh interactive
  login through this API, so this is best read as "this user's session was
  active", not "this user just typed a password". Each record's
  ``detail.new_token`` says which branch produced it (True: a token that
  did not exist on the previous poll; False: an existing token's activity
  advanced) - the closest available signal to "a new session began", and
  the one the success_after_failures detection rule keys on.
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
  hash chain is internally consistent from the retention anchor forward,
  i.e. nothing in the surviving files was edited without recomputing every
  hash after it. When retention has expired old day files, the anchor in
  ``chain_head.json`` records the seq and hash of the newest expired
  record, verification restarts the chain there, and the result reports
  ``verified_from_seq`` (1 when nothing has ever expired) plus
  ``expired_through`` so the operator can see exactly which prefix is
  attested by the anchor rather than re-checked record by record. It
  cannot prove the files were never touched: anything with the same
  filesystem access that reaches ``.storage/`` (an SSH/Terminal add-on,
  Samba, the File Editor add-on, root on the host) can rewrite
  ``chain_head.json``, the anchor inside it, and every record's hash to
  match. That makes this tamper-*evident*, not tamper-proof. Real
  integrity guarantees require exporting the chain off this box (e.g. to a
  remote syslog/SIEM) as it is written, which is out of scope for this
  module.

Storage: newline-delimited JSON, one file per UTC calendar day
(``audit-YYYY-MM-DD.jsonl``) under ``.storage/<AUDIT_STORAGE_SUBDIR>/``,
plus a tiny ``chain_head.json`` sidecar so the hash chain survives a
restart. The sidecar also carries the retention anchor described above,
written whenever retention deletes expired day files, so expiry does not
break verification of everything that survives. Records are only ever
appended; nothing is rewritten in place. All file I/O runs in the
executor - never on the event loop.

File modes (work item 1.1): the directory is created and kept 0o700, and
every file in it - day files, ``chain_head.json``, and its ``.tmp``
staging file - is opened through ``os.open`` with mode 0o600 so no other
uid on the host can read the log. Files a pre-1.1 build left wider are
tightened to 0o600 once at startup and the migration is logged at INFO.
This matches what core does for its own auth store; it does not (and
cannot) protect against the same-uid attacker described above.

Flush cadence (work item 1.7): the buffer normally drains on a 30 s
timer, but high-value categories (user lifecycle, HA SOC's own config
changes, every ``firewall_*`` record, ``detection_status_changed``,
``probe_auth_rejected``, ``audit_chain_reset``, ``privileged_read``)
schedule an immediate flush task instead, so the records most worth
tampering with reach the hash-chained files with the smallest possible
window in which a crash - or a kill - could drop them from the buffer.

Wipe/rollback detection (work item 1.5): after every successful flush the
head {seq, hash, at} is mirrored into the general HA SOC store
(``store.data["audit_head"]``), a separate file an attacker would have to
falsify consistently with the audit directory. At startup, an on-disk
head that is absent or behind that mirror means the directory was wiped,
replaced, or rolled back: an ``audit_chain_reset`` record carrying both
heads is written as the first record of the continued chain - with the
mirror's hash as its ``prev_hash``, so the discontinuity is itself
chained - a Repairs issue is raised, and ``chain_head.json`` keeps a
``reset`` marker. While that marker exists (it ages out when retention
expires the reset point), ``async_verify_chain`` reports
``reason: chain_reset`` even when everything after the reset re-verifies,
because the pre-reset history is gone and "ok" would be a false claim.
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

# Keys redacted wherever they appear in a detail payload, matched
# case-insensitively on the exact key name (never substring - "token_id"
# stays visible, "token" does not) and at any nesting depth inside dicts
# and lists (work item 1.6).
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
        # Beyond item 1.6's list: HA SOC's own Probe pairing secret rides
        # in the service_data of every ingest_probe_result and
        # poll_firewall_command call, and the call_service bus event
        # delivers that service_data straight into this module. Without
        # this key the audit chain would archive the pairing credential
        # verbatim on every poll.
        "probe_secret",
    }
)
# Domains whose message/title content is personal, not operational: what a
# notification SAID is none of the audit log's business, only that one was
# sent. persistent_notification joined notify/tts in work item 1.6.
_REDACTED_MESSAGE_DOMAINS = frozenset({"notify", "tts", "persistent_notification"})

# Categories flushed to disk immediately (work item 1.7) rather than on the
# 30 s timer, matched exactly or (for the prefixes) on startswith. These are
# the records an attacker is most motivated to keep out of the chain, so
# the buffer window for them is minimized. Public module constant so tests
# can assert the set matches the plan.
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
    }
)
IMMEDIATE_FLUSH_PREFIXES = ("firewall_",)

# Public so health.py's audit_ban_logger_silenced check reads the exact
# logger name this module's login_fail capture depends on, instead of
# duplicating the string and drifting.
BAN_LOGGER_NAME = "homeassistant.components.http.ban"
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


def _redact_service_data(
    domain: str | None, service: str | None, value: Any
) -> Any:
    """Recursively mask credential-shaped keys in a detail payload.

    Called on every record's ``detail`` from inside ``async_log`` - the
    single chokepoint of work item 1.6 - so no call path can forget to
    redact. Three rules, and why each is shaped the way it is:

    - A key in ``_REDACTED_SERVICE_DATA_KEYS`` is masked wherever it
      appears (any depth, inside lists too), matched case-insensitively on
      the EXACT key name: substring matching would eat harmless keys like
      ``token_id`` that the panel legitimately displays.
    - ``message`` and ``title`` are masked for the notify/tts/
      persistent_notification domains, and only when the record is a
      service call (``service is not None``): a config-entry record for
      the same domain carries a ``title`` that is the entry's display
      name, not a notification body, and masking it would just destroy
      information.
    - ``payload`` is masked for ``mqtt.publish`` specifically, because an
      MQTT payload routinely carries whatever the automation put in it,
      credentials included, and no generic key rule can know that.

    Values are replaced unconditionally (even empty ones) so the log never
    reveals whether a credential field was filled in.
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
        # Retention anchor: the seq and hash of the newest record whose day
        # file retention has deleted, plus when and through which day it
        # expired. Kept in memory so every chain-head rewrite preserves it;
        # None until retention first deletes something.
        self._anchor: dict[str, Any] | None = None
        # Chain-reset marker (work item 1.5): {seq, hash, at, disk_head_seq}
        # of the store-mirrored head a wiped/rolled-back on-disk chain was
        # continued from. Kept in memory for the same reason as the anchor
        # (every head rewrite must preserve it) and cleared only when
        # retention expires the reset point itself.
        self._reset: dict[str, Any] | None = None
        # Whether _sync_load_chain_head found a head file at all, so reset
        # detection can distinguish "directory wiped" (no head) from "head
        # rolled back" (head present but behind the store mirror).
        self._head_file_found = False
        # The in-flight immediate-flush task (work item 1.7), so a burst of
        # high-value records schedules one flush, not one task per record.
        self._flush_task: asyncio.Task[None] | None = None
        # Whether _sync_load_chain_head has run. Immediate flushing is
        # gated on this: an instance that has not loaded the head still
        # carries genesis seq/prev_hash, and flushing it would chain new
        # records from the wrong point and rewrite chain_head.json
        # backwards over a live chain. Until then, records only buffer.
        self._head_loaded = False

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
        # Reset detection must run after the head is loaded and before any
        # listener can log, so the audit_chain_reset record is the FIRST
        # record of the continued chain and carries the mirror's hash as
        # its prev_hash (work item 1.5).
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

    # -- Wipe / rollback detection (work item 1.5) -----------------------

    @callback
    def _async_detect_chain_reset(self) -> None:
        """Compare the loaded on-disk head against the store's mirror.

        The mirror (store.data["audit_head"]) is written after every
        successful flush, into a different file than the audit directory.
        If the on-disk head is absent or behind it, the directory was
        wiped, replaced, or rolled back since that flush. The response is
        threefold: an audit_chain_reset record carrying both heads (logged
        first, so it becomes the first record of the continued chain, with
        the mirror's hash as its prev_hash - the discontinuity is itself
        chained), a Repairs issue so a human actually sees it, and a
        persistent reset marker in chain_head.json that keeps
        verification honest (reason chain_reset) until the reset point
        ages out under retention.

        An on-disk head AHEAD of the mirror is normal, not suspicious: the
        mirror's save is debounced, so a crash can lose its last update
        while the chain head was written synchronously with the flush.
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
        # Continue numbering and chaining from the mirror rather than from
        # genesis: the next record (the audit_chain_reset record logged
        # just below) gets seq mirror_seq + 1 and prev_hash mirror_hash,
        # so the break in history is itself part of the chain.
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

        # Local import: repairs.py exists precisely so single call sites
        # like this one do not spread issue_registry imports around, and
        # importing it lazily keeps this module's import graph minimal.
        from .repairs import async_create_audit_chain_reset_issue

        async_create_audit_chain_reset_issue(
            self.hass,
            store_seq=mirror_seq,
            disk_seq=self._reset["disk_head_seq"],
        )

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
        # No redaction here on purpose: async_log is the single redaction
        # chokepoint (work item 1.6), and it receives domain and service
        # below, which is all _redact_service_data needs.
        detail = dict(service_data)
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
        events: list[tuple[str, str | None, str | None, dict[str, Any] | None]] = []

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

                # login_ok records carry detail.new_token so consumers can
                # tell a brand-new refresh token (this previous-is-None
                # branch) from an existing token whose last_used_at merely
                # advanced. detections.py's success_after_failures rule
                # depends on that distinction (work item 3.8): a token
                # refresh is not a login, and treating it as one is what
                # made the rule fire on background activity.
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
        flush: bool = False,
    ) -> None:
        """Append a normalized record to the in-memory buffer. No I/O here.

        Event-loop only (bus listeners, the token poll, and the ban log
        handler's threadsafe handoff all call this from the loop) - it must
        stay a plain, synchronous, non-blocking callback.

        This is the single redaction chokepoint (work item 1.6): every
        detail payload passes through _redact_service_data (credential-
        shaped keys, deep) and _redact_secrets_deep (HA SOC's own secret
        setting keys) here, so no caller can forget.

        ``flush=True`` forces an immediate flush task; the high-value
        categories in IMMEDIATE_FLUSH_CATEGORIES / IMMEDIATE_FLUSH_PREFIXES
        get one regardless (work item 1.7), so a caller outside this module
        - probe.py's probe_auth_rejected, for one - cannot skip it by
        omitting the flag.
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
        """Schedule one immediate flush task (work item 1.7).

        eager_start=False on purpose: an eagerly-started task would drain
        the buffer synchronously inside the caller's frame, turning
        async_log from "append and return" into "append, hash, and hand
        off to the executor" mid-listener. Deferring to the next loop
        iteration keeps async_log non-blocking and lets a burst of
        high-value records ride one flush. The done-check (rather than a
        None reset in a callback) is enough dedup: a task that is done has
        already drained whatever was buffered when it ran, and anything
        logged after that schedules a fresh one.

        No-op until the chain head has been loaded: before that, this
        instance's seq starts at genesis, and a flush would write records
        numbered from 1 and clobber chain_head.json over whatever chain is
        actually on disk. Records buffer instead, exactly as they did
        before work item 1.7, and the start-time load makes them eligible.
        """
        if not self._head_loaded:
            return
        if self._flush_task is not None and not self._flush_task.done():
            return
        self._flush_task = self.hass.async_create_task(
            self._async_flush(), eager_start=False
        )

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
            flushed_ok = await self.hass.async_add_executor_job(
                self._sync_flush, records
            )
            if flushed_ok and records:
                # Mirror the flushed head into the general store (work item
                # 1.5) - on the event loop, after the executor job returned,
                # because store.data must never be mutated off-loop. _seq
                # and _prev_hash cannot have moved since the drain: the
                # flush lock is held and only _drain_and_prepare mutates
                # them. Only a successful flush advances the mirror; a
                # failed one would make the mirror attest records that
                # never reached disk.
                self._store.async_set_audit_head(
                    {
                        "seq": self._seq,
                        "hash": self._prev_hash,
                        "at": dt_util.utcnow().isoformat(),
                    }
                )

    # -- Executor-only I/O ------------------------------------------------

    def _sync_ensure_dir(self) -> None:
        """Create the audit directory 0o700 and tighten what already exists.

        makedirs' mode is subject to the process umask and ignored entirely
        for a directory that already exists, so the explicit chmod is what
        actually guarantees 0o700 in both cases (work item 1.1). Files a
        pre-1.1 build created with default modes are tightened to 0o600
        once and the migration is logged at INFO; on an already-migrated
        directory the loop finds nothing to change and logs nothing.
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

        A plain open() creates files with the process umask (typically
        0o644); routing creation through os.open pins 0o600 at creation
        time so there is no window in which a new day file or head temp
        file is readable by another uid (work item 1.1). os.fdopen wraps
        the descriptor into a normal text file object; the mode argument
        only matters at creation, existing files keep their (already
        tightened) mode.
        """
        fd = os.open(path, flags, 0o600)
        return os.fdopen(fd, "w", encoding="utf-8")

    def _sync_load_chain_head(self) -> None:
        # Whatever this method concludes - a restored head, or a legitimate
        # fresh chain because nothing was on disk - is the real starting
        # point, so immediate flushing (gated on this flag, see __init__)
        # becomes safe the moment it has run.
        self._head_loaded = True
        path = os.path.join(self._dir_path, _CHAIN_HEAD_FILENAME)
        self._head_file_found = os.path.exists(path)
        if self._head_file_found:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                self._prev_hash = data.get("prev_hash", _GENESIS_PREV_HASH)
                self._seq = int(data.get("seq", 0))
                # The retention anchor rides along in the head file and must
                # be restored across restarts, or the next head rewrite
                # would silently drop it and expiry would break the chain.
                anchor = data.get("anchor")
                self._anchor = anchor if isinstance(anchor, dict) else None
                # The reset marker (work item 1.5) is restored for the same
                # reason: dropping it on the first post-restart head write
                # would make a wiped chain verify clean again.
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
        # Every head rewrite must carry the retention anchor forward. Losing
        # it here would make a healthy log unverifiable from the first flush
        # after retention expired anything. The reset marker is carried for
        # the same reason (see the module docstring on 1.5).
        if self._anchor is not None:
            payload["anchor"] = self._anchor
        if self._reset is not None:
            payload["reset"] = self._reset
        try:
            # The temp file is created 0o600 through os.open (work item
            # 1.1); os.replace then preserves that mode on the real head.
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
        """Append prepared records and maintain the head. Returns whether
        the write succeeded, so the caller only advances the store's head
        mirror over records that actually reached disk (work item 1.5).
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
                    # os.open with O_APPEND and mode 0o600 (work item 1.1):
                    # a brand-new day file is born private, and appends to
                    # an existing one behave exactly like open(..., "a").
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

        # Every unlink below removes the front of the hash chain, so the
        # tail (seq, hash) of each file is captured before removal and the
        # highest one becomes the retention anchor that verification
        # restarts the chain from. Only files that were actually removed
        # count; a file that survived an unlink failure still verifies.
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
        # kept is oldest-first; never delete the last remaining file, even
        # if that alone exceeds the cap - losing the entire log is worse
        # than briefly going over budget.
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
            # Files were removed but none yielded a parseable tail record,
            # so there is nothing truthful to anchor on. Any existing anchor
            # is left in place and verification will honestly fail at the
            # new front of the log rather than being papered over.
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
            # Deletions proceed oldest-first, so a new anchor should always
            # be ahead of the old one; if it somehow is not, keeping the
            # further-along anchor is the conservative choice.
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
            # Once the retention anchor has advanced past the reset point,
            # the wiped range (and the audit_chain_reset record documenting
            # it) has aged out of the retained window; keeping the marker
            # would make verification fail forever over records that are
            # legitimately gone. The reset stays discoverable in the store
            # mirror's history and the Repairs issue until dismissed.
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

    # -- Category volume stats -------------------------------------------

    async def async_category_stats(self) -> dict[str, Any]:
        """Per-category record counts and byte shares for the newest day.

        Answers the open-items report's volume observation (a busy install
        writes on the order of 10 MB of audit records per day) by showing
        the owner WHAT produces the bulk, so retention and size-cap tuning
        stops being guesswork. Deliberately cheap: only the newest day's
        file(s) are scanned - a day is normally one file, plus rollover
        segments only past 32 MB - in one pass each, with no new storage
        and nothing indexed. Flushes first so the current day's buffered
        records are counted.
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
            # Read as bytes so byte shares reflect what is actually on
            # disk, not a post-decode character count.
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

    # -- Chain verification ---------------------------------------------

    async def async_verify_chain(self) -> dict[str, Any]:
        """Recompute the hash chain and check it end to end.

        This proves the on-disk log is internally consistent - i.e. every
        surviving record's hash still matches ``prev_hash`` plus its own
        content - starting from the retention anchor when old day files
        have expired, or from the first record ever written when nothing
        has. The result reports ``verified_from_seq`` (1 when there is no
        anchor) and ``expired_through`` (the last expired day, or None) so
        the caller can state exactly which range was re-checked; records at
        or before the anchor are attested only by the anchor's stored hash.
        It does NOT prove the files were never tampered with: anyone who
        can reach ``.storage/`` with the same filesystem access this
        integration has (an SSH/Terminal add-on, Samba, the File Editor
        add-on, root on the host) can rewrite every hash, the head, and the
        anchor to be self-consistent again. Tamper-evident, not
        tamper-proof - real integrity needs an off-box export, which is out
        of scope for this module.

        Chain reset (work item 1.5): the result reports ``reason:
        chain_reset`` (with ``ok: False``) in two situations - when the
        store's head mirror is ahead of the on-disk chain head (the
        directory was wiped or rolled back and no restart has processed it
        yet), and while ``chain_head.json`` carries the reset marker a
        restart wrote after detecting exactly that (the continued chain
        after the reset point is still re-verified record by record, but
        "ok" would falsely claim an unbroken history). The marker ages out
        when retention expires the reset point.
        """
        # Flush first so the check covers everything logged so far and the
        # records-checked count matches what the query view shows. The
        # chain-head checkpoint is only written on flush, so this also
        # keeps the completeness check consistent with the buffer.
        await self._async_flush()
        return await self.hass.async_add_executor_job(self._sync_verify_chain)

    def _sync_verify_chain(self) -> dict[str, Any]:
        # The anchor and reset marker are read from disk, not from memory,
        # for the same reason the checkpoint below is: verification must
        # judge what an attacker could have edited, not what this process
        # remembers.
        anchor_seq, anchor_hash, expired_through = self._sync_read_chain_head_anchor()
        reset = self._sync_read_chain_head_reset()

        # The chain walk starts from whichever discontinuity point is
        # further along: the retention anchor (records legitimately
        # expired) or the reset marker (records lost to a wipe/rollback,
        # work item 1.5). Both carry the seq and hash the surviving chain
        # continues from; only the verdict differs - an anchored start can
        # end in ok, a reset start never can while the marker exists.
        start_seq, start_hash = anchor_seq, anchor_hash
        start_is_reset = False
        if reset is not None and (start_seq is None or reset[0] > start_seq):
            start_seq, start_hash = reset
            start_is_reset = True
        verified_from_seq = start_seq + 1 if start_seq is not None else 1

        prev_hash = start_hash if start_seq is not None else _GENESIS_PREV_HASH
        checked = 0
        # With a start point, the missing prefix legitimately ends at its
        # seq; starting last_seq there keeps the completeness check from
        # reading expiry (possibly of every file) as truncation.
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

        # A start-point contradiction is reported under the name of the
        # marker being contradicted, so the operator is told which claim
        # and which files disagree.
        start_break_reason = "chain_reset" if start_is_reset else "anchor_inconsistent"

        # Wipe/rollback while running (work item 1.5): the store's mirror
        # of the last flushed head lives in a different file than anything
        # under the audit directory, so a checkpoint that has fallen
        # behind it means the directory contents were replaced with an
        # older copy (or recreated from nothing) since that flush. Reading
        # the mirror from store.data here is a read-only dict access from
        # the executor, the same pattern _sync_apply_retention already
        # uses for settings.
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
                    # No surviving record may sit at or before the start
                    # point: the anchor asserts everything through its seq
                    # was expired, and the reset marker asserts everything
                    # through its seq was lost, so such a record is either
                    # resurrected old data or a forged marker, and either
                    # way the log and the marker cannot both be telling
                    # the truth.
                    if seq <= start_seq:
                        return _fail(start_break_reason, seq)
                    # The first surviving record must be the start point's
                    # direct successor; a gap means records written after
                    # it are missing.
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
        if head_seq is not None and (last_seq < head_seq or prev_hash != head_hash):
            return _fail(
                "tail_truncated",
                None,
                checkpoint_seq=head_seq,
                last_on_disk_seq=last_seq,
            )

        if reset is not None:
            # Everything after the reset point re-verified clean, but the
            # history before it is gone and only the store mirror ever
            # attested where it ended - reporting ok here would claim an
            # unbroken chain that does not exist. The marker (and with it
            # this verdict) ages out when retention expires the reset
            # point; until then the honest answer is "reset, then clean".
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
        """Read chain_head.json straight from disk, ignoring the in-memory
        head, so the checks above judge what an attacker could have edited.
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
        """The persisted chain head (seq, prev_hash), for the completeness
        check above. Returns (None, "") when no checkpoint exists yet (fresh
        install) or the head file is unreadable.
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

        Returns (None, "", None) when no anchor exists or the stored one is
        malformed; verification then starts at genesis, which fails loudly
        (rather than silently passing) if records really did expire.
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

        Written by _async_detect_chain_reset when a startup found the
        on-disk head behind the store's mirror (work item 1.5), preserved
        by every head rewrite, and cleared when retention expires the
        reset point. A malformed marker reads as absent, which fails
        loudly at the walk (the post-reset records' prev_hash chain has
        nowhere valid to start) rather than silently passing.
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
