"""Regression tests for the red-team hardening pass.

Each test pins a specific finding's fix so a future change can't silently
undo it. Grouped by the module the fix lives in.
"""
import os
import shutil

import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.const import AUDIT_STORAGE_SUBDIR
from custom_components.ha_soc.store import HaSocData


@pytest.fixture(autouse=True)
def _clean_audit_dir(hass: HomeAssistant):
    # The test harness's config dir isn't guaranteed fresh per test, so
    # audit files from other tests otherwise pollute the hash chain here.
    path = hass.config.path(".storage", AUDIT_STORAGE_SUBDIR)
    shutil.rmtree(path, ignore_errors=True)
    yield
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


async def test_audit_log_redacts_secret_settings(hass: HomeAssistant, store: HaSocData) -> None:
    audit = AuditLog(hass, store)
    audit.async_log(
        "user_updated",
        user_id="u1",
        detail={
            "action": "settings_changed",
            "changes": {"nvd_api_key": "SUPERSECRET", "github_token": "ghp_TOKEN", "scanner_enabled": True},
        },
    )
    await audit._async_flush()

    dir_path = hass.config.path(".storage", "ha_soc_audit")
    blob = ""
    for name in os.listdir(dir_path):
        if name.startswith("audit-"):
            with open(os.path.join(dir_path, name), encoding="utf-8") as handle:
                blob += handle.read()

    assert "SUPERSECRET" not in blob
    assert "ghp_TOKEN" not in blob
    assert "[redacted]" in blob
    # Non-secret fields still recorded.
    assert "scanner_enabled" in blob


async def test_verify_chain_detects_deleted_tail(hass: HomeAssistant, store: HaSocData) -> None:
    audit = AuditLog(hass, store)
    audit.async_log("login_ok", user_id="u1")
    await audit._async_flush()
    audit.async_log("login_ok", user_id="u2")
    await audit._async_flush()

    ok = await audit.async_verify_chain()
    assert ok["ok"] is True

    # Delete the day file(s), the chain-head checkpoint still records seq=2.
    dir_path = hass.config.path(".storage", "ha_soc_audit")
    for name in os.listdir(dir_path):
        if name.startswith("audit-"):
            os.remove(os.path.join(dir_path, name))

    tampered = await audit.async_verify_chain()
    assert tampered["ok"] is False
    assert tampered["reason"] == "tail_truncated"


async def test_firewall_secret_pin_and_reject(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.firewall import (
        async_reset_addon_secret,
        async_verify_or_pin_secret,
    )
    from custom_components.ha_soc.secrets_store import (
        PROBE_PAIRING_SECRET_KEY,
        HaSocSecretStore,
    )

    # The pin lives in the private secret store since SEC-1, so the checks
    # run against it rather than the general store.
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()

    # First non-empty secret pins.
    assert await async_verify_or_pin_secret(secrets, "addon-secret-1") is True
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) == "addon-secret-1"
    # Same secret keeps working.
    assert await async_verify_or_pin_secret(secrets, "addon-secret-1") is True
    # A forged call with the wrong (or no) secret is rejected.
    assert await async_verify_or_pin_secret(secrets, "attacker-secret") is False
    assert await async_verify_or_pin_secret(secrets, None) is False
    # Owner reset re-opens pinning.
    await async_reset_addon_secret(secrets)
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) is None
    assert await async_verify_or_pin_secret(secrets, "addon-secret-2") is True


def test_firewall_source_validation() -> None:
    from custom_components.ha_soc.firewall import RULE_SCHEMA

    # Valid: omitted (no source key), empty (normalized to None), single IP, CIDR.
    assert "source" not in RULE_SCHEMA({"action": "allow", "proto": "tcp", "port": 22})
    assert RULE_SCHEMA({"action": "allow", "proto": "tcp", "port": 22, "source": ""})["source"] is None
    RULE_SCHEMA({"action": "allow", "proto": "tcp", "port": 22, "source": "192.168.1.5"})
    RULE_SCHEMA({"action": "deny", "proto": "udp", "port": 53, "source": "10.0.0.0/8"})

    # Invalid: not an IP/CIDR at all.
    with pytest.raises(vol.Invalid):
        RULE_SCHEMA({"action": "allow", "proto": "tcp", "port": 22, "source": "not-an-ip"})
    with pytest.raises(vol.Invalid):
        RULE_SCHEMA({"action": "allow", "proto": "tcp", "port": 22, "source": "192.168.1.0/99"})


async def test_delete_user_blocks_owner(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockUser

    from custom_components.ha_soc.users import UsersManager

    owner = MockUser(is_owner=True)
    owner.add_to_hass(hass)

    mgr = UsersManager(hass)
    ok, reason = await mgr.async_delete_user(owner.id, requesting_user_id="someone-else")
    assert ok is False
    assert reason == "cannot_delete_owner"
    assert await hass.auth.async_get_user(owner.id) is not None


async def test_delete_user_blocks_self(hass: HomeAssistant) -> None:
    from pytest_homeassistant_custom_component.common import MockUser

    from custom_components.ha_soc.users import UsersManager

    admin = MockUser(is_owner=False)
    admin.add_to_hass(hass)

    mgr = UsersManager(hass)
    ok, reason = await mgr.async_delete_user(admin.id, requesting_user_id=admin.id)
    assert ok is False
    assert reason == "cannot_delete_self"
    assert await hass.auth.async_get_user(admin.id) is not None


async def test_delete_user_missing_returns_reason(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.users import UsersManager

    mgr = UsersManager(hass)
    ok, reason = await mgr.async_delete_user("does-not-exist", requesting_user_id="someone")
    assert ok is False
    assert reason == "user_not_found"


async def test_revoke_all_reports_token_breakdown(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.users import UsersManager

    mgr = UsersManager(hass)
    result = await mgr.async_revoke_all_sessions("no-such-user")
    # Shape is a per-type breakdown, not a bare int, so the UI can state
    # exactly what was cleared (including long-lived tokens).
    assert result == {"sessions": 0, "long_lived_tokens": 0}
