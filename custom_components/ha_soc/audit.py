"""Append-only, hash-chained audit log for HA SOC.

This module is the closest thing HA SOC has to a security camera pointed at
Home Assistant's own auth/service/registry surface. It is intentionally
narrow: it only listens to bus events and log records that Home Assistant
core already emits, and it never touches ``state_changed`` or a
``MATCH_ALL`` listener. What follows is an honest accounting of what is
actually captured, what is inferred/best-effort, and what is structurally
impossible from inside an integration - overclaiming any of this in a
security product is worse than not having the feature.

Captured directly (one bus event per record):

- ``service_call`` - every ``call_service`` event. This fires *before*
  permission checks and *before* the service actually runs, so it records
  an attempted call, not its outcome or even whether it was authorized.
  Obviously-sensitive ``service_data`` keys (``password``, ``token``,
  ``code``, and ``message`` for ``notify``/``tts`` domains) are redacted to
  ``"[redacted]"`` before anything touches disk.
- ``user_added`` / ``user_updated`` / ``user_removed`` - the three
  ``homeassistant.auth`` lifecycle events.
- ``lovelace_change`` - ``lovelace_updated`` (a dashboard was edited).
- ``entity_registry_change`` - ``entity_registry_updated`` (create/update/
  remove on the entity registry).

Best-effort / inferred (no bus event exists for these - confirmed against
home-assistant/core's dev branch - so they are reconstructed indirectly):

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
  ``long_lived_access_token`` id.

Out of scope / structurally impossible from here:

- The username behind a failed login attempt - Home Assistant does not
  record it anywhere an integration can reach.
- Permission-denied errors raised inside a service call or over the REST
  API - there is no bus event or log hook for these at all.
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
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import AUDIT_STORAGE_SUBDIR
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

_LOGGER = logging.getLogger(__name__)

Unsub = Callable[[], None]

_FLUSH_INTERVAL = timedelta(seconds=30)
_POLL_INTERVAL = timedelta(seconds=30)

_CHAIN_HEAD_FILENAME = "chain_head.json"
_FILENAME_RE = re.compile(r"^audit-(\d{4}-\d{2}-\d{2})\.jsonl$")
_GENESIS_PREV_HASH = ""

_DEFAULT_QUERY_LOOKBACK = timedelta(days=7)

_REDACTED_SERVICE_DATA_KEYS = frozenset({"password", "token", "code"})
_REDACTED_MESSAGE_DOMAINS = frozenset({"notify", "tts"})

_BAN_LOGGER_NAME = "homeassistant.components.http.ban"
# Real message (see homeassistant/components/http/ban.py):
#   "Login attempt or request with invalid authentication from %s (%s)."
#   record.args == (remote_host, remote_addr)
# The regex is a fallback only, in case that internal message ever changes
# shape without a matching args tuple.
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
        # Prefer the structured args tuple - (remote_host, remote_addr) -
        # over regexing the formatted message.
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

    # -- Event handlers -------------------------------------------------

    def _handle_call_service(self, event: Event) -> None:
        # Fires before permission checks and before the service runs - this
        # is an attempted call, not a confirmed outcome. See module
        # docstring; do not let a future edit here imply otherwise.
        domain = event.data.get(ATTR_DOMAIN)
        service = event.data.get(ATTR_SERVICE)
        service_data = event.data.get(ATTR_SERVICE_DATA) or {}
        entity_ids = _normalize_entity_ids(
            service_data.get("entity_id") if isinstance(service_data, dict) else None
        )
        detail = _redact_service_data(domain, service_data)
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
        user_id = event.data.get("user_id")
        name = await self._async_resolve_user_name(user_id)
        self.async_log("user_added", user_id=user_id, detail={"name": name})

    async def _handle_user_updated(self, event: Event) -> None:
        user_id = event.data.get("user_id")
        name = await self._async_resolve_user_name(user_id)
        self.async_log("user_updated", user_id=user_id, detail={"name": name})

    def _handle_user_removed(self, event: Event) -> None:
        # The user is already gone by the time this fires - nothing left to
        # resolve, just log the id core gave us.
        user_id = event.data.get("user_id")
        self.async_log("user_removed", user_id=user_id, detail={})

    async def _async_resolve_user_name(self, user_id: str | None) -> str | None:
        if user_id is None:
            return None
        try:
            user = await self.hass.auth.async_get_user(user_id)
        except Exception:  # noqa: BLE001 - best-effort enrichment only
            return None
        return user.name if user is not None else None

    def _handle_lovelace_updated(self, event: Event) -> None:
        url_path = event.data.get("url_path")
        context = event.context
        self.async_log(
            "lovelace_change",
            user_id=context.user_id,
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"url_path": url_path},
        )

    def _handle_entity_registry_updated(self, event: Event) -> None:
        action = event.data.get("action")
        entity_id = event.data.get("entity_id")
        changes = event.data.get("changes") or {}
        context = event.context
        self.async_log(
            "entity_registry_change",
            user_id=context.user_id,
            entity_ids=[entity_id] if entity_id else [],
            context_id=context.id,
            context_parent_id=context.parent_id,
            detail={"action": action, "changes": changes},
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
            "detail": detail if detail is not None else {},
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
                    file_path = os.path.join(self._dir_path, f"audit-{day}.jsonl")
                    with open(file_path, "a", encoding="utf-8") as handle:
                        handle.write("\n".join(lines) + "\n")
                self._sync_write_chain_head()
            self._sync_apply_retention()
        except OSError:
            _LOGGER.exception("HA SOC audit log: flush to disk failed")

    def _sync_list_day_files(self) -> list[tuple[date, str]]:
        if not os.path.isdir(self._dir_path):
            return []
        found: list[tuple[date, str]] = []
        for name in os.listdir(self._dir_path):
            match = _FILENAME_RE.match(name)
            if not match:
                continue
            try:
                file_date = date.fromisoformat(match.group(1))
            except ValueError:
                continue
            found.append((file_date, os.path.join(self._dir_path, name)))
        found.sort(key=lambda entry: entry[0])
        return found

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
        return await self.hass.async_add_executor_job(self._sync_verify_chain)

    def _sync_verify_chain(self) -> dict[str, Any]:
        prev_hash = _GENESIS_PREV_HASH
        checked = 0

        for _file_date, path in self._sync_list_day_files():
            for line in self._read_jsonl(path):
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    return {
                        "ok": False,
                        "records_checked": checked,
                        "first_break_seq": None,
                    }

                checked += 1
                seq = record.get("seq")
                stored_hash = record.get("hash")

                if record.get("prev_hash") != prev_hash:
                    return {
                        "ok": False,
                        "records_checked": checked,
                        "first_break_seq": seq,
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
                    }

                prev_hash = stored_hash

        return {"ok": True, "records_checked": checked, "first_break_seq": None}
