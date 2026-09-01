"""HaSocData load/save round-trip and finding-lifecycle helpers."""
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    DEFAULT_SECURITY_SOURCES_ENABLED,
    SYSLOG_FORMAT_RFC5424_JSON,
)
from custom_components.ha_soc.store import HaSocData, default_store_data


async def test_default_shape() -> None:
    data = default_store_data()
    assert data["settings"]["audit_retention_days"] == 90
    assert data["permissions_matrix"] == {}
    assert data["detections"] == {}


async def test_load_save_round_trip(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    had_data = await store.async_load()
    assert had_data is False
    assert store.settings["scanner_enabled"] is True

    store.async_update_settings(scanner_enabled=False)
    await store.async_save_now()

    store2 = HaSocData(hass)
    had_data2 = await store2.async_load()
    assert had_data2 is True
    assert store2.settings["scanner_enabled"] is False


async def test_finding_lifecycle(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()

    store.async_upsert_finding("vuln_findings", "dev1:CVE-2024-1", {"severity": "high", "status": "new"})
    assert store.data["vuln_findings"]["dev1:CVE-2024-1"]["status"] == "new"

    store.async_set_finding_status(
        "vuln_findings", "dev1:CVE-2024-1", "confirmed", by_user_id="u1", note="looked into it", at="2026-01-01T00:00:00+00:00"
    )
    finding = store.data["vuln_findings"]["dev1:CVE-2024-1"]
    assert finding["status"] == "confirmed"
    assert finding["status_by"] == "u1"

    # Re-upserting (simulating a re-scan) must preserve the analyst's status.
    store.async_upsert_finding("vuln_findings", "dev1:CVE-2024-1", {"severity": "high", "status": "new"})
    assert store.data["vuln_findings"]["dev1:CVE-2024-1"]["status"] == "confirmed"


async def test_load_merges_missing_nested_settings_keys(hass: HomeAssistant) -> None:
    """A real production bug: a store written before security_sources_enabled
    existed (any install that ran before that feature shipped) has a full
    `settings` dict on disk that is simply missing the new key entirely. The
    old load path did `defaults.update(stored)`, a one-level-deep merge —
    since `settings` is itself a top-level key present in `stored`, that
    replaced the correctly-defaulted `settings` sub-dict wholesale with the
    on-disk one, permanently dropping `security_sources_enabled`. The
    Settings tab's frontend reads `s.security_sources_enabled[domain]`
    unconditionally, so a missing key there crashed its render every time,
    with no server-side error — "Settings never loads, no error in the log".
    """
    store = HaSocData(hass)
    await store.async_load()

    old_settings = dict(store.data["settings"])
    del old_settings["security_sources_enabled"]
    del old_settings["syslog_format"]
    old_settings["scanner_enabled"] = False  # a real prior customization that must survive the merge
    store.data["settings"] = old_settings
    await store.async_save_now()

    store2 = HaSocData(hass)
    had_data = await store2.async_load()
    assert had_data is True
    assert store2.settings["security_sources_enabled"] == DEFAULT_SECURITY_SOURCES_ENABLED
    assert store2.settings["syslog_format"] == SYSLOG_FORMAT_RFC5424_JSON
    assert store2.settings["scanner_enabled"] is False


async def test_watchdog_preserves_ack(hass: HomeAssistant) -> None:
    """Work item 3.10: a writer replacing a detection row wholesale (the
    resource watchdog builds a fresh dict with status open on every
    re-trip) must not clobber an analyst's ack/resolved status."""
    store = HaSocData(hass)
    await store.async_load()

    def watchdog_row() -> dict:
        # The exact shape resource_watchdog.py writes: a fresh dict with
        # status "open", no knowledge of prior analyst state.
        return {
            "id": "watchdog_ma",
            "rule_id": "container_resource_breach",
            "severity": "high",
            "status": "open",
            "ts": "2026-08-30T00:00:00+00:00",
            "last_seen": "2026-08-30T00:00:00+00:00",
            "recurrence_count": 1,
            "title": "Container 'ma' sustained cpu",
            "detail": {},
        }

    store.async_upsert_detection("watchdog_ma", watchdog_row())
    store.async_set_detection_status(
        "watchdog_ma", "ack", by_user_id="analyst", at="2026-08-30T01:00:00+00:00"
    )

    # Re-trip: a brand-new dict, status open again.
    store.async_upsert_detection("watchdog_ma", watchdog_row())

    detection = store.data["detections"]["watchdog_ma"]
    assert detection["status"] == "ack"
    assert detection["status_by"] == "analyst"
    assert detection["status_at"] == "2026-08-30T01:00:00+00:00"


async def test_purge_user(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()
    store.async_set_user_dashboard_policy("u1", "lovelace", {"views": {"home": True}, "sidebar_hidden": False})
    assert "u1" in store.data["permissions_matrix"]

    store.async_purge_user("u1")
    assert "u1" not in store.data["permissions_matrix"]
