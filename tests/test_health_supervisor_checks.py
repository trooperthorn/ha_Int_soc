"""Tests for health.py's Supervisor-dependent checks and the config-check.

_check_addon_protection_mode / _check_ssh_addon_inventory both do local
imports of is_hassio/get_addons_info from inside health.py, so patching
the source modules (rather than health.py's own namespace) works — unlike
probe.py, which imports is_hassio at module scope.

The SEC-7 boundary-widening checks and 1.7's ban-logger check are covered
here too, since they follow the same Supervisor/finding patterns.
"""
import json
import logging
import os
from datetime import timedelta
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from custom_components.ha_soc.audit import BAN_LOGGER_NAME
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    return IntegrationHealth(hass, store)


async def test_addon_checks_are_empty_off_supervisor(hass: HomeAssistant, health: IntegrationHealth) -> None:
    protection_findings = await health._check_addon_protection_mode()
    ssh_findings = await health._check_ssh_addon_inventory()
    assert protection_findings == []
    assert ssh_findings == []


async def test_unprotected_addon_flagged(hass: HomeAssistant, health: IntegrationHealth) -> None:
    fake_addons = {
        "local_some_addon": {"name": "Some Addon", "protected": False},
        "core_mosquitto": {"name": "Mosquitto broker", "protected": True},
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_addon_protection_mode()

    assert len(findings) == 1
    assert findings[0]["check"] == "addon_unprotected"
    assert "Some Addon" in findings[0]["title"]


async def test_protected_addons_produce_no_finding(hass: HomeAssistant, health: IntegrationHealth) -> None:
    fake_addons = {"core_mosquitto": {"name": "Mosquitto broker", "protected": True}}
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_addon_protection_mode()
    assert findings == []


async def test_ssh_addon_inventory_matches_by_slug_and_name(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    fake_addons = {
        "core_ssh": {"name": "Terminal & SSH", "state": "started"},
        "some_repo_my_ssh_tunnel": {"name": "My SSH Tunnel", "state": "started"},
        "core_mosquitto": {"name": "Mosquitto broker", "state": "started"},
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_ssh_addon_inventory()

    assert len(findings) == 1
    matched_slugs = {a["slug"] for a in findings[0]["detail"]["addons"]}
    assert matched_slugs == {"core_ssh", "some_repo_my_ssh_tunnel"}


async def test_ssh_addon_not_exposed_by_default_produces_no_finding(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    # core_ssh's real shipped default: ingress-only, port unbound.
    fake_addons = {
        "core_ssh": {
            "name": "Terminal & SSH",
            "state": "started",
            "host_network": False,
            "network": {"22/tcp": None},
            "ingress": True,
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_ssh_addon_exposed()
    assert findings == []


async def test_ssh_addon_with_published_port_is_flagged(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    fake_addons = {
        "core_ssh": {
            "name": "Terminal & SSH",
            "state": "started",
            "host_network": False,
            "network": {"22/tcp": 2222},
            "ingress": True,
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_ssh_addon_exposed()
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert findings[0]["detail"]["published_ports"] == [2222]


async def test_ssh_addon_with_host_network_is_flagged(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    fake_addons = {
        "some_repo_ssh_terminal": {
            "name": "SSH Terminal",
            "state": "started",
            "host_network": True,
            "network": {},
            "ingress": False,
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_ssh_addon_exposed()
    assert len(findings) == 1
    assert findings[0]["detail"]["host_network"] is True


_PROBE_ADDON = {"local_ha_soc_probe": {"name": "HA SOC Probe", "state": "started"}}


async def test_probe_not_reporting_no_finding_off_supervisor(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    findings = await health._check_probe_addon_not_reporting()
    assert findings == []


async def test_probe_not_reporting_no_finding_when_already_reported(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    health._store.data["host_probe"] = {"open_ports": [], "reported_at": dt_util.utcnow().isoformat()}
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=_PROBE_ADDON),
    ):
        findings = await health._check_probe_addon_not_reporting()
    assert findings == []
    assert health._probe_unreported_since is None


async def test_probe_not_reporting_within_grace_produces_no_finding_yet(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=_PROBE_ADDON),
    ):
        findings = await health._check_probe_addon_not_reporting()
    assert findings == []
    # First observation is tracked so a later pass can tell it's overdue.
    assert health._probe_unreported_since is not None


async def test_probe_not_reporting_past_grace_is_flagged(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    health._probe_unreported_since = dt_util.utcnow() - timedelta(minutes=31)
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=_PROBE_ADDON),
    ):
        findings = await health._check_probe_addon_not_reporting()
    assert len(findings) == 1
    assert findings[0]["id"] == "misconfig:probe_addon_not_reporting"
    assert findings[0]["check"] == "probe_addon_not_reporting"


async def test_probe_not_reporting_clears_and_resolves_once_reported(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    health._probe_unreported_since = dt_util.utcnow() - timedelta(minutes=31)
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=_PROBE_ADDON),
    ):
        findings = await health._check_probe_addon_not_reporting()
        assert len(findings) == 1

        health._store.data["host_probe"] = {"open_ports": [], "reported_at": dt_util.utcnow().isoformat()}
        findings = await health._check_probe_addon_not_reporting()

    assert findings == []
    assert health._probe_unreported_since is None
    resolved = health._store.data["misconfig_findings"]["misconfig:probe_addon_not_reporting"]
    assert resolved["status"] == "resolved"


async def test_probe_not_reporting_ignores_stopped_addon(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    stopped = {"local_ha_soc_probe": {"name": "HA SOC Probe", "state": "stopped"}}
    health._probe_unreported_since = dt_util.utcnow() - timedelta(minutes=31)
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=stopped),
    ):
        findings = await health._check_probe_addon_not_reporting()
    assert findings == []
    assert health._probe_unreported_since is None


async def test_ban_logger_level_check(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    """Work item 1.7: silencing http.ban blinds login_fail capture (LOW).

    The logger's level is process-global state, so it is restored no
    matter how the assertions go.
    """
    logger = logging.getLogger(BAN_LOGGER_NAME)
    previous = logger.level
    try:
        logger.setLevel(logging.ERROR)
        findings = await health._check_audit_ban_logger()
        assert len(findings) == 1
        assert findings[0]["check"] == "audit_ban_logger_silenced"
        assert findings[0]["severity"] == "low"
        assert findings[0]["detail"]["logger"] == BAN_LOGGER_NAME

        logger.setLevel(logging.WARNING)
        findings = await health._check_audit_ban_logger()
        assert findings == []
        stored = health._store.data["misconfig_findings"][
            "misconfig:audit_ban_logger_silenced"
        ]
        assert stored["status"] == "resolved"
    finally:
        logger.setLevel(previous)


async def test_storage_file_modes_flagged_with_exact_chmod(
    hass: HomeAssistant, health: IntegrationHealth, tmp_path
) -> None:
    """SEC-7: wide modes on secrets.yaml / .storage are LOW findings whose
    summaries carry the exact chmod command."""
    hass.config.config_dir = str(tmp_path)
    secrets_path = tmp_path / "secrets.yaml"
    secrets_path.write_text("api_key: abc\n")
    os.chmod(secrets_path, 0o644)
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir()
    os.chmod(storage_dir, 0o700)

    findings = await health._check_storage_file_modes()
    assert len(findings) == 1
    assert findings[0]["id"] == "misconfig:storage_file_modes:secrets_yaml"
    assert f"chmod 600 {secrets_path}" in findings[0]["summary"]

    os.chmod(secrets_path, 0o600)
    os.chmod(storage_dir, 0o755)
    findings = await health._check_storage_file_modes()
    assert len(findings) == 1
    assert findings[0]["id"] == "misconfig:storage_file_modes:storage_dir"
    assert f"chmod 700 {storage_dir}" in findings[0]["summary"]

    os.chmod(storage_dir, 0o700)
    findings = await health._check_storage_file_modes()
    assert findings == []


async def test_config_mapping_addons_flagged(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    """SEC-7: the known config-mapping add-ons are flagged by name, MEDIUM
    when ingress-only and HIGH when also reachable on the host network."""
    fake_addons = {
        "core_samba": {
            "name": "Samba share",
            "state": "started",
            "host_network": False,
            "network": {},
        },
        "a0d7b954_ssh": {
            "name": "SSH & Web Terminal",
            "state": "started",
            "host_network": False,
            "network": {"22/tcp": 2222},
        },
        "core_mosquitto": {"name": "Mosquitto broker", "state": "started"},
        # A slug whose info fetch failed this cycle: skipped, not guessed at.
        "broken_addon": None,
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_config_mapping_addons()

    by_slug = {f["detail"]["slug"]: f for f in findings}
    assert set(by_slug) == {"core_samba", "a0d7b954_ssh"}
    assert by_slug["core_samba"]["severity"] == "medium"
    assert by_slug["a0d7b954_ssh"]["severity"] == "high"
    assert by_slug["a0d7b954_ssh"]["detail"]["published_ports"] == [2222]


async def test_config_mapping_addons_skip_when_cache_missing(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    """An unpopulated add-on cache is could-not-evaluate, not all-clear:
    the pass produces nothing and leaves prior findings untouched."""
    health._store.data["misconfig_findings"]["misconfig:config_mapping_addon:x"] = {
        "id": "misconfig:config_mapping_addon:x",
        "check": "config_mapping_addon",
        "severity": "medium",
        "status": "new",
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=None),
    ):
        findings = await health._check_config_mapping_addons()
    assert findings == []
    existing = health._store.data["misconfig_findings"][
        "misconfig:config_mapping_addon:x"
    ]
    assert existing["status"] == "new"


def _write_backup_store(tmp_path, *, password_set: bool, agents: dict) -> None:
    storage_dir = tmp_path / ".storage"
    storage_dir.mkdir(exist_ok=True)
    payload = {
        "version": 1,
        "key": "backup",
        "data": {
            "backups": [],
            "config": {
                "create_backup": {"password": "pw" if password_set else None},
                "agents": agents,
            },
        },
    }
    (storage_dir / "backup").write_text(json.dumps(payload))


async def test_backup_protection_off_is_flagged(
    hass: HomeAssistant, health: IntegrationHealth, tmp_path
) -> None:
    """SEC-7: no backup password, or a location with protected false, is a
    MEDIUM finding; nothing but null-ness and booleans is read."""
    hass.config.config_dir = str(tmp_path)

    _write_backup_store(
        tmp_path,
        password_set=False,
        agents={"backup.local": {"protected": False, "retention": None}},
    )
    findings = await health._check_backup_protection()
    assert len(findings) == 1
    assert findings[0]["check"] == "backup_unprotected"
    assert findings[0]["severity"] == "medium"
    assert findings[0]["detail"]["password_set"] is False
    assert findings[0]["detail"]["unprotected_agents"] == ["backup.local"]
    # The password VALUE never appears anywhere in the finding.
    assert "pw" not in json.dumps(findings[0])

    _write_backup_store(
        tmp_path,
        password_set=True,
        agents={"backup.local": {"protected": True, "retention": None}},
    )
    findings = await health._check_backup_protection()
    assert findings == []
    stored = health._store.data["misconfig_findings"]["misconfig:backup_unprotected"]
    assert stored["status"] == "resolved"


async def test_backup_protection_absent_file_is_nothing_to_check(
    hass: HomeAssistant, health: IntegrationHealth, tmp_path
) -> None:
    hass.config.config_dir = str(tmp_path)
    findings = await health._check_backup_protection()
    assert findings == []


async def test_samba_share_without_password_or_with_guest_is_flagged(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    """SEC-7: only option KEY presence and boolean-ness are evaluated, and
    no option value ever reaches the finding."""
    fake_addons = {
        "core_samba": {
            "name": "Samba share",
            "state": "started",
            "options": {"username": "smbuser42", "password": "", "allow_guests": False},
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        findings = await health._check_samba_config_share()
    assert len(findings) == 1
    assert findings[0]["severity"] == "high"
    assert findings[0]["detail"]["password_key_present"] is True
    assert findings[0]["detail"]["password_set"] is False
    assert findings[0]["detail"]["guest_keys_enabled"] == []
    assert "smbuser42" not in json.dumps(findings[0])

    guest_addons = {
        "core_samba": {
            "name": "Samba share",
            "state": "started",
            "options": {"password": "sekret123", "guest_ok": True},
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=guest_addons),
    ):
        findings = await health._check_samba_config_share()
    assert len(findings) == 1
    assert findings[0]["detail"]["guest_keys_enabled"] == ["guest_ok"]
    assert "sekret123" not in json.dumps(findings[0])

    unknown_shape = {
        "core_samba": {
            "name": "Samba share",
            "state": "started",
            # No password-shaped key and no guest key: could-not-evaluate,
            # so no finding is invented.
            "options": {"credentials": ["a"]},
        },
    }
    with (
        patch("homeassistant.helpers.hassio.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=unknown_shape),
    ):
        findings = await health._check_samba_config_share()
    assert findings == []


async def test_broken_entity_references_empty_when_nothing_broken(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    findings = await health._check_broken_entity_references()
    assert findings == []


async def test_broken_entity_references_flags_dangling_automation_entity(
    hass: HomeAssistant, health: IntegrationHealth
) -> None:
    from homeassistant.setup import async_setup_component

    config = [
        {
            "id": "auto1",
            "alias": "Broken",
            "trigger": [{"platform": "state", "entity_id": "sensor.gone"}],
            "action": [{"service": "persistent_notification.create", "data": {"message": "hi"}}],
        }
    ]
    assert await async_setup_component(hass, "automation", {"automation": config})
    await hass.async_block_till_done()

    findings = await health._check_broken_entity_references()
    assert len(findings) == 1
    assert findings[0]["check"] == "broken_entity_references"
    broken_ids = [b["entity_id"] for b in findings[0]["detail"]["broken"]]
    assert "sensor.gone" in broken_ids


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_config_check_flags_invalid_config_and_resolves(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    health_mgr = entry.runtime_data.health

    with patch(
        "homeassistant.config.async_check_ha_config_file",
        return_value="boom: invalid 'foo' key",
    ):
        findings = await health_mgr.async_run_config_check()
    assert len(findings) == 1
    assert findings[0]["id"] == "misconfig:ha_config_invalid"
    stored = entry.runtime_data.store.data["misconfig_findings"]["misconfig:ha_config_invalid"]
    assert stored["status"] == "new"

    with patch("homeassistant.config.async_check_ha_config_file", return_value=None):
        findings = await health_mgr.async_run_config_check()
    assert findings == []
    resolved = entry.runtime_data.store.data["misconfig_findings"]["misconfig:ha_config_invalid"]
    assert resolved["status"] == "resolved"
