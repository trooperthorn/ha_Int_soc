"""Security Integrations Health — always-on dashboard visibility into the
entities and integrations a security-conscious install cares most about.

Two independent sources, each toggleable via Settings
(``security_sources_enabled``, see const.py's SECURITY_INTEGRATION_DOMAINS/
SECURITY_ENTITY_DOMAINS for the known set):

- **Entity domains** (``lock``, ``siren``, ``valve``) — every entity in
  these domains, regardless of which integration owns it. These are the
  entity types where "is it actually working" is a physical-security
  question, not just a convenience one.
- **Integration domains** — a curated allowlist
  (kidde_homesafe/elkm1/emporia_vue/unifiprotect/keymaster) reported the
  same honest three-way way probe.py/peripherals.py already establish for
  this project: not installed / installed-and-state, never silently
  omitted just because a domain isn't present on this install.

Battery level uses the same convention Home Assistant's own frontend uses
for a device's battery icon (device_page.ts's ``findBatteryEntity``) —
sibling entity on the same device_id, domain ``sensor`` preferred over
``binary_sensor``, device_class ``battery`` — not a per-integration
convention this project invented. A lock/siren/valve with no such sibling
just reports no battery data; that's not itself a problem worth flagging.

"Problem" state is deliberately narrow and domain-agnostic:
``unavailable``/``unknown`` (generic to every entity) plus lock's real
``jammed`` state. Anything else (a valve simply being closed, a lock
simply being unlocked) is normal operational state, not a health issue —
this module has no way to know whether "unlocked" is expected or alarming
for a given install, and doesn't guess.
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import SECURITY_ENTITY_DOMAINS, SECURITY_INTEGRATION_DOMAINS
from .store import HaSocData

LOW_BATTERY_THRESHOLD = 20
_PROBLEM_STATES = {"unavailable", "unknown", "jammed"}


def _find_battery_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Mirrors HA's own frontend battery-icon lookup: a sibling entity on
    the same device_id, sensor domain preferred, binary_sensor fallback,
    device_class battery — not a convention this project invented."""
    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    if entry is None or entry.device_id is None:
        return None

    fallback: str | None = None
    for sibling in er.async_entries_for_device(ent_reg, entry.device_id):
        device_class = sibling.device_class or sibling.original_device_class
        if device_class != "battery":
            continue
        if sibling.domain == "sensor":
            return sibling.entity_id
        if sibling.domain == "binary_sensor" and fallback is None:
            fallback = sibling.entity_id
    return fallback


def _entity_row(hass: HomeAssistant, entity_id: str) -> dict[str, Any] | None:
    state = hass.states.get(entity_id)
    if state is None:
        return None

    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)

    battery_entity_id = _find_battery_entity_id(hass, entity_id)
    battery_level: float | None = None
    if battery_entity_id is not None:
        battery_state = hass.states.get(battery_entity_id)
        if battery_state is not None:
            try:
                battery_level = float(battery_state.state)
            except (TypeError, ValueError):
                battery_level = None

    return {
        "entity_id": entity_id,
        "name": state.name,
        "domain": entity_id.split(".", 1)[0],
        "state": state.state,
        "device_class": state.attributes.get("device_class"),
        "problem": state.state in _PROBLEM_STATES,
        "battery_entity_id": battery_entity_id,
        "battery_level": battery_level,
        "low_battery": battery_level is not None and battery_level <= LOW_BATTERY_THRESHOLD,
        "config_entry_id": entry.config_entry_id if entry is not None else None,
        "platform": entry.platform if entry is not None else None,
    }


async def async_security_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the always-present Dashboard security card needs."""
    enabled = store.settings.get("security_sources_enabled") or {}

    entities: list[dict[str, Any]] = []
    for domain in SECURITY_ENTITY_DOMAINS:
        if not enabled.get(domain, True):
            continue
        for entity_id in hass.states.async_entity_ids(domain):
            row = _entity_row(hass, entity_id)
            if row is not None:
                entities.append(row)
    entities.sort(key=lambda e: e["entity_id"])

    integrations: list[dict[str, Any]] = []
    for domain in SECURITY_INTEGRATION_DOMAINS:
        if not enabled.get(domain, True):
            continue
        entries = hass.config_entries.async_entries(domain)
        if not entries:
            integrations.append(
                {"entry_id": None, "domain": domain, "title": None, "state": None, "installed": False}
            )
            continue
        for entry in entries:
            integrations.append(
                {
                    "entry_id": entry.entry_id,
                    "domain": entry.domain,
                    "title": entry.title,
                    "state": entry.state.value,
                    "installed": True,
                }
            )

    return {
        "entities": entities,
        "integrations": integrations,
        "problem_count": sum(1 for e in entities if e["problem"]),
        "low_battery_count": sum(1 for e in entities if e["low_battery"]),
        "sources_enabled": enabled,
    }
