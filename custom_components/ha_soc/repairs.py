"""Repairs (issue registry) sync helpers not already owned by another module.

`health.py` and `scanner.py` create their own Repairs issues inline (they
have the domain-specific context to do it well). This module covers the
cross-cutting issue types that don't belong to either: admins without MFA
(a `users.py` + `risk.py` concern), confirmed high/critical device
vulnerabilities (a `vulns.py` concern), and stale long-lived access
tokens (also a `users.py` concern). Kept separate so none of those
modules needs to import `homeassistant.helpers.issue_registry` for a
single call site.
"""
from __future__ import annotations

from datetime import timedelta

import homeassistant.helpers.issue_registry as ir
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import DOMAIN

_ADMIN_MFA_PREFIX = "admin_without_mfa_"
_VULN_PREFIX = "device_vulnerability_"
_STALE_TOKEN_PREFIX = "stale_access_token_"

# Matches Spook's own long-lived-access-token staleness threshold — a
# reasonable, already-field-tested value for "probably forgotten", not
# this project's own invention.
STALE_TOKEN_UNUSED_DAYS = 180


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


async def async_sync_stale_token_issues(hass: HomeAssistant) -> None:
    """Spook-inspired: a long-lived access token unused for 180+ days is
    real attack surface someone likely forgot about — a leaked LLAT never
    expires on its own. Not auto-revoked here (that's a real, standing
    credential someone's script might still depend on); this only makes
    it visible. Actual revocation is the Users & Access tab's existing
    per-token Revoke action, already built — this issue just points at it.

    Reads straight from hass.auth rather than through UsersManager's
    async_list_users(): that method's record doesn't include
    refresh_tokens at all (only async_get_user_detail does, one user at a
    time) — this needs every user's tokens in one pass, and hass.auth
    already holds them all in memory synchronously.
    """
    registry = ir.async_get(hass)
    current_ids = {
        issue.issue_id
        for issue in registry.issues.values()
        if issue.domain == DOMAIN and issue.issue_id.startswith(_STALE_TOKEN_PREFIX)
    }
    still_open: set[str] = set()
    cutoff = dt_util.utcnow() - timedelta(days=STALE_TOKEN_UNUSED_DAYS)

    users = await hass.auth.async_get_users()
    for user in users:
        if user.system_generated:
            continue
        for token in user.refresh_tokens.values():
            if token.token_type != "long_lived_access_token":
                continue
            last_used = token.last_used_at or token.created_at
            if last_used is None or last_used >= cutoff:
                continue
            issue_id = f"{_STALE_TOKEN_PREFIX}{token.id}"
            still_open.add(issue_id)
            ir.async_create_issue(
                hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="stale_access_token",
                translation_placeholders={
                    "user_name": user.name or user.id,
                    "token_name": token.client_name or "(unnamed token)",
                    "last_used": last_used.isoformat(),
                },
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
