#!/usr/bin/env python3
"""Syslog RECEIVER for the HA SOC Probe. Stdlib only.

Long-running companion to netscan.py's one-shot-cycle design: this process
stays up for the life of the s6 service. It periodically polls Core (the
same poll/apply pattern as ha_soc_probe_snmp's `run` script) for the
owner-controlled enabled flag and listen port, runs (or stops) an asyncio
UDP syslog listener accordingly, parses each received line with the same
best-effort RFC 3164/5424 logic as the Core-side
custom_components/ha_soc/syslog_receiver.py module (duplicated here rather
than imported, since the Probe container has no access to the Core add-on's
Python package), buffers entries in a bounded in-memory deque (drop-oldest
on overflow -- Core is only pushed to periodically, not continuously, so
bursts must not grow this process's memory without bound), and periodically
POSTs a batch to Core via ingest_probe_result alongside status, the same
Supervisor-proxied, probe-secret-authenticated call every other Probe
service uses.

UDP only this phase; see docs/security.md's syslog receiver section for the
documented TCP/TLS follow-up.
"""
from __future__ import annotations

import asyncio
import collections
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

SCANNER_VERSION = "syslog_receiver/1.0"

POLL_INTERVAL_SECONDS = 30
BATCH_INTERVAL_SECONDS = 10
BATCH_MAX = 200
BUFFER_MAX = 2000
MESSAGE_MAX = 4096
FIELD_MAX = 255

_RFC5424_RE = re.compile(
    r"^<(?P<pri>\d{1,3})>(?P<version>\d{1,2})\s+"
    r"(?P<timestamp>\S+)\s+(?P<hostname>\S+)\s+(?P<app>\S+)\s+"
    r"(?P<procid>\S+)\s+(?P<msgid>\S+)\s+(?P<rest>.*)$"
)
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
_SEVERITY_NAMES = ["emerg", "alert", "crit", "err", "warning", "notice", "info", "debug"]


def _bound(value, max_length: int) -> str:
    text = str(value if value is not None else "")
    return text[:max_length]


def _pri_to_facility_severity(pri: str):
    try:
        pri_int = int(pri)
    except ValueError:
        pri_int = 13
    pri_int = max(0, min(pri_int, 191))
    return pri_int // 8, pri_int % 8


def _rfc3164_timestamp(raw: str, receipt_time: datetime) -> str:
    try:
        month = _MONTHS[raw[:3]]
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


def parse_syslog_line(line: str, receipt_time: datetime, default_hostname: str = "homeassistant") -> dict:
    """Mirror of the Core-side syslog_receiver.parse_syslog_line(); kept in
    sync manually since the two run in separate Python environments."""
    raw = line.rstrip("\r\n")

    match = _RFC5424_RE.match(raw)
    if match:
        facility, severity = _pri_to_facility_severity(match.group("pri"))
        rest = match.group("rest")
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
            "hostname": _bound(match.group("hostname"), FIELD_MAX),
            "app_name": _bound(match.group("app"), FIELD_MAX),
            "message": _bound(message, MESSAGE_MAX),
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
            "timestamp": _rfc3164_timestamp(match.group("timestamp"), receipt_time),
            "hostname": _bound(match.group("hostname"), FIELD_MAX),
            "app_name": _bound(match.group("tag"), FIELD_MAX),
            "message": _bound(match.group("message"), MESSAGE_MAX),
            "raw": False,
        }

    return {
        "format": "raw",
        "facility": None,
        "severity": None,
        "severity_name": None,
        "timestamp": receipt_time.isoformat(),
        "hostname": default_hostname,
        "app_name": None,
        "message": _bound(raw, MESSAGE_MAX),
        "raw": True,
    }


class _SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, buffer: "collections.deque[dict]") -> None:
        self._buffer = buffer

    def datagram_received(self, data: bytes, addr) -> None:  # noqa: D102
        try:
            line = data.decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 - never let a bad datagram kill the listener
            return
        entry = parse_syslog_line(line, datetime.now(timezone.utc))
        self._buffer.append(entry)


def _post_ingest(ingest_url: str, supervisor_token: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        ingest_url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.URLError:
        return 0


def _poll_config(poll_url: str, supervisor_token: str, probe_secret: str, generation: str) -> dict:
    payload = json.dumps({"generation": generation, "probe_secret": probe_secret}).encode("utf-8")
    request = urllib.request.Request(
        poll_url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
    except urllib.error.URLError:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed.get("service_response", parsed) if isinstance(parsed, dict) else {}


async def _run_listener(port: int, buffer: "collections.deque[dict]") -> asyncio.DatagramTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: _SyslogProtocol(buffer), local_addr=("0.0.0.0", port)  # nosec B104 - Probe is host_network
    )
    return transport


async def _async_main(poll_url: str, ingest_url: str) -> int:
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    probe_secret = os.environ.get("PROBE_SECRET", "")
    if not supervisor_token or not probe_secret:
        print("syslog_receiver: missing SUPERVISOR_TOKEN or PROBE_SECRET; refusing to run", file=sys.stderr)
        return 1

    buffer: "collections.deque[dict]" = collections.deque(maxlen=BUFFER_MAX)
    transport: asyncio.DatagramTransport | None = None
    current_generation = ""
    current_port: int | None = None
    last_batch_at = 0.0
    running = False
    error: str | None = None

    while True:
        config = await asyncio.get_running_loop().run_in_executor(
            None, _poll_config, poll_url, supervisor_token, probe_secret, current_generation
        )
        enabled = bool(config.get("enabled", False))
        generation = config.get("generation", current_generation)
        port = config.get("port", current_port)

        if not enabled:
            if transport is not None:
                transport.close()
                transport = None
                running = False
            current_generation = generation
        elif generation != current_generation or (enabled and transport is None):
            if transport is not None:
                transport.close()
                transport = None
            try:
                transport = await _run_listener(int(port), buffer)
                running = True
                error = None
                current_port = int(port)
            except OSError as err:
                running = False
                error = f"{type(err).__name__}: {err}"
            current_generation = generation

        # Batch + status report, on its own shorter cadence than the config poll.
        now = time.monotonic()
        if now - last_batch_at >= BATCH_INTERVAL_SECONDS:
            batch = []
            while buffer and len(batch) < BATCH_MAX:
                batch.append(buffer.popleft())
            status = {
                "enabled": enabled,
                "running": running,
                "generation": current_generation or None,
                "port": current_port,
                "entry_count": len(buffer),
                "last_received_at": batch[-1]["timestamp"] if batch else None,
                "error": error,
            }
            payload = {
                "syslog_receiver_status": status,
                "probe_secret": probe_secret,
            }
            if batch:
                payload["syslog_entries"] = batch
            await asyncio.get_running_loop().run_in_executor(
                None, _post_ingest, ingest_url, supervisor_token, payload
            )
            last_batch_at = now

        await asyncio.sleep(min(POLL_INTERVAL_SECONDS, BATCH_INTERVAL_SECONDS))


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="HA SOC Probe syslog receiver")
    parser.add_argument("--poll-url", required=True)
    parser.add_argument("--ingest-url", required=True)
    args = parser.parse_args()

    try:
        return asyncio.run(_async_main(args.poll_url, args.ingest_url))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
