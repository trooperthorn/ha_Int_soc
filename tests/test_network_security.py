"""Tests for the Network Security tab's advisory findings engine
(network_security.py). ``build_findings`` is pure (no I/O), so every test
here feeds it fixed unifi/pihole overview shapes and asserts on the
resulting findings list — no mocking needed.
"""
from __future__ import annotations

from custom_components.ha_soc.const import SEVERITY_HIGH, SEVERITY_INFO, SEVERITY_MEDIUM
from custom_components.ha_soc.network_security import build_findings

_EMPTY_ACL = {"available": False, "rules": []}
_EMPTY_SERVER_PORTS = {"available": False, "ports": []}
_UNCONFIGURED_PIHOLE = {"configured": False, "reachable": False}


def _unifi(acl=None, server_ports=None):
    return {
        "acl": acl if acl is not None else _EMPTY_ACL,
        "server_ports": server_ports if server_ports is not None else _EMPTY_SERVER_PORTS,
    }


def test_no_findings_when_everything_is_clean() -> None:
    unifi = _unifi(
        acl={
            "available": True,
            "rules": [
                {
                    "id": "r1",
                    "order": 0,
                    "enabled": True,
                    "action": "ALLOW",
                    "destination": {"ip_or_subnets": ["10.0.0.5"], "ports": [8123], "networks": []},
                    "source": {"ip_or_subnets": ["10.0.0.0/24"], "networks": [], "macs": []},
                }
            ],
        },
        server_ports={
            "available": True,
            "ports": [{"port": 8123, "proto": "tcp", "status": "covered"}],
        },
    )
    pihole = {
        "configured": True,
        "reachable": True,
        "blocking_enabled": True,
        "iot_cidr": "192.168.50.0/24",
        "iot_clients_scoped": True,
    }
    assert build_findings(unifi, pihole) == []


def test_acl_unavailable_produces_no_finding_of_its_own() -> None:
    # unifi.py already surfaces the "why" via acl.error; this module must
    # not pile on a second, redundant finding for the same condition.
    findings = build_findings(_unifi(), _UNCONFIGURED_PIHOLE)
    assert not [f for f in findings if f["id"].startswith("acl_")]


def test_acl_available_but_empty_is_informational() -> None:
    unifi = _unifi(acl={"available": True, "rules": []})
    findings = build_findings(unifi, _UNCONFIGURED_PIHOLE)
    ids = {f["id"] for f in findings}
    assert "acl_no_rules" in ids
    assert next(f for f in findings if f["id"] == "acl_no_rules")["severity"] == SEVERITY_INFO


def test_broad_allow_rule_flagged() -> None:
    unifi = _unifi(
        acl={
            "available": True,
            "rules": [
                {
                    "id": "r9",
                    "order": 0,
                    "name": "Anywhere to anywhere",
                    "enabled": True,
                    "action": "ALLOW",
                    "destination": {"ip_or_subnets": [], "ports": [], "networks": []},
                    "source": {"ip_or_subnets": [], "networks": [], "macs": []},
                },
                {
                    # A BLOCK rule with the same shape must never be flagged
                    # as a "broad allow" — it's the opposite intent.
                    "id": "r10",
                    "order": 1,
                    "name": "Block everything",
                    "enabled": True,
                    "action": "BLOCK",
                    "destination": {"ip_or_subnets": [], "ports": [], "networks": []},
                    "source": {"ip_or_subnets": [], "networks": [], "macs": []},
                },
                {
                    # Scoped to a source network — must not be flagged.
                    "id": "r11",
                    "order": 2,
                    "name": "LAN only",
                    "enabled": True,
                    "action": "ALLOW",
                    "destination": {"ip_or_subnets": [], "ports": [], "networks": []},
                    "source": {"ip_or_subnets": [], "networks": ["LAN"], "macs": []},
                },
            ],
        }
    )
    findings = build_findings(unifi, _UNCONFIGURED_PIHOLE)
    broad = [f for f in findings if f["id"].startswith("acl_broad_allow_")]
    assert len(broad) == 1
    assert broad[0]["id"] == "acl_broad_allow_r9"
    assert broad[0]["severity"] == SEVERITY_MEDIUM


