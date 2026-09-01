"""Tests for the panel "Customize" layout store and its ha_soc/layout/*
commands — per-user card order/visibility for the card-based views.

Same approach as test_settings_ws.py: call the sync WS wrappers directly
against a fake connection rather than a full websocket_api HTTP roundtrip.
What needs proving here is that each user's layout is scoped to THEM
(never readable/writable by another user's calls), that an unset view
degrades to an empty (not error) default, and that deleting a user drops
their stored layout.
"""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.websocket_api import ws_layout_get, ws_layout_set


def _connection(user_id: str = "user1") -> MagicMock:
    # is_owner=True sidesteps the generic access_level gate (already covered
    # by test_access_control.py) so these tests exercise only the layout
    # commands' own per-user scoping.
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id=user_id)
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


# ---------------------------------------------------------------------------
# Store-level
# ---------------------------------------------------------------------------


def test_get_user_panel_layout_defaults_to_empty(store: HaSocData) -> None:
    assert store.get_user_panel_layout("nobody", "network_security") == {}


def test_set_and_get_round_trip(store: HaSocData) -> None:
    store.async_set_user_panel_layout("user1", "network_security", ["b", "a"], ["c"])
    layout = store.get_user_panel_layout("user1", "network_security")
    assert layout == {"order": ["b", "a"], "hidden": ["c"]}


def test_layouts_are_scoped_per_view(store: HaSocData) -> None:
    store.async_set_user_panel_layout("user1", "network_security", ["a"], [])
    store.async_set_user_panel_layout("user1", "network", ["x", "y"], ["z"])
    assert store.get_user_panel_layout("user1", "network_security") == {"order": ["a"], "hidden": []}
    assert store.get_user_panel_layout("user1", "network") == {"order": ["x", "y"], "hidden": ["z"]}


def test_layouts_are_scoped_per_user(store: HaSocData) -> None:
    store.async_set_user_panel_layout("user1", "network_security", ["a"], [])
    store.async_set_user_panel_layout("user2", "network_security", ["b"], ["a"])
    assert store.get_user_panel_layout("user1", "network_security") == {"order": ["a"], "hidden": []}
    assert store.get_user_panel_layout("user2", "network_security") == {"order": ["b"], "hidden": ["a"]}


def test_purge_user_drops_their_layout(store: HaSocData) -> None:
    store.async_set_user_panel_layout("user1", "network_security", ["a"], [])
    store.async_purge_user("user1")
    assert store.get_user_panel_layout("user1", "network_security") == {}


# ---------------------------------------------------------------------------
# WS commands
# ---------------------------------------------------------------------------


async def test_get_unset_view_returns_empty_order_and_hidden(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection("user1")
    ws_layout_get(hass, connection, {"id": 1, "view_id": "network_security"})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"order": [], "hidden": []}


async def test_set_then_get_round_trips_through_ws(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection("user1")
    ws_layout_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/layout/set",
            "view_id": "network_security",
            "order": ["findings", "firewall_policies", "acl"],
            "hidden": ["server_ports"],
        },
    )
    await hass.async_block_till_done()

    ws_layout_get(hass, connection, {"id": 2, "view_id": "network_security"})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"order": ["findings", "firewall_policies", "acl"], "hidden": ["server_ports"]}


async def test_layout_is_isolated_per_calling_user(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """One user's ha_soc/layout/set must never be visible through another
    user's ha_soc/layout/get — there is no cross-user layout command."""
    ws_layout_set(
        hass,
        _connection("user1"),
        {"id": 1, "type": "ha_soc/layout/set", "view_id": "network_security", "order": ["a"], "hidden": []},
    )
    await hass.async_block_till_done()

    other = _connection("user2")
    ws_layout_get(hass, other, {"id": 2, "view_id": "network_security"})
    await hass.async_block_till_done()

    result = other.send_result.call_args[0][1]
    assert result == {"order": [], "hidden": []}
