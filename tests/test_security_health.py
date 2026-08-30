"""Tests for security_health.py — the always-present Security Integrations
Health dashboard data (lock/siren/valve entities + a curated integration
allowlist, both independently toggleable via settings).
"""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.ha_soc import security_health
from custom_components.ha_soc.const import SECURITY_INTEGRATION_DOMAINS
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    s = HaSocData(hass)
    await s.async_load()
    return s


def _make_device_entity(hass: HomeAssistant, domain: str, unique_id: str, device_unique: str):
    entry = MockConfigEntry(domain="test_platform")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={("test", device_unique)}
    )
    reg_entry = er.async_get(hass).async_get_or_create(
        domain, "test_platform", unique_id, device_id=device.id, config_entry=entry
    )
    return device, reg_entry


async def test_no_entities_no_integrations(hass: HomeAssistant, store: HaSocData) -> None:
    overview = await security_health.async_security_overview(hass, store)
    assert overview["entities"] == []
    assert overview["problem_count"] == 0
    assert overview["low_battery_count"] == 0
    # Every known integration domain reported honestly as not installed,
    # never silently omitted.
    assert all(not i["installed"] for i in overview["integrations"])
    assert {i["domain"] for i in overview["integrations"]} == set(SECURITY_INTEGRATION_DOMAINS)


async def test_jammed_lock_is_a_problem(hass: HomeAssistant, store: HaSocData) -> None:
    _device, reg_entry = _make_device_entity(hass, "lock", "lock1", "dev1")
    hass.states.async_set(reg_entry.entity_id, "jammed")

    overview = await security_health.async_security_overview(hass, store)
    rows = [e for e in overview["entities"] if e["entity_id"] == reg_entry.entity_id]
    assert len(rows) == 1
    assert rows[0]["problem"] is True
    assert overview["problem_count"] == 1


async def test_unavailable_valve_is_a_problem(hass: HomeAssistant, store: HaSocData) -> None:
    _device, reg_entry = _make_device_entity(hass, "valve", "valve1", "dev2")
    hass.states.async_set(reg_entry.entity_id, "unavailable")

    overview = await security_health.async_security_overview(hass, store)
    rows = [e for e in overview["entities"] if e["entity_id"] == reg_entry.entity_id]
    assert rows[0]["problem"] is True


async def test_open_valve_is_not_a_problem(hass: HomeAssistant, store: HaSocData) -> None:
    _device, reg_entry = _make_device_entity(hass, "valve", "valve2", "dev3")
    hass.states.async_set(reg_entry.entity_id, "open")

    overview = await security_health.async_security_overview(hass, store)
    rows = [e for e in overview["entities"] if e["entity_id"] == reg_entry.entity_id]
    assert rows[0]["problem"] is False


async def test_battery_sibling_is_found(hass: HomeAssistant, store: HaSocData) -> None:
    device, reg_entry = _make_device_entity(hass, "lock", "lock2", "dev4")
    hass.states.async_set(reg_entry.entity_id, "locked")

    battery_config_entry = MockConfigEntry(domain="test_platform")
    battery_config_entry.add_to_hass(hass)
    battery_entry = er.async_get(hass).async_get_or_create(
        "sensor",
        "test_platform",
        "lock2_battery",
        device_id=device.id,
        original_device_class="battery",
        config_entry=battery_config_entry,
    )
    hass.states.async_set(battery_entry.entity_id, "15")

    overview = await security_health.async_security_overview(hass, store)
    rows = [e for e in overview["entities"] if e["entity_id"] == reg_entry.entity_id]
    assert rows[0]["battery_entity_id"] == battery_entry.entity_id
    assert rows[0]["battery_level"] == 15.0
    assert rows[0]["low_battery"] is True
    assert overview["low_battery_count"] == 1


async def test_missing_lock_state_is_a_problem(hass: HomeAssistant, store: HaSocData) -> None:
    """Work plan item 4.5: a lock registered in the entity registry whose
    integration never loaded it (no state object) is the worst state a
    physical-security entity can be in and must render as a problem, not
    silently vanish from the card."""
    _device, reg_entry = _make_device_entity(hass, "lock", "ghost_lock", "dev_ghost")
    assert hass.states.get(reg_entry.entity_id) is None

    overview = await security_health.async_security_overview(hass, store)
    rows = [e for e in overview["entities"] if e["entity_id"] == reg_entry.entity_id]
    assert len(rows) == 1
    assert rows[0]["problem"] is True
    assert rows[0]["reason"] == "no state (integration not loaded)"
    assert rows[0]["state"] is None
    assert overview["problem_count"] == 1


async def test_disabled_registry_lock_is_not_flagged(hass: HomeAssistant, store: HaSocData) -> None:
    from homeassistant.helpers.entity_registry import RegistryEntryDisabler

    _device, reg_entry = _make_device_entity(hass, "lock", "off_lock", "dev_off")
    er.async_get(hass).async_update_entity(
        reg_entry.entity_id, disabled_by=RegistryEntryDisabler.USER
    )

    overview = await security_health.async_security_overview(hass, store)
    assert all(e["entity_id"] != reg_entry.entity_id for e in overview["entities"])


async def test_disabled_source_excludes_domain(hass: HomeAssistant, store: HaSocData) -> None:
    _device, reg_entry = _make_device_entity(hass, "siren", "siren1", "dev5")
    hass.states.async_set(reg_entry.entity_id, "on")

    store.data["settings"]["security_sources_enabled"]["siren"] = False

    overview = await security_health.async_security_overview(hass, store)
    assert all(e["entity_id"] != reg_entry.entity_id for e in overview["entities"])


async def test_installed_integration_reports_state(hass: HomeAssistant, store: HaSocData) -> None:
    # Deliberately left at its default (not_loaded) state rather than
    # mock_state()'d to LOADED: elkm1 is a real core integration, and
    # forcing a "loaded" state makes hass fixture teardown attempt a real
    # unload, which imports elkm1's actual PyPI dependency (elkm1_lib) —
    # not installed in this test venv, and irrelevant to what's under
    # test here (the state string just passes through unmodified).
    entry = MockConfigEntry(domain="elkm1", title="My Elk Panel")
    entry.add_to_hass(hass)
    assert entry.state is ConfigEntryState.NOT_LOADED

    overview = await security_health.async_security_overview(hass, store)
    elk_rows = [i for i in overview["integrations"] if i["domain"] == "elkm1"]
    assert len(elk_rows) == 1
    assert elk_rows[0]["installed"] is True
    assert elk_rows[0]["state"] == "not_loaded"
    assert elk_rows[0]["title"] == "My Elk Panel"


async def test_disabled_integration_source_is_omitted(hass: HomeAssistant, store: HaSocData) -> None:
    entry = MockConfigEntry(domain="elkm1", title="My Elk Panel")
    entry.add_to_hass(hass)

    store.data["settings"]["security_sources_enabled"]["elkm1"] = False

    overview = await security_health.async_security_overview(hass, store)
    assert all(i["domain"] != "elkm1" for i in overview["integrations"])
