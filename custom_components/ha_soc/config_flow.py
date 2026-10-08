"""Config flow for HA SOC: single instance, no user input required at setup.

The options flow holds the optional Observe push settings (docs/design.md, "Observe
push"). Like every other HA SOC setting they are stored in the HA SOC store and the
private secret store, never in entry.options, so options stay {} (docs/security.md).
Submitting it also reloads the entry, which restarts the push with the new values and
re-registers the panel with the bundle currently on disk (see docs/operations.md).
"""
from __future__ import annotations

import ssl
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    DEFAULT_ACCESS_LEVEL,
    CONF_OBSERVE_CA_PEM,
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_FINGERPRINT,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DEFAULT_OBSERVE_ENABLED,
    DEFAULT_OBSERVE_INTERVAL,
    DOMAIN,
    MAX_OBSERVE_INTERVAL,
    MIN_OBSERVE_INTERVAL,
    REDACTED_PLACEHOLDER,
)
from .observe_push import ERROR_INVALID_CA, build_trust, validate_options

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


CONF_CLEAR_KEY = "observe_clear_key"


class HaSocOptionsFlow(OptionsFlow):
    """Observe push settings. Everything else lives in the panel Settings tab.

    Not OptionsFlowWithReload: options stay {} on purpose, so core would never see a
    change and never reload. The flow schedules the reload itself.
    """

    async def _async_actor_may_change(self, runtime: Any, actor_id: str) -> bool:
        """The owner always may; other administrators only under "owners and admins".

        Core does not pass the acting user to an options flow, so the actor comes from the
        flow context when present and otherwise from the HTTP request that is driving the
        flow. When neither names a user the flow proceeds, as it did before, and the audit
        record carries no user.
        """
        user = await self.hass.auth.async_get_user(actor_id)
        if user is None or not user.is_admin:
            return False
        if user.is_owner:
            return True
        level = runtime.store.settings.get("access_level", DEFAULT_ACCESS_LEVEL)
        return level == ACCESS_LEVEL_OWNER_AND_ADMINS

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return self.async_abort(reason="not_loaded")

        actor_id = self.context.get("user_id") or runtime.audit.current_actor_id()
        if actor_id is not None and not await self._async_actor_may_change(runtime, actor_id):
            return self.async_abort(reason="owner_required")

        settings = runtime.store.settings
        key_set = bool(await runtime.secrets.async_get(CONF_OBSERVE_INGEST_KEY))
        errors: dict[str, str] = {}

        if user_input is not None:
            clear_key = bool(user_input.get(CONF_CLEAR_KEY))
            errors, changes, new_key = validate_options(
                user_input,
                key_already_set=key_set and not clear_key,
                stored_url=settings.get(CONF_OBSERVE_URL),
            )
            if not errors and changes[CONF_OBSERVE_CA_PEM]:
                # The certificates parse as PEM; make sure the TLS library accepts them too.
                try:
                    await self.hass.async_add_executor_job(
                        build_trust, changes[CONF_OBSERVE_CA_PEM], None
                    )
                except (ssl.SSLError, ValueError):
                    errors[CONF_OBSERVE_CA_PEM] = ERROR_INVALID_CA
            if not errors:
                missing = object()
                before = {
                    key: deepcopy(settings[key]) if key in settings else missing
                    for key in changes
                }
                runtime.store.async_update_settings(**changes)
                # The reload builds a fresh store that reads the file, and the store
                # normally debounces its writes, so write now. A write that fails
                # must not look like success: put the settings back and say so.
                try:
                    await runtime.store.async_save_now()
                except HomeAssistantError:
                    # Only the keys this form changed: the panel may have changed
                    # others while the write was in flight.
                    for key, value in before.items():
                        if value is missing:
                            settings.pop(key, None)
                        else:
                            settings[key] = value
                    errors["base"] = "save_failed"
            if not errors:
                audited: dict[str, Any] = dict(changes)
                # The certificate text is long and public; the audit record names only that it is set.
                audited[CONF_OBSERVE_CA_PEM] = "set" if changes[CONF_OBSERVE_CA_PEM] else None
                if new_key:
                    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, new_key)
                    audited[CONF_OBSERVE_INGEST_KEY] = REDACTED_PLACEHOLDER
                elif clear_key:
                    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, None)
                    audited[CONF_OBSERVE_INGEST_KEY] = None
                runtime.audit.async_log(
                    "soc_config_change",
                    user_id=actor_id,
                    detail={"action": "observe_push_changed", "changes": audited},
                )
                self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        current = user_input or {
            CONF_OBSERVE_ENABLED: settings.get(CONF_OBSERVE_ENABLED, DEFAULT_OBSERVE_ENABLED),
            CONF_OBSERVE_URL: settings.get(CONF_OBSERVE_URL) or "",
            CONF_OBSERVE_HOST_NAME: settings.get(CONF_OBSERVE_HOST_NAME) or "",
            CONF_OBSERVE_INTERVAL: settings.get(CONF_OBSERVE_INTERVAL, DEFAULT_OBSERVE_INTERVAL),
            CONF_OBSERVE_CA_PEM: settings.get(CONF_OBSERVE_CA_PEM) or "",
            CONF_OBSERVE_FINGERPRINT: settings.get(CONF_OBSERVE_FINGERPRINT) or "",
        }
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_OBSERVE_ENABLED,
                    default=bool(current.get(CONF_OBSERVE_ENABLED, DEFAULT_OBSERVE_ENABLED)),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_OBSERVE_URL,
                    description={"suggested_value": current.get(CONF_OBSERVE_URL) or ""},
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
                # Never pre-filled: a blank field keeps the stored key.
                vol.Optional(CONF_OBSERVE_INGEST_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
                vol.Optional(CONF_CLEAR_KEY, default=False): selector.BooleanSelector(),
                vol.Optional(
                    CONF_OBSERVE_HOST_NAME,
                    description={"suggested_value": current.get(CONF_OBSERVE_HOST_NAME) or ""},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_OBSERVE_CA_PEM,
                    description={"suggested_value": current.get(CONF_OBSERVE_CA_PEM) or ""},
                ): selector.TextSelector(selector.TextSelectorConfig(multiline=True)),
                vol.Optional(
                    CONF_OBSERVE_FINGERPRINT,
                    description={"suggested_value": current.get(CONF_OBSERVE_FINGERPRINT) or ""},
                ): selector.TextSelector(),
                vol.Optional(
                    CONF_OBSERVE_INTERVAL,
                    default=int(current.get(CONF_OBSERVE_INTERVAL) or DEFAULT_OBSERVE_INTERVAL),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=MIN_OBSERVE_INTERVAL,
                        max=MAX_OBSERVE_INTERVAL,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="s",
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={"key_state": "set" if key_set else "not set"},
        )
