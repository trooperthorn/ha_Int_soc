"""Config flow for HA SOC — single instance, no user input required at setup.

Every HA SOC setting is edited from the in-panel **Settings tab** (see
websocket_api.py's ha_soc/settings/* commands), which is gated to the
account **owner** only. This options flow used to mirror those settings so
they could also be changed from Home Assistant's native "Configure" dialog
— but that dialog is a different, weaker door: HA core gates it with a
generic admin check and never tells the flow which user is driving it, so
it cannot enforce HA SOC's owner-only rule. Editing security-sensitive
settings (the access level, API credentials) through it was a real
authorization bypass — any admin, not just the owner, could reach them.

So this flow no longer edits anything. It is a single informational step
that points the owner at the panel's Settings tab, where the real,
properly-gated controls live. HaSocData.settings (store.py) remains the
single source of truth.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import DOMAIN

NAME = "HA SOC"


class HaSocConfigFlow(ConfigFlow, domain=DOMAIN):
    """HA SOC only ever has one config entry — it's install-wide, not per-device."""

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
    """Informational only — all settings live in the owner-only Settings tab.

    Deliberately edits nothing. Home Assistant's native Configure dialog
    cannot identify the requesting user, so it cannot honor HA SOC's
    owner-only settings rule; exposing editable settings here was an
    authorization bypass. The one step just tells the user where the real
    controls are.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            # Always {} so a save through this dialog can never repopulate
            # entry.options: since work item SEC-2 the options mirror is
            # gone, nothing reads entry.options, and setup scrubs any
            # legacy copy to {} exactly once. Echoing the old options back
            # here would quietly resurrect the copy that scrub removed.
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "where": "Open the HA SOC panel from the sidebar and go to the "
                "Settings tab. All settings live there and are available to the "
                "account owner only."
            },
        )
