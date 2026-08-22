"""Tests for repairs.py's Spook-inspired stale long-lived access token check."""
from __future__ import annotations

from datetime import timedelta

import homeassistant.helpers.issue_registry as ir
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.repairs import (
    STALE_TOKEN_UNUSED_DAYS,
    async_sync_stale_token_issues,
)


async def test_stale_llat_is_flagged(hass: HomeAssistant) -> None:
    user = await hass.auth.async_create_user("Test User")
    token = await hass.auth.async_create_refresh_token(
        user, client_name="old-script", token_type="long_lived_access_token"
    )
    token.last_used_at = dt_util.utcnow() - timedelta(days=STALE_TOKEN_UNUSED_DAYS + 1)

    await async_sync_stale_token_issues(hass)

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert f"stale_access_token_{token.id}" in issue_ids


async def test_recently_used_llat_is_not_flagged(hass: HomeAssistant) -> None:
    user = await hass.auth.async_create_user("Test User")
    token = await hass.auth.async_create_refresh_token(
        user, client_name="active-script", token_type="long_lived_access_token"
    )
    token.last_used_at = dt_util.utcnow() - timedelta(days=1)

    await async_sync_stale_token_issues(hass)

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert f"stale_access_token_{token.id}" not in issue_ids


async def test_normal_session_token_is_never_flagged(hass: HomeAssistant) -> None:
    user = await hass.auth.async_create_user("Test User")
    token = await hass.auth.async_create_refresh_token(user, client_id="http://example.local", client_name="browser")
    token.last_used_at = dt_util.utcnow() - timedelta(days=STALE_TOKEN_UNUSED_DAYS + 1)

    await async_sync_stale_token_issues(hass)

    registry = ir.async_get(hass)
    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert f"stale_access_token_{token.id}" not in issue_ids


async def test_stale_llat_resolves_once_used(hass: HomeAssistant) -> None:
    user = await hass.auth.async_create_user("Test User")
    token = await hass.auth.async_create_refresh_token(
        user, client_name="old-script", token_type="long_lived_access_token"
    )
    token.last_used_at = dt_util.utcnow() - timedelta(days=STALE_TOKEN_UNUSED_DAYS + 1)
    await async_sync_stale_token_issues(hass)

    registry = ir.async_get(hass)
    assert any(i.issue_id == f"stale_access_token_{token.id}" for i in registry.issues.values())

    token.last_used_at = dt_util.utcnow()
    await async_sync_stale_token_issues(hass)

    issue_ids = {i.issue_id for i in registry.issues.values() if i.domain == DOMAIN}
    assert f"stale_access_token_{token.id}" not in issue_ids
