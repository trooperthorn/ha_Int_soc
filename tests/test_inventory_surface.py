"""Tests for phase 9 of the network inventory: opt-in bus events, the four count
sensors, and the two blueprints.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import parse_yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_capture_events

from custom_components.ha_soc.const import (
    CONF_NETWORK_EVENTS_ENABLED,
    CONF_NETWORK_EVENTS_INCLUDE_ADDRESSES,
    DOMAIN,
    EVENT_NETWORK_DEVICE_BACK,
    EVENT_NETWORK_DEVICE_DOWN,
    EVENT_NETWORK_DEVICE_NEW,
)

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

CYCLE = timedelta(minutes=5)
MAC_A = "00:11:22:33:44:55"
MAC_B = "00:11:22:33:44:66"
MAC_C = "00:11:22:33:44:77"
HERE = {"ip": "192.0.2.10", "mac": MAC_A, "arp_after_sweep": True}
OTHER = {"ip": "192.0.2.11", "mac": MAC_B, "arp_after_sweep": True}
BLUEPRINTS = Path(__file__).parents[1] / "blueprints" / "automation" / "ha_soc"
EVENT_TYPES = (EVENT_NETWORK_DEVICE_NEW, EVENT_NETWORK_DEVICE_DOWN, EVENT_NETWORK_DEVICE_BACK)


async def _runtime(hass: HomeAssistant):
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry.runtime_data


def _capture(hass):
    return {event_type: async_capture_events(hass, event_type) for event_type in EVENT_TYPES}


async def _story(hass, runtime):
    """A baseline, a new device after learning, then a watched device going and coming back."""
    inventory = runtime.inventory
    start = datetime.now(timezone.utc) - timedelta(days=3)
    inventory.async_merge_cycle([HERE, OTHER], presence=True, now=start)
    device = next(d for d in inventory.state["devices"].values() if d["macs"] == [MAC_A])
    inventory.async_set_label(device["id"], "Hallway NAS", at=start.isoformat())
    inventory.async_set_watch(device["id"], True, at=start.isoformat())

    later = start + timedelta(days=2)
    newcomer = {"ip": "192.0.2.12", "mac": MAC_C, "arp_after_sweep": True}
    inventory.async_merge_cycle([HERE, OTHER, newcomer], presence=True, now=later)
    for index in range(1, 4):
        inventory.async_merge_cycle([OTHER, newcomer], presence=True, now=later + index * CYCLE)
    inventory.async_merge_cycle([HERE, OTHER, newcomer], presence=True, now=later + 4 * CYCLE)
    await hass.async_block_till_done()
    return device


async def test_no_event_is_fired_unless_the_owner_turned_them_on(hass: HomeAssistant) -> None:
    runtime = await _runtime(hass)
    captured = _capture(hass)
    await _story(hass, runtime)
    assert all(events == [] for events in captured.values())


async def test_events_carry_the_id_and_label_only_by_default(hass: HomeAssistant) -> None:
    runtime = await _runtime(hass)
    runtime.store.async_update_settings(**{CONF_NETWORK_EVENTS_ENABLED: True})
    captured = _capture(hass)
    device = await _story(hass, runtime)

    new = [e.data for e in captured[EVENT_NETWORK_DEVICE_NEW]]
    assert len(new) == 1  # the two baseline devices fire nothing
    assert set(new[0]) == {"device_id", "label"}
    assert new[0]["label"] is None

    assert [e.data for e in captured[EVENT_NETWORK_DEVICE_DOWN]] == [
        {"device_id": device["id"], "label": "Hallway NAS"}
    ]
    assert [e.data for e in captured[EVENT_NETWORK_DEVICE_BACK]] == [
        {"device_id": device["id"], "label": "Hallway NAS", "minutes_away": 5}
    ]
    everything = repr([e.data for events in captured.values() for e in events])
    assert MAC_A not in everything and "192.0.2." not in everything


async def test_addresses_are_added_only_with_the_second_switch(hass: HomeAssistant) -> None:
    runtime = await _runtime(hass)
    runtime.store.async_update_settings(
        **{CONF_NETWORK_EVENTS_ENABLED: True, CONF_NETWORK_EVENTS_INCLUDE_ADDRESSES: True}
    )
    captured = _capture(hass)
    await _story(hass, runtime)
    down = captured[EVENT_NETWORK_DEVICE_DOWN][0].data
    assert (down["mac"], down["ip"]) == (MAC_A, "192.0.2.10")

    # The second switch alone does nothing.
    runtime.store.async_update_settings(**{CONF_NETWORK_EVENTS_ENABLED: False})
    before = len(captured[EVENT_NETWORK_DEVICE_NEW])
    runtime.inventory.async_merge_cycle(
        [HERE, OTHER, {"ip": "192.0.2.13", "mac": "00:11:22:33:44:88"}], presence=True
    )
    await hass.async_block_till_done()
    assert len(captured[EVENT_NETWORK_DEVICE_NEW]) == before


async def test_a_device_the_controller_reports_fires_the_new_event(hass: HomeAssistant) -> None:
    runtime = await _runtime(hass)
    runtime.store.async_update_settings(**{CONF_NETWORK_EVENTS_ENABLED: True})
    runtime.inventory.state["meta"]["learning_started_at"] = (
        datetime.now(timezone.utc) - timedelta(days=3)
    ).isoformat()
    captured = _capture(hass)
    runtime.inventory.async_merge_unifi_clients([{"mac": MAC_A, "ipv4": "198.51.100.5", "name": "tablet"}])
    await hass.async_block_till_done()
    assert len(captured[EVENT_NETWORK_DEVICE_NEW]) == 1


async def test_count_sensors_follow_the_inventory_and_have_no_attributes(hass: HomeAssistant) -> None:
    runtime = await _runtime(hass)
    names = {
        "known": "sensor.ha_soc_network_devices",
        "unacknowledged": "sensor.ha_soc_unacknowledged_network_devices",
        "watched": "sensor.ha_soc_watched_network_devices",
        "offline": "sensor.ha_soc_watched_network_devices_offline",
    }

    def _values():
        return {key: hass.states.get(entity_id).state for key, entity_id in names.items()}

    assert _values() == {"known": "0", "unacknowledged": "0", "watched": "0", "offline": "0"}

    inventory = runtime.inventory
    now = datetime.now(timezone.utc) - timedelta(hours=1)
    inventory.async_merge_cycle([HERE, OTHER], presence=True, now=now)
    await hass.async_block_till_done()
    assert _values() == {"known": "2", "unacknowledged": "2", "watched": "0", "offline": "0"}

    by_mac = {d["macs"][0]: d for d in inventory.state["devices"].values()}
    inventory.async_set_verdict(by_mac[MAC_A]["id"], "acknowledged", by_user_id=None, at=now.isoformat())
    inventory.async_set_watch(by_mac[MAC_A]["id"], True, at=now.isoformat())
    inventory.async_set_verdict(by_mac[MAC_B]["id"], "ignored", by_user_id=None, at=now.isoformat())
    await hass.async_block_till_done()
    assert _values() == {"known": "1", "unacknowledged": "0", "watched": "1", "offline": "0"}

    for index in range(1, 4):
        inventory.async_merge_cycle([OTHER], presence=True, now=now + index * CYCLE)
    await hass.async_block_till_done()
    assert _values()["offline"] == "1"

    for entity_id in names.values():
        attributes = set(hass.states.get(entity_id).attributes)
        assert attributes <= {"friendly_name", "icon", "state_class"}, attributes


@pytest.mark.parametrize(
    ("name", "event_types"),
    [
        ("network_device_new.yaml", {EVENT_NETWORK_DEVICE_NEW}),
        ("network_device_offline.yaml", {EVENT_NETWORK_DEVICE_DOWN, EVENT_NETWORK_DEVICE_BACK}),
    ],
)
def test_blueprints_parse_and_trigger_on_the_events_the_integration_fires(name, event_types):
    text = (BLUEPRINTS / name).read_text(encoding="utf-8")
    assert "—" not in text
    document = parse_yaml(text)
    blueprint = document["blueprint"]
    assert blueprint["domain"] == "automation"
    assert blueprint["source_url"].endswith(f"/blueprints/automation/ha_soc/{name}")
    assert "notify_device" in blueprint["input"]
    triggers = document["triggers"]
    triggers = triggers if isinstance(triggers, list) else [triggers]
    assert {trigger["event_type"] for trigger in triggers} == event_types
    assert all(trigger["trigger"] == "event" for trigger in triggers)
    # Only fields every event carries are used, never the optional address fields.
    assert "data.mac" not in text and "data.ip" not in text
