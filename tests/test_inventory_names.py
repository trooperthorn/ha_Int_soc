"""Tests for phase 7 of the network inventory: names from DHCP discovery, router
trackers and certificate subjects, and which name wins.
"""
import sys
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DOMAIN

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
MAC_A = "00:11:22:33:44:55"
MAC_B = "00:11:22:33:44:66"


def _state():
    state = inv.empty_state()
    inv.merge_cycle(
        state,
        [{"ip": "192.0.2.10", "mac": MAC_A, "open_ports": [{"port": 443}]}],
        T0,
        new_id=lambda: "d_0001",
    )
    return state


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("001122334455", MAC_A),
        ("00-11-22-33-44-55", MAC_A),
        ("00:11:22:33:44:55".upper(), MAC_A),
        ("0011.2233.4455", MAC_A),
        ("00:11:22:33:44", None),
        ("not a mac", None),
        (None, None),
    ],
)
def test_normalize_mac(value, expected):
    assert inv.normalize_mac(value) == expected


def test_passive_names_are_attached_with_their_source():
    state = _state()
    changed = inv.apply_names(
        state,
        [
            {"mac": "001122334455", "name": "hallway-nas", "source": "dhcp"},
            {"mac": MAC_A.upper(), "name": "NAS (router)", "source": "tracker"},
        ],
        T0,
    )
    assert changed is True
    names = {n["source"]: n["value"] for n in state["devices"]["d_0001"]["names"]}
    assert names == {"dhcp": "hallway-nas", "tracker": "NAS (router)"}
    assert inv.apply_names(state, [{"mac": MAC_A, "name": "hallway-nas", "source": "dhcp"}], T0) is False


def test_a_name_never_creates_a_device_and_bad_entries_are_skipped():
    state = _state()
    inv.apply_names(
        state,
        [
            {"mac": MAC_B, "name": "stranger", "source": "dhcp"},
            {"mac": "garbage", "name": "x", "source": "dhcp"},
            {"mac": MAC_A, "name": None, "source": "dhcp"},
            {"mac": MAC_A, "name": "sneaky", "source": "label"},
            {"mac": MAC_A, "name": "sneaky", "source": "ha_registry"},
        ],
        T0,
    )
    assert list(state["devices"]) == ["d_0001"]
    assert state["devices"]["d_0001"]["names"] == []


def test_an_announced_name_is_length_bounded():
    state = _state()
    inv.apply_names(state, [{"mac": MAC_A, "name": "x" * 5000, "source": "dhcp"}], T0)
    assert len(state["devices"]["d_0001"]["names"][0]["value"]) == inv.MAX_NAME_LENGTH


@pytest.mark.parametrize(
    ("subject", "expected"),
    [
        ("CN=nas.example,O=Home", "nas.example"),
        ("O=Home,CN=nas.example", "nas.example"),
        ("CN=Smith\\, John,O=Home", "Smith\\, John"),
        ("O=Home", None),
        (None, None),
    ],
)
def test_certificate_common_name_becomes_a_name(subject, expected):
    state = _state()
    state["certs"]["c1"] = {"sha256": "c1", "subject": subject, "unreadable": False}
    state["devices"]["d_0001"]["ports"]["443"]["cert_sha256"] = "c1"
    inv.apply_names(state, [], T0)
    names = {n["source"]: n["value"] for n in state["devices"]["d_0001"]["names"]}
    assert names.get("cert") == expected


def test_certificate_on_a_closed_port_gives_no_name():
    state = _state()
    state["certs"]["c1"] = {"sha256": "c1", "subject": "CN=nas.example", "unreadable": False}
    state["devices"]["d_0001"]["ports"]["443"].update(cert_sha256="c1", closed_at=T0.isoformat())
    inv.apply_names(state, [], T0)
    assert state["devices"]["d_0001"]["names"] == []


def test_name_precedence_is_label_registry_controller_dhcp_tracker_certificate():
    state = _state()
    device = state["devices"]["d_0001"]
    state["certs"]["c1"] = {"sha256": "c1", "subject": "CN=from-cert", "unreadable": False}
    device["ports"]["443"]["cert_sha256"] = "c1"

    inv.apply_names(state, [], T0)
    assert inv.best_name(device) == {"value": "from-cert", "source": "cert"}
    inv.apply_names(state, [{"mac": MAC_A, "name": "from-tracker", "source": "tracker"}], T0)
    assert inv.best_name(device)["source"] == "tracker"
    inv.apply_names(state, [{"mac": MAC_A, "name": "from-dhcp", "source": "dhcp"}], T0)
    assert inv.best_name(device)["source"] == "dhcp"
    inv.merge_unifi_clients(state, [{"mac": MAC_A, "name": "from-unifi"}], T0)
    assert inv.best_name(device)["source"] == "unifi"
    inv.merge_cycle(
        state,
        [{"ip": "192.0.2.10", "mac": MAC_A}],
        T0,
        registry=lambda mac: {"name": "from-registry", "device_id": "abc"},
    )
    assert inv.best_name(device)["source"] == "ha_registry"
    device["label"] = "Mine"
    assert inv.best_name(device) == {"value": "Mine", "source": "label"}
    assert len(device["names"]) == 5


def _fake_dhcp(discovered):
    """Stand in for core's dhcp integration, whose own dependencies the test environment lacks."""
    module = ModuleType("homeassistant.components.dhcp")
    module.async_discovered_service_info = discovered
    return patch.dict(sys.modules, {"homeassistant.components.dhcp": module})


async def test_cycle_collects_dhcp_and_router_tracker_names(hass: HomeAssistant) -> None:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    inventory = config_entry.runtime_data.inventory

    hass.states.async_set(
        "device_tracker.router_nas",
        "home",
        {"source_type": "router", "mac": MAC_A.upper(), "host_name": "nas-from-router", "ip": "192.0.2.10"},
    )
    hass.states.async_set(
        "device_tracker.phone_gps", "home", {"source_type": "gps", "mac": MAC_B, "host_name": "phone"}
    )
    hass.states.async_set("device_tracker.no_name", "home", {"source_type": "router", "mac": MAC_B})

    names = inventory._passive_names()
    assert names == [{"mac": MAC_A.upper(), "name": "nas-from-router", "source": "tracker"}]

    hass.config.components.add("dhcp")
    discovered = [SimpleNamespace(macaddress="001122334455", hostname="nas-from-dhcp", ip="192.0.2.10")]
    with _fake_dhcp(lambda hass: discovered):
        inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}, {"ip": "192.0.2.11", "mac": MAC_B}])

    by_mac = {d["macs"][0]: d for d in inventory.overview()["devices"]}
    assert by_mac[MAC_A]["display_name"] == {"value": "nas-from-dhcp", "source": "dhcp"}
    assert {n["source"] for n in by_mac[MAC_A]["names"]} == {"dhcp", "tracker"}
    assert by_mac[MAC_B]["names"] == []
    # A name is not a sighting.
    assert by_mac[MAC_A]["sources"] == ["probe_arp"]


async def test_a_failing_dhcp_source_does_not_break_the_cycle(hass: HomeAssistant) -> None:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    inventory = config_entry.runtime_data.inventory
    hass.config.components.add("dhcp")
    def _broken(hass):
        raise RuntimeError

    with _fake_dhcp(_broken):
        outcome = inventory.async_merge_cycle([{"ip": "192.0.2.10", "mac": MAC_A}])
    assert len(outcome.created) == 1
