"""UniFi configuration baseline and drift detection (NIST 800-53 CM-6).

Takes a canonical projection of the controller's security-relevant
configuration, compares it against the baseline the owner accepted, and
reports what changed. Read-only: nothing here writes to the controller.

The projection is deliberately narrow. Only fields whose change is a
configuration decision are carried; anything that moves on its own (uptime,
signal, client counts, IP leases) is excluded, because a baseline that drifts
by itself teaches the reader to ignore it. Scope and field list are in
docs/design.md; the control mapping is in docs/NIST-SOC2-CONTROL-MATRIX.md.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import homeassistant.util.dt as dt_util

from .const import SEVERITY_INFO, SEVERITY_MEDIUM

_LOGGER = logging.getLogger(__name__)

# Sections are compared independently so a rule change is not buried in a
# device change; the order here is the order the panel renders.
SECTIONS = ("networks", "zones", "firewall_policies", "acl_rules", "devices")

SECTION_LABELS = {
    "networks": "Networks",
    "zones": "Firewall zones",
    "firewall_policies": "Firewall policies",
    "acl_rules": "ACL rules",
    "devices": "Devices",
}

# Keys the ledger will not store even if a future projection adds them.
_NEVER_STORE = frozenset({"api_key", "password", "passphrase", "token", "secret"})

MAX_HISTORY = 50
MAX_REPORTED_CHANGES = 200

AUDIT_CATEGORY_DRIFT = "unifi_config_drift"
AUDIT_CATEGORY_BASELINE = "unifi_baseline_accepted"


def _canonical(value: Any) -> Any:
    """Sort every container so an unordered API response hashes stably.

    Without this a controller that returns the same policies in a different
    order every poll would read as constant drift, which is the fastest way to
    make a drift report worthless.
    """
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in sorted(value.items()) if k not in _NEVER_STORE}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _network_rows(overview: dict[str, Any]) -> list[dict[str, Any]]:
    """Networks, taken from the zone membership the policies fetch resolved.

    The overview does not carry a standalone network list; zones carry the
    resolved names, which is what a segmentation change would alter.
    """
    names: set[str] = set()
    for zone in (overview.get("firewall_policies") or {}).get("zones") or []:
        for name in zone.get("networks") or []:
            names.add(str(name))
    return [{"id": name, "name": name} for name in sorted(names)]


def _zone_rows(overview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for zone in (overview.get("firewall_policies") or {}).get("zones") or []:
        rows.append(
            {
                "id": str(zone.get("id") or ""),
                "name": zone.get("name"),
                "networks": sorted(str(n) for n in (zone.get("networks") or [])),
            }
        )
    return sorted(rows, key=lambda r: r["id"])


def _policy_rows(overview: dict[str, Any]) -> list[dict[str, Any]]:
    """Firewall policies, reduced to the fields that decide what traffic passes."""
    rows = []
    for rule in (overview.get("firewall_policies") or {}).get("rules") or []:
        rows.append(
            {
                "id": str(rule.get("id") or ""),
                "name": rule.get("name"),
                "enabled": rule.get("enabled"),
                "action": rule.get("action"),
                "allow_return_traffic": rule.get("allow_return_traffic"),
                "ip_version": rule.get("ip_version"),
                "protocol": rule.get("protocol"),
                "connection_state_filter": rule.get("connection_state_filter"),
                "scheduled": rule.get("scheduled"),
                "origin": rule.get("origin"),
                "source": _filter_row(rule.get("source")),
                "destination": _filter_row(rule.get("destination")),
                "ports": sorted(str(p) for p in (rule.get("ports") or [])),
            }
        )
    return sorted(rows, key=lambda r: r["id"])


def _acl_rows(overview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for rule in (overview.get("acl") or {}).get("rules") or []:
        rows.append(
            {
                "id": str(rule.get("id") or ""),
                "name": rule.get("name"),
                "enabled": rule.get("enabled"),
                "action": rule.get("action"),
                "source": _filter_row(rule.get("source")),
                "destination": _filter_row(rule.get("destination")),
            }
        )
    return sorted(rows, key=lambda r: r["id"])


def _filter_row(value: Any) -> dict[str, Any]:
    """The matching half of a rule, normalized and order-stable."""
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {"zone": value.get("zone"), "filter_type": value.get("filter_type")}
    for key in ("networks", "ip_or_subnets", "macs", "domains", "ports"):
        items = value.get(key)
        out[key] = sorted(str(item) for item in items) if isinstance(items, list) else []
    return out


def _device_rows(overview: dict[str, Any]) -> list[dict[str, Any]]:
    """Devices, keyed on MAC rather than on the controller's record id.

    A device that is unadopted and re-adopted keeps its MAC; whether it keeps
    its id is not established, so keying on the id risks reading one device as
    a removal plus an addition. ``configuration_id`` and ``provisioned_at``
    are carried because together they say the running configuration is behind
    the intended one without saying how.
    """
    rows = []
    for device in overview.get("devices") or []:
        mac = device.get("mac") or device.get("macAddress")
        if not mac:
            continue
        rows.append(
            {
                "id": str(mac).lower(),
                "name": device.get("name"),
                "model": device.get("model"),
                "adopted_at": device.get("adopted_at"),
                "configuration_id": device.get("configuration_id"),
                "provisioned_at": device.get("provisioned_at"),
            }
        )
    return sorted(rows, key=lambda r: r["id"])


def build_snapshot(overview: dict[str, Any]) -> dict[str, Any]:
    """A canonical, comparable projection of the controller's configuration.

    Returns ``sections`` keyed by name, each a list of rows with a stable
    ``id``, plus a digest per section and one for the whole snapshot. Rule
    evaluation order is carried alongside the rules, because reordering
    changes behavior without changing any rule.
    """
    sections: dict[str, list[dict[str, Any]]] = {
        "networks": _network_rows(overview),
        "zones": _zone_rows(overview),
        "firewall_policies": _policy_rows(overview),
        "acl_rules": _acl_rows(overview),
        "devices": _device_rows(overview),
    }
    ordering = {
        "firewall_policies": (overview.get("firewall_policies") or {}).get("ordering"),
        "acl_rules": (overview.get("acl") or {}).get("ordering"),
    }
    snapshot = {
        "taken_at": dt_util.utcnow().isoformat(),
        "application_version": overview.get("application_version"),
        "site_id": overview.get("site_id"),
        "sections": sections,
        "ordering": ordering,
        "section_digests": {name: _digest(rows) for name, rows in sections.items()},
    }
    snapshot["digest"] = _digest(
        {"sections": sections, "ordering": ordering}
    )
    return snapshot


def snapshot_is_complete(overview: dict[str, Any]) -> tuple[bool, str | None]:
    """Whether a snapshot may be compared at all.

    A partial fetch must never become a baseline or a drift report: an ACL
    collection that failed to load would read as every rule deleted. This is
    the same refusal the unused-resource check makes for YAML dashboards.
    """
    if not overview.get("configured"):
        return False, "UniFi Network is not configured"
    if overview.get("error"):
        return False, str(overview["error"])
    if not (overview.get("firewall_policies") or {}).get("available"):
        return False, "Firewall policies could not be read"
    if not (overview.get("acl") or {}).get("available"):
        return False, "ACL rules could not be read"
    return True, None


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {row["id"]: row for row in rows}


def _field_changes(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    changes = []
    for key in sorted(set(before) | set(after)):
        if key == "id":
            continue
        old, new = before.get(key), after.get(key)
        if old != new:
            changes.append({"field": key, "from": old, "to": new})
    return changes


def diff_snapshots(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    """Per-section added, removed, and changed rows between two snapshots.

    Rows are matched on their stable id, so a renamed policy is a change and
    not a delete plus an add. ``ordering_changed`` is tracked separately
    because a reorder alters which rule wins with no row changing at all.
    """
    sections: dict[str, Any] = {}
    total = 0
    for name in SECTIONS:
        before = _rows_by_id(baseline.get("sections", {}).get(name) or [])
        after = _rows_by_id(current.get("sections", {}).get(name) or [])
        added = [after[i] for i in sorted(set(after) - set(before))]
        removed = [before[i] for i in sorted(set(before) - set(after))]
        changed = []
        for row_id in sorted(set(before) & set(after)):
            field_changes = _field_changes(before[row_id], after[row_id])
            if field_changes:
                changed.append(
                    {
                        "id": row_id,
                        "name": after[row_id].get("name") or before[row_id].get("name"),
                        "changes": field_changes,
                    }
                )
        ordering_changed = baseline.get("ordering", {}).get(name) != current.get("ordering", {}).get(name)
        count = len(added) + len(removed) + len(changed) + (1 if ordering_changed else 0)
        total += count
        sections[name] = {
            "added": added[:MAX_REPORTED_CHANGES],
            "removed": removed[:MAX_REPORTED_CHANGES],
            "changed": changed[:MAX_REPORTED_CHANGES],
            "ordering_changed": ordering_changed,
            "count": count,
        }
    return {
        "total": total,
        "sections": sections,
        "baseline_digest": baseline.get("digest"),
        "current_digest": current.get("digest"),
    }


def build_findings(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Advisory findings for the panel, from the ledger state.

    Drift is MEDIUM, not HIGH: a change that the owner made deliberately and
    has not yet accepted looks identical to one they did not make, and calling
    both of them urgent would train the reader to clear the card without
    reading it.
    """
    findings: list[dict[str, Any]] = []
    if not state.get("available"):
        return findings

    if state.get("baseline") is None:
        findings.append(
            {
                "id": "unifi_baseline_absent",
                "severity": SEVERITY_INFO,
                "category": "config_ledger",
                "title": "No UniFi configuration baseline has been accepted",
                "detail": (
                    "Drift cannot be reported until a baseline exists. Review the current "
                    "networks, zones, policies, and ACL rules, then accept them as the "
                    "baseline; every later change is compared against it."
                ),
                "remediation": None,
            }
        )
        return findings

    drift = state.get("drift") or {}
    for name in SECTIONS:
        section = (drift.get("sections") or {}).get(name) or {}
        if not section.get("count"):
            continue
        parts = []
        if section.get("added"):
            parts.append(f"{len(section['added'])} added")
        if section.get("removed"):
            parts.append(f"{len(section['removed'])} removed")
        if section.get("changed"):
            parts.append(f"{len(section['changed'])} changed")
        if section.get("ordering_changed"):
            parts.append("evaluation order changed")
        findings.append(
            {
                "id": f"unifi_drift_{name}",
                "severity": SEVERITY_MEDIUM,
                "category": "config_ledger",
                "title": f"{SECTION_LABELS[name]} differ from the accepted baseline",
                "detail": (
                    f"{', '.join(parts)} since the baseline was accepted "
                    f"{state['baseline'].get('accepted_at') or 'at an unrecorded time'}. "
                    "Review the change, then either accept the current configuration as the "
                    "new baseline or undo it on the controller."
                ),
                "remediation": None,
            }
        )
    return findings


