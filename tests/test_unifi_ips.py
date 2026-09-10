"""Tests for unifi_ips.py: the gateway's Threat Management posture and block log.

Every fixture below is the shape one UCG-Fiber on Network 10.4.57 produced on
2026-09-10, with the daemon token replaced. The properties that matter: a
file that did not parse is reported as unparsed rather than as empty, the
server-exemption finding fires only when the server's address is known, and
the block log parser reads the projected rows without inventing signature
detail that the gateway does not persist.
"""
from __future__ import annotations

from datetime import UTC, datetime

from custom_components.ha_soc import unifi_ips
from custom_components.ha_soc.network_security import build_findings

_CONFIG_JSON = """{
    "alert": {"category": [], "signature_id": []},
    "drop": {"category": ["BOTCC", "EXPLOIT", "SCAN", "MISC"], "signature_id": []},
    "whitelist": []
}
"""
_DAEMON_JSON = """{
    "block_category": ["BOTCC", "EXPLOIT", "SCAN", "MISC"],
    "block_sid": [],
    "block_time": 300,
    "device_id": "a8:9c:6c:98:1c:78",
    "is_ssl_inspection_enabled": false,
    "logging_threat_event": true,
    "suricata_version": 8,
    "token": "not-the-real-token"
}
"""
_REPUTATION_JSON = """{
    "dst_whitelist": ["192.168.1.11/32", "192.168.30.3/32", "10.30.30.0/24"],
    "src_whitelist": ["192.168.1.11/32", "192.168.30.3/32", "10.30.30.0/24"]
}
"""
_HOMENET_YAML = """%YAML 1.1
---
vars:
  address-groups:
    HOME_NET: "[192.168.1.1/24,192.168.254.254/28,192.168.30.1/24,2603:8080:1b00:a300::1/64]"
    EXTERNAL_NET: "!$HOME_NET"
  port-groups:
    HTTP_PORTS: "80"
"""
_IFACE_YAML = """%YAML 1.1
---
pcap:
  - interface: br0
    threads: 1
    bpf-filter: "not net 169.254.254.0/24"
  - interface: br30
    threads: 1
    bpf-filter: "not net 169.254.254.0/24"
"""
_THRESHOLD = (
    "suppress gen_id 0, sig_id 0, track by_src , ip [192.168.1.11/32,192.168.30.3/32,10.30.30.0/24]\n"
    "suppress gen_id 0, sig_id 0, track by_dst , ip [192.168.1.11/32,192.168.30.3/32,10.30.30.0/24]\n"
    "suppress gen_id 1, sig_id 2210045, track by_src, ip 192.168.1.50\n"
)

FULL = _CONFIG_JSON + _DAEMON_JSON + _REPUTATION_JSON + _HOMENET_YAML + _IFACE_YAML + _THRESHOLD


def test_the_verified_gateway_output_parses_completely() -> None:
    posture = unifi_ips.parse_ips_config(FULL)
    assert posture["kind"] == "ips_config"
    assert all(posture["parsed"].values()), posture["parsed"]
    assert posture["mode"] == "prevent"
    assert posture["drop_categories"] == ["BOTCC", "EXPLOIT", "SCAN", "MISC"]
    assert posture["block_time_seconds"] == 300
    assert posture["logging_threat_event"] is True
    assert posture["ssl_inspection"] is False
    assert posture["suricata_version"] == 8
    assert posture["exempt_networks"] == ["192.168.1.11/32", "192.168.30.3/32", "10.30.30.0/24"]
    assert posture["suppressed_networks"] == ["192.168.1.11/32", "192.168.30.3/32", "10.30.30.0/24"]
    assert posture["suppressed_signatures"] == [
        {"gen_id": 1, "sig_id": 2210045, "networks": ["192.168.1.50/32"]}
    ]
    assert posture["home_networks"] == [
        "192.168.1.0/24",
        "192.168.254.240/28",
        "192.168.30.0/24",
        "2603:8080:1b00:a300::/64",
    ]
    assert [i["interface"] for i in posture["interfaces"]] == ["br0", "br30"]
    # The token never appears in the derived posture.
    assert "not-the-real-token" not in repr(posture)


