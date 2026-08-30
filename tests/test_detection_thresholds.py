"""Work item 3.0 (D-9): tunable detection thresholds with secure defaults.

The shipped parameter table, its range validation, the audit trail on a
change, the one-action reset, and the migration that replaced
risk_learning_period_days with the two per-rule learning_days fields.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.detections import (
    THRESHOLD_SPECS,
    secure_default_thresholds,
    thresholds,
)
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.websocket_api import (
    ws_detections_thresholds_get,
    ws_detections_thresholds_reset,
    ws_settings_set,
)

# The work plan's item 3.0 table, transcribed: rule -> parameter ->
# (secure default, min, max). Booleans carry no range.
PLAN_TABLE = {
    "brute_force_ip": {
        "failures": (5, 3, 100),
        "window_minutes": (15, 5, 120),
    },
    "success_after_failures": {
        "failures": (3, 2, 50),
        "window_minutes": (30, 5, 240),
        "require_new_token": (True, None, None),
        "derate_shared_ip": (True, None, None),
    },
    "new_ip_login": {
        "ipv4_prefix": (24, 16, 32),
        "ipv6_prefix": (64, 32, 128),
        "baseline_days_required": (3, 1, 30),
        "prefix_expiry_days": (90, 30, 730),
        "learning_days": (7, 1, 90),
    },
    "off_hours_anomaly": {
        "quiet_start_hour": (23, 0, 23),
        "quiet_end_hour": (6, 0, 23),
        "burst_threshold": (5, 2, 100),
        "ratio_threshold": (0.01, 0.001, 0.2),
        "learning_days": (7, 1, 90),
    },
    "dormant_revival": {
        "dormant_days": (30, 7, 365),
        "min_account_age_days": (60, 7, 365),
    },
    "mass_entity_burst": {
        "calls": (20, 5, 500),
        "distinct_entities": (10, 2, 200),
        "window_minutes": (5, 1, 60),
    },
    "token_minting_anomaly": {
        "tokens": (2, 2, 20),
        "window_hours": (24, 1, 168),
    },
    "disabled_user_activity": {
        "risk_cap_points": (40, 10, 100),
    },
    "privilege_escalation": {
        "risk_cap_points": (24, 8, 100),
    },
}


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner1")
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant, tmp_path) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    # The harness's config dir is shared across tests, so the audit chain
    # would otherwise accumulate records from every test in the session;
    # point this entry's audit log at a per-test directory (same isolation
    # trick test_audit.py uses).
    config_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    return config_entry


def test_thresholds_defaults_are_secure() -> None:
    """THRESHOLD_SPECS matches the plan's table exactly: same rules, same
    parameters, same secure defaults, same inclusive ranges."""
    assert set(THRESHOLD_SPECS) == set(PLAN_TABLE)
    for rule, params in PLAN_TABLE.items():
        assert set(THRESHOLD_SPECS[rule]) == set(params), rule
        for name, (default, minimum, maximum) in params.items():
            spec = THRESHOLD_SPECS[rule][name]
            assert spec["default"] == default, f"{rule}.{name} default"
            if minimum is None:
                assert isinstance(spec["default"], bool), f"{rule}.{name} bool"
                assert "min" not in spec and "max" not in spec
            else:
                assert spec["min"] == minimum, f"{rule}.{name} min"
                assert spec["max"] == maximum, f"{rule}.{name} max"


async def test_thresholds_helper_merges_over_defaults(hass: HomeAssistant) -> None:
    """A missing key never means off: stored overrides merge OVER the
    secure defaults, unknown stored keys are ignored."""
    store = HaSocData(hass)
    await store.async_load()

    assert thresholds(store, "brute_force_ip") == secure_default_thresholds(
        "brute_force_ip"
    )

    store.async_update_settings(
        detection_thresholds={
            "brute_force_ip": {"failures": 12, "not_a_real_param": 1}
        }
    )
    effective = thresholds(store, "brute_force_ip")
    assert effective["failures"] == 12
    assert effective["window_minutes"] == 15
    assert "not_a_real_param" not in effective


def test_thresholds_range_validation() -> None:
    """The settings schema accepts in-range values and rejects everything
    else - out-of-range numbers, unknown rules, unknown parameters."""
    schema = ws_settings_set._ws_schema

    def msg(payload):
        return {"id": 1, "type": "ha_soc/settings/set", "detection_thresholds": payload}

    validated = schema(msg({"brute_force_ip": {"failures": 3}}))
    assert validated["detection_thresholds"]["brute_force_ip"]["failures"] == 3
    schema(msg({"brute_force_ip": {"failures": 100}}))
    schema(msg({"off_hours_anomaly": {"ratio_threshold": 0.2}}))
    schema(msg({"success_after_failures": {"require_new_token": False}}))

    with pytest.raises(vol.Invalid):
        schema(msg({"brute_force_ip": {"failures": 2}}))  # below min 3
    with pytest.raises(vol.Invalid):
        schema(msg({"brute_force_ip": {"failures": 101}}))  # above max 100
    with pytest.raises(vol.Invalid):
        schema(msg({"off_hours_anomaly": {"ratio_threshold": 0.5}}))
    with pytest.raises(vol.Invalid):
        schema(msg({"no_such_rule": {"failures": 5}}))
    with pytest.raises(vol.Invalid):
        schema(msg({"brute_force_ip": {"no_such_param": 5}}))


async def test_thresholds_change_is_audited(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A threshold change lands as soc_config_change with a per-field diff
    against the previously effective value."""
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/settings/set",
            "detection_thresholds": {"brute_force_ip": {"failures": 20}},
        },
    )
    await hass.async_block_till_done()

    store = entry.runtime_data.store
    assert store.settings["detection_thresholds"]["brute_force_ip"]["failures"] == 20
    assert thresholds(store, "brute_force_ip")["failures"] == 20
    # The merge is per field: window_minutes keeps its secure default.
    assert thresholds(store, "brute_force_ip")["window_minutes"] == 15

    # soc_config_change is an immediate-flush category, so the record has
    # already left the in-memory buffer; read it back through the log.
    records = [
        r
        for r in await entry.runtime_data.audit.async_query(
            category="soc_config_change"
        )
        if r["detail"].get("action") == "settings_changed"
    ]
    assert records
    diff = records[0]["detail"]["changes"]["detection_thresholds"]
    assert diff == {"brute_force_ip.failures": {"old": 5, "new": 20}}


