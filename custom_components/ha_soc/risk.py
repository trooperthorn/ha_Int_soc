"""Per-user risk scoring and whole-install security posture scoring.

Every score is additive, capped, and explainable: a result's `factors`
list is the complete arithmetic behind its `score` (factor rationale and
weights: docs/design.md).
"""
from __future__ import annotations

import ipaddress
import logging
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from .const import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
)
from .detections import (
    RULE_DISABLED_USER_ACTIVITY,
    RULE_NEW_IP_LOGIN,
    RULE_OFF_HOURS_ANOMALY,
    RULE_PRIVILEGE_ESCALATION,
    RULE_SUCCESS_AFTER_FAILURES,
    RULE_TOKEN_MINTING_ANOMALY,
    thresholds,
)
from .store import HaSocData

if TYPE_CHECKING:
    # Not imported at runtime so this module stays importable without users.py.
    from .users import UsersManager

_LOGGER = logging.getLogger(__name__)

BAND_LOW_MAX = 29
BAND_MODERATE_MAX = 59
BAND_HIGH_MAX = 79
# critical is anything above BAND_HIGH_MAX, up to 100

ADMIN_WITHOUT_MFA_POINTS = 25
NON_ADMIN_WITHOUT_MFA_POINTS = 8

# Age gate applies only when credential_age_days is known; core's Credentials has no created_at.
NEVER_LOGGED_IN_POINTS = 10
NEVER_LOGGED_IN_MIN_ACCOUNT_AGE_DAYS = 14

STALE_ACCOUNT_90D_DAYS = 90
STALE_ACCOUNT_90D_POINTS = 8
STALE_ACCOUNT_180D_DAYS = 180
STALE_ACCOUNT_180D_POINTS = 12

# The old-token bonus is added before the cap, so LLAT_POINTS_CAP is a true ceiling.
LLAT_POINTS_PER_TOKEN = 3
LLAT_POINTS_CAP = 12
LLAT_OLD_TOKEN_DAYS = 365
LLAT_OLD_TOKEN_BONUS_POINTS = 4

# A decayed contribution below this is dropped entirely, not carried as a fraction.
DECAY_DROP_THRESHOLD = 1.0

SUCCESS_AFTER_FAILURES_BASE_POINTS = 12
SUCCESS_AFTER_FAILURES_HALF_LIFE_DAYS = 3.5
SUCCESS_AFTER_FAILURES_CAP = 18

NEW_IP_LOGIN_BASE_POINTS = 8
NEW_IP_LOGIN_PUBLIC_BASE_POINTS = 12
NEW_IP_LOGIN_HALF_LIFE_DAYS = 7
NEW_IP_LOGIN_CAP = 16

OFF_HOURS_BASE_POINTS = 6
OFF_HOURS_HALF_LIFE_DAYS = 3.5
OFF_HOURS_CAP = 10

# Flat within the window, no decay; the total is capped by the rule's tunable risk_cap_points.
PRIVILEGE_ESCALATION_POINTS = 8
PRIVILEGE_ESCALATION_WINDOW_DAYS = 30

TOKEN_MINTING_BASE_POINTS = 5
TOKEN_MINTING_HALF_LIFE_DAYS = 3.5
TOKEN_MINTING_CAP = 10

# Flat while open, decays once acked; the total is capped by the rule's tunable risk_cap_points.
DISABLED_USER_ACTIVITY_OPEN_POINTS = 20
DISABLED_USER_ACTIVITY_HALF_LIFE_DAYS = 7

# Deliberately double-counts open detections already scored by a named factor.
GENERIC_OPEN_DETECTION_SEVERITY_POINTS = {
    SEVERITY_CRITICAL: 25,
    SEVERITY_HIGH: 15,
    SEVERITY_MEDIUM: 8,
    SEVERITY_LOW: 3,
}
GENERIC_OPEN_DETECTION_CAP = 30

USER_SCORE_MIN = 0
USER_SCORE_MAX = 100

POSTURE_WEIGHT_USER = 0.35
POSTURE_WEIGHT_VULN = 0.25
POSTURE_WEIGHT_MISCONFIG = 0.20
POSTURE_WEIGHT_INTEGRATION = 0.10
POSTURE_WEIGHT_DETECTION = 0.10

