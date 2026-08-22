"""Tests for mfa_policy.py's grace-period tracking and auto-deactivation.

Uses real hass.auth-backed users (via the pytest-homeassistant-custom-
component hass_admin_user/hass_owner_user fixtures) and the real
UsersManager.async_deactivate_user path rather than mocks — the whole
point of this module is that it's allowed to take a real, irreversible
action on a real account, so the test should prove that action actually
happens (and doesn't) against the real auth store, not against a stub.
"""
from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import MockUser

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.const import MFA_POLICY_AUDIT_ONLY, MFA_POLICY_AUTO_DEACTIVATE
from custom_components.ha_soc.mfa_policy import async_enforce_mfa_policy
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.users import UsersManager


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


@pytest.fixture
def users_manager(hass: HomeAssistant) -> UsersManager:
    return UsersManager(hass)


@pytest.fixture
def audit(hass: HomeAssistant, store: HaSocData) -> AuditLog:
    return AuditLog(hass, store)


async def _user_record(users_manager: UsersManager, user_id: str) -> dict:
    return await users_manager.async_get_user_detail(user_id)


async def test_audit_only_tracks_but_never_deactivates(
    hass: HomeAssistant, store: HaSocData, users_manager: UsersManager, audit: AuditLog, hass_admin_user: MockUser
) -> None:
    assert store.settings["mfa_policy"] == MFA_POLICY_AUDIT_ONLY
    users = [await _user_record(users_manager, hass_admin_user.id)]

    deactivated = await async_enforce_mfa_policy(store, users_manager, audit, users)

    assert deactivated == []
    assert hass_admin_user.id in store.data["mfa_grace_started"]
    refreshed = await hass.auth.async_get_user(hass_admin_user.id)
    assert refreshed.is_active is True


async def test_owner_is_never_tracked_or_deactivated(
    hass: HomeAssistant, store: HaSocData, users_manager: UsersManager, audit: AuditLog, hass_owner_user: MockUser
) -> None:
    store.async_update_settings(mfa_policy=MFA_POLICY_AUTO_DEACTIVATE, mfa_grace_period_days=0)
    users = [await _user_record(users_manager, hass_owner_user.id)]

    deactivated = await async_enforce_mfa_policy(store, users_manager, audit, users)

    assert deactivated == []
    assert hass_owner_user.id not in store.data["mfa_grace_started"]
    refreshed = await hass.auth.async_get_user(hass_owner_user.id)
    assert refreshed.is_active is True


async def test_auto_deactivate_waits_out_the_grace_period(
    hass: HomeAssistant, store: HaSocData, users_manager: UsersManager, audit: AuditLog, hass_admin_user: MockUser
) -> None:
    store.async_update_settings(mfa_policy=MFA_POLICY_AUTO_DEACTIVATE, mfa_grace_period_days=14)
    users = [await _user_record(users_manager, hass_admin_user.id)]

    # First pass: just started being noncompliant, grace period untouched.
    deactivated = await async_enforce_mfa_policy(store, users_manager, audit, users)
    assert deactivated == []
    refreshed = await hass.auth.async_get_user(hass_admin_user.id)
    assert refreshed.is_active is True


async def test_auto_deactivate_fires_once_grace_period_expires(
    hass: HomeAssistant, store: HaSocData, users_manager: UsersManager, audit: AuditLog, hass_admin_user: MockUser
) -> None:
    store.async_update_settings(mfa_policy=MFA_POLICY_AUTO_DEACTIVATE, mfa_grace_period_days=14)
    long_ago = (dt_util.utcnow() - timedelta(days=15)).isoformat()
    store.data["mfa_grace_started"][hass_admin_user.id] = long_ago
    users = [await _user_record(users_manager, hass_admin_user.id)]

    deactivated = await async_enforce_mfa_policy(store, users_manager, audit, users)

    assert deactivated == [hass_admin_user.id]
    assert hass_admin_user.id not in store.data["mfa_grace_started"]
    refreshed = await hass.auth.async_get_user(hass_admin_user.id)
    assert refreshed.is_active is False

    logged = [r for r in audit._buffer if r["category"] == "user_updated"]
    assert any(
        r["detail"].get("action") == "mfa_policy_auto_deactivated"
        and r["detail"].get("target_user_id") == hass_admin_user.id
        for r in logged
    )


async def test_restored_compliance_clears_the_grace_clock(
    hass: HomeAssistant, store: HaSocData, users_manager: UsersManager, audit: AuditLog, hass_admin_user: MockUser
) -> None:
    store.data["mfa_grace_started"][hass_admin_user.id] = dt_util.utcnow().isoformat()

    # This pass reports the same user as compliant (e.g. MFA now enabled) —
    # simulated here by simply omitting them from the noncompliant set,
    # since _is_noncompliant only looks at the fields on the passed dict.
    compliant_record = await _user_record(users_manager, hass_admin_user.id)
    compliant_record["mfa_enabled"] = True

    deactivated = await async_enforce_mfa_policy(store, users_manager, audit, [compliant_record])

    assert deactivated == []
    assert hass_admin_user.id not in store.data["mfa_grace_started"]
