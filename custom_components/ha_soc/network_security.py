"""Network Security tab: advisory findings tying together UniFi ACL rules,
UniFi Firewall Policies, the HA server's own open ports, and Pi-hole's
DNS-level IoT visibility.

``build_findings`` is a pure function over the UniFi and Pi-hole snapshots.
The owner's decisions on each suggestion (planned, ignored, applied) live in
the store, and the one mutating path, ``async_apply_suggestion``, runs only
through the write-scoped connection when write-back is enabled (design,
scope, and trust boundary: docs/design.md, docs/decisions.md,
docs/security.md).
"""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from .const import (
    CONF_UNIFI_NETWORK_WRITE_ENABLED,
    DEFAULT_UNIFI_NETWORK_WRITE_ENABLED,
    REMEDIATION_DISABLE_ACL_RULE,
    REMEDIATION_DISABLE_FIREWALL_POLICY,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_MEDIUM,
    SUGGESTION_STATUS_APPLIED,
    SUGGESTION_STATUS_IGNORED,
    SUGGESTION_STATUS_PLANNED,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

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
    remediation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One suggestion. ``remediation`` names a change HA SOC can carry out
    itself (kind, target id, label); None means the fix is manual and the
    detail text says what to do."""
    return {
        "id": finding_id,
        "severity": severity,
        "category": category,
        "title": title,
        "detail": detail,
        "remediation": remediation,
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
                remediation=(
                    {
                        "kind": REMEDIATION_DISABLE_ACL_RULE,
                        "target_id": r["id"],
                        "label": f'Disable ACL rule "{name}"',
                        "reversible": "Re-enable the rule in UniFi Network under Settings, then Network, then ACL Rules.",
                    }
                    if r.get("id")
                    else None
                ),
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
                remediation=(
                    {
                        "kind": REMEDIATION_DISABLE_FIREWALL_POLICY,
                        "target_id": r["id"],
                        "label": f'Disable policy "{name}"',
                        "reversible": "Re-enable the policy in UniFi Network under Settings, then Security, then Policy Table.",
                    }
                    if r.get("id")
                    else None
                ),
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


def decorate_findings(
    findings: list[dict[str, Any]], decisions: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Copies of the findings with the owner's stored decision attached as
    ``decision`` ({status, at, by, detail}) or None. A finding that no longer
    fires drops out of the list on its own; its stale decision is harmless."""
    out = []
    for finding in findings:
        copy = dict(finding)
        copy["decision"] = decisions.get(finding["id"])
        out.append(copy)
    return out


def async_set_suggestion_decision(
    store: HaSocData, finding_id: str, status: str | None, *, by_user_id: str | None
) -> None:
    """Record plan or ignore (or clear with None). ``applied`` is written only
    by async_apply_suggestion after the controller confirmed the change."""
    if status not in (None, SUGGESTION_STATUS_PLANNED, SUGGESTION_STATUS_IGNORED):
        raise ValueError(f"status {status!r} cannot be set by hand")
    store.async_set_suggestion_decision(
        finding_id, status, by_user_id=by_user_id, at=dt_util.utcnow().isoformat()
    )


async def async_apply_suggestion(
    hass: HomeAssistant,
    store: HaSocData,
    secrets: HaSocSecretStore,
    finding_id: str,
    *,
    by_user_id: str,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Carry out a suggestion's remediation on the controller. Returns
    (ok, reason, result). The finding is re-derived from a fresh snapshot so
    a stale panel can never act on a policy that has since changed."""
    from .unifi import (
        UniFiError,
        async_disable_acl_rule,
        async_disable_firewall_policy,
        async_network_overview,
    )

    if not store.settings.get(CONF_UNIFI_NETWORK_WRITE_ENABLED, DEFAULT_UNIFI_NETWORK_WRITE_ENABLED):
        return False, "write_disabled", None
    unifi_overview = await async_network_overview(hass, store, secrets)
    from .pihole import async_pihole_overview

    pihole_overview = await async_pihole_overview(hass, store, secrets)
    finding = next((f for f in build_findings(unifi_overview, pihole_overview) if f["id"] == finding_id), None)
    if finding is None:
        return False, "finding_not_current", None
    remediation = finding.get("remediation")
    if not remediation:
        return False, "no_automatic_remediation", None
    kind = remediation["kind"]
    try:
        if kind == REMEDIATION_DISABLE_FIREWALL_POLICY:
            result = await async_disable_firewall_policy(hass, store, secrets, remediation["target_id"])
        elif kind == REMEDIATION_DISABLE_ACL_RULE:
            result = await async_disable_acl_rule(hass, store, secrets, remediation["target_id"])
        else:
            return False, "unknown_remediation", None
    except UniFiError as err:
        return False, str(err), None
    except Exception as err:  # noqa: BLE001 - the panel gets a reason, never a trace
        _LOGGER.exception("UniFi write-back failed for %s", finding_id)
        return False, f"Unexpected error: {err}", None
    store.async_set_suggestion_decision(
        finding_id,
        SUGGESTION_STATUS_APPLIED,
        by_user_id=by_user_id,
        at=dt_util.utcnow().isoformat(),
        detail={"kind": kind, **result},
    )
    return True, None, result


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

    write_enabled = bool(
        store.settings.get(CONF_UNIFI_NETWORK_WRITE_ENABLED, DEFAULT_UNIFI_NETWORK_WRITE_ENABLED)
    )
    return {
        "acl": unifi_overview["acl"],
        "firewall_policies": unifi_overview["firewall_policies"],
        "server_ports": unifi_overview["server_ports"],
        "clients": _client_summaries(unifi_overview.get("clients") or []),
        "unifi_reachable": unifi_overview["reachable"],
        "unifi_error": unifi_overview["error"],
        "pihole": pihole_overview,
        "findings": decorate_findings(
            build_findings(unifi_overview, pihole_overview),
            store.data.get("network_suggestions") or {},
        ),
        # True only when the owner enabled write-back; the write key's presence is not disclosed here.
        "write_enabled": write_enabled,
        "generated_at": unifi_overview["generated_at"],
    }