ADMIN_POSTURE_WEIGHT_MULTIPLIER = 2  # admins count double in the P_user average

VULN_POINTS_CRITICAL = 25  # cvss >= 9.0
VULN_POINTS_HIGH = 10  # cvss >= 7.0
VULN_POINTS_MEDIUM = 4  # cvss >= 4.0
VULN_POINTS_LOW = 1  # cvss < 4.0, or missing/unscored
VULN_CVSS_CRITICAL_THRESHOLD = 9.0
VULN_CVSS_HIGH_THRESHOLD = 7.0
VULN_CVSS_MEDIUM_THRESHOLD = 4.0
VULN_EXCLUDED_STATUS = "dismissed"
P_VULN_CAP = 100

MISCONFIG_SEVERITY_POINTS = {
    SEVERITY_CRITICAL: 25,
    SEVERITY_HIGH: 12,
    SEVERITY_MEDIUM: 5,
    SEVERITY_LOW: 2,
    SEVERITY_INFO: 0,
}
MISCONFIG_INCLUDED_STATUSES = ("new", "confirmed")
P_MISCONFIG_CAP = 100

INTEGRATION_SETUP_ERROR_POINTS = 20
INTEGRATION_HIGH_ERROR_COUNT_THRESHOLD = 10
INTEGRATION_HIGH_ERROR_POINTS = 8
INTEGRATION_UNAVAILABLE_RATIO_WEIGHT = 50
P_INTEGRATION_CAP = 100

DETECTION_SEVERITY_POSTURE_POINTS = {
    SEVERITY_CRITICAL: 30,
    SEVERITY_HIGH: 15,
    SEVERITY_MEDIUM: 6,
    SEVERITY_LOW: 2,
    SEVERITY_INFO: 0,
}
P_DETECTION_CAP = 100

POSTURE_SCORE_MIN = 0
POSTURE_SCORE_MAX = 100

GRADE_A_MIN = 90
GRADE_B_MIN = 80
GRADE_C_MIN = 70
GRADE_D_MIN = 60

POSTURE_HISTORY_MAX_DAYS = 90

# Each posture term is stamped only on real evidence that it computed at least once.
POSTURE_TERM_USER = "p_user"
POSTURE_TERM_VULN = "p_vuln"
POSTURE_TERM_MISCONFIG = "p_misconfig"
POSTURE_TERM_INTEGRATION = "p_integration"
POSTURE_TERM_DETECTION = "p_detection"
POSTURE_TERMS = (
    POSTURE_TERM_USER,
    POSTURE_TERM_VULN,
    POSTURE_TERM_MISCONFIG,
    POSTURE_TERM_INTEGRATION,
    POSTURE_TERM_DETECTION,
)


def _band_for_score(score: int) -> str:
    if score > BAND_HIGH_MAX:
        return "critical"
    if score > BAND_MODERATE_MAX:
        return "high"
    if score > BAND_LOW_MAX:
        return "moderate"
    return "low"


def _grade_for_score(score: int) -> str:
    if score >= GRADE_A_MIN:
        return "A"
    if score >= GRADE_B_MIN:
        return "B"
    if score >= GRADE_C_MIN:
        return "C"
    if score >= GRADE_D_MIN:
        return "D"
    return "F"


def _decayed_points(ts_str: str | None, now: datetime, base: float, half_life_days: float) -> float:
    if not ts_str:
        return 0.0
    ts = dt_util.parse_datetime(ts_str)
    if ts is None:
        return 0.0
    days_since = max((now - ts).days, 0)
    points = base * (0.5 ** (days_since / half_life_days))
    return points if points >= DECAY_DROP_THRESHOLD else 0.0


def _is_public_ip(ip: str | None) -> bool:
    """True IPv4/IPv6 global-unicast address (`is_global`), so CGNAT and other
    reserved-but-not-private ranges do not count as public."""
    if not ip:
        return False
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