def test_disabled_broad_allow_rule_not_flagged() -> None:
    unifi = _unifi(
        acl={
            "available": True,
            "rules": [
                {
                    "id": "r9",
                    "order": 0,
                    "enabled": False,
                    "action": "ALLOW",
                    "destination": {"ip_or_subnets": [], "ports": [], "networks": []},
                    "source": {"ip_or_subnets": [], "networks": [], "macs": []},
                }
            ],
        }
    )
    findings = build_findings(unifi, _UNCONFIGURED_PIHOLE)
    assert not [f for f in findings if f["id"].startswith("acl_broad_allow_")]


def test_uncovered_server_ports_grouped_into_one_finding() -> None:
    unifi = _unifi(
        acl={"available": True, "rules": [{"id": "r1", "order": 0, "enabled": True, "action": "ALLOW"}]},
        server_ports={
            "available": True,
            "ports": [
                {"port": 22, "proto": "tcp", "status": "uncovered"},
                {"port": 8123, "proto": "tcp", "status": "covered"},
                {"port": 51827, "proto": "tcp", "status": "uncovered"},
            ],
        },
    )
    findings = build_findings(unifi, _UNCONFIGURED_PIHOLE)
    port_finding = next(f for f in findings if f["id"] == "server_ports_uncovered")
    assert port_finding["severity"] == SEVERITY_MEDIUM
    assert "22/tcp" in port_finding["detail"]
    assert "51827/tcp" in port_finding["detail"]
    assert "8123/tcp" not in port_finding["detail"]


def test_pihole_not_configured_is_informational() -> None:
    findings = build_findings(_unifi(), _UNCONFIGURED_PIHOLE)
    f = next(f for f in findings if f["id"] == "pihole_not_configured")
    assert f["severity"] == SEVERITY_INFO


def test_pihole_unreachable_produces_no_extra_finding() -> None:
    # pihole.py already surfaces the "why" via pihole.error.
    pihole = {"configured": True, "reachable": False, "error": "Timed out reaching Pi-hole."}
    findings = build_findings(_unifi(), pihole)
    assert findings == []


def test_pihole_blocking_disabled_is_high_severity() -> None:
    pihole = {
        "configured": True,
        "reachable": True,
        "blocking_enabled": False,
        "iot_cidr": "192.168.50.0/24",
        "iot_clients_scoped": True,
    }
    findings = build_findings(_unifi(), pihole)
    f = next(f for f in findings if f["id"] == "pihole_blocking_disabled")
    assert f["severity"] == SEVERITY_HIGH


def test_pihole_iot_cidr_not_set_prompts_configuration() -> None:
    pihole = {"configured": True, "reachable": True, "blocking_enabled": True, "iot_cidr": None}
    findings = build_findings(_unifi(), pihole)
    ids = {f["id"] for f in findings}
    assert "pihole_iot_cidr_not_set" in ids
    assert "pihole_iot_not_scoped" not in ids


def test_pihole_iot_not_scoped_flagged_medium() -> None:
    pihole = {
        "configured": True,
        "reachable": True,
        "blocking_enabled": True,
        "iot_cidr": "192.168.50.0/24",
        "iot_clients_scoped": False,
    }
    findings = build_findings(_unifi(), pihole)
    f = next(f for f in findings if f["id"] == "pihole_iot_not_scoped")
    assert f["severity"] == SEVERITY_MEDIUM
    assert "192.168.50.0/24" in f["detail"]


def test_findings_sorted_by_severity_then_id() -> None:
    unifi = _unifi(acl={"available": True, "rules": []})
    pihole = {"configured": True, "reachable": True, "blocking_enabled": False, "iot_cidr": None}
    findings = build_findings(unifi, pihole)
    severities = [f["severity"] for f in findings]
    order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_INFO: 2}
    assert severities == sorted(severities, key=lambda s: order[s])
