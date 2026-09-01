"""Security and wire-format tests for SIEM Syslog export."""
from __future__ import annotations

import json

import pytest
import voluptuous as vol

from custom_components.ha_soc.syslog_export import format_rfc5424, frame_rfc6587
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
