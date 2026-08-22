"""Real dynamic check of DeviceVulnerabilityTracker.async_device_overview().

Status is a separate axis from vulnerability severity — it reflects only
whether Home Assistant is actually hearing from the device right now
(available/partial/unavailable/disabled/no_entities), independent of any
CVE finding. These tests exercise both axes against real device/entity
registries and live states.
"""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.vulns import (
    DEVICE_STATUS_AVAILABLE,
    DEVICE_STATUS_DISABLED,
    DEVICE_STATUS_NO_ENTITIES,
    DEVICE_STATUS_PARTIAL,
    DEVICE_STATUS_UNAVAILABLE,
)


async def test_device_overview_status_buckets_and_risk_score(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    def _make_device(key: str, **kwargs):
        return device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, key)}, **kwargs
        )

    available_device = _make_device("available-cam", manufacturer="Reolink", model="RLC-810A", name="Driveway Camera")
    available_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "available-entity", device_id=available_device.id, config_entry=entry
    )
    hass.states.async_set(available_entity.entity_id, "42")

    unavailable_device = _make_device("dead-router", manufacturer="TP-Link", model="Archer C7", name="Office Router")
    dead_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "dead-entity", device_id=unavailable_device.id, config_entry=entry
    )
    hass.states.async_set(dead_entity.entity_id, "unavailable")

    partial_device = _make_device("flaky-hub", manufacturer="Philips", model="Hue Bridge", name="Living Room Hub")
    flaky_ok_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "flaky-ok", device_id=partial_device.id, config_entry=entry
    )
    flaky_dead_entity = entity_registry.async_get_or_create(
        "sensor", DOMAIN, "flaky-dead", device_id=partial_device.id, config_entry=entry
    )
    hass.states.async_set(flaky_ok_entity.entity_id, "on")
    hass.states.async_set(flaky_dead_entity.entity_id, "unknown")

    disabled_device = _make_device("mothballed-plug", manufacturer="Sonoff", name="Old Smart Plug")
    device_registry.async_update_device(disabled_device.id, disabled_by=dr.DeviceEntryDisabler.USER)

    empty_device = _make_device("mystery-device", name="Mystery Device")

    store = entry.runtime_data.store
    store.async_upsert_finding(
        "vuln_findings",
        f"{unavailable_device.id}:CVE-2024-9999",
        {
            "device_id": unavailable_device.id,
            "device_name": "Office Router",
            "cve_id": "CVE-2024-9999",
            "cvss": 9.1,
            "severity": "critical",
            "confidence": "curated_map",
            "status": "new",
        },
    )

    overview = await entry.runtime_data.vulns.async_device_overview()
    by_id = {d["device_id"]: d for d in overview["devices"]}

    assert by_id[available_device.id]["status"] == DEVICE_STATUS_AVAILABLE
    assert by_id[available_device.id]["risk_score"] == 0.0

    # A critical CVE finding must NOT change the availability status — it's
    # a separate axis, only risk_score/severity_counts reflect it.
    assert by_id[unavailable_device.id]["status"] == DEVICE_STATUS_UNAVAILABLE
    assert by_id[unavailable_device.id]["risk_score"] == 9.1
    assert by_id[unavailable_device.id]["severity_counts"]["critical"] == 1
    assert by_id[unavailable_device.id]["vendor"] == "TP-Link"

    assert by_id[partial_device.id]["status"] == DEVICE_STATUS_PARTIAL
    assert by_id[disabled_device.id]["status"] == DEVICE_STATUS_DISABLED
    assert by_id[empty_device.id]["status"] == DEVICE_STATUS_NO_ENTITIES

    assert overview["status_counts"][DEVICE_STATUS_UNAVAILABLE] == 1
    assert overview["status_counts"][DEVICE_STATUS_PARTIAL] == 1
    assert overview["status_counts"][DEVICE_STATUS_DISABLED] == 1
    assert overview["status_counts"][DEVICE_STATUS_NO_ENTITIES] == 1
    assert overview["status_counts"][DEVICE_STATUS_AVAILABLE] == 1
    assert overview["by_vendor"]["TP-Link"] == 1

    # Highest-risk device sorts first.
    assert overview["devices"][0]["device_id"] == unavailable_device.id

    assert await hass.config_entries.async_unload(entry.entry_id)
