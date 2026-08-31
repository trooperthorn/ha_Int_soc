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
    _normalize_firewall_policy,
    async_network_overview,
    async_protect_status,
    correlate_server_ports_with_rules,
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
    """Build an AsyncMock side_effect for _get(hass, conn, path). Unknown
    paths answer with UniFiError exactly like a real console 404 does -
    the best-effort fetchers (broadcasts, networks, ACL) catch precisely
    that and nothing broader since work plan item 4.11."""

    async def _side_effect(hass, conn, path):
        if path == "/sites":
            return {"data": [{"id": "default", "name": "Default"}]}
        if path.startswith("/sites/default/clients"):
            return {"data": clients}
        if path.startswith("/sites/default/devices"):
            return {"data": devices}
        raise UniFiError(f"Endpoint not found ({path}).")

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


def test_normalize_acl_rule_ipv4_resolves_networks_ports_and_order() -> None:
    """The real IPV4 ACL Rule schema, verified directly against a live
    controller's own uploaded OpenAPI spec (network_v10.4.57): a top-level
    ``type: "IPV4"``/``protocolFilter`` (TCP/UDP only), and
    sourceFilter/destinationFilter discriminated by their own ``type``
    into IP_ADDRESSES_OR_SUBNETS/NETWORKS/PORTS, each carrying only the
    fields that variant actually has."""
    nm = {"n1": "IoT (VLAN 30)", "n2": "Guest (VLAN 40)"}
    raw = {
        "type": "IPV4",
        "name": "Block IoT to LAN",
        "action": "BLOCK",
        "enabled": True,
        "index": 3,
        "protocolFilter": ["TCP", "UDP"],
        "metadata": {"origin": "USER_DEFINED"},
        "sourceFilter": {"type": "NETWORKS", "networkIds": ["n1"]},
        "destinationFilter": {
            "type": "IP_ADDRESSES_OR_SUBNETS",
            "ipAddressesOrSubnets": ["192.168.1.0/24"],
            "portFilter": [22, 443, "8080"],
        },
    }
    row = _normalize_acl_rule(raw, 0, nm)
    assert row["order"] == 3
    assert row["name"] == "Block IoT to LAN"
    assert row["rule_type"] == "IPV4"
    assert row["action"] == "BLOCK"
    assert row["enabled"] is True
    assert row["origin"] == "USER_DEFINED"
    assert row["custom"] is True
    assert row["protocols"] == ["TCP", "UDP"]
    assert row["networks"] == ["IoT (VLAN 30)"]
    assert row["ports"] == [22, 443, 8080]
    assert row["source"]["networks"] == ["IoT (VLAN 30)"]
    assert row["destination"]["ip_or_subnets"] == ["192.168.1.0/24"]
    assert row["destination"]["ports"] == [22, 443, 8080]


def test_normalize_acl_rule_mac_type_scopes_network_via_networkid_filter() -> None:
    """A MAC-type rule's sourceFilter/destinationFilter never carries a
    network (only macAddresses/prefixLength) — its network comes from the
    rule-level ``networkIdFilter`` instead, which must still land in the
    row's ``networks`` list."""
    nm = {"n1": "IoT (VLAN 30)"}
    raw = {
        "type": "MAC",
        "name": "Block IoT device",
        "action": "BLOCK",
        "enabled": True,
        "index": 1,
        "networkIdFilter": "n1",
        "metadata": {"origin": "SYSTEM_DEFINED"},
        "sourceFilter": {"type": "MAC_ADDRESSES", "macAddresses": ["aa:bb:cc:dd:ee:ff"]},
        "destinationFilter": None,
    }
    row = _normalize_acl_rule(raw, 0, nm)
    assert row["rule_type"] == "MAC"
    assert row["origin"] == "SYSTEM_DEFINED"
    assert row["custom"] is False
    assert row["networks"] == ["IoT (VLAN 30)"]
    assert row["source"]["macs"] == ["aa:bb:cc:dd:ee:ff"]
    # IPV4-only field; a MAC rule never carries protocolFilter.
    assert row["protocols"] == []


