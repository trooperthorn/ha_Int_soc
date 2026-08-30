"""Work item 4.12 (server half): a password reset revokes the target's
interactive sessions by default, sparing long-lived access tokens."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.users import UsersManager
from custom_components.ha_soc.websocket_api import ws_users_set_password


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
    config_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    return config_entry


async def _user_with_tokens(hass: HomeAssistant):
    user = await hass.auth.async_create_user("Target")
    for i in range(2):
        await hass.auth.async_create_refresh_token(
            user, client_id=f"http://client{i}.local", client_name=f"browser{i}"
        )
    await hass.auth.async_create_refresh_token(
        user, client_name="script", token_type="long_lived_access_token"
    )
    return user


async def test_revoke_interactive_sessions_spares_llats(hass: HomeAssistant) -> None:
    users_manager = UsersManager(hass)
    user = await _user_with_tokens(hass)

    revoked = await users_manager.async_revoke_interactive_sessions(user.id)

    assert revoked == 2
    remaining = [t.token_type for t in user.refresh_tokens.values()]
    assert remaining == ["long_lived_access_token"]


def test_revoke_sessions_defaults_true_in_schema() -> None:
    """The schema injects revoke_sessions=True when the client omits it, so
    the secure behavior is the default, not an opt-in."""
    validated = ws_users_set_password._ws_schema(
        {"id": 1, "type": "ha_soc/users/set_password", "user_id": "u1", "password": "pw"}
    )
    assert validated["revoke_sessions"] is True


async def test_set_password_revokes_sessions(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """After a successful password set the target's interactive sessions
    are revoked (LLATs kept), the count is answered and audited."""
    runtime = entry.runtime_data
    user = await _user_with_tokens(hass)
    connection = _connection()

    # The password write itself needs a live homeassistant auth provider,
    # which the harness does not configure; it is patched to succeed so
    # the piece under test - the post-success revocation - runs for real.
    with patch.object(
        runtime.users, "async_set_password", new=AsyncMock(return_value=(True, None))
    ):
        ws_users_set_password(
            hass,
            connection,
            {
                "id": 1,
                "type": "ha_soc/users/set_password",
                "user_id": user.id,
                "password": "new-password",
                "revoke_sessions": True,
            },
        )
        await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "sessions_revoked": 2}
    remaining = [t.token_type for t in user.refresh_tokens.values()]
    assert remaining == ["long_lived_access_token"]

    records = [
        r
        for r in await runtime.audit.async_query(category="user_updated")
        if r["detail"].get("action") == "password_reset"
    ]
    assert len(records) == 1
    assert records[0]["detail"]["revoke_sessions"] is True
    assert records[0]["detail"]["sessions_revoked"] == 2


async def test_set_password_can_keep_sessions(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    user = await _user_with_tokens(hass)
    connection = _connection()

    with patch.object(
        runtime.users, "async_set_password", new=AsyncMock(return_value=(True, None))
    ):
        ws_users_set_password(
            hass,
            connection,
            {
                "id": 1,
                "type": "ha_soc/users/set_password",
                "user_id": user.id,
                "password": "new-password",
                "revoke_sessions": False,
            },
        )
        await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "sessions_revoked": 0}
    assert len(user.refresh_tokens) == 3


async def test_failed_set_password_revokes_nothing(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The revocation only ever follows a SUCCESSFUL password set - a
    refused reset must not sign anyone out."""
    runtime = entry.runtime_data
    user = await _user_with_tokens(hass)
    connection = _connection()

    with patch.object(
        runtime.users,
        "async_set_password",
        new=AsyncMock(return_value=(False, "owner_required")),
    ):
        ws_users_set_password(
            hass,
            connection,
            {
                "id": 1,
                "type": "ha_soc/users/set_password",
                "user_id": user.id,
                "password": "new-password",
                "revoke_sessions": True,
            },
        )
        await hass.async_block_till_done()

    assert connection.send_error.called
    assert len(user.refresh_tokens) == 3
