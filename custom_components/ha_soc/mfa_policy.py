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

Scope of assessment (work item 3.11, decision D-18 option (a)): this
policy assesses Home Assistant's OWN MFA modules only - it cannot see a
second factor enforced upstream by an SSO/header-auth proxy, an identity
provider, or anything else outside hass.auth. A user whose only
credentials come from a non-`homeassistant` auth provider is therefore
exempt from `auto_deactivate` and reported as "MFA not assessable"
(users.py sets `mfa_assessable` on the user payload; the Users view
renders the marker from that field): deactivating an externally-MFA'd
admin for "missing" a factor HA cannot observe would punish a compliant
account. An instance that authenticates entirely through such an external
proxy should keep the default `audit_only` policy - auto_deactivate has
nothing it can honestly judge there.
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
    # mfa_assessable defaults True for a record that predates the field:
    # failing open here would mean "cannot assess, so exempt", quietly
    # widening the exemption to every stale payload - the D-18 exemption
    # applies only when users.py positively established that the user's
    # credentials all come from a non-homeassistant provider.
    return bool(
        user.get("is_admin")
        and not user.get("is_owner")
        and user.get("is_active")
        and not user.get("mfa_enabled")
        and user.get("mfa_assessable", True)
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
