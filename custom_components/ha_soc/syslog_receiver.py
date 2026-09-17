"""Syslog RECEIVER: config/validation contract for the Probe's UDP listener.

Opposite direction from syslog_export.py: that module sends HA SOC's own
audit records out; this module ingests arbitrary syslog lines forwarded by
something else on the LAN, most notably the "logspout" HA add-on
(github.com/bertbaron/hassio-addons/logspout), which forwards every Docker
container's stdout/stderr to a configured ``syslog+udp://<host>:<port>``
target.

This phase is UDP-only. TCP/TLS receive support is a documented follow-up
(see docs/security.md's syslog receiver section) — logspout's simplest and
most commonly used config is UDP, and a listening TCP/TLS server is a larger
attack surface (connection lifecycle, framing, cert handling) that is not
justified until there's a concrete need.

Parsing is best-effort, not RFC-compliant: RFC 3164 (BSD syslog) and RFC 5424
headers are recognized well enough to extract PRI (facility/severity),
timestamp, hostname, and app-name/tag, with a raw fallback (the whole line
kept as the message) so a malformed or unrecognized line is never dropped.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from .const import (
    CONF_SYSLOG_RECEIVER_ENABLED,
    CONF_SYSLOG_RECEIVER_PORT,
    SYSLOG_RECEIVER_FIELD_MAX,
    SYSLOG_RECEIVER_MESSAGE_MAX,
)

# <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD]MSG  (RFC 5424)
_RFC5424_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<version>\d{1,2})\s+"
    r"(?P<timestamp>\S+)\s+(?P<hostname>\S+)\s+(?P<app>\S+)\s+"
    r"(?P<procid>\S+)\s+(?P<msgid>\S+)\s+(?P<rest>.*)$"
)

# <PRI>MMM DD HH:MM:SS HOSTNAME TAG[PID]: MSG  (RFC 3164 / BSD syslog)
_RFC3164_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<hostname>\S+)\s+"
    r"(?P<tag>[^:\[\s]+)(?:\[(?P<pid>\d+)\])?:\s*(?P<message>.*)$"
)

_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}

_SEVERITY_NAMES = [
    "emerg", "alert", "crit", "err", "warning", "notice", "info", "debug",
]


def _bound(value: Any, max_length: int) -> str:
    text = str(value if value is not None else "")
    return text[:max_length]


def _pri_to_facility_severity(pri: str) -> tuple[int, int]:
    try:
        pri_int = int(pri)
    except ValueError:
        pri_int = 13  # user.notice, syslog's own documented default
    pri_int = max(0, min(pri_int, 191))
    return pri_int // 8, pri_int % 8


def _rfc3164_timestamp(raw: str, *, receipt_time: datetime) -> str:
    """Best-effort parse of "Mmm DD HH:MM:SS"; the year is not on the wire,
    so it is inferred from the receipt time (rolling back one year if that
    would otherwise place the timestamp in the future)."""
    try:
        month_name = raw[:3]
        month = _MONTHS[month_name]
        rest = raw[3:].strip()
        day_str, time_str = rest.split(None, 1)
        day = int(day_str)
        hour, minute, second = (int(part) for part in time_str.split(":"))
        year = receipt_time.year
        candidate = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        if candidate > receipt_time:
            candidate = candidate.replace(year=year - 1)
        return candidate.isoformat()
    except (KeyError, ValueError, IndexError):
        return receipt_time.isoformat()


def parse_syslog_line(
    line: str, *, receipt_time: datetime | None = None, default_hostname: str = "homeassistant"
) -> dict[str, Any]:
    """Best-effort parse of one syslog line (RFC 3164 or RFC 5424).

    Never raises. A line whose header does not match either pattern falls
    back to storing the whole line as the message, with the receipt time as
    the timestamp and ``default_hostname`` (logspout's own documented
    default) as the hostname, so nothing is silently dropped.
    """
    if receipt_time is None:
        receipt_time = datetime.now(timezone.utc)
    raw = line.rstrip("\r\n")

    match = _RFC5424_RE.match(raw)
    if match:
        facility, severity = _pri_to_facility_severity(match.group("pri"))
        rest = match.group("rest")
        # Strip a leading structured-data block "[...]" (possibly several),
        # if present, to recover the plain message text.
        message = rest
        # The structured-data field's NILVALUE is a bare "-" (RFC 5424 6.3);
        # strip it before any "[...]" element(s) so it never leaks into the message.
        if message.startswith("-"):
            message = message[1:].lstrip()
        while message.startswith("["):
            depth = 0
            for idx, ch in enumerate(message):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        message = message[idx + 1 :].lstrip()
                        break
            else:
                break
        timestamp = match.group("timestamp")
        if timestamp == "-":
            timestamp = receipt_time.isoformat()
        return {
            "format": "rfc5424",
            "facility": facility,
            "severity": severity,
            "severity_name": _SEVERITY_NAMES[severity],
            "timestamp": timestamp,
            "hostname": _bound(match.group("hostname"), SYSLOG_RECEIVER_FIELD_MAX),
            "app_name": _bound(match.group("app"), SYSLOG_RECEIVER_FIELD_MAX),
            "message": _bound(message, SYSLOG_RECEIVER_MESSAGE_MAX),
            "raw": False,
        }

    match = _RFC3164_RE.match(raw)
    if match:
        facility, severity = _pri_to_facility_severity(match.group("pri"))
        return {
            "format": "rfc3164",
            "facility": facility,
            "severity": severity,
            "severity_name": _SEVERITY_NAMES[severity],
            "timestamp": _rfc3164_timestamp(match.group("timestamp"), receipt_time=receipt_time),
            "hostname": _bound(match.group("hostname"), SYSLOG_RECEIVER_FIELD_MAX),
            "app_name": _bound(match.group("tag"), SYSLOG_RECEIVER_FIELD_MAX),
            "message": _bound(match.group("message"), SYSLOG_RECEIVER_MESSAGE_MAX),
            "raw": False,
        }

    # Raw fallback: nothing is silently dropped.
    return {
        "format": "raw",
        "facility": None,
        "severity": None,
        "severity_name": None,
        "timestamp": receipt_time.isoformat(),
        "hostname": default_hostname,
        "app_name": None,
        "message": _bound(raw, SYSLOG_RECEIVER_MESSAGE_MAX),
        "raw": True,
    }


async def async_config_for_probe(settings: dict[str, Any]) -> dict[str, Any]:
    """Build the Probe-facing syslog receiver config, including a change token.

    No secret material, matching netscan's config shape: the generation only
    exists so steady-state polling can skip unnecessary work.
    """
    enabled = bool(settings.get(CONF_SYSLOG_RECEIVER_ENABLED, False))
    port = int(settings.get(CONF_SYSLOG_RECEIVER_PORT, 5514))
    material = {"enabled": enabled, "port": port}
    generation = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**material, "generation": generation}