def test_normalize_acl_rule_ports_only_filter_carries_no_network_or_ip() -> None:
    """The PORTS-discriminated endpoint filter matches by port alone —
    ipAddressesOrSubnets/networkIds/macs must all stay empty for it."""
    row = _normalize_acl_rule(
        {
            "type": "IPV4",
            "name": "Any source, port 67 only",
            "action": "ALLOW",
            "enabled": True,
            "index": 0,
            "destinationFilter": {"type": "PORTS", "portFilter": [67]},
        },
        0,
        {},
    )
    assert row["destination"]["ports"] == [67]
    assert row["destination"]["ip_or_subnets"] == []
    assert row["destination"]["networks"] == []
    assert row["destination"]["macs"] == []


def test_normalize_acl_rule_missing_origin_is_none_not_false() -> None:
    """No metadata at all (e.g. a private-API fallback row) must report
    ``custom`` as None (unknown), never a false "not custom"."""
    row = _normalize_acl_rule({"name": "x", "action": "ALLOW", "index": 0}, 0, {})
    assert row["origin"] is None
    assert row["custom"] is None


def test_normalize_acl_rule_legacy_flat_fields_degrade_gracefully() -> None:
    """A private-API row with no sourceFilter/destinationFilter at all
    (an older controller surface) still yields a shaped, non-crashing row —
    empty filter sides rather than a fabricated guess, plus the legacy
    flat source/destination string kept as a bare IP/zone hint."""
    row = _normalize_acl_rule(
        {"name": "Legacy rule", "action": "allow", "source": "10.0.0.5", "destination": "any"},
        2,
        {},
    )
    assert row["order"] == 2
    assert row["protocols"] == []
    assert row["ports"] == []
    assert row["source"]["ip_or_subnets"] == ["10.0.0.5"]
    assert row["destination"]["ip_or_subnets"] == ["any"]


