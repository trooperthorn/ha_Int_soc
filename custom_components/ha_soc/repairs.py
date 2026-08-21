"""Repairs (issue registry) sync helpers not already owned by another module.

`health.py` and `scanner.py` create their own Repairs issues inline (they
have the domain-specific context to do it well). This module covers the two
cross-cutting issue types that don't belong to either: admins without MFA
(a `users.py` + `risk.py` concern) and confirmed high/critical device
vulnerabilities (a `vulns.py` concern). Kept separate so neither of those
modules needs to import `homeassistant.helpers.issue_registry` for a single
call site.
"""
from __future__ import annotations

import homeassistant.helpers.issue_registry as ir
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_ADMIN_MFA_PREFIX = "admin_without_mfa_"
_VULN_PREFIX = "device_vulnerability_"


async def async_sync_admin_mfa_issues(hass: HomeAssistant, users: list[dict]) -> None:
    registry = ir.async_get(hass)
    current_ids = {
        issue.issue_id
        for issue in registry.issues.values()
        if issue.domain == DOMAIN and issue.issue_id.startswith(_ADMIN_MFA_PREFIX)
    }
    still_open: set[str] = set()

    for user in users:
        if not (user.get("is_admin") and user.get("is_active") and not user.get("mfa_enabled")):
            continue
        issue_id = f"{_ADMIN_MFA_PREFIX}{user['id']}"
        still_open.add(issue_id)
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="admin_without_mfa",
            translation_placeholders={"user_name": user.get("name") or user["id"]},
        )

    for issue_id in current_ids - still_open:
        ir.async_delete_issue(hass, DOMAIN, issue_id)


async def async_sync_vuln_issues(hass: HomeAssistant, findings: list[dict]) -> None:
    registry = ir.async_get(hass)
    current_ids = {
        issue.issue_id
        for issue in registry.issues.values()
        if issue.domain == DOMAIN and issue.issue_id.startswith(_VULN_PREFIX)
    }
    still_open: set[str] = set()

    by_device: dict[str, list[dict]] = {}
    for finding in findings:
        if finding.get("status") == "dismissed":
            continue
        severity = finding.get("severity")
        if severity not in ("critical", "high"):
            continue
        by_device.setdefault(finding["device_id"], []).append(finding)

    for device_id, device_findings in by_device.items():
        issue_id = f"{_VULN_PREFIX}{device_id}"
        still_open.add(issue_id)
        device_name = device_findings[0].get("device_name") or device_id
        worst = max(device_findings, key=lambda f: f.get("cvss") or 0)
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=ir.IssueSeverity.CRITICAL if worst.get("severity") == "critical" else ir.IssueSeverity.ERROR,
            translation_key="device_vulnerability",
            translation_placeholders={
                "device_name": device_name,
                "count": str(len(device_findings)),
            },
        )

    for issue_id in current_ids - still_open:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
