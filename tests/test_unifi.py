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
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.unifi import (
    UniFiError,
    _as_epoch,
    _derive_wan,
    _first,
    _hosts_from_value,
    _normalize_acl_rule,
    _normalize_camera,
    _normalize_client,
    _normalize_device,
    _normalize_event,
    async_network_overview,
    async_protect_status,
)


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


@pytest.fixture
async def secrets(hass: HomeAssistant) -> HaSocSecretStore:
    # The UniFi API keys live in the private secret store since SEC-1;
    # the overview/status functions fetch them from it at use time.
    data = HaSocSecretStore(hass)
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


def test_normalize_device_fields() -> None:
    raw = {
        "name": "USW-24",
        "model": "USW-24-PoE",
        "ipAddress": "10.0.0.2",
        "macAddress": "aa:bb:cc:00:00:10",
        "state": "ONLINE",
        "firmwareUpdatable": True,
        "lastHeartbeatAt": 1_690_000_000,
        "statistics": {"uplink": {"rxBytes": 10, "txBytes": 5}},
    }
    row = _normalize_device(raw, {})
    assert row["model"] == "USW-24-PoE"
    assert row["state"] == "ONLINE"
    assert row["ssid"] is None  # infra devices have no SSID
    # Uptime replaced by firmware_updatable; last-seen + bandwidth from detail.
    assert "uptime" not in row
    assert row["firmware_updatable"] is True
    assert row["last_seen"] == 1_690_000_000
    assert row["bandwidth"] == {"rx_bytes": 10, "tx_bytes": 5, "total_bytes": 15}


def test_normalize_device_firmware_from_nested() -> None:
    row = _normalize_device({"id": "d", "firmware": {"updatable": False}}, {})
    assert row["firmware_updatable"] is False
    assert _normalize_device({"id": "d"}, {})["firmware_updatable"] is None


def test_client_ssid_join_via_broadcast_map() -> None:
    """A wireless client with only a broadcast reference resolves its SSID
    name through the /wifi/broadcasts map."""
    bmap = {"bcast-1": "HomeWiFi", "bcast-2": "Guest"}
    raw = {"name": "phone", "type": "WIRELESS", "wifiBroadcastId": "bcast-2"}
    row = _normalize_client(raw, {}, bmap)
    assert row["ssid"] == "Guest"
    assert row["wired"] is False


def test_client_uptime_derived_from_connected_at() -> None:
    now = 1_690_000_000
    raw = {"name": "x", "connectedAt": now - 3600}
    row = _normalize_client(raw, {}, {}, now)
    assert row["uptime"] == 3600


def test_client_vlan_from_nested_access() -> None:
    row = _normalize_client({"name": "x", "access": {"vlanId": 42}}, {})
    assert row["vlan"] == 42


def test_client_bandwidth_from_statistics() -> None:
    row = _normalize_client({"name": "x", "statistics": {"rxBytes": 100, "txBytes": 50}}, {})
    assert row["bandwidth"] == {"rx_bytes": 100, "tx_bytes": 50, "total_bytes": 150}


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


async def test_overview_not_configured(hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore) -> None:
    overview = await async_network_overview(hass, store, secrets)
    assert overview["configured"] is False
    assert overview["reachable"] is False
    assert overview["clients"] == []
    assert overview["devices"] == []


