"""Optional HA SOC Probe add-on integration, Supervisor-only host visibility.

The boundary between what this integration can see on its own and what
needs the companion add-on. Protocol and authentication rules are in
docs/protocol.md and docs/security.md.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.hassio import is_hassio
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    FIREWALL_REPORT_REASON_MAX,
    PROBE_ADDON_NAME,
    SERVICE_INGEST_PROBE_RESULT,
    SERVICE_POLL_FIREWALL_COMMAND,
    SERVICE_POLL_SNMP_CONFIG,
)
from .firewall import (
    RULE_SCHEMA,
    async_next_addon_command,
    async_report_from_addon,
    async_verify_or_pin_secret,
)
from .secrets_store import HaSocSecretStore
from .snmp import async_config_for_probe
from .store import HaSocData

if TYPE_CHECKING:
    # Type-only import: this module must stay importable without audit.py at runtime.
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

# The audit record is written for every rejection; only the WARNING log line is rate-limited.
_REJECT_WARN_INTERVAL_SECONDS = 600
_SNMP_STATUS_ERROR_MAX = 200

_PORT_SCHEMA = vol.Schema(
    {
        vol.Required("port"): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required("proto"): vol.In(["tcp", "udp"]),
        vol.Optional("process"): vol.Any(None, str),
        vol.Optional("address"): vol.Any(None, str),
        vol.Optional("interface"): vol.Any(None, str),
    }
)

INGEST_SERVICE_SCHEMA = vol.Schema(
    {
        # Optional: the firewall poller calls this service too and never sends a port list.
        vol.Optional("open_ports"): [_PORT_SCHEMA],
        vol.Optional("scanner_version"): vol.Any(None, str),
        vol.Optional("firewall_known_rules"): vol.Any(None, [RULE_SCHEMA]),
        vol.Optional("firewall_resolved_test_id"): vol.Any(None, str),
        vol.Optional("firewall_resolved_status"): vol.Any(None, str),
        # Add-on-supplied text that is stored and rendered, so length-bounded.
        vol.Optional("firewall_resolved_reason"): vol.Any(
            None, vol.All(str, vol.Length(max=FIREWALL_REPORT_REASON_MAX))
        ),
        vol.Optional("firewall_ipv6_supported"): vol.Any(None, bool),
        vol.Optional("resource_limit_state"): vol.Any(None, {str: dict}),
        vol.Optional("snmp_status"): vol.Any(
            None,
            {
                vol.Required("enabled"): bool,
                vol.Required("running"): bool,
                vol.Optional("generation"): vol.Any(
                    None, vol.All(str, vol.Length(max=64))
                ),
                vol.Optional("listen_address"): vol.Any(
                    None, vol.All(str, vol.Length(max=45))
                ),
                vol.Optional("port"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=1, max=65535))),
                vol.Optional("error"): vol.Any(
                    None, vol.All(str, vol.Length(max=_SNMP_STATUS_ERROR_MAX))
                ),
            },
        ),
        # Optional in the schema so a missing secret reaches the handler and is audited as no_secret.
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)

POLL_FIREWALL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("current_test_id"): vol.Any(None, str),
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)

POLL_SNMP_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("generation"): vol.Any(
            None, vol.All(str, vol.Length(max=64))
        ),
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)


async def _async_supervisor_user_id(hass: HomeAssistant) -> str | None:
    """Resolve the Supervisor system user's id, or None when there is none."""
    try:
        from homeassistant.components.hassio.const import DATA_HASSIO_SUPERVISOR_USER

        supervisor_user = hass.data.get(DATA_HASSIO_SUPERVISOR_USER)
        if supervisor_user is not None and supervisor_user.id:
            return supervisor_user.id
    except ImportError:
        pass

    for user in await hass.auth.async_get_users():
        if user.system_generated and user.name == HASSIO_USER_NAME:
            return user.id
    return None


def _addon_info(hass: HomeAssistant) -> dict[str, Any] | None:
    """This project's own add-on's cached info dict, or None if absent."""
    from homeassistant.components.hassio import get_addons_info

    addons = get_addons_info(hass)
    if not addons:
        return None
    for info in addons.values():
        if info.get("name") == PROBE_ADDON_NAME:
            return info
    return None


