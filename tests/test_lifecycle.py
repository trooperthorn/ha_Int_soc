"""Setup failure, retry, unload and reload: nothing is left running and nothing is lost."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady, Unauthorized
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.ha_soc import (
    get_runtime_data,
    websocket_api as wa,
)
from custom_components.ha_soc import firewall
from custom_components.ha_soc import panel as panel_mod
from custom_components.ha_soc.audit import BAN_LOGGER_NAME, AuditLog
from custom_components.ha_soc.const import (
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DOMAIN,
)
from custom_components.ha_soc.observe_push import ObservePusher
from custom_components.ha_soc.store import StoreSaveError

ISOLATED_CONFIG_DIR = True

STORAGE_KEY = "ha_soc.storage"


def _chain_report(directory: str) -> tuple[int, int, int | None]:
    """Return (records, duplicate sequence numbers, first broken sequence number)."""
    prev = ""
    seqs: list[int] = []
    broken: int | None = None
    for name in sorted(n for n in os.listdir(directory) if n.startswith("audit-")):
        with open(os.path.join(directory, name), encoding="utf8") as handle:
            for line in handle:
                record = json.loads(line)
                seqs.append(record["seq"])
                body = {k: v for k, v in record.items() if k != "hash"}
                expected = hashlib.sha256(
                    (prev + json.dumps(body, sort_keys=True)).encode()
                ).hexdigest()
                if broken is None and (
                    record["prev_hash"] != prev or expected != record["hash"]
                ):
                    broken = record["seq"]
                prev = record["hash"]
    return len(seqs), len(seqs) - len(set(seqs)), broken


def _assert_runtime_stopped(runtime) -> None:
    """Every timer, listener and log handler the managers own has been released."""
    audit = runtime.audit
    assert audit._cancel_flush_timer is None
    assert audit._cancel_poll_timer is None
    assert not audit._unsubs
    assert audit._ban_handler is None
    assert runtime.health._timer_unsub is None
    assert runtime.health._dispatcher_unsub is None
    assert runtime.health._log_handler is None
    assert runtime.watchdog._unsub is None
    assert runtime.scanner._unsub_config_entry_changed is None
    assert runtime.permissions._unsub_bus is None
    assert runtime.observe._unsub is None
    assert runtime.crash_forensics._unsub_interval is None


async def test_setup_failure_then_retry_leaves_one_audit_log_and_no_timers(
    hass, freezer
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)

    created: list[AuditLog] = []
    real_init = AuditLog.__init__

    def recording_init(self, *args, **kwargs) -> None:
        real_init(self, *args, **kwargs)
        created.append(self)

    calls = {"n": 0}
    real_register = panel_mod.async_register_panel

    async def flaky_register(h):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConfigEntryNotReady("panel not ready")
        return await real_register(h)

    ban_logger = logging.getLogger(BAN_LOGGER_NAME)
    ban_before = len(ban_logger.handlers)

    def health_handlers() -> int:
        return sum(
            type(h).__name__ == "_HealthLogHandler"
            for h in logging.getLogger().handlers
        )

    with (
        patch.object(AuditLog, "__init__", recording_init),
        patch("custom_components.ha_soc.async_register_panel", flaky_register),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.SETUP_RETRY
        assert len(created) == 1
        # The failed attempt released everything it started, timers included,
        # before the retry runs.
        assert created[0]._cancel_flush_timer is None
        assert created[0]._cancel_poll_timer is None
        assert not created[0]._unsubs
        assert len(ban_logger.handlers) == ban_before
        assert health_handlers() == 0
        assert not hasattr(entry, "runtime_data")
        assert not hass.services.has_service(DOMAIN, "ingest_audit")
        with pytest.raises(RuntimeError, match="HA SOC is not set up"):
            get_runtime_data(hass)

        freezer.tick(timedelta(seconds=90))
        async_fire_time_changed(hass)
        # The retry runs as a background task of the config entry.
        await hass.async_block_till_done(wait_background_tasks=True)
        assert entry.state is ConfigEntryState.LOADED
        assert len(created) == 2
        assert entry.runtime_data.audit is created[1]
        # Exactly one failed-login handler, owned by the live audit log.
        assert len(ban_logger.handlers) == ban_before + 1
        assert health_handlers() == 1

        hass.bus.async_fire(
            "call_service",
            {
                "domain": "light",
                "service": "turn_on",
                "service_data": {"entity_id": "light.x"},
            },
        )
        await hass.async_block_till_done()
        freezer.tick(timedelta(seconds=31))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        audit = entry.runtime_data.audit
        await audit._async_flush()
        records, duplicates, broken = _chain_report(audit._dir_path)
        assert records > 0
        assert duplicates == 0
        assert broken is None
        assert (await audit.async_verify_chain())["ok"] is True

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert len(ban_logger.handlers) == ban_before
    assert health_handlers() == 0
    for audit_log in created:
        assert audit_log._cancel_flush_timer is None
        assert audit_log._cancel_poll_timer is None


async def test_failed_setup_stops_every_service(hass) -> None:
    """The failure comes after every service started, at the last setup step."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)

    seen: list = []
    real_start = ObservePusher.async_start

    async def start_enabled(self, config_entry) -> None:
        # Arm the push too, so a timer exists for every service that has one.
        self._store.async_update_settings(
            **{
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "https://observe.example.com",
                CONF_OBSERVE_HOST_NAME: "haos-lab",
                CONF_OBSERVE_INTERVAL: 60,
            }
        )
        await self._secrets.async_set(CONF_OBSERVE_INGEST_KEY, "wpi_" + "a" * 32)
        await real_start(self, config_entry)

    async def push_noop(self) -> None:
        return None

    async def failing_forward(config_entry, platforms):
        from custom_components.ha_soc import HaSocRuntimeData  # noqa: F401

        seen.append(config_entry.runtime_data)
        # Everything has started by now; prove it before failing.
        assert config_entry.runtime_data.audit._cancel_flush_timer is not None
        assert config_entry.runtime_data.health._timer_unsub is not None
        raise ConfigEntryNotReady("platforms not ready")

    with (
        patch.object(ObservePusher, "async_start", start_enabled),
        patch.object(ObservePusher, "async_push_once", push_noop),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", failing_forward
        ),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert len(seen) == 1
    _assert_runtime_stopped(seen[0])
    assert seen[0].observe.status["active"] is False
    assert not hass.services.has_service(DOMAIN, "ingest_audit")
    assert "ha_soc" not in hass.data.get("frontend_panels", {})


