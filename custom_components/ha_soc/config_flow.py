"""Config flow for HA SOC — single instance, no user input required at setup.

The options flow and the in-panel Settings tab (see websocket_api.py's
ha_soc/settings/* commands) are two UIs over the exact same underlying
state: HaSocData.settings (store.py), never `entry.options` directly.
`entry.options` is still written on every save (HA expects
`async_create_entry` to complete the flow, and it gives a value to prefill
from before the integration has ever been set up), but the moment the
runtime is reachable, both read their defaults from and write straight to
the live store — so changing a setting from either place takes effect
immediately, and neither one can silently revert the other back to a
stale value.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    CONF_ACCESS_LEVEL,
    CONF_AUDIT_MAX_BYTES,
    CONF_AUDIT_RETENTION_DAYS,
    CONF_MFA_GRACE_PERIOD_DAYS,
    CONF_MFA_POLICY,
    CONF_NVD_API_KEY,
    CONF_RISK_LEARNING_PERIOD_DAYS,
    CONF_SCANNER_ENABLED,
    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
    DEFAULT_ACCESS_LEVEL,
    DEFAULT_AUDIT_MAX_BYTES,
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_MFA_GRACE_PERIOD_DAYS,
    DEFAULT_MFA_POLICY,
    DEFAULT_RISK_LEARNING_PERIOD_DAYS,
    DEFAULT_SCANNER_ENABLED,
    DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
    DOMAIN,
    MFA_POLICY_AUDIT_ONLY,
    MFA_POLICY_AUTO_DEACTIVATE,
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
    """Lets an admin tune every HA SOC setting from Settings > Devices & Services.

    The same settings are also editable from the panel's own Settings tab
    while HA SOC is loaded — this dialog is the one that also works before
    first setup or if the panel itself is inaccessible (e.g. access_level
    is set to owner_only and a non-owner admin needs to loosen it back up).
    """

    def _live_settings(self) -> dict[str, Any] | None:
        try:
            from . import get_runtime_data  # local import: avoid a circular import at module load

            return dict(get_runtime_data(self.hass).store.settings)
        except RuntimeError:
            return None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            live = self._live_settings()
            if live is not None:
                from . import get_runtime_data

                get_runtime_data(self.hass).store.async_update_settings(**user_input)
            return self.async_create_entry(title="", data=user_input)

        current = self._live_settings() or dict(self.config_entry.options)
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ACCESS_LEVEL,
                    default=current.get(CONF_ACCESS_LEVEL, DEFAULT_ACCESS_LEVEL),
                ): vol.In([ACCESS_LEVEL_OWNER_ONLY, ACCESS_LEVEL_OWNER_AND_ADMINS]),
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
                vol.Optional(
                    CONF_MFA_POLICY,
                    default=current.get(CONF_MFA_POLICY, DEFAULT_MFA_POLICY),
                ): vol.In([MFA_POLICY_AUDIT_ONLY, MFA_POLICY_AUTO_DEACTIVATE]),
                vol.Optional(
                    CONF_MFA_GRACE_PERIOD_DAYS,
                    default=current.get(CONF_MFA_GRACE_PERIOD_DAYS, DEFAULT_MFA_GRACE_PERIOD_DAYS),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
