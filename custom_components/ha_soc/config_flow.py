"""Config flow for HA SOC: single instance, no user input required at setup.

The options flow carries no settings (they live in the owner-only panel
Settings tab, see docs/security.md); submitting it reloads the entry so the
panel re-registers with the bundle currently on disk (see docs/operations.md).
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import DOMAIN

NAME = "HA SOC"


class HaSocConfigFlow(ConfigFlow, domain=DOMAIN):
    """HA SOC only ever has one config entry; it is install-wide, not per-device."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HaSocOptionsFlow()


class HaSocOptionsFlow(OptionsFlow):
    """No settings here; submitting reloads the entry and re-registers the panel."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            # Options stay {} so core's change-triggered reload never fires; reload explicitly.
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "where": "Open the HA SOC panel from the sidebar and go to the "
                "Settings tab. All settings live there and are available to the "
                "account owner only. Submitting this dialog reloads HA SOC and "
                "re-registers the panel with the bundle currently installed; "
                "reload the browser afterwards to load it."
            },
        )
