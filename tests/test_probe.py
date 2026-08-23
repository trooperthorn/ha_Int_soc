"""Tests for probe.py — Supervisor/add-on detection and the ingest service.

The test harness never runs under real Supervisor, so is_hassio(hass) is
always False here unless patched — which is itself the first thing worth
proving: this module must degrade honestly (not silently) off Supervisor.
"""
from unittest.mock import patch

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN, PROBE_ADDON_NAME
from custom_components.ha_soc.probe import async_probe_overview
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


async def test_off_supervisor_is_honestly_unavailable(hass: HomeAssistant, store: HaSocData) -> None:
    overview = await async_probe_overview(hass, store)
    assert overview == {
        "supervisor": False,
        "installed": False,
        "running": False,
        "version": None,
        "update_available": False,
        "result": None,
    }


async def test_on_supervisor_addon_not_installed(hass: HomeAssistant, store: HaSocData) -> None:
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value={}),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["supervisor"] is True
    assert overview["installed"] is False
    assert overview["running"] is False


async def test_on_supervisor_addon_installed_and_running(hass: HomeAssistant, store: HaSocData) -> None:
    fake_addons = {
        "local_ha_soc_probe": {
            "name": PROBE_ADDON_NAME,
            "state": "started",
            "version": "1.2.0",
            "update_available": False,
        },
        "core_ssh": {"name": "Terminal & SSH", "state": "started"},
    }
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["supervisor"] is True
    assert overview["installed"] is True
    assert overview["running"] is True
    assert overview["version"] == "1.2.0"


async def test_on_supervisor_addon_installed_but_stopped(hass: HomeAssistant, store: HaSocData) -> None:
    fake_addons = {
        "local_ha_soc_probe": {
            "name": PROBE_ADDON_NAME,
            "state": "stopped",
            "version": "1.2.0",
            "update_available": True,
        },
    }
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["installed"] is True
    assert overview["running"] is False
    assert overview["update_available"] is True


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_ingest_service_stores_result(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "open_ports": [
                {"port": 22, "proto": "tcp", "process": "sshd"},
                {"port": 8123, "proto": "tcp"},
            ],
            "scanner_version": "0.1.0",
        },
        blocking=True,
    )
    result = entry.runtime_data.store.data["host_probe"]
    assert result is not None
    assert result["scanner_version"] == "0.1.0"
    assert result["open_ports"][0]["port"] == 22
    assert result["reported_at"]


async def test_ingest_service_accepts_address_and_interface(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "open_ports": [
                {"port": 8123, "proto": "tcp", "address": "0.0.0.0", "interface": "(all interfaces)"},
                {"port": 22, "proto": "tcp", "address": "192.168.10.5", "interface": "eth0.10"},
                {"port": 5353, "proto": "udp"},  # older report shape, no address/interface at all
            ],
        },
        blocking=True,
    )
    ports = entry.runtime_data.store.data["host_probe"]["open_ports"]
    assert ports[0]["address"] == "0.0.0.0"
    assert ports[0]["interface"] == "(all interfaces)"
    assert ports[1]["address"] == "192.168.10.5"
    assert ports[1]["interface"] == "eth0.10"
    assert ports[2].get("address") is None


async def test_ingest_service_rejects_bad_port(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {"open_ports": [{"port": 999999, "proto": "tcp"}]},
            blocking=True,
        )


async def test_ws_probe_status_returns_overview(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    from unittest.mock import MagicMock

    from custom_components.ha_soc.websocket_api import ws_probe_status

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True)

    ws_probe_status(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["supervisor"] is False
    assert result["installed"] is False
