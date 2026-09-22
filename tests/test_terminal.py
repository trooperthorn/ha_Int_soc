"""Tests for terminal.py and the ha_soc/terminal/* commands.

Nothing here opens a socket. The Supervisor is faked at the same two
boundaries the module uses (the cached add-on list and the info call), and
ttyd is a fake WebSocket that records what it was sent and can be fed frames.
What is pinned down: the pairing service trusts only the Supervisor caller
and pins the first secret, a session cannot open without the app installed,
running and paired, output and input cross as base64 with the ttyd command
byte, the per-user and per-install limits hold, and every open and close
leaves an audit record with byte counts.
"""
from __future__ import annotations

import asyncio
import base64
import json
from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.components.hassio.const import DATA_COMPONENT
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc import terminal as tm
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.secrets_store import TERMINAL_SECRET_KEY
from custom_components.ha_soc.websocket_api import (
    ws_terminal_app_control,
    ws_terminal_close,
    ws_terminal_export_event,
    ws_terminal_forget_pairing,
    ws_terminal_input,
    ws_terminal_open,
    ws_terminal_resize,
    ws_terminal_run,
    ws_terminal_status,
    ws_terminal_transcript,
)

HASSIO_USER_NAME = "Supervisor"
SECRET = "a" * 64
ADDONS = {"addons": [{"slug": "3fd1bd45_ha_soc_terminal", "name": "HA SOC Terminal", "state": "started", "version": "2026.09.10.5"}]}


class _FakeTtyd:
    """Stands in for aiohttp's ClientWebSocketResponse."""

    def __init__(self) -> None:
        self.sent: list[bytes | str] = []
        self.incoming: asyncio.Queue = asyncio.Queue()
        self.closed = False

    async def send_str(self, data: str) -> None:
        self.sent.append(data)

    async def send_bytes(self, data: bytes) -> None:
        self.sent.append(data)

    async def receive(self):
        return await self.incoming.get()

    async def close(self) -> None:
        self.closed = True
        await self.incoming.put(aiohttp.WSMessage(aiohttp.WSMsgType.CLOSED, None, None))

    def feed(self, data: bytes) -> None:
        self.incoming.put_nowait(aiohttp.WSMessage(aiohttp.WSMsgType.BINARY, data, None))


class _FakeHassio:
    def __init__(self, info: dict[str, Any] | None) -> None:
        self.info = info
        self.calls: list[str] = []

    async def send_command(self, path, method="get", timeout=None, **_):
        self.calls.append(path)
        return {"result": "ok", "data": self.info}


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> str:
    hass.config.config_dir = str(tmp_path)
    return str(tmp_path)


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])


@pytest.fixture
async def entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("custom_components.ha_soc.terminal.is_hassio", return_value=True),
        patch("custom_components.ha_soc.external_audit.is_hassio", return_value=True),
    ):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def app_running(hass: HomeAssistant, monkeypatch):
    """The app installed, started, and answering its info call."""
    hass.data[DATA_COMPONENT] = _FakeHassio(
        {"state": "started", "hostname": "3fd1bd45-ha-soc-terminal", "version": "2026.09.10.5", "options": {"session_recording": True}}
    )
    monkeypatch.setattr(tm, "_installed_addon", lambda _hass: dict(ADDONS["addons"][0]))
    monkeypatch.setattr(tm, "is_hassio", lambda _hass: True)
    return hass.data[DATA_COMPONENT]


@pytest.fixture
def fake_ttyd(monkeypatch):
    """Replace the one network call with a fake ttyd; records the handshake."""
    state: dict[str, Any] = {"ws": None, "connect_args": None, "raises": None}

    async def _connect(self, host, secret, cols, rows):
        if state["raises"] is not None:
            raise state["raises"]
        state["connect_args"] = (host, secret, cols, rows)
        ws = _FakeTtyd()
        token = base64.b64encode(f"hasoc:{secret}".encode()).decode()
        await ws.send_str(json.dumps({"AuthToken": token, "columns": cols, "rows": rows}))
        state["ws"] = ws
        return ws

    monkeypatch.setattr(tm.TerminalSessions, "_connect", _connect)
    return state


