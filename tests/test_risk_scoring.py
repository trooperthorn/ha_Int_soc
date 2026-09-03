"""Sprint 3 risk-engine semantics (work items 3.2, 3.4, 3.5).

Reachable never_logged_in, reconciled applied_points, the LLAT bonus
under the cap, the tunable risk caps, and provisional posture.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.risk import POSTURE_TERMS, RiskEngine
from custom_components.ha_soc.store import HaSocData


class FakeUsers:
    def __init__(self, users: list[dict[str, Any]]) -> None:
        self.users = users

    async def async_list_users(self):
        return self.users


def _user(user_id: str = "u1", **overrides: Any) -> dict[str, Any]:
    record = {
        "id": user_id,
        "name": user_id,
        "is_owner": False,
        "is_admin": False,
        "is_active": True,
        "mfa_enabled": True,
        "last_login_at": dt_util.utcnow().isoformat(),
        "account_age_days": 100,
        "credential_age_days": None,
        "credentials_count": 1,
        "refresh_token_count": 2,
        "llat_count": 0,
        "llat_oldest_days": None,
    }
    record.update(overrides)
    return record


def _detection(rule_id: str, *, status: str = "open", days_old: int = 0, severity: str = "high") -> dict:
    ts = (dt_util.utcnow() - timedelta(days=days_old)).isoformat()
    return {"rule_id": rule_id, "status": status, "severity": severity, "ts": ts, "user_id": "u1"}


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


def _engine(hass, store, users=None) -> RiskEngine:
    return RiskEngine(hass, store, users=FakeUsers(users or []))


def _factor(result: dict, name: str) -> dict | None:
    return next((f for f in result["factors"] if f["name"] == name), None)


async def test_never_logged_in_fires_for_credentialed_user(
    hass: HomeAssistant, store: HaSocData
) -> None:
    """An active user with a credential and NO refresh tokens fires the
    factor. With no tokens there is no account age, so the detail says so
    honestly instead of inventing one."""
    engine = _engine(hass, store)
    user = _user(
        last_login_at=None,
        account_age_days=None,
        credentials_count=1,
        refresh_token_count=0,
    )
    result = engine._compute_user_risk(user, [], dt_util.utcnow())

    factor = _factor(result, "never_logged_in")
    assert factor is not None
    assert "unknown age, never logged in" in factor["detail"]


async def test_never_logged_in_needs_a_credential(hass: HomeAssistant, store: HaSocData) -> None:
    engine = _engine(hass, store)
    user = _user(
        last_login_at=None,
        account_age_days=None,
        credentials_count=0,
        refresh_token_count=0,
    )
    result = engine._compute_user_risk(user, [], dt_util.utcnow())
    assert _factor(result, "never_logged_in") is None


async def test_never_logged_in_age_gate_applies_when_age_is_known(
    hass: HomeAssistant, store: HaSocData
) -> None:
    """Where a credential age IS known (a future core), the maturity gate
    still applies: a brand-new account is not flagged."""
    engine = _engine(hass, store)
    young = _user(
        last_login_at=None, credentials_count=1, refresh_token_count=0, credential_age_days=2
    )
    result = engine._compute_user_risk(young, [], dt_util.utcnow())
    assert _factor(result, "never_logged_in") is None

    old = _user(
        last_login_at=None, credentials_count=1, refresh_token_count=0, credential_age_days=30
    )
    result = engine._compute_user_risk(old, [], dt_util.utcnow())
    factor = _factor(result, "never_logged_in")
    assert factor is not None
    assert "30d-old" in factor["detail"]


async def test_risk_factors_reconcile(hass: HomeAssistant, store: HaSocData) -> None:
    """applied_points sums exactly to the clamped score even when the raw
    factor total blows past 100."""
    engine = _engine(hass, store)
    user = _user(
        is_admin=True,
        mfa_enabled=False,
        llat_count=4,
        llat_oldest_days=400,
    )
    detections = [
        _detection("disabled_user_activity", severity="high") for _ in range(4)
    ] + [_detection("success_after_failures", severity="critical")]
    result = engine._compute_user_risk(user, detections, dt_util.utcnow())

    raw_total = sum(f["points"] for f in result["factors"])
    assert raw_total > 100
    assert result["score"] == 100
    applied_total = sum(f["applied_points"] for f in result["factors"])
    assert applied_total == pytest.approx(result["score"], abs=0.05)

    # The unclamped case reconciles too (rounding residue folded in).
    mild = _user(is_admin=True, mfa_enabled=False)
    result = engine._compute_user_risk(mild, [], dt_util.utcnow())
    assert result["score"] == 25
    assert sum(f["applied_points"] for f in result["factors"]) == pytest.approx(
        result["score"], abs=0.05
    )


async def test_llat_bonus_applies_before_cap(hass: HomeAssistant, store: HaSocData) -> None:
    """5 tokens (15 raw) + old-token bonus (4) still caps at 12: the bonus
    lands before min(), so the cap is the true ceiling."""
    engine = _engine(hass, store)
    user = _user(llat_count=5, llat_oldest_days=400)
    result = engine._compute_user_risk(user, [], dt_util.utcnow())
    factor = _factor(result, "long_lived_token_load")
    assert factor is not None
    assert factor["points"] == 12


async def test_disabled_user_activity_capped(hass: HomeAssistant, store: HaSocData) -> None:
    """Six open disabled-user detections (120 raw points) cap at the
    secure default of 40; a non-default cap is read live."""
    engine = _engine(hass, store)
    user = _user()
    detections = [_detection("disabled_user_activity") for _ in range(6)]

    result = engine._compute_user_risk(user, detections, dt_util.utcnow())
    factor = _factor(result, "disabled_user_activity")
    assert factor is not None
    assert factor["points"] == 40

    store.async_update_settings(
        detection_thresholds={"disabled_user_activity": {"risk_cap_points": 10}}
    )
    result = engine._compute_user_risk(user, detections, dt_util.utcnow())
    assert _factor(result, "disabled_user_activity")["points"] == 10


async def test_privilege_escalation_capped(hass: HomeAssistant, store: HaSocData) -> None:
    """Five recent escalations (40 raw points) cap at the secure default
    of 24; a non-default cap is read live."""
    engine = _engine(hass, store)
    user = _user()
    detections = [_detection("privilege_escalation") for _ in range(5)]

    result = engine._compute_user_risk(user, detections, dt_util.utcnow())
    factor = _factor(result, "privilege_escalation")
    assert factor is not None
    assert factor["points"] == 24

    store.async_update_settings(
        detection_thresholds={"privilege_escalation": {"risk_cap_points": 8}}
    )
    result = engine._compute_user_risk(user, detections, dt_util.utcnow())
    assert _factor(result, "privilege_escalation")["points"] == 8


async def test_posture_provisional_until_complete(hass: HomeAssistant, store: HaSocData) -> None:
    """Posture is provisional (with the missing terms listed) until every
    term has computed once ever; the stamps persist so a source table
    that later empties never resurrects the badge."""
    engine = _engine(hass, store)

    result = await engine.async_compute_posture()
    assert result["provisional"] is True
    # p_user computes live on the first pass; the other four are waiting.
    assert set(result["missing_terms"]) == {
        "p_vuln",
        "p_misconfig",
        "p_integration",
        "p_detection",
    }
    assert result["term_computed_at"]["p_user"] is not None

    # Sources come online one by one.
    store.data["vuln_findings"]["f1"] = {"status": "new", "severity": "high"}
    store.data["misconfig_findings"]["m1"] = {"status": "new", "severity": "low"}
    store.data["integration_health"]["e1"] = {"state": "loaded"}
    store.async_note_detection_pass_completed(dt_util.utcnow().isoformat())

    result = await engine.async_compute_posture()
    assert result["provisional"] is False
    assert result["missing_terms"] == []
    assert all(result["term_computed_at"][t] is not None for t in POSTURE_TERMS)

    # Computed once ever: an emptied table does not bring the badge back.
    store.data["vuln_findings"].clear()
    result = await engine.async_compute_posture()
    assert result["provisional"] is False
