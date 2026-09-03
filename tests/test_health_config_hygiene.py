"""Integration tests for health.py's config_hygiene.py-backed checks: does
the finding get constructed correctly, and does severity correctly decide
whether it's mirrored to Repairs (never for SEVERITY_INFO, always
otherwise) — the actual user-facing wiring, on top of config_hygiene.py's
own already-tested detection logic.
"""
from __future__ import annotations

import homeassistant.helpers.issue_registry as ir
import pytest
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationHealth(hass, store)


async def test_alert_check_high_severity_mirrors_to_repairs(hass: HomeAssistant, health: IntegrationHealth) -> None:
    from unittest.mock import patch

    fake_config = {
        "alert": {"broken": {"name": "Broken", "entity_id": "binary_sensor.nonexistent", "notifiers": []}}
    }
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        findings = await health._check_alert_unknown_references()

    assert len(findings) == 1
    assert findings[0]["check"] == "alert_unknown_references"
    assert findings[0]["severity"] == "high"

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert findings[0]["id"] in issue_ids


async def test_empty_areas_check_info_severity_not_mirrored(hass: HomeAssistant, health: IntegrationHealth) -> None:
    from homeassistant.helpers import area_registry as ar

    ar.async_get(hass).async_get_or_create("Lonely Room")

    findings = await health._check_empty_areas_and_floors()

    assert len(findings) == 1
    assert findings[0]["severity"] == "info"

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert findings[0]["id"] not in issue_ids


async def test_empty_areas_check_clears_once_populated(hass: HomeAssistant, health: IntegrationHealth) -> None:
    from homeassistant.helpers import area_registry as ar, device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    area = ar.async_get(hass).async_get_or_create("Fills Up")
    findings = await health._check_empty_areas_and_floors()
    assert len(findings) == 1
    finding_id = findings[0]["id"]

    entry = MockConfigEntry(domain="test_platform")
    entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "d1")}, suggested_area="Fills Up"
    )

    findings = await health._check_empty_areas_and_floors()
    assert findings == []
    resolved = health._store.data["misconfig_findings"][finding_id]
    assert resolved["status"] == "resolved"


async def test_no_findings_when_nothing_broken(hass: HomeAssistant, health: IntegrationHealth) -> None:
    # _check_unused_labels_and_blueprints is excluded: the harness config dir ships a real example blueprint.
    checks = (
        health._check_unknown_service_references,
        health._check_unknown_device_references,
        health._check_unknown_area_floor_label_references,
        health._check_notify_group_unknown_members,
        health._check_person_unknown_trackers,
        health._check_group_unknown_members,
        health._check_proximity_unknown_references,
        health._check_lovelace_missing_resources,
        health._check_orphaned_statistics,
        health._check_energy_unknown_references,
        health._check_notify_coverage_gaps,
    )
    for check in checks:
        assert await check() == []


async def test_notify_coverage_gap_severities_split_per_d11(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    """D-11 (work plan item 4.4): an untracked source is LOW, a source the
    operator toggled off is MEDIUM; both still mirror to Repairs."""
    from homeassistant.setup import async_setup_component

    config = [
        {
            "id": "auto1",
            "alias": "Smoke -> Phone",
            "trigger": [{"platform": "state", "entity_id": "binary_sensor.smoke_detector", "to": "on"}],
            "action": [{"service": "notify.mobile_app_test", "data": {"message": "smoke!"}}],
        },
        {
            "id": "auto2",
            "alias": "Lock -> Phone",
            "trigger": [{"platform": "state", "entity_id": "lock.front_door", "to": "unlocked"}],
            "action": [{"service": "notify.mobile_app_test", "data": {"message": "unlocked!"}}],
        },
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    health._store.data["settings"]["security_sources_enabled"]["lock"] = False

    findings = await health._check_notify_coverage_gaps()

    by_id = {f["id"]: f for f in findings}
    assert set(by_id) == {
        "misconfig:notify_coverage_gaps:untracked",
        "misconfig:notify_coverage_gaps:disabled",
    }
    assert by_id["misconfig:notify_coverage_gaps:untracked"]["severity"] == "low"
    assert by_id["misconfig:notify_coverage_gaps:disabled"]["severity"] == "medium"
    for finding in findings:
        assert finding["check"] == "notify_coverage_gaps"
        assert finding["detail"]["total_count"] == len(finding["detail"]["items"])

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert set(by_id) <= issue_ids
