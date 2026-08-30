"""Audit chain verification across retention: the anchor contract.

Retention deletes whole day files, which used to remove the front of the
hash chain and make a perfectly healthy log fail verification. The fix
records an anchor (the seq and hash of the newest expired record) in
chain_head.json and restarts verification there. These tests drive the
real files on disk through AuditLog's own flush, retention, and
verification paths, fabricating only the wall clock, because the
guarantee under test is what survives on disk: an expired-but-healthy log
must verify, and every tamper class that was detectable before the anchor
existed must stay detectable after it.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

import homeassistant.helpers.issue_registry as ir
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.store import HaSocData


async def _make_audit(hass: HomeAssistant, tmp_path: Any) -> AuditLog:
    """Build an AuditLog writing into this test's private tmp directory.

    The directory is overridden before anything touches disk so tests never
    share audit files through a common config dir.
    """
    store = HaSocData(hass)
    await store.async_load()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    return audit


async def _log_on_day(audit: AuditLog, when: datetime, count: int) -> None:
    """Log and flush ``count`` records with the clock pinned to ``when``.

    Pinning the clock routes the records into that UTC day's file, and it
    also pins the retention cutoff inside the same flush, so a file being
    written in the "past" is not expired by the very flush that creates it.
    """
    with patch(
        "custom_components.ha_soc.audit.dt_util.utcnow", return_value=when
    ):
        for index in range(count):
            audit.async_log(
                "service_call",
                user_id=f"user-{index}",
                domain="light",
                service="turn_on",
            )
        await audit._async_flush()


async def _build_expired_log(
    hass: HomeAssistant, tmp_path: Any
) -> tuple[AuditLog, datetime, dict[str, str]]:
    """A log whose two oldest day files have expired under retention.

    Writes 3 records 100 days ago, 2 records 99 days ago, then 2 records
    now. The final flush's retention pass deletes both old files (the
    default window is 90 days) and writes the anchor at seq 5. Returns the
    audit log, the newest expired day, and the expired files' original
    contents keyed by path so a test can resurrect one.
    """
    audit = await _make_audit(hass, tmp_path)
    now = dt_util.utcnow()
    day_a = now - timedelta(days=100)
    day_b = now - timedelta(days=99)
    await _log_on_day(audit, day_a, 3)
    await _log_on_day(audit, day_b, 2)

    expired_contents: dict[str, str] = {}
    for _file_date, path in audit._sync_list_day_files():
        with open(path, "r", encoding="utf-8") as handle:
            expired_contents[path] = handle.read()

    audit.async_log("service_call", user_id="keeper-1", domain="light", service="turn_on")
    audit.async_log("service_call", user_id="keeper-2", domain="light", service="turn_off")
    await audit._async_flush()

    # Preconditions for every test below: the old files really are gone
    # and only the current day's file survived.
    surviving = audit._sync_list_day_files()
    assert len(surviving) == 1
    assert all(path not in expired_contents for _d, path in surviving)
    return audit, day_b, expired_contents


def _head_path(audit: AuditLog) -> str:
    return os.path.join(audit._dir_path, "chain_head.json")


def _read_head(audit: AuditLog) -> dict[str, Any]:
    with open(_head_path(audit), "r", encoding="utf-8") as handle:
        return json.load(handle)


async def test_retention_applied_healthy_log_verifies_from_anchor(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Expiry alone must not read as tampering: the anchored chain verifies.

    This is the inversion of the review's reproduction test (a healthy log
    failed verification as soon as retention deleted a day file).
    """
    audit, day_b, _expired = await _build_expired_log(hass, tmp_path)

    head = _read_head(audit)
    anchor = head["anchor"]
    assert anchor["seq"] == 5
    assert isinstance(anchor["hash"], str) and anchor["hash"]
    assert anchor["expired_through"] == day_b.date().isoformat()
    assert dt_util.parse_datetime(anchor["expired_at"]) is not None

    result = await audit.async_verify_chain()
    assert result["ok"] is True
    assert result["reason"] is None
    assert result["records_checked"] == 2
    assert result["verified_from_seq"] == 6
    assert result["expired_through"] == day_b.date().isoformat()


