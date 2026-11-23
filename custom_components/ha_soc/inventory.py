"""Persistent network device inventory built from the Probe's netscan cycles.

Design, identity rules, bounds and the threat model live in
docs/NETWORK-INVENTORY-DESIGN.md. This module holds phases 1 and 2 of that
design: the device record, the observation merge, the owner's verdict and
label, the certificates seen on the network, and the change events (a port
opened, a certificate changed, an identity shift) the detection rules read.

The merge (`merge_cycle`) is a pure function of the previous state, one cycle's
hosts and the clock, so recorded cycle sequences can be replayed in tests. The
manager (`NetworkInventory`) adds the Store file and the Home Assistant device
registry lookup.
"""
from __future__ import annotations

import ipaddress
import logging
import re
import secrets as _secrets
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .netscan import NETSCAN_MAX_DER_PER_RESULT, parse_certificates
from .store import HaSocStore

_LOGGER = logging.getLogger(__name__)

INVENTORY_STORAGE_KEY = f"{DOMAIN}.inventory"
INVENTORY_STORAGE_VERSION = 1
# Same delay as the syslog ring: a cycle arrives every 300 seconds, so a shorter
# delay would rewrite the file once per cycle.
INVENTORY_SAVE_DELAY = 300

VERDICT_UNACKNOWLEDGED = "unacknowledged"
VERDICT_ACKNOWLEDGED = "acknowledged"
VERDICT_IGNORED = "ignored"
VERDICTS = (VERDICT_UNACKNOWLEDGED, VERDICT_ACKNOWLEDGED, VERDICT_IGNORED)

IDENTITY_MAC = "mac"
IDENTITY_ADDRESS = "address"

SOURCE_PROBE_ARP = "probe_arp"
SOURCE_PROBE_TCP = "probe_tcp"
SOURCE_HA_REGISTRY = "ha_registry"
SOURCE_UNIFI = "unifi"
# Which name wins when the owner set no label: first in this list, then the rest
# in the order they were learned.
SOURCE_DHCP = "dhcp"
SOURCE_TRACKER = "tracker"
SOURCE_CERT = "cert"
NAME_PRECEDENCE = (SOURCE_HA_REGISTRY, SOURCE_UNIFI, SOURCE_DHCP, SOURCE_TRACKER, SOURCE_CERT)
# Sources that only ever add a name. They do not count as having seen the device.
PASSIVE_NAME_SOURCES = (SOURCE_DHCP, SOURCE_TRACKER)
_CERT_CN_RE = re.compile(r"(?:^|,)CN=((?:[^,\\]|\\.)+)")
_MAC_RE = re.compile(r"^[0-9a-f]{2}(:[0-9a-f]{2}){5}$")

# Fixed bounds, not owner-tunable: a hostile LAN must not be able to grow the file.
MAX_DEVICES = 4096
MAX_NAMES_PER_DEVICE = 8
MAX_ADDRESSES_PER_DEVICE = 4
MAX_PORTS_PER_DEVICE = 64
MAX_EVENTS = 2000
MAX_LABEL_LENGTH = 64
MAX_NAME_LENGTH = 128

DEFAULT_LEARNING_HOURS = 24
DEFAULT_RETENTION_DAYS = 30
# A port not seen open for this long is dropped from the record.
PORT_RETENTION_DAYS = 7

MAX_CERTS = 1024
# How many fingerprints the Probe is told about; it resends DER for the rest.
MAX_KNOWN_CERTS = 512
MAX_SIMULTANEOUS_ADDRESSES = 8
# A port counts as newly opened when it was not open in this many of the device's
# previous cycles. The same number of cycles is the settling time for a new device
# and for a port newly added to the scan list, during which nothing is reported.
PORT_QUIET_CYCLES = 3
# A certificate replaced by one with the same subject and issuer this close to its
# expiry is a renewal, not a change.
RENEWAL_WINDOW_DAYS = 30

EVENT_PORT_OPENED = "port_opened"
EVENT_PORT_CLOSED = "port_closed"
EVENT_CERT_CHANGED = "cert_changed"
EVENT_CERT_RENEWED = "cert_renewed"
EVENT_IDENTITY_SHIFT = "identity_shift"
CHANGE_EVENT_KINDS = (
    EVENT_PORT_OPENED,
    EVENT_PORT_CLOSED,
    EVENT_CERT_CHANGED,
    EVENT_CERT_RENEWED,
    EVENT_IDENTITY_SHIFT,
)
EVENT_DEVICE_DOWN = "device_down"
EVENT_DEVICE_BACK = "device_back"
EVENT_DUPLICATE_ADDRESS = "duplicate_address"
PRESENCE_EVENT_KINDS = (EVENT_DEVICE_DOWN, EVENT_DEVICE_BACK, EVENT_DUPLICATE_ADDRESS)

# Network health (phase 5).
DEFAULT_DUPLICATE_FLIPS = 3
ADDRESS_FLIP_WINDOW = timedelta(hours=1)
MAX_TRACKED_ADDRESSES = 4096
# How many judged cycles of drop counts are kept; a drop older than this is forgotten.
DROP_CYCLES_KEPT = 3
DROP_WINDOW = timedelta(hours=24)
MAX_DROPS_PER_DEVICE = 64
RESTART_GAP_MIN = timedelta(minutes=2)
RESTART_GAP_MAX = timedelta(hours=6)
GATEWAY_RECENT = timedelta(minutes=15)
GATEWAY_BASELINE = timedelta(hours=6)
GATEWAY_BASELINE_MIN_SAMPLES = 12
MAX_RTT_SAMPLES = 96

