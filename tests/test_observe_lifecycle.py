"""Observe push lifecycle: settings survive the options reload, and a failed setup stops the timer."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import observe_push as op
from custom_components.ha_soc.const import (
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DOMAIN,
)

ISOLATED_CONFIG_DIR = True

KEY = "wpi_" + "a" * 32


async def _no_push(self) -> None:
    return None


async def test_options_submit_then_reload_ends_with_push_active(hass, hass_storage) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    with patch.object(op.ObservePusher, "async_push_once", _no_push):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.runtime_data.observe.status["active"] is False

        result = await hass.config_entries.options.async_init(entry.entry_id)
        done = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "https://observe.example.com",
                CONF_OBSERVE_INGEST_KEY: KEY,
                CONF_OBSERVE_HOST_NAME: "haos-lab",
                CONF_OBSERVE_INTERVAL: 45,
            },
        )
        assert done["type"] == "create_entry"
        await hass.async_block_till_done()

        # The settings were written to storage by the flow itself, not left to the debounce.
        stored = next(v for k, v in hass_storage.items() if "settings" in v.get("data", {}))
        assert stored["data"]["settings"][CONF_OBSERVE_ENABLED] is True

        assert entry.state is ConfigEntryState.LOADED
        runtime = entry.runtime_data
        assert runtime.store.settings[CONF_OBSERVE_URL] == "https://observe.example.com"
        status = runtime.observe.status
        assert status["active"] is True
        assert status["interval_seconds"] == 45
        assert runtime.observe._unsub is not None


async def test_setup_failure_after_push_start_leaves_no_timer(hass) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    created: list[op.ObservePusher] = []
    real_start = op.ObservePusher.async_start

    async def start_enabled(self, config_entry) -> None:
        created.append(self)
        self._store.async_update_settings(
            **{
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "https://observe.example.com",
                CONF_OBSERVE_HOST_NAME: "haos-lab",
                CONF_OBSERVE_INTERVAL: 60,
            }
        )
        await self._secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)
        await real_start(self, config_entry)

    with (
        patch.object(op.ObservePusher, "async_push_once", _no_push),
        patch.object(op.ObservePusher, "async_start", start_enabled),
        patch(
            "custom_components.ha_soc.async_register_panel",
            side_effect=ConfigEntryNotReady("boom"),
        ),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert len(created) == 1
    assert created[0]._unsub is None
    assert created[0].status["active"] is False

    # Other components that setup started before the failure are outside this slice's
    # contract; stop them here so the harness does not report their timers as lingering.
    runtime = entry.runtime_data
    await runtime.audit.async_stop()
    await runtime.syslog.async_stop(drain=True)
    await runtime.permissions.async_stop()
    await runtime.health.async_stop()
    runtime.scanner.async_stop()
    runtime.watchdog.async_stop()
