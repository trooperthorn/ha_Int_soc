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
import hashlib
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
# The one-shot run/transcript listener (busybox httpd), same host and
# credential as ttyd, a different port so it can be reached without opening
# an interactive session. See ha_soc_terminal/rootfs/etc/services.d/ha_soc_terminal_httpd.
TERMINAL_HTTPD_PORT = 7682
RUN_MAX_TIMEOUT_SECONDS = 120
RUN_DEFAULT_TIMEOUT_SECONDS = 30
RUN_HTTP_TIMEOUT_PAD_SECONDS = 10

AUDIT_CATEGORY_OPEN = "terminal_session_open"
AUDIT_CATEGORY_CLOSE = "terminal_session_close"
AUDIT_CATEGORY_PAIRING_REJECTED = "terminal_pairing_rejected"
AUDIT_CATEGORY_APP_CONTROL = "terminal_app_control"
AUDIT_CATEGORY_FORGET_PAIRING = "terminal_forget_pairing"
AUDIT_CATEGORY_RUN = "terminal_run"
AUDIT_CATEGORY_EXPORT = "terminal_export"

EXPORT_KINDS = (
    "copy_screen",
    "copy_all",
    "copy_last",
    "download_screen",
    "download_all",
    "download_transcript",
    "copy_run",
    "download_run",
    "copy_logs",
    "download_logs",
)

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
ERR_TERMINAL_BUSY = "terminal_busy"
ERR_TRANSCRIPT_HASH_MISMATCH = "transcript_hash_mismatch"

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

        info = get_supervisor_info(hass) or {}
    except Exception:  # noqa: BLE001 - not a Supervisor install, or hassio not set up yet
        return None
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


# --- app control (Supervisor start/restart) ----------------------------------
#
# The app boots manual (docs/TERMINAL-DESIGN.md): after a host reboot it is
# stopped and, before this, the panel could only point the owner at Settings
# to start it by hand. This reuses the same Supervisor client the Probe
# restart button already calls (ws_probe_restart in websocket_api.py) so
# there is exactly one way this integration talks to the Supervisor's addon
# API, not two.