async def test_reset_to_secure_defaults(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    store.async_update_settings(
        detection_thresholds={
            "brute_force_ip": {"failures": 20},
            "new_ip_login": {"learning_days": 30},
        }
    )

    connection = _connection()
    ws_detections_thresholds_reset(
        hass, connection, {"id": 1, "type": "ha_soc/detections/thresholds_reset"}
    )
    await hass.async_block_till_done()

    assert store.settings["detection_thresholds"] == {}
    assert thresholds(store, "brute_force_ip")["failures"] == 5
    assert thresholds(store, "new_ip_login")["learning_days"] == 7

    records = [
        r
        for r in await entry.runtime_data.audit.async_query(
            category="soc_config_change"
        )
        if r["detail"].get("action") == "detection_thresholds_reset"
    ]
    assert len(records) == 1
    assert records[0]["detail"]["changes"] == {
        "brute_force_ip.failures": {"old": 20, "new": 5},
        "new_ip_login.learning_days": {"old": 30, "new": 7},
    }

    # The command answers with the effective table so the UI re-renders
    # without a second round trip.
    result = connection.send_result.call_args[0][1]
    assert result["rules"]["brute_force_ip"]["failures"]["value"] == 5


async def test_thresholds_get_reports_table_and_effective_values(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    entry.runtime_data.store.async_update_settings(
        detection_thresholds={"token_minting_anomaly": {"tokens": 9}}
    )
    connection = _connection()
    ws_detections_thresholds_get(
        hass, connection, {"id": 1, "type": "ha_soc/detections/thresholds"}
    )
    await hass.async_block_till_done()

    rules = connection.send_result.call_args[0][1]["rules"]
    assert rules["token_minting_anomaly"]["tokens"] == {
        "value": 9,
        "default": 2,
        "min": 2,
        "max": 20,
        "type": "int",
    }
    assert rules["success_after_failures"]["require_new_token"]["type"] == "bool"
    assert rules["off_hours_anomaly"]["ratio_threshold"]["type"] == "float"


async def test_learning_period_setting_is_used(hass: HomeAssistant) -> None:
    """The legacy risk_learning_period_days migrates into BOTH per-rule
    learning_days overrides once, and the rules read the migrated value."""
    store = HaSocData(hass)
    await store.async_load()
    legacy_settings = dict(store.data["settings"])
    legacy_settings.pop("detection_thresholds", None)
    legacy_settings["risk_learning_period_days"] = 21
    store.data["settings"] = legacy_settings
    await store.async_save_now()

    store2 = HaSocData(hass)
    assert await store2.async_load() is True
    assert "risk_learning_period_days" not in store2.settings
    assert thresholds(store2, "new_ip_login")["learning_days"] == 21
    assert thresholds(store2, "off_hours_anomaly")["learning_days"] == 21


async def test_migration_never_clobbers_explicit_learning_days(
    hass: HomeAssistant,
) -> None:
    store = HaSocData(hass)
    await store.async_load()
    legacy_settings = dict(store.data["settings"])
    legacy_settings["risk_learning_period_days"] = 21
    legacy_settings["detection_thresholds"] = {"new_ip_login": {"learning_days": 3}}
    store.data["settings"] = legacy_settings
    await store.async_save_now()

    store2 = HaSocData(hass)
    assert await store2.async_load() is True
    # The explicitly-set per-rule value wins; only the unset rule inherits.
    assert thresholds(store2, "new_ip_login")["learning_days"] == 3
    assert thresholds(store2, "off_hours_anomaly")["learning_days"] == 21
