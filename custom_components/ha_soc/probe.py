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

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.hassio import is_hassio
import homeassistant.util.dt as dt_util

from .const import DOMAIN, PROBE_ADDON_NAME, SERVICE_INGEST_PROBE_RESULT
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
        vol.Required("open_ports"): [_PORT_SCHEMA],
        vol.Optional("scanner_version"): vol.Any(None, str),
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
    """Register ha_soc.ingest_probe_result — the add-on's only way in.

    Called via Supervisor's core-API proxy (SUPERVISOR_TOKEN + POST
    http://supervisor/core/api/services/ha_soc/ingest_probe_result), the
    same mechanism any Supervisor add-on uses to call a Home Assistant
    service — no new communication channel on this side.
    """

    @callback
    def _handle_ingest(call: ServiceCall) -> None:
        store.async_set_host_probe_result(
            {
                "open_ports": call.data["open_ports"],
                "scanner_version": call.data.get("scanner_version"),
                "reported_at": dt_util.utcnow().isoformat(),
            }
        )

    hass.services.async_register(
        DOMAIN, SERVICE_INGEST_PROBE_RESULT, _handle_ingest, schema=INGEST_SERVICE_SCHEMA
    )


def async_unregister_probe_service(hass: HomeAssistant) -> None:
    hass.services.async_remove(DOMAIN, SERVICE_INGEST_PROBE_RESULT)
