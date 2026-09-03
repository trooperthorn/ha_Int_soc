"""Tests for entity_remap.py — the Entity ReMap detect/apply engine and the
Spook-inspired broken-reference scan.
"""
from __future__ import annotations

import json
import os
import re
import stat
import time
from types import SimpleNamespace

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from homeassistant.const import EVENT_CALL_SERVICE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import homeassistant.util.dt as dt_util
import homeassistant.util.yaml as ha_yaml

from custom_components.ha_soc import entity_remap as remap


@pytest.fixture(autouse=True)
async def _flush_delayed_store_writes(hass: HomeAssistant):
    """Fire the config-entry store's delayed save before teardown.

    Updating an entry schedules a delayed Store write; when the test ends
    first, the harness reports it as a lingering timer.
    """
    yield
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=5))
    await hass.async_block_till_done()


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

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
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
            "trigger": [{"platform": "state", "entity_id": "sensor.never_changes"}],
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


async def test_automation_not_in_flat_file_is_not_editable(hass: HomeAssistant) -> None:
    # Deliberately no automations.yaml: the loaded automation lives in a split file this module cannot edit.
    config = [
        {
            "id": "auto_split",
            "alias": "Split File Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.old_name"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["automation"]) == 1
    assert report["automation"][0]["editable"] is False
    assert "split across multiple files" in report["automation"][0]["reason"]
    assert report["editable_count"] == 0

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["automation"] == 0
    assert result["errors"] == []


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

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["script"] == 1

    on_disk = ha_yaml.load_yaml(hass.config.path("scripts.yaml"))
    assert on_disk["test_script"]["sequence"][0]["target"]["entity_id"] == "sensor.new_name"


SCENE_YAML = [{"id": "scene1", "name": "Test Scene", "entities": {"sensor.old_name": "on"}}]


async def test_find_and_apply_scene_reference(hass: HomeAssistant) -> None:
    ha_yaml.save_yaml(hass.config.path("scenes.yaml"), SCENE_YAML)
    assert await async_setup_component(hass, "scene", {"scene": SCENE_YAML})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["scene"]) == 1
    assert report["scene"][0]["editable"] is True

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["scene"] == 1

    on_disk = ha_yaml.load_yaml(hass.config.path("scenes.yaml"))
    assert "sensor.new_name" in on_disk[0]["entities"]
    assert "sensor.old_name" not in on_disk[0]["entities"]


async def test_find_and_apply_scalar_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="derivative", title="My Derivative", options={"source": "sensor.old_name"})
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["helper"]) == 1
    assert report["helper"][0]["id"] == entry.entry_id

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["helper"] == 1
    assert entry.options["source"] == "sensor.new_name"


async def test_find_and_apply_list_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain="min_max", title="My Min Max", options={"entity_ids": ["sensor.old_name", "sensor.other"]}
    )
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["helper"]) == 1

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["helper"] == 1
    assert entry.options["entity_ids"] == ["sensor.new_name", "sensor.other"]


async def test_unmodeled_entry_mention_is_detect_only(hass: HomeAssistant) -> None:
    # The mention must sit under an INTEGRATION_LOCATOR_KEYS key (here "source") to be found at all.
    entry = MockConfigEntry(
        domain="unmodeled_domain", title="My Unmodeled", options={"source": "{{ states('sensor.old_name') }}"}
    )
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["other"]) == 1
    assert report["other"][0]["editable"] is False

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["helper"] == 0
    assert entry.options["source"] == "{{ states('sensor.old_name') }}"


async def test_entity_remap_reads_only_locator_keys(hass: HomeAssistant) -> None:
    # SEC-4: a mention that only exists inside a credential value must
    # never be read, so it produces no report item at all.
    secret_entry = MockConfigEntry(
        domain="some_cloud",
        title="Cloud",
        data={"password": "pw-sensor.old_name-pw"},
        options={"api_key": "sensor.old_name"},
    )
    secret_entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert report["other"] == []
    assert report["total_count"] == 0

    # The same needle under a locator key is still found (behavior parity
    # for locator-shaped values), reading entry.data as well.
    locator_entry = MockConfigEntry(
        domain="other_cloud", title="Cloud 2", data={"source": "{{ states('sensor.old_name') }}"}
    )
    locator_entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert [item["id"] for item in report["other"]] == [locator_entry.entry_id]
    assert report["other"][0]["editable"] is False

    # The moved fallback: a helper domain whose structural field holds a
    # template (not an exact entity_id) no longer short-circuits past the
    # allowlisted substring check, so it is surfaced for manual review.
    helper_entry = MockConfigEntry(
        domain="threshold", title="Templated Threshold", options={"entity_id": "{{ states('sensor.old_name') }}"}
    )
    helper_entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert report["helper"] == []
    other_ids = {item["id"] for item in report["other"]}
    assert helper_entry.entry_id in other_ids
    assert all(item["editable"] is False for item in report["other"])


