"""Tests for require_soc_access, ha_soc/access/info, and the D-23 gates.

Exercises the decorators directly against fake connection objects rather
than going through a full websocket_api HTTP+auth roundtrip — the
decorators only ever touch `connection.user` and the live store, so a
MagicMock stand-in is enough to prove the access_level/owner logic itself,
which is the part with real branching to get wrong. The D-23 target-admin
tests below do create REAL users in hass.auth, because resolving the
target's admin-group membership server-side is exactly the property under
test.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc.const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    DOMAIN,
)
from custom_components.ha_soc.websocket_api import (
    require_soc_access,
    ws_access_info,
    ws_entity_remap_apply,
    ws_permissions_sidebar_push,
    ws_users_deactivate,
    ws_users_delete,
    ws_users_revoke_all_sessions,
    ws_users_revoke_token,
    ws_users_update,
    ws_version_get,
)


def _connection(*, is_admin: bool, is_owner: bool) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner)
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_owner_always_allowed(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    calls = []
    wrapped = require_soc_access(lambda hass, connection, msg: calls.append(msg))

    wrapped(hass, _connection(is_admin=True, is_owner=True), {"id": 1})

    assert calls == [{"id": 1}]


async def test_non_admin_always_blocked(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    wrapped = require_soc_access(lambda hass, connection, msg: pytest.fail("should not run"))

    with pytest.raises(Unauthorized):
        wrapped(hass, _connection(is_admin=False, is_owner=False), {"id": 1})


async def test_non_owner_admin_blocked_by_default(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    assert entry.runtime_data.store.settings["access_level"] == ACCESS_LEVEL_OWNER_ONLY
    wrapped = require_soc_access(lambda hass, connection, msg: pytest.fail("should not run"))

    with pytest.raises(Unauthorized):
        wrapped(hass, _connection(is_admin=True, is_owner=False), {"id": 1})


async def test_non_owner_admin_allowed_when_opened_up(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    entry.runtime_data.store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_AND_ADMINS)
    calls = []
    wrapped = require_soc_access(lambda hass, connection, msg: calls.append(msg))

    wrapped(hass, _connection(is_admin=True, is_owner=False), {"id": 1})

    assert calls == [{"id": 1}]


async def test_access_info_reports_state_for_blocked_admin(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection(is_admin=True, is_owner=False)

    ws_access_info(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {
        "is_owner": False,
        "access_level": ACCESS_LEVEL_OWNER_ONLY,
        "allowed": False,
    }


async def test_access_info_reports_state_for_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection(is_admin=True, is_owner=True)

    ws_access_info(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {
        "is_owner": True,
        "access_level": ACCESS_LEVEL_OWNER_ONLY,
        "allowed": True,
    }


async def test_version_get_reads_manifest_version(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    # Single source of truth: manifest.json, the same file HA itself
    # already reads for update-checking — not a second hardcoded string
    # in websocket_api.py that could drift from it on the next release.
    import json
    import os

    manifest_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "custom_components", "ha_soc", "manifest.json")
    with open(manifest_path) as f:
        expected_version = json.load(f)["version"]

    connection = _connection(is_admin=True, is_owner=False)

    ws_version_get(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"version": expected_version}
    # And it follows the YYYY.MM.DD.V shape, not the old pre-1.0 semver.
    assert len(expected_version.split(".")) == 4


# ---------------------------------------------------------------------------
# D-23 option (a): owner-only whenever the TARGET is an admin-group user
# (update, deactivate, delete, revoke_token, revoke_all_sessions), and owner-only
# outright for entity_remap/apply and permissions/sidebar/push.
# ---------------------------------------------------------------------------


def _ws_connection(*, is_owner: bool) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(
        is_admin=True, is_owner=is_owner, id="owner1" if is_owner else "admin2"
    )
    return connection


def _unauthorized_raised(connection: MagicMock) -> bool:
    """True when the async handler ended in Unauthorized (the async_response
    wrapper hands exceptions to connection.async_handle_exception, which
    the real ActiveConnection maps to the standard unauthorized error)."""
    if not connection.async_handle_exception.called:
        return False
    return isinstance(connection.async_handle_exception.call_args[0][1], Unauthorized)


async def test_admin_target_requires_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Each target-user command is refused for a non-owner admin when
    the target is an admin-group user (deactivated admins included, since
    group membership, not the is_admin flag, is what the gate resolves),
    still allowed for the owner, and still allowed to a non-owner admin
    for a non-admin target."""
    runtime = entry.runtime_data
    runtime.store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_AND_ADMINS)
    runtime.audit._async_schedule_flush = lambda: None

    admin_target = await hass.auth.async_create_user(
        "Admin Target", group_ids=[GROUP_ID_ADMIN]
    )
    plain_target = await hass.auth.async_create_user(
        "Plain Target", group_ids=[GROUP_ID_USER]
    )
    deactivated_admin = await hass.auth.async_create_user(
        "Former Admin", group_ids=[GROUP_ID_ADMIN]
    )
    await hass.auth.async_update_user(deactivated_admin, is_active=False)
    assert deactivated_admin.is_admin is False  # the flag the gate must NOT use

    # The command machinery under the gate is mocked out: what is under
    # test is who may reach it, not the user mutation itself.
    runtime.users.async_deactivate_user = AsyncMock(return_value=(True, None))
    runtime.users.async_update_user = AsyncMock(return_value=True)
    runtime.users.async_delete_user = AsyncMock(return_value=(True, None))
    runtime.users.async_revoke_token = AsyncMock(return_value=True)
    runtime.users.async_revoke_all_sessions = AsyncMock(
        return_value={"sessions": 0, "long_lived_tokens": 0}
    )
    mocks = {
        ws_users_update: runtime.users.async_update_user,
        ws_users_deactivate: runtime.users.async_deactivate_user,
        ws_users_delete: runtime.users.async_delete_user,
        ws_users_revoke_token: runtime.users.async_revoke_token,
        ws_users_revoke_all_sessions: runtime.users.async_revoke_all_sessions,
    }

    def _msg(handler, target_id: str) -> dict:
        msg = {"id": 1, "type": "x", "user_id": target_id}
        if handler is ws_users_update:
            msg["name"] = "Updated name"
        if handler is ws_users_revoke_token:
            msg["token_id"] = "tok1"
        return msg

    for handler, users_mock in mocks.items():
        # Non-owner admin, admin-group target: standard unauthorized error,
        # and the mutation is never reached.
        users_mock.reset_mock()
        connection = _ws_connection(is_owner=False)
        handler(hass, connection, _msg(handler, admin_target.id))
        await hass.async_block_till_done()
        assert _unauthorized_raised(connection), handler.__name__
        connection.send_result.assert_not_called()
        users_mock.assert_not_awaited()

        # Non-owner admin, DEACTIVATED admin-group target: still refused.
        connection = _ws_connection(is_owner=False)
        handler(hass, connection, _msg(handler, deactivated_admin.id))
        await hass.async_block_till_done()
        assert _unauthorized_raised(connection), handler.__name__
        users_mock.assert_not_awaited()

        # Owner, admin-group target: allowed.
        connection = _ws_connection(is_owner=True)
        handler(hass, connection, _msg(handler, admin_target.id))
        await hass.async_block_till_done()
        connection.send_result.assert_called_once()
        users_mock.assert_awaited_once()

        # Non-owner admin, non-admin target: routine management stays open.
        users_mock.reset_mock()
        connection = _ws_connection(is_owner=False)
        handler(hass, connection, _msg(handler, plain_target.id))
        await hass.async_block_till_done()
        connection.send_result.assert_called_once()
        users_mock.assert_awaited_once()


