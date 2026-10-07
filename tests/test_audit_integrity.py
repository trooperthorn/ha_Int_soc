"""The audit log keeps every record and an unbroken hash chain through faults."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging
import os
from typing import Any
from unittest.mock import patch

import pytest

from custom_components.ha_soc import atomic_json
from custom_components.ha_soc.audit import AuditLog, _is_secret_key
from custom_components.ha_soc.store import HaSocData

ISOLATED_CONFIG_DIR = True


async def _make_audit(hass, tmp_path) -> AuditLog:
    store = HaSocData(hass)
    await store.async_load()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    audit._head_loaded = True
    os.makedirs(audit._dir_path, exist_ok=True)
    return audit


def _records_on_disk(audit: AuditLog) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for name in sorted(os.listdir(audit._dir_path)):
        if name.startswith("audit-"):
            with open(os.path.join(audit._dir_path, name), encoding="utf-8") as handle:
                out.extend(json.loads(line) for line in handle)
    return out


def _log(audit: AuditLog, i: int) -> None:
    audit.async_log(
        "service_call", domain="light", service="turn_on", detail={"i": i}
    )


def _mirror_seq(audit: AuditLog) -> int:
    return audit._store.data["audit_head"]["seq"]


async def test_nonserializable_detail_is_coerced_and_chain_verifies(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for i in range(3):
        _log(audit, i)
    audit.async_log(
        "service_call",
        domain="calendar",
        service="create_event",
        detail={
            "start": dt.datetime(2026, 10, 7, 12, 0),
            "dur": dt.timedelta(minutes=5),
            "tags": {"b", "a"},
            "nested": {1: object, "when": dt.date(2026, 10, 7)},
        },
    )
    _log(audit, 4)
    await audit._async_flush()
    _log(audit, 5)
    await audit._async_flush()

    records = _records_on_disk(audit)
    assert [r["seq"] for r in records] == [1, 2, 3, 4, 5, 6]
    event = records[3]["detail"]
    assert event["start"] == "2026-10-07T12:00:00"
    assert event["dur"] == "0:05:00"
    assert event["tags"] == ["a", "b"]
    assert event["nested"]["when"] == "2026-10-07"
    assert not audit._buffer
    assert (await audit.async_verify_chain())["ok"] is True


async def test_failed_flush_keeps_records_buffered_without_chain_gap(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for i in range(3):
        _log(audit, i)
    await audit._async_flush()
    for i in range(3, 6):
        _log(audit, i)

    real_open = os.open
    calls = {"n": 0}

    def flaky(path, *args, **kwargs):
        if str(path).endswith(".jsonl") and calls["n"] == 0:
            calls["n"] += 1
            raise OSError(28, "No space left on device")
        return real_open(path, *args, **kwargs)

    with patch("custom_components.ha_soc.audit.os.open", flaky):
        await audit._async_flush()

    assert len(audit._buffer) == 3
    assert audit._seq == 3
    assert _mirror_seq(audit) == 3

    _log(audit, 6)
    await audit._async_flush()

    records = _records_on_disk(audit)
    assert [r["seq"] for r in records] == [1, 2, 3, 4, 5, 6, 7]
    assert [r["detail"]["i"] for r in records] == [0, 1, 2, 3, 4, 5, 6]
    assert not audit._buffer
    assert _mirror_seq(audit) == 7
    assert (await audit.async_verify_chain())["ok"] is True


async def test_partial_write_is_trimmed_and_not_duplicated(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for i in range(3):
        _log(audit, i)

    real_write = os.write
    calls = {"n": 0}

    def short_then_fail(fd, data):
        calls["n"] += 1
        if calls["n"] == 1:
            real_write(fd, bytes(data[:20]))
            raise OSError(28, "No space left on device")
        return real_write(fd, data)

    with patch("custom_components.ha_soc.audit.os.write", short_then_fail):
        await audit._async_flush()
    assert len(audit._buffer) == 3
    assert _records_on_disk(audit) == []

    await audit._async_flush()
    assert [r["seq"] for r in _records_on_disk(audit)] == [1, 2, 3]
    assert (await audit.async_verify_chain())["ok"] is True


async def test_retention_failure_does_not_requeue_written_records(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for i in range(2):
        _log(audit, i)
    with patch.object(audit, "_sync_apply_retention", side_effect=OSError("boom")):
        await audit._async_flush()
    assert not audit._buffer
    assert [r["seq"] for r in _records_on_disk(audit)] == [1, 2]


async def test_audit_writes_are_fsynced(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    _log(audit, 0)
    with patch("custom_components.ha_soc.audit.os.fsync") as fsync:
        await audit._async_flush()
    # One for the day file and one for the chain head.
    assert fsync.call_count >= 2


async def test_syslog_receives_only_written_redacted_records(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    sent: list[dict[str, Any]] = []

    class _Exporter:
        def async_enqueue(self, records):
            sent.extend(records)

    audit.async_set_syslog_exporter(_Exporter())
    audit.async_log(
        "service_call",
        domain="lock",
        service="set_usercode",
        detail={"usercode": "482913"},
    )
    with patch(
        "custom_components.ha_soc.audit.os.open", side_effect=OSError(5, "io")
    ):
        await audit._async_flush()
    assert sent == []
    await audit._async_flush()
    assert len(sent) == 1
    assert "482913" not in json.dumps(sent)


@pytest.mark.parametrize(
    "key",
    [
        "password",
        "wifi_password",
        "passwd",
        "pass",
        "token",
        "bearer_token",
        "accessToken",
        "api_key",
        "api-key",
        "apiKey",
        "private_key",
        "secret",
        "client_secret",
        "pin",
        "pin_code",
        "code",
        "usercode",
        "user_code",
        "access_code",
        "psk",
        "credential",
        "key",
    ],
)
def test_credential_like_keys_are_secret(key):
    assert _is_secret_key(key)


@pytest.mark.parametrize(
    "key",
    [
        "token_id",
        "code_slot",
        "status_code",
        "entity_id",
        "brightness",
        "key_type",
        "pin_count",
    ],
)
def test_ordinary_keys_stay_visible(key):
    assert not _is_secret_key(key)


def _flatten(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _flatten(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten(item)
    else:
        yield value


async def test_pattern_redaction_in_written_audit_log(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    payloads = {
        "zwave_js.set_lock_usercode": {"code_slot": 3, "usercode": "482913"},
        "esphome.x_set_wifi": {"wifi_password": "hunter2hunter2"},
        "rest_command.x": {"bearer_token": "abc123token", "api-key": "k-api"},
        "elkm1.alarm_arm_home": {"code": "pin-7391"},
        "shell_command.deploy": {"private_key": "BEGIN-KEY", "psk": "wpa-psk"},
        "tuya.login": {"passwd": "pass1", "pass": "pass2", "credential": "cred-val-88"},
        "esphome.nested": {"outer": [{"Api_Key": "deep-secret"}]},
    }
    for name, data in payloads.items():
        domain, service = name.split(".", 1)
        audit.async_log(
            "service_call", domain=domain, service=service, detail=dict(data)
        )
    await audit._async_flush()
    text = json.dumps(_records_on_disk(audit))
    for data in payloads.values():
        for value in _flatten(data):
            if isinstance(value, str):
                assert value not in text
    # Non-secret neighbours remain readable.
    assert '"code_slot": 3' in text


def test_durable_json_write_fsyncs_file_and_directory(tmp_path):
    path = str(tmp_path / "state" / "heartbeat.json")
    with patch.object(atomic_json.os, "fsync") as fsync:
        atomic_json.sync_write_json_atomic(path, {"a": 1}, durable=True)
    assert fsync.call_count >= 1
    assert atomic_json.sync_read_json(path) == {"a": 1}
    with patch.object(atomic_json.os, "fsync") as fsync:
        atomic_json.sync_write_json_atomic(path, {"a": 2})
    assert fsync.call_count == 0


async def test_crash_forensics_markers_are_written_durably(hass, tmp_path):
    from custom_components.ha_soc import crash_forensics

    calls: list[bool] = []
    real = crash_forensics.sync_write_json_atomic

    def spy(path, payload, **kwargs):
        calls.append(bool(kwargs.get("durable")))
        return real(path, payload, **kwargs)

    store = HaSocData(hass)
    forensics = crash_forensics.CrashForensics(hass, store, None, None)
    forensics._heartbeat_path = str(tmp_path / "heartbeat.json")
    forensics._last_stop_path = str(tmp_path / "last_stop.json")
    with patch.object(crash_forensics, "sync_write_json_atomic", spy):
        forensics._sync_write_heartbeat()
        await forensics._async_on_stop(None)
    assert calls == [True, True]


async def test_retry_after_failed_flush_hashes_only_new_records(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for i in range(50):
        _log(audit, i)
    with patch(
        "custom_components.ha_soc.audit.os.open", side_effect=OSError(28, "full")
    ):
        await audit._async_flush()
    for i in range(50, 55):
        _log(audit, i)
    with patch(
        "custom_components.ha_soc.audit.hashlib.sha256", wraps=hashlib.sha256
    ) as sha:
        with patch(
            "custom_components.ha_soc.audit.os.open", side_effect=OSError(28, "full")
        ):
            await audit._async_flush()
    assert sha.call_count == 5
    await audit._async_flush()
    assert [r["seq"] for r in _records_on_disk(audit)] == list(range(1, 56))


async def test_buffer_is_bounded_and_the_loss_is_recorded(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with patch("custom_components.ha_soc.audit._BUFFER_MAX_RECORDS", 5):
        for i in range(9):
            _log(audit, i)
        assert len(audit._buffer) == 5
        await audit._async_flush()
        await audit._async_flush()
    records = _records_on_disk(audit)
    assert [r["seq"] for r in records] == list(range(1, 7))
    assert records[-1]["category"] == "audit_records_dropped"
    assert records[-1]["detail"]["dropped"] == 4
    assert (await audit.async_verify_chain())["ok"] is True


async def test_failure_traceback_is_rate_limited(hass, tmp_path, caplog):
    audit = await _make_audit(hass, tmp_path)
    _log(audit, 0)
    with patch(
        "custom_components.ha_soc.audit.os.open", side_effect=OSError(28, "full")
    ):
        for _ in range(3):
            await audit._async_flush()
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1


async def test_unrecoverable_torn_tail_does_not_corrupt_the_next_record(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    _log(audit, 0)
    real_write = os.write
    calls = {"n": 0}

    def torn_write(fd, data):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_write(fd, data[:10])
        raise OSError(5, "io")

    with (
        patch("custom_components.ha_soc.audit.os.write", side_effect=torn_write),
        patch("custom_components.ha_soc.audit.os.ftruncate", side_effect=OSError(5, "io")),
    ):
        await audit._async_flush()
    assert len(audit._buffer) == 1
    await audit._async_flush()
    day_file = os.path.join(
        audit._dir_path, next(n for n in os.listdir(audit._dir_path) if n.startswith("audit-"))
    )
    lines = [ln for ln in open(day_file, encoding="utf-8").read().split(chr(10)) if ln]
    assert json.loads(lines[-1])["seq"] == 1
    assert len(audit._buffer) == 0


async def test_close_failure_after_durable_write_is_not_a_lost_batch(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    _log(audit, 0)
    real_close = os.close
    state = {"failed": False}

    def close(fd):
        real_close(fd)
        if not state["failed"]:
            state["failed"] = True
            raise OSError(5, "io")

    with patch("custom_components.ha_soc.audit.os.close", side_effect=close):
        await audit._async_flush()
    assert len(audit._buffer) == 0
    assert [r["seq"] for r in _records_on_disk(audit)] == [1]


async def test_directories_are_fsynced_for_new_day_file_and_chain_head(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    _log(audit, 0)
    with patch("custom_components.ha_soc.audit.fsync_directory") as fsd:
        await audit._async_flush()
    assert fsd.call_count >= 2
    assert all(call.args[0] == audit._dir_path for call in fsd.call_args_list)


@pytest.mark.parametrize(
    "key",
    ["token_value", "token_data", "otp", "totp_secret", "auth_header", "cookie", "session", "session_cookie"],
)
def test_more_credential_shapes_are_secret(key):
    assert _is_secret_key(key)


@pytest.mark.parametrize("key", ["auth_type", "session_id", "token_count", "auth_method", "revoke_sessions", "sessions_revoked"])
def test_credential_metadata_stays_visible(key):
    assert not _is_secret_key(key)
