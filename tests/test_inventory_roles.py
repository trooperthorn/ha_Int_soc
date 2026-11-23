"""Tests for phase 6 of the network inventory: gateway and DNS roles from the
Supervisor's network information, and the NAT finding from the UniFi WAN address.
"""
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DOMAIN, SIGNAL_UNIFI_WAN
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

MAC_ROUTER = "00:11:22:33:44:01"
MAC_DNS = "00:11:22:33:44:02"

# The documented response of the Supervisor's /network/info, with a second interface.
NETWORK_INFO = {
    "interfaces": [
        {
            "interface": "wlan0",
            "primary": False,
            "connected": True,
            "ipv4": {"gateway": "198.51.100.1", "nameservers": ["198.51.100.53"]},
        },
        {
            "interface": "eth0",
            "primary": True,
            "connected": True,
            "ipv4": {
                "method": "static",
                "address": ["192.0.2.100/24"],
                "gateway": "192.0.2.1",
                "nameservers": ["192.0.2.53", "192.0.2.53", "not-an-address"],
            },
            "ipv6": None,
        },
    ],
    "docker": {"interface": "hassio", "gateway": "172.30.32.1", "dns": "172.30.32.3"},
}


@pytest.mark.parametrize(
    ("address", "kind"),
    [
        ("203.0.113.7", "public"),
        ("192.168.1.2", "private"),
        ("10.9.8.7", "private"),
        ("172.16.0.1", "private"),
        ("172.32.0.1", "public"),
        ("100.64.0.1", "cgnat"),
        ("100.127.255.254", "cgnat"),
        ("100.128.0.1", "public"),
        ("2001:db8::1", None),
        ("0.0.0.0", None),
        ("not an address", None),
        (None, None),
    ],
)
def test_wan_address_kinds(address, kind):
    assert inv.classify_wan_address(address) == kind


def test_host_roles_take_the_primary_interface_and_drop_bad_values():
    assert inv.host_network_roles(NETWORK_INFO) == {"gateway": "192.0.2.1", "dns": ["192.0.2.53"]}


@pytest.mark.parametrize(
    "info",
    [
        None,
        {},
        {"interfaces": "eth0"},
        {"interfaces": [{"interface": "eth0", "primary": True, "connected": False, "ipv4": {"gateway": "192.0.2.1"}}]},
        {"interfaces": [{"interface": "eth0", "primary": True, "connected": True, "ipv4": None}]},
        {"interfaces": [{"interface": "eth0", "connected": True, "ipv4": {"gateway": None, "nameservers": None}}]},
    ],
)
def test_host_roles_read_as_unknown_on_missing_or_malformed_information(info):
    assert inv.host_network_roles(info) == {"gateway": None, "dns": []}


async def _entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


HOSTS = [
    {"ip": "192.0.2.1", "mac": MAC_ROUTER, "open_ports": []},
    {"ip": "192.0.2.53", "mac": MAC_DNS, "open_ports": []},
]


async def test_devices_are_tagged_from_the_supervisor_when_the_probe_sends_no_gateway(
    hass: HomeAssistant,
) -> None:
    inventory = (await _entry(hass)).runtime_data.inventory
    with patch.object(inventory, "_host_roles", return_value=inv.host_network_roles(NETWORK_INFO)):
        inventory.async_merge_cycle(HOSTS)
    overview = inventory.overview()
    roles = {d["macs"][0]: d["roles"] for d in overview["devices"]}
    assert roles == {MAC_ROUTER: ["gateway"], MAC_DNS: ["dns"]}
    assert overview["network"] == {
        "gateway_ip": "192.0.2.1",
        "dns_servers": ["192.0.2.53"],
        "roles_source": "supervisor",
        "wan": None,
    }


async def test_the_probes_gateway_wins_over_the_supervisors(hass: HomeAssistant) -> None:
    inventory = (await _entry(hass)).runtime_data.inventory
    with patch.object(inventory, "_host_roles", return_value=inv.host_network_roles(NETWORK_INFO)):
        inventory.async_merge_cycle(HOSTS, gateway_ip="192.0.2.53")
    overview = inventory.overview()
    assert overview["network"]["roles_source"] == "probe"
    by_mac = {d["macs"][0]: d["roles"] for d in overview["devices"]}
    assert by_mac == {MAC_ROUTER: [], MAC_DNS: ["gateway", "dns"]}


async def test_no_supervisor_means_roles_are_not_known(hass: HomeAssistant) -> None:
    inventory = (await _entry(hass)).runtime_data.inventory
    assert inventory._host_roles() is None
    inventory.async_merge_cycle(HOSTS)
    overview = inventory.overview()
    assert all(d["roles"] == [] for d in overview["devices"])
    assert overview["network"]["gateway_ip"] is None


async def test_wan_signal_records_the_kind_and_never_the_address(hass: HomeAssistant) -> None:
    inventory = (await _entry(hass)).runtime_data.inventory
    async_dispatcher_send(hass, SIGNAL_UNIFI_WAN, "100.64.3.9")
    await hass.async_block_till_done()
    assert inventory.state["meta"]["wan"]["kind"] == "cgnat"
    assert "100.64.3.9" not in repr(inventory.state)
    async_dispatcher_send(hass, SIGNAL_UNIFI_WAN, "garbage")
    await hass.async_block_till_done()
    assert inventory.state["meta"]["wan"]["kind"] == "cgnat"


class _Inventory:
    def __init__(self, wan):
        self.state = inv.empty_state()
        self.state["meta"]["wan"] = wan


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationHealth(hass, store)


@pytest.mark.parametrize(
    ("wan", "title"),
    [
        ({"kind": "private", "at": "2026-11-01T12:00:00+00:00"}, "The gateway is behind another router (double NAT)"),
        ({"kind": "cgnat", "at": "2026-11-01T12:00:00+00:00"}, "The internet provider uses carrier-grade NAT"),
    ],
)
async def test_nat_is_an_informational_finding(hass, health, wan, title) -> None:
    health.inventory = _Inventory(wan)
    findings = await health._check_network_nat()
    assert [(f["id"], f["severity"], f["title"]) for f in findings] == [
        ("misconfig:network_nat", "info", title)
    ]
    assert findings[0]["detail"] == {"kind": wan["kind"], "observed_at": wan["at"]}


@pytest.mark.parametrize("wan", [None, {"kind": "public", "at": "2026-11-01T12:00:00+00:00"}])
async def test_public_or_unknown_wan_is_no_finding(hass, health, wan) -> None:
    health.inventory = _Inventory(wan)
    assert await health._check_network_nat() == []
    health.inventory = None
    assert await health._check_network_nat() == []
