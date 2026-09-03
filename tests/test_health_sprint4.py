"""Sprint 4 health.py behaviors (work plan items 4.1, 4.2, 4.4, 4.7):
startup grace, protected confirmations, could_not_evaluate honesty, the
proxy trust check, trusted_users privilege mapping, finding lifecycle
status, dismissed-finding Repairs cleanup, and the one-YAML-load-per-sweep
guarantee.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from ipaddress import ip_network
from unittest.mock import AsyncMock, PropertyMock, patch

import pytest

import homeassistant.helpers.issue_registry as ir
import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.audit import BAN_LOGGER_NAME
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import STARTUP_GRACE, IntegrationHealth, _new_finding
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationHealth(hass, store)


async def test_sweep_respects_startup_grace(hass: HomeAssistant, health: IntegrationHealth) -> None:
    spy = AsyncMock(return_value=[])
    with patch.object(health, "_check_http_insecure", spy):
        # HA has not finished starting: nothing runs.
        health._started_at = None
        assert await health.async_run_misconfig_checks() == []
        spy.assert_not_called()

        # Started, but still inside the grace window: nothing runs.
        health._started_at = dt_util.utcnow() - timedelta(seconds=30)
        assert await health.async_run_misconfig_checks() == []
        spy.assert_not_called()

        # Grace has passed: the sweep runs its checks.
        health._started_at = dt_util.utcnow() - STARTUP_GRACE - timedelta(seconds=1)
        await health.async_run_misconfig_checks()
        spy.assert_awaited()


async def test_confirmed_survives_empty_pass(hass: HomeAssistant, health: IntegrationHealth) -> None:
    logger = logging.getLogger(BAN_LOGGER_NAME)
    previous = logger.level
    try:
        logger.setLevel(logging.ERROR)
        findings = await health._check_audit_ban_logger()
        assert len(findings) == 1
        finding_id = findings[0]["id"]

        # An analyst confirms the finding; the next pass sees the
        # condition gone but must not override the analyst's verdict.
        health._store.async_set_finding_status(
            "misconfig_findings", finding_id, "confirmed",
            by_user_id="u1", note=None, at=dt_util.utcnow().isoformat(),
        )
        logger.setLevel(logging.WARNING)
        assert await health._check_audit_ban_logger() == []
        stored = health._store.data["misconfig_findings"][finding_id]
        assert stored["status"] == "confirmed"
    finally:
        logger.setLevel(previous)


async def test_could_not_evaluate_leaves_findings(hass: HomeAssistant, health: IntegrationHealth) -> None:
    from homeassistant.exceptions import HomeAssistantError

    # A prior pass recorded a broken alert reference.
    fake_config = {
        "alert": {"broken": {"name": "Broken", "entity_id": "binary_sensor.gone", "notifiers": []}}
    }
    with patch("homeassistant.config.async_hass_config_yaml", return_value=fake_config):
        findings = await health._check_alert_unknown_references()
    assert len(findings) == 1
    finding_id = findings[0]["id"]

    # The next pass cannot load the YAML at all: the check must report
    # nothing AND leave the stored finding exactly as it was, because a
    # failed load is not evidence the alert got fixed.
    health._sweep_yaml_state = "stale"
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        side_effect=HomeAssistantError("broken yaml"),
    ):
        assert await health._check_alert_unknown_references() == []
    stored = health._store.data["misconfig_findings"][finding_id]
    assert stored["status"] == "new"


async def test_proxy_trust_check(hass: HomeAssistant, health: IntegrationHealth) -> None:
    async def _run(http_conf: dict) -> dict | None:
        health._sweep_yaml_state = "stale"
        with patch(
            "homeassistant.config.async_hass_config_yaml",
            return_value={"http": http_conf},
        ):
            findings = await health._check_http_hardening()
        for finding in findings:
            if finding["id"] == "misconfig:http_hardening:proxy_trust":
                return finding
        return None

    # use_x_forwarded_for with no trusted_proxies at all: HIGH.
    finding = await _run({"use_x_forwarded_for": True})
    assert finding is not None
    assert finding["severity"] == "high"

    # An any-address network: HIGH.
    finding = await _run({"use_x_forwarded_for": True, "trusted_proxies": ["0.0.0.0/0"]})
    assert finding is not None
    assert "every address" in finding["summary"]

    # Broader than /24 (IPv4) or /64 (IPv6): HIGH.
    assert await _run({"use_x_forwarded_for": True, "trusted_proxies": ["10.0.0.0/8"]}) is not None
    assert await _run({"use_x_forwarded_for": True, "trusted_proxies": ["fd00::/48"]}) is not None

    # A narrow list is fine, and the finding resolves.
    assert await _run(
        {"use_x_forwarded_for": True, "trusted_proxies": ["127.0.0.1/32", "fd00::1/128"]}
    ) is None
    stored = health._store.data["misconfig_findings"]["misconfig:http_hardening:proxy_trust"]
    assert stored["status"] == "resolved"

    # Without use_x_forwarded_for, a broad list changes nothing.
    assert await _run({"trusted_proxies": ["10.0.0.0/8"]}) is None


async def test_narrow_proxy_quiets_no_ssl_finding(hass: HomeAssistant, health: IntegrationHealth) -> None:
    hass.config.external_url = "https://example.invalid"

    async def _no_ssl(http_conf: dict) -> dict:
        health._sweep_yaml_state = "stale"
        with patch(
            "homeassistant.config.async_hass_config_yaml",
            return_value={"http": http_conf},
        ):
            findings = await health._check_http_insecure()
        return next(f for f in findings if f["id"] == "misconfig:http_insecure:no_ssl")

    # No proxy configuration: the LOW finding stands.
    finding = await _no_ssl({})
    assert finding["severity"] == "low"

    # A truthy use_x_forwarded_for with a narrow list quiets it to INFO
    # with the explanatory note.
    finding = await _no_ssl({"use_x_forwarded_for": True, "trusted_proxies": ["127.0.0.1/32"]})
    assert finding["severity"] == "info"
    assert "reverse proxy" in finding["summary"]

    # A broad list does NOT quiet it.
    finding = await _no_ssl({"use_x_forwarded_for": True, "trusted_proxies": ["10.0.0.0/8"]})
    assert finding["severity"] == "low"


class _FakeProvider:
    type = "trusted_networks"
    id = "tn"

    def __init__(self, trusted_users: dict) -> None:
        self.trusted_networks = [ip_network("192.168.1.0/24")]
        self.config = {"allow_bypass_login": False}
        self.trusted_users = trusted_users


async def test_trusted_users_admin_mapping(hass: HomeAssistant, health: IntegrationHealth, hass_admin_user) -> None:
    provider = _FakeProvider({ip_network("192.168.1.0/24"): [hass_admin_user.id]})
    with patch.object(
        type(hass.auth), "auth_providers", new_callable=PropertyMock, return_value=[provider]
    ):
        findings = await health._check_trusted_networks()

    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert any("admin account" in r for r in findings[0]["detail"]["privileged_trusted_users"])


async def test_trusted_users_admin_group_mapping(hass: HomeAssistant, health: IntegrationHealth) -> None:
    provider = _FakeProvider({ip_network("192.168.1.0/24"): [{"group": "system-admin"}]})
    with patch.object(
        type(hass.auth), "auth_providers", new_callable=PropertyMock, return_value=[provider]
    ):
        findings = await health._check_trusted_networks()

    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert any("admin group" in r for r in findings[0]["detail"]["privileged_trusted_users"])


async def test_trusted_users_non_admin_mapping_is_quiet(hass: HomeAssistant, health: IntegrationHealth) -> None:
    # Core makes the very first user created the owner, so an owner is
    # created first and the mapped user is a genuinely plain account.
    await hass.auth.async_create_user("The Owner", group_ids=["system-admin"])
    user = await hass.auth.async_create_user("Plain User", group_ids=["system-users"])
    assert not user.is_admin and not user.is_owner
    provider = _FakeProvider({ip_network("192.168.1.0/24"): [user.id]})
    with patch.object(
        type(hass.auth), "auth_providers", new_callable=PropertyMock, return_value=[provider]
    ):
        findings = await health._check_trusted_networks()
    assert findings == []


def test_new_finding_has_status() -> None:
    finding = _new_finding(
        "misconfig:x", "x", "low", title="t", summary="s", detail={}
    )
    assert finding["status"] == "new"


async def test_dismiss_removes_repair(hass: HomeAssistant, health: IntegrationHealth) -> None:
    logger = logging.getLogger(BAN_LOGGER_NAME)
    previous = logger.level
    try:
        logger.setLevel(logging.ERROR)
        findings = await health._check_audit_ban_logger()
        finding_id = findings[0]["id"]
        registry = ir.async_get(hass)
        assert any(
            i.issue_id == finding_id for i in registry.issues.values() if i.domain == DOMAIN
        )

        # The analyst dismisses it; the condition persists, but the next
        # sweep pass must delete the Repairs issue instead of re-raising
        # it, while the table row keeps the dismissed status.
        health._store.async_set_finding_status(
            "misconfig_findings", finding_id, "dismissed",
            by_user_id="u1", note=None, at=dt_util.utcnow().isoformat(),
        )
        await health._check_audit_ban_logger()
        assert not any(
            i.issue_id == finding_id for i in registry.issues.values() if i.domain == DOMAIN
        )
        assert health._store.data["misconfig_findings"][finding_id]["status"] == "dismissed"
    finally:
        logger.setLevel(previous)


async def test_detail_item_lists_are_capped_with_total_count(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    items = [{"n": i} for i in range(150)]
    findings = health._async_hygiene_finding(
        "unknown_service_references", "medium", "t", "s", items
    )
    detail = findings[0]["detail"]
    assert len(detail["items"]) == 100
    assert detail["total_count"] == 150


async def test_unknown_repairs_severity_maps_to_warning(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    finding = _new_finding(
        "misconfig:weird", "weird", "catastrophic", title="t", summary="s", detail={}
    )
    health._async_mirror_to_repairs(finding, "misconfig_finding", {"title": "t", "summary": "s"})
    registry = ir.async_get(hass)
    issue = next(
        i for i in registry.issues.values()
        if i.domain == DOMAIN and i.issue_id == "misconfig:weird"
    )
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_yaml_loaded_once_per_sweep(hass: HomeAssistant, health: IntegrationHealth) -> None:
    health._started_at = dt_util.utcnow() - STARTUP_GRACE - timedelta(seconds=1)
    loader = AsyncMock(return_value={"http": {}, "alert": {}, "homeassistant": {}})
    with patch("homeassistant.config.async_hass_config_yaml", loader):
        await health.async_run_misconfig_checks()
    assert loader.await_count == 1

    # The next sweep loads exactly once again (the cache is per sweep,
    # not forever).
    with patch("homeassistant.config.async_hass_config_yaml", loader):
        await health.async_run_misconfig_checks()
    assert loader.await_count == 2


async def test_failed_yaml_load_warns_once_per_sweep(
    hass: HomeAssistant, health: IntegrationHealth, caplog
) -> None:
    from homeassistant.exceptions import HomeAssistantError

    health._started_at = dt_util.utcnow() - STARTUP_GRACE - timedelta(seconds=1)
    loader = AsyncMock(side_effect=HomeAssistantError("broken"))
    with patch("homeassistant.config.async_hass_config_yaml", loader), caplog.at_level(
        logging.WARNING
    ):
        await health.async_run_misconfig_checks()
    assert loader.await_count == 1
    warnings = [
        r for r in caplog.records
        if "could not load the merged YAML configuration" in r.getMessage()
    ]
    assert len(warnings) == 1