class RiskEngine:
    """Computes per-user risk scores and the whole-install posture score."""

    def __init__(self, hass: HomeAssistant, store: HaSocData, *, users: "UsersManager") -> None:
        self.hass = hass
        self.store = store
        self.users = users

        self.last_risk_results: dict[str, dict[str, Any]] = {}
        self.last_posture_result: dict[str, Any] | None = None

    async def async_recompute_all(self) -> dict[str, dict[str, Any]]:
        now = dt_util.utcnow()
        users = await self.users.async_list_users()

        detections_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for detection in self.store.data["detections"].values():
            uid = detection.get("user_id")
            if uid:
                detections_by_user[uid].append(detection)

        results: dict[str, dict[str, Any]] = {}
        for user in users:
            result = self._compute_user_risk(user, detections_by_user.get(user["id"], []), now)
            results[user["id"]] = result

        self.last_risk_results = results
        return results

    def _compute_user_risk(
        self, user: dict[str, Any], user_detections: list[dict[str, Any]], now: datetime
    ) -> dict[str, Any]:
        factors: list[dict[str, Any]] = []

        is_admin = bool(user.get("is_admin"))
        mfa_enabled = bool(user.get("mfa_enabled"))
        if is_admin and not mfa_enabled:
            factors.append(
                {
                    "name": "admin_without_mfa",
                    "points": ADMIN_WITHOUT_MFA_POINTS,
                    "detail": "Administrator account has no MFA module enabled",
                }
            )
        elif not is_admin and not mfa_enabled:
            factors.append(
                {
                    "name": "non_admin_without_mfa",
                    "points": NON_ADMIN_WITHOUT_MFA_POINTS,
                    "detail": "Account has no MFA module enabled",
                }
            )

        is_active = user.get("is_active")
        last_login_at = user.get("last_login_at")
        account_age_days = user.get("account_age_days")

        # Age gate applies only when credential_age_days is known; otherwise fires with unknown age.
        credentials_count = user.get("credentials_count") or 0
        refresh_token_count = user.get("refresh_token_count") or 0
        credential_age_days = user.get("credential_age_days")
        if is_active and credentials_count >= 1 and refresh_token_count == 0:
            if credential_age_days is not None:
                if credential_age_days >= NEVER_LOGGED_IN_MIN_ACCOUNT_AGE_DAYS:
                    factors.append(
                        {
                            "name": "never_logged_in",
                            "points": NEVER_LOGGED_IN_POINTS,
                            "detail": (
                                f"Enabled {credential_age_days}d-old account "
                                "has never logged in"
                            ),
                        }
                    )
            else:
                factors.append(
                    {
                        "name": "never_logged_in",
                        "points": NEVER_LOGGED_IN_POINTS,
                        "detail": (
                            "Enabled account with a credential has never "
                            "logged in (unknown age, never logged in)"
                        ),
                    }
                )

        if is_active and last_login_at:
            last_login_dt = dt_util.parse_datetime(last_login_at)
            if last_login_dt is not None:
                days_since_login = (now - last_login_dt).days
                if days_since_login > STALE_ACCOUNT_180D_DAYS:
                    factors.append(
                        {
                            "name": "stale_account",
                            "points": STALE_ACCOUNT_180D_POINTS,
                            "detail": f"No login in {days_since_login}d",
                        }
                    )
                elif days_since_login > STALE_ACCOUNT_90D_DAYS:
                    factors.append(
                        {
                            "name": "stale_account",
                            "points": STALE_ACCOUNT_90D_POINTS,
                            "detail": f"No login in {days_since_login}d",
                        }
                    )

        llat_count = user.get("llat_count") or 0
        if llat_count:
            raw_llat = llat_count * LLAT_POINTS_PER_TOKEN
            detail_msg = f"{llat_count} long-lived access token(s)"
            llat_oldest_days = user.get("llat_oldest_days")
            if llat_oldest_days is not None and llat_oldest_days > LLAT_OLD_TOKEN_DAYS:
                # Bonus before the cap so the cap is the factor's ceiling.
                raw_llat += LLAT_OLD_TOKEN_BONUS_POINTS
                detail_msg += f", oldest {llat_oldest_days}d"
            llat_points = min(raw_llat, LLAT_POINTS_CAP)
            factors.append(
                {"name": "long_lived_token_load", "points": llat_points, "detail": detail_msg}
            )

        # Resolved detections never contribute to any factor.
        active_detections = [d for d in user_detections if d.get("status") != "resolved"]

        self._add_success_after_failures_factor(factors, active_detections, now)
        self._add_new_ip_login_factor(factors, active_detections, now)
        self._add_off_hours_factor(factors, active_detections, now)
        # dormant_revival is informational by design and contributes no points.
        self._add_privilege_escalation_factor(factors, active_detections, now)
        self._add_token_minting_factor(factors, active_detections, now)
        self._add_disabled_user_activity_factor(factors, active_detections, now)
        # mass_entity_burst feeds only the generic catch-all below.
        self._add_generic_open_detections_factor(factors, active_detections)

        factors.sort(key=lambda f: f["points"], reverse=True)
        raw_score = sum(f["points"] for f in factors)
        score = int(round(min(max(raw_score, USER_SCORE_MIN), USER_SCORE_MAX)))
        self._reconcile_applied_points(factors, raw_score, score)

        return {
            "user_id": user["id"],
            "score": score,
            "band": _band_for_score(score),
            "factors": factors,
        }

    @staticmethod
    def _reconcile_applied_points(
        factors: list[dict[str, Any]], raw_score: float, score: int
    ) -> None:
        """Give every factor an `applied_points` that sums exactly to `score`.

        Shares are proportional, rounded to one decimal, with the rounding
        residue folded into the largest factor.
        """
        if not factors:
            return
        if raw_score <= 0:
            for factor in factors:
                factor["applied_points"] = 0.0
            return
        scale = score / raw_score
        for factor in factors:
            factor["applied_points"] = round(factor["points"] * scale, 1)
        residue = round(score - sum(f["applied_points"] for f in factors), 1)
        if residue:
            largest = max(factors, key=lambda f: f["applied_points"])
            largest["applied_points"] = round(largest["applied_points"] + residue, 1)

    @staticmethod
    def _add_success_after_failures_factor(factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_SUCCESS_AFTER_FAILURES]
        if not matches:
            return
        total = min(
            sum(
                _decayed_points(
                    d.get("ts"), now, SUCCESS_AFTER_FAILURES_BASE_POINTS, SUCCESS_AFTER_FAILURES_HALF_LIFE_DAYS
                )
                for d in matches
            ),
            SUCCESS_AFTER_FAILURES_CAP,
        )
        if total >= 1:
            factors.append(
                {
                    "name": "success_after_failed_logins",
                    "points": round(total, 1),
                    "detail": f"{len(matches)} success-after-failed-login detection(s)",
                }
            )

    @staticmethod
    def _add_new_ip_login_factor(factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_NEW_IP_LOGIN]
        if not matches:
            return
        total = 0.0
        for d in matches:
            ip = d.get("ip") or (d.get("detail") or {}).get("ip")
            base = NEW_IP_LOGIN_PUBLIC_BASE_POINTS if _is_public_ip(ip) else NEW_IP_LOGIN_BASE_POINTS
            total += _decayed_points(d.get("ts"), now, base, NEW_IP_LOGIN_HALF_LIFE_DAYS)
        total = min(total, NEW_IP_LOGIN_CAP)
        if total >= 1:
            factors.append(
                {
                    "name": "new_ip_login",
                    "points": round(total, 1),
                    "detail": f"{len(matches)} new-network login(s)",
                }
            )

    @staticmethod
    def _add_off_hours_factor(factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_OFF_HOURS_ANOMALY]
        if not matches:
            return
        total = min(
            sum(_decayed_points(d.get("ts"), now, OFF_HOURS_BASE_POINTS, OFF_HOURS_HALF_LIFE_DAYS) for d in matches),
            OFF_HOURS_CAP,
        )
        if total >= 1:
            factors.append(
                {
                    "name": "off_hours_activity",
                    "points": round(total, 1),
                    "detail": f"{len(matches)} off-hours burst(s)",
                }
            )

    def _add_privilege_escalation_factor(self, factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_PRIVILEGE_ESCALATION]
        if not matches:
            return
        total = 0
        for d in matches:
            ts = dt_util.parse_datetime(d.get("ts", ""))
            if ts is None:
                continue
            days_since = (now - ts).days
            total += PRIVILEGE_ESCALATION_POINTS if days_since <= PRIVILEGE_ESCALATION_WINDOW_DAYS else 0
        # Capped by the rule's tunable risk_cap_points.
        total = min(
            total,
            thresholds(self.store, RULE_PRIVILEGE_ESCALATION)["risk_cap_points"],
        )
        if total >= 1:
            factors.append(
                {
                    "name": "privilege_escalation",
                    "points": total,
                    "detail": (
                        f"{len(matches)} privilege escalation event(s) logged - "
                        "always logged, not proof of compromise; legitimate "
                        "promotions look identical"
                    ),
                }
            )

    @staticmethod
    def _add_token_minting_factor(factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_TOKEN_MINTING_ANOMALY]
        if not matches:
            return
        total = min(
            sum(
                _decayed_points(d.get("ts"), now, TOKEN_MINTING_BASE_POINTS, TOKEN_MINTING_HALF_LIFE_DAYS)
                for d in matches
            ),
            TOKEN_MINTING_CAP,
        )
        if total >= 1:
            factors.append(
                {
                    "name": "token_minting_anomaly",
                    "points": round(total, 1),
                    "detail": f"{len(matches)} token-minting burst(s)",
                }
            )

    def _add_disabled_user_activity_factor(self, factors, detections, now) -> None:
        matches = [d for d in detections if d.get("rule_id") == RULE_DISABLED_USER_ACTIVITY]
        if not matches:
            return
        total = 0.0
        for d in matches:
            if d.get("status") == "open":
                total += DISABLED_USER_ACTIVITY_OPEN_POINTS
            else:
                total += _decayed_points(
                    d.get("ts"), now, DISABLED_USER_ACTIVITY_OPEN_POINTS, DISABLED_USER_ACTIVITY_HALF_LIFE_DAYS
                )
        # Capped by the rule's tunable risk_cap_points.
        total = min(
            total,
            thresholds(self.store, RULE_DISABLED_USER_ACTIVITY)["risk_cap_points"],
        )
        if total >= 1:
            factors.append(
                {
                    "name": "disabled_user_activity",
                    "points": round(total, 1),
                    "detail": f"{len(matches)} activity attempt(s) by this disabled account",
                }
            )

    @staticmethod
    def _add_generic_open_detections_factor(factors, detections) -> None:
        open_detections = [d for d in detections if d.get("status") == "open"]
        if not open_detections:
            return
        total = min(
            sum(GENERIC_OPEN_DETECTION_SEVERITY_POINTS.get(d.get("severity"), 0) for d in open_detections),
            GENERIC_OPEN_DETECTION_CAP,
        )
        if total >= 1:
            factors.append(
                {
                    "name": "open_detections",
                    "points": total,
                    "detail": f"{len(open_detections)} open detection(s) across all rules",
                }
            )

    async def async_compute_posture(self) -> dict[str, Any]:
        # Recompute risk first so P_user reflects current state, not the last cached pass.
        risk_results = await self.async_recompute_all()
        users = await self.users.async_list_users()

        p_user = self._compute_p_user(users, risk_results)
        p_vuln = self._compute_p_vuln()
        p_misconfig = self._compute_p_misconfig()
        p_integration = self._compute_p_integration()
        p_detection = self._compute_p_detection()

        raw_score = 100 - round(
            POSTURE_WEIGHT_USER * p_user
            + POSTURE_WEIGHT_VULN * p_vuln
            + POSTURE_WEIGHT_MISCONFIG * p_misconfig
            + POSTURE_WEIGHT_INTEGRATION * p_integration
            + POSTURE_WEIGHT_DETECTION * p_detection
        )
        posture_score = int(min(max(raw_score, POSTURE_SCORE_MIN), POSTURE_SCORE_MAX))
        grade = _grade_for_score(posture_score)

        term_computed_at = self._update_posture_terms()
        missing_terms = [t for t in POSTURE_TERMS if term_computed_at.get(t) is None]

        result = {
            "score": posture_score,
            "grade": grade,
            # The grade always shows, labeled provisional until every term has computed once.
            "provisional": bool(missing_terms),
            "missing_terms": missing_terms,
            "term_computed_at": term_computed_at,
            "breakdown": {
                "p_user": round(p_user, 1),
                "p_vuln": p_vuln,
                "p_misconfig": p_misconfig,
                "p_integration": p_integration,
                "p_detection": p_detection,
            },
        }

        self._maybe_append_posture_snapshot(posture_score, grade)

        self.last_posture_result = result
        return result

    def _update_posture_terms(self) -> dict[str, str | None]:
        """Stamp newly-computable terms and return term -> first computed_at.

        Stamps persist in the store, so a term that has computed once never
        turns provisional again.
        """
        now_iso = dt_util.utcnow().isoformat()
        data = self.store.data
        evidence = {
            POSTURE_TERM_USER: True,
            POSTURE_TERM_VULN: bool(data.get("vuln_findings")),
            POSTURE_TERM_MISCONFIG: bool(data.get("misconfig_findings")),
            POSTURE_TERM_INTEGRATION: bool(data.get("integration_health")),
            POSTURE_TERM_DETECTION: bool(
                data.get("detections_meta", {}).get("last_pass_completed_at")
            ),
        }
        for term, ready in evidence.items():
            if ready:
                self.store.async_mark_posture_term_computed(term, now_iso)
        stamped = data.get("posture_terms", {})
        return {term: stamped.get(term) for term in POSTURE_TERMS}

    @staticmethod
    def _compute_p_user(users: list[dict[str, Any]], risk_results: dict[str, dict[str, Any]]) -> float:
        if not users:
            return 0.0
        weighted_total = 0.0
        weight_sum = 0.0
        for user in users:
            weight = ADMIN_POSTURE_WEIGHT_MULTIPLIER if user.get("is_admin") else 1
            score = risk_results.get(user["id"], {}).get("score", 0)
            weighted_total += score * weight
            weight_sum += weight
        return weighted_total / weight_sum if weight_sum else 0.0

    def _compute_p_vuln(self) -> int:
        total = 0
        for finding in self.store.data.get("vuln_findings", {}).values():
            if finding.get("status") == VULN_EXCLUDED_STATUS:
                continue
            cvss = finding.get("cvss")
            if cvss is None:
                total += VULN_POINTS_LOW
            elif cvss >= VULN_CVSS_CRITICAL_THRESHOLD:
                total += VULN_POINTS_CRITICAL
            elif cvss >= VULN_CVSS_HIGH_THRESHOLD:
                total += VULN_POINTS_HIGH
            elif cvss >= VULN_CVSS_MEDIUM_THRESHOLD:
                total += VULN_POINTS_MEDIUM
            else:
                total += VULN_POINTS_LOW
        return min(total, P_VULN_CAP)

    def _compute_p_misconfig(self) -> int:
        total = 0
        for finding in self.store.data.get("misconfig_findings", {}).values():
            if finding.get("status") in MISCONFIG_INCLUDED_STATUSES:
                total += MISCONFIG_SEVERITY_POINTS.get(finding.get("severity"), 0)
        return min(total, P_MISCONFIG_CAP)

    def _compute_p_integration(self) -> int:
        entries = list(self.store.data.get("integration_health", {}).values())
        setup_error_count = sum(1 for e in entries if e.get("state") == "setup_error")
        high_error_count = sum(
            1 for e in entries if e.get("error_count_24h", 0) >= INTEGRATION_HIGH_ERROR_COUNT_THRESHOLD
        )
        mean_unavailable_ratio = (
            sum(e.get("unavailable_ratio", 0.0) for e in entries) / len(entries) if entries else 0.0
        )
        raw = (
            INTEGRATION_SETUP_ERROR_POINTS * setup_error_count
            + INTEGRATION_HIGH_ERROR_POINTS * high_error_count
            + INTEGRATION_UNAVAILABLE_RATIO_WEIGHT * mean_unavailable_ratio
        )
        return min(P_INTEGRATION_CAP, round(raw))

    def _compute_p_detection(self) -> int:
        total = 0
        for detection in self.store.data.get("detections", {}).values():
            if detection.get("status") == "open":
                total += DETECTION_SEVERITY_POSTURE_POINTS.get(detection.get("severity"), 0)
        return min(total, P_DETECTION_CAP)

    def _maybe_append_posture_snapshot(self, posture_score: int, grade: str) -> None:
        # At most one snapshot per calendar day.
        today = dt_util.now().strftime("%Y-%m-%d")
        history = self.store.data["posture_history"]
        if history and history[-1].get("date") == today:
            return
        self.store.async_append_posture_snapshot(
            {"date": today, "score": posture_score, "grade": grade},
            max_days=POSTURE_HISTORY_MAX_DAYS,
        )
