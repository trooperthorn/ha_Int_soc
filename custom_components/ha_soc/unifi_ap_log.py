"""Per-client join attempts, parsed from an access point's own log.

`unifi_wifi.py` reads the configuration that would refuse a join. This reads
what actually happened, which no UniFi API endpoint carries at any version:
alongside hostapd's authenticate and associate lines, UniFi's station tracker
(`stahtd`) emits one `STA_ASSOC_TRACKER` JSON object per attempt, with the
stage that failed, the failure counters, the signal at the time, and the
802.11 reason code when the client went away.

Two rules shape everything here.

An absent record is not a passing record. A log with no wireless events at all
is what an unadopted access point produces, and it looks identical to an
access point where every client is happy. `parse_log` reports what it saw,
including that it saw nothing, and never converts silence into "no failures".

The device's own clock is not to be trusted. An access point that cannot reach
the controller cannot reach NTP either, and its syslog timestamps drift years
out. The tracker's `auth_utc` is a real epoch and is preferred; the syslog
prefix is only a fallback and is marked as such.
"""
from __future__ import annotations

import json
import re
from typing import Any

# The tracker line, wherever it sits in a syslog record.
_TRACKER = re.compile(r"stahtd_dump_event\(\):\s*(\{.*\})\s*$")

# An unadopted device's log is almost entirely this; see the module docstring.
_INFORM_FAILURE = re.compile(r"ace_reporter\.reporter_fail\(\)|inform failed #", re.IGNORECASE)

# hostapd's own lines, used only to say wireless activity existed at all when
# the tracker is absent or silent on this firmware.
_HOSTAPD_STA = re.compile(r"hostapd\[\d+\]:\s+(?P<vap>\S+):\s+STA\s+(?P<mac>[0-9a-f:]{17})", re.IGNORECASE)

# IEEE 802.11 reason codes that say something about a join. Codes outside this
# set are reported as their number with no invented meaning.
REASON_CODES: dict[int, str] = {
    1: "Unspecified",
    2: "Previous authentication no longer valid",
    3: "Deauthenticated because the client is leaving",
    4: "Disassociated due to inactivity",
    5: "The access point cannot handle any more associated clients",
    6: "Class 2 frame from an unauthenticated client",
    7: "Class 3 frame from an unassociated client",
    8: "Disassociated because the client is leaving the BSS",
    9: "Client requested association without authenticating",
    14: "Message integrity check failure",
    15: "Four-way handshake timeout",
    16: "Group key handshake timeout",
    17: "Handshake element differs from the association request",
    18: "Invalid group cipher",
    19: "Invalid pairwise cipher",
    20: "Invalid AKMP",
    23: "802.1X authentication failed",
    24: "Cipher suite rejected by the security policy",
}

# Where an attempt stopped. Ordered: a later stage implies the earlier ones passed.
STAGE_AUTH = "802.11 authentication"
STAGE_ASSOC = "association"
STAGE_WPA = "WPA handshake"
STAGE_IP = "address assignment"
STAGE_NONE = "completed"

OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_SOFT = "soft failure"
OUTCOME_IN_PROGRESS = "in progress"
OUTCOME_LEFT = "left"


def _int(value: Any) -> int | None:
    """The tracker quotes its numbers, including negative ones."""
    if value in (None, ""):
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def reason_text(code: int | None) -> str | None:
    """A reason code's meaning, or None when the code is outside the table.

    Returning None rather than a guess matters: an unmapped code rendered as
    prose would read as an explanation the standard does not give.
    """
    if code is None:
        return None
    return REASON_CODES.get(code)


def _stage_and_outcome(raw: dict[str, Any]) -> tuple[str, str]:
    """Which stage an attempt reached, and how it ended.

    The tracker names the outcome; the stage has to be inferred from which
    counter it incremented, because a client that fails 802.11 authentication
    and one that fails the WPA handshake are different problems with different
    fixes, and both arrive as event_type "failure".
    """
    event = str(raw.get("event_type") or "").strip().lower()
    auth_failures = _int(raw.get("auth_failures")) or 0
    wpa_failures = _int(raw.get("wpa_auth_failures")) or 0

    if event == "success":
        return STAGE_NONE, OUTCOME_SUCCESS
    if event == "association":
        return STAGE_ASSOC, OUTCOME_IN_PROGRESS
    if event == "sta_leave":
        return STAGE_NONE, OUTCOME_LEFT
    if event == "soft failure":
        # The client got far enough to be tracked and then went away, usually
        # by roaming. Not a refusal.
        return STAGE_NONE, OUTCOME_SOFT
    if event == "failure":
        if wpa_failures:
            return STAGE_WPA, OUTCOME_FAILURE
        if auth_failures:
            return STAGE_AUTH, OUTCOME_FAILURE
        # A failure with neither counter set: the tracker saw it end badly but
        # did not say where. Naming a stage here would be invention.
        return "unknown", OUTCOME_FAILURE
    return "unknown", OUTCOME_IN_PROGRESS


