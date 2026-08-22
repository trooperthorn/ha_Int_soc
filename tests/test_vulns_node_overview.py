"""Real dynamic check of DeviceVulnerabilityTracker.async_node_overview()."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.vulns import (
    NODE_STATUS_CRITICAL,
    NODE_STATUS_UNMANAGED,
    NODE_STATUS_UP,
)


async def test_node_overview_buckets_and_risk_score(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    healthy = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "healthy-cam")},
        manufacturer="Reolink",
        model="RLC-810A",
        name="Driveway Camera",
    )
    risky = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "risky-router")},
        manufacturer="TP-Link",
        model="Archer C7",
        name="Office Router",
    )
    unmanaged = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "mystery-device")},
        name="Mystery Device",
    )

    store = entry.runtime_data.store
    store.async_upsert_finding(
        "vuln_findings",
        f"{risky.id}:CVE-2024-9999",
        {
            "device_id": risky.id,
            "device_name": "Office Router",
            "cve_id": "CVE-2024-9999",
            "cvss": 9.1,
            "severity": "critical",
            "confidence": "curated_map",
            "status": "new",
        },
    )

    overview = await entry.runtime_data.vulns.async_node_overview()
    by_id = {n["device_id"]: n for n in overview["nodes"]}

    assert by_id[healthy.id]["status"] == NODE_STATUS_UP
    assert by_id[healthy.id]["risk_score"] == 0.0

    assert by_id[risky.id]["status"] == NODE_STATUS_CRITICAL
    assert by_id[risky.id]["risk_score"] == 9.1
    assert by_id[risky.id]["severity_counts"]["critical"] == 1
    assert by_id[risky.id]["vendor"] == "TP-Link"

    assert by_id[unmanaged.id]["status"] == NODE_STATUS_UNMANAGED

    assert overview["status_counts"][NODE_STATUS_CRITICAL] == 1
    assert overview["status_counts"][NODE_STATUS_UNMANAGED] == 1
    assert overview["by_vendor"]["TP-Link"] == 1

    # Highest-risk node sorts first.
    assert overview["nodes"][0]["device_id"] == risky.id

    assert await hass.config_entries.async_unload(entry.entry_id)