def test_mode_is_read_from_the_daemon_config() -> None:
    detect = _DAEMON_JSON.replace('["BOTCC", "EXPLOIT", "SCAN", "MISC"]', "[]")
    config = _CONFIG_JSON.replace(
        '"alert": {"category": [], "signature_id": []}',
        '"alert": {"category": ["SCAN"], "signature_id": []}',
    ).replace('"drop": {"category": ["BOTCC", "EXPLOIT", "SCAN", "MISC"], "signature_id": []}', '"drop": {"category": [], "signature_id": []}')
    assert unifi_ips.parse_ips_config(config + detect)["mode"] == "detect"

    off = _CONFIG_JSON.replace('["BOTCC", "EXPLOIT", "SCAN", "MISC"]', "[]") + detect
    assert unifi_ips.parse_ips_config(off)["mode"] == "off"


def test_a_missing_file_is_unparsed_not_empty() -> None:
    """Only the two JSON files came back: the rest must read as unknown."""
    posture = unifi_ips.parse_ips_config(_CONFIG_JSON + _DAEMON_JSON)
    assert posture["parsed"]["reputation"] is False
    assert posture["parsed"]["homenet"] is False
    assert posture["parsed"]["threshold"] is False
    assert posture["exempt_networks"] == []
    assert posture["home_networks"] == []
    # And nothing at all gives an unknown mode rather than "off".
    assert unifi_ips.parse_ips_config("cat: /run/ips/config/config.json: No such file")["mode"] == "unknown"


def test_the_server_exemption_finding_needs_the_servers_address() -> None:
    posture = unifi_ips.parse_ips_config(FULL)

    with_ip = {f["id"]: f for f in unifi_ips.evaluate(posture, ["192.168.30.3"])}
    assert with_ip["ips_exempts_server"]["severity"] == "high"
    assert "192.168.30.3 (in 192.168.30.3/32)" in with_ip["ips_exempts_server"]["detail"]
    assert "ips_not_covering_server" not in with_ip
    assert "ips_exemptions_unchecked" not in with_ip

    without_ip = {f["id"]: f for f in unifi_ips.evaluate(posture, [])}
    assert "ips_exempts_server" not in without_ip
    assert without_ip["ips_exemptions_unchecked"]["severity"] == "info"

    clean = {f["id"]: f for f in unifi_ips.evaluate(posture, ["192.168.30.40"])}
    assert "ips_exempts_server" not in clean
    assert "ips_exemptions_unchecked" not in clean


def test_a_server_outside_home_net_is_reported() -> None:
    posture = unifi_ips.parse_ips_config(FULL)
    found = {f["id"]: f for f in unifi_ips.evaluate(posture, ["192.168.50.60"])}
    assert found["ips_not_covering_server"]["severity"] == "medium"
    assert "192.168.50.60" in found["ips_not_covering_server"]["detail"]


def test_mode_findings() -> None:
    off = dict(unifi_ips.parse_ips_config(FULL), mode="off")
    assert [f["id"] for f in unifi_ips.evaluate(off, [])][0] == "ips_off"
    detect = dict(unifi_ips.parse_ips_config(FULL), mode="detect", alert_categories=["SCAN"])
    assert "ips_detect_only" in {f["id"] for f in unifi_ips.evaluate(detect, [])}
    quiet = dict(unifi_ips.parse_ips_config(FULL), logging_threat_event=False)
    assert "ips_threat_logging_off" in {f["id"] for f in unifi_ips.evaluate(quiet, [])}
    unknown = unifi_ips.parse_ips_config("")
    assert [f["id"] for f in unifi_ips.evaluate(unknown, ["192.168.30.3"])] == ["ips_mode_unknown"]


def test_network_security_findings_use_the_stored_posture() -> None:
    """The findings engine folds the posture in with the server's addresses
    from the Probe's port report, and says nothing when nothing was collected."""
    unifi = {
        "acl": {"available": False, "rules": []},
        "firewall_policies": {"available": False, "rules": [], "zones": []},
        "server_ports": {"available": True, "ports": [{"address": "192.168.30.3", "port": 8123, "proto": "tcp"}]},
    }
    pihole = {"configured": False, "reachable": False}
    stored = {
        "host": "192.168.254.254",
        "collected_at": "2026-09-10T18:00:00+00:00",
        "posture": unifi_ips.parse_ips_config(FULL),
    }
    ids = [f["id"] for f in build_findings(unifi, pihole, stored)]
    assert "ips_exempts_server" in ids
    exempt = next(f for f in build_findings(unifi, pihole, stored) if f["id"] == "ips_exempts_server")
    assert exempt["remediation"] is None
    assert "192.168.254.254" in exempt["detail"]

    assert not [f for f in build_findings(unifi, pihole, None) if f["id"].startswith("ips_")]
    assert not [f for f in build_findings(unifi, pihole) if f["id"].startswith("ips_")]


