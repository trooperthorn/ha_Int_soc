"""Config hygiene: the Spook-inspired proactive sweep beyond entity_id references.

Every function answers one question: does this piece of configuration point
at something that no longer exists? Each returns a HygieneResult carrying a
tri-state status; see docs/design.md.
"""
from __future__ import annotations

import re
from typing import Any

from homeassistant.core import HomeAssistant

from .const import SECURITY_ENTITY_DOMAINS, SECURITY_INTEGRATION_DOMAINS

_SERVICE_CALL_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")

HYGIENE_EVALUATED = "evaluated"
HYGIENE_EMPTY = "empty"
HYGIENE_COULD_NOT_EVALUATE = "could_not_evaluate"

# Sentinel: "no config passed, load here" versus "the sweep's own load failed" (could_not_evaluate).
_UNSET: Any = object()


class HygieneResult(list):
    """Found items plus the tri-state outcome of one hygiene evaluation.

    ``status`` is what health.py reads to decide whether an empty result may
    resolve prior findings.
    """

    def __init__(self, items: Any = (), status: str | None = None) -> None:
        super().__init__(items)
        if status is None:
            status = HYGIENE_EVALUATED if self else HYGIENE_EMPTY
        self.status = status


def _could_not_evaluate() -> HygieneResult:
    return HygieneResult(status=HYGIENE_COULD_NOT_EVALUATE)


async def _merged_yaml_config(hass: HomeAssistant) -> dict[str, Any] | None:
    """The merged (not schema-validated) configuration.yaml tree, or None when
    the load fails, which callers must report as could_not_evaluate."""
    from homeassistant.config import async_hass_config_yaml

    try:
        return await async_hass_config_yaml(hass)
    except Exception:  # noqa: BLE001 - a broken config must not take the sweep down
        return None


# Keys under these are service-call payload, not targets; never treated as service references.
_SERVICE_REF_OPAQUE_KEYS = frozenset({"data", "data_template", "variables"})


def _walk_service_refs(node: Any):
    """Recursively find every {"service": "domain.x"} / {"action": "domain.x"}
    field in a raw automation/script config tree; templated targets and
    payload subtrees are skipped."""
    if isinstance(node, dict):
        for key in ("service", "action"):
            value = node.get(key)
            if isinstance(value, str) and _SERVICE_CALL_RE.match(value):
                yield tuple(value.split(".", 1))
        for key, value in node.items():
            if key in _SERVICE_REF_OPAQUE_KEYS:
                continue
            yield from _walk_service_refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_service_refs(item)


def _iter_automation_and_script_entities(hass: HomeAssistant):
    from homeassistant.components.automation import DATA_COMPONENT as AUTOMATION_DATA_COMPONENT
    from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN

    automation_component = hass.data.get(AUTOMATION_DATA_COMPONENT)
    for entity in automation_component.entities if automation_component else ():
        yield "automation", entity
    script_component = hass.data.get(SCRIPT_DOMAIN)
    for entity in script_component.entities if script_component else ():
        yield "script", entity


def _trigger_entity_ids(raw_config: dict[str, Any]) -> set[str]:
    """entity_id(s) named directly on a trigger (automation-only in practice)."""
    triggers = raw_config.get("triggers") or raw_config.get("trigger") or []
    if isinstance(triggers, dict):
        triggers = [triggers]
    found: set[str] = set()
    for trig in triggers:
        if not isinstance(trig, dict):
            continue
        entity_id = trig.get("entity_id")
        if isinstance(entity_id, str):
            found.add(entity_id)
        elif isinstance(entity_id, list):
            found.update(e for e in entity_id if isinstance(e, str))
    return found


