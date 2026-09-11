"""The HA SOC Terminal app, reached only through this integration.

The app runs ttyd on the Supervisor's internal network with no ingress. A
browser never talks to it: the panel opens a session through the
``ha_soc/terminal/*`` WebSocket commands, this module holds one aiohttp
WebSocket to ttyd per session, and every byte crosses here. That is what
makes the terminal tiered (the same owner-or-admins gate as the rest of the
panel), counted (one session per user, three per install), bounded (a hard
maximum duration) and audited (open and close records with byte counts).

Pairing follows the Probe's model: the app generates a secret once, ttyd
requires it as HTTP basic auth, and the app hands it to Core through the
``ha_soc.pair_terminal`` service, which accepts only a call carrying the
Supervisor user's context and pins the first secret it sees. Design, phases
and residuals: docs/TERMINAL-DESIGN.md; wire shapes: docs/protocol.md.
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import json
import logging
import secrets as secrets_module
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

import aiohttp
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.hassio import is_hassio
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .probe import async_supervisor_call_rejection
from .secrets_store import TERMINAL_SECRET_KEY, HaSocSecretStore
from .store import HaSocData

if TYPE_CHECKING:
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

SERVICE_PAIR = "pair_terminal"
APP_SLUG = "ha_soc_terminal"
TTYD_PORT = 7681
TTYD_USER = "hasoc"

AUDIT_CATEGORY_OPEN = "terminal_session_open"
AUDIT_CATEGORY_CLOSE = "terminal_session_close"
AUDIT_CATEGORY_PAIRING_REJECTED = "terminal_pairing_rejected"

MAX_SESSIONS_PER_USER = 1
MAX_SESSIONS_TOTAL = 3
MAX_SESSION_SECONDS = 8 * 3600
CONNECT_TIMEOUT_SECONDS = 10
MAX_INPUT_BYTES = 64 * 1024

TARGET_SELF = "self"

# Coded refusals the panel branches on.
ERR_NOT_SUPERVISOR = "not_supervisor"
ERR_NOT_INSTALLED = "app_not_installed"
ERR_NOT_RUNNING = "app_not_running"
ERR_NOT_PAIRED = "app_not_paired"
ERR_LIMIT_USER = "session_limit_user"
ERR_LIMIT_TOTAL = "session_limit_total"
ERR_UNKNOWN_TARGET = "unknown_target"
ERR_UNKNOWN_SESSION = "unknown_session"
ERR_CONNECT = "connect_failed"

# ttyd's wire protocol: one command byte then the payload, in both directions.
_TTYD_INPUT = b"0"
_TTYD_RESIZE = b"1"
_TTYD_OUTPUT = 0x30
_TTYD_TITLE = 0x31
_TTYD_PREFERENCES = 0x32

PAIR_SCHEMA = vol.Schema(
    {
        vol.Required("secret"): vol.All(str, vol.Length(min=32, max=256)),
        vol.Optional("version"): str,
    }
)


class TerminalError(Exception):
    """A refusal carrying the code the panel branches on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# --- the app, as the Supervisor sees it ------------------------------------


def _installed_addon(hass: HomeAssistant) -> dict[str, Any] | None:
    """The app's entry in the Supervisor's cached add-on list, or None.

    The slug the Supervisor assigns is ``{repository}_{slug}``; matching on
    the suffix avoids knowing the repository hash.
    """
    try:
        from homeassistant.components.hassio import get_supervisor_info
    except Exception:  # noqa: BLE001 - not a Supervisor install
        return None
    info = get_supervisor_info(hass) or {}
    for addon in info.get("addons") or []:
        slug = str(addon.get("slug") or "")
        if slug == APP_SLUG or slug.endswith(f"_{APP_SLUG}"):
            return dict(addon)
    return None


async def _addon_info(hass: HomeAssistant, slug: str) -> dict[str, Any] | None:
    """``GET /addons/{slug}/info``: hostname, state, version, and (for Core) options."""
    try:
        from homeassistant.components.hassio.const import DATA_COMPONENT

        hassio = hass.data[DATA_COMPONENT]
        result = await hassio.send_command(f"/addons/{slug}/info", method="get", timeout=10)
    except Exception as err:  # noqa: BLE001 - surfaced as not available, never raised
        _LOGGER.debug("Terminal app info failed: %s", err)
        return None
    data = result.get("data") if isinstance(result, dict) else None
    return data if isinstance(data, dict) else None


