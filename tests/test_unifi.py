"""Tests for the UniFi Network / Protect direct-to-console client.

Two concerns are pinned here:

1. **Defensive normalization.** The exact UniFi field names could not be
   verified against a live controller, so unifi.py resolves each field from a
   list of candidate keys spanning the Integration API (camelCase) and the
   legacy controller API (snake_case). These tests feed BOTH conventions and
   assert the same normalized row comes out either way, and that a genuinely
   absent field degrades to None (never a guess).

2. **The integration-endpoint correlation** — the "I want to know when an
   integration IP fails" feature. A UniFi client whose IP matches a Home
   Assistant config entry in a setup-error/retry state must be flagged
   failing; one matching a loaded entry is healthy; one matching nothing is
   None.

No real network call is ever made — the module-level ``_get`` is patched.
"""
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.ha_soc import unifi
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.unifi import (
    UniFiError,
    _as_epoch,
    _derive_wan,
    _first,
    _hosts_from_value,
    _normalize_client,
    _normalize_device,
    async_network_overview,
    async_protect_status,
)


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_first_picks_first_present_nonempty() -> None:
    obj = {"a": None, "b": "", "c": "value", "d": "other"}
    assert _first(obj, "a", "b", "c", "d") == "value"
    assert _first(obj, "a", "b", default="fallback") == "fallback"
    assert _first({}, "x", default=None) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("10.0.0.5", ["10.0.0.5"]),
        ("10.0.0.5:443", ["10.0.0.5"]),
        ("https://10.0.0.5:443/proxy", ["10.0.0.5"]),
        ("HTTP://Host.Local/x", ["host.local"]),
        ("", []),
        (None, []),
        (12345, []),
    ],
)
def test_hosts_from_value(value, expected) -> None:
    assert _hosts_from_value(value) == expected


def test_as_epoch_handles_seconds_millis_iso_and_junk() -> None:
    assert _as_epoch(1_690_000_000) == 1_690_000_000
    # 13-digit millis collapses to seconds.
    assert _as_epoch(1_690_000_000_000) == 1_690_000_000
    assert _as_epoch("2026-01-02T03:04:05+00:00") is not None
    assert _as_epoch(None) is None
    assert _as_epoch("not a date") is None


def test_normalize_client_integration_api_camelcase() -> None:
    raw = {
        "name": "phone",
        "ipAddress": "10.0.0.20",
        "macAddress": "AA:BB:CC:00:00:01",
        "type": "WIRELESS",
        "ssid": "HomeWiFi",
        "uptime": 3600,
        "rxBytes": 1000,
        "txBytes": 2000,
        "lastSeen": 1_690_000_000,
    }
    row = _normalize_client(raw, {})
    assert row["name"] == "phone"
    assert row["ipv4"] == "10.0.0.20"
    assert row["mac"] == "aa:bb:cc:00:00:01"  # lowercased
    assert row["ssid"] == "HomeWiFi"
    assert row["wired"] is False
    assert row["uptime"] == 3600
    assert row["bandwidth"] == {"rx_bytes": 1000, "tx_bytes": 2000, "total_bytes": 3000}
    assert row["last_seen"] == 1_690_000_000
    assert row["integration_match"] is None


def test_normalize_client_legacy_snake_case_equivalent() -> None:
    """The legacy field names must yield an equivalent normalized row — the
    whole point of the multi-key resolution."""
    raw = {
        "hostname": "nvr",
        "ip": "10.0.0.50",
        "mac": "aa:bb:cc:00:00:02",
        "vlan": 20,
        "uptime": 7200,
        "rx_bytes": 5,
        "tx_bytes": 7,
        "last_seen": 1_690_000_000,
        "wired": True,
    }
    row = _normalize_client(raw, {})
    assert row["name"] == "nvr"
    assert row["ipv4"] == "10.0.0.50"
    assert row["vlan"] == 20
    assert row["wired"] is True
    assert row["ssid"] is None
    assert row["bandwidth"]["total_bytes"] == 12


def test_normalize_client_absent_fields_degrade_to_none() -> None:
    row = _normalize_client({"macAddress": "aa:bb:cc:dd:ee:ff"}, {})
    # No name -> falls back to the MAC; every optional field is None, never guessed.
    assert row["name"] == "aa:bb:cc:dd:ee:ff"
    assert row["ipv4"] is None
    assert row["ipv6"] is None
    assert row["vlan"] is None
    assert row["ssid"] is None
    assert row["uptime"] is None
    assert row["bandwidth"] is None
    assert row["last_seen"] is None


def test_normalize_device_shares_client_columns_plus_extras() -> None:
    raw = {
        "name": "USW-24",
        "model": "USW-24-PoE",
        "ipAddress": "10.0.0.2",
        "macAddress": "aa:bb:cc:00:00:10",
        "state": "ONLINE",
        "uptime": 100000,
    }
    row = _normalize_device(raw, {})
    # Same column set as a client...
    assert {"name", "ipv4", "ipv6", "mac", "vlan", "ssid", "uptime", "bandwidth", "last_seen"} <= set(row)
    # ...plus device extras.
    assert row["model"] == "USW-24-PoE"
    assert row["state"] == "ONLINE"
    assert row["ssid"] is None  # infra devices have no SSID -> "—" in the UI


def test_derive_wan_from_gateway_uplink() -> None:
    gateway = {
        "name": "UDM",
        "uplink": {
            "rxRateBps": 1_250_000,
            "txRateBps": 625_000,
            "up": True,
            "ip": "1.2.3.4",
            "name": "wan1",
        },
    }
    wan = _derive_wan(gateway)
    assert wan["rx_rate_bps"] == 1_250_000
    assert wan["tx_rate_bps"] == 625_000
    assert wan["up"] is True
    assert wan["ip"] == "1.2.3.4"
    assert wan["port"] == "wan1"


