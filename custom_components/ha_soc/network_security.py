"""Network Security tab: advisory findings tying together UniFi ACL rules,
UniFi Firewall Policies, the HA server's own open ports, and Pi-hole's
DNS-level IoT visibility.

This module never mutates anything and never talks to the network itself;
``build_findings`` is a pure function over the UniFi and Pi-hole snapshots
(design and scope decisions: docs/design.md, docs/decisions.md).
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import SEVERITY_HIGH, SEVERITY_INFO, SEVERITY_MEDIUM
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_ALLOW_WORDS = ("allow", "accept", "permit")
_DENY_WORDS = ("deny", "drop", "block", "reject")


def _action_is_allow(action: str | None) -> bool:
    a = (action or "").lower()
    return any(w in a for w in _ALLOW_WORDS)


def _finding(
    finding_id: str,
    severity: str,
    category: str,
    title: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
    }


def _acl_findings(acl: dict[str, Any]) -> list[dict[str, Any]]:
    """ACL-Rules-specific findings; the "no rules at all" case is handled by
    _no_rules_finding."""
    findings: list[dict[str, Any]] = []
    if not acl.get("available"):
        return findings  # unifi.py already surfaces the "why" via acl.error

    rules = acl.get("rules") or []
    broad_allows = [
        r
        for r in rules
        if r.get("enabled") is not False
        and _action_is_allow(r.get("action"))
        and not (r.get("destination") or {}).get("ports")
        and not (r.get("destination") or {}).get("ip_or_subnets")
        and not (r.get("destination") or {}).get("networks")
        and not (r.get("source") or {}).get("ip_or_subnets")
        and not (r.get("source") or {}).get("networks")
        and not (r.get("source") or {}).get("macs")
    ]
    for r in broad_allows:
        name = r.get("name") or f"rule {r.get('order')}"
        findings.append(
            _finding(
                f"acl_broad_allow_{r.get('id') or r.get('order')}",
                SEVERITY_MEDIUM,
                "acl",
                f'ACL rule "{name}" allows all ports/protocols with no source or destination scoping',
                "This enabled ALLOW rule has no source IP/subnet/network/MAC "
                "restriction and no destination IP/subnet/network/port "
                "restriction — it matches from anywhere to anywhere. Review "
                "whether it should be scoped to specific networks or ports.",
            )
        )
    return findings


def _firewall_policy_findings(fw: dict[str, Any]) -> list[dict[str, Any]]:
    """Firewall-Policy-specific findings; "broad" means no traffic filter
    beyond the mandatory zone pair."""
    findings: list[dict[str, Any]] = []
    if not fw.get("available"):
        return findings  # unifi.py already surfaces the "why" via firewall_policies.error

    rules = fw.get("rules") or []
    broad_allows = [
        r
        for r in rules
        if r.get("enabled") is not False
        and _action_is_allow(r.get("action"))
        and not (r.get("source") or {}).get("filter_type")
        and not (r.get("destination") or {}).get("filter_type")
    ]
    for r in broad_allows:
        name = r.get("name") or f"policy {r.get('order')}"
        src_zone = (r.get("source") or {}).get("zone") or "an unnamed zone"
        dst_zone = (r.get("destination") or {}).get("zone") or "an unnamed zone"
        findings.append(
            _finding(
                f"firewall_policy_broad_allow_{r.get('id') or r.get('order')}",
                SEVERITY_MEDIUM,
                "firewall_policy",
                f'Firewall policy "{name}" allows all traffic from {src_zone} to {dst_zone}',
                "This enabled ALLOW policy has no traffic filter beyond its "
                "zone-to-zone scope — no network, IP, MAC, port, or protocol "
                "narrowing within that zone pair. Review whether it should be "
                "scoped more tightly, especially if either zone includes your "
                "IoT network.",
            )
        )
    return findings


def _no_rules_finding(acl: dict[str, Any], fw: dict[str, Any]) -> list[dict[str, Any]]:
    """One informational finding when both ACL Rules and Firewall Policies
    were read successfully and both came back empty."""
    acl_confirmed_empty = bool(acl.get("available")) and not (acl.get("rules") or [])
    fw_confirmed_empty = bool(fw.get("available")) and not (fw.get("rules") or [])
    if not (acl_confirmed_empty and fw_confirmed_empty):
        return []
    return [
        _finding(
            "no_traffic_rules_configured",
            SEVERITY_INFO,
            "acl",
            "No ACL rules or Firewall Policies are configured on this controller",
            "Neither of UniFi's two rule mechanisms has anything configured. "
            "Traffic between your networks/zones is governed entirely by "
            "UniFi's built-in default behavior, which is usually permissive "
            "between zones on the same gateway. Consider adding an explicit "
            "Firewall Policy (Settings -> Security -> Create Policy) denying "
            "the IoT network access to your LAN/management network.",
        )
    ]


def _server_port_findings(server_ports: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not server_ports.get("available"):
        return findings
    uncovered = [p for p in server_ports.get("ports") or [] if p.get("status") == "uncovered"]
    if not uncovered:
        return findings
    port_list = ", ".join(
        f"{p['port']}/{p['proto']}" for p in sorted(uncovered, key=lambda p: (p["port"], p["proto"]))
    )
    findings.append(
        _finding(
            "server_ports_uncovered",
            SEVERITY_MEDIUM,
            "exposure",
            f"{len(uncovered)} port(s) open on the Home Assistant server have no matching rule",
            f"These listening ports were reported by the HA SOC Probe and don't "
            f"appear as a destination in any enabled ACL rule or Firewall Policy "
            f"on this controller (by IP/subnet): {port_list}. This doesn't "
            f"necessarily mean they're reachable from every network — UniFi's "
            f"default zone policy still applies — but no rule of either kind "
            f"enumerates who may reach them. If any network other than your "
            f"trusted LAN can reach the server's IP, consider adding an explicit "
            f"rule or policy scoping these ports.",
        )
    )
    return findings


def _pihole_findings(pihole: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not pihole.get("configured"):
        findings.append(
            _finding(
                "pihole_not_configured",
                SEVERITY_INFO,
                "dns",
                "Pi-hole is not connected to HA SOC",
                "Configure the Pi-hole host and app password in Settings to see "
                "DNS blocking status, IoT client group scoping, and recently "
                "blocked domains here.",
            )
        )
        return findings
    if not pihole.get("reachable"):
        return findings  # pihole.py already surfaces the "why" via pihole.error

    if pihole.get("blocking_enabled") is False:
        findings.append(
            _finding(
                "pihole_blocking_disabled",
                SEVERITY_HIGH,
                "dns",
                "Pi-hole DNS blocking is currently disabled",
                "Blocking is off, so IoT devices and TVs whose DNS is forwarded "
                "here are not having any application-reporting/telemetry domains "
                "filtered right now.",
            )
        )

    if not pihole.get("iot_cidr"):
        findings.append(
            _finding(
                "pihole_iot_cidr_not_set",
                SEVERITY_INFO,
                "dns",
                "No IoT subnet is configured for the Pi-hole group-scoping check",
                "Set the IoT network CIDR in Settings (the subnet whose DNS the "
                "UniFi gateway forwards to Pi-hole) so HA SOC can check whether "
                "it has a dedicated Pi-hole client group.",
            )
        )
    elif pihole.get("iot_clients_scoped") is False:
        findings.append(
            _finding(
                "pihole_iot_not_scoped",
                SEVERITY_MEDIUM,
                "dns",
                "The IoT subnet has no dedicated Pi-hole client group",
                f"No client entry in Pi-hole for {pihole['iot_cidr']} is assigned "
                f"to anything but the global Default group. Every IoT device is "
                f"getting Pi-hole's site-wide blocklists rather than a group you "
                f"can tune specifically for IoT/TV telemetry domains — create a "
                f"Pi-hole client entry for this subnet and assign it a dedicated "
                f"group if you want stricter, IoT-specific blocking.",
            )
        )

    return findings


def build_findings(
    unifi_overview: dict[str, Any], pihole_overview: dict[str, Any]
) -> list[dict[str, Any]]:
    """Pure combination of the two snapshots into an advisory findings list,
    highest severity first, then stable by id. No I/O, no persistence."""
    acl = unifi_overview.get("acl") or {}
    firewall_policies = unifi_overview.get("firewall_policies") or {}
    findings: list[dict[str, Any]] = []
    findings.extend(_no_rules_finding(acl, firewall_policies))
    findings.extend(_acl_findings(acl))
    findings.extend(_firewall_policy_findings(firewall_policies))
    findings.extend(_server_port_findings(unifi_overview.get("server_ports") or {}))
    findings.extend(_pihole_findings(pihole_overview))

    order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_INFO: 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 99), f["id"]))
    return findings


def _client_summaries(clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """A lightweight projection of the Network tab's client rows: just enough
    to match a rule's source/destination against a real device."""
    out = []
    for c in clients:
        out.append(
            {
                "name": c.get("name"),
                "ipv4": c.get("ipv4"),
                "ipv6": c.get("ipv6"),
                "mac": c.get("mac"),
                "vlan": c.get("vlan"),
            }
        )
    return out


async def async_network_security_overview(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Network Security tab renders in one snapshot. Never
    raises: both underlying fetchers degrade to reachable=False with a
    human-readable error."""
    from .unifi import async_network_overview

    unifi_overview = await async_network_overview(hass, store, secrets)

    from .pihole import async_pihole_overview

    pihole_overview = await async_pihole_overview(hass, store, secrets)

    return {
        "acl": unifi_overview["acl"],
        "firewall_policies": unifi_overview["firewall_policies"],
        "server_ports": unifi_overview["server_ports"],
        "clients": _client_summaries(unifi_overview.get("clients") or []),
        "unifi_reachable": unifi_overview["reachable"],
        "unifi_error": unifi_overview["error"],
        "pihole": pihole_overview,
        "findings": build_findings(unifi_overview, pihole_overview),
        "generated_at": unifi_overview["generated_at"],
    }