class _FakeHttpResponse:
    """Stands in for aiohttp's response, as an async context manager."""

    def __init__(self, *, status: int = 200, json_body: Any = None, text_body: str = "", headers: dict | None = None) -> None:
        self.status = status
        self._json_body = json_body
        self._text_body = text_body
        self.headers = headers or {}

    async def __aenter__(self) -> "_FakeHttpResponse":
        return self

    async def __aexit__(self, *exc_info) -> None:
        return None

    async def json(self, content_type=None) -> Any:
        return self._json_body

    async def text(self) -> str:
        return self._text_body


class _FakeHttpdSession:
    """Stands in for the aiohttp ClientSession the run/transcript calls use."""

    def __init__(self) -> None:
        self.post_response: _FakeHttpResponse | None = None
        self.get_response: _FakeHttpResponse | None = None
        self.post_calls: list[dict] = []
        self.get_calls: list[dict] = []
        self.raises: Exception | None = None

    def post(self, url, *, json, auth):
        if self.raises is not None:
            raise self.raises
        self.post_calls.append({"url": url, "json": json, "auth": auth})
        return self.post_response

    def get(self, url, *, params, auth):
        if self.raises is not None:
            raise self.raises
        self.get_calls.append({"url": url, "params": params, "auth": auth})
        return self.get_response


@pytest.fixture
def fake_httpd(monkeypatch):
    """Replace the run/transcript listener's HTTP calls with a fake session."""
    fake_session = _FakeHttpdSession()
    monkeypatch.setattr(tm, "async_get_clientsession", lambda _hass: fake_session)
    return fake_session


def _connection(user_id: str = "owner1", is_owner: bool = True, is_admin: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner, id=user_id)
    connection.subscriptions = {}
    return connection


async def _call(hass: HomeAssistant, handler, connection: MagicMock, msg: dict) -> MagicMock:
    connection.send_result.reset_mock()
    connection.send_error.reset_mock()
    handler(hass, connection, msg)
    for _ in range(300):
        await hass.async_block_till_done()
        if connection.send_result.called or connection.send_error.called:
            await hass.async_block_till_done()
            return connection
        await asyncio.sleep(0.01)
    raise AssertionError(f"no reply to {msg['type']}")


def _events(connection: MagicMock) -> list[dict]:
    return [
        call.args[0]["event"]
        for call in connection.send_message.call_args_list
        if isinstance(call.args[0], dict) and call.args[0].get("type") == "event"
    ]


async def _audit(hass: HomeAssistant, entry: MockConfigEntry, category: str) -> list[dict]:
    return await entry.runtime_data.audit.async_query(category=category, limit=50)


# --- pairing ---------------------------------------------------------------


async def test_pairing_pins_the_first_secret_and_refuses_a_different_one(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_user
) -> None:
    ctx = Context(user_id=supervisor_user.id)
    first = await hass.services.async_call(
        DOMAIN, "pair_terminal", {"secret": SECRET, "version": "x"}, blocking=True, context=ctx, return_response=True
    )
    assert first == {"accepted": True, "pinned": True}
    assert await entry.runtime_data.secrets.async_get(TERMINAL_SECRET_KEY) == SECRET

    again = await hass.services.async_call(
        DOMAIN, "pair_terminal", {"secret": SECRET}, blocking=True, context=ctx, return_response=True
    )
    assert again == {"accepted": True, "pinned": False}

    other = await hass.services.async_call(
        DOMAIN, "pair_terminal", {"secret": "b" * 64}, blocking=True, context=ctx, return_response=True
    )
    assert other["accepted"] is False and other["rejected"] == "secret_mismatch"
    assert await entry.runtime_data.secrets.async_get(TERMINAL_SECRET_KEY) == SECRET
    rejected = await _audit(hass, entry, tm.AUDIT_CATEGORY_PAIRING_REJECTED)
    assert rejected and rejected[0]["detail"]["reason"] == "secret_mismatch"


