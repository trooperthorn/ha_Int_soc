"""Work item 3.3 (D-6): evidence retention and bulk detection resolve."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.websocket_api import ws_detections_bulk_set_status


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner1")
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant, tmp_path) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # Per-test audit directory; the harness config dir is shared (see
    # test_audit.py for the same isolation trick).
    config_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    return config_entry


def _record(status: str, *, days_old: int, kind: str = "detection") -> dict:
    at = (dt_util.utcnow() - timedelta(days=days_old)).isoformat()
    if kind == "detection":
        return {
            "id": "x",
            "rule_id": "brute_force_ip",
            "status": status,
            "status_at": at,
            "ts": at,
            "last_seen": at,
        }
    return {"id": "x", "severity": "high", "status": status, "status_at": at, "first_seen": at}


async def test_detections_retention(hass: HomeAssistant) -> None:
    """Only RESOLVED detections and RESOLVED/DISMISSED findings older than
    evidence_retention_days are pruned; open/ack/confirmed items never
    expire, and recent closed items survive."""
    store = HaSocData(hass)
    await store.async_load()
    assert store.settings["evidence_retention_days"] == 365

    detections = store.data["detections"]
    detections["old_resolved"] = _record("resolved", days_old=400)
    detections["old_ack"] = _record("ack", days_old=400)
    detections["old_open"] = _record("open", days_old=400)
    detections["fresh_resolved"] = _record("resolved", days_old=10)

    findings = store.data["vuln_findings"]
    findings["old_dismissed"] = _record("dismissed", days_old=400, kind="finding")
    findings["old_resolved"] = _record("resolved", days_old=400, kind="finding")
    findings["old_confirmed"] = _record("confirmed", days_old=400, kind="finding")
    findings["fresh_dismissed"] = _record("dismissed", days_old=10, kind="finding")
    store.data["misconfig_findings"]["old_resolved"] = _record(
        "resolved", days_old=400, kind="finding"
    )
    store.data["scanner_findings"]["old_dismissed"] = _record(
        "dismissed", days_old=400, kind="finding"
    )

    removed = store.async_prune_evidence(dt_util.utcnow())

    assert set(detections) == {"old_ack", "old_open", "fresh_resolved"}
    assert set(findings) == {"old_confirmed", "fresh_dismissed"}
    assert store.data["misconfig_findings"] == {}
    assert store.data["scanner_findings"] == {}
    assert removed == {
        "detections": 1,
        "vuln_findings": 2,
        "misconfig_findings": 1,
        "scanner_findings": 1,
    }


async def test_detections_retention_respects_setting(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()
    store.async_update_settings(evidence_retention_days=30)
    store.data["detections"]["resolved_40d"] = _record("resolved", days_old=40)

    store.async_prune_evidence(dt_util.utcnow())

    assert store.data["detections"] == {}


async def test_bulk_resolve_is_audited(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """One bulk call flips every named detection and writes ONE audit
    record carrying the id list; unknown ids come back as missing."""
    store = entry.runtime_data.store
    for det_id in ("d1", "d2", "d3"):
        store.data["detections"][det_id] = _record("open", days_old=1) | {"id": det_id}

    connection = _connection()
    ws_detections_bulk_set_status(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/detections/bulk_set_status",
            "detection_ids": ["d1", "d2", "ghost"],
            "status": "resolved",
        },
    )
    await hass.async_block_till_done()

    assert store.data["detections"]["d1"]["status"] == "resolved"
    assert store.data["detections"]["d1"]["status_by"] == "owner1"
    assert store.data["detections"]["d2"]["status"] == "resolved"
    assert store.data["detections"]["d3"]["status"] == "open"

    result = connection.send_result.call_args[0][1]
    assert result == {"updated": 2, "missing": ["ghost"]}

    records = [
        r
        for r in await entry.runtime_data.audit.async_query(
            category="detection_status_changed"
        )
        if r["detail"].get("action") == "bulk_set_status"
    ]
    assert len(records) == 1
    assert records[0]["detail"]["detection_ids"] == ["d1", "d2"]
    assert records[0]["detail"]["new_status"] == "resolved"
