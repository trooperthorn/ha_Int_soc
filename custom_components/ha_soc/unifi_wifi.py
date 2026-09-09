"""Why a wireless client may be unable to join a broadcast.

The UniFi Network Integration API carries no association attempt, no
authentication failure, and no error counter for any client; a device that
cannot join is simply absent from every client collection. See
docs/UNIFI-LOCAL-API-CONTRACT.md. What the API does carry is the
configuration that decides whether a join is permitted at all, and that is
what this module reads: the SSID's own state, the radios it uses, the MAC
filter, and the set of access points allowed to broadcast it.

The one place a refused join IS recorded is the access point itself, in
hostapd's log. That is not an API and is not read here; the `wstalist`,
`mca_dump` and `syslog_tail` entries in ssh_devices.py reach it over the
read-only device SSH path instead.

Nothing here says a client failed. Each finding says a condition exists that
would refuse or hide the network from some class of device, and each carries
its own certainty, because "this SSID is disabled" and "this SSID may be off
right now on a schedule" are not the same claim.
"""
from __future__ import annotations

from typing import Any

# A finding is what the configuration proves, not what happened to a client.
SEVERITY_BLOCKING = "blocking"  # No client can join while this holds.
SEVERITY_POSSIBLE = "possible"  # Refuses some devices, or some of the time.
SEVERITY_UNKNOWN = "unknown"  # The API does not expose enough to say.


