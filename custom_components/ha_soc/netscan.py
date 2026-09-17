"""Secure configuration and result-validation contract for the Probe's optional netscan.

Netscan is local-subnet host/port discovery using TCP-connect liveness, a banner
grab, a TLS certificate read (no verification — self-signed is expected on a
LAN), and a MAC vendor label from the host's own ARP table. It is stdlib-only
in the Probe: no NET_RAW, no ICMP, no new privileges. See docs/security.md's
"Netscan capability" section and the netscan row in docs/THREAT-MODEL.md for
the gating reasoning; a LAN service map is a reconnaissance asset, so this
capability is owner-gated the same way firewall status is.

This module mirrors snmp.py's role: it builds the generation-tagged config the
Probe polls for, and it defines the schema the Probe's results are validated
against before they reach the store.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import voluptuous as vol

from .const import (
    CONF_NETSCAN_ENABLED,
    CONF_NETSCAN_MAX_CONCURRENCY,
    CONF_NETSCAN_PORT_LIST,
    DEFAULT_NETSCAN_MAX_CONCURRENCY,
    DEFAULT_NETSCAN_PORT_LIST,
    NETSCAN_MAX_CONCURRENCY_MAX,
    NETSCAN_MAX_CONCURRENCY_MIN,
    NETSCAN_MAX_PORT_LIST_ENTRIES,
    NETSCAN_PORT_MAX,
    NETSCAN_PORT_MIN,
)

_PORT = vol.All(vol.Coerce(int), vol.Range(min=NETSCAN_PORT_MIN, max=NETSCAN_PORT_MAX))

# Bounded text fields the Probe reports back; long enough for a real banner or
# certificate subject/issuer, short enough that a hostile or malfunctioning
# host on the LAN cannot use them to inflate stored data.
_BANNER_MAX = 256
_SERVICE_GUESS_MAX = 64
_TLS_FIELD_MAX = 256
_MAC_PATTERN = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")


def validate_port_list(value: Any) -> list[int]:
    """A de-duplicated, bounded list of TCP ports to sweep."""
    if value is None:
        return list(DEFAULT_NETSCAN_PORT_LIST)
    if not isinstance(value, (list, tuple)):
        raise vol.Invalid("netscan port list must be a list of ports")
    if len(value) > NETSCAN_MAX_PORT_LIST_ENTRIES:
        raise vol.Invalid(
            f"netscan port list may not exceed {NETSCAN_MAX_PORT_LIST_ENTRIES} entries"
        )
    ports: list[int] = []
    for item in value:
        port = _PORT(item)
        if port not in ports:
            ports.append(port)
    if not ports:
        raise vol.Invalid("netscan port list must not be empty")
    return ports


def validate_max_concurrency(value: Any) -> int:
    return vol.All(
        vol.Coerce(int),
        vol.Range(min=NETSCAN_MAX_CONCURRENCY_MIN, max=NETSCAN_MAX_CONCURRENCY_MAX),
    )(value)


def validate_mac(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if not _MAC_PATTERN.fullmatch(text):
        raise vol.Invalid("netscan MAC address is not a colon-separated hex address")
    return text.lower()


_TLS_SCHEMA = vol.Schema(
    {
        vol.Optional("subject"): vol.Any(None, vol.All(str, vol.Length(max=_TLS_FIELD_MAX))),
        vol.Optional("issuer"): vol.Any(None, vol.All(str, vol.Length(max=_TLS_FIELD_MAX))),
        vol.Optional("not_after"): vol.Any(None, vol.All(str, vol.Length(max=64))),
        vol.Optional("self_signed"): vol.Any(None, bool),
    }
)

# One open port on one discovered host: the port itself, whatever the connection
# handed back (banner and/or a TLS certificate), and the curated regex match
# against SERVICE_SIGNATURES, if any. Every text field is length-bounded before
# it ever reaches storage or the panel.
NETSCAN_OPEN_PORT_SCHEMA = vol.Schema(
    {
        vol.Required("port"): _PORT,
        vol.Optional("banner"): vol.Any(None, vol.All(str, vol.Length(max=_BANNER_MAX))),
        vol.Optional("service_guess"): vol.Any(
            None, vol.All(str, vol.Length(max=_SERVICE_GUESS_MAX))
        ),
        # "high" for a banner-text match, "low" for a port-only heuristic
        # fallback (see the Probe's PORT_SERVICE_HINTS); absent on older
        # results recorded before this field existed.
        vol.Optional("service_confidence"): vol.Any(None, vol.In(("high", "low"))),
        vol.Optional("tls"): vol.Any(None, _TLS_SCHEMA),
    }
)

# One discovered host: address, optional MAC/vendor from the ARP table union,
# and whatever ports answered. `vendor` is a label only, from the Probe's
# static, explicitly non-exhaustive OUI table — never treated as identity.
NETSCAN_HOST_SCHEMA = vol.Schema(
    {
        vol.Required("ip"): vol.All(str, vol.Length(max=45)),
        vol.Optional("mac"): vol.Any(None, validate_mac),
        vol.Optional("vendor"): vol.Any(None, vol.All(str, vol.Length(max=64))),
        vol.Optional("open_ports"): vol.Any(None, [NETSCAN_OPEN_PORT_SCHEMA]),
    }
)

# A whole cycle's worth of hosts; bounded so a misbehaving or hostile Probe
# cannot use one ingest call to write an unbounded amount of scan data.
NETSCAN_MAX_HOSTS_PER_RESULT = 1024


def candidate_hosts_for_service(
    netscan_result: Any, service: str
) -> list[dict[str, Any]]:
    """Hosts from the most recent stored netscan_result whose open_ports
    include a service_guess matching ``service`` (e.g. "pihole",
    "technitium"). Never raises: a missing/disabled/malformed result yields
    an empty list. One entry per host, de-duplicated, at the host's
    highest-confidence match ("high" wins over "low").

    ``netscan_result`` is store.py's stored shape: {"hosts": [...], ...}
    (see store.async_set_netscan_result), so a bare list is also accepted
    for convenience/testing.
    """
    hosts_list: Any = netscan_result
    if isinstance(netscan_result, dict):
        hosts_list = netscan_result.get("hosts")
    if not isinstance(hosts_list, list):
        return []
    out: dict[str, str] = {}
    for host in hosts_list:
        if not isinstance(host, dict):
            continue
        ip = host.get("ip")
        if not isinstance(ip, str) or not ip:
            continue
        for port_entry in host.get("open_ports") or []:
            if not isinstance(port_entry, dict):
                continue
            if port_entry.get("service_guess") != service:
                continue
            confidence = port_entry.get("service_confidence") or "low"
            if ip not in out or (confidence == "high" and out[ip] == "low"):
                out[ip] = confidence
    return [{"ip": ip, "confidence": confidence} for ip, confidence in sorted(out.items())]


async def async_config_for_probe(settings: dict[str, Any]) -> dict[str, Any]:
    """Build the Probe-facing netscan config, including a change token.

    Unlike SNMP's config there is no secret material here, so the generation
    exists purely so steady-state polling can skip re-sending an unchanged
    port list; nothing is withheld from a repeat poll.
    """
    enabled = bool(settings.get(CONF_NETSCAN_ENABLED, False))
    port_list = validate_port_list(settings.get(CONF_NETSCAN_PORT_LIST))
    max_concurrency = validate_max_concurrency(
        settings.get(CONF_NETSCAN_MAX_CONCURRENCY, DEFAULT_NETSCAN_MAX_CONCURRENCY)
    )
    material = {
        "enabled": enabled,
        "port_list": port_list,
        "max_concurrency": max_concurrency,
    }
    generation = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**material, "generation": generation}
