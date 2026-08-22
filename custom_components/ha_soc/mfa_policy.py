"""MFA non-compliance enforcement — the one place HA SOC acts on MFA state
rather than just reporting it.

Home Assistant core has no hook to *require* MFA for a user (see
users.py's module docstring: there is no "reject login without a second
factor" mechanism an integration can attach to). What core does expose is
`async_deactivate_user` — a real, enforceable action. So the
`auto_deactivate` policy doesn't pretend to force MFA; once an admin has
stayed out of compliance past the configured grace period, it deactivates
the account, the same real-world outcome a human admin would eventually
reach by hand. The default policy, `audit_only`, never calls this — it
leaves enforcement to the existing Repairs issue and risk-score factor
(repairs.py, risk.py), matching what this module replaces if disabled.

The account owner is never evaluated here, deliberately: HA's own auth
store refuses to deactivate the owner (`async_deactivate_user` raises
ValueError), and locking out the one account that manages the whole
install would be a self-inflicted outage, not a security improvement.
"""
from __future__ import annotations

import logging
from typing import Any

import homeassistant.util.dt as dt_util

from .audit import AuditLog
from .const import MFA_POLICY_AUTO_DEACTIVATE
from .store import HaSocData
from .users import UsersManager

_LOGGER = logging.getLogger(__name__)


def _is_noncompliant(user: dict[str, Any]) -> bool:
    return bool(
        user.get("is_admin")
        and not user.get("is_owner")
        and user.get("is_active")
        and not user.get("mfa_enabled")
    )


async def async_enforce_mfa_policy(
    store: HaSocData,
    users_manager: UsersManager,
    audit: AuditLog,
    users: list[dict[str, Any]],
) -> list[str]:
    """Track non-compliance duration and, under auto_deactivate, act on it.

    Always runs the bookkeeping half (starting/clearing each noncompliant
    admin's grace-period clock) regardless of policy, so switching from
    audit_only to auto_deactivate doesn't instantly deactivate everyone who
    has been sitting out of compliance for a while — they still get a full
    grace period measured from when this actually started tracking them.

    Returns the user_ids deactivated on this pass (always empty unless the
    policy is auto_deactivate and at least one grace period has expired).
    """
    settings = store.settings
    grace_started = store.data["mfa_grace_started"]
    now = dt_util.utcnow()

    noncompliant_ids = {user["id"] for user in users if _is_noncompliant(user)}

    changed = False
    for user_id in noncompliant_ids:
        if user_id not in grace_started:
            grace_started[user_id] = now.isoformat()
            changed = True

    for user_id in set(grace_started) - noncompliant_ids:
        del grace_started[user_id]
        changed = True

    if changed:
        store.async_schedule_save()

    if settings.get("mfa_policy") != MFA_POLICY_AUTO_DEACTIVATE:
        return []

    grace_days = settings.get("mfa_grace_period_days", 14)
    users_by_id = {user["id"]: user for user in users}
    deactivated: list[str] = []

    for user_id in noncompliant_ids:
        started = dt_util.parse_datetime(grace_started[user_id])
        if started is None or (now - started).days < grace_days:
            continue

        ok, reason = await users_manager.async_deactivate_user(user_id)
        if not ok:
            if reason != "cannot_deactivate_owner":
                _LOGGER.warning(
                    "MFA policy could not deactivate user %s: %s", user_id, reason
                )
            continue

        del grace_started[user_id]
        deactivated.append(user_id)
        audit.async_log(
            "user_updated",
            user_id=None,
            detail={
                "target_user_id": user_id,
                "target_user_name": users_by_id[user_id].get("name"),
                "action": "mfa_policy_auto_deactivated",
                "grace_period_days": grace_days,
            },
        )

    if deactivated:
        store.async_schedule_save()

    return deactivated