def _first(obj: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in obj and obj[key] not in (None, ""):
            return obj[key]
    return default


def _finding(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def _ap_scope(
    raw: dict[str, Any], device_names: dict[str, str], ap_count: int | None
) -> dict[str, Any]:
    """Which access points broadcast this SSID.

    ``broadcastingDeviceFilter`` is documented as "List of Access Point
    capable device IDs to which the WiFi broadcast applies". Its absence is
    the unrestricted case: every AP carries the SSID. A DEVICE_TAGS filter
    names tag ids the API exposes no route to resolve, so that case reports
    the tag count and claims nothing about which APs are covered.
    """
    filt = raw.get("broadcastingDeviceFilter")
    if not isinstance(filt, dict):
        return {"type": "ALL", "device_names": [], "unresolved": 0, "tag_count": 0}
    kind = str(_first(filt, "type", default="")).upper()
    if kind == "DEVICES":
        ids = [str(i) for i in (filt.get("deviceIds") or [])]
        names = sorted(device_names[i] for i in ids if i in device_names)
        return {
            "type": "DEVICES",
            "device_names": names,
            "unresolved": len(ids) - len(names),
            "tag_count": 0,
            "total_aps": ap_count,
        }
    if kind == "DEVICE_TAGS":
        return {
            "type": "DEVICE_TAGS",
            "device_names": [],
            "unresolved": 0,
            "tag_count": len(filt.get("deviceTagIds") or []),
        }
    return {"type": "ALL", "device_names": [], "unresolved": 0, "tag_count": 0}


def _client_filter(raw: dict[str, Any]) -> dict[str, Any] | None:
    policy = raw.get("clientFilteringPolicy")
    if not isinstance(policy, dict):
        return None
    action = str(_first(policy, "action", default="")).upper()
    if action not in ("ALLOW", "BLOCK"):
        return None
    return {"action": action, "count": len(policy.get("macAddressFilter") or [])}


def _blackout_days(raw: dict[str, Any]) -> int | None:
    schedule = raw.get("blackoutScheduleConfiguration")
    if not isinstance(schedule, dict):
        return None
    days = schedule.get("days")
    return len(days) if isinstance(days, list) else None


def _frequencies(raw: dict[str, Any]) -> list[float]:
    values = raw.get("broadcastingFrequenciesGHz")
    if not isinstance(values, list):
        return []
    out: list[float] = []
    for value in values:
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return sorted(out)


def _security_type(raw: dict[str, Any]) -> str | None:
    security = raw.get("securityConfiguration")
    if not isinstance(security, dict):
        return None
    return str(_first(security, "type", default="")).upper() or None


def _network_label(raw: dict[str, Any], network_names: dict[str, str]) -> str | None:
    """The network (and so the VLAN) the SSID puts its clients on.

    A NATIVE reference means the console's default network; a SPECIFIC one
    names a network id, which is what a VLAN migration changes.
    """
    network = raw.get("network")
    if not isinstance(network, dict):
        return None
    kind = str(_first(network, "type", default="")).upper()
    if kind == "NATIVE":
        return "Default network"
    network_id = _first(network, "networkId", "id")
    if network_id is None:
        return None
    return network_names.get(str(network_id)) or str(network_id)


def _likely_iot(ssid: str, kind: str | None) -> bool:
    """Whether this broadcast is the IoT network, for the default selection.

    Two signals, both from the API: the broadcast type the controller itself
    assigns, and the name. "iot" as a case-insensitive substring catches the
    common spellings, "IoT" and "wifiot" among them. It only chooses which
    SSID the view opens on; every SSID stays selectable.
    """
    return kind == "IOT_OPTIMIZED" or "iot" in ssid.lower()


def _findings(entry: dict[str, Any]) -> list[dict[str, str]]:
    """Plain statements about what this SSID's configuration refuses."""
    out: list[dict[str, str]] = []

    if entry["enabled"] is False:
        out.append(
            _finding(
                "ssid_disabled", SEVERITY_BLOCKING, "This SSID is turned off. No client can join it."
            )
        )

    client_filter = entry["client_filter"]
    if client_filter and client_filter["action"] == "ALLOW":
        out.append(
            _finding(
                "mac_allow_list",
                SEVERITY_BLOCKING,
                f"MAC filtering is set to allow only {client_filter['count']} listed "
                "addresses. Any device not on that list is refused.",
            )
        )
    elif client_filter and client_filter["count"]:
        out.append(
            _finding(
                "mac_block_list",
                SEVERITY_POSSIBLE,
                f"MAC filtering blocks {client_filter['count']} listed addresses. "
                "A device on that list is refused.",
            )
        )

    scope = entry["ap_scope"]
    if scope["type"] == "DEVICES":
        total = scope.get("total_aps")
        named = ", ".join(scope["device_names"]) or "no resolvable access point"
        count = len(scope["device_names"]) + scope["unresolved"]
        of_total = f" of {total}" if isinstance(total, int) and total else ""
        out.append(
            _finding(
                "ap_restricted",
                SEVERITY_POSSIBLE,
                f"Broadcast by {count}{of_total} access points: {named}. A client "
                "out of range of those cannot see this network, wherever else it roams.",
            )
        )
    elif scope["type"] == "DEVICE_TAGS":
        out.append(
            _finding(
                "ap_restricted_by_tag",
                SEVERITY_UNKNOWN,
                f"Broadcast is restricted to {scope['tag_count']} device tags. The API "
                "exposes no route to resolve a tag, so which access points carry this "
                "SSID cannot be determined here.",
            )
        )

    frequencies = entry["frequencies"]
    if frequencies and 2.4 not in frequencies:
        bands = ", ".join(f"{f:g} GHz" for f in frequencies)
        out.append(
            _finding(
                "no_2ghz",
                SEVERITY_BLOCKING,
                f"Broadcast only on {bands}. A 2.4 GHz-only device, which most IoT "
                "hardware is, cannot join.",
            )
        )

    security = entry["security"]
    if security and "WPA3" in security and "WPA2" not in security:
        out.append(
            _finding(
                "wpa3_only",
                SEVERITY_BLOCKING,
                f"Security is {security}. A device without WPA3 support cannot associate.",
            )
        )
    elif security == "OPEN":
        out.append(
            _finding(
                "open_security", SEVERITY_POSSIBLE, "This SSID is open, with no passphrase."
            )
        )

    if entry["hide_name"]:
        out.append(
            _finding(
                "hidden_ssid",
                SEVERITY_POSSIBLE,
                "The name is hidden. Devices that only join broadcast networks, and "
                "onboarding flows that scan for the SSID, will not find it.",
            )
        )

    days = entry["blackout_days"]
    if days:
        out.append(
            _finding(
                "blackout_schedule",
                SEVERITY_UNKNOWN,
                f"A blackout schedule covers {days} days. Whether it is in force at this "
                "moment is not evaluated here.",
            )
        )

    return out


def build_ssid_readiness(
    broadcast_rows: list[dict[str, Any]],
    device_names: dict[str, str],
    network_names: dict[str, str],
    ap_count: int | None = None,
) -> list[dict[str, Any]]:
    """One readiness entry per wifi broadcast, sorted by name.

    ``broadcast_rows`` are the raw rows from /wifi/broadcasts, ideally
    enriched with each broadcast's detail response: the collection response
    carries the SSID's state, radios, network and AP filter, while hideName,
    the MAC filter and the blackout schedule appear only in the detail.
    A row missing those simply produces fewer findings.
    """
    out: list[dict[str, Any]] = []
    for raw in broadcast_rows:
        name = _first(raw, "name", "ssid", "ssidName")
        if not name:
            continue
        enabled = raw.get("enabled")
        entry: dict[str, Any] = {
            "id": str(_first(raw, "id", "_id", default="")) or None,
            "ssid": str(name),
            "enabled": bool(enabled) if enabled is not None else None,
            "kind": str(_first(raw, "type", default="")).upper() or None,
            "security": _security_type(raw),
            "frequencies": _frequencies(raw),
            "network": _network_label(raw, network_names),
            "hide_name": raw.get("hideName"),
            "client_filter": _client_filter(raw),
            "blackout_days": _blackout_days(raw),
            "ap_scope": _ap_scope(raw, device_names, ap_count),
        }
        entry["likely_iot"] = _likely_iot(entry["ssid"], entry["kind"])
        entry["findings"] = _findings(entry)
        out.append(entry)
    return sorted(out, key=lambda e: e["ssid"].lower())


def build_absent_clients(
    history: dict[str, dict[str, Any]],
    connected_macs: set[str],
    now_ts: int,
) -> list[dict[str, Any]]:
    """Wireless clients the controller knows but that are not connected now.

    This is the population the Clients table can never show, and the one a
    device that cannot join belongs to. ``last_seen`` is the controller's
    last sighting; the absence of a client that has never connected at all
    means it is absent from here too, which is itself the answer when a
    device has never once associated.
    """
    out: list[dict[str, Any]] = []
    for mac, entry in history.items():
        if mac in connected_macs or entry.get("is_wired"):
            continue
        last_seen = entry.get("last_seen")
        out.append(
            {
                "mac": mac,
                "name": entry.get("name") or entry.get("hostname") or mac,
                "ssid": entry.get("essid"),
                "first_seen": entry.get("first_seen"),
                "last_seen": last_seen,
                "absent_seconds": (
                    max(0, now_ts - last_seen) if isinstance(last_seen, int) else None
                ),
            }
        )
    # Most recently seen first; a client with no timestamp sorts last.
    return sorted(out, key=lambda e: (e["last_seen"] is None, -(e["last_seen"] or 0)))