async def test_owner_cannot_be_deactivated_through_generic_update(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The generic update endpoint must preserve core's owner invariant."""
    runtime = entry.runtime_data
    runtime.audit._async_schedule_flush = lambda: None
    runtime.users.async_update_user = AsyncMock(return_value=True)
    target = MagicMock(is_owner=True)
    connection = _ws_connection(is_owner=True)

    with patch.object(hass.auth, "async_get_user", AsyncMock(return_value=target)):
        ws_users_update(
            hass,
            connection,
            {
                "id": 1,
                "type": "ha_soc/users/update",
                "user_id": "owner1",
                "is_active": False,
            },
        )
        await hass.async_block_till_done()

    connection.send_error.assert_called_once_with(
        1, "cannot_deactivate_owner", "The owner account cannot be deactivated"
    )
    runtime.users.async_update_user.assert_not_awaited()


async def test_remap_apply_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """D-23: entity_remap/apply rewrites configuration, so it is owner-only
    outright, even under owner_and_admins."""
    runtime = entry.runtime_data
    runtime.store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_AND_ADMINS)
    runtime.audit._async_schedule_flush = lambda: None
    msg = {
        "id": 1,
        "type": "ha_soc/entity_remap/apply",
        "old_entity_id": "sensor.old",
        "new_entity_id": "sensor.new",
        "backup_acknowledged": True,
    }

    with pytest.raises(Unauthorized):
        ws_entity_remap_apply(hass, _ws_connection(is_owner=False), msg)

    with patch(
        "custom_components.ha_soc.entity_remap.async_apply_remap",
        AsyncMock(
            return_value={
                "old_entity_id": "sensor.old",
                "new_entity_id": "sensor.new",
                "fixed": {},
                "errors": [],
            }
        ),
    ):
        connection = _ws_connection(is_owner=True)
        ws_entity_remap_apply(hass, connection, msg)
        await hass.async_block_till_done()
        connection.send_result.assert_called_once()


async def test_sidebar_push_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """D-23: permissions/sidebar/push rewrites another user's policy, so it
    is owner-only outright, even under owner_and_admins."""
    runtime = entry.runtime_data
    runtime.store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_AND_ADMINS)
    runtime.audit._async_schedule_flush = lambda: None
    msg = {
        "id": 1,
        "type": "ha_soc/permissions/sidebar/push",
        "user_id": "someone",
        "hidden_dashboard_paths": ["lovelace-cams"],
    }

    with pytest.raises(Unauthorized):
        ws_permissions_sidebar_push(hass, _ws_connection(is_owner=False), msg)

    runtime.permissions.async_push_sidebar_policy = AsyncMock(return_value=(True, None))
    connection = _ws_connection(is_owner=True)
    ws_permissions_sidebar_push(hass, connection, msg)
    await hass.async_block_till_done()
    connection.send_result.assert_called_once()
    runtime.permissions.async_push_sidebar_policy.assert_awaited_once()