async def async_notify_coverage_gaps(hass: HomeAssistant, store: Any) -> HygieneResult:
    """Automations that call notify.* when triggered by an entity Security
    Integrations Health does not currently watch; gap is "untracked" or "disabled"."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entries_by_id = {entry.entry_id: entry for entry in hass.config_entries.async_entries()}
    sources_enabled = (store.settings.get("security_sources_enabled") or {}) if store else {}

    found: list[dict[str, Any]] = []
    for entity in (e for kind, e in _iter_automation_and_script_entities(hass) if kind == "automation"):
        raw = entity.raw_config
        if not raw:
            continue
        if not any(domain == "notify" for domain, _service in _walk_service_refs(raw)):
            continue

        for trigger_entity_id in _trigger_entity_ids(raw):
            entity_domain = trigger_entity_id.split(".", 1)[0]
            reg_entry = registry.async_get(trigger_entity_id)
            integration_domain = (
                entries_by_id[reg_entry.config_entry_id].domain
                if reg_entry and reg_entry.config_entry_id in entries_by_id
                else None
            )

            if entity_domain in SECURITY_ENTITY_DOMAINS:
                tracked_as = entity_domain
            elif integration_domain in SECURITY_INTEGRATION_DOMAINS:
                tracked_as = integration_domain
            else:
                found.append(
                    {
                        "automation_entity_id": entity.entity_id,
                        "name": entity.name or entity.entity_id,
                        "trigger_entity_id": trigger_entity_id,
                        "gap": "untracked",
                        "integration_domain": integration_domain,
                    }
                )
                continue

            if not sources_enabled.get(tracked_as, True):
                found.append(
                    {
                        "automation_entity_id": entity.entity_id,
                        "name": entity.name or entity.entity_id,
                        "trigger_entity_id": trigger_entity_id,
                        "gap": "disabled",
                        "tracked_as": tracked_as,
                    }
                )
    return HygieneResult(found)


async def async_unknown_service_references(hass: HomeAssistant) -> HygieneResult:
    found: list[dict[str, Any]] = []
    for kind, entity in _iter_automation_and_script_entities(hass):
        if not entity.raw_config:
            continue
        seen: set[tuple[str, str]] = set()
        for domain, service in _walk_service_refs(entity.raw_config):
            if (domain, service) in seen:
                continue
            seen.add((domain, service))
            if not hass.services.has_service(domain, service):
                found.append(
                    {"kind": kind, "entity_id": entity.entity_id, "name": entity.name or entity.entity_id,
                     "service": f"{domain}.{service}"}
                )
    return HygieneResult(found)


async def async_unknown_device_references(hass: HomeAssistant) -> HygieneResult:
    """Dangling device_ids in automations/scripts that loaded fine and lost
    the device afterwards; HA itself rejects never-existed ids at setup."""
    from homeassistant.components.automation import devices_in_automation
    from homeassistant.components.script import devices_in_script
    from homeassistant.helpers import device_registry as dr

    registry = dr.async_get(hass)
    found: list[dict[str, Any]] = []
    for kind, lookup in (("automation", devices_in_automation), ("script", devices_in_script)):
        for entity_id in hass.states.async_entity_ids(kind):
            for device_id in lookup(hass, entity_id):
                if registry.async_get(device_id) is None:
                    found.append({"kind": kind, "entity_id": entity_id, "device_id": device_id})
    return HygieneResult(found)


async def async_unknown_area_floor_label_references(hass: HomeAssistant) -> HygieneResult:
    from homeassistant.components.automation import (
        areas_in_automation, floors_in_automation, labels_in_automation,
    )
    from homeassistant.components.script import areas_in_script, floors_in_script, labels_in_script
    from homeassistant.helpers import area_registry as ar, floor_registry as fr, label_registry as lr

    areas = ar.async_get(hass).areas
    floors = fr.async_get(hass).floors
    labels = lr.async_get(hass).labels

    found: list[dict[str, Any]] = []
    lookups = (
        ("automation", "area", areas_in_automation, areas),
        ("automation", "floor", floors_in_automation, floors),
        ("automation", "label", labels_in_automation, labels),
        ("script", "area", areas_in_script, areas),
        ("script", "floor", floors_in_script, floors),
        ("script", "label", labels_in_script, labels),
    )
    for kind, ref_type, lookup, registry_items in lookups:
        for entity_id in hass.states.async_entity_ids(kind):
            for ref_id in lookup(hass, entity_id):
                if ref_id not in registry_items:
                    found.append({"kind": kind, "entity_id": entity_id, "ref_type": ref_type, "ref_id": ref_id})
    return HygieneResult(found)


async def async_alert_unknown_references(
    hass: HomeAssistant, config: dict[str, Any] | None = _UNSET
) -> HygieneResult:
    """``config`` is the sweep-shared merged YAML tree; None is could_not_evaluate, never an empty pass."""
    if config is _UNSET:
        config = await _merged_yaml_config(hass)
    if config is None:
        return _could_not_evaluate()
    alerts = config.get("alert") or {}
    found: list[dict[str, Any]] = []
    for object_id, cfg in alerts.items():
        cfg = cfg or {}
        watched = cfg.get("entity_id")
        if watched and hass.states.get(watched) is None:
            found.append({"alert_id": object_id, "kind": "entity", "ref": watched})
        for notifier in cfg.get("notifiers", []) or []:
            if not hass.services.has_service("notify", notifier):
                found.append({"alert_id": object_id, "kind": "notifier", "ref": notifier})
    return HygieneResult(found)


async def async_notify_group_unknown_members(hass: HomeAssistant) -> HygieneResult:
    """Best-effort: the legacy-YAML half degrades to nothing when the internal
    notify API moves; the config-entry half always evaluates."""
    found: list[dict[str, Any]] = []

    # (a) Legacy YAML notify groups: internal module, degrade to empty if it moves.
    try:
        from homeassistant.components.group.notify import GroupNotifyPlatform
        from homeassistant.components.notify.legacy import NOTIFY_SERVICES

        for svc in hass.data.get(NOTIFY_SERVICES, {}).get("group", []):
            if not isinstance(svc, GroupNotifyPlatform):
                continue
            for member in svc.entities:
                action = member.get("action")
                if action and not hass.services.has_service("notify", action):
                    found.append({"kind": "legacy_group", "group": None, "ref": action})
    except Exception:  # noqa: BLE001 - internal module; degrade honestly rather than crash the sweep
        pass

    # (b) Modern config-entry "Notify Group" helper (group_type == "notify").
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for entry in hass.config_entries.async_entries("group"):
        if entry.options.get("group_type") != "notify":
            continue
        for member in entry.options.get("entities", []) or []:
            if hass.states.get(member) is None:
                found.append({"kind": "notify_group_helper", "group": entry.title, "ref": member})
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            state = hass.states.get(reg_entry.entity_id)
            if state is None:
                continue
            for member in state.attributes.get("entity_id", []) or []:
                if hass.states.get(member) is None:
                    found.append({"kind": "notify_group_helper", "group": entry.title, "ref": member})

    return HygieneResult(found)


async def async_person_unknown_trackers(hass: HomeAssistant) -> HygieneResult:
    found: list[dict[str, Any]] = []
    for state in hass.states.async_all("person"):
        for tracker_id in state.attributes.get("device_trackers", []) or []:
            if hass.states.get(tracker_id) is None:
                found.append({"person": state.entity_id, "ref": tracker_id})
    return HygieneResult(found)


async def async_group_unknown_members(hass: HomeAssistant) -> HygieneResult:
    found: list[dict[str, Any]] = []
    for state in hass.states.async_all("group"):
        for member in state.attributes.get("entity_id", []) or []:
            if hass.states.get(member) is None:
                found.append({"group": state.entity_id, "ref": member})
    return HygieneResult(found)


async def async_proximity_unknown_references(hass: HomeAssistant) -> HygieneResult:
    from homeassistant.components.proximity.const import CONF_IGNORED_ZONES, CONF_TRACKED_ENTITIES
    from homeassistant.const import CONF_ZONE

    found: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries("proximity"):
        zone = entry.data.get(CONF_ZONE)
        if zone and hass.states.get(zone) is None:
            found.append({"proximity": entry.title, "kind": "zone", "ref": zone})
        for ref in entry.data.get(CONF_TRACKED_ENTITIES, []) or []:
            if hass.states.get(ref) is None:
                found.append({"proximity": entry.title, "kind": "tracked_entity", "ref": ref})
        for ref in entry.data.get(CONF_IGNORED_ZONES, []) or []:
            if hass.states.get(ref) is None:
                found.append({"proximity": entry.title, "kind": "ignored_zone", "ref": ref})
    return HygieneResult(found)


async def async_lovelace_missing_resources(hass: HomeAssistant) -> HygieneResult:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    ll_data = hass.data.get(LOVELACE_DATA)
    if ll_data is None:
        return _could_not_evaluate()

    resources = ll_data.resources
    if hasattr(resources, "loaded") and not resources.loaded:
        # Read through async_get_info() so core's own loaded flag stays core's; see docs/decisions.md.
        try:
            await resources.async_get_info()
        except Exception:  # noqa: BLE001
            return _could_not_evaluate()

    found: list[dict[str, Any]] = []
    for item in resources.async_items():
        url = item.get("url", "")
        if not url.startswith("/local/"):
            # Only /local/ is verifiable; other resource URLs are never flagged.
            continue
        base = hass.config.path("www")
        path = hass.config.path("www", url.removeprefix("/local/"))
        exists = await hass.async_add_executor_job(_path_exists, path, base)
        if not exists:
            found.append({"url": url, "type": item.get("type")})
    return HygieneResult(found)


def _path_exists(path: str, base: str) -> bool:
    """isfile(), but only inside the www base directory: both sides are
    realpath'd so a resource URL can never escape www."""
    import os

    real_base = os.path.realpath(base)
    real_path = os.path.realpath(path)
    if real_path != real_base and not real_path.startswith(real_base + os.sep):
        return False
    return os.path.isfile(real_path)


