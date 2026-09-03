"""Tests for config_hygiene.py — the Spook-inspired proactive sweep for
reference kinds beyond plain entity_id (service/device/area/floor/label/
alert/notify-group/person/group/proximity/lovelace-resource/registry
tidiness/customize/statistics/energy).
"""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr, label_registry as lr
from homeassistant.setup import async_setup_component

from custom_components.ha_soc import config_hygiene as ch


async def test_unknown_service_reference_is_found(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto1",
            "alias": "Broken Service",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"service": "nonexistent_domain.nonexistent_service", "data": {}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_service_references(hass)
    assert any(f["service"] == "nonexistent_domain.nonexistent_service" for f in found)


async def test_known_service_reference_is_not_flagged(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "persistent_notification", {})
    config = [
        {
            "id": "auto2",
            "alias": "Working Service",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_service_references(hass)
    assert not any(f["service"] == "persistent_notification.create" for f in found)


async def test_unknown_service_found_inside_nested_choose_block(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto3",
            "alias": "Nested",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [
                {
                    "choose": [
                        {
                            "conditions": [],
                            "sequence": [{"service": "ghost_domain.ghost_service", "data": {}}],
                        }
                    ]
                }
            ],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_service_references(hass)
    assert any(f["service"] == "ghost_domain.ghost_service" for f in found)


def test_action_key_in_data_is_not_a_service() -> None:
    """Work plan item 4.6: an ``action:`` key inside a data/data_template/
    variables subtree is service-call PAYLOAD (e.g. a mobile_app
    actionable-notification button), never a service reference."""
    tree = {
        "service": "notify.mobile_app_test",
        "data": {
            "action": "ghost.service",
            "actions": [{"action": "other.ghost"}],
        },
        "data_template": {"service": "template.ghost"},
        "variables": {"action": "var.ghost"},
    }
    refs = list(ch._walk_service_refs(tree))
    assert refs == [("notify", "mobile_app_test")]


async def test_action_in_notify_data_not_reported_as_unknown_service(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, "persistent_notification", {})
    config = [
        {
            "id": "auto_actionable",
            "alias": "Actionable notification",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [
                {
                    "service": "persistent_notification.create",
                    "data": {"message": "hi", "action": "open.door"},
                }
            ],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_service_references(hass)
    assert not any(f["service"] == "open.door" for f in found)


async def test_templated_service_call_is_not_flagged(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto4",
            "alias": "Dynamic",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"service": "{{ 'light.turn_on' }}", "data": {}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    # Should not crash, and should not report the template text itself as
    # a broken "domain.service", it never matches the plain-string shape.
    found = await ch.async_unknown_service_references(hass)
    assert not any("{{" in f["service"] for f in found)


async def test_unknown_device_reference_is_found(hass: HomeAssistant) -> None:
    # A device removed from the registry after the automation loaded leaves a dangling device_id with no HA-native warning.
    entry = MockConfigEntry(domain="test_platform")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={("test", "dev1")})

    config = [
        {
            "id": "auto5",
            "alias": "Device Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"device_id": device.id, "domain": "switch", "type": "turn_on", "entity_id": "switch.x"}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    # Confirm it loaded successfully before deleting the device.
    found_before = await ch.async_unknown_device_references(hass)
    assert not any(f["device_id"] == device.id for f in found_before)

    dr.async_get(hass).async_remove_device(device.id)

    found_after = await ch.async_unknown_device_references(hass)
    assert any(f["device_id"] == device.id for f in found_after)


async def test_unknown_area_reference_is_found(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto6",
            "alias": "Ghost Area",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"service": "light.turn_on", "target": {"area_id": "nonexistent-area"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_area_floor_label_references(hass)
    assert any(f["ref_type"] == "area" and f["ref_id"] == "nonexistent-area" for f in found)


async def test_real_area_reference_is_not_flagged(hass: HomeAssistant) -> None:
    area = ar.async_get(hass).async_get_or_create("Kitchen")
    config = [
        {
            "id": "auto7",
            "alias": "Real Area",
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
            "action": [{"service": "light.turn_on", "target": {"area_id": area.id}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_unknown_area_floor_label_references(hass)
    assert not any(f["ref_id"] == area.id for f in found)


async def test_alert_unknown_entity_and_notifier(hass: HomeAssistant) -> None:
    from unittest.mock import patch

    fake_config = {
        "alert": {
            "broken_alert": {
                "name": "Broken",
                "entity_id": "binary_sensor.nonexistent",
                "notifiers": ["nonexistent_notifier"],
            }
        }
    }
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        found = await ch.async_alert_unknown_references(hass)

    kinds = {(f["alert_id"], f["kind"]) for f in found}
    assert ("broken_alert", "entity") in kinds
    assert ("broken_alert", "notifier") in kinds


async def test_alert_with_real_entity_is_not_flagged(hass: HomeAssistant) -> None:
    from unittest.mock import patch

    hass.states.async_set("binary_sensor.smoke", "off")
    fake_config = {"alert": {"real_alert": {"name": "Real", "entity_id": "binary_sensor.smoke", "notifiers": []}}}
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        found = await ch.async_alert_unknown_references(hass)

    assert not any(f["alert_id"] == "real_alert" for f in found)


async def test_person_unknown_tracker_is_found(hass: HomeAssistant) -> None:
    hass.states.async_set("person.alice", "home", {"device_trackers": ["device_tracker.nonexistent"]})
    found = await ch.async_person_unknown_trackers(hass)
    assert any(f["person"] == "person.alice" and f["ref"] == "device_tracker.nonexistent" for f in found)


async def test_person_real_tracker_is_not_flagged(hass: HomeAssistant) -> None:
    hass.states.async_set("device_tracker.alice_phone", "home")
    hass.states.async_set("person.alice", "home", {"device_trackers": ["device_tracker.alice_phone"]})
    found = await ch.async_person_unknown_trackers(hass)
    assert not any(f["ref"] == "device_tracker.alice_phone" for f in found)


async def test_group_unknown_member_is_found(hass: HomeAssistant) -> None:
    hass.states.async_set("group.all_locks", "locked", {"entity_id": ["lock.nonexistent"]})
    found = await ch.async_group_unknown_members(hass)
    assert any(f["group"] == "group.all_locks" and f["ref"] == "lock.nonexistent" for f in found)


async def test_empty_area_is_found(hass: HomeAssistant) -> None:
    ar.async_get(hass).async_get_or_create("Unused Room")
    result = await ch.async_empty_areas_and_floors(hass)
    assert "Unused Room" in result["areas"]


async def test_area_with_device_is_not_empty(hass: HomeAssistant) -> None:
    area = ar.async_get(hass).async_get_or_create("Used Room")
    entry = MockConfigEntry(domain="test_platform")
    entry.add_to_hass(hass)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", "dev1")}, suggested_area="Used Room"
    )
    result = await ch.async_empty_areas_and_floors(hass)
    assert "Used Room" not in result["areas"]


async def test_empty_floor_is_found(hass: HomeAssistant) -> None:
    fr.async_get(hass).async_create("Unused Floor")
    result = await ch.async_empty_areas_and_floors(hass)
    assert "Unused Floor" in result["floors"]


async def test_unknown_customize_entity_is_found(hass: HomeAssistant) -> None:
    from unittest.mock import patch

    fake_config = {"homeassistant": {"customize": {"light.nonexistent": {"friendly_name": "Ghost"}}}}
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        found = await ch.async_unknown_customize_entities(hass)

    assert "light.nonexistent" in found


async def test_customize_for_real_entity_is_not_flagged(hass: HomeAssistant) -> None:
    from unittest.mock import patch

    hass.states.async_set("light.kitchen", "on")
    fake_config = {"homeassistant": {"customize": {"light.kitchen": {"friendly_name": "Kitchen"}}}}
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        found = await ch.async_unknown_customize_entities(hass)

    assert "light.kitchen" not in found


async def test_orphaned_statistics_returns_empty_without_recorder(hass: HomeAssistant) -> None:
    found = await ch.async_orphaned_statistics(hass)
    assert found == []


async def test_energy_returns_empty_without_manager(hass: HomeAssistant) -> None:
    found = await ch.async_energy_unknown_references(hass)
    assert found == []


async def test_lovelace_missing_resources_returns_empty_without_lovelace(hass: HomeAssistant) -> None:
    found = await ch.async_lovelace_missing_resources(hass)
    assert found == []


async def test_proximity_returns_empty_without_entries(hass: HomeAssistant) -> None:
    found = await ch.async_proximity_unknown_references(hass)
    assert found == []


async def test_notify_group_returns_empty_without_entries(hass: HomeAssistant) -> None:
    found = await ch.async_notify_group_unknown_members(hass)
    assert found == []


class _FakeStore:
    def __init__(self, security_sources_enabled: dict) -> None:
        self.settings = {"security_sources_enabled": security_sources_enabled}


async def test_notify_automation_triggered_by_untracked_entity_is_flagged(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto1",
            "alias": "Smoke -> Phone",
            "trigger": [{"platform": "state", "entity_id": "binary_sensor.smoke_detector", "to": "on"}],
            "action": [{"service": "notify.mobile_app_test", "data": {"message": "smoke!"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_notify_coverage_gaps(hass, _FakeStore({}))
    assert any(
        f["gap"] == "untracked" and f["trigger_entity_id"] == "binary_sensor.smoke_detector" for f in found
    )


async def test_notify_automation_triggered_by_disabled_tracked_source_is_flagged(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto2",
            "alias": "Lock -> Phone",
            "trigger": [{"platform": "state", "entity_id": "lock.front_door", "to": "unlocked"}],
            "action": [{"service": "notify.mobile_app_test", "data": {"message": "unlocked!"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_notify_coverage_gaps(hass, _FakeStore({"lock": False}))
    assert any(f["gap"] == "disabled" and f["tracked_as"] == "lock" for f in found)


async def test_notify_automation_triggered_by_enabled_tracked_source_is_not_flagged(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto3",
            "alias": "Lock -> Phone",
            "trigger": [{"platform": "state", "entity_id": "lock.front_door", "to": "unlocked"}],
            "action": [{"service": "notify.mobile_app_test", "data": {"message": "unlocked!"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_notify_coverage_gaps(hass, _FakeStore({"lock": True}))
    assert found == []


async def test_automation_without_notify_action_is_ignored(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto4",
            "alias": "Smoke -> Light",
            "trigger": [{"platform": "state", "entity_id": "binary_sensor.smoke_detector", "to": "on"}],
            "action": [{"service": "light.turn_on", "data": {}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    found = await ch.async_notify_coverage_gaps(hass, _FakeStore({}))
    assert found == []


async def test_notify_coverage_gaps_returns_empty_without_automations(hass: HomeAssistant) -> None:
    found = await ch.async_notify_coverage_gaps(hass, _FakeStore({}))
    assert found == []