async def test_verify_reports_from_seq_one_without_anchor(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """With nothing expired the whole chain is re-checked from record 1."""
    audit = await _make_audit(hass, tmp_path)
    audit.async_log("service_call", user_id="u1", domain="light", service="turn_on")
    await audit._async_flush()

    result = await audit.async_verify_chain()
    assert result["ok"] is True
    assert result["verified_from_seq"] == 1
    assert result["expired_through"] is None
    assert "anchor" not in _read_head(audit)


async def test_tamper_after_anchor_detected(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Editing a surviving record still fails with hash_mismatch."""
    audit, _day_b, _expired = await _build_expired_log(hass, tmp_path)
    _file_date, path = audit._sync_list_day_files()[0]

    with open(path, "r", encoding="utf-8") as handle:
        lines = [line for line in handle.read().splitlines() if line.strip()]
    record = json.loads(lines[0])
    record["user_id"] = "attacker"
    lines[0] = json.dumps(record, sort_keys=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")

    result = await audit.async_verify_chain()
    assert result["ok"] is False
    assert result["reason"] == "hash_mismatch"
    assert result["first_break_seq"] == 6
    # The failure result still tells the operator which range was covered.
    assert result["verified_from_seq"] == 6


async def test_deleting_newest_file_after_anchor_still_tail_truncated(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Removing the tail still trips the checkpoint completeness check.

    The anchor must never weaken the truncation defense: the head
    checkpoint says seq 7 was flushed, the anchor only accounts for seqs
    through 5, and nothing on disk covers the gap.
    """
    audit, _day_b, _expired = await _build_expired_log(hass, tmp_path)
    _file_date, path = audit._sync_list_day_files()[0]
    os.remove(path)

    result = await audit.async_verify_chain()
    assert result["ok"] is False
    assert result["reason"] == "tail_truncated"
    assert result["checkpoint_seq"] == 7
    assert result["last_on_disk_seq"] == 5


async def test_surviving_record_at_or_below_anchor_is_anchor_inconsistent(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """A resurrected expired file contradicts the anchor and must fail.

    The anchor asserts everything through its seq was expired; a surviving
    record at or below it means the log and the anchor cannot both be
    telling the truth, which is its own distinct failure, not a hash break.
    The resurrected records are planted in a file dated inside the
    retention window: a file at its original expired date would simply be
    deleted again by the retention pass that runs before verification,
    which is the other layer of this defense.
    """
    audit, _day_b, expired = await _build_expired_log(hass, tmp_path)
    # Resurrect the newest expired file's records (seqs 4 and 5) under
    # yesterday's date, so they sort ahead of the surviving records.
    yesterday = (dt_util.utcnow() - timedelta(days=1)).date().isoformat()
    resurrect_path = os.path.join(audit._dir_path, f"audit-{yesterday}.jsonl")
    source_path = sorted(expired)[-1]
    with open(resurrect_path, "w", encoding="utf-8") as handle:
        handle.write(expired[source_path])

    result = await audit.async_verify_chain()
    assert result["ok"] is False
    assert result["reason"] == "anchor_inconsistent"
    assert result["first_break_seq"] == 4


async def test_anchor_survives_flush_rewrite_of_head(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Later flushes rewrite chain_head.json but must keep the anchor.

    Without this, the first flush after retention would drop the anchor
    and the healthy log would become unverifiable again.
    """
    audit, _day_b, _expired = await _build_expired_log(hass, tmp_path)
    before = _read_head(audit)
    assert before["anchor"]["seq"] == 5

    audit.async_log("service_call", user_id="later", domain="switch", service="toggle")
    await audit._async_flush()

    after = _read_head(audit)
    assert after["seq"] == 8
    assert after["anchor"] == before["anchor"]

    # A restart must restore the anchor from disk too, or the restarted
    # process's first head rewrite would silently drop it.
    restarted = AuditLog(hass, audit._store)
    restarted._dir_path = audit._dir_path
    await hass.async_add_executor_job(restarted._sync_load_chain_head)
    restarted.async_log(
        "service_call", user_id="after-restart", domain="switch", service="toggle"
    )
    await restarted._async_flush()

    final = _read_head(audit)
    assert final["seq"] == 9
    assert final["anchor"] == before["anchor"]

    result = await audit.async_verify_chain()
    assert result["ok"] is True
    assert result["verified_from_seq"] == 6
    assert result["records_checked"] == 4


async def _build_wiped_log(
    hass: HomeAssistant, tmp_path: Any
) -> tuple[AuditLog, dict[str, Any]]:
    """Three flushed records, mirror at seq 3, then the directory deleted
    and a fresh AuditLog restarted over the same store. Returns the
    restarted log (started, caller must stop it) and the pre-wipe mirror.
    """
    audit = await _make_audit(hass, tmp_path)
    for index in range(3):
        audit.async_log(
            "service_call", user_id=f"u{index}", domain="light", service="turn_on"
        )
    await audit._async_flush()
    mirror = dict(audit._store.data["audit_head"])
    assert mirror["seq"] == 3
    assert mirror["hash"]

    shutil.rmtree(audit._dir_path)

    restarted = AuditLog(hass, audit._store)
    restarted._dir_path = audit._dir_path
    await restarted.async_start()
    # audit_chain_reset is an immediate-flush category (work item 1.7), so
    # letting the loop settle writes the reset record to disk.
    await hass.async_block_till_done()
    return restarted, mirror


async def test_audit_directory_wipe_is_detected(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Work item 1.5 acceptance: deleting the audit directory and
    restarting yields the audit record, the Repairs issue, and
    reason chain_reset on verify - and stays chain_reset on a later
    verify, because the missing history does not grow back.
    """
    restarted, mirror = await _build_wiped_log(hass, tmp_path)
    try:
        result = await restarted.async_verify_chain()
        assert result["ok"] is False
        assert result["reason"] == "chain_reset"
        assert result["first_break_seq"] is None
        # Everything after the reset point still re-verified record by
        # record: the reset record itself was checked.
        assert result["records_checked"] == 1
        assert result["verified_from_seq"] == mirror["seq"] + 1

        registry = ir.async_get(hass)
        assert registry.async_get_issue(DOMAIN, "audit_chain_reset") is not None

        # The verdict is sticky across flushes, not a one-shot: more
        # records extend the post-reset chain cleanly and the reason stays.
        restarted.async_log(
            "service_call", user_id="later", domain="switch", service="toggle"
        )
        result = await restarted.async_verify_chain()
        assert result["ok"] is False
        assert result["reason"] == "chain_reset"
        assert result["records_checked"] == 2
    finally:
        await restarted.async_stop()


async def test_chain_reset_is_itself_chained(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Work item 1.5: the discontinuity is a chained record, not a gap.

    The first record of the continued chain is the audit_chain_reset
    record, its prev_hash is the store mirror's hash, its seq continues
    the mirror's numbering, and its detail carries both heads. The head
    file keeps the reset marker so a later restart cannot lose it.
    """
    restarted, mirror = await _build_wiped_log(hass, tmp_path)
    try:
        day_files = restarted._sync_list_day_files()
        assert len(day_files) == 1
        with open(day_files[0][1], "r", encoding="utf-8") as handle:
            lines = [line for line in handle.read().splitlines() if line.strip()]
        first = json.loads(lines[0])
        assert first["category"] == "audit_chain_reset"
        assert first["seq"] == mirror["seq"] + 1
        assert first["prev_hash"] == mirror["hash"]
        assert first["detail"]["store_head"]["seq"] == mirror["seq"]
        assert first["detail"]["store_head"]["hash"] == mirror["hash"]
        # The head file was gone entirely, and the record says so.
        assert first["detail"]["disk_head"] is None

        with open(
            os.path.join(restarted._dir_path, "chain_head.json"), encoding="utf-8"
        ) as handle:
            head = json.load(handle)
        assert head["reset"]["seq"] == mirror["seq"]
        assert head["reset"]["hash"] == mirror["hash"]

        # The store mirror has moved on to the new head, which is what lets
        # the NEXT wipe be caught the same way.
        assert restarted._store.data["audit_head"]["seq"] == mirror["seq"] + 1
    finally:
        await restarted.async_stop()
