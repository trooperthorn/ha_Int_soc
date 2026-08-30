"""Audit category-volume stats: per-category record counts and byte shares
for the newest day, so the owner can see what produces the log's bulk."""
from __future__ import annotations

import os
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.store import HaSocData


async def _make_audit(hass: HomeAssistant, tmp_path: Any) -> AuditLog:
    store = HaSocData(hass)
    await store.async_load()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    return audit


async def test_audit_category_stats(hass: HomeAssistant, tmp_path: Any) -> None:
    audit = await _make_audit(hass, tmp_path)
    await audit.async_start()
    try:
        for i in range(5):
            audit.async_log(
                "service_call",
                user_id="u1",
                domain="light",
                service="turn_on",
                detail={"padding": "x" * 200},
            )
        audit.async_log("login_ok", user_id="u1", ip="10.0.0.2")
        audit.async_log("login_fail", ip="10.0.0.3")

        stats = await audit.async_category_stats()

        assert stats["day"] is not None
        assert stats["files"] >= 1
        assert stats["total_records"] == 7
        by_category = {c["category"]: c for c in stats["categories"]}
        assert by_category["service_call"]["records"] == 5
        assert by_category["login_ok"]["records"] == 1
        assert by_category["login_fail"]["records"] == 1

        # Categories come back sorted by byte volume, largest first, and
        # the padded service_call records dominate.
        assert stats["categories"][0]["category"] == "service_call"
        assert by_category["service_call"]["byte_share"] > 0.5

        # Byte accounting adds up: shares sum to ~1 and bytes to the total.
        assert sum(c["bytes"] for c in stats["categories"]) == stats["total_bytes"]
        assert abs(sum(c["byte_share"] for c in stats["categories"]) - 1.0) < 0.01
    finally:
        await audit.async_stop()


async def test_audit_category_stats_scans_newest_day_only(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    audit = await _make_audit(hass, tmp_path)
    await audit.async_start()
    try:
        audit.async_log("login_ok", user_id="u1")
        await audit._async_flush()

        # Plant an older day file by hand; it must not enter the stats.
        old_path = os.path.join(audit._dir_path, "audit-2020-01-01.jsonl")
        with open(old_path, "w", encoding="utf-8") as handle:
            handle.write('{"category": "service_call", "seq": 1, "ts": "2020-01-01T00:00:00+00:00"}\n')

        stats = await audit.async_category_stats()

        assert stats["total_records"] == 1
        assert {c["category"] for c in stats["categories"]} == {"login_ok"}
    finally:
        await audit.async_stop()


async def test_audit_category_stats_empty_log(hass: HomeAssistant, tmp_path: Any) -> None:
    audit = await _make_audit(hass, tmp_path)
    stats = await audit.async_category_stats()
    assert stats == {
        "day": None,
        "files": 0,
        "total_records": 0,
        "total_bytes": 0,
        "categories": [],
    }
