"""Tests for the syslog RECEIVER: RFC 3164/5424 parsing, config generation,
the bounded store ring buffer, INGEST_SERVICE_SCHEMA's syslog_entries bound,
and owner-gating on ha_soc/syslog_receiver/entries.

Follows test_netscan.py's Supervisor-context fixture pattern for the
ingest/poll service tests and its ws_netscan_status pattern for the
WebSocket owner-only check.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.ha_soc.const import (
    CONF_SYSLOG_RECEIVER_ENABLED,
    DOMAIN,
    SYSLOG_RECEIVER_MAX_ENTRIES,
)
from custom_components.ha_soc.store import HaSocData, default_store_data
from custom_components.ha_soc.syslog_receiver import (
    async_config_for_probe,
    parse_syslog_line,
)

PROBE_SECRET = "unit-test-probe-secret"

# --------------------------------------------------------------------------
# RFC 3164 / RFC 5424 parsing
# --------------------------------------------------------------------------


def test_parse_rfc5424_basic_line():
    line = '<34>1 2025-09-16T10:00:00.000Z homeassistant su - ID47 - BOM\'su root\' failed'
    entry = parse_syslog_line(line)
    assert entry["format"] == "rfc5424"
    assert entry["facility"] == 4
    assert entry["severity"] == 2
    assert entry["severity_name"] == "crit"
    assert entry["hostname"] == "homeassistant"
    assert entry["app_name"] == "su"
    assert "failed" in entry["message"]
    assert entry["raw"] is False


def test_parse_rfc5424_with_structured_data_strips_sd():
    line = '<165>1 2025-09-16T10:00:00Z myhost myapp 1234 ID1 [ha_soc@32473 seq="1"] the actual message'
    entry = parse_syslog_line(line)
    assert entry["format"] == "rfc5424"
    assert entry["hostname"] == "myhost"
    assert entry["app_name"] == "myapp"
    assert entry["message"] == "the actual message"


def test_parse_rfc5424_nil_timestamp_falls_back_to_receipt_time():
    receipt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    entry = parse_syslog_line("<13>1 - myhost myapp - - - hello", receipt_time=receipt)
    assert entry["timestamp"] == receipt.isoformat()


def test_parse_rfc3164_basic_line():
    receipt = datetime(2026, 6, 15, tzinfo=timezone.utc)
    line = "<34>Oct 11 22:14:15 mymachine su: 'su root' failed for lonvick"
    entry = parse_syslog_line(line, receipt_time=receipt)
    assert entry["format"] == "rfc3164"
    assert entry["facility"] == 4
    assert entry["severity"] == 2
    assert entry["hostname"] == "mymachine"
    assert entry["app_name"] == "su"
    assert "failed for lonvick" in entry["message"]
    # Year is inferred from receipt time (Oct is before Jun -> rolled back a year).
    assert entry["timestamp"].startswith("2025-10-11")


def test_parse_rfc3164_with_pid():
    line = "<13>Jan  5 10:00:00 host dockerd[123]: container started"
    entry = parse_syslog_line(line, receipt_time=datetime(2026, 1, 6, tzinfo=timezone.utc))
    assert entry["format"] == "rfc3164"
    assert entry["app_name"] == "dockerd"
    assert entry["message"] == "container started"


def test_parse_logspout_style_docker_line():
    # logspout's own documented default hostname and typical container tag shape.
    line = "<14>1 2026-01-01T00:00:00Z homeassistant my-container - - - hello from stdout"
    entry = parse_syslog_line(line)
    assert entry["hostname"] == "homeassistant"
    assert entry["app_name"] == "my-container"
    assert entry["message"] == "hello from stdout"


def test_parse_malformed_line_falls_back_to_raw():
    receipt = datetime(2026, 1, 1, tzinfo=timezone.utc)
    entry = parse_syslog_line("this is not syslog at all", receipt_time=receipt)
    assert entry["format"] == "raw"
    assert entry["raw"] is True
    assert entry["facility"] is None
    assert entry["severity"] is None
    assert entry["hostname"] == "homeassistant"
    assert entry["message"] == "this is not syslog at all"
    assert entry["timestamp"] == receipt.isoformat()


def test_parse_empty_line_does_not_raise():
    entry = parse_syslog_line("")
    assert entry["format"] == "raw"
    assert entry["message"] == ""


def test_parse_bounds_message_length():
    entry = parse_syslog_line("<13>1 - host app - - - " + ("x" * 10_000))
    assert len(entry["message"]) <= 4096


# --------------------------------------------------------------------------
# Config generation for the Probe
# --------------------------------------------------------------------------


async def test_config_for_probe_disabled_by_default():
    config = await async_config_for_probe({})
    assert config["enabled"] is False
    assert config["port"] == 5514
    assert config["generation"]


async def test_config_for_probe_generation_changes_with_settings():
    base = await async_config_for_probe({CONF_SYSLOG_RECEIVER_ENABLED: False})
    changed = await async_config_for_probe(
        {CONF_SYSLOG_RECEIVER_ENABLED: True, "syslog_receiver_port": 6000}
    )
    assert base["generation"] != changed["generation"]
    assert changed["enabled"] is True
    assert changed["port"] == 6000


# --------------------------------------------------------------------------
# Bounded ring-buffer store bucket
# --------------------------------------------------------------------------


async def test_append_syslog_entries_bounds_and_drops_oldest(hass: HomeAssistant):
    store = HaSocData(hass)
    store.data = default_store_data()

    store.async_append_syslog_entries(
        [{"message": "first"}, {"message": "second"}], max_entries=3
    )
    store.async_append_syslog_entries(
        [{"message": "third"}, {"message": "fourth"}], max_entries=3
    )

    buffer = store.data["syslog_receiver_entries"]
    assert len(buffer) == 3
    # Oldest ("first") was dropped; the most recent 3 survive in arrival order.
    assert [e["message"] for e in buffer] == ["second", "third", "fourth"]


async def test_append_syslog_entries_noop_on_empty_list(hass: HomeAssistant):
    store = HaSocData(hass)
    store.data = default_store_data()
    store.async_append_syslog_entries([])
    assert store.data["syslog_receiver_entries"] == []


async def test_append_syslog_entries_default_bound_matches_const(hass: HomeAssistant):
    store = HaSocData(hass)
    store.data = default_store_data()
    entries = [{"message": str(i)} for i in range(SYSLOG_RECEIVER_MAX_ENTRIES + 50)]
    store.async_append_syslog_entries(entries)
    assert len(store.data["syslog_receiver_entries"]) == SYSLOG_RECEIVER_MAX_ENTRIES
    # The tail (most recently appended) survives.
    assert store.data["syslog_receiver_entries"][-1]["message"] == str(
        SYSLOG_RECEIVER_MAX_ENTRIES + 49
    )


# --------------------------------------------------------------------------
# INGEST_SERVICE_SCHEMA's syslog_entries bound
# --------------------------------------------------------------------------


def _valid_entry(message="hello"):
    return {"format": "raw", "timestamp": "2026-01-01T00:00:00+00:00", "message": message}


def test_ingest_schema_accepts_within_bound():
    from custom_components.ha_soc.probe import INGEST_SERVICE_SCHEMA

    doc = INGEST_SERVICE_SCHEMA({"syslog_entries": [_valid_entry(), _valid_entry("two")]})
    assert len(doc["syslog_entries"]) == 2


def test_ingest_schema_rejects_oversized_batch():
    from custom_components.ha_soc.probe import INGEST_SERVICE_SCHEMA

    with pytest.raises(vol.Invalid):
        INGEST_SERVICE_SCHEMA({"syslog_entries": [_valid_entry() for _ in range(201)]})


def test_ingest_schema_rejects_oversized_message():
    from custom_components.ha_soc.probe import INGEST_SERVICE_SCHEMA

    with pytest.raises(vol.Invalid):
        INGEST_SERVICE_SCHEMA({"syslog_entries": [_valid_entry("x" * 5000)]})


def test_ingest_schema_rejects_bad_format():
    from custom_components.ha_soc.probe import INGEST_SERVICE_SCHEMA

    with pytest.raises(vol.Invalid):
        INGEST_SERVICE_SCHEMA(
            {"syslog_entries": [{"format": "not_a_format", "timestamp": "x", "message": "y"}]}
        )


def test_ingest_schema_accepts_syslog_receiver_status():
    from custom_components.ha_soc.probe import INGEST_SERVICE_SCHEMA

    doc = INGEST_SERVICE_SCHEMA(
        {
            "syslog_receiver_status": {
                "enabled": True,
                "running": True,
                "port": 5514,
                "entry_count": 12,
            }
        }
    )
    assert doc["syslog_receiver_status"]["port"] == 5514


# --------------------------------------------------------------------------
# Capability gating and ingest, mirroring test_netscan.py's Supervisor fixtures
# --------------------------------------------------------------------------


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def supervisor_context(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


async def test_poll_syslog_receiver_config_registered_and_gated(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context, tmp_path
) -> None:
    supervisor_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    assert hass.services.has_service(DOMAIN, "poll_syslog_receiver_config")

    intruder = MockUser()
    intruder.add_to_hass(hass)
    response = await hass.services.async_call(
        DOMAIN,
        "poll_syslog_receiver_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=Context(user_id=intruder.id),
    )
    assert response == {"enabled": False}

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=supervisor_context,
    )
    response = await hass.services.async_call(
        DOMAIN,
        "poll_syslog_receiver_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response["enabled"] is False  # default; owner never enabled it in this test
    assert "generation" in response
    assert "port" in response


async def test_ingest_syslog_entries_appends_to_store(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "syslog_entries": [_valid_entry("first"), _valid_entry("second")],
            "syslog_receiver_status": {"enabled": True, "running": True, "port": 5514},
            "probe_secret": PROBE_SECRET,
        },
        blocking=True,
        context=supervisor_context,
    )
    entries = supervisor_entry.runtime_data.store.data["syslog_receiver_entries"]
    assert [e["message"] for e in entries] == ["first", "second"]
    status = supervisor_entry.runtime_data.store.data["syslog_receiver_status"]
    assert status["running"] is True
    assert status["reported_at"]


async def test_ingest_syslog_entries_rejects_oversized_batch_end_to_end(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {
                "syslog_entries": [_valid_entry() for _ in range(500)],
                "probe_secret": PROBE_SECRET,
            },
            blocking=True,
            context=supervisor_context,
        )


async def test_unauthenticated_syslog_ingest_is_rejected(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, tmp_path
) -> None:
    supervisor_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    intruder = MockUser()
    intruder.add_to_hass(hass)
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"syslog_entries": [_valid_entry("should not land")], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=intruder.id),
    )
    assert supervisor_entry.runtime_data.store.data["syslog_receiver_entries"] == []


# --------------------------------------------------------------------------
# Websocket fetch command: owner-gating
# --------------------------------------------------------------------------


async def test_ws_syslog_receiver_entries_requires_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_syslog_receiver_entries

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=False)

    with pytest.raises(Unauthorized):
        ws_syslog_receiver_entries(hass, connection, {"id": 1, "limit": 200})


async def test_ws_syslog_receiver_entries_returns_page_for_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_syslog_receiver_entries

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    config_entry.runtime_data.store.async_append_syslog_entries(
        [_valid_entry("one"), _valid_entry("two"), _valid_entry("three")]
    )

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True)

    ws_syslog_receiver_entries(hass, connection, {"id": 1, "limit": 2})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["total"] == 3
    # Most recent first, bounded to the requested limit.
    assert [e["message"] for e in result["entries"]] == ["three", "two"]
