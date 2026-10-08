"""The audit chain stays valid across clock steps, torn tails and crashes."""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any
from unittest.mock import patch

from custom_components.ha_soc.audit import AuditLog
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


def _at(day: int, hour: int = 12):
    return patch(
        "custom_components.ha_soc.audit.dt_util.utcnow",
        return_value=dt.datetime(2026, 10, day, hour, 0, tzinfo=dt.timezone.utc),
    )


def _day_files(audit: AuditLog) -> list[str]:
    return sorted(n for n in os.listdir(audit._dir_path) if n.startswith("audit-"))


def _seqs(audit: AuditLog) -> list[int]:
    out: list[int] = []
    for name in _day_files(audit):
        with open(os.path.join(audit._dir_path, name), encoding="utf-8") as handle:
            out.extend(json.loads(line)["seq"] for line in handle if line.strip())
    return out


async def _restart(hass, audit: AuditLog) -> AuditLog:
    """A new instance on the same directory, as after a process restart."""
    fresh = AuditLog(hass, audit._store)
    fresh._dir_path = audit._dir_path
    await hass.async_add_executor_job(fresh._sync_load_chain_head)
    fresh._async_log_recovery_events()
    return fresh


async def test_backward_clock_step_keeps_chain_ok(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()
    with _at(7):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()
    with _at(8, 13):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()

    assert _day_files(audit) == ["audit-2026-10-08.jsonl"]
    assert _seqs(audit) == [1, 2, 3]
    result = await audit.async_verify_chain()
    assert result["ok"] is True
    assert result["records_checked"] == 3


async def test_backward_clock_step_inside_one_batch(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        audit.async_log("login_ok", user_id="u")
    with _at(9):
        audit.async_log("login_ok", user_id="u")
    with _at(8, 23):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()

    assert _day_files(audit) == ["audit-2026-10-08.jsonl", "audit-2026-10-09.jsonl"]
    assert _seqs(audit) == [1, 2, 3]
    assert (await audit.async_verify_chain())["ok"] is True


async def test_clock_step_back_survives_restart(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(9):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()
    audit = await _restart(hass, audit)
    with _at(7):
        audit.async_log("login_ok", user_id="u")
    await audit._async_flush()

    assert _day_files(audit) == ["audit-2026-10-09.jsonl"]
    assert (await audit.async_verify_chain())["ok"] is True


async def test_verify_walks_seq_order_across_out_of_order_files(hass, tmp_path):
    """Files an older build wrote with a stepped-back clock still verify."""
    audit = await _make_audit(hass, tmp_path)
    for day in (8, 9, 8):
        with _at(day):
            audit.async_log("login_ok", user_id="u")
        await audit._async_flush()
    # Rebuild the layout the old grouping produced: record 3 in the day-8 file.
    records: list[dict[str, Any]] = []
    for name in _day_files(audit):
        with open(os.path.join(audit._dir_path, name), encoding="utf-8") as handle:
            records.extend(json.loads(line) for line in handle)
    for name in _day_files(audit):
        os.remove(os.path.join(audit._dir_path, name))
    layout = {
        "audit-2026-10-08.jsonl": [records[0], records[2]],
        "audit-2026-10-09.jsonl": [records[1]],
    }
    for name, recs in layout.items():
        with open(os.path.join(audit._dir_path, name), "w", encoding="utf-8") as handle:
            for rec in recs:
                handle.write(json.dumps(rec, sort_keys=True) + "\n")

    assert (await audit.async_verify_chain())["ok"] is True


async def test_edited_record_still_fails_verify(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        for i in range(3):
            audit.async_log("login_ok", user_id="u", detail={"i": i})
    await audit._async_flush()
    path = os.path.join(audit._dir_path, _day_files(audit)[0])
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    record = json.loads(lines[1])
    record["user_id"] = "someone-else"
    lines[1] = json.dumps(record, sort_keys=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    result = await audit.async_verify_chain()
    assert result["ok"] is False
    assert result["reason"] == "hash_mismatch"
    assert result["first_break_seq"] == 2


async def test_edited_record_in_stepped_back_layout_still_fails(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    for day in (8, 7, 8):
        with _at(day):
            audit.async_log("login_ok", user_id="u")
        await audit._async_flush()
    path = os.path.join(audit._dir_path, _day_files(audit)[0])
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    record = json.loads(lines[1])
    record["category"] = "forged"
    lines[1] = json.dumps(record, sort_keys=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    assert (await audit.async_verify_chain())["ok"] is False


async def test_torn_tail_is_repaired_once_with_an_audit_event(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        for i in range(3):
            audit.async_log("login_ok", user_id="u", detail={"i": i})
    await audit._async_flush()
    path = os.path.join(audit._dir_path, _day_files(audit)[0])
    torn = '{"seq": 4, "ts": "2026-10-08T12:00:00+00:00", "category": "login_o'
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(torn)

    restarted = await _restart(hass, audit)
    with _at(8, 14):
        restarted.async_log("login_ok", user_id="u", detail={"after": "restart"})
    await restarted._async_flush()

    with open(path, encoding="utf-8") as handle:
        content = handle.read()
    assert torn not in content
    records = [json.loads(line) for line in content.splitlines()]
    assert [r["seq"] for r in records] == [1, 2, 3, 4, 5]
    repairs = [r for r in records if r["category"] == "audit_tail_repaired"]
    assert len(repairs) == 1
    assert repairs[0]["detail"]["bytes_removed"] == len(torn)
    assert repairs[0]["detail"]["file"] == os.path.basename(path)
    assert (await restarted.async_verify_chain())["ok"] is True

    # A second restart finds nothing to repair.
    again = await _restart(hass, restarted)
    await again._async_flush()
    assert again._recovery_events == []
    assert len(_seqs(again)) == 5
    assert (await again.async_verify_chain())["ok"] is True


async def test_torn_tail_that_is_a_whole_record_is_kept(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        for i in range(2):
            audit.async_log("login_ok", user_id="u", detail={"i": i})
    await audit._async_flush()
    path = os.path.join(audit._dir_path, _day_files(audit)[0])
    with open(path, "rb+") as handle:
        handle.seek(-1, os.SEEK_END)
        assert handle.read(1) == b"\n"
        handle.truncate(handle.tell() - 1)

    restarted = await _restart(hass, audit)
    assert restarted._recovery_events == []
    with _at(8, 14):
        restarted.async_log("login_ok", user_id="u")
    await restarted._async_flush()
    assert _seqs(restarted) == [1, 2, 3]
    assert (await restarted.async_verify_chain())["ok"] is True


async def test_crash_between_append_and_head_write_has_no_duplicate_seq(hass, tmp_path):
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        for i in range(3):
            audit.async_log("login_ok", user_id="u", detail={"i": i})
    await audit._async_flush()
    with _at(8, 13):
        audit.async_log("login_ok", user_id="u", detail={"i": 3})
    with patch.object(AuditLog, "_sync_write_chain_head", return_value=False):
        await audit._async_flush()
    assert _seqs(audit) == [1, 2, 3, 4]
    with open(os.path.join(audit._dir_path, "chain_head.json"), encoding="utf-8") as handle:
        assert json.load(handle)["seq"] == 3

    restarted = await _restart(hass, audit)
    with _at(8, 14):
        restarted.async_log("login_ok", user_id="u", detail={"after": "restart"})
    await restarted._async_flush()

    seqs = _seqs(restarted)
    assert len(seqs) == len(set(seqs))
    assert seqs[:4] == [1, 2, 3, 4]
    records = []
    for name in _day_files(restarted):
        with open(os.path.join(restarted._dir_path, name), encoding="utf-8") as handle:
            records.extend(json.loads(line) for line in handle)
    assert [r["category"] for r in records[4:]] == ["audit_head_rebuilt", "login_ok"]
    assert records[4]["detail"] == {
        "head_seq_before": 3,
        "head_seq_after": 4,
        "actor_source": "system",
    }
    assert (await restarted.async_verify_chain())["ok"] is True


async def test_truncated_tail_is_not_masked_by_the_rebuild(hass, tmp_path):
    """A head ahead of the files is truncation, not a lagging head."""
    audit = await _make_audit(hass, tmp_path)
    with _at(8):
        for i in range(4):
            audit.async_log("login_ok", user_id="u", detail={"i": i})
    await audit._async_flush()
    path = os.path.join(audit._dir_path, _day_files(audit)[0])
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines[:2]) + "\n")

    restarted = await _restart(hass, audit)
    assert restarted._recovery_events == []
    result = await restarted.async_verify_chain()
    assert result["ok"] is False
    assert result["reason"] == "tail_truncated"
