"""Why a client may be unable to join, from configuration alone.

These exercise unifi_wifi directly: it is pure functions over the shapes the
UniFi Integration API documents, so it needs no Home Assistant fixtures.
"""
from __future__ import annotations

import re
from pathlib import Path

from custom_components.ha_soc import unifi_wifi

DEVICE_NAMES = {"ap-1": "Garage AP", "ap-2": "Attic AP", "ap-3": "Kitchen AP"}
NETWORK_NAMES = {"net-iot": "IoT (VLAN 30)", "net-lan": "LAN (VLAN 1)"}


def _codes(entry: dict) -> set[str]:
    return {f["code"] for f in entry["findings"]}


def _by_code(entry: dict, code: str) -> dict:
    return next(f for f in entry["findings"] if f["code"] == code)


def test_unrestricted_healthy_ssid_reports_nothing() -> None:
    rows = [
        {
            "id": "b1",
            "name": "IoT",
            "enabled": True,
            "type": "STANDARD",
            "broadcastingFrequenciesGHz": [2.4, 5],
            "securityConfiguration": {"type": "WPA2_PERSONAL"},
            "network": {"type": "SPECIFIC", "networkId": "net-iot"},
            "hideName": False,
        }
    ]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, DEVICE_NAMES, NETWORK_NAMES)
    assert entry["ssid"] == "IoT"
    assert entry["network"] == "IoT (VLAN 30)"
    assert entry["ap_scope"]["type"] == "ALL"
    assert entry["findings"] == []


def test_ap_restriction_names_the_access_points() -> None:
    rows = [
        {
            "id": "b1",
            "name": "IoT",
            "enabled": True,
            "broadcastingDeviceFilter": {"type": "DEVICES", "deviceIds": ["ap-1", "ap-3"]},
        }
    ]
    (entry,) = unifi_wifi.build_ssid_readiness(
        rows, DEVICE_NAMES, NETWORK_NAMES, ap_count=3
    )
    assert entry["ap_scope"]["device_names"] == ["Garage AP", "Kitchen AP"]
    assert entry["ap_scope"]["unresolved"] == 0
    message = _by_code(entry, "ap_restricted")["message"]
    assert "2 of 3 access points" in message
    assert "Garage AP, Kitchen AP" in message


def test_ap_restriction_counts_ids_it_cannot_name() -> None:
    """A device id the snapshot did not list is counted, never invented."""
    rows = [
        {
            "name": "IoT",
            "enabled": True,
            "broadcastingDeviceFilter": {"type": "DEVICES", "deviceIds": ["ap-1", "ghost"]},
        }
    ]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, DEVICE_NAMES, NETWORK_NAMES)
    assert entry["ap_scope"]["device_names"] == ["Garage AP"]
    assert entry["ap_scope"]["unresolved"] == 1
    assert "2 access points" in _by_code(entry, "ap_restricted")["message"]


def test_device_tag_restriction_claims_nothing() -> None:
    """The API exposes no route to resolve a device tag, so the finding says so."""
    rows = [
        {
            "name": "IoT",
            "enabled": True,
            "broadcastingDeviceFilter": {"type": "DEVICE_TAGS", "deviceTagIds": ["t1", "t2"]},
        }
    ]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, DEVICE_NAMES, NETWORK_NAMES)
    finding = _by_code(entry, "ap_restricted_by_tag")
    assert finding["severity"] == unifi_wifi.SEVERITY_UNKNOWN
    assert entry["ap_scope"]["tag_count"] == 2


def test_mac_allow_list_is_blocking_and_block_list_is_not() -> None:
    allow = [
        {
            "name": "IoT",
            "enabled": True,
            "clientFilteringPolicy": {"action": "ALLOW", "macAddressFilter": ["a", "b"]},
        }
    ]
    block = [
        {
            "name": "IoT",
            "enabled": True,
            "clientFilteringPolicy": {"action": "BLOCK", "macAddressFilter": ["a"]},
        }
    ]
    (allow_entry,) = unifi_wifi.build_ssid_readiness(allow, {}, {})
    (block_entry,) = unifi_wifi.build_ssid_readiness(block, {}, {})
    assert _by_code(allow_entry, "mac_allow_list")["severity"] == unifi_wifi.SEVERITY_BLOCKING
    assert _by_code(block_entry, "mac_block_list")["severity"] == unifi_wifi.SEVERITY_POSSIBLE


