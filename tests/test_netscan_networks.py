"""Tests for phase 8 of the network inventory: owner-added routed networks, the
Probe's own refusal rules, and the try-before-add flow.
"""
import asyncio
import importlib.util
import ipaddress
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant.common import MockConfigEntry

from custom_components.ha_soc import websocket_api
from custom_components.ha_soc.const import CONF_NETSCAN_EXTRA_NETWORKS, DOMAIN
from custom_components.ha_soc.netscan import (
    NETSCAN_HOST_SCHEMA,
    async_config_for_probe,
    validate_extra_network,
    validate_extra_networks,
)

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

PROBE_SECRET = "unit-test-probe-secret"
PROBE_NETSCAN = (
    Path(__file__).parents[1] / "ha_soc_probe" / "rootfs" / "usr" / "lib" / "ha_soc" / "netscan.py"
)

REFUSED = [
    "8.8.8.0/24",
    "100.64.0.0/24",
    "169.254.0.0/24",
    "127.0.0.0/24",
    "224.0.0.0/24",
    "192.168.0.0/16",
    "10.0.0.0/21",
    "192.168.1.1/32",
    "172.30.32.0/24",
    "172.30.33.128/25",
    "2001:db8::/64",
    "not a network",
    "",
]


# --------------------------------------------------------------------------
# Validation in the integration
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.168.20.0/24", "192.168.20.0/24"),
        (" 192.168.20.77/24 ", "192.168.20.0/24"),
        ("10.1.0.0/22", "10.1.0.0/22"),
        ("172.16.5.4/30", "172.16.5.4/30"),
    ],
)
def test_private_networks_within_the_size_bounds_are_accepted(value, expected):
    assert validate_extra_network(value) == expected


@pytest.mark.parametrize("value", REFUSED)
def test_everything_else_is_refused_by_the_integration(value):
    with pytest.raises(vol.Invalid):
        validate_extra_network(value)


def test_the_list_is_deduplicated_and_capped():
    assert validate_extra_networks(None) == []
    assert validate_extra_networks(["192.168.20.0/24", "192.168.20.5/24"]) == ["192.168.20.0/24"]
    with pytest.raises(vol.Invalid):
        validate_extra_networks([f"10.0.{index}.0/24" for index in range(9)])
    with pytest.raises(vol.Invalid):
        validate_extra_networks("192.168.20.0/24")


async def test_extra_networks_change_the_generation_only_when_set():
    base = await async_config_for_probe({})
    assert "extra_networks" not in base
    with_network = await async_config_for_probe({CONF_NETSCAN_EXTRA_NETWORKS: ["192.168.20.0/24"]})
    assert with_network["extra_networks"] == ["192.168.20.0/24"]
    assert with_network["generation"] != base["generation"]
    # A stored value that no longer validates is not sent to the Probe.
    broken = await async_config_for_probe({CONF_NETSCAN_EXTRA_NETWORKS: ["8.8.8.0/24"]})
    assert "extra_networks" not in broken


# --------------------------------------------------------------------------
# The Probe's own rules
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def probe_netscan():
    pytest.importorskip("fcntl", reason="the Probe scanner is Linux only")
    sys.path.insert(0, str(PROBE_NETSCAN.parent))
    try:
        spec = importlib.util.spec_from_file_location("ha_soc_probe_netscan_networks", PROBE_NETSCAN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROBE_NETSCAN.parent))
    return module


@pytest.mark.parametrize("value", REFUSED)
def test_probe_refuses_the_same_networks_whatever_the_integration_sent(probe_netscan, value):
    network, reason = probe_netscan._refusal_reason(value, [probe_netscan._SUPERVISOR_NETWORK])
    assert network is None
    assert reason


def test_probe_refuses_a_network_overlapping_a_container_bridge(probe_netscan):
    bridge = ipaddress.ip_network("172.17.0.0/16")
    assert probe_netscan._refusal_reason("172.17.4.0/24", [bridge]) == (None, "overlaps a container network")
    assert probe_netscan._refusal_reason("172.18.4.0/24", [bridge])[0] == ipaddress.ip_network("172.18.4.0/24")