async def test_no_references_produces_empty_report(hass: HomeAssistant) -> None:
    report = await remap.async_find_references(hass, "sensor.nonexistent")
    assert report["total_count"] == 0
    assert report["editable_count"] == 0


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

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
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

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["dashboard"] == 0
    assert yaml_config.saved is None


async def test_scan_finds_broken_helper_reference(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="threshold", title="Broken Threshold", options={"entity_id": "sensor.gone"})
    entry.add_to_hass(hass)

    broken = await remap.async_scan_broken_references(hass)
    entity_ids = [b["entity_id"] for b in broken]
    assert "sensor.gone" in entity_ids
    assert broken[entity_ids.index("sensor.gone")]["referenced_by"][0]["kind"] == "helper"


async def test_remap_backs_up_dashboard_and_helper(hass: HomeAssistant) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    storage_config = _FakeDashboardConfig(
        "storage",
        {"views": [{"cards": [{"type": "entities", "entities": ["sensor.old_name"]}]}]},
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: storage_config})
    # A complete option set, so the reload core triggers on the options
    # update sets up cleanly instead of leaving a delayed store write.
    derivative_options = {
        "source": "sensor.old_name",
        "round": 2,
        "time_window": {"hours": 0, "minutes": 0, "seconds": 0},
        "unit_time": "h",
    }
    entry = MockConfigEntry(domain="derivative", title="My Derivative", options=derivative_options)
    entry.add_to_hass(hass)

    # A stale backup from an earlier run is pruned at the start of the apply.
    backup_dir = hass.config.path(remap.REMAP_BACKUP_DIR)
    os.makedirs(backup_dir, mode=0o700, exist_ok=True)
    stale = os.path.join(backup_dir, "stale-old.json")
    with open(stale, "w", encoding="utf-8") as file:
        file.write("{}")
    old_time = time.time() - 31 * 24 * 3600
    os.utime(stale, (old_time, old_time))

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["dashboard"] == 1
    assert result["fixed"]["helper"] == 1
    assert result["errors"] == []
    assert not os.path.exists(stale)

    assert stat.S_IMODE(os.stat(backup_dir).st_mode) == 0o700
    backups = result["backups"]
    assert len(backups) == 2
    dashboard_backup = next(p for p in backups if os.path.basename(p).startswith("default-"))
    helper_backup = next(p for p in backups if os.path.basename(p).startswith(entry.entry_id))
    for path in (dashboard_backup, helper_backup):
        assert os.path.dirname(path) == backup_dir
        assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
        # Millisecond stamp (work plan item 4.14): 8 date digits, then a
        # 9-digit HHMMSSmmm block.
        assert re.search(r"-\d{8}T\d{9}\.json$", path)

    with open(dashboard_backup, encoding="utf-8") as file:
        assert json.load(file) == {
            "views": [{"cards": [{"type": "entities", "entities": ["sensor.old_name"]}]}]
        }
    with open(helper_backup, encoding="utf-8") as file:
        snapshot = json.load(file)
    assert snapshot["entry_id"] == entry.entry_id
    assert snapshot["options"] == derivative_options

    # The live objects really did move on while the backups kept the past.
    assert storage_config.saved["views"][0]["cards"][0]["entities"] == ["sensor.new_name"]
    assert entry.options["source"] == "sensor.new_name"


_REFERENCE_TAGGED_AUTOMATIONS = """\
- id: auto_taint
  alias: Tainted Automation
  trigger:
  - platform: state
    entity_id: sensor.old_name
  action:
  - service: persistent_notification.create
    data:
      message: !secret hidden_message
"""

_INCLUDE_TAINTED_AUTOMATIONS = """\
- id: auto_taint
  alias: Tainted Automation
  trigger:
  - platform: state
    entity_id: sensor.old_name
  action: !include actions.yaml
"""