def test_derive_wan_no_gateway_is_all_none() -> None:
    wan = _derive_wan(None)
    assert wan == {
        "port": None,
        "up": None,
        "rx_rate_bps": None,
        "tx_rate_bps": None,
        "ip": None,
    }


# ---------------------------------------------------------------------------
# async_network_overview — configuration, reachability, correlation
# ---------------------------------------------------------------------------


async def test_overview_not_configured(hass: HomeAssistant, store: HaSocData) -> None:
    overview = await async_network_overview(hass, store)
    assert overview["configured"] is False
    assert overview["reachable"] is False
    assert overview["clients"] == []
    assert overview["devices"] == []


async def test_overview_unreachable_reports_error_not_raise(
    hass: HomeAssistant, store: HaSocData
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1", unifi_network_api_key="k")
    with patch.object(
        unifi, "_get", new=AsyncMock(side_effect=UniFiError("boom"))
    ):
        overview = await async_network_overview(hass, store)
    assert overview["configured"] is True
    assert overview["reachable"] is False
    assert overview["error"] == "boom"


def _dispatch_get(clients, devices):
    """Build an AsyncMock side_effect for _get(hass, conn, path)."""

    async def _side_effect(hass, conn, path):
        if path == "/sites":
            return {"data": [{"id": "default", "name": "Default"}]}
        if path.startswith("/sites/default/clients"):
            return {"data": clients}
        if path.startswith("/sites/default/devices"):
            return {"data": devices}
        raise AssertionError(f"unexpected path {path}")

    return _side_effect


async def test_overview_full_snapshot_and_endpoint_correlation(
    hass: HomeAssistant, store: HaSocData
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1", unifi_network_api_key="k")

    # Register two fake integrations that load/unload cleanly, so marking an
    # entry LOADED doesn't drag a real (uninstalled) component into teardown.
    mock_integration(hass, MockModule("acme_cam"))
    mock_integration(hass, MockModule("acme_hub"))

    # A FAILING integration whose device IP (10.0.0.50) is a live client.
    failing = MockConfigEntry(domain="acme_cam", data={"host": "10.0.0.50"}, title="Acme Cam")
    failing.add_to_hass(hass)
    failing.mock_state(hass, ConfigEntryState.SETUP_RETRY)
    # A HEALTHY integration at 10.0.0.60.
    healthy = MockConfigEntry(domain="acme_hub", data={"host": "10.0.0.60"}, title="Acme Hub")
    healthy.add_to_hass(hass)
    healthy.mock_state(hass, ConfigEntryState.LOADED)

    clients = [
        {"name": "phone", "ipAddress": "10.0.0.20", "type": "WIRELESS", "ssid": "HomeWiFi"},
        {"hostname": "nvr", "ip": "10.0.0.50", "mac": "aa:bb:cc:00:00:02", "wired": True},
        {"name": "tablet", "ipAddress": "10.0.0.60", "type": "WIRELESS", "ssid": "Guest"},
    ]
    devices = [
        {
            "name": "UDM",
            "model": "UDM-Pro",
            "type": "gateway",
            "ipAddress": "10.0.0.1",
            "state": "ONLINE",
            "uplink": {"rxRateBps": 1_000_000, "txRateBps": 500_000, "up": True, "name": "wan1"},
        },
        {"name": "USW", "model": "USW-24", "ipAddress": "10.0.0.2", "state": "ONLINE"},
    ]

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_dispatch_get(clients, devices))):
        o = await async_network_overview(hass, store)

    assert o["configured"] is True
    assert o["reachable"] is True
    assert o["status"] == "online"
    assert o["internet_connected"] is True
    assert o["wan"]["rx_rate_bps"] == 1_000_000
    assert o["wan"]["tx_rate_bps"] == 500_000

    assert o["total_client_count"] == 3
    assert o["wireless_client_count"] == 2
    assert o["wired_client_count"] == 1
    assert {s["ssid"]: s["count"] for s in o["clients_per_ssid"]} == {"HomeWiFi": 1, "Guest": 1}
    assert len(o["devices"]) == 2

    by_ip = {c["ipv4"]: c for c in o["clients"]}
    # Failing integration: flagged.
    assert by_ip["10.0.0.50"]["integration_match"]["failing"] is True
    assert by_ip["10.0.0.50"]["integration_match"]["domain"] == "acme_cam"
    # Healthy integration: matched but not failing.
    assert by_ip["10.0.0.60"]["integration_match"]["failing"] is False
    assert by_ip["10.0.0.60"]["integration_match"]["healthy"] is True
    # No integration at this IP.
    assert by_ip["10.0.0.20"]["integration_match"] is None

    assert o["failing_endpoint_count"] == 1


# ---------------------------------------------------------------------------
# Protect
# ---------------------------------------------------------------------------


async def test_protect_not_configured(hass: HomeAssistant, store: HaSocData) -> None:
    out = await async_protect_status(hass, store)
    assert out["configured"] is False
    assert out["reachable"] is False


async def test_protect_status_counts_online_cameras(
    hass: HomeAssistant, store: HaSocData
) -> None:
    store.async_update_settings(unifi_protect_host="10.0.0.1", unifi_protect_api_key="k")
    cameras = {
        "data": [
            {"name": "front", "state": "CONNECTED"},
            {"name": "back", "state": "DISCONNECTED"},
            {"name": "side", "state": "CONNECTED"},
        ]
    }
    with patch.object(unifi, "_get", new=AsyncMock(return_value=cameras)):
        out = await async_protect_status(hass, store)
    assert out["configured"] is True
    assert out["reachable"] is True
    assert out["camera_count"] == 3
    assert out["cameras_online"] == 2
