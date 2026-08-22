"""Tests for entity_remap.py — the Entity ReMap detect/apply engine and the
Spook-inspired broken-reference scan.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import homeassistant.util.yaml as ha_yaml

from custom_components.ha_soc import entity_remap as remap


# -- Pure structure-walker tests (no HA needed) ------------------------------


def test_exact_replace_scalar():
    new_value, count = remap._exact_replace("sensor.old", "sensor.old", "sensor.new")
    assert new_value == "sensor.new"
    assert count == 1


def test_exact_replace_ignores_template_substring():
    template = "{{ states('sensor.old') }}"
    new_value, count = remap._exact_replace(template, "sensor.old", "sensor.new")
    assert new_value == template
    assert count == 0


def test_exact_replace_nested_structure():
    config = {
        "trigger": [{"platform": "state", "entity_id": "sensor.old"}],
        "action": [{"service": "light.turn_on", "target": {"entity_id": ["sensor.old", "sensor.other"]}}],
    }
    new_config, count = remap._exact_replace(config, "sensor.old", "sensor.new")
    assert count == 2
    assert new_config["trigger"][0]["entity_id"] == "sensor.new"
    assert new_config["action"][0]["target"]["entity_id"] == ["sensor.new", "sensor.other"]


def test_mentions_substring_finds_template_reference():
    assert remap._mentions_substring({"value_template": "{{ states('sensor.old') }}"}, "sensor.old")
    assert not remap._mentions_substring({"value_template": "{{ states('sensor.other') }}"}, "sensor.old")


# -- Automation detect + apply ------------------------------------------------


AUTOMATION_YAML = [
    {
        "id": "auto1",
        "alias": "Test Automation",
        "trigger": [{"platform": "state", "entity_id": "sensor.old_name"}],
        "action": [{"service": "light.turn_on", "target": {"entity_id": "sensor.old_name"}}],
    }
]


async def test_find_and_apply_automation_reference(hass: HomeAssistant) -> None:
    ha_yaml.save_yaml(hass.config.path("automations.yaml"), AUTOMATION_YAML)
    assert await async_setup_component(hass, "automation", {"automation": AUTOMATION_YAML})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["automation"]) == 1
    assert report["automation"][0]["editable"] is True

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["automation"] == 1
    assert result["errors"] == []

    on_disk = ha_yaml.load_yaml(hass.config.path("automations.yaml"))
    assert on_disk[0]["trigger"][0]["entity_id"] == "sensor.new_name"
    assert on_disk[0]["action"][0]["target"]["entity_id"] == "sensor.new_name"


async def test_automation_template_only_reference_is_not_editable(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto2",
            "alias": "Templated Automation",
            "trigger": [{"platform": "time", "at": "12:00:00"}],
            "condition": [{"condition": "template", "value_template": "{{ states('sensor.old_name') == 'on' }}"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    ha_yaml.save_yaml(hass.config.path("automations.yaml"), config)
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["automation"]) == 1
    assert report["automation"][0]["editable"] is False
    assert report["automation"][0]["template_only"] is True


# -- Script detect + apply ----------------------------------------------------


SCRIPT_YAML = {
    "test_script": {
        "alias": "Test Script",
        "sequence": [{"service": "light.turn_on", "target": {"entity_id": "sensor.old_name"}}],
    }
}


async def test_find_and_apply_script_reference(hass: HomeAssistant) -> None:
    ha_yaml.save_yaml(hass.config.path("scripts.yaml"), SCRIPT_YAML)
    assert await async_setup_component(hass, "script", {"script": SCRIPT_YAML})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["script"]) == 1

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["script"] == 1

    on_disk = ha_yaml.load_yaml(hass.config.path("scripts.yaml"))
    assert on_disk["test_script"]["sequence"][0]["target"]["entity_id"] == "sensor.new_name"


# -- Scene detect + apply (entity_id is a dict KEY, not a value) -------------


SCENE_YAML = [{"id": "scene1", "name": "Test Scene", "entities": {"sensor.old_name": "on"}}]


async def test_find_and_apply_scene_reference(hass: HomeAssistant) -> None:
    ha_yaml.save_yaml(hass.config.path("scenes.yaml"), SCENE_YAML)
    assert await async_setup_component(hass, "scene", {"scene": SCENE_YAML})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["scene"]) == 1
    assert report["scene"][0]["editable"] is True

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["scene"] == 1

    on_disk = ha_yaml.load_yaml(hass.config.path("scenes.yaml"))
    assert "sensor.new_name" in on_disk[0]["entities"]
    assert "sensor.old_name" not in on_disk[0]["entities"]


# -- Helpers (config-entry-backed) -------------------------------------------


async def test_find_and_apply_scalar_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="derivative", title="My Derivative", options={"source": "sensor.old_name"})
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["helper"]) == 1
    assert report["helper"][0]["id"] == entry.entry_id

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["helper"] == 1
    assert entry.options["source"] == "sensor.new_name"


async def test_find_and_apply_list_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain="min_max", title="My Min Max", options={"entity_ids": ["sensor.old_name", "sensor.other"]}
    )
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["helper"]) == 1

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["helper"] == 1
    assert entry.options["entity_ids"] == ["sensor.new_name", "sensor.other"]


async def test_unmodeled_entry_mention_is_detect_only(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain="template", title="My Template", options={"state": "{{ states('sensor.old_name') }}"}
    )
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["other"]) == 1
    assert report["other"][0]["editable"] is False

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["helper"] == 0
    assert entry.options["state"] == "{{ states('sensor.old_name') }}"


async def test_no_references_produces_empty_report(hass: HomeAssistant) -> None:
    report = await remap.async_find_references(hass, "sensor.nonexistent")
    assert report["total_count"] == 0
    assert report["editable_count"] == 0


# -- Broken-reference scan (Spook-inspired proactive check) -----------------


async def test_scan_finds_broken_automation_reference(hass: HomeAssistant) -> None:
    config = [
        {
            "id": "auto3",
            "alias": "Broken Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.does_not_exist"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    broken = await remap.async_scan_broken_references(hass)
    entity_ids = [b["entity_id"] for b in broken]
    assert "sensor.does_not_exist" in entity_ids


async def test_scan_ignores_live_entity_references(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.alive", "on")
    config = [
        {
            "id": "auto4",
            "alias": "Healthy Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.alive"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    broken = await remap.async_scan_broken_references(hass)
    entity_ids = [b["entity_id"] for b in broken]
    assert "sensor.alive" not in entity_ids


# -- Lovelace dashboards ("Views") -------------------------------------------


class _FakeDashboardConfig:
    def __init__(self, mode: str, config: dict) -> None:
        self.mode = mode
        self._config = config
        self.saved: dict | None = None

    async def async_load(self, force: bool) -> dict:
        return self._config

    async def async_save(self, config: dict) -> None:
        self.saved = config
        self._config = config


async def test_find_and_apply_storage_dashboard_reference(hass: HomeAssistant) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    storage_config = _FakeDashboardConfig(
        "storage",
        {"views": [{"cards": [{"type": "entities", "entities": ["sensor.old_name", "sensor.other"]}]}]},
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: storage_config})

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["dashboard"]) == 1
    assert report["dashboard"][0]["editable"] is True

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["dashboard"] == 1
    assert storage_config.saved["views"][0]["cards"][0]["entities"] == ["sensor.new_name", "sensor.other"]


async def test_yaml_dashboard_reference_is_not_editable(hass: HomeAssistant) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    yaml_config = _FakeDashboardConfig(
        "yaml", {"views": [{"cards": [{"type": "entities", "entities": ["sensor.old_name"]}]}]}
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: yaml_config})

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["dashboard"]) == 1
    assert report["dashboard"][0]["editable"] is False
    assert "YAML-mode" in report["dashboard"][0]["reason"]

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name")
    assert result["fixed"]["dashboard"] == 0
    assert yaml_config.saved is None


async def test_scan_finds_broken_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="threshold", title="Broken Threshold", options={"entity_id": "sensor.gone"})
    entry.add_to_hass(hass)

    broken = await remap.async_scan_broken_references(hass)
    entity_ids = [b["entity_id"] for b in broken]
    assert "sensor.gone" in entity_ids
    assert broken[entity_ids.index("sensor.gone")]["referenced_by"][0]["kind"] == "helper"
