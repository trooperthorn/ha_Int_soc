"""Persistent network device inventory built from the Probe's netscan cycles.

Design, identity rules, bounds and the threat model live in
docs/NETWORK-INVENTORY-DESIGN.md. This module is phase 1 of that design: the
device record, the observation merge, and the owner's verdict and label.

The merge (`merge_cycle`) is a pure function of the previous state, one cycle's
hosts and the clock, so recorded cycle sequences can be replayed in tests. The
manager (`NetworkInventory`) adds the Store file and the Home Assistant device
registry lookup.
"""
from __future__ import annotations

import logging
import secrets as _secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
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
        },
        "devices": {},
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


def _set_address(state: dict[str, Any], device: dict[str, Any], ip: str, now_iso: str) -> bool:
    addresses = device["addresses"]
    if addresses and addresses[0]["ip"] == ip:
        return False
    previous = addresses[0]["ip"] if addresses else None
    addresses[:] = [a for a in addresses if a["ip"] != ip]
    addresses.insert(0, {"ip": ip, "since": now_iso})
    del addresses[MAX_ADDRESSES_PER_DEVICE:]
    if previous is not None:
        _append_event(state, now_iso, device["id"], "address_changed", previous=previous, ip=ip)
    return True


def _set_ports(device: dict[str, Any], open_ports: Any, now: datetime, now_iso: str) -> bool:
    changed = False
    ports = device["ports"]
    for entry in open_ports or []:
        if not isinstance(entry, dict) or "port" not in entry:
            continue
        key = str(entry["port"])
        record = ports.get(key)
        if record is None:
            if len(ports) >= MAX_PORTS_PER_DEVICE:
                continue
            record = ports[key] = {"first_seen": now_iso}
            changed = True
        record["last_seen"] = now_iso
        record["service"] = entry.get("service_guess")
        record["confidence"] = entry.get("service_confidence")
    cutoff = now - timedelta(days=PORT_RETENTION_DAYS)
    for key in [k for k, r in ports.items() if (_parse(r.get("last_seen")) or now) < cutoff]:
        del ports[key]
        changed = True
    return changed


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
) -> MergeOutcome:
    """Fold one netscan cycle into the inventory state, in place.

    ``hosts`` is the list ``probe.py`` already validated against
    NETSCAN_HOST_SCHEMA. ``registry`` maps a MAC to the Home Assistant device
    that carries it (``{"name", "device_id"}``) or None.
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
        if _set_address(state, device, ip, now_iso):
            outcome.changed = True
        for source, present in ((SOURCE_PROBE_ARP, bool(mac)), (SOURCE_PROBE_TCP, bool(open_ports))):
            if present and source not in device["sources"]:
                device["sources"].append(source)
                outcome.changed = True
        if host.get("vendor") and device.get("vendor") is None and device.get("mac_kind") != "local":
            device["vendor"] = {"value": str(host["vendor"])[:64], "source": "probe_oui"}
            outcome.changed = True
        if _set_ports(device, open_ports, now, now_iso):
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


def best_name(device: dict[str, Any]) -> dict[str, str] | None:
    """The name to show and where it came from. The owner's label always wins."""
    if device.get("label"):
        return {"value": device["label"], "source": "label"}
    names = device.get("names") or []
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

    async def async_load(self) -> None:
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        state = empty_state()
        for key in ("devices", "pending"):
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
    ) -> MergeOutcome:
        outcome = merge_cycle(
            self.state,
            hosts,
            now or dt_util.utcnow(),
            learning_hours=learning_hours,
            registry=self._registry_lookup,
        )
        # last_seen, the cycle counter and last_cycle_at change every cycle. They are
        # written on stop and with the next real change, not once per cycle, so after
        # a crash they can be as old as the last real change.
        self._dirty = True
        if outcome.changed:
            self._schedule_save()
        return outcome

    def overview(self) -> dict[str, Any]:
        """The owner-facing view: every record with its display name, plus counts."""
        devices = []
        counts = {verdict: 0 for verdict in VERDICTS}
        for device in self.state["devices"].values():
            counts[device.get("verdict", VERDICT_UNACKNOWLEDGED)] += 1
            devices.append({**device, "display_name": best_name(device)})
        meta = self.state["meta"]
        return {
            "devices": devices,
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
    def async_set_label(self, device_id: str, label: str | None, *, at: str) -> dict[str, Any] | None:
        device = self.state["devices"].get(device_id)
        if device is None:
            return None
        cleaned = (label or "").strip()[:MAX_LABEL_LENGTH] or None
        device["label"] = cleaned
        _append_event(self.state, at, device_id, "label", set=cleaned is not None)
        self._schedule_save()
        return device