async def test_overview_unreachable_reports_error_not_raise(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")
    with patch.object(
        unifi, "_get", new=AsyncMock(side_effect=UniFiError("boom"))
    ):
        overview = await async_network_overview(hass, store, secrets)
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
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

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
        o = await async_network_overview(hass, store, secrets)

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
# SSID join + ACL audit report (end to end through the overview)
# ---------------------------------------------------------------------------


def test_normalize_acl_rule_resolves_networks_and_order() -> None:
    nm = {"n1": "IoT (VLAN 30)", "n2": "Guest (VLAN 40)"}
    raw = {
        "name": "Block IoT to LAN",
        "action": "DENY",
        "enabled": True,
        "ruleIndex": 3,
        "networkIds": ["n1", "n2"],
        "direction": "in",
        "protocol": "tcp",
    }
    row = _normalize_acl_rule(raw, 0, nm)
    assert row["order"] == 3
    assert row["name"] == "Block IoT to LAN"
    assert row["action"] == "DENY"
    assert row["enabled"] is True
    assert row["networks"] == ["IoT (VLAN 30)", "Guest (VLAN 40)"]
    assert row["direction"] == "in"
    assert row["protocol"] == "tcp"


async def test_overview_ssid_join_and_acl_report(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

    clients = [{"name": "phone", "type": "WIRELESS", "wifiBroadcastId": "b1"}]
    broadcasts = [{"id": "b1", "name": "HomeWiFi"}]
    networks = [{"id": "n1", "name": "LAN", "vlan": 1}]
    acl = [{"name": "Block IoT", "action": "deny", "networkIds": ["n1"], "enabled": True, "ruleIndex": 0}]

    async def _se(hass, conn, path):
        base = path.split("?", 1)[0]
        if base == "/sites":
            return {"data": [{"id": "default"}]}
        if base == "/sites/default/clients":
            return {"data": clients}
        if base == "/sites/default/devices":
            return {"data": []}
        if base == "/sites/default/wifi/broadcasts":
            return {"data": broadcasts}
        if base == "/sites/default/networks":
            return {"data": networks}
        if base == "/sites/default/acl-rules":
            return {"data": acl}
        raise UniFiError("Endpoint not found")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_se)):
        o = await async_network_overview(hass, store, secrets)

    # SSID resolved through the broadcast map.
    assert o["clients"][0]["ssid"] == "HomeWiFi"
    assert {s["ssid"]: s["count"] for s in o["clients_per_ssid"]} == {"HomeWiFi": 1}

    # ACL report populated, order-preserved, network name resolved.
    assert o["acl"]["available"] is True
    assert o["acl"]["endpoint"] == "acl-rules"
    rule = o["acl"]["rules"][0]
    assert rule["name"] == "Block IoT"
    assert rule["action"] == "deny"
    assert rule["networks"] == ["LAN (VLAN 1)"]


async def test_overview_acl_unavailable_when_no_endpoint(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

    async def _se(hass, conn, path):
        base = path.split("?", 1)[0]
        if base == "/sites":
            return {"data": [{"id": "default"}]}
        if base in ("/sites/default/clients", "/sites/default/devices"):
            return {"data": []}
        raise UniFiError("Endpoint not found")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_se)):
        o = await async_network_overview(hass, store, secrets)

    assert o["acl"]["available"] is False
    assert o["acl"]["endpoints_tried"]  # lists what was probed, for the audit


# ---------------------------------------------------------------------------
# Protect
# ---------------------------------------------------------------------------


async def test_protect_not_configured(hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore) -> None:
    out = await async_protect_status(hass, store, secrets)
    assert out["configured"] is False
    assert out["reachable"] is False


def _dispatch_protect(cameras, events):
    async def _side_effect(hass, conn, path):
        if path.startswith("/cameras"):
            return {"data": cameras}
        if path.startswith("/events"):
            return {"data": events}
        raise AssertionError(f"unexpected path {path}")

    return _side_effect


async def test_protect_status_counts_online_cameras(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_protect_host="10.0.0.1")
    await secrets.async_set("unifi_protect_api_key", "k")
    cameras = [
        {"name": "front", "state": "CONNECTED"},
        {"name": "back", "state": "DISCONNECTED"},
        {"name": "side", "state": "CONNECTED"},
    ]
    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_dispatch_protect(cameras, []))):
        out = await async_protect_status(hass, store, secrets)
    assert out["configured"] is True
    assert out["reachable"] is True
    assert out["camera_count"] == 3
    assert out["cameras_online"] == 2
    assert out["host"] == "https://10.0.0.1"