async def async_terminal_status(hass: HomeAssistant, secrets: HaSocSecretStore, sessions: "TerminalSessions") -> dict[str, Any]:
    """Everything the panel needs to decide what to offer."""
    status: dict[str, Any] = {
        "supervisor": is_hassio(hass),
        "installed": False,
        "running": False,
        "paired": bool(await secrets.async_get(TERMINAL_SECRET_KEY)),
        "version": None,
        "hostname": None,
        "recording": None,
        "targets": [{"id": TARGET_SELF, "label": "Terminal app shell", "available": False}],
        "sessions_open": len(sessions.sessions),
        "max_sessions": MAX_SESSIONS_TOTAL,
        "max_session_seconds": MAX_SESSION_SECONDS,
    }
    if not status["supervisor"]:
        return status
    addon = _installed_addon(hass)
    if addon is None:
        return status
    status["installed"] = True
    status["version"] = addon.get("version")
    info = await _addon_info(hass, str(addon["slug"]))
    if info:
        status["running"] = info.get("state") == "started"
        status["hostname"] = info.get("hostname")
        options = info.get("options") if isinstance(info.get("options"), dict) else {}
        if "session_recording" in options:
            status["recording"] = bool(options["session_recording"])
    else:
        status["running"] = addon.get("state") == "started"
    status["targets"][0]["available"] = bool(status["running"] and status["paired"])
    return status


# --- pairing ----------------------------------------------------------------


def async_register_pairing_service(
    hass: HomeAssistant, store: HaSocData, audit: "AuditLog", secrets: HaSocSecretStore
) -> None:
    """``ha_soc.pair_terminal``: the app hands Core the ttyd credential.

    Accepted only from the Supervisor user's context (the app calls through
    the Supervisor's Core proxy). The first secret is pinned; a later call
    with a different secret is refused and audited, because the app only
    ever generates its secret once and a different one means something else
    is claiming to be the app. Replacing the app's data directory is the
    documented way to re-pair; see docs/operations.md.
    """
    if not is_hassio(hass):
        _LOGGER.debug("HA SOC: not a Supervisor install; pair_terminal is not registered.")
        return

    async def _handle(call: ServiceCall) -> dict[str, Any]:
        reason = await async_supervisor_call_rejection(hass, store, call)
        presented = call.data["secret"]
        if reason is None:
            pinned = await secrets.async_get(TERMINAL_SECRET_KEY)
            if pinned is None:
                await secrets.async_set(TERMINAL_SECRET_KEY, presented)
                _LOGGER.info("HA SOC: paired the Terminal app (first call).")
                return {"accepted": True, "pinned": True}
            if hmac.compare_digest(pinned, presented):
                return {"accepted": True, "pinned": False}
            reason = "secret_mismatch"
        audit.async_log(
            AUDIT_CATEGORY_PAIRING_REJECTED,
            user_id=call.context.user_id,
            detail={"reason": reason, "caller_user_id": call.context.user_id, "version": call.data.get("version")},
            flush=True,
        )
        return {"accepted": False, "pinned": False, "rejected": reason}

    hass.services.async_register(
        DOMAIN, SERVICE_PAIR, _handle, schema=PAIR_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )


def async_unregister_pairing_service(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_PAIR):
        hass.services.async_remove(DOMAIN, SERVICE_PAIR)


async def async_forget_pairing(secrets: HaSocSecretStore) -> None:
    await secrets.async_set(TERMINAL_SECRET_KEY, None)


# --- sessions ---------------------------------------------------------------


