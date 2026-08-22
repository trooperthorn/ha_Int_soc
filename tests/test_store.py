"""HaSocData load/save round-trip and finding-lifecycle helpers."""
from homeassistant.core import HomeAssistant

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


async def test_purge_user(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()
    store.async_set_user_dashboard_policy("u1", "lovelace", {"views": {"home": True}, "sidebar_hidden": False})
    assert "u1" in store.data["permissions_matrix"]

    store.async_purge_user("u1")
    assert "u1" not in store.data["permissions_matrix"]
