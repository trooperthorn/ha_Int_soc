"""Tests for unused_installs.py: integrations on disk with no entry, entries
with no entities or devices, HACS downloads that never load, and dashboard
resources no dashboard references (storage and, when enabled, YAML).
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import MODE_STORAGE, MODE_YAML
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import unused_installs as ui
from custom_components.ha_soc.config_hygiene import HYGIENE_COULD_NOT_EVALUATE
from custom_components.ha_soc.const import DOMAIN


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> None:
    """The harness shares one config directory across tests; files written
    under it would otherwise leak from one test into the next."""
    hass.config.config_dir = str(tmp_path)


def _write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _fake_custom_component(hass: HomeAssistant, domain: str) -> None:
    _write(
        hass.config.path("custom_components", domain, "manifest.json"),
        f'{{"domain": "{domain}", "name": "X", "version": "1.0.0"}}',
    )


class _FakeDashboard:
    def __init__(self, mode: str, config: dict | None, fail: bool = False) -> None:
        self.mode = mode
        self._config = config or {}
        self._fail = fail

    async def async_load(self, force: bool) -> dict:
        if self._fail:
            raise OSError("unreadable")
        return self._config


class _FakeResources:
    loaded = True

    def __init__(self, urls: list[str]) -> None:
        self._urls = urls

    def async_items(self) -> list[dict]:
        return [{"url": u, "type": "module"} for u in self._urls]


def _install_lovelace(hass: HomeAssistant, dashboards: dict, urls: list[str]) -> None:
    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards=dashboards, resources=_FakeResources(urls))


async def test_integration_on_disk_without_entry_is_found(hass: HomeAssistant) -> None:
    _fake_custom_component(hass, "orphan_thing")
    found = await ui.async_integrations_without_entry(hass)
    assert [f["domain"] for f in found] == ["orphan_thing"]


async def test_integration_with_entry_is_not_flagged(hass: HomeAssistant) -> None:
    _fake_custom_component(hass, "orphan_thing")
    MockConfigEntry(domain="orphan_thing").add_to_hass(hass)
    found = await ui.async_integrations_without_entry(hass)
    assert found == []


async def test_integration_loaded_from_yaml_is_not_flagged(hass: HomeAssistant) -> None:
    _fake_custom_component(hass, "yaml_thing")
    hass.config.components.add("yaml_thing")
    found = await ui.async_integrations_without_entry(hass)
    assert found == []


async def test_legacy_platform_integration_is_not_flagged(hass: HomeAssistant) -> None:
    _fake_custom_component(hass, "platform_thing")
    hass.config.components.add("sensor.platform_thing")
    found = await ui.async_integrations_without_entry(hass)
    assert found == []


async def test_no_custom_components_directory_is_empty(hass: HomeAssistant) -> None:
    found = await ui.async_integrations_without_entry(hass)
    assert found == [] and found.status == "empty"


async def test_loaded_entry_without_entities_or_devices_is_found(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, title="Bare")
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    found = await ui.async_entries_without_entities_or_devices(hass)
    assert [f["entry_id"] for f in found] == [entry.entry_id]
    assert found[0]["title"] == "Bare"


async def test_entry_with_an_entity_is_not_flagged(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    er.async_get(hass).async_get_or_create("sensor", DOMAIN, "u1", config_entry=entry)
    found = await ui.async_entries_without_entities_or_devices(hass)
    assert found == []


async def test_entry_with_a_device_only_is_not_flagged(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "dev1")}
    )
    found = await ui.async_entries_without_entities_or_devices(hass)
    assert found == []


async def test_not_loaded_entry_is_not_an_unused_finding(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.SETUP_ERROR)
    found = await ui.async_entries_without_entities_or_devices(hass)
    assert found == []


def _hacs(*rows: dict) -> SimpleNamespace:
    repos = [SimpleNamespace(data=SimpleNamespace(installed=True, **row)) for row in rows]
    return SimpleNamespace(repositories=SimpleNamespace(list_all=repos))


async def test_hacs_absent_evaluates_to_empty(hass: HomeAssistant) -> None:
    found = await ui.async_hacs_not_loaded(hass)
    assert found == [] and found.status == "empty"


async def test_hacs_unreadable_is_could_not_evaluate(hass: HomeAssistant) -> None:
    hass.data["hacs"] = object()
    found = await ui.async_hacs_not_loaded(hass)
    assert found.status == HYGIENE_COULD_NOT_EVALUATE


async def test_hacs_integration_not_set_up_is_found(hass: HomeAssistant) -> None:
    hass.data["hacs"] = _hacs(
        {"full_name": "someone/ha-thing", "category": "integration", "domain": "thing", "file_name": None},
        {"full_name": "someone/ha-soc", "category": "integration", "domain": DOMAIN, "file_name": None},
    )
    MockConfigEntry(domain=DOMAIN).add_to_hass(hass)
    _install_lovelace(hass, {}, [])
    found = await ui.async_hacs_not_loaded(hass)
    assert [f["domain"] for f in found] == ["thing"]


async def test_hacs_plugin_without_resource_is_found(hass: HomeAssistant) -> None:
    hass.data["hacs"] = _hacs(
        {"full_name": "someone/used-card", "category": "plugin", "domain": None, "file_name": "used-card.js"},
        {"full_name": "someone/stale-card", "category": "plugin", "domain": None, "file_name": "stale-card.js"},
    )
    _install_lovelace(hass, {}, ["/hacsfiles/used-card/used-card.js?hacstag=1"])
    found = await ui.async_hacs_not_loaded(hass)
    assert [f["full_name"] for f in found] == ["someone/stale-card"]


async def test_hacs_plugin_without_lovelace_is_could_not_evaluate(hass: HomeAssistant) -> None:
    hass.data["hacs"] = _hacs(
        {"full_name": "someone/stale-card", "category": "plugin", "domain": None, "file_name": "stale-card.js"},
    )
    found = await ui.async_hacs_not_loaded(hass)
    assert found.status == HYGIENE_COULD_NOT_EVALUATE


def test_defined_elements_finds_both_registration_styles(hass: HomeAssistant) -> None:
    path = hass.config.path("www", "community", "x", "x.js")
    _write(
        path,
        'customElements.define("my-card",A);window.customCards=window.customCards||[];'
        'window.customCards.push({type:"my-card-editor",name:"n"});const t={type:"button"};',
    )
    names = ui._defined_elements_sync(path, hass.config.path("www", "community"))
    assert names == {"my-card", "my-card-editor"}


def test_defined_elements_refuses_paths_outside_base(hass: HomeAssistant) -> None:
    path = hass.config.path("secrets.yaml")
    _write(path, "x: 1")
    assert ui._defined_elements_sync(path, hass.config.path("www")) is None


def test_walk_custom_types_reaches_nested_cards() -> None:
    out: set[str] = set()
    ui._walk_custom_types(
        {
            "views": [
                {
                    "cards": [
                        {"type": "custom:outer-card", "cards": [{"type": "custom:inner-card"}]},
                        {"type": "entities", "entities": [{"type": "custom:row-thing", "entity": "x.y"}]},
                    ]
                }
            ]
        },
        out,
    )
    assert out == {"outer-card", "inner-card", "row-thing"}


async def test_unused_resource_is_found_and_used_one_is_not(hass: HomeAssistant) -> None:
    _write(hass.config.path("www", "community", "used", "used.js"), 'customElements.define("used-card",A)')
    _write(hass.config.path("www", "community", "stale", "stale.js"), 'customElements.define("stale-card",B)')
    _write(hass.config.path("www", "mystery.js"), "var a = 1;")
    dashboards = {None: _FakeDashboard(MODE_STORAGE, {"views": [{"cards": [{"type": "custom:used-card"}]}]})}
    _install_lovelace(
        hass,
        dashboards,
        ["/hacsfiles/used/used.js?v=1", "/hacsfiles/stale/stale.js", "/local/mystery.js", "https://cdn.example/x.js"],
    )
    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=False)
    assert [f["url"] for f in found] == ["/hacsfiles/stale/stale.js"]
    assert found[0]["elements"] == ["stale-card"]
    assert [u["url"] for u in found.undeterminable] == ["/local/mystery.js"]


async def test_yaml_dashboard_skipped_makes_check_could_not_evaluate(hass: HomeAssistant) -> None:
    _write(hass.config.path("www", "community", "stale", "stale.js"), 'customElements.define("stale-card",B)')
    dashboards = {
        None: _FakeDashboard(MODE_STORAGE, {}),
        "yaml-dash": _FakeDashboard(MODE_YAML, {"views": [{"cards": [{"type": "custom:stale-card"}]}]}),
    }
    _install_lovelace(hass, dashboards, ["/hacsfiles/stale/stale.js"])

    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=False)
    assert found.status == HYGIENE_COULD_NOT_EVALUATE
    assert found.yaml_dashboards_skipped == 1

    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=True)
    assert found == [] and found.status == "empty"


async def test_unloadable_dashboard_makes_check_could_not_evaluate(hass: HomeAssistant) -> None:
    _write(hass.config.path("www", "community", "stale", "stale.js"), 'customElements.define("stale-card",B)')
    _install_lovelace(hass, {None: _FakeDashboard(MODE_STORAGE, {}, fail=True)}, ["/hacsfiles/stale/stale.js"])
    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=False)
    assert found.status == HYGIENE_COULD_NOT_EVALUATE


async def test_without_lovelace_is_could_not_evaluate(hass: HomeAssistant) -> None:
    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=True)
    assert found.status == HYGIENE_COULD_NOT_EVALUATE


async def test_real_yaml_dashboard_with_include_counts_as_used(hass: HomeAssistant) -> None:
    """The YAML scan goes through core's LovelaceYAML loader, so an !include'd card counts."""
    from homeassistant.components.lovelace.dashboard import LovelaceYAML

    _write(hass.config.path("www", "community", "inc", "inc.js"), 'customElements.define("inc-card",C)')
    _write(hass.config.path("cards", "one.yaml"), "type: custom:inc-card\n")
    _write(hass.config.path("dash.yaml"), "views:\n  - cards:\n      - !include cards/one.yaml\n")
    dashboards = {"dash": LovelaceYAML(hass, "dash", {"filename": "dash.yaml"})}
    _install_lovelace(hass, dashboards, ["/hacsfiles/inc/inc.js"])

    found = await ui.async_unused_dashboard_resources(hass, scan_yaml=True)
    assert found == [] and found.status == "empty"
