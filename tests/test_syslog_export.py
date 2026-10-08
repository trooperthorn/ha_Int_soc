"""Security and wire-format tests for SIEM Syslog export."""
from __future__ import annotations

import json
import ssl
from types import SimpleNamespace

import pytest
import voluptuous as vol

from custom_components.ha_soc.const import (
    SYSLOG_FORMAT_CEF,
    SYSLOG_FORMAT_RAW_JSON,
    SYSLOG_FORMAT_RFC5424_JSON,
    SYSLOG_TRANSPORT_UDP,
)
from custom_components.ha_soc.store import default_store_data
from custom_components.ha_soc.syslog_export import (
    format_cef_payload,
    format_raw_json,
    format_rfc5424,
    format_rfc5424_cef,
    format_syslog_message,
    frame_rfc6587,
    SyslogExporter,
)
from custom_components.ha_soc.websocket_api import _syslog_host


def _record() -> dict:
    return {
        "ts": "2026-09-01T12:00:00+00:00",
        "seq": 42,
        "hash": "a" * 64,
        "prev_hash": "b" * 64,
        "category": "login_fail",
        "user_id": None,
        "domain": None,
        "service": None,
        "entity_ids": [],
        "context_id": None,
        "context_parent_id": None,
        "ip": "192.0.2.4",
        "attempted_user": "admin\nforged-header",
        "detail": {"password": "[redacted]"},
    }


def test_rfc5424_contains_chain_evidence_and_valid_json() -> None:
    message = format_rfc5424(_record(), 16)
    text = message.decode()
    assert text.startswith("<132>1 2026-09-01T12:00:00+00:00 homeassistant ha-soc - login_fail ")
    assert 'seq="42"' in text
    assert f'hash="{"a" * 64}"' in text
    payload = json.loads(text[text.index("{") :])
    assert payload["attempted_user"] == "admin\nforged-header"
    assert "\nforged-header" not in text.split(" {", 1)[0]


def test_tcp_and_tls_use_rfc6587_octet_counting() -> None:
    message = format_rfc5424(_record(), 16)
    framed = frame_rfc6587(message)
    count, payload = framed.split(b" ", 1)
    assert int(count) == len(message)
    assert payload == message


def test_oversized_detail_is_replaced_not_byte_truncated() -> None:
    record = _record()
    record["detail"] = {"blob": "x" * 100_000}
    text = format_rfc5424(record, 16).decode()
    payload = json.loads(text[text.index("{") :])
    assert payload["seq"] == 42
    assert payload["detail"]["truncated"] is True
    assert len(text.encode()) <= 32 * 1024


def test_existing_entries_default_to_rfc5424_json() -> None:
    settings = default_store_data()["settings"]
    assert settings["syslog_format"] == SYSLOG_FORMAT_RFC5424_JSON


def test_cef_has_stable_identity_severity_and_chain_evidence() -> None:
    message = format_rfc5424_cef(_record(), 16, "2026.08.31.2")
    text = message.decode()
    cef = text[text.index("CEF:0|") :]
    assert cef.startswith(
        "CEF:0|Home Assistant|HA SOC|2026.08.31.2|"
        "ha_soc.login_fail|Failed Login|7|"
    )
    assert "rt=1788264000000" in cef
    assert "start=1788264000000" in cef
    assert "cat=login_fail" in cef
    assert "outcome=failure" in cef
    assert "src=192.0.2.4" in cef
    assert "duser=admin\\nforged-header" in cef
    assert "cn1Label=Audit Sequence cn1=42" in cef
    assert f"cs1Label=Audit Hash cs1={'a' * 64}" in cef
    assert f"cs2Label=Previous Audit Hash cs2={'b' * 64}" in cef
    assert 'seq="42"' in text[: text.index("CEF:0|")]
    assert "\n" not in cef


def test_cef_context_specific_escaping_prevents_field_injection() -> None:
    record = _record()
    record["detail"] = {"note": "x=y\\z\nforgedKey=value"}
    payload = format_cef_payload(record, "2026|x\\y\nz")
    assert payload.startswith(
        "CEF:0|Home Assistant|HA SOC|2026\\|x\\\\y\\nz|"
    )
    assert "duser=admin\\nforged-header" in payload
    assert "x\\=y" in payload
    assert "forgedKey\\=value" in payload
    assert "\n" not in payload


def test_cef_unknown_category_is_safely_preserved() -> None:
    record = _record()
    record["category"] = "future|category\nname"
    payload = format_cef_payload(record, "1")
    assert "|ha_soc.future_category_name|Future Category Name|4|" in payload
    assert "cat=future|category\\nname" in payload


