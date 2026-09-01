"""Tests for the in-memory enrichment from the core unifi / unifiprotect
integrations (unifi_core.py plus the enrichment glue in unifi.py).

Everything the core integrations would hand us is faked with plain
duck-typed objects: attribute-only classes standing in for aiounifi Client /
Device / Wlan and uiprotect Camera / Event, and a handler fake that exposes
only ``.values()`` because the real aiounifi containers are not dicts. No
aiounifi or uiprotect import ever happens (the libraries are not installed
in this venv, which is itself part of what these tests protect).

The enrichment contract under test:

1. Direct-API values win; core memory fills only what is blank. Bandwidth is
   the one API-absent field, so core memory is its primary source.
2. Wireless clients read rx_bytes_r/tx_bytes_r, wired clients read the
   wired-* rate pair.
3. The controller's uptime field is seconds when small and an epoch start
   when large; both directions must come out as seconds.
4. WAN/internet blanks resolve from the gateway device (uplink rates, the
   raw internet flag, WAN monitor availability).
5. An empty /wifi/broadcasts map falls back to the core WLAN inventory.
6. Protect events normalize from bootstrap-shaped data, license plate
   included.
7. Absent or unloaded core entries yield no enrichment and no exception.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from custom_components.ha_soc import unifi, unifi_core
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.unifi import (
    UniFiError,
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
# Duck-typed fakes for the core integrations' in-memory objects
# ---------------------------------------------------------------------------


class FakeHandler:
    """aiounifi handler stand-in: values() only, deliberately not a dict."""

    def __init__(self, items):
        self._items = list(items)

    def values(self):
        return list(self._items)


class EnumName:
    """IntEnum stand-in exposing only .name, like aiounifi DeviceState."""

    def __init__(self, name: str) -> None:
        self.name = name


class EnumValue:
    """String-enum stand-in exposing .value, like uiprotect enums."""

    def __init__(self, value: str) -> None:
        self.value = value


class Obj:
    """Bag of attributes for nested fakes (channels, metadata, groups)."""

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)


class FakeClient:
    def __init__(self, mac, **kw):
        self.mac = mac
        self.name = kw.get("name")
        self.hostname = kw.get("hostname")
        self.ip = kw.get("ip")
        self.essid = kw.get("essid")
        self.is_wired = kw.get("is_wired", False)
        self.uptime = kw.get("uptime")
        self.last_seen = kw.get("last_seen")
        self.rx_bytes_r = kw.get("rx_bytes_r")
        self.tx_bytes_r = kw.get("tx_bytes_r")
        self.wired_rx_bytes_r = kw.get("wired_rx_bytes_r")
        self.wired_tx_bytes_r = kw.get("wired_tx_bytes_r")
        self.raw = kw.get("raw", {})


class FakeDevice:
    def __init__(self, mac, **kw):
        self.mac = mac
        self.name = kw.get("name")
        self.model = kw.get("model")
        self.type = kw.get("type")
        self.ip = kw.get("ip")
        self.version = kw.get("version")
        self.state = kw.get("state")
        self.last_seen = kw.get("last_seen")
        self.upgradable = kw.get("upgradable")
        self.uplink = kw.get("uplink")
        self.uptime_stats = kw.get("uptime_stats")
        self.raw = kw.get("raw", {})


class FakeWlan:
    def __init__(self, wlan_id, name, enabled=True):
        self.id = wlan_id
        self.name = name
        self.enabled = enabled
        # The secret that must never cross into a payload.
        self.x_passphrase = "WLAN-SECRET-PASSPHRASE"


class FakeController:
    def __init__(self, clients=(), devices=(), wlans=()):
        self.clients = FakeHandler(clients)
        self.devices = FakeHandler(devices)
        self.wlans = FakeHandler(wlans)


class FakeHub:
    def __init__(self, api):
        self.api = api


class FakeProtectApi:
    def __init__(self, bootstrap, base_url="https://192.168.30.2"):
        self.bootstrap = bootstrap
        self.base_url = base_url


class FakeProtectData:
    def __init__(self, api):
        self.api = api


def _gateway_device() -> FakeDevice:
    return FakeDevice(
        "aa:bb:cc:00:00:10",
        name="UDM",
        model="UDM-Pro",
        type="ugw",
        ip="10.0.0.1",
        version="4.0.0",
        state=EnumName("CONNECTED"),
        last_seen=1_700_000_000,
        upgradable=False,
        uplink={
            "name": "eth8",
            "ip": "203.0.113.7",
            "up": True,
            "speed": 1000,
            "rx_bytes": 10_000,
            "tx_bytes": 5_000,
            "rx_bytes_r": 1_250_000,
            "tx_bytes_r": 625_000,
        },
        uptime_stats={
            "WAN": {
                "monitors": [
                    {
                        "target": "1.1.1.1",
                        "type": "icmp",
                        "availability": 100.0,
                        "latency_average": 12,
                    }
                ]
            }
        },
        raw={
            "internet": True,
            "network_table": [
                {
                    "_id": "n30",
                    "name": "IoT",
                    "vlan": 30,
                    "vlan_enabled": True,
                    "ip_subnet": "10.0.30.1/24",
                    "purpose": "corporate",
                    "is_guest": False,
                    "enabled": True,
                    "num_sta": 5,
                },
                {
                    "_id": "n1",
                    "name": "LAN",
                    "vlan_enabled": False,
                    "ip_subnet": "10.0.0.1/24",
                    "purpose": "corporate",
                    "is_guest": False,
                    "enabled": True,
                    "num_sta": 12,
                },
            ],
            "x_authkey": "DEVICE-SECRET-AUTHKEY",
            "serial": "SERIAL123",
        },
    )


def _install_core_entry(hass: HomeAssistant, domain: str, runtime) -> MockConfigEntry:
    """A LOADED core-integration config entry carrying fake runtime_data,
    registered under a MockModule so teardown never imports the real
    (uninstalled) component."""
    mock_integration(hass, MockModule(domain))
    entry = MockConfigEntry(domain=domain)
    entry.add_to_hass(hass)
    entry.mock_state(hass, ConfigEntryState.LOADED)
    entry.runtime_data = runtime
    return entry


# ---------------------------------------------------------------------------
# Pure helpers (unifi_core)
# ---------------------------------------------------------------------------


def test_normalize_mac_forms() -> None:
    # Protect style (uppercase, no separators) and Network style (colons)
    # must land on the same normalized form for the MAC join to work.
    assert unifi_core.normalize_mac("AABBCC001122") == "aa:bb:cc:00:11:22"
    assert unifi_core.normalize_mac("aa:bb:cc:00:11:22") == "aa:bb:cc:00:11:22"
    assert unifi_core.normalize_mac("AA-BB-CC-00-11-22") == "aa:bb:cc:00:11:22"
    assert unifi_core.normalize_mac(None) is None
    assert unifi_core.normalize_mac("") is None


def test_uptime_to_seconds_both_directions() -> None:
    now_ts = 1_700_000_000
    # Below the threshold the value already is a duration in seconds.
    assert unifi_core.uptime_to_seconds(3600, now_ts) == 3600
    # At or above the threshold it is the epoch moment the client came up.
    assert unifi_core.uptime_to_seconds(now_ts - 7200, now_ts) == 7200
    assert unifi_core.uptime_to_seconds(None, now_ts) is None
    assert unifi_core.uptime_to_seconds("junk", now_ts) is None
    assert unifi_core.uptime_to_seconds(-5, now_ts) is None


def test_client_bandwidth_wireless_vs_wired_key_choice() -> None:
    wireless = {
        "is_wired": False,
        "rx_bytes_r": 1000.0,
        "tx_bytes_r": 500.0,
        "wired_rx_bytes_r": 1.0,
        "wired_tx_bytes_r": 2.0,
    }
    assert unifi_core.client_bandwidth(wireless) == {
        "rx_bytes": 1000,
        "tx_bytes": 500,
        "total_bytes": 1500,
    }
    wired = {
        "is_wired": True,
        "rx_bytes_r": 1.0,
        "tx_bytes_r": 2.0,
        "wired_rx_bytes_r": 300.0,
        "wired_tx_bytes_r": 100.0,
    }
    assert unifi_core.client_bandwidth(wired) == {
        "rx_bytes": 300,
        "tx_bytes": 100,
        "total_bytes": 400,
    }
    # Wired-bug fallback: a client flagged wired but carrying only the
    # wireless rate pair must still get a value.
    mislabelled = {"is_wired": True, "rx_bytes_r": 42.0, "tx_bytes_r": 7.0}
    assert unifi_core.client_bandwidth(mislabelled)["total_bytes"] == 49
    assert unifi_core.client_bandwidth({"is_wired": False}) is None


def test_resolve_client_vlan_direct_table_and_name_fallback() -> None:
    networks = [
        {"id": "n30", "name": "IoT", "vlan": 30},
        {"id": "n1", "name": "LAN", "vlan": None},
    ]
    # A raw vlan value always wins.
    assert unifi_core.resolve_client_vlan({"vlan": 7}, networks) == 7
    # Resolution by network id, then by network name.
    assert unifi_core.resolve_client_vlan({"network_id": "n30"}, networks) == 30
    assert unifi_core.resolve_client_vlan({"network": "IoT"}, networks) == 30
    # A network without a numeric VLAN resolves to its name, which is still
    # more useful in the table than a blank.
    assert unifi_core.resolve_client_vlan({"network_id": "n1"}, networks) == "LAN"
    assert unifi_core.resolve_client_vlan({"network": "Guest"}, networks) == "Guest"
    assert unifi_core.resolve_client_vlan({}, networks) is None


def test_wan_from_gateway_rates_availability_and_internet() -> None:
    gateway = {
        "internet": True,
        "uplink": {
            "name": "eth8",
            "ip": "203.0.113.7",
            "up": True,
            "rx_bytes_r": 1_250_000,
            "tx_bytes_r": 625_000,
        },
        "uptime_stats": {
            "WAN": {"monitors": [{"target": "1.1.1.1", "availability": 99.5}]}
        },
    }
    wan = unifi_core.wan_from_gateway(gateway)
    assert wan["port"] == "eth8"
    assert wan["ip"] == "203.0.113.7"
    assert wan["rx_rate_bps"] == 1_250_000
    assert wan["tx_rate_bps"] == 625_000
    assert wan["up"] is True
    assert wan["availability"] == 99.5
    assert wan["internet"] is True

    # Without an uplink up flag the internet verdict decides, and without
    # that the WAN probe availability does.
    assert unifi_core.wan_from_gateway({"internet": False})["up"] is False
    only_probe = {
        "uptime_stats": {"WAN": {"monitors": [{"availability": 0.0}]}}
    }
    assert unifi_core.wan_from_gateway(only_probe)["up"] is False


# ---------------------------------------------------------------------------
# Snapshots against a fake hass (no core integration required)
# ---------------------------------------------------------------------------


class FakeConfigEntries:
    def __init__(self, entries_by_domain):
        self._entries = entries_by_domain

    def async_loaded_entries(self, domain):
        return self._entries.get(domain, [])


class FakeHass:
    def __init__(self, entries_by_domain, data=None):
        self.config_entries = FakeConfigEntries(entries_by_domain)
        self.data = data or {}


class FakeEntry:
    def __init__(self, runtime=None):
        # runtime_data is intentionally absent (not None) when not provided,
        # mirroring how HA deletes the attribute on unload.
        if runtime is not None:
            self.runtime_data = runtime


def test_network_snapshot_absent_and_unloaded_entries() -> None:
    # No entries at all.
    snap = unifi_core.network_snapshot(FakeHass({}))
    assert snap["available"] is False
    assert snap["clients"] == {} and snap["devices"] == {}
    # A loaded entry whose runtime_data was deleted must be skipped quietly.
    snap = unifi_core.network_snapshot(FakeHass({"unifi": [FakeEntry()]}))
    assert snap["available"] is False


def test_network_snapshot_collects_and_redacts() -> None:
    wireless_client = FakeClient(
        "AA:BB:CC:00:00:01",
        name="phone",
        ip="10.0.30.20",
        essid="HomeWiFi",
        uptime=3600,
        last_seen=1_700_000_000,
        rx_bytes_r=1000.0,
        tx_bytes_r=500.0,
        raw={"vlan": 30, "x_fingerprint": "CLIENT-SECRET"},
    )
    hub = FakeHub(
        FakeController(
            clients=[wireless_client],
            devices=[_gateway_device()],
            wlans=[FakeWlan("wl1", "HomeWiFi")],
        )
    )
    # The wireless-clients registry marks a wired-flagged MAC as wireless.
    registry = Obj(wireless_clients={"AA:BB:CC:00:00:01"})
    snap = unifi_core.network_snapshot(
        FakeHass({"unifi": [FakeEntry(hub)]}, data={"unifi_wireless_clients": registry})
    )
    assert snap["available"] is True
    client = snap["clients"]["aa:bb:cc:00:00:01"]
    assert client["essid"] == "HomeWiFi"
    assert client["vlan"] == 30
    assert client["is_wired"] is False
    gateway = snap["gateway"]
    assert gateway is not None
    assert gateway["mac"] == "aa:bb:cc:00:00:10"
    assert gateway["state"] == "CONNECTED"
    assert snap["networks"][0]["name"] == "IoT"
    assert snap["wlans"] == [{"id": "wl1", "name": "HomeWiFi", "enabled": True}]
    # Nothing secret may survive the whitelist copy.
    blob = repr(snap)
    assert "SECRET" not in blob
    assert "SERIAL123" not in blob
    assert "x_passphrase" not in blob


def test_protect_snapshot_camera_and_event_with_plate() -> None:
    now = datetime.now(timezone.utc)
    camera = Obj(
        id="cam1",
        name="Front Door",
        host="192.168.30.50",
        mac="AABBCC445566",
        state=EnumValue("CONNECTED"),
        is_connected=True,
        is_recording=True,
        last_ring=now - timedelta(hours=1),
        recording_settings=Obj(mode=EnumValue("always")),
        channels=[Obj(name="High", width=3840, height=2160)],
    )
    event = Obj(
        id="ev1",
        type=EnumValue("smartDetectZone"),
        smart_detect_types=[EnumValue("vehicle"), EnumValue("licensePlate")],
        score=87,
        start=now - timedelta(minutes=10),
        end=now - timedelta(minutes=9),
        camera_id="cam1",
        camera=camera,
        thumbnail_id="e-thumb-1",
        metadata=Obj(
            detected_thumbnails=[Obj(group=Obj(matched_name="ABC1234"))]
        ),
    )
    data = FakeProtectData(
        FakeProtectApi(Obj(cameras={"cam1": camera}, events={"ev1": event}))
    )
    snap = unifi_core.protect_snapshot(FakeHass({"unifiprotect": [FakeEntry(data)]}))
    assert snap["available"] is True
    assert snap["origin"] == "https://192.168.30.2"
    cam = snap["cameras"][0]
    assert cam["id"] == "cam1"
    assert cam["mac"] == "aa:bb:cc:44:55:66"
    assert cam["isRecording"] is True
    assert cam["state"] == "CONNECTED"
    ev = snap["events"][0]
    assert ev["type"] == "smartDetectZone"
    assert ev["smartDetectTypes"] == ["vehicle", "licensePlate"]
    assert ev["camera"] == "cam1"
    assert ev["camera_name"] == "Front Door"
    assert ev["metadata"] == {"licensePlate": {"name": "ABC1234"}}
    assert isinstance(ev["start"], int)


def test_protect_snapshot_absent_entries() -> None:
    snap = unifi_core.protect_snapshot(FakeHass({}))
    assert snap["available"] is False
    assert snap["cameras"] == [] and snap["events"] == []


# ---------------------------------------------------------------------------
# Network overview enrichment (end to end through async_network_overview)
# ---------------------------------------------------------------------------


def _dispatch_get(clients, devices):
    async def _side_effect(hass, conn, path):
        base = path.split("?", 1)[0]
        if base == "/sites":
            return {"data": [{"id": "default"}]}
        if base == "/sites/default/clients":
            return {"data": clients}
        if base == "/sites/default/devices":
            return {"data": devices}
        raise UniFiError("Endpoint not found")

    return _side_effect


async def test_client_enrichment_fills_blanks_and_api_wins(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

    api_clients = [
        # This row already has API values for ssid/vlan/uptime; core memory
        # must not overwrite them. Bandwidth is API-absent so it is filled.
        {
            "macAddress": "AA:BB:CC:00:00:01",
            "name": "phone",
            "type": "WIRELESS",
            "ssid": "ApiWiFi",
            "vlan": 10,
            "uptime": 111,
        },
        # This row is blank everywhere core memory can help.
        {"macAddress": "AA:BB:CC:00:00:02", "name": "cam"},
    ]
    core_clients = [
        FakeClient(
            "aa:bb:cc:00:00:01",
            essid="CoreWiFi",
            uptime=222,
            rx_bytes_r=1000.0,
            tx_bytes_r=500.0,
            raw={"vlan": 99},
        ),
        FakeClient(
            "aa:bb:cc:00:00:02",
            essid="IoT",
            uptime=3600,
            last_seen=1_700_000_000,
            rx_bytes_r=2000.0,
            tx_bytes_r=250.0,
            raw={"vlan": 30},
        ),
    ]
    hub = FakeHub(FakeController(clients=core_clients, devices=[_gateway_device()]))
    _install_core_entry(hass, "unifi", hub)

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_dispatch_get(api_clients, []))):
        o = await async_network_overview(hass, store, secrets)

    by_mac = {c["mac"]: c for c in o["clients"]}
    row1 = by_mac["aa:bb:cc:00:00:01"]
    assert row1["ssid"] == "ApiWiFi"  # API value wins
    assert row1["vlan"] == 10
    assert row1["uptime"] == 111
    assert row1["bandwidth"] == {"rx_bytes": 1000, "tx_bytes": 500, "total_bytes": 1500}
    row2 = by_mac["aa:bb:cc:00:00:02"]
    assert row2["ssid"] == "IoT"
    assert row2["vlan"] == 30
    assert row2["uptime"] == 3600
    assert row2["last_seen"] == 1_700_000_000
    assert row2["bandwidth"] == {"rx_bytes": 2000, "tx_bytes": 250, "total_bytes": 2250}

    # The per-SSID card is recomputed after enrichment resolved row2's SSID.
    assert {s["ssid"]: s["count"] for s in o["clients_per_ssid"]} == {
        "ApiWiFi": 1,
        "IoT": 1,
    }

    # The API device list was empty, so devices and WAN come from core: this
    # is exactly the "Internet - Unknown" / "WAN Bandwidth - Unknown" fix.
    assert o["internet_connected"] is True
    assert o["wan"]["rx_rate_bps"] == 1_250_000
    assert o["wan"]["tx_rate_bps"] == 625_000
    assert o["wan"]["ip"] == "203.0.113.7"
    assert o["wan"]["availability"] == 100.0
    assert o["devices"][0]["origin"] == "core_unifi"


async def test_overview_built_entirely_from_core_when_unconfigured(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    now_ts = int(dt_util.utcnow().timestamp())
    core_clients = [
        FakeClient(
            "aa:bb:cc:00:00:03",
            hostname="printer",
            ip="10.0.30.9",
            is_wired=True,
            # Epoch-style uptime: the quirk conversion must land near 7200s.
            uptime=now_ts - 7200,
            last_seen=now_ts - 30,
            wired_rx_bytes_r=100.0,
            wired_tx_bytes_r=50.0,
            raw={"network_id": "n30"},
        ),
        FakeClient(
            "aa:bb:cc:00:00:04",
            name="phone",
            ip="10.0.30.10",
            essid="HomeWiFi",
            uptime=600,
            rx_bytes_r=10.0,
            tx_bytes_r=20.0,
            raw={"vlan": 30},
        ),
    ]
    hub = FakeHub(
        FakeController(
            clients=core_clients,
            devices=[_gateway_device()],
            wlans=[FakeWlan("wl1", "HomeWiFi")],
        )
    )
    _install_core_entry(hass, "unifi", hub)

    o = await async_network_overview(hass, store, secrets)

    # Core memory is real data, so the panel is told it can render it even
    # though the direct API was never configured.
    assert o["configured"] is True
    assert o["reachable"] is True
    assert o["status"] == "online"
    assert o["internet_connected"] is True

    by_mac = {c["mac"]: c for c in o["clients"]}
    printer = by_mac["aa:bb:cc:00:00:03"]
    assert printer["origin"] == "core_unifi"
    assert printer["wired"] is True
    assert printer["vlan"] == 30  # resolved through the gateway network_table
    assert printer["bandwidth"] == {"rx_bytes": 100, "tx_bytes": 50, "total_bytes": 150}
    assert 7195 <= printer["uptime"] <= 7210  # epoch quirk, converted to seconds
    phone = by_mac["aa:bb:cc:00:00:04"]
    assert phone["ssid"] == "HomeWiFi"
    assert phone["uptime"] == 600

    assert o["wireless_client_count"] == 1
    assert o["wired_client_count"] == 1
    assert o["total_client_count"] == 2

    device = o["devices"][0]
    assert device["origin"] == "core_unifi"
    assert device["state"] == "CONNECTED"
    assert device["firmware_updatable"] is False
    assert device["bandwidth"] == {
        "rx_bytes": 10_000,
        "tx_bytes": 5_000,
        "total_bytes": 15_000,
    }

    assert o["wan"]["port"] == "eth8"
    assert o["wan"]["up"] is True
    assert o["wan"]["availability"] == 100.0

    # Redaction: nothing from the raw secret fields may reach the payload.
    blob = repr(o)
    assert "SECRET" not in blob
    assert "SERIAL123" not in blob


async def test_broadcast_map_falls_back_to_core_wlans(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")
    # The API client references its WLAN by id only, and /wifi/broadcasts is
    # one of the endpoints the dispatcher 404s, so the SSID name can only
    # come from the core WLAN inventory.
    api_clients = [{"name": "phone", "type": "WIRELESS", "wlanId": "wl1"}]
    hub = FakeHub(FakeController(wlans=[FakeWlan("wl1", "HomeWiFi")]))
    _install_core_entry(hass, "unifi", hub)

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_dispatch_get(api_clients, []))):
        o = await async_network_overview(hass, store, secrets)

    assert o["clients"][0]["ssid"] == "HomeWiFi"
    assert "WLAN-SECRET-PASSPHRASE" not in repr(o)


async def test_overview_unloaded_core_entry_changes_nothing(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    # A core entry that exists but is not loaded (and one loaded without
    # runtime_data) must leave the overview exactly as it is today.
    mock_integration(hass, MockModule("unifi"))
    not_loaded = MockConfigEntry(domain="unifi")
    not_loaded.add_to_hass(hass)
    not_loaded.mock_state(hass, ConfigEntryState.NOT_LOADED)
    loaded_no_runtime = MockConfigEntry(domain="unifi")
    loaded_no_runtime.add_to_hass(hass)
    loaded_no_runtime.mock_state(hass, ConfigEntryState.LOADED)

    o = await async_network_overview(hass, store, secrets)
    assert o["configured"] is False
    assert o["reachable"] is False
    assert o["clients"] == []
    assert o["devices"] == []


# ---------------------------------------------------------------------------
# Protect enrichment (end to end through async_protect_status)
# ---------------------------------------------------------------------------


def _protect_runtime(now: datetime) -> FakeProtectData:
    camera = Obj(
        id="cam1",
        name="Front Door",
        host="192.168.30.50",
        mac="AABBCC445566",
        state=EnumValue("CONNECTED"),
        is_connected=True,
        is_recording=True,
        last_ring=now - timedelta(hours=2),
        recording_settings=Obj(mode=EnumValue("always")),
        channels=[Obj(name="High", width=3840, height=2160), Obj(name="Low", width=640, height=360)],
    )
    event = Obj(
        id="ev1",
        type=EnumValue("smartDetectZone"),
        smart_detect_types=[EnumValue("vehicle"), EnumValue("licensePlate")],
        score=87,
        start=now - timedelta(minutes=10),
        end=now - timedelta(minutes=9),
        camera_id="cam1",
        camera=camera,
        thumbnail_id="e-thumb-1",
        metadata=Obj(detected_thumbnails=[Obj(group=Obj(matched_name="ABC1234"))]),
    )
    stale_event = Obj(
        id="ev0",
        type=EnumValue("motion"),
        smart_detect_types=[],
        score=10,
        start=now - timedelta(days=3),
        end=None,
        camera_id="cam1",
        camera=camera,
        thumbnail_id=None,
        metadata=None,
    )
    bootstrap = Obj(cameras={"cam1": camera}, events={"ev1": event, "ev0": stale_event})
    return FakeProtectData(FakeProtectApi(bootstrap))


async def test_protect_status_from_core_only(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    _install_core_entry(hass, "unifiprotect", _protect_runtime(dt_util.utcnow()))

    out = await async_protect_status(hass, store, secrets)

    assert out["configured"] is True
    assert out["reachable"] is True
    assert out["host"] == "https://192.168.30.2"
    assert out["camera_count"] == 1
    assert out["cameras_online"] == 1
    cam = out["cameras"][0]
    assert cam["origin"] == "core_unifiprotect"
    assert cam["is_recording"] is True
    assert cam["state"] == "CONNECTED"
    assert cam["online"] is True
    assert cam["channels"] == ["High", "Low"]
    assert cam["link"] == "https://192.168.30.2/protect/dashboard/devices/cam1"

    # Only the event inside the card's 24h window survives the filter.
    assert len(out["events"]) == 1
    ev = out["events"][0]
    assert ev["origin"] == "core_unifiprotect"
    assert ev["type"] == "smartDetectZone"
    assert ev["smart_detect_types"] == ["vehicle", "licensePlate"]
    assert ev["score"] == 87
    assert ev["duration"] == 60
    assert ev["license_plate"] == "ABC1234"
    assert ev["camera"] == "Front Door"
    assert ev["thumbnail"] is True
    assert ev["thumbnail_link"] == "https://192.168.30.2/protect/dashboard/devices/cam1"
    assert out["events_error"] is None


async def test_protect_events_from_core_when_subscription_history_is_needed(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    """Cameras load via Local API while core supplies subscription history.
    Core bootstrap events must fill the card and clear the notice, and the
    REST camera row must gain the detail fields it was missing."""
    store.async_update_settings(unifi_protect_host="10.0.0.1")
    await secrets.async_set("unifi_protect_api_key", "k")
    _install_core_entry(hass, "unifiprotect", _protect_runtime(dt_util.utcnow()))

    async def _side_effect(hass_, conn, path):
        if path == "/cameras":
            # Sparse REST row: same camera, no recording/ring/channel detail.
            return [{"id": "cam1", "name": "Front Door", "state": "CONNECTED"}]
        raise AssertionError(f"undocumented Protect path called: {path}")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_side_effect)):
        out = await async_protect_status(hass, store, secrets)

    assert out["reachable"] is True
    assert out["camera_count"] == 1
    cam = out["cameras"][0]
    # REST had no is_recording/last_ring/channels; core filled them in.
    assert cam["is_recording"] is True
    assert cam["last_ring"] is not None
    assert cam["channels"] == ["High", "Low"]
    assert cam["ip"] == "192.168.30.50"
    # Events came from the bootstrap and the 404 message is gone.
    assert len(out["events"]) == 1
    assert out["events"][0]["license_plate"] == "ABC1234"
    assert out["events_error"] is None


async def test_protect_absent_core_keeps_subscription_notice(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    """Without core unifiprotect, the subscription limitation is explicit."""
    store.async_update_settings(unifi_protect_host="10.0.0.1")
    await secrets.async_set("unifi_protect_api_key", "k")

    async def _side_effect(hass_, conn, path):
        if path == "/cameras":
            return [{"id": "c1", "name": "cam", "state": "CONNECTED"}]
        raise AssertionError(f"undocumented Protect path called: {path}")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_side_effect)):
        out = await async_protect_status(hass, store, secrets)

    assert out["camera_count"] == 1
    assert out["events"] == []
    assert out["events_error"] is not None