@pytest.mark.parametrize("reload", [False, True])
async def test_change_made_within_the_debounce_window_survives_unload_and_reload(
    hass, hass_storage, freezer, reload
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entry.runtime_data.store.async_update_settings(audit_retention_days=45)
    stored = hass_storage.get(STORAGE_KEY, {}).get("data", {}).get("settings", {})
    assert stored.get("audit_retention_days") != 45  # still inside the 15 s debounce

    freezer.tick(timedelta(seconds=2))
    if reload:
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data.store.settings["audit_retention_days"] == 45
    else:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert hass_storage[STORAGE_KEY]["data"]["settings"]["audit_retention_days"] == 45

    if reload:
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_unloaded_entry_gives_the_documented_error(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert get_runtime_data(hass) is entry.runtime_data

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED

    with pytest.raises(RuntimeError, match="HA SOC is not set up"):
        get_runtime_data(hass)
    # Callers that document "None when HA SOC is not set up" really get None.
    assert firewall._async_runtime_audit(hass) is None

    owner = MagicMock(is_admin=True, is_owner=True, id="owner")
    connection = MagicMock(user=owner)
    wa.ws_users_list(hass, connection, {"id": 7, "type": "ha_soc/users/list"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once_with(
        7, "not_loaded", "HA SOC is not set up"
    )
    connection.send_result.assert_not_called()

    # An administrator who is not the owner still fails closed to "unauthorized".
    admin = MagicMock(is_admin=True, is_owner=False, id="admin")
    with pytest.raises(Unauthorized):
        wa.ws_users_list(
            hass, MagicMock(user=admin), {"id": 8, "type": "ha_soc/users/list"}
        )

    # require_owner commands answer the same way.
    connection = MagicMock(user=owner)
    wa.ws_hacs_refresh_all(hass, connection, {"id": 9, "type": "ha_soc/hacs/refresh_all"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once_with(
        9, "not_loaded", "HA SOC is not set up"
    )

    # ha_soc/access/info stays on plain require_admin but gives the same answer.
    connection = MagicMock(user=owner)
    wa.ws_access_info(hass, connection, {"id": 10, "type": "ha_soc/access/info"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once_with(
        10, "not_loaded", "HA SOC is not set up"
    )
    connection.send_result.assert_not_called()


async def test_unload_twice_is_harmless(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    runtime = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    # Core ran the registered stop after the unload hook already stopped everything.
    await runtime.async_stop_services()
    _assert_runtime_stopped(runtime)


async def test_options_flow_shows_a_form_error_when_the_save_fails(
    hass, hass_storage
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)

    async def push_noop(self) -> None:
        return None

    with patch.object(ObservePusher, "async_push_once", push_noop):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data
        before = dict(runtime.store.settings)

        user_input = {
            CONF_OBSERVE_ENABLED: True,
            CONF_OBSERVE_URL: "https://observe.example.com",
            CONF_OBSERVE_INGEST_KEY: "wpi_" + "a" * 32,
            CONF_OBSERVE_HOST_NAME: "haos-lab",
            CONF_OBSERVE_INTERVAL: 60,
        }
        result = await hass.config_entries.options.async_init(entry.entry_id)
        with (
            patch.object(Store, "_async_write_data", side_effect=WriteError("disk full")),
            patch.object(
                hass.config_entries, "async_schedule_reload"
            ) as schedule_reload,
        ):
            failed = await hass.config_entries.options.async_configure(
                result["flow_id"], user_input
            )
        assert failed["type"] == "form"
        assert failed["errors"] == {"base": "save_failed"}
        schedule_reload.assert_not_called()
        # Nothing half-applied: the settings are back as they were.
        assert runtime.store.settings == before
        assert entry.state is ConfigEntryState.LOADED

        # Once the disk works again the same form submits.
        done = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input
        )
        assert done["type"] == "create_entry"
        await hass.async_block_till_done()
        assert entry.runtime_data.store.settings[CONF_OBSERVE_URL] == (
            "https://observe.example.com"
        )
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_failed_save_schedules_another_attempt_and_flush_does_not(
    hass, hass_storage
) -> None:
    """Core clears the pending save before it writes, so a failure must re-arm it."""
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    with patch.object(ObservePusher, "async_push_once", return_value=None):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        store = entry.runtime_data.store
        inner = store._store

        store.async_schedule_save()
        with patch.object(Store, "_async_write_data", side_effect=WriteError("disk full")):
            with pytest.raises(StoreSaveError):
                await store.async_save_now()
        assert inner._delay_handle is not None

        # A flush during teardown must not leave a timer behind.
        inner._async_cleanup_delay_listener()
        with patch.object(Store, "_async_write_data", side_effect=WriteError("disk full")):
            await store.async_flush()
        assert inner._delay_handle is None

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_stop_services_bounds_a_stalled_stop_and_still_flushes_the_store(
    hass, caplog
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    with patch.object(ObservePusher, "async_push_once", return_value=None):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        runtime = entry.runtime_data

        async def stalled(*_args, **_kwargs) -> None:
            await asyncio.sleep(3600)

        flushed = []
        real_flush = runtime.store.async_flush

        async def recording_flush() -> None:
            flushed.append(True)
            await real_flush()

        with (
            patch("custom_components.ha_soc.SERVICE_STOP_BUDGET", 0.2),
            patch.object(runtime.syslog, "async_stop", stalled),
            patch.object(runtime.store, "async_flush", recording_flush),
        ):
            await asyncio.wait_for(runtime.async_stop_services(), timeout=5)
        assert flushed == [True]
        assert "gave up waiting for syslog exporter" in caplog.text
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