@pytest.mark.parametrize(
    ("category", "severity"),
    [
        ("audit_chain_reset", "10"),
        ("probe_auth_rejected", "9"),
        ("login_fail", "7"),
        ("user_removed", "7"),
        ("soc_config_change", "5"),
        ("watchdog_triggered", "5"),
        ("login_ok", "3"),
        ("service_call", "3"),
        ("future_category", "4"),
    ],
)
def test_cef_severity_policy(category: str, severity: str) -> None:
    record = _record()
    record["category"] = category
    payload = format_cef_payload(record, "1")
    assert payload.split("|", 7)[6] == severity


def test_cef_maps_ipv6_without_misusing_cef_zero_src() -> None:
    record = _record()
    record["ip"] = "2001:db8::20"
    payload = format_cef_payload(record, "1")
    assert " c6a1Label=Source IPv6 c6a1=2001:db8::20 " in payload
    assert " src=" not in payload


def test_cef_omits_invalid_ip() -> None:
    record = _record()
    record["ip"] = "not-an-ip"
    payload = format_cef_payload(record, "1")
    assert " src=" not in payload
    assert " c6a1=" not in payload


def test_cef_maps_actor_and_target_user_ids_without_conflating_names() -> None:
    record = _record()
    record["category"] = "user_updated"
    record["user_id"] = "acting-admin-id"
    record["attempted_user"] = None
    record["detail"] = {
        "target_user_id": "target-user-id",
        "target_name": "Target User",
    }
    payload = format_cef_payload(record, "1")
    assert " suid=acting-admin-id " in payload
    assert " duid=target-user-id " in payload
    assert " duser=Target User " in payload


def test_oversized_cef_detail_is_structurally_truncated() -> None:
    record = _record()
    record["detail"] = {"blob": "x" * 100_000}
    message = format_rfc5424_cef(record, 16, "1")
    text = message.decode()
    assert len(message) <= 32 * 1024
    assert "msg={\"original_characters\":" in text
    assert ",\"truncated\":true}" in text
    assert f"cs1={'a' * 64}" in text
    assert f"cs2={'b' * 64}" in text


def test_raw_json_is_canonical_and_has_no_syslog_envelope() -> None:
    message = format_raw_json(_record())
    assert not message.startswith(b"<")
    payload = json.loads(message)
    assert payload["seq"] == 42
    assert payload["hash"] == "a" * 64
    assert payload["prev_hash"] == "b" * 64


@pytest.mark.parametrize(
    ("payload_format", "prefix"),
    [
        (SYSLOG_FORMAT_RFC5424_JSON, b"<132>1 "),
        (SYSLOG_FORMAT_CEF, b"<132>1 "),
        (SYSLOG_FORMAT_RAW_JSON, b"{"),
    ],
)
def test_format_selector_dispatches_without_changing_transport_framing(
    payload_format: str, prefix: bytes
) -> None:
    message = format_syslog_message(_record(), 16, payload_format, "1")
    assert message.startswith(prefix)
    framed = frame_rfc6587(message)
    count, payload = framed.split(b" ", 1)
    assert int(count) == len(message)
    assert payload == message


def test_queue_snapshots_selected_format_before_reconfiguration() -> None:
    settings = {
        "syslog_transport": SYSLOG_TRANSPORT_UDP,
        "syslog_host": "192.0.2.20",
        "syslog_format": SYSLOG_FORMAT_CEF,
    }
    exporter = SyslogExporter(None, SimpleNamespace(settings=settings), "1")  # type: ignore[arg-type]
    exporter.async_enqueue([_record()])
    settings["syslog_format"] = SYSLOG_FORMAT_RAW_JSON

    queued = exporter._queue.get_nowait()  # noqa: SLF001 - queue contract test
    assert queued["payload_format"] == SYSLOG_FORMAT_CEF


@pytest.mark.parametrize("host", ["sem.example.lan", "192.0.2.20", "2001:db8::20"])
def test_syslog_destination_accepts_only_host_literals(host: str) -> None:
    assert _syslog_host(host) == host


@pytest.mark.parametrize(
    "host",
    ["https://sem.example.lan", "sem.example.lan/path", "user@sem", "bad host"],
)
def test_syslog_destination_rejects_urls_paths_and_userinfo(host: str) -> None:
    with pytest.raises(vol.Invalid):
        _syslog_host(host)