async def test_protect_camera_deep_link_and_fields(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_protect_host="192.168.30.2")
    await secrets.async_set("unifi_protect_api_key", "k")
    cameras = [
        {
            "id": "68ebc36300ac5703e40232d0",
            "name": "Front Door",
            "ip": "192.168.30.50",
            "mac": "AA:BB:CC:11:22:33",
            "isRecording": True,
            "lastRing": 1_690_000_000,
            "channels": [{"name": "High", "width": 3840, "height": 2160}, {"name": "Low"}],
            "state": "CONNECTED",
        }
    ]
    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_dispatch_protect(cameras, []))):
        out = await async_protect_status(hass, store, secrets)

    cam = out["cameras"][0]
    # The exact deep-link format the user asked for.
    assert cam["link"] == "https://192.168.30.2/protect/dashboard/devices/68ebc36300ac5703e40232d0"
    assert cam["ip"] == "192.168.30.50"
    assert cam["mac"] == "aa:bb:cc:11:22:33"
    assert cam["is_recording"] is True
    assert cam["last_ring"] == 1_690_000_000
    assert cam["channel_count"] == 2
    assert cam["channels"] == ["High", "Low"]


def test_normalize_camera_recording_from_mode() -> None:
    """isRecording derived from recordingSettings.mode when no boolean field."""
    on = _normalize_camera({"id": "x", "recordingSettings": {"mode": "always"}}, "https://h")
    off = _normalize_camera({"id": "y", "recordingSettings": {"mode": "never"}}, "https://h")
    unknown = _normalize_camera({"id": "z"}, "https://h")
    assert on["is_recording"] is True
    assert off["is_recording"] is False
    assert unknown["is_recording"] is None


def test_normalize_event_smart_detection_and_plate() -> None:
    raw = {
        "id": "ev1",
        "type": "smartDetectZone",
        "smartDetectTypes": ["vehicle", "licensePlate"],
        "score": 92,
        "start": 1_690_000_000,
        "end": 1_690_000_012,
        "camera": "cam1",
        "thumbnail": "thumbtoken",
        "metadata": {"licensePlate": {"name": "ABC1234"}},
    }
    row = _normalize_event(raw, "https://192.168.30.2")
    assert row["type"] == "smartDetectZone"
    assert row["smart_detect_types"] == ["vehicle", "licensePlate"]
    assert row["score"] == 92
    assert row["duration"] == 12
    assert row["license_plate"] == "ABC1234"
    assert row["thumbnail"] is True
    # A token (not a URL) links to the camera's console page.
    assert row["thumbnail_link"] == "https://192.168.30.2/protect/dashboard/devices/cam1"


async def test_protect_events_error_still_returns_cameras(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    """A failing events call must not wipe out the cameras table."""
    store.async_update_settings(unifi_protect_host="10.0.0.1")
    await secrets.async_set("unifi_protect_api_key", "k")

    async def _side_effect(hass, conn, path):
        if path.startswith("/cameras"):
            return {"data": [{"id": "c1", "name": "cam", "state": "CONNECTED"}]}
        raise UniFiError("events endpoint not found")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_side_effect)):
        out = await async_protect_status(hass, store, secrets)

    assert out["reachable"] is True
    assert out["camera_count"] == 1
    assert out["events"] == []
    # A "not found" on every candidate degrades to the friendly explanation.
    assert out["events_error"] is not None
    assert "REST events list" in out["events_error"]


# ---------------------------------------------------------------------------
# SEC-3: the short-lived connection object must never print its key
# ---------------------------------------------------------------------------


def test_unifi_conn_repr_masks_key() -> None:
    """_Conn is built fresh per snapshot and dropped after it, but while it
    exists a stray repr()/str() (log line, debugger, traceback locals) must
    not print the API key."""
    from custom_components.ha_soc.unifi import _Conn

    conn = _Conn(
        host="10.0.0.1",
        api_key="SUPERSECRETKEY",
        verify_ssl=False,
        base_path="/proxy/network/integration/v1",
    )
    for rendered in (repr(conn), str(conn), f"{conn}"):
        assert "SUPERSECRETKEY" not in rendered
        assert "[redacted]" in rendered
    # The useful debugging fields are still there.
    assert "10.0.0.1" in repr(conn)