async def async_ledger_state(hass, store, secrets) -> dict[str, Any]:
    """The full ledger view: baseline, current snapshot, drift, and history.

    Never raises. A controller that cannot be read completely comes back as
    available=False with the reason, and no drift is claimed either way.
    """
    from .unifi import async_network_overview

    overview = await async_network_overview(hass, store, secrets)
    complete, reason = snapshot_is_complete(overview)
    stored = store.data.get("unifi_ledger") or {}
    baseline = stored.get("baseline")

    state: dict[str, Any] = {
        "available": complete,
        "error": reason,
        "application_version": overview.get("application_version"),
        "baseline": baseline,
        "current": None,
        "drift": None,
        "history": list(stored.get("history") or [])[:MAX_HISTORY],
    }
    if not complete:
        return state

    current = build_snapshot(overview)
    state["current"] = current
    if baseline is not None:
        state["drift"] = diff_snapshots(baseline.get("snapshot") or {}, current)
    state["findings"] = build_findings(state)
    return state


def record_drift(store, audit, state: dict[str, Any]) -> bool:
    """Append one history entry and audit it, once per distinct digest.

    Returns True when a new entry was written. The digest guard is what keeps
    a polled check from writing an identical record every interval; the point
    of the ledger is the transitions, not the polling.
    """
    drift = state.get("drift")
    current = state.get("current")
    if not drift or not current or not drift.get("total"):
        return False

    stored = dict(store.data.get("unifi_ledger") or {})
    history = list(stored.get("history") or [])
    if history and history[0].get("digest") == current.get("digest"):
        return False

    entry = {
        "at": dt_util.utcnow().isoformat(),
        "digest": current.get("digest"),
        "baseline_digest": drift.get("baseline_digest"),
        "total": drift["total"],
        "sections": {
            name: section["count"]
            for name, section in (drift.get("sections") or {}).items()
            if section.get("count")
        },
    }
    history.insert(0, entry)
    stored["history"] = history[:MAX_HISTORY]
    store.async_set_unifi_ledger(stored)

    if audit is not None:
        audit.async_log(
            AUDIT_CATEGORY_DRIFT,
            detail={
                "total": entry["total"],
                "sections": entry["sections"],
                "digest": entry["digest"],
                "baseline_digest": entry["baseline_digest"],
            },
            flush=True,
        )
    return True


def accept_baseline(store, audit, snapshot: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    """Make the given snapshot the accepted baseline.

    The snapshot comes from the caller rather than being re-fetched here so
    the owner accepts exactly what the panel showed them, and the websocket
    layer is what proves it is current.
    """
    baseline = {
        "accepted_at": dt_util.utcnow().isoformat(),
        "accepted_by": user_id,
        "digest": snapshot.get("digest"),
        "snapshot": snapshot,
    }
    stored = dict(store.data.get("unifi_ledger") or {})
    previous = stored.get("baseline") or {}
    stored["baseline"] = baseline
    # History restarts against the new baseline; entries measured against the
    # old one would compare to something no longer in force.
    stored["history"] = []
    store.async_set_unifi_ledger(stored)

    if audit is not None:
        audit.async_log(
            AUDIT_CATEGORY_BASELINE,
            user_id=user_id,
            detail={
                "digest": baseline["digest"],
                "previous_digest": previous.get("digest"),
                "application_version": snapshot.get("application_version"),
                "section_digests": snapshot.get("section_digests"),
            },
            flush=True,
        )
    return baseline