async def _assert_tainted_yaml_refused(hass: HomeAssistant, tainted_text: str) -> None:
    # Tainted file text (!secret or !include) must report "manual edit required" and never be rewritten.
    path = hass.config.path("automations.yaml")
    with open(path, "w", encoding="utf-8") as file:
        file.write(tainted_text)
    config = [
        {
            "id": "auto_taint",
            "alias": "Tainted Automation",
            "trigger": [{"platform": "state", "entity_id": "sensor.old_name"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["automation"]) == 1
    assert report["automation"][0]["editable"] is False
    assert report["automation"][0]["reason"] == "contains !include or !secret; manual edit required"
    assert report["editable_count"] == 0

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["automation"] == 0
    assert result["errors"] == []
    assert result["backups"] == []
    with open(path, encoding="utf-8") as file:
        assert file.read() == tainted_text


async def test_remap_refuses_secret_tagged_yaml(hass: HomeAssistant) -> None:
    await _assert_tainted_yaml_refused(hass, _REFERENCE_TAGGED_AUTOMATIONS)


async def test_remap_refuses_include_tagged_yaml(hass: HomeAssistant) -> None:
    await _assert_tainted_yaml_refused(hass, _INCLUDE_TAINTED_AUTOMATIONS)


async def test_remap_detects_dict_key_reference(hass: HomeAssistant) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    # Pure walker behavior first: keys now count as exact hits, but only
    # for detection; the value walker still ignores them.
    assert remap._contains_exact({"sensor.old_name": "on"}, "sensor.old_name") is True
    assert remap._contains_exact_value({"sensor.old_name": "on"}, "sensor.old_name") is False

    storage_config = _FakeDashboardConfig(
        "storage",
        {"views": [{"cards": [{"type": "custom:map-card", "entities": {"sensor.old_name": {"label": "Old"}}}]}]},
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: storage_config})

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert len(report["dashboard"]) == 1
    item = report["dashboard"][0]
    assert item["editable"] is False
    assert item["template_only"] is True
    assert "dictionary key" in item["reason"]

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["dashboard"] == 0
    assert storage_config.saved is None


async def test_remap_reads_entry_data(hass: HomeAssistant) -> None:
    # Item 1.9: structural helper fields living in entry.data (imported or
    # older entries) are found, rewritten, and scanned, not just options.
    entry = MockConfigEntry(domain="derivative", title="Data Derivative", data={"source": "sensor.old_name"})
    entry.add_to_hass(hass)

    report = await remap.async_find_references(hass, "sensor.old_name")
    assert [item["id"] for item in report["helper"]] == [entry.entry_id]
    assert report["helper"][0]["editable"] is True

    result = await remap.async_apply_remap(hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True)
    assert result["fixed"]["helper"] == 1
    assert entry.data["source"] == "sensor.new_name"

    scan_entry = MockConfigEntry(domain="threshold", title="Data Threshold", data={"entity_id": "sensor.gone"})
    scan_entry.add_to_hass(hass)
    broken = await remap.async_scan_broken_references(hass)
    entity_ids = [b["entity_id"] for b in broken]
    assert "sensor.gone" in entity_ids


async def test_remap_reloads_scripts_and_scenes_once_per_domain(hass: HomeAssistant) -> None:
    # script.reload and scene.reload take an EMPTY schema; the real services run here, so any data would fail.
    scripts = {
        "s_one": {"alias": "One", "sequence": [{"service": "light.turn_on", "target": {"entity_id": "sensor.old_name"}}]},
        "s_two": {"alias": "Two", "sequence": [{"service": "light.turn_on", "target": {"entity_id": "sensor.old_name"}}]},
    }
    scenes = [
        {"id": "sc_one", "name": "Scene One", "entities": {"sensor.old_name": "on"}},
        {"id": "sc_two", "name": "Scene Two", "entities": {"sensor.old_name": "on"}},
    ]
    ha_yaml.save_yaml(hass.config.path("scripts.yaml"), scripts)
    ha_yaml.save_yaml(hass.config.path("scenes.yaml"), scenes)
    assert await async_setup_component(hass, "script", {"script": scripts})
    assert await async_setup_component(hass, "scene", {"scene": scenes})
    await hass.async_block_till_done()

    events = async_capture_events(hass, EVENT_CALL_SERVICE)
    result = await remap.async_apply_remap(
        hass, "sensor.old_name", "sensor.new_name", backup_acknowledged=True
    )
    await hass.async_block_till_done()

    assert result["errors"] == []
    assert result["fixed"]["script"] == 2
    assert result["fixed"]["scene"] == 2
    calls = [(e.data["domain"], e.data["service"]) for e in events]
    assert calls.count(("script", "reload")) == 1
    assert calls.count(("scene", "reload")) == 1