async def test_overview_ssid_join_and_acl_report(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

    clients = [{"name": "phone", "type": "WIRELESS", "wifiBroadcastId": "b1"}]
    broadcasts = [{"id": "b1", "name": "HomeWiFi"}]
    networks = [{"id": "n1", "name": "LAN", "vlan": 1}]
    acl = [
        {
            "type": "IPV4",
            "name": "Block IoT",
            "action": "BLOCK",
            "enabled": True,
            "index": 0,
            "destinationFilter": {"type": "NETWORKS", "networkIds": ["n1"], "portFilter": [443]},
        }
    ]

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
    assert rule["action"] == "BLOCK"
    assert rule["networks"] == ["LAN (VLAN 1)"]
    assert rule["ports"] == [443]


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
# Firewall Policies — UniFi's zone-based default allow/deny UI, genuinely
# separate from ACL Rules (confirmed against a live controller: acl-rules
# returned count=0 while the real rules lived under firewall/policies).
# ---------------------------------------------------------------------------


def test_normalize_firewall_policy_network_source_ip_destination() -> None:
    nm = {"n1": "IoT (VLAN 30)"}
    zone_names = {"z-int": "Internal", "z-ext": "External"}
    raw = {
        "id": "p1",
        "name": "Block IoT to LAN",
        "description": "IoT devices should not reach the LAN",
        "enabled": True,
        "index": 2,
        "loggingEnabled": True,
        "action": {"type": "BLOCK"},
        "ipProtocolScope": {
            "ipVersion": "IPV4",
            "protocolFilter": {"type": "NAMED_PROTOCOL", "name": "TCP"},
        },
        "connectionStateFilter": ["NEW", "ESTABLISHED"],
        "source": {
            "zoneId": "z-int",
            "trafficFilter": {"type": "NETWORK", "networkFilter": {"networkIds": ["n1"], "matchOpposite": False}},
        },
        "destination": {
            "zoneId": "z-int",
            "trafficFilter": {
                "type": "IP_ADDRESS",
                "ipAddressFilter": {
                    "type": "IP_ADDRESSES",
                    "matchOpposite": False,
                    "items": [{"type": "SUBNET", "value": "192.168.1.0/24"}],
                },
                "portFilter": {
                    "type": "PORTS",
                    "matchOpposite": False,
                    "items": [
                        {"type": "PORT_NUMBER", "value": 22},
                        {"type": "PORT_NUMBER_RANGE", "start": 8000, "stop": 8010},
                    ],
                },
            },
        },
    }
    row = _normalize_firewall_policy(raw, 0, nm, zone_names)
    assert row["order"] == 2
    assert row["name"] == "Block IoT to LAN"
    assert row["action"] == "BLOCK"
    assert row["enabled"] is True
    assert row["logging_enabled"] is True
    assert row["ip_version"] == "IPV4"
    assert row["protocol"] == "TCP"
    assert row["connection_state_filter"] == ["NEW", "ESTABLISHED"]
    assert row["scheduled"] is False
    assert row["source"]["zone"] == "Internal"
    assert row["source"]["filter_type"] == "NETWORK"
    assert row["source"]["networks"] == ["IoT (VLAN 30)"]
    assert row["destination"]["zone"] == "Internal"
    assert row["destination"]["filter_type"] == "IP_ADDRESS"
    assert row["destination"]["ip_or_subnets"] == ["192.168.1.0/24"]
    assert row["destination"]["ports"] == ["22", "8000-8010"]
    assert row["networks"] == ["IoT (VLAN 30)"]
    assert row["ports"] == ["22", "8000-8010"]


def test_normalize_firewall_policy_port_filter_from_traffic_matching_list() -> None:
    """A port filter scoped to a saved Traffic Matching List carries no raw
    port numbers at all — this must surface as 'from_list', never a
    fabricated port number."""
    raw = {
        "id": "p2",
        "index": 0,
        "action": {"type": "ALLOW"},
        "source": {"zoneId": "z1"},
        "destination": {
            "zoneId": "z1",
            "trafficFilter": {
                "type": "PORT",
                "portFilter": {
                    "type": "TRAFFIC_MATCHING_LIST",
                    "matchOpposite": False,
                    "trafficMatchingListId": "list-1",
                },
            },
        },
    }
    row = _normalize_firewall_policy(raw, 0, {}, {})
    assert row["destination"]["ports"] == []
    assert row["destination"]["ports_from_list"] is True


def test_normalize_firewall_policy_missing_zone_name_degrades_to_none() -> None:
    row = _normalize_firewall_policy(
        {"id": "p3", "index": 0, "action": {"type": "ALLOW"}, "source": {"zoneId": "unknown"}, "destination": {"zoneId": "unknown"}},
        0,
        {},
        {},
    )
    assert row["source"]["zone"] is None
    assert row["destination"]["zone"] is None


async def test_overview_firewall_policies_report(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    store.async_update_settings(unifi_network_host="10.0.0.1")
    await secrets.async_set("unifi_network_api_key", "k")

    zones = [{"id": "z1", "name": "Internal", "networkIds": ["n1"]}]
    policies = [
        {
            "id": "p1",
            "name": "Allow LAN to HA",
            "enabled": True,
            "index": 0,
            "action": {"type": "ALLOW"},
            "source": {"zoneId": "z1"},
            "destination": {"zoneId": "z1"},
        }
    ]

    async def _se(hass, conn, path):
        base = path.split("?", 1)[0]
        if base == "/sites":
            return {"data": [{"id": "default"}]}
        if base in ("/sites/default/clients", "/sites/default/devices"):
            return {"data": []}
        if base == "/sites/default/acl-rules":
            return {"data": []}
        if base == "/sites/default/firewall/zones":
            return {"data": zones}
        if base == "/sites/default/firewall/policies":
            return {"data": policies}
        raise UniFiError("Endpoint not found")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_se)):
        o = await async_network_overview(hass, store, secrets)

    assert o["firewall_policies"]["available"] is True
    assert len(o["firewall_policies"]["rules"]) == 1
    assert o["firewall_policies"]["rules"][0]["name"] == "Allow LAN to HA"
    assert o["firewall_policies"]["rules"][0]["source"]["zone"] == "Internal"
    # network_map is empty here (no /sites/default/networks mock), so the
    # zone's networkIds fall back to their raw id string, same as
    # _resolve_network_refs does everywhere else in this module.
    assert o["firewall_policies"]["zones"] == [{"id": "z1", "name": "Internal", "networks": ["n1"]}]


