"""Network Security tab — advisory findings tying together UniFi ACL rules,
the HA server's own open ports, and Pi-hole's DNS-level IoT visibility.

This module never mutates anything and never talks to the network itself;
``async_network_security_overview`` is a thin wrapper that fetches the two
existing read-only snapshots (unifi.async_network_overview,
pihole.async_pihole_overview) and hands them to ``build_findings``, a pure
function with no I/O so it can be unit tested against fixed input the way
config_hygiene.py's checks are.

Every finding here is advisory only — a suggestion for the account owner to
look at, never a verdict and never something this project enforces or
auto-remediates. That matches the Scanner tab's own posture: this project
observes and reports on network security controls it does not own; it does
not edit UniFi ACL rules, does not toggle Pi-hole blocking, and does not
reassign Pi-hole clients to groups. A finding fires only when the
underlying data actually supports the specific claim being made — no
finding here guesses at which UniFi network is "the IoT network" beyond
what the owner has explicitly told Pi-hole (the ``pihole_iot_cidr``
setting), because the Integration API's client/device rows in this build
were not verified to expose a reliable per-network IP-subnet mapping HA SOC
could use to infer that on its own (see unifi.py's
correlate_server_ports_with_acl docstring for the same caveat applied to
port coverage).

Explicitly out of scope for this version, and why: a dismiss/resolve
lifecycle like vulns.py's CVE findings or config_hygiene.py's registry
checks. Those findings are about state that changes slowly and needs a
persisted "an owner already looked at this and dismissed it" record across
restarts. These findings are about live network/DNS configuration that can
change from one refresh to the next (a rule edited in the UniFi app, Pi-hole
blocking toggled from its own UI) — recomputing them fresh on every fetch,
the same way the ACL report itself already works, is more honest than a
persisted status that could silently go stale. If sustained false-positive
noise from a real deployment argues for dismissal state later, add it then;
building it now would be exactly the kind of premature persistence layer
this project's own conventions warn against.
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
    findings: list[dict[str, Any]] = []
    if not acl.get("available"):
        return findings  # unifi.py already surfaces the "why" via acl.error

    rules = acl.get("rules") or []
    if not rules:
        findings.append(
            _finding(
                "acl_no_rules",
                SEVERITY_INFO,
                "acl",
                "No ACL rules are configured on this controller",
                "The controller's ACL endpoint responded but returned zero rules. "
                "Traffic between your networks is governed entirely by UniFi's "
                "default same-broadcast-domain/zone behavior, which is usually "
                "permissive by default. Consider adding an explicit rule denying "
                "the IoT network access to your LAN/management network as a "
                "starting point.",
            )
        )
        return findings

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
            f"{len(uncovered)} port(s) open on the Home Assistant server have no matching ACL rule",
            f"These listening ports were reported by the HA SOC Probe and don't "
            f"appear as a destination in any enabled ACL rule on this controller "
            f"(by IP/subnet): {port_list}. This doesn't necessarily mean they're "
            f"reachable from every network — UniFi's default zone policy still "
            f"applies — but no rule enumerates who may reach them. If any network "
            f"other than your trusted LAN can reach the server's IP, consider "
            f"adding an explicit rule scoping these ports.",
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
    highest severity first, then stable by id. No I/O, no persistence —
    safe to call repeatedly with the same input and get the same output."""
    findings: list[dict[str, Any]] = []
    findings.extend(_acl_findings(unifi_overview.get("acl") or {}))
    findings.extend(_server_port_findings(unifi_overview.get("server_ports") or {}))
    findings.extend(_pihole_findings(pihole_overview))

    order = {SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 1, SEVERITY_INFO: 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 99), f["id"]))
    return findings


async def async_network_security_overview(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Network Security tab renders in one snapshot: the ACL
    rules report and server-port correlation (both already computed inside
    the UniFi overview), the Pi-hole overview, and the findings derived from
    both. Never raises — both underlying fetchers already degrade to
    reachable=False with a human-readable error on failure."""
    from .unifi import async_network_overview

    unifi_overview = await async_network_overview(hass, store, secrets)

    from .pihole import async_pihole_overview

    pihole_overview = await async_pihole_overview(hass, store, secrets)

    return {
        "acl": unifi_overview["acl"],
        "server_ports": unifi_overview["server_ports"],
        "unifi_reachable": unifi_overview["reachable"],
        "unifi_error": unifi_overview["error"],
        "pihole": pihole_overview,
        "findings": build_findings(unifi_overview, pihole_overview),
        "generated_at": unifi_overview["generated_at"],
    }
