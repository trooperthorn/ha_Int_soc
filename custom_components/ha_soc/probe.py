"""Optional HA SOC Probe add-on integration — Supervisor-only host visibility.

This module is the honest boundary between what this integration can see
on its own and what needs the companion add-on. From inside Home
Assistant's own Python process, a socket/port enumeration only sees the
container HA itself runs in — never the actual host's listening ports,
even on Home Assistant OS. Real port-scanning needs a process running
with host-level network access, which is what the optional `ha_soc_probe`
add-on provides (see README's "Optional HA SOC Probe add-on" section for
the full design rationale and what it deliberately does *not* cover).

Detecting the add-on is read-only and uses only public, documented hassio
helpers — no Supervisor websocket proxy calls, no assumptions about the
add-on's installed slug (Supervisor derives that from whatever repository
URL the user added, which this project doesn't control). Matching is done
on the add-on's `name:` field instead, a literal string this project's own
config.yaml owns and sets once.

Every caller of async_probe_overview() gets an honest, three-way answer,
never silently-empty data that could be misread as "scanned, nothing
found":
  - not running under Supervisor at all (Core/Container install) -> the
    feature is structurally unavailable here, full stop.
  - under Supervisor, add-on not installed -> available in principle, not
    set up yet.
  - add-on installed -> real state (running/stopped, version, and the
    latest ingested scan result, if any).
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.hassio import is_hassio
import homeassistant.util.dt as dt_util

from .const import (
    DOMAIN,
    PROBE_ADDON_NAME,
    SERVICE_INGEST_PROBE_RESULT,
    SERVICE_POLL_FIREWALL_COMMAND,
)
from .firewall import (
    RULE_SCHEMA,
    async_next_addon_command,
    async_report_from_addon,
    async_verify_or_pin_secret,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_PORT_SCHEMA = vol.Schema(
    {
        vol.Required("port"): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required("proto"): vol.In(["tcp", "udp"]),
        vol.Optional("process"): vol.Any(None, str),
        # Bind address decoded from /proc/net/tcp[6] (e.g. "192.168.10.5",
        # or "0.0.0.0" meaning every interface) and, for an IPv4 address
        # that isn't 0.0.0.0, a best-effort match against the host's own
        # `ip addr` output — real, since this add-on shares the host's
        # network namespace (host_network: true), not a guess. Both are
        # optional: an older add-on version predates these fields, and
        # IPv6 addresses are reported without interface resolution (see
        # run.sh — decoding IPv6's byte layout correctly wasn't worth the
        # risk of silently showing a wrong address).
        vol.Optional("address"): vol.Any(None, str),
        vol.Optional("interface"): vol.Any(None, str),
    }
)

INGEST_SERVICE_SCHEMA = vol.Schema(
    {
        # Optional, not required: the firewall poller (a separate,
        # ~5s-cadence s6 service from the port scanner) also calls this
        # service, purely to report firewall state, and must never be
        # forced to send a port list just to satisfy the schema — the
        # handler below only touches store.data["host_probe"] when
        # open_ports is actually present, so a firewall-only report can
        # never stomp the port scanner's own, much slower-cadence data.
        vol.Optional("open_ports"): [_PORT_SCHEMA],
        vol.Optional("scanner_version"): vol.Any(None, str),
        # Firewall report fields — all optional so an add-on build that
        # predates the firewall feature (or one where NET_ADMIN wasn't
        # granted) keeps reporting ports normally. The add-on includes
        # firewall_known_rules on its regular cycle, and calls this service
        # out-of-cycle immediately after a test is confirmed or reverted so
        # the two report fields below reach Core promptly rather than
        # waiting for the next slow poll.
        vol.Optional("firewall_known_rules"): vol.Any(None, [RULE_SCHEMA]),
        vol.Optional("firewall_resolved_test_id"): vol.Any(None, str),
        vol.Optional("firewall_resolved_status"): vol.Any(None, str),
        # Hard-cap application state from the resource-limit applier:
        # {slug: {"status": applied|failed|denied, "detail": str|None}}.
        # Optional so a Probe build predating the feature reports normally.
        vol.Optional("resource_limit_state"): vol.Any(None, {str: dict}),
        # Trust-on-first-use secret proving this call really came from the
        # add-on and not a forged local service call (see firewall.py).
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)

POLL_FIREWALL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("current_test_id"): vol.Any(None, str),
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)


def _addon_info(hass: HomeAssistant) -> dict[str, Any] | None:
    """This project's own add-on's cached info dict, or None if absent.

    Local import: `homeassistant.components.hassio` is only meaningfully
    populated when the `hassio` component is actually loaded (Supervisor
    installs), but the module itself is always importable on any install
    type — this never raises on Core/Container, get_addons_info() just
    returns None there.
    """
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


def async_register_probe_service(hass: HomeAssistant, store: HaSocData) -> None:
    """Register the add-on's two ways in: ha_soc.ingest_probe_result (its
    existing periodic report, now also carrying firewall state) and
    ha_soc.poll_firewall_command (a fast ~5s poll for pending firewall
    work — the reverse direction, using return_response=True on an
    ordinary service call rather than a new listening port on the add-on).

    Both are called via Supervisor's core-API proxy (SUPERVISOR_TOKEN +
    POST http://supervisor/core/api/services/ha_soc/<service>), the same
    mechanism any Supervisor add-on uses to call a Home Assistant service —
    no new communication channel on this side.
    """

    async def _handle_ingest(call: ServiceCall) -> None:
        # Reject a call that can't prove it came from the add-on — anyone
        # who can make a service call could otherwise forge a report. On
        # failure, process NOTHING (not even open_ports): a bad secret means
        # an untrusted caller, full stop.
        if not async_verify_or_pin_secret(store, call.data.get("probe_secret")):
            _LOGGER.warning(
                "HA SOC: rejected an ingest_probe_result call with a bad/missing "
                "probe secret — possible forged report, ignoring it."
            )
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
        )
        if call.data.get("resource_limit_state") is not None:
            from .resource_watchdog import async_store_limit_report

            async_store_limit_report(store, call.data["resource_limit_state"])

    async def _handle_poll_firewall(call: ServiceCall) -> dict:
        if not async_verify_or_pin_secret(store, call.data.get("probe_secret")):
            _LOGGER.warning(
                "HA SOC: rejected a poll_firewall_command call with a bad/missing "
                "probe secret — possible forged poll, returning no work."
            )
            return {"action": "none"}
        command = await async_next_addon_command(
            hass, store, current_test_id=call.data.get("current_test_id")
        )
        # Piggyback the owner-configured Docker hard caps on the same poll
        # channel (see resource_watchdog.py) — an older Probe build just
        # ignores the extra key. Only attached when caps are configured.
        from .resource_watchdog import async_resource_limits_for_probe

        limits = async_resource_limits_for_probe(store)
        if limits is not None:
            command["resource_limits"] = limits
        return command

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


def async_unregister_probe_service(hass: HomeAssistant) -> None:
    hass.services.async_remove(DOMAIN, SERVICE_INGEST_PROBE_RESULT)
    hass.services.async_remove(DOMAIN, SERVICE_POLL_FIREWALL_COMMAND)