async def test_overview_firewall_policies_unreachable_reports_error(
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
        if base == "/sites/default/acl-rules":
            return {"data": []}
        if base == "/sites/default/firewall/zones":
            raise UniFiError("Endpoint not found")
        if base == "/sites/default/firewall/policies":
            raise UniFiError("Endpoint not found")
        raise UniFiError("Endpoint not found")

    with patch.object(unifi, "_get", new=AsyncMock(side_effect=_se)):
        o = await async_network_overview(hass, store, secrets)

    # Unlike ACL Rules, Firewall Policies is a confirmed-real endpoint, so a
    # failure here is a genuine error, not "not supported by this build".
    assert o["firewall_policies"]["available"] is False
    assert o["firewall_policies"]["error"]


# ---------------------------------------------------------------------------
# HA server port <-> ACL rule correlation
# ---------------------------------------------------------------------------


def test_correlate_server_ports_no_open_ports_reports_unavailable() -> None:
    assert correlate_server_ports_with_rules(None, [])["available"] is False
    assert correlate_server_ports_with_rules([], [])["available"] is False


def test_correlate_server_ports_ignores_wildcard_and_loopback_binds() -> None:
    # 0.0.0.0/::/127.0.0.1 say "every interface"/"this host only", never a
    # real address another device on the LAN could target.
    ports = [
        {"port": 8123, "proto": "tcp", "address": "0.0.0.0"},
        {"port": 22, "proto": "tcp", "address": "127.0.0.1"},
    ]
    out = correlate_server_ports_with_rules(ports, [])
    assert out["available"] is False
    assert out["ports"] == []


def test_correlate_server_ports_covered_vs_network_scoped_vs_uncovered() -> None:
    ports = [
        {"port": 8123, "proto": "tcp", "address": "192.168.10.5"},
        {"port": 22, "proto": "tcp", "address": "192.168.10.5"},
        {"port": 51827, "proto": "tcp", "address": "192.168.10.5"},
    ]
    rules = [
        {
            "id": "r1",
            "order": 0,
            "name": "Allow LAN to HA UI",
            "enabled": True,
            "destination": {
                "ip_or_subnets": ["192.168.10.0/24"],
                "ports": [8123],
                "networks": [],
            },
        },
        {
            "id": "r2",
            "order": 1,
            "name": "Guest zone reaches HA",
            "enabled": True,
            "destination": {"ip_or_subnets": [], "ports": [22], "networks": ["Guest"]},
        },
        {
            # Disabled rules must never count as coverage.
            "id": "r3",
            "order": 2,
            "name": "Disabled catch-all",
            "enabled": False,
            "destination": {"ip_or_subnets": ["192.168.10.0/24"], "ports": [], "networks": []},
        },
    ]
    out = correlate_server_ports_with_rules(ports, rules)
    assert out["available"] is True
    assert out["server_ips"] == ["192.168.10.5"]
    by_port = {p["port"]: p for p in out["ports"]}
    assert by_port[8123]["status"] == "covered"
    assert by_port[8123]["covered_by"] == ["ACL: Allow LAN to HA UI"]
    assert by_port[22]["status"] == "network_scoped"
    assert by_port[22]["network_scoped_by"] == ["ACL: Guest zone reaches HA"]
    assert by_port[51827]["status"] == "uncovered"
    assert by_port[51827]["covered_by"] == []
    assert by_port[51827]["network_scoped_by"] == []


def test_correlate_server_ports_firewall_policy_with_string_and_range_ports() -> None:
    """Firewall Policy destinations carry port entries as strings (a single
    number or a "start-stop" range), never plain ints like ACL rules —
    _port_in_dest_list must tolerate both shapes."""
    ports = [
        {"port": 8123, "proto": "tcp", "address": "192.168.10.5"},
        {"port": 8443, "proto": "tcp", "address": "192.168.10.5"},
        {"port": 9999, "proto": "tcp", "address": "192.168.10.5"},
    ]
    policies = [
        {
            "id": "p1",
            "order": 0,
            "name": "Allow LAN to HA (single port)",
            "enabled": True,
            "destination": {"ip_or_subnets": ["192.168.10.0/24"], "ports": ["8123"], "networks": []},
        },
        {
            "id": "p2",
            "order": 1,
            "name": "Allow LAN to HA (range)",
            "enabled": True,
            "destination": {"ip_or_subnets": ["192.168.10.0/24"], "ports": ["8400-8500"], "networks": []},
        },
    ]
    out = correlate_server_ports_with_rules(ports, [], policies)
    by_port = {p["port"]: p for p in out["ports"]}
    assert by_port[8123]["covered_by"] == ["Policy: Allow LAN to HA (single port)"]
    assert by_port[8443]["covered_by"] == ["Policy: Allow LAN to HA (range)"]
    assert by_port[9999]["status"] == "uncovered"


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


# ---------------------------------------------------------------------------
# Sprint 4 client hardening (work plan item 4.11)
# ---------------------------------------------------------------------------


class _FakeStreamReader:
    def __init__(self, body: bytes) -> None:
        self._body = body

    async def read(self, n: int = -1) -> bytes:
        return self._body if n < 0 else self._body[:n]


class _FakeResponse:
    def __init__(self, status: int = 200, body: bytes = b"{}", content_length=None) -> None:
        self.status = status
        self.headers = {}
        self.content_length = content_length if content_length is not None else len(body)
        self.content = _FakeStreamReader(body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def raise_for_status(self) -> None:
        assert self.status < 400


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict] = []

    def get(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self._response


def _conn() -> "unifi._Conn":
    return unifi._Conn(
        host="10.0.0.1", api_key="k", verify_ssl=False,
        base_path="/proxy/network/integration/v1",
    )


async def test_unifi_get_never_follows_redirects(hass: HomeAssistant) -> None:
    session = _FakeSession(_FakeResponse(status=302))
    with patch.object(unifi, "async_get_clientsession", return_value=session):
        with pytest.raises(UniFiError, match="redirect"):
            await unifi._get(hass, _conn(), "/sites")
    # The request itself must carry allow_redirects=False, so even a
    # transport that would auto-follow never gets the chance.
    assert session.calls[0]["allow_redirects"] is False


async def test_unifi_body_cap(hass: HomeAssistant) -> None:
    # A declared Content-Length above the cap is refused before reading.
    oversized_declared = _FakeSession(
        _FakeResponse(status=200, body=b"{}", content_length=unifi._MAX_BODY_BYTES + 1)
    )
    with patch.object(unifi, "async_get_clientsession", return_value=oversized_declared):
        with pytest.raises(UniFiError, match="too large"):
            await unifi._get(hass, _conn(), "/sites")

    # A lying (absent/short) Content-Length is caught by the capped read.
    big_body = b"x" * (unifi._MAX_BODY_BYTES + 10)
    lying = _FakeSession(_FakeResponse(status=200, body=big_body, content_length=10))
    with patch.object(unifi, "async_get_clientsession", return_value=lying):
        with pytest.raises(UniFiError, match="too large"):
            await unifi._get(hass, _conn(), "/sites")

    # A small valid body still parses.
    ok = _FakeSession(_FakeResponse(status=200, body=b'{"data": []}'))
    with patch.object(unifi, "async_get_clientsession", return_value=ok):
        assert await unifi._get(hass, _conn(), "/sites") == {"data": []}


async def test_unifi_bad_host_in_other_entry_does_not_raise(hass: HomeAssistant) -> None:
    """A malformed host value in ANOTHER integration's config entry (an
    unclosed IPv6 bracket makes urlparse raise ValueError) must degrade
    to no hosts for that value, never take the endpoint index down."""
    bad = MockConfigEntry(domain="weird_int", data={"host": "http://[::1"}, title="Weird")
    bad.add_to_hass(hass)
    good = MockConfigEntry(domain="fine_int", data={"host": "10.0.0.9"}, title="Fine")
    good.add_to_hass(hass)

    assert _hosts_from_value("http://[::1") == []
    index = unifi._integration_endpoints(hass)
    assert "10.0.0.9" in index


async def test_unifi_invalid_configured_host_reports_error(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    """Only http/https schemes are allowed and userinfo is rejected; the
    overview reports a configuration error rather than connecting."""
    await secrets.async_set("unifi_network_api_key", "k")

    store.async_update_settings(unifi_network_host="ftp://10.0.0.1")
    overview = await async_network_overview(hass, store, secrets)
    assert overview["configured"] is True
    assert "scheme" in overview["error"]

    store.async_update_settings(unifi_network_host="https://root:pw@10.0.0.1")
    overview = await async_network_overview(hass, store, secrets)
    assert "username/password" in overview["error"]


def test_gateway_selected_by_role_before_name_tokens() -> None:
    """A device whose role field declares gateway wins over any number of
    name-token lookalikes; tokens are only consulted when nothing
    declares the role."""
    lookalike = {"name": "gateway closet switch", "model": "USW-24"}
    real = {"name": "core router", "type": "gateway"}
    assert unifi._select_gateway([lookalike, real]) is real
    # With no declared role anywhere, the token fallback still finds one.
    assert unifi._select_gateway([lookalike]) is lookalike
    assert unifi._select_gateway([{"name": "plain switch"}]) is None


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
