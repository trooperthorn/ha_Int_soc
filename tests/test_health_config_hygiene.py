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
    # _check_unused_labels_and_blueprints deliberately excluded: the test
    # harness's own config dir ships a real default example blueprint
    # (homeassistant/*.yaml), so that check correctly reports it as
    # unused here — genuine, correct behavior, not something to assert
    # away as "nothing found".
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
    )
    for check in checks:
        assert await check() == []
