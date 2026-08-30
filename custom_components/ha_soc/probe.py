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

Authentication of the two inbound services (ingest_probe_result and
poll_firewall_command): the add-on reaches Core only through the
Supervisor's core-API proxy, which forwards every call under the
Supervisor system user's own token and passes no add-on identity. Core
therefore requires exactly that context: a call whose context user is
missing or is any account other than the Supervisor system user is
rejected before its payload is looked at, audited as probe_auth_rejected,
and surfaced as a HIGH detection. The shared probe secret (pinned on the
first Supervisor-context call and held in the private secret store, see
firewall.py and secrets_store.py) stays as defense in depth behind that
check, and a call presenting no secret is rejected too. On a
Core or Container install (is_hassio false) there is no Supervisor proxy
and so no legitimate caller; the two services are not registered at all
there rather than registered-and-always-rejecting.
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
from .secrets_store import HaSocSecretStore
from .store import HaSocData

if TYPE_CHECKING:
    # Type-only import, mirroring detections.py's convention: this module
    # must stay importable without dragging in audit.py at runtime.
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

# A rejected caller is logged at WARNING at most once per caller per this
# interval. The audit record is written for EVERY rejection; only the log
# line is rate-limited, so a polling forger cannot flood the system log.
_REJECT_WARN_INTERVAL_SECONDS = 600

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
        # Shared secret, defense in depth behind the Supervisor-context
        # check performed by the handler (see firewall.py). Optional in
        # the schema so its absence reaches the handler, which rejects and
        # audits it as no_secret instead of failing schema validation.
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)

POLL_FIREWALL_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional("current_test_id"): vol.Any(None, str),
        vol.Optional("probe_secret"): vol.Any(None, str),
    }
)


async def _async_supervisor_user_id(hass: HomeAssistant) -> str | None:
    """Resolve the Supervisor system user's id, or None when there is none.

    Preferred source: the hassio component's own config store, which is
    where core records the id when it creates the user
    (hass.data[DATA_CONFIG_STORE].data.hassio_user, verified against core
    2026.2.3, components/hassio/__init__.py:341-361). DATA_CONFIG_STORE is
    internal to the hassio component, so the import is guarded and the
    public auth registry serves as the fallback: the Supervisor user is
    the system-generated user named HASSIO_USER_NAME ("Supervisor",
    homeassistant/const.py), created via async_create_system_user in that
    same code path.
    """
    try:
        from homeassistant.components.hassio.const import DATA_CONFIG_STORE

        config_store = hass.data.get(DATA_CONFIG_STORE)
        if config_store is not None:
            user_id = config_store.data.hassio_user
            if user_id:
                return user_id
    except ImportError:
        # An internal symbol moved between core versions; fall through to
        # the public auth registry rather than failing the lookup.
        pass

    for user in await hass.auth.async_get_users():
        if user.system_generated and user.name == HASSIO_USER_NAME:
            return user.id
    return None


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


def async_register_probe_service(
    hass: HomeAssistant, store: HaSocData, audit: "AuditLog", secrets: HaSocSecretStore
) -> None:
    """Register the add-on's two ways in: ha_soc.ingest_probe_result (its
    existing periodic report, now also carrying firewall state) and
    ha_soc.poll_firewall_command (a fast ~5s poll for pending firewall
    work — the reverse direction, using return_response=True on an
    ordinary service call rather than a new listening port on the add-on).

    Both are called via Supervisor's core-API proxy (SUPERVISOR_TOKEN +
    POST http://supervisor/core/api/services/ha_soc/<service>), the same
    mechanism any Supervisor add-on uses to call a Home Assistant service —
    no new communication channel on this side. Because that proxy forwards
    with the Supervisor's own token, every legitimate call arrives in the
    Supervisor system user's context, and both handlers below require
    exactly that before touching the payload (see the module docstring).

    On a non-Supervisor install nothing can legitimately call these
    services, so they are not registered at all; the panel already
    explains why the Host Probe feature is structurally unavailable there.
    """
    if not is_hassio(hass):
        _LOGGER.debug(
            "HA SOC: not a Supervisor install; the Probe callback services "
            "are not registered."
        )
        return

    # Log-rate-limit bookkeeping per caller, and the resolved Supervisor
    # user id. The id is cached on the store's runtime attribute after the
    # first successful resolution so steady-state polls (one every ~5s)
    # never re-enumerate the auth registry.
    last_warned_at: dict[str | None, float] = {}

    async def _async_call_rejected(call: ServiceCall, service: str) -> str | None:
        """Authenticate one inbound call. Returns None when the call is
        trusted, else the rejection reason after recording the rejection
        (audit record always, WARNING log at most once per caller per 10
        minutes).
        """
        caller_user_id = call.context.user_id
        reason: str | None = None

        supervisor_id = store.supervisor_user_id
        if supervisor_id is None:
            supervisor_id = await _async_supervisor_user_id(hass)
            store.supervisor_user_id = supervisor_id

        if caller_user_id is None or caller_user_id != supervisor_id:
            # Covers both a forged call from another user's session and a
            # context-less call (an automation); is_hassio was already
            # true at registration, so a None supervisor_id here means the
            # Supervisor user genuinely does not exist and nothing may pass.
            reason = "not_supervisor"
        else:
            presented = call.data.get("probe_secret") or None
            if presented is None:
                reason = "no_secret"
            elif not await async_verify_or_pin_secret(secrets, presented):
                # The pinned value lives in the private secret store
                # (SEC-1) and is fetched at use time; see firewall.py.
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
        # Authenticate before anything else. On failure, process NOTHING
        # (not even open_ports): an unauthenticated caller is untrusted,
        # full stop, and in particular must never be the one that pins the
        # probe secret.
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
        )
        if call.data.get("resource_limit_state") is not None:
            from .resource_watchdog import async_store_limit_report

            async_store_limit_report(store, call.data["resource_limit_state"])

    async def _handle_poll_firewall(call: ServiceCall) -> dict:
        # Same gate as ingest: authenticate before anything else, and hand
        # a rejected caller an empty answer rather than an error so a
        # forger learns nothing about pending firewall work.
        if await _async_call_rejected(call, SERVICE_POLL_FIREWALL_COMMAND) is not None:
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
    # On a non-Supervisor install the services were never registered (see
    # async_register_probe_service), so unregistration checks first; a bare
    # async_remove of an unknown service would log a spurious warning on
    # every unload of a Core or Container install.
    for service in (SERVICE_INGEST_PROBE_RESULT, SERVICE_POLL_FIREWALL_COMMAND):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)
