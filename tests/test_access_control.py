"""Tests for require_soc_access and ha_soc/access/info.

Exercises the decorator directly against fake connection objects rather
than going through a full websocket_api HTTP+auth roundtrip — the
decorator only ever touches `connection.user` and the live store, so a
MagicMock stand-in is enough to prove the access_level/owner logic itself,
which is the part with real branching to get wrong.
"""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc.const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    DOMAIN,
)
from custom_components.ha_soc.websocket_api import require_soc_access, ws_access_info


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