async def async_app_control(hass: HomeAssistant, action: str) -> dict[str, Any]:
    """Start or restart the Terminal app through the Supervisor. Never raises.

    Every failure mode comes back as {"ok": false, "reason": ...} so the
    calling websocket command can audit and report it without a try/except
    of its own.
    """
    if action not in ("start", "restart"):
        return {"ok": False, "reason": "unknown_action"}
    if not is_hassio(hass):
        return {"ok": False, "reason": ERR_NOT_SUPERVISOR}
    try:
        addon = _installed_addon(hass)
    except Exception:  # noqa: BLE001 - the cached add-on list may not exist yet
        addon = None
    if addon is None:
        return {"ok": False, "reason": ERR_NOT_INSTALLED}
    try:
        from homeassistant.components.hassio import get_supervisor_client
    except Exception:  # noqa: BLE001 - hassio internals not guaranteed stable
        return {"ok": False, "reason": "hassio_unavailable"}
    try:
        client = get_supervisor_client(hass)
    except Exception:  # noqa: BLE001
        return {"ok": False, "reason": "no_supervisor_client"}
    if client is None:
        return {"ok": False, "reason": "no_supervisor_client"}
    slug = str(addon["slug"])
    try:
        if action == "start":
            await client.addons.start_addon(slug)
        else:
            await client.addons.restart_addon(slug)
    except Exception as err:  # noqa: BLE001 - never let a websocket command raise
        _LOGGER.exception("Failed to %s the %s app", action, APP_SLUG)
        return {"ok": False, "reason": f"{action}_failed", "error": str(err)}
    return {"ok": True}


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
        # One-shot runs are not sessions (no reader task, nothing in
        # self.sessions); this is the only state that stops a second run
        # while a user's first one is still in flight.
        self._running_users: set[str] = set()

    def _for_user(self, user_id: str) -> list[TerminalSession]:
        return [s for s in self.sessions.values() if s.user_id == user_id]

    async def _target_host_and_secret(self) -> tuple[str, str]:
        """The app's hostname and paired secret, or the same refusals async_open uses."""
        if not is_hassio(self._hass):
            raise TerminalError(ERR_NOT_SUPERVISOR, "The terminal needs a Supervisor-based install")
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
        return host, secret

    async def async_run(self, *, user_id: str, command: str, timeout_seconds: int) -> dict[str, Any]:
        """POST a command to the app's run/transcript listener; one at a time per user.

        The overall wait is the command's own timeout plus a fixed pad for
        the HTTP round trip, so a command that runs the app's full
        ``timeout_seconds`` still gets a response before this call gives up.
        """
        if user_id in self._running_users:
            raise TerminalError(ERR_TERMINAL_BUSY, "A command is already running for you; wait for it to finish")
        host, secret = await self._target_host_and_secret()
        self._running_users.add(user_id)
        started = dt_util.utcnow()
        try:
            session = async_get_clientsession(self._hass)
            url = f"http://{host}:{TERMINAL_HTTPD_PORT}/cgi-bin/run"
            try:
                async with asyncio.timeout(timeout_seconds + RUN_HTTP_TIMEOUT_PAD_SECONDS):
                    async with session.post(
                        url,
                        json={"command": command, "timeout_seconds": timeout_seconds},
                        auth=aiohttp.BasicAuth(TTYD_USER, secret),
                    ) as resp:
                        data = await resp.json(content_type=None)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
                raise TerminalError(ERR_CONNECT, f"Could not reach the Terminal app at {host}: {err}") from err
        finally:
            self._running_users.discard(user_id)
        if not isinstance(data, dict) or "error" in data:
            message = data.get("error") if isinstance(data, dict) else "malformed response"
            raise TerminalError(ERR_CONNECT, f"The Terminal app refused the command: {message}")
        duration = int((dt_util.utcnow() - started).total_seconds())
        stdout = str(data.get("stdout", ""))
        output_bytes = len(stdout.encode("utf-8"))
        digest = hashlib.sha256(stdout.encode("utf-8")).hexdigest()
        self._audit.async_log(
            AUDIT_CATEGORY_RUN,
            user_id=user_id,
            detail={
                "command": command,
                "exit_code": data.get("exit_code"),
                "bytes": output_bytes,
                "sha256": digest,
                "duration_seconds": duration,
            },
            flush=True,
        )
        return data

    async def async_transcript(self, *, user_id: str, session_id: str) -> dict[str, Any]:
        """GET a recorded transcript from the run/transcript listener, hash-verified."""
        host, secret = await self._target_host_and_secret()
        session = async_get_clientsession(self._hass)
        url = f"http://{host}:{TERMINAL_HTTPD_PORT}/cgi-bin/transcript"
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
                async with session.get(
                    url,
                    params={"id": session_id},
                    auth=aiohttp.BasicAuth(TTYD_USER, secret),
                ) as resp:
                    if resp.status == 404:
                        raise TerminalError(ERR_UNKNOWN_SESSION, "No such transcript")
                    if resp.status != 200:
                        raise TerminalError(ERR_CONNECT, f"Transcript request failed with HTTP {resp.status}")
                    text = await resp.text()
                    expected_sha256 = resp.headers.get("X-Sha256", "")
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise TerminalError(ERR_CONNECT, f"Could not reach the Terminal app at {host}: {err}") from err
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if expected_sha256 and not hmac.compare_digest(expected_sha256, digest):
            raise TerminalError(ERR_TRANSCRIPT_HASH_MISMATCH, "The transcript's hash did not match what the app recorded")
        byte_count = len(text.encode("utf-8"))
        self._audit.async_log(
            AUDIT_CATEGORY_EXPORT,
            user_id=user_id,
            detail={"kind": "download_transcript", "session_id": session_id, "bytes": byte_count, "sha256": digest},
            flush=True,
        )
        return {"session_id": session_id, "text": text, "sha256": digest, "bytes": byte_count}

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
        # ttyd checks the credential twice: HTTP basic auth on the upgrade,
        # and the same base64 "user:password" again as AuthToken in the
        # first message. An empty AuthToken is a policy-violation close
        # (1008) right after the handshake; verified against ttyd 1.7.7.
        token = base64.b64encode(f"{TTYD_USER}:{secret}".encode("utf-8")).decode("ascii")
        try:
            async with asyncio.timeout(CONNECT_TIMEOUT_SECONDS):
                ws = await session.ws_connect(
                    url,
                    protocols=("tty",),
                    headers={"Authorization": f"Basic {token}"},
                    heartbeat=30,
                )
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as err:
            raise TerminalError(ERR_CONNECT, f"Could not reach the Terminal app at {host}: {err}") from err
        await ws.send_str(json.dumps({"AuthToken": token, "columns": cols, "rows": rows}))
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

    async def async_close(
        self, session_id: str, user_id: str | None, reason: str = "user_closed", *, allow_any: bool = False
    ) -> None:
        """Close a session. ``allow_any`` lets the owner close someone else's
        session from the session list; every other caller is restricted to
        its own sessions (``user_id`` is None only for the internal
        unload/all-sessions path)."""
        session = self.sessions.get(session_id)
        if session is None:
            raise TerminalError(ERR_UNKNOWN_SESSION, "No such terminal session")
        if user_id is not None and session.user_id != user_id and not allow_any:
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