async def test_pairing_refuses_a_non_supervisor_caller(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    other = await hass.auth.async_create_user("Someone", group_ids=[GROUP_ID_ADMIN])
    result = await hass.services.async_call(
        DOMAIN, "pair_terminal", {"secret": SECRET}, blocking=True, context=Context(user_id=other.id), return_response=True
    )
    assert result["accepted"] is False and result["rejected"] == "not_supervisor"
    assert await entry.runtime_data.secrets.async_get(TERMINAL_SECRET_KEY) is None


# --- status and refusals ---------------------------------------------------


async def test_status_says_what_is_missing(hass: HomeAssistant, entry: MockConfigEntry, app_running) -> None:
    connection = await _call(hass, ws_terminal_status, _connection(), {"id": 1, "type": "ha_soc/terminal/status"})
    status = connection.send_result.call_args[0][1]
    assert status["installed"] is True and status["running"] is True
    assert status["paired"] is False
    assert status["recording"] is True
    assert status["targets"] == [{"id": "self", "label": "Terminal app shell", "available": False}]

    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = await _call(hass, ws_terminal_status, _connection(), {"id": 2, "type": "ha_soc/terminal/status"})
    assert connection.send_result.call_args[0][1]["targets"][0]["available"] is True


async def test_open_is_refused_until_the_app_is_paired(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    connection = await _call(hass, ws_terminal_open, _connection(), {"id": 1, "type": "ha_soc/terminal/open", "target": "self", "cols": 80, "rows": 24})
    assert connection.send_error.call_args[0][1] == tm.ERR_NOT_PAIRED
    assert fake_ttyd["ws"] is None


async def test_open_is_refused_for_an_unknown_target_and_a_stopped_app(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = await _call(hass, ws_terminal_open, _connection(), {"id": 1, "type": "ha_soc/terminal/open", "target": "core"})
    assert connection.send_error.call_args[0][1] == tm.ERR_UNKNOWN_TARGET

    app_running.info = {"state": "stopped", "hostname": "x"}
    connection = await _call(hass, ws_terminal_open, _connection(), {"id": 2, "type": "ha_soc/terminal/open"})
    assert connection.send_error.call_args[0][1] == tm.ERR_NOT_RUNNING


async def test_every_terminal_command_respects_the_tier(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Default access is owner-only; a plain admin is refused on each command."""
    admin = _connection(user_id="admin1", is_owner=False)
    for handler, msg in (
        (ws_terminal_status, {"type": "ha_soc/terminal/status"}),
        (ws_terminal_open, {"type": "ha_soc/terminal/open"}),
        (ws_terminal_input, {"type": "ha_soc/terminal/input", "session_id": "x", "data": "AA=="}),
        (ws_terminal_resize, {"type": "ha_soc/terminal/resize", "session_id": "x", "cols": 80, "rows": 24}),
        (ws_terminal_close, {"type": "ha_soc/terminal/close", "session_id": "x"}),
        (ws_terminal_run, {"type": "ha_soc/terminal/run", "command": "echo hi"}),
        (ws_terminal_transcript, {"type": "ha_soc/terminal/transcript", "session_id": "x"}),
        (ws_terminal_app_control, {"type": "ha_soc/terminal/app_control", "action": "start"}),
        (ws_terminal_forget_pairing, {"type": "ha_soc/terminal/forget_pairing"}),
        (
            ws_terminal_export_event,
            {"type": "ha_soc/terminal/export_event", "kind": "copy_screen", "lines": 1, "bytes": 1, "sha256": "a" * 64},
        ),
    ):
        with pytest.raises(Unauthorized):
            handler(hass, admin, {"id": 1, **msg})


# --- a session -------------------------------------------------------------


async def _open(hass: HomeAssistant, connection: MagicMock, msg_id: int = 1) -> dict:
    await _call(hass, ws_terminal_open, connection, {"id": msg_id, "type": "ha_soc/terminal/open", "target": "self", "cols": 100, "rows": 30})
    assert not connection.send_error.called, connection.send_error.call_args
    return connection.send_result.call_args[0][1]


async def test_a_session_relays_bytes_both_ways_and_is_audited(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = _connection()
    opened = await _open(hass, connection)
    session_id = opened["session_id"]
    assert opened["host"] == "3fd1bd45-ha-soc-terminal"
    assert fake_ttyd["connect_args"] == ("3fd1bd45-ha-soc-terminal", SECRET, 100, 30)
    # The handshake carried the size; the "opened" event repeats the result.
    assert json.loads(fake_ttyd["ws"].sent[0]) == {
        "AuthToken": base64.b64encode(f"hasoc:{SECRET}".encode()).decode(),
        "columns": 100,
        "rows": 30,
    }
    assert _events(connection)[0]["kind"] == "opened"
    assert _events(connection)[0]["session_id"] == session_id
    assert 1 in connection.subscriptions

    # Output from ttyd: command byte '0' then bytes, delivered as base64.
    fake_ttyd["ws"].feed(b"0hello\x1b[31m!\x1b[0m")
    await asyncio.sleep(0.05)
    await hass.async_block_till_done()
    outputs = [e for e in _events(connection) if e["kind"] == "output"]
    assert base64.b64decode(outputs[-1]["data"]) == b"hello\x1b[31m!\x1b[0m"

    # Input from the panel: base64 in, '0' plus bytes to ttyd.
    await _call(hass, ws_terminal_input, connection, {"id": 2, "type": "ha_soc/terminal/input", "session_id": session_id, "data": base64.b64encode(b"ls\r").decode()})
    assert fake_ttyd["ws"].sent[-1] == b"0ls\r"
    await _call(hass, ws_terminal_resize, connection, {"id": 3, "type": "ha_soc/terminal/resize", "session_id": session_id, "cols": 120, "rows": 40})
    assert fake_ttyd["ws"].sent[-1] == b'1{"columns": 120, "rows": 40}'

    # Another user cannot drive this session.
    stranger = _connection(user_id="owner2")
    await _call(hass, ws_terminal_input, stranger, {"id": 4, "type": "ha_soc/terminal/input", "session_id": session_id, "data": "AA=="})
    assert stranger.send_error.call_args[0][1] == tm.ERR_UNKNOWN_SESSION

    await _call(hass, ws_terminal_close, connection, {"id": 5, "type": "ha_soc/terminal/close", "session_id": session_id})
    assert connection.send_result.call_args[0][1] == {"closed": True}
    await hass.async_block_till_done()
    assert fake_ttyd["ws"].closed is True
    assert entry.runtime_data.terminal.sessions == {}
    closed = [e for e in _events(connection) if e["kind"] == "closed"]
    assert closed and closed[0]["reason"] == "user_closed"

    opens = await _audit(hass, entry, tm.AUDIT_CATEGORY_OPEN)
    closes = await _audit(hass, entry, tm.AUDIT_CATEGORY_CLOSE)
    assert opens[0]["detail"]["session_id"] == session_id
    assert closes[0]["detail"]["bytes_in"] == 3
    assert closes[0]["detail"]["bytes_out"] == len(b"hello\x1b[31m!\x1b[0m")
    assert closes[0]["detail"]["reason"] == "user_closed"


async def test_ttyd_going_away_closes_the_session(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = _connection()
    opened = await _open(hass, connection)
    await fake_ttyd["ws"].close()
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not entry.runtime_data.terminal.sessions:
            break
    assert entry.runtime_data.terminal.sessions == {}
    closes = await _audit(hass, entry, tm.AUDIT_CATEGORY_CLOSE)
    assert closes[0]["detail"]["session_id"] == opened["session_id"]
    assert closes[0]["detail"]["reason"] == "remote_closed"


async def test_the_browser_going_away_closes_the_session(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = _connection()
    opened = await _open(hass, connection)
    connection.subscriptions[1]()
    await hass.async_block_till_done()
    for _ in range(50):
        await asyncio.sleep(0.01)
        if not entry.runtime_data.terminal.sessions:
            break
    assert entry.runtime_data.terminal.sessions == {}
    closes = await _audit(hass, entry, tm.AUDIT_CATEGORY_CLOSE)
    assert closes[0]["detail"]["session_id"] == opened["session_id"]
    assert closes[0]["detail"]["reason"] == "connection_lost"


async def test_session_limits(hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd, monkeypatch) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    owner = _connection()
    await _open(hass, owner)
    again = await _call(hass, ws_terminal_open, owner, {"id": 9, "type": "ha_soc/terminal/open"})
    assert again.send_error.call_args[0][1] == tm.ERR_LIMIT_USER

    monkeypatch.setattr(tm, "MAX_SESSIONS_TOTAL", 1)
    other = await _call(hass, ws_terminal_open, _connection(user_id="owner2"), {"id": 10, "type": "ha_soc/terminal/open"})
    assert other.send_error.call_args[0][1] == tm.ERR_LIMIT_TOTAL


async def test_connect_failure_is_a_coded_refusal_with_no_session(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    fake_ttyd["raises"] = tm.TerminalError(tm.ERR_CONNECT, "no route")
    connection = await _call(hass, ws_terminal_open, _connection(), {"id": 1, "type": "ha_soc/terminal/open"})
    assert connection.send_error.call_args[0][1] == tm.ERR_CONNECT
    assert entry.runtime_data.terminal.sessions == {}
    assert not await _audit(hass, entry, tm.AUDIT_CATEGORY_OPEN)


# --- app control, forget pairing, owner-any close --------------------------


async def test_app_control_start_and_restart_call_the_supervisor_client(
    hass: HomeAssistant, entry: MockConfigEntry, app_running
) -> None:
    client = MagicMock()
    client.addons.start_addon = MagicMock(return_value=asyncio.sleep(0))
    client.addons.restart_addon = MagicMock(return_value=asyncio.sleep(0))
    with patch("homeassistant.components.hassio.get_supervisor_client", return_value=client):
        connection = await _call(
            hass, ws_terminal_app_control, _connection(), {"id": 1, "type": "ha_soc/terminal/app_control", "action": "start"}
        )
        assert connection.send_result.call_args[0][1] == {"ok": True}
        client.addons.start_addon.assert_called_once_with(ADDONS["addons"][0]["slug"])

        connection = await _call(
            hass, ws_terminal_app_control, _connection(), {"id": 2, "type": "ha_soc/terminal/app_control", "action": "restart"}
        )
        assert connection.send_result.call_args[0][1] == {"ok": True}
        client.addons.restart_addon.assert_called_once_with(ADDONS["addons"][0]["slug"])

    logged = await _audit(hass, entry, tm.AUDIT_CATEGORY_APP_CONTROL)
    assert {d["detail"]["action"] for d in logged} == {"start", "restart"}


async def test_app_control_refuses_when_not_installed(hass: HomeAssistant, entry: MockConfigEntry, monkeypatch) -> None:
    monkeypatch.setattr(tm, "is_hassio", lambda _hass: True)
    connection = await _call(
        hass, ws_terminal_app_control, _connection(), {"id": 1, "type": "ha_soc/terminal/app_control", "action": "start"}
    )
    assert connection.send_result.call_args[0][1] == {"ok": False, "reason": tm.ERR_NOT_INSTALLED}


async def test_forget_pairing_clears_the_secret_and_is_audited(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = await _call(hass, ws_terminal_forget_pairing, _connection(), {"id": 1, "type": "ha_soc/terminal/forget_pairing"})
    assert connection.send_result.call_args[0][1] == {"ok": True}
    assert await entry.runtime_data.secrets.async_get(TERMINAL_SECRET_KEY) is None
    logged = await _audit(hass, entry, tm.AUDIT_CATEGORY_FORGET_PAIRING)
    assert logged


async def test_owner_can_close_another_users_session_but_a_stranger_cannot(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd
) -> None:
    from custom_components.ha_soc.const import ACCESS_LEVEL_OWNER_AND_ADMINS

    entry.runtime_data.store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_AND_ADMINS)
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    owner = _connection(user_id="owner1", is_owner=True)
    opened = await _open(hass, owner)
    session_id = opened["session_id"]

    # A non-owner with soc access may close only their own session.
    stranger = _connection(user_id="someone_else", is_owner=False)
    refused = await _call(hass, ws_terminal_close, stranger, {"id": 9, "type": "ha_soc/terminal/close", "session_id": session_id})
    assert refused.send_error.call_args[0][1] == tm.ERR_UNKNOWN_SESSION

    second_owner = _connection(user_id="owner2", is_owner=True)
    closed = await _call(hass, ws_terminal_close, second_owner, {"id": 10, "type": "ha_soc/terminal/close", "session_id": session_id})
    assert closed.send_result.call_args[0][1] == {"closed": True}
    await hass.async_block_till_done()
    assert entry.runtime_data.terminal.sessions == {}
    closes = await _audit(hass, entry, tm.AUDIT_CATEGORY_CLOSE)
    assert closes[0]["detail"]["reason"] == "owner_closed"


async def test_export_event_is_audited_with_its_fields(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = await _call(
        hass,
        ws_terminal_export_event,
        _connection(),
        {
            "id": 1,
            "type": "ha_soc/terminal/export_event",
            "kind": "download_all",
            "session_id": "abc123",
            "lines": 42,
            "bytes": 1024,
            "sha256": "b" * 64,
        },
    )
    assert connection.send_result.call_args[0][1] == {"ok": True}
    logged = await _audit(hass, entry, tm.AUDIT_CATEGORY_EXPORT)
    assert logged[0]["detail"] == {
        "kind": "download_all",
        "session_id": "abc123",
        "lines": 42,
        "bytes": 1024,
        "sha256": "b" * 64,
    }


async def test_unload_closes_open_sessions(hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_ttyd) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    connection = _connection()
    await _open(hass, connection)
    sessions = entry.runtime_data.terminal
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert sessions.sessions == {}
    assert fake_ttyd["ws"].closed is True


# --- run and transcript (the one-shot listener) -----------------------------


async def test_run_happy_path_is_audited(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_httpd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    fake_httpd.post_response = _FakeHttpResponse(
        json_body={"id": "run1", "stdout": "hello\n", "exit_code": 0, "duration_seconds": 0, "truncated": False}
    )
    connection = await _call(
        hass, ws_terminal_run, _connection(), {"id": 1, "type": "ha_soc/terminal/run", "command": "echo hello", "timeout_seconds": 30}
    )
    result = connection.send_result.call_args[0][1]
    assert result["stdout"] == "hello\n" and result["exit_code"] == 0
    assert fake_httpd.post_calls[0]["json"] == {"command": "echo hello", "timeout_seconds": 30}
    assert fake_httpd.post_calls[0]["auth"].login == tm.TTYD_USER
    assert fake_httpd.post_calls[0]["auth"].password == SECRET

    logged = await _audit(hass, entry, tm.AUDIT_CATEGORY_RUN)
    assert logged[0]["detail"]["command"] == "echo hello"
    assert logged[0]["detail"]["exit_code"] == 0
    assert logged[0]["detail"]["bytes"] == len("hello\n".encode())
    import hashlib

    assert logged[0]["detail"]["sha256"] == hashlib.sha256(b"hello\n").hexdigest()
    assert "duration_seconds" in logged[0]["detail"]


async def test_run_respects_the_tier(hass: HomeAssistant) -> None:
    admin = _connection(user_id="admin1", is_owner=False)
    with pytest.raises(Unauthorized):
        ws_terminal_run(hass, admin, {"id": 1, "type": "ha_soc/terminal/run", "command": "echo hi"})


async def test_run_refuses_a_second_concurrent_run_for_the_same_user(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_httpd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    fake_httpd.post_response = _FakeHttpResponse(
        json_body={"id": "run1", "stdout": "", "exit_code": 0, "duration_seconds": 0, "truncated": False}
    )
    connection = _connection()
    entry.runtime_data.terminal._running_users.add(connection.user.id)
    await _call(
        hass,
        ws_terminal_run,
        connection,
        {"id": 1, "type": "ha_soc/terminal/run", "command": "echo hi", "timeout_seconds": 30},
    )
    assert connection.send_error.call_args[0][1] == tm.ERR_TERMINAL_BUSY


async def test_transcript_ok_verifies_the_hash_and_is_audited(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_httpd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    import hashlib

    text = "line one\nline two\n"
    digest = hashlib.sha256(text.encode()).hexdigest()
    fake_httpd.get_response = _FakeHttpResponse(status=200, text_body=text, headers={"X-Sha256": digest})
    connection = await _call(
        hass, ws_terminal_transcript, _connection(), {"id": 1, "type": "ha_soc/terminal/transcript", "session_id": "abc123"}
    )
    result = connection.send_result.call_args[0][1]
    assert result == {"session_id": "abc123", "text": text, "sha256": digest, "bytes": len(text.encode())}
    logged = await _audit(hass, entry, tm.AUDIT_CATEGORY_EXPORT)
    assert logged[0]["detail"] == {
        "kind": "download_transcript",
        "session_id": "abc123",
        "bytes": len(text.encode()),
        "sha256": digest,
    }


async def test_transcript_hash_mismatch_is_refused(
    hass: HomeAssistant, entry: MockConfigEntry, app_running, fake_httpd
) -> None:
    await entry.runtime_data.secrets.async_set(TERMINAL_SECRET_KEY, SECRET)
    fake_httpd.get_response = _FakeHttpResponse(status=200, text_body="tampered", headers={"X-Sha256": "0" * 64})
    connection = await _call(
        hass, ws_terminal_transcript, _connection(), {"id": 1, "type": "ha_soc/terminal/transcript", "session_id": "abc123"}
    )
    assert connection.send_error.call_args[0][1] == tm.ERR_TRANSCRIPT_HASH_MISMATCH


def test_transcript_rejects_a_bad_id_at_the_schema() -> None:
    with pytest.raises(vol.Invalid):
        ws_terminal_transcript._ws_schema(
            {"id": 1, "type": "ha_soc/terminal/transcript", "session_id": "../etc/passwd"}
        )