async def async_empty_areas_and_floors(hass: HomeAssistant) -> dict[str, list[str]]:
    from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, floor_registry as fr

    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    floor_registry = fr.async_get(hass)

    empty_areas = [
        area.name
        for area in area_registry.areas.values()
        if not dr.async_entries_for_area(device_registry, area.id)
        and not er.async_entries_for_area(entity_registry, area.id)
    ]
    empty_floors = [
        floor.name
        for floor in floor_registry.floors.values()
        if not ar.async_entries_for_floor(area_registry, floor.floor_id)
    ]
    return {"areas": empty_areas, "floors": empty_floors}


async def async_unused_labels_and_blueprints(hass: HomeAssistant) -> dict[str, list[str]]:
    from homeassistant.components.automation import automations_with_blueprint, automations_with_label
    from homeassistant.components.automation.helpers import async_get_blueprints as automation_blueprints
    from homeassistant.components.script import scripts_with_blueprint, scripts_with_label
    from homeassistant.components.script.helpers import async_get_blueprints as script_blueprints
    from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er, label_registry as lr

    label_registry = lr.async_get(hass)
    area_registry = ar.async_get(hass)
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    unused_labels: list[str] = []
    for label in label_registry.labels.values():
        used = (
            er.async_entries_for_label(entity_registry, label.label_id)
            or dr.async_entries_for_label(device_registry, label.label_id)
            or ar.async_entries_for_label(area_registry, label.label_id)
            or automations_with_label(hass, label.label_id)
            or scripts_with_label(hass, label.label_id)
        )
        if not used:
            unused_labels.append(label.name)

    unused_blueprints: list[str] = []
    for domain, get_bps, with_bp in (
        ("automation", automation_blueprints, automations_with_blueprint),
        ("script", script_blueprints, scripts_with_blueprint),
    ):
        try:
            manager = get_bps(hass)
            installed = await manager.async_get_blueprints()
        except Exception:  # noqa: BLE001
            continue
        for path in installed:
            if not with_bp(hass, path):
                unused_blueprints.append(f"{domain}/{path}")

    return {"labels": unused_labels, "blueprints": unused_blueprints}


