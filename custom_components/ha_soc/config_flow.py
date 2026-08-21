"""Config flow for HA SOC — single instance, no user input required at setup."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    CONF_AUDIT_MAX_BYTES,
    CONF_AUDIT_RETENTION_DAYS,
    CONF_NVD_API_KEY,
    CONF_RISK_LEARNING_PERIOD_DAYS,
    CONF_SCANNER_ENABLED,
    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
    DEFAULT_AUDIT_MAX_BYTES,
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_RISK_LEARNING_PERIOD_DAYS,
    DEFAULT_SCANNER_ENABLED,
    DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
    DOMAIN,
)

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
    """Lets an admin tune retention, scanner network access, and the NVD key."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AUDIT_RETENTION_DAYS,
                    default=current.get(CONF_AUDIT_RETENTION_DAYS, DEFAULT_AUDIT_RETENTION_DAYS),
                ): vol.All(vol.Coerce(int), vol.Range(min=7, max=3650)),
                vol.Optional(
                    CONF_AUDIT_MAX_BYTES,
                    default=current.get(CONF_AUDIT_MAX_BYTES, DEFAULT_AUDIT_MAX_BYTES),
                ): vol.All(vol.Coerce(int), vol.Range(min=1_000_000)),
                vol.Optional(
                    CONF_SCANNER_ENABLED,
                    default=current.get(CONF_SCANNER_ENABLED, DEFAULT_SCANNER_ENABLED),
                ): bool,
                vol.Optional(
                    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
                    default=current.get(
                        CONF_SCANNER_NETWORK_CHECKS_ENABLED,
                        DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_NVD_API_KEY,
                    default=current.get(CONF_NVD_API_KEY, "") or "",
                ): str,
                vol.Optional(
                    CONF_RISK_LEARNING_PERIOD_DAYS,
                    default=current.get(
                        CONF_RISK_LEARNING_PERIOD_DAYS, DEFAULT_RISK_LEARNING_PERIOD_DAYS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