_BLOCK_ROWS = "\n".join(
    [
        '{"id":"6aa2edc13ea40c4bb6ba3a44","key":"THREAT_BLOCKED_KNOWN_SOURCE_CLIENT","time":1789062593555,'
        '"severity":"VERY_HIGH","parameters":{"SRC_CLIENT":{"hostname":"x15-wk","name":"x15-wk b4:21",'
        '"target_id":"d4:3b:04:e3:b4:21","_class":"DEVICE_CLIENT_PARAMETER_DATA"},'
        '"DEVICE":{"model":"UCG-Fiber","ip":"192.168.254.254","name":"Ranchero-Fiber","target_id":"a8:9c:6c:98:1c:78"},'
        '"DST_IP":{"name":"2001:8d8:100f:f000::208","target_id":"2001:8d8:100f:f000::208","not_actionable":true},'
        '"INITIATOR_ID":{"target_id":"6aa2edc03ea40c4bb6ba3a42"}}}',
        '{"id":"6a9e19f98e077ff35b9e6cb0","key":"THREAT_BLOCKED_V3","time":1788746233090,"severity":"VERY_HIGH",'
        '"parameters":{"SRC_IP":{"name":"192.168.1.2","target_id":"192.168.1.2"},'
        '"DST_IP":{"name":"224.0.0.252","target_id":"224.0.0.252"}}}',
        '{"id":"6aa2e8553ea40c4bb6ba3677","key":"TRAFFIC_BLOCKED_KNOWN_SOURCE_DEVICE","time":1789061205837,'
        '"parameters":{"SRC_DEVICE":{"model":"USW-Pro-Max-16-PoE","ip":"192.168.254.253","name":"USW Pro Max 16 PoE",'
        '"target_id":"0c:ea:14:f1:54:71"},"DST_IP":{"name":"1.1.1.1","target_id":"1.1.1.1"},'
        '"TRIGGER":{"name":"Block all but web","target_id":"6a2485fa0e1b906078d2e7ad"}}}',
        "not json at all",
    ]
)


def test_block_log_rows_are_read_as_projected() -> None:
    now = datetime.fromtimestamp(1789062593555 / 1000, UTC)
    log = unifi_ips.parse_block_log(_BLOCK_ROWS, now=now)
    assert log["kind"] == "ips_block_log"
    assert log["unparsed"] == 1
    assert [r["key"] for r in log["rows"]] == [
        "THREAT_BLOCKED_KNOWN_SOURCE_CLIENT",
        "TRAFFIC_BLOCKED_KNOWN_SOURCE_DEVICE",
        "THREAT_BLOCKED_V3",
    ]
    client_block, policy_block, old_block = log["rows"]
    assert client_block["kind"] == "threat"
    assert client_block["source"] == {
        "kind": "SRC_CLIENT",
        "address": None,
        "mac": "d4:3b:04:e3:b4:21",
        "name": "x15-wk",
    }
    assert client_block["destination"]["address"] == "2001:8d8:100f:f000::208"
    assert client_block["severity"] == "VERY_HIGH"
    assert client_block["policy"] is None
    assert policy_block["kind"] == "firewall"
    assert policy_block["policy"] == "Block all but web"
    assert policy_block["source"]["address"] == "192.168.254.253"
    assert policy_block["source"]["mac"] == "0c:ea:14:f1:54:71"
    assert old_block["last_24h"] is False
    assert log["threat_blocks_24h"] == 1
    assert log["firewall_blocks_24h"] == 1
    assert log["sources_24h"] == ["d4:3b:04:e3:b4:21", "192.168.254.253"]
    assert log["by_key"]["THREAT_BLOCKED_V3"] == 1
