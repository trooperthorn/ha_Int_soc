"""Access-control regression test for sensor.py's per-user risk entity.

Every ha_soc/* websocket command is gated by require_soc_access (admin,
plus the access_level owner-only/owner+admin setting) — but Home Assistant
core has no equivalent per-user read ACL for entity states/attributes.
sensor.ha_soc_risk_<user_id> is readable by ANY authenticated user,
including a non-admin, local-only account, regardless of access_level.
UserRiskSensor must therefore never put another user's account-security
detail (MFA status, long-lived-token count/age, specific flagged
behavior — risk.py's `factors` list) into its entity attributes; only the
coarse `band` belongs there.
"""
from types import SimpleNamespace

from custom_components.ha_soc.sensor import PostureScoreSensor, UserRiskSensor


def _runtime_with_risk_result(result: dict) -> SimpleNamespace:
    risk = SimpleNamespace(last_risk_results={"u-target": result})
    return SimpleNamespace(risk=risk)


def test_user_risk_sensor_does_not_expose_factors() -> None:
    runtime = _runtime_with_risk_result(
        {
            "score": 62,
            "band": "high",
            "factors": [
                {"name": "admin_without_mfa", "points": 20, "detail": "Administrator account has no MFA module enabled"},
                {"name": "long_lived_token_load", "points": 10, "detail": "3 long-lived access token(s), oldest 400d"},
            ],
        }
    )
    sensor = UserRiskSensor(runtime, "u-target")

    assert sensor.native_value == 62
    attrs = sensor.extra_state_attributes
    assert attrs == {"band": "high"}
    assert "factors" not in attrs
    assert "top_factors" not in attrs
    serialized = str(attrs)
    assert "MFA" not in serialized
    assert "token" not in serialized


def test_user_risk_sensor_missing_result_reports_no_band() -> None:
    runtime = _runtime_with_risk_result({"score": 62, "band": "high", "factors": []})
    sensor = UserRiskSensor(runtime, "u-someone-else")

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {"band": None}
    assert sensor.available is False


def test_user_risk_sensor_name_derives_from_user_id() -> None:
    """Work item 3.10 (D-19): the name (and therefore the entity id) comes
    from the immutable user id, not the mutable display name, so two users
    can never collide onto one base entity id."""
    runtime = _runtime_with_risk_result({"score": 1, "band": "low", "factors": []})
    sensor = UserRiskSensor(runtime, "abcdef1234567890")
    assert sensor._attr_name == "Risk abcdef12"

    other = UserRiskSensor(runtime, "fedcba0987654321")
    assert other._attr_name == "Risk fedcba09"
    assert other._attr_name != sensor._attr_name


def test_posture_sensor_exposes_grade_only() -> None:
    """Work item 3.10 (D-19 option (a)): the posture sensor's attributes
    carry the grade and nothing else - the per-term breakdown maps where
    the install is weakest and stays behind the gated WS command."""
    posture = {
        "score": 82,
        "grade": "B",
        "provisional": False,
        "missing_terms": [],
        "breakdown": {"p_user": 30.0, "p_vuln": 12, "p_misconfig": 4, "p_integration": 0, "p_detection": 15},
    }
    runtime = SimpleNamespace(risk=SimpleNamespace(last_posture_result=posture))
    sensor = PostureScoreSensor(runtime)

    assert sensor.native_value == 82
    assert sensor.extra_state_attributes == {"grade": "B"}
    serialized = str(sensor.extra_state_attributes)
    assert "breakdown" not in serialized
    assert "p_user" not in serialized