@dataclass
class TerminalSession:
    session_id: str
    user_id: str
    target: str
    host: str
    started: datetime
    send: Callable[[dict[str, Any]], None]
    ws: aiohttp.ClientWebSocketResponse
    bytes_in: int = 0
    bytes_out: int = 0
    reader: asyncio.Task | None = None
    closed: bool = False
    close_reason: str | None = None
    title: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class TerminalSessions:
    """Every open terminal session, and the one place they are opened and closed."""

    def __init__(self, hass: HomeAssistant, audit: "AuditLog", secrets: HaSocSecretStore) -> None:
        self._hass = hass
        self._audit = audit
        self._secrets = secrets
        self.sessions: dict[str, TerminalSession] = {}

    def _for_user(self, user_id: str) -> list[TerminalSession]:
        return [s for s in self.sessions.values() if s.user_id == user_id]

    async def async_open(
        self,
        *,
        user_id: str,
        target: str,
        cols: int,
        rows: int,
        send: Callable[[dict[str, Any]], None],
    ) -> TerminalSession:
        if target != TARGET_SELF:
            raise TerminalError(ERR_UNKNOWN_TARGET, f"Unknown terminal target {target!r}")
        if not is_hassio(self._hass):
            raise TerminalError(ERR_NOT_SUPERVISOR, "The terminal needs a Supervisor-based install")
        if len(self._for_user(user_id)) >= MAX_SESSIONS_PER_USER:
            raise TerminalError(ERR_LIMIT_USER, "You already have a terminal session open; close it first")
        if len(self.sessions) >= MAX_SESSIONS_TOTAL:
            raise TerminalError(ERR_LIMIT_TOTAL, f"{MAX_SESSIONS_TOTAL} sessions are already open on this install")

        addon = _installed_addon(self._hass)
        if addon is None:
            raise TerminalError(ERR_NOT_INSTALLED, "The HA SOC Terminal app is not installed")
        info = await _addon_info(self._hass, str(addon["slug"]))
        if not info or info.get("state") != "started":
            raise TerminalError(ERR_NOT_RUNNING, "The HA SOC Terminal app is not running; start it first")
        host = str(info.get("hostname") or "")
        if not host:
            raise TerminalError(ERR_NOT_RUNNING, "The Supervisor reported no hostname for the Terminal app")
        secret = await self._secrets.async_get(TERMINAL_SECRET_KEY)
        if not secret:
            raise TerminalError(
                ERR_NOT_PAIRED,
                "The Terminal app has not paired with HA SOC yet; it does so within a minute of starting",
            )

        ws = await self._connect(host, secret, cols, rows)
        session = TerminalSession(
            session_id=secrets_module.token_urlsafe(12),
            user_id=user_id,
            target=target,
            host=host,
            started=dt_util.utcnow(),
            send=send,
            ws=ws,
        )
        self.sessions[session.session_id] = session
        session.reader = self._hass.async_create_background_task(
            self._read(session), f"ha_soc terminal {session.session_id}"
        )
        self._audit.async_log(
            AUDIT_CATEGORY_OPEN,
            user_id=user_id,
            detail={"session_id": session.session_id, "target": target, "host": host, "cols": cols, "rows": rows},
            flush=True,
        )
        return session

    async def _connect(self, host: str, secret: str, cols: int, rows: int) -> aiohttp.ClientWebSocketResponse:
        """One WebSocket to ttyd, authenticated, with the size handshake sent.

        Kept as a method so the tests replace it; nothing else in the module
        touches the network.
        """
        session = async_get_clientsession(self._hass)
        url = f"ws://{host}:{TTYD_PORT}/ws"
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
                ws = await session.ws_connect(
                    url,
                    protocols=("tty",),
                    auth=aiohttp.BasicAuth(TTYD_USER, secret),
                    heartbeat=30,
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise TerminalError(ERR_CONNECT, f"Could not reach the Terminal app at {host}: {err}") from err
        await ws.send_str(json.dumps({"AuthToken": "", "columns": cols, "rows": rows}))
        return ws

    async def _read(self, session: TerminalSession) -> None:
        """Forward ttyd's frames to the panel until either side goes away."""
        deadline = self._hass.loop.time() + MAX_SESSION_SECONDS
        reason = "remote_closed"
        try:
            while True:
                remaining = deadline - self._hass.loop.time()
                if remaining <= 0:
                    reason = "max_duration"
                    break
                try:
                    msg = await asyncio.wait_for(session.ws.receive(), timeout=remaining)
                except asyncio.TimeoutError:
                    reason = "max_duration"
                    break
                if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSED):
                    break
                if msg.type == aiohttp.WSMsgType.ERROR:
                    reason = "error"
                    break
                if msg.type == aiohttp.WSMsgType.BINARY:
                    payload = msg.data
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    payload = msg.data.encode("utf-8")
                else:
                    continue
                if not payload:
                    continue
                command, body = payload[0], payload[1:]
                if command == _TTYD_OUTPUT:
                    session.bytes_out += len(body)
                    session.send({"kind": "output", "data": base64.b64encode(body).decode("ascii")})
                elif command == _TTYD_TITLE:
                    session.title = body.decode("utf-8", errors="replace")
                    session.send({"kind": "title", "title": session.title})
                elif command == _TTYD_PREFERENCES:
                    continue
        except asyncio.CancelledError:
            reason = session.close_reason or "cancelled"
            raise
        except Exception as err:  # noqa: BLE001 - a broken session must close, not crash the loop
            _LOGGER.debug("Terminal session %s reader failed: %s", session.session_id, err)
            reason = "error"
        finally:
            await self._finish(session, reason)

    async def async_input(self, session_id: str, user_id: str, data_b64: str) -> None:
        session = self._get(session_id, user_id)
        try:
            data = base64.b64decode(data_b64, validate=True)
        except (ValueError, TypeError) as err:
            raise TerminalError(ERR_UNKNOWN_SESSION, "Input was not valid base64") from err
        if len(data) > MAX_INPUT_BYTES:
            raise TerminalError(ERR_UNKNOWN_SESSION, "Input frame too large")
        session.bytes_in += len(data)
        await session.ws.send_bytes(_TTYD_INPUT + data)

    async def async_resize(self, session_id: str, user_id: str, cols: int, rows: int) -> None:
        session = self._get(session_id, user_id)
        await session.ws.send_bytes(_TTYD_RESIZE + json.dumps({"columns": cols, "rows": rows}).encode("utf-8"))

    async def async_close(self, session_id: str, user_id: str | None, reason: str = "user_closed") -> None:
        session = self.sessions.get(session_id)
        if session is None:
            raise TerminalError(ERR_UNKNOWN_SESSION, "No such terminal session")
        if user_id is not None and session.user_id != user_id:
            raise TerminalError(ERR_UNKNOWN_SESSION, "No such terminal session")
        session.close_reason = reason
        if session.reader is not None and not session.reader.done():
            session.reader.cancel()
            try:
                await session.reader
            except (asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        else:
            await self._finish(session, reason)

    async def async_close_all(self, reason: str = "unloaded") -> None:
        for session_id in list(self.sessions):
            try:
                await self.async_close(session_id, None, reason)
            except TerminalError:
                continue

    def _get(self, session_id: str, user_id: str) -> TerminalSession:
        session = self.sessions.get(session_id)
        if session is None or session.user_id != user_id or session.closed:
            raise TerminalError(ERR_UNKNOWN_SESSION, "No such terminal session")
        return session

    async def _finish(self, session: TerminalSession, reason: str) -> None:
        if session.closed:
            return
        session.closed = True
        session.close_reason = session.close_reason or reason
        self.sessions.pop(session.session_id, None)
        try:
            await session.ws.close()
        except Exception:  # noqa: BLE001
            pass
        duration = int((dt_util.utcnow() - session.started).total_seconds())
        self._audit.async_log(
            AUDIT_CATEGORY_CLOSE,
            user_id=session.user_id,
            detail={
                "session_id": session.session_id,
                "target": session.target,
                "host": session.host,
                "duration_seconds": duration,
                "bytes_in": session.bytes_in,
                "bytes_out": session.bytes_out,
                "reason": session.close_reason,
            },
            flush=True,
        )
        try:
            session.send({"kind": "closed", "reason": session.close_reason, "duration_seconds": duration})
        except Exception:  # noqa: BLE001 - the browser may already be gone
            pass

    @callback
    def async_session_summaries(self) -> list[dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "target": s.target,
                "started": s.started.isoformat(),
                "bytes_in": s.bytes_in,
                "bytes_out": s.bytes_out,
            }
            for s in self.sessions.values()
        ]
