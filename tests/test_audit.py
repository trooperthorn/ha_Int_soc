"""AuditLog capture, actor recovery, and query-freshness behavior.

These tests fabricate events and ambient context rather than driving real
registries, because what is under test is audit.py's own contract: which
records it writes, how it labels actor recovery, and that the buffer is
flushed before a query. Core's side of the contract (which events fire and
with what payload) is documented in audit.py's module docstring.
"""
from __future__ import annotations

from typing import Any

import pytest
from homeassistant.components.websocket_api import current_connection
from homeassistant.core import Context, Event, HomeAssistant

from custom_components.ha_soc.audit import AuditLog
from custom_components.ha_soc.store import HaSocData


class _FakeUser:
    def __init__(self, user_id: str) -> None:
        self.id = user_id


class _FakeConnection:
    """Duck-typed ActiveConnection: only .user and .refresh_token_id are read."""

    def __init__(self, user_id: str, refresh_token_id: str) -> None:
        self.user = _FakeUser(user_id)
        self.refresh_token_id = refresh_token_id


class _FakeConfigEntry:
    domain = "demo"
    entry_id = "entry-1"
    title = "Demo entry"
    disabled_by = None


async def _make_audit(hass: HomeAssistant, tmp_path: Any) -> AuditLog:
    """Build an AuditLog writing into this test's private tmp directory.

    The directory is overridden before anything touches disk so tests never
    share audit files through a common config dir.
    """
    store = HaSocData(hass)
    await store.async_load()
    audit = AuditLog(hass, store)
    audit._dir_path = str(tmp_path / "audit")
    return audit


def _buffered(audit: AuditLog, category: str) -> list[dict[str, Any]]:
    return [r for r in audit._buffer if r["category"] == category]


async def test_registry_updated_bus_event_writes_record_with_actor_source(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """An area registry event fired on the bus lands as a record, inline.

    The listener is registered through functools.partial and must still be
    classified as a @callback (HassJob unwraps partials), which means it
    runs synchronously inside async_fire. The buffer is therefore checked
    immediately after the fire, without yielding to the loop, so this test
    fails if the handler ever falls back to executor dispatch (which would
    also break contextvar-based actor recovery).
    """
    audit = await _make_audit(hass, tmp_path)
    await audit.async_start()
    try:
        hass.bus.async_fire(
            "area_registry_updated", {"action": "update", "area_id": "kitchen"}
        )
        records = _buffered(audit, "area_registry_change")
        assert len(records) == 1
        record = records[0]
        # Fired from the test with no user context and no ambient
        # connection, so recovery honestly reports "system".
        assert record["user_id"] is None
        assert record["detail"]["actor_source"] == "system"
        assert record["detail"]["action"] == "update"
        assert record["detail"]["area_id"] == "kitchen"
        assert record["detail"]["changes"] == {}

        # The record must also survive the full flush/query round trip.
        results = await audit.async_query(category="area_registry_change")
        assert len(results) == 1
        assert results[0]["detail"]["area_id"] == "kitchen"
    finally:
        await audit.async_stop()


async def test_resolve_actor_prefers_event_context_over_ambient(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    audit = await _make_audit(hass, tmp_path)
    token = current_connection.set(_FakeConnection("ws-user", "tok-1"))
    try:
        with_context = Event(
            "area_registry_updated",
            {"action": "update"},
            context=Context(user_id="ctx-user"),
        )
        assert audit._resolve_actor(with_context) == ("ctx-user", "event_context")

        # Same ambient connection, but the event context is empty: the
        # resolver falls back to the contextvar and labels it as such.
        without_context = Event("area_registry_updated", {"action": "update"})
        assert audit._resolve_actor(without_context) == ("ws-user", "ws_connection")
    finally:
        current_connection.reset(token)


async def test_session_seen_emitted_once_per_refresh_token(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """The first ws_connection hit emits one synthetic session_seen record."""
    audit = await _make_audit(hass, tmp_path)
    token = current_connection.set(_FakeConnection("ws-user", "tok-1"))
    try:
        event = Event("area_registry_updated", {"action": "update"})
        audit._resolve_actor(event)
        audit._resolve_actor(event)
    finally:
        current_connection.reset(token)

    seen = _buffered(audit, "session_seen")
    assert len(seen) == 1
    assert seen[0]["user_id"] == "ws-user"
    assert seen[0]["detail"]["refresh_token_id"] == "tok-1"
    # The record itself must carry the LLAT-invisibility caveat so an
    # export of the raw log stays honest without this module's docstring.
    assert "invisible" in seen[0]["detail"]["note"]


async def test_user_removed_splits_actor_from_target(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """user_id is the acting admin; the removed user is target_user_id."""
    audit = await _make_audit(hass, tmp_path)
    token = current_connection.set(_FakeConnection("admin-user", "tok-2"))
    try:
        audit._handle_user_removed(Event("user_removed", {"user_id": "victim"}))
    finally:
        current_connection.reset(token)

    records = _buffered(audit, "user_removed")
    assert len(records) == 1
    record = records[0]
    assert record["user_id"] == "admin-user"
    assert record["detail"]["target_user_id"] == "victim"
    assert record["detail"]["actor_source"] == "ws_connection"


async def test_query_flushes_buffer_first(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """A record logged a moment ago is visible without waiting 30 seconds."""
    audit = await _make_audit(hass, tmp_path)
    audit.async_log("service_call", user_id="u1", domain="light", service="turn_on")
    assert len(audit._buffer) == 1

    results = await audit.async_query(category="service_call")
    assert len(results) == 1
    assert results[0]["user_id"] == "u1"
    # The buffer really was flushed, not just peeked at.
    assert len(audit._buffer) == 0


async def test_call_service_extracts_area_targets(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Non-entity targets are normalized into detail["targets"].

    Core merges the target block into service_data before firing
    call_service, so an area-targeted call arrives with an area_id key and
    no entity_id at all; without extraction it would audit as touching
    nothing.
    """
    audit = await _make_audit(hass, tmp_path)
    event = Event(
        "call_service",
        {
            "domain": "light",
            "service": "turn_on",
            "service_data": {"area_id": "kitchen", "brightness_pct": 50},
        },
        context=Context(user_id="u1"),
    )
    audit._handle_call_service(event)

    records = _buffered(audit, "service_call")
    assert len(records) == 1
    record = records[0]
    assert record["user_id"] == "u1"
    assert record["entity_ids"] == []
    assert record["detail"]["targets"] == {"area_id": ["kitchen"]}
    # The rest of service_data still lands in detail unchanged.
    assert record["detail"]["brightness_pct"] == 50


async def test_config_entry_change_is_ambient_only(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """The dispatcher signal carries no Event, so recovery is ambient-only."""
    audit = await _make_audit(hass, tmp_path)
    audit._handle_config_entry_changed("added", _FakeConfigEntry())

    records = _buffered(audit, "config_entry_change")
    assert len(records) == 1
    record = records[0]
    assert record["domain"] == "demo"
    assert record["detail"]["change"] == "added"
    assert record["detail"]["entry_id"] == "entry-1"
    assert record["detail"]["actor_source"] == "system"