async def test_tls_reconnect_builds_the_ssl_context_once_in_the_executor(hass) -> None:
    """Building a TLS context loads the CA bundle from disk, which must never
    happen on the event loop, and a reconnect must reuse the built context."""
    import threading
    from unittest.mock import AsyncMock, MagicMock, patch

    import ssl as ssl_module

    from custom_components.ha_soc import syslog_export

    loop_thread = threading.get_ident()
    build_threads: list[int] = []
    real_create = ssl_module.create_default_context

    def recording_create(*args, **kwargs):
        build_threads.append(threading.get_ident())
        return real_create(*args, **kwargs)

    settings = {
        "syslog_transport": "tls",
        "syslog_host": "sem.example.lan",
        "syslog_port": 6514,
        "syslog_tls_verify": True,
    }
    exporter = SyslogExporter(hass, SimpleNamespace(settings=settings), "1")
    opened: list[dict] = []

    async def fake_open_connection(host, port, **kwargs):
        opened.append(kwargs)
        writer = MagicMock()
        writer.drain = AsyncMock()
        return MagicMock(), writer

    item = {"record": _record(), "payload_format": "rfc5424"}
    with (
        patch.object(syslog_export.ssl, "create_default_context", recording_create),
        patch.object(syslog_export.asyncio, "open_connection", fake_open_connection),
    ):
        await exporter._async_send(item)  # noqa: SLF001
        exporter._writer = None  # noqa: SLF001 - simulate a dropped connection
        await exporter._async_send(item)  # noqa: SLF001

    assert len(build_threads) == 1
    assert build_threads[0] != loop_thread
    assert len(opened) == 2
    assert opened[0]["ssl"] is opened[1]["ssl"]
    assert opened[0]["server_hostname"] == "sem.example.lan"


async def test_tls_reconnect_triggers_no_blocking_call_detection(hass, monkeypatch) -> None:
    """Home Assistant's own detector, made strict, must stay silent while the
    exporter connects, drops and reconnects over TLS.

    The harness leaves the SSL entries of ``block_async_io`` switched off, so
    the test installs the same ``protect_loop`` wrapper on them itself, in
    strict mode, and builds the real context rather than a recorded one.
    """
    import threading
    from unittest.mock import AsyncMock, MagicMock, patch

    from homeassistant.block_async_io import _BLOCKING_CALLS
    from homeassistant.util.loop import protect_loop

    from custom_components.ha_soc import syslog_export

    loop_thread_id = threading.get_ident()
    protected = 0
    for call in _BLOCKING_CALLS:
        if call.object is ssl.SSLContext:
            monkeypatch.setattr(
                call.object,
                call.function,
                protect_loop(
                    call.original_func,
                    loop_thread_id=loop_thread_id,
                    strict=True,
                    strict_core=True,
                    check_allowed=call.check_allowed,
                ),
            )
            protected += 1
    assert protected >= 3

    settings = {
        "syslog_transport": "tls",
        "syslog_host": "sem.example.lan",
        "syslog_port": 6514,
        "syslog_tls_verify": True,
    }
    exporter = SyslogExporter(hass, SimpleNamespace(settings=settings), "1")
    opened: list[dict] = []

    async def fake_open_connection(host, port, **kwargs):
        opened.append(kwargs)
        writer = MagicMock()
        writer.drain = AsyncMock()
        return MagicMock(), writer

    item = {"record": _record(), "payload_format": "rfc5424"}
    with patch.object(syslog_export.asyncio, "open_connection", fake_open_connection):
        await exporter._async_send(item)  # noqa: SLF001
        exporter._writer = None  # noqa: SLF001 - simulate a dropped connection
        await exporter._async_send(item)  # noqa: SLF001

    assert len(opened) == 2
    assert isinstance(opened[0]["ssl"], ssl.SSLContext)


async def test_tls_unverified_context_is_built_off_the_loop_and_cached(hass) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from custom_components.ha_soc import syslog_export

    settings = {
        "syslog_transport": "tls",
        "syslog_host": "sem.example.lan",
        "syslog_tls_verify": False,
    }
    exporter = SyslogExporter(hass, SimpleNamespace(settings=settings), "1")
    seen: list[dict] = []

    async def fake_open_connection(host, port, **kwargs):
        seen.append(kwargs)
        writer = MagicMock()
        writer.drain = AsyncMock()
        return MagicMock(), writer

    with patch.object(syslog_export.asyncio, "open_connection", fake_open_connection):
        await exporter._async_send({"record": _record(), "payload_format": "rfc5424"})  # noqa: SLF001
    assert seen[0]["server_hostname"] is None
    assert seen[0]["ssl"].check_hostname is False
    assert exporter._ssl_contexts[False] is seen[0]["ssl"]  # noqa: SLF001