def test_no_2ghz_radio_blocks_iot_hardware() -> None:
    rows = [{"name": "IoT", "enabled": True, "broadcastingFrequenciesGHz": [5, 6]}]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, {}, {})
    assert "no_2ghz" in _codes(entry)
    rows[0]["broadcastingFrequenciesGHz"] = [2.4, 5]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, {}, {})
    assert "no_2ghz" not in _codes(entry)


def test_wpa3_only_blocks_but_mixed_mode_does_not() -> None:
    only = [{"name": "IoT", "enabled": True, "securityConfiguration": {"type": "WPA3_PERSONAL"}}]
    mixed = [
        {
            "name": "IoT",
            "enabled": True,
            "securityConfiguration": {"type": "WPA2_WPA3_PERSONAL"},
        }
    ]
    assert "wpa3_only" in _codes(unifi_wifi.build_ssid_readiness(only, {}, {})[0])
    assert "wpa3_only" not in _codes(unifi_wifi.build_ssid_readiness(mixed, {}, {})[0])


def test_disabled_hidden_and_scheduled_ssid() -> None:
    rows = [
        {
            "name": "IoT",
            "enabled": False,
            "hideName": True,
            "blackoutScheduleConfiguration": {"days": [{}, {}, {}]},
        }
    ]
    (entry,) = unifi_wifi.build_ssid_readiness(rows, {}, {})
    assert _codes(entry) >= {"ssid_disabled", "hidden_ssid", "blackout_schedule"}
    assert _by_code(entry, "ssid_disabled")["severity"] == unifi_wifi.SEVERITY_BLOCKING
    # The schedule is reported, not evaluated: nothing here claims it is in force now.
    assert _by_code(entry, "blackout_schedule")["severity"] == unifi_wifi.SEVERITY_UNKNOWN


def test_row_without_a_name_is_skipped_and_output_is_sorted() -> None:
    rows = [{"name": "zeta"}, {"id": "x"}, {"name": "Alpha"}]
    entries = unifi_wifi.build_ssid_readiness(rows, {}, {})
    assert [e["ssid"] for e in entries] == ["Alpha", "zeta"]


def test_absent_clients_exclude_connected_and_wired() -> None:
    history = {
        "aa:aa:aa:aa:aa:aa": {"name": "Sensor", "essid": "IoT", "last_seen": 900, "is_wired": False},
        "bb:bb:bb:bb:bb:bb": {"name": "Laptop", "essid": "LAN", "last_seen": 950, "is_wired": False},
        "cc:cc:cc:cc:cc:cc": {"name": "NAS", "last_seen": 999, "is_wired": True},
    }
    out = unifi_wifi.build_absent_clients(history, {"bb:bb:bb:bb:bb:bb"}, now_ts=1000)
    assert [c["mac"] for c in out] == ["aa:aa:aa:aa:aa:aa"]
    assert out[0]["absent_seconds"] == 100
    assert out[0]["ssid"] == "IoT"


def test_absent_clients_sort_recent_first_and_tolerate_no_timestamp() -> None:
    history = {
        "aa:aa:aa:aa:aa:aa": {"last_seen": 100},
        "bb:bb:bb:bb:bb:bb": {"last_seen": None},
        "cc:cc:cc:cc:cc:cc": {"last_seen": 500},
    }
    out = unifi_wifi.build_absent_clients(history, set(), now_ts=1000)
    assert [c["mac"] for c in out] == [
        "cc:cc:cc:cc:cc:cc",
        "aa:aa:aa:aa:aa:aa",
        "bb:bb:bb:bb:bb:bb",
    ]
    assert out[-1]["absent_seconds"] is None
    # A client with no name falls back to its MAC rather than rendering blank.
    assert out[-1]["name"] == "bb:bb:bb:bb:bb:bb"


def test_clients_table_columns_are_unchanged() -> None:
    """The Clients table's format is fixed; the join view is a separate section.

    Wi-Fi join diagnostics added ``ap``/``ap_id``/``ap_mac`` to every client
    row. None of them is a column, and this locks that: the table's ten
    headers, in order, are what they were.
    """
    source = Path(
        "custom_components/ha_soc/frontend/src/views/network-view.ts"
    ).read_text(encoding="utf-8")
    headers = source.split("private _colHeaders()")[1].split("private ")[0]
    found = re.findall(r'sortableTh\(\s*"([^"]+)"', headers)
    assert found == [
        "Client",
        "IPv4",
        "IPv6",
        "MAC",
        "VLAN",
        "SSID",
        "Uptime",
        "Bandwidth",
        "Last Seen",
        "Integration",
    ]
