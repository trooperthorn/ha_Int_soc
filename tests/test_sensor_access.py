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

from custom_components.ha_soc.sensor import UserRiskSensor


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
