"""Security Integrations Health: dashboard visibility into the entities and
integrations a security-conscious install cares most about.

Two sources, each toggleable via the ``security_sources_enabled`` setting:
entity domains (lock, siren, valve) and a curated integration allowlist.
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
    """Mirrors HA's frontend battery-icon lookup: a battery device_class
    sibling on the same device, sensor preferred over binary_sensor."""
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


def _no_state_row(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """The row for a registry entity with no state object: its integration
    never loaded it."""
    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    return {
        "entity_id": entity_id,
        "name": (entry.name or entry.original_name) if entry is not None else None,
        "domain": entity_id.split(".", 1)[0],
        "state": None,
        "device_class": None,
        "problem": True,
        "reason": "no state (integration not loaded)",
        "battery_entity_id": None,
        "battery_level": None,
        "low_battery": False,
        "config_entry_id": entry.config_entry_id if entry is not None else None,
        "platform": entry.platform if entry is not None else None,
    }


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
        "reason": state.state if state.state in _PROBLEM_STATES else None,
        "battery_entity_id": battery_entity_id,
        "battery_level": battery_level,
        "low_battery": battery_level is not None and battery_level <= LOW_BATTERY_THRESHOLD,
        "config_entry_id": entry.config_entry_id if entry is not None else None,
        "platform": entry.platform if entry is not None else None,
    }


async def async_security_overview(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the always-present Dashboard security card needs."""
    enabled = store.settings.get("security_sources_enabled") or {}

    ent_reg = er.async_get(hass)
    entities: list[dict[str, Any]] = []
    for domain in SECURITY_ENTITY_DOMAINS:
        if not enabled.get(domain, True):
            continue
        # Union of state machine and registry so a never-loaded entity still appears; disabled entries skipped.
        state_ids = set(hass.states.async_entity_ids(domain))
        registry_ids = {
            entry.entity_id
            for entry in ent_reg.entities.values()
            if entry.domain == domain and entry.disabled_by is None
        }
        for entity_id in state_ids | registry_ids:
            row = _entity_row(hass, entity_id)
            if row is None:
                row = _no_state_row(hass, entity_id)
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