def test_probe_parses_at_most_eight_valid_networks(probe_netscan, monkeypatch):
    monkeypatch.setattr(probe_netscan, "_container_networks", lambda: [probe_netscan._SUPERVISOR_NETWORK])
    raw = '["192.168.20.0/24", "8.8.8.0/24", "192.168.20.0/24", "10.9.0.0/22", 7]'
    assert [str(n) for n in probe_netscan._parse_extra_networks(raw)] == ["192.168.20.0/24", "10.9.0.0/22"]
    many = "[" + ",".join(f'"10.0.{i}.0/24"' for i in range(20)) + "]"
    assert len(probe_netscan._parse_extra_networks(many)) == 8
    assert probe_netscan._parse_extra_networks(None) == []
    assert probe_netscan._parse_extra_networks("not json") == []
    assert probe_netscan._parse_extra_networks('{"a": 1}') == []


@pytest.mark.usefixtures("socket_enabled")
async def test_probe_trial_sweeps_only_the_given_network_and_tags_its_hosts(probe_netscan, monkeypatch):
    async def _serve(_reader, writer):
        writer.close()

    server = await asyncio.start_server(_serve, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    network = ipaddress.ip_network("192.168.20.0/30")
    # The sweep itself is pointed at loopback; what is under test is which
    # networks are asked for and how the hosts found are labelled.
    asked = []

    def _targets(networks, arp):
        asked.append((list(networks), set(arp)))
        return ["127.0.0.1"]

    monkeypatch.setattr(probe_netscan, "_sweep_targets", _targets)
    monkeypatch.setattr(probe_netscan, "_read_arp_table", lambda: pytest.fail("a trial reads no ARP table"))
    monkeypatch.setattr(probe_netscan, "_read_arp_complete", lambda: pytest.fail("a trial reads no ARP table"))
    try:
        hosts = await probe_netscan._run_cycle([port], 4, set(), True, [network], only_extra=True)
    finally:
        server.close()
        await server.wait_closed()
    assert asked == [([network], set())]
    assert [h["ip"] for h in hosts] == ["127.0.0.1"]
    assert "network" not in hosts[0]  # loopback is not inside the trial network

    tagged = {"ip": "192.168.20.1", "open_ports": [], "network": "192.168.20.0/30", "responded": True}
    NETSCAN_HOST_SCHEMA(tagged)


# --------------------------------------------------------------------------
# Try before add
# --------------------------------------------------------------------------


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


def _owner(owner=True):
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=owner, id="owner-id")
    return connection


async def _call(hass, handler, connection, **message):
    getattr(websocket_api, handler)(hass, connection, {"id": 1, **message})
    await hass.async_block_till_done()


async def _poll(hass, supervisor_user) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=Context(user_id=supervisor_user.id),
    )


async def _ingest(hass, supervisor_user, **payload) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {**payload, "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=supervisor_user.id),
    )


@pytest.mark.parametrize(
    "handler", ["ws_netscan_network_try", "ws_netscan_network_add", "ws_netscan_network_remove"]
)
async def test_network_commands_require_owner(hass: HomeAssistant, supervisor_entry, handler) -> None:
    with pytest.raises(Unauthorized):
        getattr(websocket_api, handler)(hass, _owner(False), {"id": 1, "network": "192.168.20.0/24"})


