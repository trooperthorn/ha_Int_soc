"""Owner-only administrator management and Observe settings (audit probes p06 and p22)."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.dispatcher import async_dispatcher_send
from aiohttp.test_utils import make_mocked_request
from homeassistant.components.http import KEY_HASS_USER
from homeassistant.helpers.http import current_request
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import observe_push as op
from custom_components.ha_soc import websocket_api as wa
from custom_components.ha_soc.const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DOMAIN,
    SIGNAL_UPDATE,
)

ISOLATED_CONFIG_DIR = True

KEY = "wpi_" + "a" * 32
FIRST_URL = "http://192.168.1.50:8000"


async def _no_push(self) -> None:
    return None


@pytest.fixture
async def entry(hass):
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    with patch.object(op.ObservePusher, "async_push_once", _no_push):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
        yield config_entry
        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()


async def _run(hass, handler, user, msg):
    connection = MagicMock()
    connection.user = user
    handler(hass, connection, msg)
    await hass.async_block_till_done()
    return connection


async def _users(hass):
    owner = await hass.auth.async_create_user("Owner", group_ids=[GROUP_ID_ADMIN])
    owner.is_owner = True
    admin = await hass.auth.async_create_user("Admin2", group_ids=[GROUP_ID_ADMIN])
    regular = await hass.auth.async_create_user("Regular", group_ids=[GROUP_ID_USER])
    return owner, admin, regular


def _refused(connection) -> bool:
    """True when the async handler ended in Unauthorized (the async_response wrapper
    hands the exception to connection.async_handle_exception)."""
    if not connection.async_handle_exception.called:
        return False
    return isinstance(connection.async_handle_exception.call_args[0][1], Unauthorized)


def _admin_names(users) -> set[str]:
    return {u.name for u in users if any(g.id == GROUP_ID_ADMIN for g in u.groups)}


async def test_non_owner_admin_cannot_create_an_admin(hass, entry) -> None:
    entry.runtime_data.store.settings["access_level"] = ACCESS_LEVEL_OWNER_AND_ADMINS
    _, admin, _ = await _users(hass)
    message = {
        "id": 1,
        "type": "ha_soc/users/create",
        "name": "NewAdmin",
        "group_ids": [GROUP_ID_ADMIN],
    }

    connection = await _run(hass, wa.ws_users_create, admin, message)

    assert _refused(connection)

    assert "NewAdmin" not in {u.name for u in await hass.auth.async_get_users()}


async def test_non_owner_admin_cannot_promote_to_admin(hass, entry) -> None:
    entry.runtime_data.store.settings["access_level"] = ACCESS_LEVEL_OWNER_AND_ADMINS
    _, admin, regular = await _users(hass)
    message = {
        "id": 2,
        "type": "ha_soc/users/update",
        "user_id": regular.id,
        "group_ids": [GROUP_ID_ADMIN],
    }

    connection = await _run(hass, wa.ws_users_update, admin, message)

    assert _refused(connection)

    refreshed = await hass.auth.async_get_user(regular.id)
    assert [g.id for g in refreshed.groups] == [GROUP_ID_USER]
    assert "Regular" not in _admin_names(await hass.auth.async_get_users())


async def test_non_owner_admin_may_still_create_and_edit_plain_users(hass, entry) -> None:
    entry.runtime_data.store.settings["access_level"] = ACCESS_LEVEL_OWNER_AND_ADMINS
    _, admin, regular = await _users(hass)

    created = await _run(
        hass,
        wa.ws_users_create,
        admin,
        {"id": 3, "type": "ha_soc/users/create", "name": "Plain", "group_ids": [GROUP_ID_USER]},
    )
    created.send_result.assert_called_once()
    updated = await _run(
        hass,
        wa.ws_users_update,
        admin,
        {"id": 4, "type": "ha_soc/users/update", "user_id": regular.id, "name": "Renamed"},
    )
    updated.send_result.assert_called_once()


async def test_owner_can_create_and_promote_an_admin(hass, entry) -> None:
    owner, _, regular = await _users(hass)

    created = await _run(
        hass,
        wa.ws_users_create,
        owner,
        {"id": 5, "type": "ha_soc/users/create", "name": "OwnerMade", "group_ids": [GROUP_ID_ADMIN]},
    )
    created.send_result.assert_called_once()
    promoted = await _run(
        hass,
        wa.ws_users_update,
        owner,
        {"id": 6, "type": "ha_soc/users/update", "user_id": regular.id, "group_ids": [GROUP_ID_ADMIN]},
    )
    promoted.send_result.assert_called_once()
    assert {"OwnerMade", "Regular"} <= _admin_names(await hass.auth.async_get_users())


async def _submit(hass, entry, values):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    if result["type"] == "abort":
        return result
    done = await hass.config_entries.options.async_configure(result["flow_id"], values)
    await hass.async_block_till_done()
    return done


def _values(url, key=None):
    values = {
        CONF_OBSERVE_ENABLED: True,
        CONF_OBSERVE_URL: url,
        CONF_OBSERVE_HOST_NAME: "haos",
        CONF_OBSERVE_INTERVAL: 60,
    }
    if key is not None:
        values[CONF_OBSERVE_INGEST_KEY] = key
    return values


async def test_url_change_without_the_key_is_refused(hass, entry) -> None:
    first = await _submit(hass, entry, _values(FIRST_URL, KEY))
    assert first["type"] == "create_entry"

    refused = await _submit(hass, entry, _values("https://collector.example.org"))

    assert refused["type"] == "form"
    assert refused["errors"] == {CONF_OBSERVE_INGEST_KEY: "key_required_for_url_change"}
    runtime = entry.runtime_data
    assert runtime.store.settings[CONF_OBSERVE_URL] == FIRST_URL
    assert (await runtime.observe._async_load_config()).key == KEY


async def test_url_change_with_the_key_and_unchanged_url_without_it_are_accepted(
    hass, entry
) -> None:
    await _submit(hass, entry, _values(FIRST_URL, KEY))

    same = await _submit(hass, entry, _values(FIRST_URL))
    assert same["type"] == "create_entry"

    moved = await _submit(hass, entry, _values("https://collector.example.org", KEY))
    assert moved["type"] == "create_entry"
    assert entry.runtime_data.store.settings[CONF_OBSERVE_URL] == "https://collector.example.org"


async def test_options_audit_record_names_the_acting_user(hass, entry) -> None:
    owner, _, _ = await _users(hass)
    token = current_request.set({"hass_user": owner})
    try:
        await _submit(hass, entry, _values(FIRST_URL, KEY))
    finally:
        current_request.reset(token)

    runtime = entry.runtime_data
    await runtime.audit._async_flush()
    records = await runtime.audit.async_query(category="soc_config_change", limit=10)
    changed = [r for r in records if r["detail"].get("action") == "observe_push_changed"]
    assert changed
    assert all(r["user_id"] == owner.id for r in changed)
    assert KEY not in str(changed)


async def test_non_owner_admin_is_refused_the_observe_options_under_owner_only(
    hass, entry
) -> None:
    _, admin, _ = await _users(hass)
    token = current_request.set({"hass_user": admin})
    try:
        result = await hass.config_entries.options.async_init(entry.entry_id)
    finally:
        current_request.reset(token)

    assert result["type"] == "abort"
    assert result["reason"] == "owner_required"


async def test_non_owner_admin_may_use_observe_options_when_admins_are_allowed(
    hass, entry
) -> None:
    entry.runtime_data.store.settings["access_level"] = ACCESS_LEVEL_OWNER_AND_ADMINS
    _, admin, _ = await _users(hass)
    token = current_request.set({"hass_user": admin})
    try:
        result = await hass.config_entries.options.async_init(entry.entry_id)
    finally:
        current_request.reset(token)

    assert result["type"] == "form"
    hass.config_entries.options.async_abort(result["flow_id"])


async def test_non_admin_state_view_of_user_risk_shows_the_band_only(hass, entry) -> None:
    """Entity states have no per-user read check, so what the state machine holds is
    what every logged-in user can read."""
    runtime = entry.runtime_data
    runtime.risk.last_risk_results = {
        "u-target-0001": {
            "score": 62,
            "band": "high",
            "factors": [{"name": "admin_without_mfa", "points": 20, "detail": "no MFA module"}],
        }
    }
    async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_dashboard")
    await hass.async_block_till_done()

    states = [
        s for s in hass.states.async_all("sensor") if s.entity_id.startswith("sensor.ha_soc_risk")
    ]
    assert states, "the per-user risk sensor was not created"
    for state in states:
        public = {
            k: v
            for k, v in state.attributes.items()
            if k not in ("friendly_name", "icon", "state_class")
        }
        assert public == {"band": "high"}
        assert "MFA" not in str(state.as_dict())
        assert "factors" not in state.attributes


async def test_posture_sensor_shows_the_grade_only(hass, entry) -> None:
    runtime = entry.runtime_data
    runtime.risk.last_posture_result = {
        "score": 71,
        "grade": "C",
        "terms": [{"name": "mfa", "points": 12, "detail": "two admins lack MFA"}],
    }
    async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_dashboard")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.security_posture_score")
    if state is None:
        matches = [
            s for s in hass.states.async_all("sensor") if "posture" in s.entity_id
        ]
        assert matches, "the posture sensor was not created"
        state = matches[0]
    public = {
        k: v
        for k, v in state.attributes.items()
        if k not in ("friendly_name", "icon", "state_class")
    }
    assert public == {"grade": "C"}
    assert state.state == "71"
    assert "two admins" not in str(state.as_dict())


async def test_options_audit_record_names_the_user_of_a_real_request(hass, entry) -> None:
    """The actor comes from a real aiohttp request carrying the authenticated user."""
    owner, _, _ = await _users(hass)
    request = make_mocked_request("POST", "/api/config/config_entries/options/flow/x")
    request[KEY_HASS_USER] = owner
    token = current_request.set(request)
    try:
        await _submit(hass, entry, _values(FIRST_URL, KEY))
    finally:
        current_request.reset(token)

    runtime = entry.runtime_data
    await runtime.audit._async_flush()
    records = await runtime.audit.async_query(category="soc_config_change", limit=10)
    changed = [r for r in records if r["detail"].get("action") == "observe_push_changed"]
    assert changed
    assert all(r["user_id"] == owner.id for r in changed)


def test_owner_required_abort_text_is_under_options_abort() -> None:
    """An options flow looks its abort reasons up under options.abort, not config.abort."""
    path = (
        Path(__file__).parent.parent
        / "custom_components"
        / "ha_soc"
        / "translations"
        / "en.json"
    )
    strings = json.loads(path.read_text(encoding="utf-8"))
    assert "owner_required" in strings["options"]["abort"]
    assert "owner_required" not in strings["config"]["abort"]
