"""AuditLog capture, actor recovery, and query-freshness behavior.

These tests fabricate events and ambient context rather than driving real
registries, because what is under test is audit.py's own contract: which
records it writes, how it labels actor recovery, and that the buffer is
flushed before a query. Core's side of the contract (which events fire and
with what payload) is documented in audit.py's module docstring.
"""
from __future__ import annotations

import json
import logging
import os
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


async def test_audit_files_and_store_are_private(
    hass: HomeAssistant, tmp_path: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """Work item 1.1, on a real filesystem: 0o700 directory, 0o600 files.

    Also the one-time migration: a file a pre-1.1 build left world-readable
    is tightened to 0o600 by _sync_ensure_dir and the change is logged at
    INFO. And the general HA SOC Store itself is private with atomic
    writes, which is the other half of the same item.
    """
    audit = await _make_audit(hass, tmp_path)

    # Plant a pre-existing wide-mode file before the directory setup runs,
    # simulating an install upgrading from a pre-1.1 build.
    os.makedirs(audit._dir_path)
    legacy = os.path.join(audit._dir_path, "audit-2020-01-01.jsonl")
    with open(legacy, "w", encoding="utf-8") as handle:
        handle.write("")
    os.chmod(legacy, 0o644)

    with caplog.at_level(logging.INFO):
        await hass.async_add_executor_job(audit._sync_ensure_dir)
    assert os.stat(audit._dir_path).st_mode & 0o777 == 0o700
    assert os.stat(legacy).st_mode & 0o777 == 0o600
    assert "tightened 1 pre-existing audit file(s)" in caplog.text

    # Fresh writes are born private: a day file and the chain head (whose
    # .tmp staging file becomes the head via os.replace, preserving mode).
    audit.async_log("service_call", user_id="u1", domain="light", service="turn_on")
    await audit._async_flush()
    day_files = [path for _d, path in audit._sync_list_day_files()]
    assert day_files
    for path in day_files:
        assert os.stat(path).st_mode & 0o777 == 0o600
    head_path = os.path.join(audit._dir_path, "chain_head.json")
    assert os.stat(head_path).st_mode & 0o777 == 0o600

    # The general store: private=True, atomic_writes=True on the Store.
    assert audit._store._store._private is True
    assert audit._store._store._atomic_writes is True


async def test_service_data_redaction_is_deep(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Work item 1.6: the async_log chokepoint walks nested dicts and lists.

    Key matching is case-insensitive and exact (token redacted, token_id
    kept); message/title fall only for the notification-shaped domains and
    only on service calls; payload falls only for mqtt.publish.
    """
    audit = await _make_audit(hass, tmp_path)

    audit.async_log(
        "service_call",
        user_id="u1",
        domain="light",
        service="turn_on",
        detail={
            "password": "hunter2",
            "Token": "tok-value",
            "options": {"api_key": "k1", "nested": [{"client_secret": "cs"}]},
            "token_id": "tok-id-visible",
            "brightness_pct": 50,
        },
    )
    detail = _buffered(audit, "service_call")[0]["detail"]
    assert detail["password"] == "[redacted]"
    assert detail["Token"] == "[redacted]"
    assert detail["options"]["api_key"] == "[redacted]"
    assert detail["options"]["nested"][0]["client_secret"] == "[redacted]"
    assert detail["token_id"] == "tok-id-visible"
    assert detail["brightness_pct"] == 50

    audit.async_log(
        "service_call",
        domain="notify",
        service="mobile_app_phone",
        detail={"message": "the alarm went off", "title": "Alarm", "target": "phone"},
    )
    detail = _buffered(audit, "service_call")[1]["detail"]
    assert detail["message"] == "[redacted]"
    assert detail["title"] == "[redacted]"
    assert detail["target"] == "phone"

    audit.async_log(
        "service_call",
        domain="persistent_notification",
        service="create",
        detail={"message": "secret door open"},
    )
    assert _buffered(audit, "service_call")[2]["detail"]["message"] == "[redacted]"

    audit.async_log(
        "service_call",
        domain="mqtt",
        service="publish",
        detail={"payload": "creds-in-here", "topic": "home/lock"},
    )
    detail = _buffered(audit, "service_call")[3]["detail"]
    assert detail["payload"] == "[redacted]"
    assert detail["topic"] == "home/lock"

    # A non-publish mqtt call keeps its payload, and a record that is not a
    # service call (service=None) keeps title even for a notify domain: a
    # config entry named "My Notify" is metadata, not a notification body.
    audit.async_log(
        "service_call", domain="mqtt", service="dump", detail={"payload": "x"}
    )
    assert _buffered(audit, "service_call")[4]["detail"]["payload"] == "x"
    audit.async_log(
        "config_entry_change", domain="notify", detail={"title": "My Notify"}
    )
    assert _buffered(audit, "config_entry_change")[0]["detail"]["title"] == "My Notify"


async def test_high_value_records_flush_immediately(
    hass: HomeAssistant, tmp_path: Any
) -> None:
    """Work item 1.7: high-value categories schedule a flush task at once.

    A plain service_call waits for the 30 s timer; user_added, any
    firewall_* category, and an explicit flush=True do not. Before the
    chain head has been loaded nothing schedules at all - an unloaded
    instance flushing would chain records from genesis over a live chain.
    """
    audit = await _make_audit(hass, tmp_path)

    # Pre-load gate: high-value or not, nothing schedules until the head
    # is loaded; the record just buffers like it did before item 1.7.
    audit.async_log("user_removed", user_id="early", detail={"target_user_id": "x"})
    assert audit._flush_task is None
    assert len(audit._buffer) == 1
    audit._buffer.clear()

    await hass.async_add_executor_job(audit._sync_ensure_dir)
    await hass.async_add_executor_job(audit._sync_load_chain_head)

    audit.async_log("service_call", user_id="u1", domain="light", service="turn_on")
    assert audit._flush_task is None
    assert len(audit._buffer) == 1

    audit.async_log("user_added", user_id="admin", detail={"target_user_id": "new"})
    assert audit._flush_task is not None
    await hass.async_block_till_done()
    # The task drained the whole buffer, low-value record included, and the
    # records are on disk without any timer having fired.
    assert len(audit._buffer) == 0
    on_disk = await audit.hass.async_add_executor_job(
        lambda: [
            json.loads(line)
            for _d, path in audit._sync_list_day_files()
            for line in open(path, encoding="utf-8").read().splitlines()
            if line.strip()
        ]
    )
    assert {r["category"] for r in on_disk} == {"service_call", "user_added"}

    audit.async_log(
        "firewall_resolved", detail={"actor_source": "addon", "test_id": "t1"}
    )
    assert audit._flush_task is not None and not audit._flush_task.done()
    await hass.async_block_till_done()
    assert len(audit._buffer) == 0

    # flush=True forces the same behavior for a category outside the set.
    audit.async_log("service_call", user_id="u2", flush=True)
    assert audit._flush_task is not None and not audit._flush_task.done()
    await hass.async_block_till_done()
    assert len(audit._buffer) == 0