async def test_a_network_cannot_be_added_without_a_completed_trial(
    hass: HomeAssistant, supervisor_entry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    await _ingest(hass, supervisor_user, netscan_result=[])  # pins the Probe secret

    connection = _owner()
    await _call(hass, "ws_netscan_network_add", connection, network="192.168.20.0/24")
    assert connection.send_error.call_args.args[1] == "trial_required"

    connection = _owner()
    await _call(hass, "ws_netscan_network_try", connection, network="8.8.8.0/24")
    assert connection.send_error.call_args.args[1] == "invalid_network"
    assert runtime.inventory.trial is None

    with patch.object(runtime.audit, "async_log") as audit_log:
        connection = _owner()
        await _call(hass, "ws_netscan_network_try", connection, network="192.168.20.9/24")
    trial = connection.send_result.call_args.args[1]["trial"]
    assert trial["network"] == "192.168.20.0/24"
    audit_log.assert_called_once_with(
        "user_updated",
        user_id="owner-id",
        detail={"action": "netscan_network_trial", "network": "192.168.20.0/24"},
    )

    # Requested but not yet swept: still not addable, and offered to the Probe.
    connection = _owner()
    await _call(hass, "ws_netscan_network_add", connection, network="192.168.20.0/24")
    assert connection.send_error.call_args.args[1] == "trial_required"
    assert (await _poll(hass, supervisor_user))["trial"] == {"id": trial["id"], "network": "192.168.20.0/24"}

    # An answer for some other trial is ignored.
    await _ingest(hass, supervisor_user, netscan_trial={"id": "someone-else", "network": "192.168.20.0/24", "hosts": []})
    assert runtime.inventory.trial["completed_at"] is None

    await _ingest(
        hass,
        supervisor_user,
        netscan_trial={
            "id": trial["id"],
            "network": "192.168.20.0/24",
            "refused": None,
            "hosts": [{"ip": "192.168.20.5", "open_ports": [{"port": 80}], "network": "192.168.20.0/24"}],
        },
    )
    assert runtime.inventory.trial["hosts"] == [{"ip": "192.168.20.5", "open_ports": [80]}]
    assert "trial" not in await _poll(hass, supervisor_user)
    # Nothing from the trial is stored or recorded as a device.
    assert runtime.store.data["netscan_result"]["hosts"] == []
    assert runtime.inventory.state["devices"] == {}
    assert runtime.store.settings.get(CONF_NETSCAN_EXTRA_NETWORKS) == []

    with patch.object(runtime.audit, "async_log") as audit_log:
        connection = _owner()
        await _call(hass, "ws_netscan_network_add", connection, network="192.168.20.0/24")
    assert connection.send_result.call_args.args[1] == {"ok": True, "extra_networks": ["192.168.20.0/24"]}
    assert audit_log.call_args.kwargs["detail"] == {"action": "netscan_network_added", "network": "192.168.20.0/24"}
    assert (await _poll(hass, supervisor_user))["extra_networks"] == ["192.168.20.0/24"]

    # A trial of one network does not let a different one in.
    connection = _owner()
    await _call(hass, "ws_netscan_network_add", connection, network="192.168.30.0/24")
    assert connection.send_error.call_args.args[1] == "trial_required"


async def test_a_trial_the_probe_refused_cannot_be_added(
    hass: HomeAssistant, supervisor_entry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    await _ingest(hass, supervisor_user, netscan_result=[])
    connection = _owner()
    await _call(hass, "ws_netscan_network_try", connection, network="172.17.4.0/24")
    trial = runtime.inventory.trial
    await _ingest(
        hass,
        supervisor_user,
        netscan_trial={"id": trial["id"], "network": "172.17.4.0/24", "refused": "overlaps a container network", "hosts": []},
    )
    connection = _owner()
    await _call(hass, "ws_netscan_network_add", connection, network="172.17.4.0/24")
    assert connection.send_error.call_args.args[1] == "trial_required"


async def test_status_says_which_networks_were_swept_and_removal_is_audited(
    hass: HomeAssistant, supervisor_entry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    runtime.store.async_update_settings(
        **{CONF_NETSCAN_EXTRA_NETWORKS: ["192.168.20.0/24", "192.168.30.0/24"]}
    )
    host = {"ip": "192.168.20.5", "open_ports": [], "network": "192.168.20.0/24", "responded": True}

    await _ingest(hass, supervisor_user, netscan_result=[host])
    connection = _owner()
    await _call(hass, "ws_netscan_status", connection)
    assert connection.send_result.call_args.args[1]["extra_networks"] == [
        {"network": "192.168.20.0/24", "swept": None, "hosts": 1},
        {"network": "192.168.30.0/24", "swept": None, "hosts": 0},
    ]

    await _ingest(hass, supervisor_user, netscan_result=[host], netscan_networks=["192.168.20.0/24"])
    connection = _owner()
    await _call(hass, "ws_netscan_status", connection)
    assert [n["swept"] for n in connection.send_result.call_args.args[1]["extra_networks"]] == [True, False]

    with patch.object(runtime.audit, "async_log") as audit_log:
        connection = _owner()
        await _call(hass, "ws_netscan_network_remove", connection, network="192.168.30.0/24")
        await _call(hass, "ws_netscan_network_remove", connection, network="192.168.30.0/24")
    assert runtime.store.settings[CONF_NETSCAN_EXTRA_NETWORKS] == ["192.168.20.0/24"]
    assert audit_log.call_count == 1
    assert connection.send_error.call_args.args[1] == "not_found"


async def test_host_on_an_added_network_is_recorded_by_address_with_its_network(
    hass: HomeAssistant, supervisor_entry, supervisor_user
) -> None:
    host = {"ip": "192.168.20.5", "open_ports": [{"port": 80}], "network": "192.168.20.0/24"}
    await _ingest(hass, supervisor_user, netscan_result=[host])
    await _ingest(hass, supervisor_user, netscan_result=[host])
    devices = list(supervisor_entry.runtime_data.inventory.state["devices"].values())
    assert [(d["identity"], d["addresses"][0]["ip"], d["addresses"][0]["network"]) for d in devices] == [
        ("address", "192.168.20.5", "192.168.20.0/24")
    ]