async def async_probe_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the panel needs to render the Host Probe section honestly."""
    if not is_hassio(hass):
        return {
            "supervisor": False,
            "installed": False,
            "running": False,
            "version": None,
            "update_available": False,
            "result": None,
        }

    info = _addon_info(hass)
    return {
        "supervisor": True,
        "installed": info is not None,
        "running": bool(info is not None and info.get("state") == "started"),
        "version": info.get("version") if info is not None else None,
        "update_available": bool(info is not None and info.get("update_available")),
        "result": store.data.get("host_probe"),
    }


async def async_supervisor_call_rejection(
    hass: HomeAssistant, store: HaSocData, call: ServiceCall
) -> str | None:
    """None when the call carries the Supervisor user's context, else the reason.

    The Supervisor user id is cached on the store after the first resolution.
    A None Supervisor id means the user does not exist; nothing may pass.
    """
    supervisor_id = store.supervisor_user_id
    if supervisor_id is None:
        supervisor_id = await _async_supervisor_user_id(hass)
        store.supervisor_user_id = supervisor_id
    caller = call.context.user_id
    if caller is None or supervisor_id is None or caller != supervisor_id:
        return "not_supervisor"
    return None


def async_register_probe_service(
    hass: HomeAssistant, store: HaSocData, audit: "AuditLog", secrets: HaSocSecretStore
) -> None:
    """Register the add-on's authenticated service endpoints.

    Not registered at all on a non-Supervisor install; see docs/protocol.md.
    """
    if not is_hassio(hass):
        _LOGGER.debug(
            "HA SOC: not a Supervisor install; the Probe callback services "
            "are not registered."
        )
        return

    # The Supervisor user id is cached on the store runtime attribute after the first resolution.
    last_warned_at: dict[str | None, float] = {}

    async def _async_call_rejected(call: ServiceCall, service: str) -> str | None:
        """Authenticate one inbound call: None when trusted, else the rejection
        reason after recording the rejection."""
        caller_user_id = call.context.user_id
        reason: str | None = None

        supervisor_id = store.supervisor_user_id
        if supervisor_id is None:
            supervisor_id = await _async_supervisor_user_id(hass)
            store.supervisor_user_id = supervisor_id

        if caller_user_id is None or caller_user_id != supervisor_id:
            # A None supervisor_id here means the Supervisor user does not exist; nothing may pass.
            reason = "not_supervisor"
        else:
            presented = call.data.get("probe_secret") or None
            if presented is None:
                reason = "no_secret"
            elif not await async_verify_or_pin_secret(secrets, presented):
                reason = "bad_secret"

        if reason is None:
            return None

        audit.async_log(
            "probe_auth_rejected",
            user_id=caller_user_id,
            detail={
                "service": service,
                "caller_user_id": caller_user_id,
                "reason": reason,
            },
        )
        now = time.monotonic()
        if now - last_warned_at.get(caller_user_id, -_REJECT_WARN_INTERVAL_SECONDS) >= (
            _REJECT_WARN_INTERVAL_SECONDS
        ):
            last_warned_at[caller_user_id] = now
            _LOGGER.warning(
                "HA SOC: rejected a %s call (reason=%s, caller_user_id=%s). "
                "Further rejections from this caller are audited but not "
                "logged again for 10 minutes.",
                service,
                reason,
                caller_user_id,
            )
        return reason

    async def _handle_ingest(call: ServiceCall) -> None:
        # Authenticate first; a rejected caller must never be the one that pins the probe secret.
        if await _async_call_rejected(call, SERVICE_INGEST_PROBE_RESULT) is not None:
            return
        if call.data.get("open_ports") is not None:
            store.async_set_host_probe_result(
                {
                    "open_ports": call.data["open_ports"],
                    "scanner_version": call.data.get("scanner_version"),
                    "reported_at": dt_util.utcnow().isoformat(),
                }
            )
        await async_report_from_addon(
            hass,
            store,
            known_rules=call.data.get("firewall_known_rules"),
            resolved_test_id=call.data.get("firewall_resolved_test_id"),
            resolved_status=call.data.get("firewall_resolved_status"),
            resolved_reason=call.data.get("firewall_resolved_reason"),
            ipv6_supported=call.data.get("firewall_ipv6_supported"),
        )
        if call.data.get("resource_limit_state") is not None:
            from .resource_watchdog import async_store_limit_report

            async_store_limit_report(store, call.data["resource_limit_state"])
        if call.data.get("snmp_status") is not None:
            status = dict(call.data["snmp_status"])
            status["reported_at"] = dt_util.utcnow().isoformat()
            store.async_set_snmp_status(status)

    async def _handle_poll_firewall(call: ServiceCall) -> dict:
        # A rejected caller gets an empty answer, not an error.
        if await _async_call_rejected(call, SERVICE_POLL_FIREWALL_COMMAND) is not None:
            return {"action": "none"}
        command = await async_next_addon_command(
            hass, store, current_test_id=call.data.get("current_test_id")
        )
        # Only attached when caps are configured; an older Probe build ignores the extra key.
        from .resource_watchdog import async_resource_limits_for_probe

        limits = async_resource_limits_for_probe(store)
        if limits is not None:
            command["resource_limits"] = limits
        return command

    async def _handle_poll_snmp(call: ServiceCall) -> dict:
        if await _async_call_rejected(call, SERVICE_POLL_SNMP_CONFIG) is not None:
            return {"enabled": False}
        config = await async_config_for_probe(store.settings, secrets)
        if call.data.get("generation") == config["generation"]:
            # Steady-state polling never retransmits passphrases.
            return {"enabled": config["enabled"], "generation": config["generation"]}
        return config

    hass.services.async_register(
        DOMAIN, SERVICE_INGEST_PROBE_RESULT, _handle_ingest, schema=INGEST_SERVICE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_POLL_FIREWALL_COMMAND,
        _handle_poll_firewall,
        schema=POLL_FIREWALL_SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_POLL_SNMP_CONFIG,
        _handle_poll_snmp,
        schema=POLL_SNMP_SERVICE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )


def async_unregister_probe_service(hass: HomeAssistant) -> None:
    # Services are not registered off Supervisor; a bare async_remove would warn on every unload.
    for service in (
        SERVICE_INGEST_PROBE_RESULT,
        SERVICE_POLL_FIREWALL_COMMAND,
        SERVICE_POLL_SNMP_CONFIG,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