async def async_unknown_customize_entities(
    hass: HomeAssistant, config: dict[str, Any] | None = _UNSET
) -> HygieneResult:
    """``config`` is the sweep-shared merged YAML tree, same contract as async_alert_unknown_references."""
    if config is _UNSET:
        config = await _merged_yaml_config(hass)
    if config is None:
        return _could_not_evaluate()
    customize = ((config.get("homeassistant") or {}).get("customize")) or {}
    return HygieneResult(
        entity_id for entity_id in customize if hass.states.get(entity_id) is None
    )


async def async_orphaned_statistics(hass: HomeAssistant) -> HygieneResult:
    from homeassistant.components.recorder.statistics import async_list_statistic_ids

    try:
        rows = await async_list_statistic_ids(hass)
    except Exception:  # noqa: BLE001 - recorder not loaded/configured
        # No recorder means nothing to judge; leave prior findings alone.
        return _could_not_evaluate()

    orphaned = []
    for row in rows:
        statistic_id = row.get("statistic_id", "")
        if statistic_id.count(".") == 1 and hass.states.get(statistic_id) is None:
            orphaned.append(statistic_id)
    return HygieneResult(orphaned)


async def async_energy_unknown_references(hass: HomeAssistant) -> HygieneResult:
    from homeassistant.components.energy.data import async_get_manager

    try:
        manager = await async_get_manager(hass)
    except Exception:  # noqa: BLE001
        # Energy manager unavailable; nothing can be evaluated this pass.
        return _could_not_evaluate()
    prefs = manager.data
    if prefs is None:
        # Energy was never configured; genuinely nothing to check.
        return HygieneResult()

    found: list[dict[str, Any]] = []

    def _check(ref: str | None, field: str) -> None:
        if ref and hass.states.get(ref) is None:
            found.append({"field": field, "ref": ref})

    for source in prefs.get("energy_sources", []):
        source_type = source.get("type")
        if source_type == "grid":
            for flow in source.get("flow_from", []):
                _check(flow.get("stat_energy_from"), "grid.flow_from.stat_energy_from")
            for flow in source.get("flow_to", []):
                _check(flow.get("stat_energy_to"), "grid.flow_to.stat_energy_to")
        elif source_type in ("solar", "battery"):
            _check(source.get("stat_energy_from"), f"{source_type}.stat_energy_from")
            if source_type == "battery":
                _check(source.get("stat_energy_to"), "battery.stat_energy_to")
        elif source_type in ("gas", "water"):
            _check(source.get("stat_energy_from"), f"{source_type}.stat_energy_from")
            _check(source.get("entity_energy_price"), f"{source_type}.entity_energy_price")

    for device in prefs.get("device_consumption", []):
        _check(device.get("stat_consumption"), "device_consumption.stat_consumption")

    return HygieneResult(found)