def _event(raw: dict[str, Any]) -> dict[str, Any] | None:
    mac = str(raw.get("mac") or "").strip().lower()
    if not mac:
        return None
    stage, outcome = _stage_and_outcome(raw)
    disassoc = _int(raw.get("disassoc_reason"))
    deauth = _int(raw.get("deauth_reason"))
    code = disassoc if disassoc is not None else deauth
    return {
        "mac": mac,
        "vap": str(raw.get("vap") or "") or None,
        "event_type": str(raw.get("event_type") or "") or None,
        "outcome": outcome,
        "stage": stage,
        "auth_failures": _int(raw.get("auth_failures")) or 0,
        "wpa_auth_failures": _int(raw.get("wpa_auth_failures")) or 0,
        "auth_rssi": _int(raw.get("auth_rssi")),
        "avg_rssi": _int(raw.get("avg_rssi")),
        "auth_algo": str(raw.get("auth_algo") or "") or None,
        "ip_assign_type": str(raw.get("ip_assign_type") or "") or None,
        "dns_resp_seen": str(raw.get("dns_resp_seen") or "") or None,
        # Microseconds in the tracker's own units; kept raw, since what a
        # "slow" handshake is depends on the client, not on this parser.
        "auth_delta": _int(raw.get("auth_delta")),
        "assoc_delta": _int(raw.get("assoc_delta")),
        "wpa_auth_delta": _int(raw.get("wpa_auth_delta")),
        "ip_delta": _int(raw.get("ip_delta")),
        "reason_code": code,
        "reason": reason_text(code),
        "sta_dc_reason": str(raw.get("sta_dc_reason") or "") or None,
        # The tracker's own UTC clock, which survives a device whose syslog
        # timestamps have drifted; None when the line did not carry it.
        "at": _float(raw.get("auth_utc")),
    }


def parse_log(text: str) -> dict[str, Any]:
    """Everything one syslog excerpt says about wireless joins.

    ``events`` is every tracker record, oldest first. ``wireless_activity`` is
    whether the excerpt contained any wireless event at all, from the tracker
    or from hostapd: false means this log cannot answer the question, not that
    every client is fine. ``controller_unreachable`` flags the shape an
    unadopted device produces, which is the usual reason the answer is false.
    """
    events: list[dict[str, Any]] = []
    hostapd_lines = 0
    inform_failures = 0
    lines = 0

    for line in (text or "").splitlines():
        lines += 1
        if _INFORM_FAILURE.search(line):
            inform_failures += 1
        if _HOSTAPD_STA.search(line):
            hostapd_lines += 1
        match = _TRACKER.search(line)
        if not match:
            continue
        try:
            raw = json.loads(match.group(1))
        except ValueError:
            # A truncated final line is normal in a tail; skip it rather than
            # discard the whole excerpt.
            continue
        if not isinstance(raw, dict):
            continue
        event = _event(raw)
        if event is not None:
            events.append(event)

    return {
        "lines": lines,
        "events": events,
        "hostapd_station_lines": hostapd_lines,
        "wireless_activity": bool(events or hostapd_lines),
        "controller_unreachable": inform_failures > 0,
        "inform_failures": inform_failures,
    }


def summarize_clients(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per client: what it last did, and whether it ever got on.

    Sorted worst first, because the reason to read this is to find the clients
    that are failing. A client that succeeded once and failed later is not the
    same as one that never succeeded, so both facts are kept.
    """
    by_mac: dict[str, dict[str, Any]] = {}
    for event in events:
        row = by_mac.setdefault(
            event["mac"],
            {
                "mac": event["mac"],
                "vap": event["vap"],
                "attempts": 0,
                "failures": 0,
                "ever_succeeded": False,
                "last_outcome": None,
                "last_stage": None,
                "last_reason": None,
                "last_reason_code": None,
                "auth_failures": 0,
                "wpa_auth_failures": 0,
                "worst_rssi": None,
                "last_rssi": None,
                "last_seen_at": None,
            },
        )
        row["attempts"] += 1
        if event["vap"]:
            row["vap"] = event["vap"]
        if event["outcome"] == OUTCOME_SUCCESS:
            row["ever_succeeded"] = True
        if event["outcome"] == OUTCOME_FAILURE:
            row["failures"] += 1
        row["auth_failures"] += event["auth_failures"]
        row["wpa_auth_failures"] += event["wpa_auth_failures"]
        row["last_outcome"] = event["outcome"]
        row["last_stage"] = event["stage"]
        if event["reason_code"] is not None:
            row["last_reason_code"] = event["reason_code"]
            row["last_reason"] = event["reason"]
        rssi = event["avg_rssi"] if event["avg_rssi"] is not None else event["auth_rssi"]
        if rssi is not None:
            row["last_rssi"] = rssi
            if row["worst_rssi"] is None or rssi < row["worst_rssi"]:
                row["worst_rssi"] = rssi
        if event["at"] is not None:
            row["last_seen_at"] = event["at"]

    def _rank(row: dict[str, Any]) -> tuple[int, int, int]:
        # Never got on, and failing, first; then failure count; then weakest signal.
        never = 0 if (row["failures"] and not row["ever_succeeded"]) else 1
        return (never, -row["failures"], row["worst_rssi"] or 0)

    return sorted(by_mac.values(), key=_rank)


def analyze(text: str) -> dict[str, Any]:
    """parse_log plus the per-client rollup, as the panel consumes it."""
    parsed = parse_log(text)
    parsed["clients"] = summarize_clients(parsed["events"])
    return parsed