# Network roles (phase 6).
ROLE_GATEWAY = "gateway"
ROLE_DNS = "dns"
MAX_DNS_SERVERS = 8
# A trial sweep the Probe has not answered after this long is no longer offered to it.
TRIAL_PENDING = timedelta(minutes=10)
MAX_TRIAL_HOSTS = 256
WAN_PUBLIC = "public"
WAN_PRIVATE = "private"
WAN_CGNAT = "cgnat"
_RFC1918 = tuple(
    ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
_CGNAT = ipaddress.ip_network("100.64.0.0/10")


def classify_wan_address(value: Any) -> str | None:
    """What kind of address the gateway's WAN side holds, or None when it cannot be read.

    "private" (RFC 1918) means another router does NAT in front of this one.
    "cgnat" (100.64.0.0/10, RFC 6598) means the provider does. Anything else that
    is a valid IPv4 address is "public"; an IPv6 WAN address says nothing about
    IPv4 NAT and reads None.
    """
    try:
        address = ipaddress.ip_address(str(value))
    except ValueError:
        return None
    if address.version != 4 or address.is_unspecified or address.is_loopback:
        return None
    if address in _CGNAT:
        return WAN_CGNAT
    if any(address in network for network in _RFC1918):
        return WAN_PRIVATE
    return WAN_PUBLIC


def host_network_roles(network_info: Any) -> dict[str, Any]:
    """The gateway and DNS servers the Home Assistant host is configured with.

    ``network_info`` is the Supervisor's network information as a dict
    (docs/protocol.md, "Supervisor network information"). The primary interface
    wins; without one, the first connected interface with IPv4 settings does.
    Anything missing or malformed reads as not known. Never raises.
    """
    roles: dict[str, Any] = {"gateway": None, "dns": []}
    interfaces = network_info.get("interfaces") if isinstance(network_info, dict) else None
    if not isinstance(interfaces, list):
        return roles
    usable = [
        i for i in interfaces
        if isinstance(i, dict) and isinstance(i.get("ipv4"), dict) and i.get("connected")
    ]
    usable.sort(key=lambda i: not i.get("primary"))
    for interface in usable[:1]:
        ipv4 = interface["ipv4"]
        for candidate in ipv4.get("nameservers") or []:
            try:
                address = str(ipaddress.IPv4Address(str(candidate)))
            except ValueError:
                continue
            if address not in roles["dns"] and len(roles["dns"]) < MAX_DNS_SERVERS:
                roles["dns"].append(address)
        try:
            roles["gateway"] = str(ipaddress.IPv4Address(str(ipv4.get("gateway"))))
        except ValueError:
            pass
    return roles
DEFAULT_DOWN_CYCLES = 3
# Two sightings this close together are one stay: one missed cycle does not split it.
PRESENCE_JOIN = timedelta(minutes=11)
PRESENCE_RETENTION_DAYS = 30
MAX_PRESENCE_SEGMENTS = 512
PRESENCE_OVERVIEW_HOURS = 24
SHIFT_TWO_ADDRESSES = "two_addresses"
SHIFT_PORTS_AND_CERTIFICATE = "ports_and_certificate"
RECENT_CHANGE_DAYS = 7

# Exposure findings (phase 3). A service is recognized by the Probe's banner guess
# or, failing that, by its registered port; the finding says which.
CLEARTEXT_SERVICES: dict[str, dict[str, Any]] = {
    "telnet": {"port": 23, "severity": "high", "label": "Telnet"},
    "ftp": {"port": 21, "severity": "medium", "label": "FTP"},
    "vnc": {"port": 5900, "severity": "medium", "label": "VNC"},
}
_CLEARTEXT_BY_PORT = {spec["port"]: name for name, spec in CLEARTEXT_SERVICES.items()}
HTTP_PORTS = (80, 8080)
HTTPS_PORTS = (443, 8443)
CERT_EXPIRY_LOW_DAYS = 14
CERT_EXPIRY_INFO_DAYS = 30
BASIS_BANNER = "banner"
BASIS_PORT = "port"
RECENT_CHANGES_PER_DEVICE = 5


def mac_kind(mac: str) -> str:
    """"local" for a locally administered (randomized) MAC, otherwise "global"."""
    try:
        first_octet = int(mac[:2], 16)
    except ValueError:
        return "global"
    return "local" if first_octet & 0x02 else "global"


def empty_state() -> dict[str, Any]:
    return {
        "meta": {
            "learning_started_at": None,
            "last_cycle_at": None,
            "cycles": 0,
            "cap_reached_at": None,
            # port -> how many cycles it has been in the scan list, see merge_cycle.
            "scan_ports": {},
            # The Probe host's default next hop, and the device last seen at it.
            "gateway_ip": None,
            "gateway_device_id": None,
            # The host's configured DNS servers, and where they and the gateway came from.
            "dns_servers": [],
            "roles_source": None,
            # The kind of address on the gateway's WAN side, never the address itself.
            "wan": None,
            # ip -> {"device_id": holder, "flips": [times the holder changed]}.
            "address_holders": {},
            # The last DROP_CYCLES_KEPT judged cycles: {"at", "dropped", "of"}.
            "drop_cycles": [],
        },
        "devices": {},
        # fingerprint -> the parsed certificate, see async_absorb_certificates.
        "certs": {},
        # ip -> first cycle a MAC-less host was seen, see merge_cycle.
        "pending": {},
        "events": [],
    }


def _new_device_id() -> str:
    return f"d_{_secrets.token_hex(5)}"


@dataclass
class MergeOutcome:
    """What one cycle changed."""

    created: list[str] = field(default_factory=list)
    changed: bool = False


def _append_event(state: dict[str, Any], now_iso: str, device_id: str, kind: str, **detail: Any) -> None:
    events = state["events"]
    events.append({"ts": now_iso, "device_id": device_id, "kind": kind, **detail})
    if len(events) > MAX_EVENTS:
        del events[: len(events) - MAX_EVENTS]


def _prunable(device: dict[str, Any]) -> bool:
    """Only a record the owner never touched may be removed automatically."""
    return (
        device.get("verdict") == VERDICT_UNACKNOWLEDGED
        and not device.get("label")
        and not device.get("watched")
    )


def _parse(value: Any) -> datetime | None:
    return dt_util.parse_datetime(value) if isinstance(value, str) else None


def _make_room(state: dict[str, Any], now_iso: str) -> bool:
    """Free one slot at the cap. Returns False when nothing may be removed."""
    devices = state["devices"]
    if len(devices) < MAX_DEVICES:
        return True
    state["meta"]["cap_reached_at"] = now_iso
    candidates = [d for d in devices.values() if _prunable(d)]
    if not candidates:
        return False
    oldest = min(candidates, key=lambda d: d.get("last_seen") or "")
    del devices[oldest["id"]]
    _append_event(state, now_iso, oldest["id"], "pruned", reason="cap")
    return True


def _set_address(
    state: dict[str, Any], device: dict[str, Any], ip: str, now_iso: str, *, secondary: bool = False
) -> bool:
    """Record where the device is. ``secondary`` is a second address in the same
    cycle: it is kept, but the first one stays the current address, so a device
    with two addresses does not flip between them on every cycle."""
    addresses = device["addresses"]
    if addresses and addresses[0]["ip"] == ip:
        return False
    if secondary:
        if any(a["ip"] == ip for a in addresses):
            return False
        addresses.insert(1, {"ip": ip, "since": now_iso})
        del addresses[MAX_ADDRESSES_PER_DEVICE:]
        return True
    previous = addresses[0]["ip"] if addresses else None
    addresses[:] = [a for a in addresses if a["ip"] != ip]
    addresses.insert(0, {"ip": ip, "since": now_iso})
    del addresses[MAX_ADDRESSES_PER_DEVICE:]
    if previous is not None:
        _append_event(state, now_iso, device["id"], "address_changed", previous=previous, ip=ip)
    return True


def _is_renewal(certs: dict[str, Any], old: str, new: str, now: datetime) -> bool:
    """Same subject and issuer, and the old certificate was close to expiry or past it."""
    before, after = certs.get(old), certs.get(new)
    if not before or not after or before.get("unreadable") or after.get("unreadable"):
        return False
    if not before.get("subject") or not before.get("issuer"):
        return False
    if before["subject"] != after.get("subject") or before["issuer"] != after.get("issuer"):
        return False
    expiry = _parse(before.get("not_after"))
    return expiry is not None and expiry - now <= timedelta(days=RENEWAL_WINDOW_DAYS)


def _observe_ports(
    device: dict[str, Any],
    open_ports: Any,
    now: datetime,
    now_iso: str,
    *,
    settled: Callable[[int], bool],
    certs: dict[str, Any],
) -> tuple[bool, list[dict[str, Any]]]:
    """Fold one host's open ports into the device. Returns (changed, change events).

    ``settled`` says whether a port has been in the scan list long enough for its
    first sighting to mean it opened, rather than that the scan started looking.
    """
    changed = False
    changes: list[dict[str, Any]] = []
    ports = device["ports"]
    seen = int(device.get("seen_cycles") or 0)
    for entry in open_ports or []:
        if not isinstance(entry, dict) or "port" not in entry:
            continue
        port = int(entry["port"])
        key = str(port)
        record = ports.get(key)
        opened = False
        if record is None:
            if len(ports) >= MAX_PORTS_PER_DEVICE:
                continue
            record = ports[key] = {"first_seen": now_iso}
            changed = True
            opened = True
        elif record.get("closed_at") is not None:
            record["closed_at"] = None
            changed = True
            opened = True
        if opened and seen > PORT_QUIET_CYCLES and settled(port):
            changes.append({"kind": EVENT_PORT_OPENED, "port": port})
        record["last_seen"] = now_iso
        record["last_seen_cycle"] = seen
        record["service"] = entry.get("service_guess")
        record["confidence"] = entry.get("service_confidence")
        tls = entry.get("tls")
        fingerprint = tls.get("sha256") if isinstance(tls, dict) else None
        if fingerprint and record.get("cert_sha256") != fingerprint:
            previous = record.get("cert_sha256")
            record["cert_sha256"] = fingerprint
            record["cert_since"] = now_iso
            changed = True
            if previous:
                renewal = _is_renewal(certs, previous, fingerprint, now)
                changes.append(
                    {
                        "kind": EVENT_CERT_RENEWED if renewal else EVENT_CERT_CHANGED,
                        "port": port,
                        "previous": previous,
                        "sha256": fingerprint,
                    }
                )
    cutoff = now - timedelta(days=PORT_RETENTION_DAYS)
    for key in [k for k, r in ports.items() if (_parse(r.get("last_seen")) or now) < cutoff]:
        del ports[key]
        changed = True
    return changed, changes


def _close_quiet_ports(
    device: dict[str, Any], now_iso: str, scanned: set[int] | None
) -> list[dict[str, Any]]:
    """Mark ports that stayed shut for PORT_QUIET_CYCLES of the device's cycles.

    A port that left the scan list is not closed, it is just no longer looked at.
    """
    seen = int(device.get("seen_cycles") or 0)
    changes = []
    for key, record in device["ports"].items():
        record.setdefault("last_seen_cycle", seen)
        if record.get("closed_at") is not None:
            continue
        if seen - record["last_seen_cycle"] <= PORT_QUIET_CYCLES:
            continue
        if scanned is not None and int(key) not in scanned:
            continue
        record["closed_at"] = now_iso
        changes.append({"kind": EVENT_PORT_CLOSED, "port": int(key)})
    return changes


def _set_name(device: dict[str, Any], value: str, source: str, now_iso: str) -> bool:
    value = value.strip()[:MAX_NAME_LENGTH]
    if not value:
        return False
    names = device["names"]
    for name in names:
        if name["source"] == source:
            if name["value"] == value:
                return False
            name["value"] = value
            name["ts"] = now_iso
            return True
    if len(names) >= MAX_NAMES_PER_DEVICE:
        return False
    names.append({"value": value, "source": source, "ts": now_iso})
    return True


def merge_cycle(
    state: dict[str, Any],
    hosts: list[dict[str, Any]],
    now: datetime,
    *,
    learning_hours: int = DEFAULT_LEARNING_HOURS,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    registry: Callable[[str], dict[str, str] | None] | None = None,
    new_id: Callable[[], str] = _new_device_id,
    port_list: list[int] | None = None,
    presence: bool = False,
    down_cycles: int = DEFAULT_DOWN_CYCLES,
    duplicate_flips: int = DEFAULT_DUPLICATE_FLIPS,
    gateway_ip: str | None = None,
) -> MergeOutcome:
    """Fold one netscan cycle into the inventory state, in place.

    ``hosts`` is the list ``probe.py`` already validated against
    NETSCAN_HOST_SCHEMA. ``registry`` maps a MAC to the Home Assistant device
    that carries it (``{"name", "device_id"}``) or None. ``port_list`` is the
    scan list the owner configured; without it every port counts as long scanned.

    ``presence`` says the cycle carries the Probe's presence signals. Only then is
    presence judged: a cycle from a Probe that cannot say who answered proves
    nothing about who is gone. A watched device with ``down_cycles`` consecutive
    judged cycles without an answer gets a ``device_down`` event, and a
    ``device_back`` event on its first answer after that.

    Change events carry ``alert: True`` only when the device was acknowledged at
    that moment, so acknowledging a device later does not raise its past changes.
    """
    outcome = MergeOutcome()
    now = dt_util.as_utc(now)
    now_iso = now.isoformat()
    meta = state["meta"]
    devices: dict[str, dict[str, Any]] = state["devices"]

    if meta.get("learning_started_at") is None:
        meta["learning_started_at"] = now_iso
    started = _parse(meta["learning_started_at"]) or now
    learning = now < started + timedelta(hours=learning_hours)

    certs: dict[str, Any] = state.setdefault("certs", {})
    scanned: set[int] | None = None
    scan_ports: dict[str, int] = {}
    if port_list is not None:
        scanned = {int(port) for port in port_list}
        previous_counts = meta.get("scan_ports") or {}
        scan_ports = {str(port): int(previous_counts.get(str(port), 0)) + 1 for port in scanned}
        meta["scan_ports"] = scan_ports

    def _settled(port: int) -> bool:
        return scanned is None or scan_ports.get(str(port), 0) > PORT_QUIET_CYCLES

    # device id -> the addresses and change events this cycle produced for it.
    observed: dict[str, dict[str, Any]] = {}

    by_mac: dict[str, str] = {}
    by_address: dict[str, str] = {}
    by_current_ip: dict[str, str] = {}
    for device in devices.values():
        for mac in device.get("macs") or []:
            by_mac[mac] = device["id"]
        current = device["addresses"][0]["ip"] if device.get("addresses") else None
        if current is None:
            continue
        if device.get("identity") == IDENTITY_ADDRESS:
            by_address[current] = device["id"]
        else:
            by_current_ip[current] = device["id"]

    def _create(identity: str, mac: str | None) -> dict[str, Any] | None:
        if not _make_room(state, now_iso):
            return None
        device = {
            "id": new_id(),
            "identity": identity,
            "macs": [mac] if mac else [],
            "mac_kind": mac_kind(mac) if mac else None,
            "addresses": [],
            "names": [],
            "label": None,
            "vendor": None,
            "first_seen": now_iso,
            "last_seen": now_iso,
            "verdict": VERDICT_UNACKNOWLEDGED,
            "watched": False,
            "sources": [],
            "ports": {},
            "baseline": learning,
            "ha_device_id": None,
            "seen_cycles": 0,
        }
        devices[device["id"]] = device
        outcome.created.append(device["id"])
        _append_event(state, now_iso, device["id"], "created", baseline=learning)
        return device

    pending: dict[str, str] = state["pending"]
    seen_without_mac: set[str] = set()

    for host in hosts:
        ip = host.get("ip")
        if not isinstance(ip, str) or not ip:
            continue
        mac = host.get("mac") or None
        open_ports = host.get("open_ports") or []
        device: dict[str, Any] | None = None

        if mac:
            pending.pop(ip, None)
            device_id = by_mac.get(mac)
            if device_id is not None:
                device = devices.get(device_id)
            elif ip in by_address:
                # The MAC arrived for a host first recorded by address: same record, stronger key.
                device = devices.get(by_address.pop(ip))
                if device is not None:
                    device["identity"] = IDENTITY_MAC
                    device["macs"] = [mac]
                    device["mac_kind"] = mac_kind(mac)
                    by_mac[mac] = device["id"]
                    _append_event(state, now_iso, device["id"], "rekeyed_to_mac")
            if device is None:
                device = _create(IDENTITY_MAC, mac)
                if device is None:
                    continue
                by_mac[mac] = device["id"]
        else:
            seen_without_mac.add(ip)
            device_id = by_address.get(ip) or by_current_ip.get(ip)
            if device_id is not None:
                device = devices.get(device_id)
            elif ip in pending:
                # Second consecutive cycle without a MAC: record it by address.
                del pending[ip]
                device = _create(IDENTITY_ADDRESS, None)
                if device is None:
                    continue
                by_address[ip] = device["id"]
            else:
                # The ARP table is read before the sweep, so a host that answered TCP
                # may simply not be resolved yet. Wait one cycle before recording it.
                pending[ip] = now_iso
                outcome.changed = True
                continue

        if device is None:
            continue
        device["last_seen"] = now_iso
        first_host = device["id"] not in observed
        if first_host:
            device["seen_cycles"] = int(device.get("seen_cycles") or 0) + 1
        seen_now = observed.setdefault(
            device["id"], {"ips": [], "changes": [], "present": False, "rtt_ms": None}
        )
        seen_now["ips"].append(ip)
        if host.get("arp_after_sweep") or host.get("responded") or open_ports:
            seen_now["present"] = True
        rtt = host.get("rtt_ms")
        if isinstance(rtt, (int, float)) and (seen_now["rtt_ms"] is None or rtt < seen_now["rtt_ms"]):
            seen_now["rtt_ms"] = float(rtt)
        if _set_address(state, device, ip, now_iso, secondary=not first_host):
            outcome.changed = True
        if host.get("network"):
            for address in device["addresses"]:
                if address["ip"] == ip and address.get("network") != host["network"]:
                    address["network"] = host["network"]
                    outcome.changed = True
        for source, present in ((SOURCE_PROBE_ARP, bool(mac)), (SOURCE_PROBE_TCP, bool(open_ports))):
            if present and source not in device["sources"]:
                device["sources"].append(source)
                outcome.changed = True
        if host.get("vendor") and device.get("vendor") is None and device.get("mac_kind") != "local":
            device["vendor"] = {"value": str(host["vendor"])[:64], "source": "probe_oui"}
            outcome.changed = True
        ports_changed, port_changes = _observe_ports(
            device, open_ports, now, now_iso, settled=_settled, certs=certs
        )
        seen_now["changes"].extend(port_changes)
        if ports_changed:
            outcome.changed = True
        if mac and _note_address_holder(state, ip, device["id"], now, now_iso, duplicate_flips):
            outcome.changed = True
        if mac and registry is not None:
            match = registry(mac)
            if match and match.get("name"):
                if _set_name(device, match["name"], SOURCE_HA_REGISTRY, now_iso):
                    outcome.changed = True
                if device.get("ha_device_id") != match.get("device_id"):
                    device["ha_device_id"] = match.get("device_id")
                    outcome.changed = True
                if SOURCE_HA_REGISTRY not in device["sources"]:
                    device["sources"].append(SOURCE_HA_REGISTRY)

    for device_id, seen_now in observed.items():
        device = devices.get(device_id)
        if device is None:
            continue
        changes: list[dict[str, Any]] = seen_now["changes"]
        changes.extend(_close_quiet_ports(device, now_iso, scanned))
        reasons: list[str] = []
        ips = sorted(set(seen_now["ips"]))
        if len(ips) > 1:
            # A device that always answers on two addresses is reported once: only
            # an address not seen alongside the others before counts.
            known = device.setdefault("simultaneous_addresses", [])
            fresh = [ip for ip in ips if ip not in known]
            if fresh:
                if int(device.get("seen_cycles") or 0) > PORT_QUIET_CYCLES:
                    reasons.append(SHIFT_TWO_ADDRESSES)
                known.extend(fresh)
                del known[:-MAX_SIMULTANEOUS_ADDRESSES]
                outcome.changed = True
        kinds = {change["kind"] for change in changes}
        if EVENT_CERT_CHANGED in kinds and kinds & {EVENT_PORT_OPENED, EVENT_PORT_CLOSED}:
            reasons.append(SHIFT_PORTS_AND_CERTIFICATE)
        acknowledged = device.get("verdict") == VERDICT_ACKNOWLEDGED
        for change in changes:
            detail = {k: v for k, v in change.items() if k != "kind"}
            # One identity shift stands in for the separate changes that make it up.
            alert = (
                acknowledged
                and not reasons
                and change["kind"] in (EVENT_PORT_OPENED, EVENT_CERT_CHANGED)
            )
            _append_event(state, now_iso, device_id, change["kind"], alert=alert, **detail)
        if reasons:
            _append_event(
                state, now_iso, device_id, EVENT_IDENTITY_SHIFT, alert=acknowledged, reasons=reasons
            )
        if changes or reasons:
            outcome.changed = True

    if presence and _judge_presence(state, observed, now, now_iso, down_cycles):
        outcome.changed = True
    _note_gateway(state, gateway_ip, observed, now, now_iso)

    # "Consecutive" means exactly that: an address that skipped this cycle starts over.
    for ip in [ip for ip in pending if ip not in seen_without_mac]:
        del pending[ip]

    cutoff = now - timedelta(days=retention_days)
    for device in [d for d in devices.values() if _prunable(d)]:
        last_seen = _parse(device.get("last_seen"))
        if last_seen is not None and last_seen < cutoff:
            del devices[device["id"]]
            _append_event(state, now_iso, device["id"], "pruned", reason="retention")
            outcome.changed = True

    meta["last_cycle_at"] = now_iso
    meta["cycles"] = int(meta.get("cycles") or 0) + 1
    if outcome.created:
        outcome.changed = True
    return outcome


def _note_address_holder(
    state: dict[str, Any], ip: str, device_id: str, now: datetime, now_iso: str, flips_needed: int
) -> bool:
    """Record which MAC-keyed device holds an address, and report two devices swapping it.

    One change of holder is a DHCP lease moving on. ``flips_needed`` changes inside
    ADDRESS_FLIP_WINDOW is two devices that both believe the address is theirs, or
    one device answering ARP for another's address. Returns True when it wrote the
    duplicate-address event, which happens once per window.
    """
    holders: dict[str, dict[str, Any]] = state["meta"].setdefault("address_holders", {})
    entry = holders.pop(ip, None)
    if entry is None:
        entry = {"device_id": device_id, "flips": []}
    raised = False
    if entry["device_id"] != device_id:
        previous = entry["device_id"]
        cutoff = (now - ADDRESS_FLIP_WINDOW).isoformat()
        entry["flips"] = [ts for ts in entry["flips"] if ts >= cutoff] + [now_iso]
        entry["device_id"] = device_id
        reported = entry.get("reported_at") or ""
        if len(entry["flips"]) >= flips_needed and reported < cutoff:
            entry["reported_at"] = now_iso
            _append_event(
                state,
                now_iso,
                device_id,
                EVENT_DUPLICATE_ADDRESS,
                alert=True,
                other_device_id=previous,
                flips=len(entry["flips"]),
            )
            raised = True
    # Re-inserted last, so the cap below drops the addresses not seen for longest.
    holders[ip] = entry
    while len(holders) > MAX_TRACKED_ADDRESSES:
        del holders[next(iter(holders))]
    return raised


def _note_gateway(
    state: dict[str, Any],
    gateway_ip: str | None,
    observed: dict[str, dict[str, Any]],
    now: datetime,
    now_iso: str,
) -> None:
    """Remember the Probe host's default next hop and keep that device's latency history."""
    meta = state["meta"]
    if gateway_ip is not None:
        try:
            meta["gateway_ip"] = str(ipaddress.IPv4Address(gateway_ip))
        except ValueError:
            return
    gateway = meta.get("gateway_ip")
    if not gateway:
        return
    for device_id, seen in observed.items():
        device = state["devices"].get(device_id)
        if device is None or gateway not in seen["ips"]:
            continue
        if meta.get("gateway_device_id") != device_id:
            # A different device at the gateway address starts a fresh baseline.
            meta["gateway_device_id"] = device_id
            device["rtt_history"] = []
        if seen["rtt_ms"] is not None:
            history = device.setdefault("rtt_history", [])
            history.append([now_iso, seen["rtt_ms"]])
            cutoff = (now - GATEWAY_BASELINE - GATEWAY_RECENT).isoformat()
            history[:] = [sample for sample in history if sample[0] >= cutoff][-MAX_RTT_SAMPLES:]
        return


def _judge_presence(
    state: dict[str, Any],
    observed: dict[str, dict[str, Any]],
    now: datetime,
    now_iso: str,
    down_cycles: int,
) -> bool:
    """Update presence for every device the Probe can see. Returns True on a real change.

    A cycle in which nothing at all answered is not judged: that is the Probe's
    host losing its network, not every device leaving at once. Devices only the
    controller reports are not judged either, because the Probe has no signal
    for them.
    """
    present_ids = {device_id for device_id, seen in observed.items() if seen["present"]}
    if not present_ids:
        state["meta"]["presence_skipped_at"] = now_iso
        return False
    changed = False
    cutoff = (now - timedelta(days=PRESENCE_RETENTION_DAYS)).isoformat()
    drop_cutoff = (now - DROP_WINDOW).isoformat()
    # Devices with a fixed MAC that answered last cycle, and how many of them did not now.
    # A randomized MAC is a phone, and a phone leaving is not a fault.
    were_present = 0
    dropped = 0
    for device in state["devices"].values():
        if not any(s in device.get("sources", []) for s in (SOURCE_PROBE_ARP, SOURCE_PROBE_TCP)):
            continue
        steady = device.get("mac_kind") != "local"
        if steady and device.get("missed_cycles") == 0:
            were_present += 1
            if device["id"] not in present_ids:
                dropped += 1
                drops = device.setdefault("drops", [])
                drops.append(now_iso)
                drops[:] = [ts for ts in drops if ts >= drop_cutoff][-MAX_DROPS_PER_DEVICE:]
        if device["id"] in present_ids:
            segments = device.setdefault("presence", [])
            last_end = _parse(segments[-1]["to"]) if segments else None
            if last_end is not None and now - last_end <= PRESENCE_JOIN:
                segments[-1]["to"] = now_iso
            else:
                segments.append({"from": now_iso, "to": now_iso})
                changed = True
            while segments and (segments[0]["to"] < cutoff or len(segments) > MAX_PRESENCE_SEGMENTS):
                del segments[0]
            device["missed_cycles"] = 0
            rtt = observed[device["id"]]["rtt_ms"]
            if rtt is not None:
                device["rtt_ms"] = rtt
            down_since = device.pop("down_since", None)
            if down_since:
                started = _parse(down_since)
                minutes = int((now - started).total_seconds() // 60) if started else None
                _append_event(
                    state,
                    now_iso,
                    device["id"],
                    EVENT_DEVICE_BACK,
                    alert=bool(device.get("watched")),
                    down_since=down_since,
                    minutes_away=minutes,
                )
                changed = True
        else:
            device["missed_cycles"] = int(device.get("missed_cycles") or 0) + 1
            if (
                device.get("watched")
                and not device.get("down_since")
                and device["missed_cycles"] >= down_cycles
            ):
                device["down_since"] = now_iso
                _append_event(state, now_iso, device["id"], EVENT_DEVICE_DOWN, alert=True)
                changed = True
    drop_cycles = state["meta"].setdefault("drop_cycles", [])
    drop_cycles.append({"at": now_iso, "dropped": dropped, "of": were_present})
    del drop_cycles[:-DROP_CYCLES_KEPT]
    return changed or dropped > 0


def drop_together(state: dict[str, Any], *, min_devices: int, percent: int) -> dict[str, Any] | None:
    """The worst recent cycle in which many devices stopped answering at once, or None."""
    worst = None
    for cycle in state["meta"].get("drop_cycles") or []:
        if cycle["dropped"] < min_devices or cycle["of"] <= 0:
            continue
        if cycle["dropped"] * 100 < percent * cycle["of"]:
            continue
        if worst is None or cycle["dropped"] > worst["dropped"]:
            worst = cycle
    return worst


def steady_restarts(state: dict[str, Any], now: datetime, *, drops_per_day: int) -> list[dict[str, Any]]:
    """Devices that stopped answering ``drops_per_day`` times in the last day, each
    drop between 2 minutes and 6 hours after the one before. Regularity beyond
    those bounds is not tested."""
    cutoff = dt_util.as_utc(now) - DROP_WINDOW
    rows = []
    for device in state["devices"].values():
        if device.get("verdict") == VERDICT_IGNORED or device.get("mac_kind") == "local":
            continue
        times = [t for t in (_parse(ts) for ts in device.get("drops") or []) if t and t >= cutoff]
        if len(times) < drops_per_day:
            continue
        gaps = [later - earlier for earlier, later in zip(times, times[1:])]
        if all(RESTART_GAP_MIN <= gap <= RESTART_GAP_MAX for gap in gaps):
            rows.append({"device_id": device["id"], "drops": len(times), "last_drop": times[-1].isoformat()})
    return rows


def slower_gateway(
    state: dict[str, Any], now: datetime, *, factor: int, min_ms: int
) -> dict[str, Any] | None:
    """The gateway's recent TCP connect time against its own last six hours, or None.

    Medians, because a connect time measured in a busy event loop has outliers.
    """
    device = state["devices"].get(state["meta"].get("gateway_device_id") or "")
    if device is None:
        return None
    now = dt_util.as_utc(now)
    recent_from = (now - GATEWAY_RECENT).isoformat()
    baseline_from = (now - GATEWAY_RECENT - GATEWAY_BASELINE).isoformat()
    recent = [ms for ts, ms in device.get("rtt_history") or [] if ts >= recent_from]
    baseline = [ms for ts, ms in device.get("rtt_history") or [] if baseline_from <= ts < recent_from]
    if len(recent) < 2 or len(baseline) < GATEWAY_BASELINE_MIN_SAMPLES:
        return None
    recent_ms, baseline_ms = statistics.median(recent), statistics.median(baseline)
    if recent_ms >= factor * baseline_ms and recent_ms - baseline_ms >= min_ms:
        return {
            "device_id": device["id"],
            "recent_ms": round(recent_ms, 1),
            "baseline_ms": round(baseline_ms, 1),
        }
    return None


def merge_unifi_clients(
    state: dict[str, Any],
    clients: list[dict[str, Any]],
    now: datetime,
    *,
    learning_hours: int = DEFAULT_LEARNING_HOURS,
    new_id: Callable[[], str] = _new_device_id,
) -> MergeOutcome:
    """Fold the UniFi controller's client list into the inventory, in place.

    ``clients`` is unifi.py's normalized shape. A client with a MAC the inventory
    does not hold becomes a record, so a device the controller sees and the Probe
    cannot reach is still listed. For a device the Probe also sees, the controller
    adds a name, the VLAN and SSID, and a later last-seen time, and nothing else:
    the Probe's address stays the current one and ports are never touched.

    The controller is trusted as far as the Probe is. A client name is set on the
    device or in the controller, so it is length-bounded and only ever displayed.
    """
    outcome = MergeOutcome()
    now = dt_util.as_utc(now)
    now_iso = now.isoformat()
    meta = state["meta"]
    devices: dict[str, dict[str, Any]] = state["devices"]
    if meta.get("learning_started_at") is None:
        meta["learning_started_at"] = now_iso
    started = _parse(meta["learning_started_at"]) or now
    learning = now < started + timedelta(hours=learning_hours)

    by_mac: dict[str, str] = {}
    by_address: dict[str, str] = {}
    for device in devices.values():
        for mac in device.get("macs") or []:
            by_mac[mac] = device["id"]
        if device.get("identity") == IDENTITY_ADDRESS and device.get("addresses"):
            by_address[device["addresses"][0]["ip"]] = device["id"]

    for client in clients:
        mac = str(client.get("mac") or "").lower()
        if not _MAC_RE.match(mac):
            continue
        ip = client.get("ipv4") if isinstance(client.get("ipv4"), str) else None
        device = devices.get(by_mac.get(mac, ""))
        if device is None and ip and ip in by_address:
            # The controller supplies the MAC for a host the Probe could only key by address.
            device = devices.get(by_address.pop(ip))
            if device is not None:
                device["identity"] = IDENTITY_MAC
                device["macs"] = [mac]
                device["mac_kind"] = mac_kind(mac)
                _append_event(state, now_iso, device["id"], "rekeyed_to_mac", source=SOURCE_UNIFI)
                outcome.changed = True
        if device is None:
            if not _make_room(state, now_iso):
                continue
            device = {
                "id": new_id(),
                "identity": IDENTITY_MAC,
                "macs": [mac],
                "mac_kind": mac_kind(mac),
                "addresses": [],
                "names": [],
                "label": None,
                "vendor": None,
                "first_seen": now_iso,
                "last_seen": now_iso,
                "verdict": VERDICT_UNACKNOWLEDGED,
                "watched": False,
                "sources": [],
                "ports": {},
                "baseline": learning,
                "ha_device_id": None,
                "seen_cycles": 0,
            }
            devices[device["id"]] = device
            outcome.created.append(device["id"])
            _append_event(state, now_iso, device["id"], "created", baseline=learning, source=SOURCE_UNIFI)
        by_mac[mac] = device["id"]

        if SOURCE_UNIFI not in device["sources"]:
            device["sources"].append(SOURCE_UNIFI)
            outcome.changed = True
        probed = any(source in device["sources"] for source in (SOURCE_PROBE_ARP, SOURCE_PROBE_TCP))
        if ip and not probed and _set_address(state, device, ip, now_iso):
            outcome.changed = True
        name = client.get("name")
        if isinstance(name, str) and name.lower() not in (mac, "unknown"):
            if _set_name(device, name, SOURCE_UNIFI, now_iso):
                outcome.changed = True
        seen = client.get("last_seen")
        seen_at = now
        if isinstance(seen, (int, float)) and seen > 0:
            seen_at = min(now, dt_util.utc_from_timestamp(seen))
        if seen_at > (_parse(device.get("last_seen")) or seen_at - timedelta(seconds=1)):
            device["last_seen"] = seen_at.isoformat()
        network = {
            "vlan": client.get("vlan") if isinstance(client.get("vlan"), (int, str)) else None,
            "ssid": str(client["ssid"])[:64] if client.get("ssid") else None,
            "wired": bool(client.get("wired")),
        }
        if device.get("unifi") != network:
            device["unifi"] = network
            outcome.changed = True

    if outcome.created:
        outcome.changed = True
    return outcome


def _open_ports(device: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {
        int(key): record
        for key, record in (device.get("ports") or {}).items()
        if record.get("closed_at") is None
    }


def cleartext_exposures(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Open cleartext management services, one row per device and port.

    Ignored devices are left out: ignoring a device is the owner saying it is not
    theirs to fix. Plain HTTP beside HTTPS is reported as ``service: "http"`` with
    severity "info"; every other row takes its severity from CLEARTEXT_SERVICES.
    """
    rows: list[dict[str, Any]] = []
    for device in state["devices"].values():
        if device.get("verdict") == VERDICT_IGNORED:
            continue
        ports = _open_ports(device)
        for port, record in ports.items():
            guess = record.get("service")
            if guess in CLEARTEXT_SERVICES:
                service, basis = guess, BASIS_BANNER
            elif port in _CLEARTEXT_BY_PORT and guess in (None, "tls") and not record.get("cert_sha256"):
                service, basis = _CLEARTEXT_BY_PORT[port], BASIS_PORT
            else:
                continue
            rows.append(
                {
                    "device_id": device["id"],
                    "port": port,
                    "service": service,
                    "basis": basis,
                    "severity": CLEARTEXT_SERVICES[service]["severity"],
                }
            )
        if any(port in ports for port in HTTPS_PORTS):
            for port in HTTP_PORTS:
                record = ports.get(port)
                if record is not None and not record.get("cert_sha256"):
                    basis = BASIS_BANNER if record.get("service") == "http" else BASIS_PORT
                    rows.append(
                        {
                            "device_id": device["id"],
                            "port": port,
                            "service": "http",
                            "basis": basis,
                            "severity": "info",
                        }
                    )
    return rows


def certificate_expiries(state: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    """Certificates on open ports that have expired or expire within 30 days.

    A certificate that could not be parsed has no expiry to judge and is left out.
    """
    now = dt_util.as_utc(now)
    certs = state.get("certs") or {}
    rows: list[dict[str, Any]] = []
    for device in state["devices"].values():
        if device.get("verdict") == VERDICT_IGNORED:
            continue
        for port, record in _open_ports(device).items():
            cert = certs.get(record.get("cert_sha256") or "")
            expiry = _parse(cert.get("not_after")) if cert else None
            if expiry is None:
                continue
            days_left = (expiry - now).days
            if expiry <= now:
                severity = "medium"
            elif days_left <= CERT_EXPIRY_LOW_DAYS:
                severity = "low"
            elif days_left <= CERT_EXPIRY_INFO_DAYS:
                severity = "info"
            else:
                continue
            rows.append(
                {
                    "device_id": device["id"],
                    "port": port,
                    "not_after": cert["not_after"],
                    "days_left": days_left,
                    "expired": expiry <= now,
                    "severity": severity,
                }
            )
    return rows


def normalize_mac(value: Any) -> str | None:
    """A MAC in any common spelling as lowercase with colons, or None."""
    digits = re.sub(r"[^0-9a-fA-F]", "", str(value or ""))
    if len(digits) != 12:
        return None
    digits = digits.lower()
    return ":".join(digits[i : i + 2] for i in range(0, 12, 2))


def apply_names(state: dict[str, Any], names: list[dict[str, Any]], now: datetime) -> bool:
    """Add names other parts of Home Assistant already hold, and certificate names.

    ``names`` is a list of ``{"mac", "name", "source"}`` with the source one of
    PASSIVE_NAME_SOURCES. A name is only ever attached to a device the inventory
    already holds by that MAC: these sources name devices, they do not discover
    them. A name the device announced is attacker-chosen text, so it is
    length-bounded, shown with its source, and ranks below the owner's label, the
    registry and the controller. Returns True when anything changed.
    """
    now_iso = dt_util.as_utc(now).isoformat()
    devices: dict[str, dict[str, Any]] = state["devices"]
    by_mac = {mac: device for device in devices.values() for mac in device.get("macs") or []}
    changed = False
    for entry in names:
        if entry.get("source") not in PASSIVE_NAME_SOURCES:
            continue
        mac = normalize_mac(entry.get("mac"))
        device = by_mac.get(mac or "")
        name = entry.get("name")
        if device is None or not isinstance(name, str):
            continue
        if _set_name(device, name, entry["source"], now_iso):
            changed = True

    certs = state.get("certs") or {}
    for device in devices.values():
        subject = None
        for key in sorted(device.get("ports") or {}, key=int):
            record = device["ports"][key]
            cert = certs.get(record.get("cert_sha256") or "")
            if record.get("closed_at") is None and cert and cert.get("subject"):
                subject = cert["subject"]
                break
        match = _CERT_CN_RE.search(subject) if subject else None
        if match and _set_name(device, match.group(1), SOURCE_CERT, now_iso):
            changed = True
    return changed


def best_name(device: dict[str, Any]) -> dict[str, str] | None:
    """The name to show and where it came from. The owner's label always wins."""
    if device.get("label"):
        return {"value": device["label"], "source": "label"}
    names = device.get("names") or []
    for source in NAME_PRECEDENCE:
        for name in names:
            if name["source"] == source:
                return {"value": name["value"], "source": source}
    return {"value": names[0]["value"], "source": names[0]["source"]} if names else None


class NetworkInventory:
    """Owns the inventory Store file and applies cycles and owner actions to it."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = HaSocStore(
            hass,
            INVENTORY_STORAGE_VERSION,
            INVENTORY_STORAGE_KEY,
            private=True,
            atomic_writes=True,
        )
        self.state: dict[str, Any] = empty_state()
        self._dirty = False
        # The owner's current try-before-add sweep. In memory only: its hosts are
        # not inventory until the network is added and a regular cycle reports them.
        self.trial: dict[str, Any] | None = None

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        state = empty_state()
        for key in ("devices", "pending", "certs"):
            if isinstance(stored.get(key), dict):
                state[key] = stored[key]
        if isinstance(stored.get("events"), list):
            state["events"] = stored["events"][-MAX_EVENTS:]
        if isinstance(stored.get("meta"), dict):
            state["meta"].update(stored["meta"])
        self.state = state

    def _payload(self) -> dict[str, Any]:
        self._dirty = False
        return self.state

    def _schedule_save(self) -> None:
        self._dirty = True
        self._store.async_delay_save(self._payload, INVENTORY_SAVE_DELAY)

    async def async_flush(self) -> None:
        """Write now if anything changed. Called when the entry stops; never raises."""
        if not self._dirty:
            return
        try:
            await self._store.async_save(self._payload())
        except Exception:  # noqa: BLE001 - teardown must finish
            self._dirty = True
            _LOGGER.exception("HA SOC could not write the network inventory file")

    def _registry_lookup(self, mac: str) -> dict[str, str] | None:
        registry = dr.async_get(self.hass)
        matches = registry.async_get_devices(connections={(dr.CONNECTION_NETWORK_MAC, mac)})
        for entry in matches:
            name = entry.name_by_user or entry.name
            if name:
                return {"name": name, "device_id": entry.id}
        return None

    @callback
    def async_merge_cycle(
        self,
        hosts: list[dict[str, Any]],
        *,
        learning_hours: int = DEFAULT_LEARNING_HOURS,
        now: datetime | None = None,
        port_list: list[int] | None = None,
        presence: bool = False,
        down_cycles: int = DEFAULT_DOWN_CYCLES,
        duplicate_flips: int = DEFAULT_DUPLICATE_FLIPS,
        gateway_ip: str | None = None,
    ) -> MergeOutcome:
        host_roles = self._host_roles()
        meta = self.state["meta"]
        if host_roles is not None:
            meta["dns_servers"] = host_roles["dns"]
        if gateway_ip:
            meta["roles_source"] = "probe"
        elif host_roles is not None and host_roles["gateway"]:
            # The Probe's own read of the route table wins; this covers a Probe too old to send it.
            gateway_ip = host_roles["gateway"]
            meta["roles_source"] = "supervisor"
        outcome = merge_cycle(
            self.state,
            hosts,
            now or dt_util.utcnow(),
            learning_hours=learning_hours,
            registry=self._registry_lookup,
            port_list=port_list,
            presence=presence,
            down_cycles=down_cycles,
            duplicate_flips=duplicate_flips,
            gateway_ip=gateway_ip,
        )
        if apply_names(self.state, self._passive_names(), now or dt_util.utcnow()):
            outcome.changed = True
        # last_seen, the cycle counter and last_cycle_at change every cycle. They are
        # written on stop and with the next real change, not once per cycle, so after
        # a crash they can be as old as the last real change.
        self._dirty = True
        if outcome.changed:
            self._schedule_save()
        return outcome

    @callback
    def async_merge_unifi_clients(
        self,
        clients: list[dict[str, Any]],
        *,
        learning_hours: int = DEFAULT_LEARNING_HOURS,
        now: datetime | None = None,
    ) -> MergeOutcome:
        outcome = merge_unifi_clients(
            self.state, clients, now or dt_util.utcnow(), learning_hours=learning_hours
        )
        self._dirty = True
        if outcome.changed:
            self._schedule_save()
        return outcome

    @callback
    def async_request_trial(self, network: str) -> dict[str, Any]:
        """Ask the Probe for one sweep of ``network``. Replaces any earlier trial."""
        self.trial = {
            "id": _secrets.token_hex(8),
            "network": network,
            "requested_at": dt_util.utcnow().isoformat(),
            "completed_at": None,
            "refused": None,
            "hosts": None,
        }
        return self.trial

    def pending_trial(self) -> dict[str, str] | None:
        """What the netscan poll response offers the Probe, or None."""
        trial = self.trial
        if trial is None or trial["completed_at"] is not None:
            return None
        requested = _parse(trial["requested_at"])
        if requested is None or dt_util.utcnow() - requested > TRIAL_PENDING:
            return None
        return {"id": trial["id"], "network": trial["network"]}

    @callback
    def async_trial_result(self, report: dict[str, Any]) -> bool:
        """Record the Probe's answer. False when it is not for the current trial."""
        trial = self.trial
        if trial is None or report.get("id") != trial["id"] or trial["completed_at"] is not None:
            return False
        trial["completed_at"] = dt_util.utcnow().isoformat()
        trial["refused"] = report.get("refused")
        hosts = report.get("hosts") or []
        trial["host_count"] = len(hosts)
        trial["hosts"] = [
            {
                "ip": host.get("ip"),
                "open_ports": [p.get("port") for p in host.get("open_ports") or []],
            }
            for host in hosts[:MAX_TRIAL_HOSTS]
        ]
        return True

    def trial_passed(self, network: str) -> bool:
        """True when the current trial swept exactly this network and was not refused."""
        trial = self.trial
        return bool(
            trial
            and trial["network"] == network
            and trial["completed_at"] is not None
            and not trial["refused"]
        )

    def _passive_names(self) -> list[dict[str, Any]]:
        """Names Home Assistant already holds: DHCP hostnames and router trackers.

        Nothing is sent or listened for here. Core's dhcp integration watches DHCP
        traffic for discovery and keeps what it saw; router integrations expose the
        hostname their router reports as a tracker attribute.
        """
        names: list[dict[str, Any]] = []
        if "dhcp" in self.hass.config.components:
            try:
                from homeassistant.components.dhcp import async_discovered_service_info

                for info in async_discovered_service_info(self.hass):
                    names.append({"mac": info.macaddress, "name": info.hostname, "source": SOURCE_DHCP})
            except Exception:  # noqa: BLE001 - a name source must never break a cycle
                _LOGGER.debug("HA SOC could not read DHCP discovery names", exc_info=True)
        for tracker in self.hass.states.async_all("device_tracker"):
            attributes = tracker.attributes
            if attributes.get("source_type") != "router":
                continue
            if attributes.get("mac") and attributes.get("host_name"):
                names.append(
                    {
                        "mac": attributes["mac"],
                        "name": str(attributes["host_name"]),
                        "source": SOURCE_TRACKER,
                    }
                )
        return names

    def _host_roles(self) -> dict[str, Any] | None:
        """Gateway and DNS servers from the Supervisor's cached network information.

        None when there is no Supervisor or it has not reported yet. No I/O: core's
        hassio integration keeps the data and this only reads it.
        """
        if "hassio" not in self.hass.config.components:
            return None
        try:
            from homeassistant.components.hassio import get_network_info

            return host_network_roles(get_network_info(self.hass))
        except Exception:  # noqa: BLE001 - not ready, or an older core without the helper
            return None

    @callback
    def async_note_wan_address(self, address: Any) -> None:
        """Record what kind of address the UniFi gateway's WAN side holds."""
        kind = classify_wan_address(address)
        if kind is None:
            return
        previous = (self.state["meta"].get("wan") or {}).get("kind")
        self.state["meta"]["wan"] = {"kind": kind, "at": dt_util.utcnow().isoformat()}
        self._dirty = True
        if previous != kind:
            self._schedule_save()

    def _roles(self, device: dict[str, Any]) -> list[str]:
        meta = self.state["meta"]
        roles = []
        if device["id"] == meta.get("gateway_device_id"):
            roles.append(ROLE_GATEWAY)
        current = device["addresses"][0]["ip"] if device.get("addresses") else None
        if current is not None and current in (meta.get("dns_servers") or []):
            roles.append(ROLE_DNS)
        return roles

    def known_cert_fingerprints(self) -> list[str]:
        """The fingerprints the Probe need not send DER for, most recently seen first."""
        certs = self.state["certs"]
        ordered = sorted(certs, key=lambda sha: certs[sha].get("last_seen") or "", reverse=True)
        return ordered[:MAX_KNOWN_CERTS]

    async def async_absorb_certificates(
        self, hosts: list[dict[str, Any]], *, now: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Parse the certificates one cycle delivered and return the hosts without DER.

        Each TLS entry that names a fingerprint comes back with the subject, issuer,
        expiry and self-signed flag of that certificate when it is held, so the stored
        netscan result and the inventory read the same parsed fields. A certificate
        whose bytes do not hash to the fingerprint the Probe named is dropped.
        """
        certs: dict[str, Any] = self.state["certs"]
        now_iso = dt_util.as_utc(now or dt_util.utcnow()).isoformat()
        wanted: dict[str, str] = {}
        for host in hosts:
            for entry in host.get("open_ports") or []:
                tls = entry.get("tls")
                if not isinstance(tls, dict) or not tls.get("der") or not tls.get("sha256"):
                    continue
                if tls["sha256"] in certs or tls["sha256"] in wanted:
                    continue
                if len(wanted) < NETSCAN_MAX_DER_PER_RESULT:
                    wanted[tls["sha256"]] = tls["der"]
        if wanted:
            parsed = await self.hass.async_add_executor_job(parse_certificates, list(wanted.values()))
            for cert in parsed:
                if cert["sha256"] in wanted:
                    certs[cert["sha256"]] = {**cert, "first_seen": now_iso, "last_seen": now_iso}
            self._schedule_save()

        out: list[dict[str, Any]] = []
        for host in hosts:
            copy = dict(host)
            if host.get("open_ports") is not None:
                ports = []
                for entry in host["open_ports"]:
                    tls = entry.get("tls")
                    if isinstance(tls, dict) and tls.get("sha256"):
                        held = certs.get(tls["sha256"]) or {}
                        if held:
                            held["last_seen"] = now_iso
                        entry = {
                            **entry,
                            "tls": {
                                "sha256": tls["sha256"],
                                "subject": held.get("subject"),
                                "issuer": held.get("issuer"),
                                "not_after": held.get("not_after"),
                                "self_signed": held.get("self_signed"),
                            },
                        }
                    elif isinstance(tls, dict) and "der" in tls:
                        entry = {**entry, "tls": {k: v for k, v in tls.items() if k != "der"}}
                    ports.append(entry)
                copy["open_ports"] = ports
            out.append(copy)

        if len(certs) > MAX_CERTS:
            oldest = sorted(certs, key=lambda sha: certs[sha].get("last_seen") or "")
            for sha in oldest[: len(certs) - MAX_CERTS]:
                del certs[sha]
        return out

    def _recent_changes(self) -> dict[str, list[dict[str, Any]]]:
        """device id -> its newest change events, for the owner's device list."""
        cutoff = (dt_util.utcnow() - timedelta(days=RECENT_CHANGE_DAYS)).isoformat()
        recent: dict[str, list[dict[str, Any]]] = {}
        for event in reversed(self.state["events"]):
            kinds = CHANGE_EVENT_KINDS + PRESENCE_EVENT_KINDS
            if event.get("kind") not in kinds or (event.get("ts") or "") < cutoff:
                continue
            bucket = recent.setdefault(event["device_id"], [])
            if len(bucket) < RECENT_CHANGES_PER_DEVICE:
                bucket.append(event)
        return recent

    def overview(self) -> dict[str, Any]:
        """The owner-facing view: every record with its display name, plus counts."""
        devices = []
        counts = {verdict: 0 for verdict in VERDICTS}
        recent = self._recent_changes()
        presence_cutoff = (
            dt_util.utcnow() - timedelta(hours=PRESENCE_OVERVIEW_HOURS)
        ).isoformat()
        certs = self.state["certs"]
        referenced: dict[str, Any] = {}
        for device in self.state["devices"].values():
            counts[device.get("verdict", VERDICT_UNACKNOWLEDGED)] += 1
            for record in device.get("ports", {}).values():
                fingerprint = record.get("cert_sha256")
                if fingerprint in certs:
                    referenced[fingerprint] = certs[fingerprint]
            devices.append(
                {
                    **device,
                    "display_name": best_name(device),
                    "roles": self._roles(device),
                    "recent_changes": recent.get(device["id"], []),
                    # The last day only; the file keeps PRESENCE_RETENTION_DAYS.
                    "presence": [
                        segment
                        for segment in device.get("presence", [])
                        if segment["to"] >= presence_cutoff
                    ],
                }
            )
        meta = self.state["meta"]
        return {
            "devices": devices,
            "certs": referenced,
            "network": {
                "gateway_ip": meta.get("gateway_ip"),
                "dns_servers": list(meta.get("dns_servers") or []),
                "roles_source": meta.get("roles_source"),
                "wan": meta.get("wan"),
            },
            "counts": counts,
            "learning_started_at": meta.get("learning_started_at"),
            "last_cycle_at": meta.get("last_cycle_at"),
            "cycles": meta.get("cycles", 0),
            "cap": MAX_DEVICES,
            "cap_reached_at": meta.get("cap_reached_at"),
        }

    @callback
    def async_set_verdict(
        self, device_id: str, verdict: str, *, by_user_id: str | None, at: str
    ) -> dict[str, Any] | None:
        """Record the owner's verdict. Returns the record, or None when it does not exist."""
        device = self.state["devices"].get(device_id)
        if device is None or verdict not in VERDICTS:
            return None
        previous = device.get("verdict")
        device["verdict"] = verdict
        device["verdict_by"] = by_user_id
        device["verdict_at"] = at
        _append_event(self.state, at, device_id, "verdict", previous=previous, verdict=verdict)
        self._schedule_save()
        return device

    @callback
    def async_set_watch(self, device_id: str, watched: bool, *, at: str) -> dict[str, Any] | None:
        """Turn gone-and-back alerts for a device on or off. None when it does not exist."""
        device = self.state["devices"].get(device_id)
        if device is None:
            return None
        device["watched"] = bool(watched)
        if not watched:
            device.pop("down_since", None)
        _append_event(self.state, at, device_id, "watch", watched=bool(watched))
        self._schedule_save()
        return device

    @callback
    def async_set_label(self, device_id: str, label: str | None, *, at: str) -> dict[str, Any] | None:
        device = self.state["devices"].get(device_id)
        if device is None:
            return None
        cleaned = (label or "").strip()[:MAX_LABEL_LENGTH] or None
        device["label"] = cleaned
        _append_event(self.state, at, device_id, "label", set=cleaned is not None)
        self._schedule_save()
        return device
