"""Entity ReMap — find and fix broken/stale entity_id references.

Home Assistant has no feature for this today, in core or in the well-known
`Spook` HACS add-on (research done before writing this module confirmed
both directly against their source): renaming an entity_id, or an entity
simply disappearing (replaced hardware, a re-added integration, a typo'd
YAML edit), only ever touches the entity registry. Every automation,
script, scene, Lovelace dashboard, and helper that referenced the old
entity_id keeps the literal old string and silently breaks — Home
Assistant's own delete-confirmation dialog says as much ("you will need
to update those manually"). This module is that manual step, automated,
with real limits stated honestly rather than papered over:

- Automations/scripts/scenes: real, structured entity_id fields (a
  trigger's `entity_id:`, a service call's `target:`, a condition) are
  found via core's own `referenced_entities` extraction and safely
  rewritten by replicating the exact read/lock/atomic-write/reload
  primitives `homeassistant.components.config`'s own editor views use
  (there is no importable library function for this — the views are
  tied to the HTTP layer). A reference that only exists inside a Jinja
  template string (`{{ states('sensor.old') }}`) is NOT found by
  `referenced_entities` (core's own extractor explicitly skips templated
  fields) and is NEVER auto-rewritten — a regex could just as easily
  corrupt a similarly-named entity_id or miss a computed one. Templates
  are flagged detect-only, for a human to fix.
- Lovelace dashboards ("Views"): storage-mode dashboards are freely
  read/writable through the same `LovelaceConfig` object core's frontend
  uses. YAML-mode dashboards are a confirmed, hard dead end — core's own
  `LovelaceYAML.async_save()` raises `HomeAssistantError("Not
  supported")` — surfaced as "manual edit required" with the file path,
  never silently skipped.
- Helpers: config-entry-backed helpers (derivative, utility_meter,
  threshold, generic_thermostat, generic_hygrostat, integration,
  min_max, filter, switch_as_x, trend, history_stats, statistics,
  mold_indicator) store their source entity_id(s) as plain option
  fields, actively rewritten via `config_entries.async_update_entry` +
  `async_schedule_reload`. Template helpers store a Jinja string with no
  structured field to rewrite — same detect-only treatment as automation
  templates. Any other config entry gets a best-effort substring check
  across its stored data/options (the same technique peripherals.py uses
  for USB-path matching) — a hit is reported, never rewritten.

Nothing here performs an entity registry rename. This module's job is
strictly the *consuming configuration* — the old entity_id, whether it
still exists in the registry or not, is left alone; if the user also
wants it renamed, that's Home Assistant's own existing Settings > Entities
rename, unrelated to and safe to combine with what this module does.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import dump as yaml_dump, load_yaml

from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

REFERENCE_KIND_AUTOMATION = "automation"
REFERENCE_KIND_SCRIPT = "script"
REFERENCE_KIND_SCENE = "scene"
REFERENCE_KIND_DASHBOARD = "dashboard"
REFERENCE_KIND_HELPER = "helper"
REFERENCE_KIND_OTHER = "other"

# Config-entry-backed helper domains whose source entity_id(s) live in a
# single scalar option field, verified directly against the installed
# homeassistant package's const.py/config_flow.py for each domain (not
# guessed) — see this module's docstring for the reasoning.
_HELPER_SCALAR_FIELDS: dict[str, list[str]] = {
    "derivative": ["source"],
    "utility_meter": ["source"],
    "threshold": ["entity_id"],
    "generic_thermostat": ["heater", "target_sensor"],
    "generic_hygrostat": ["humidifier", "target_sensor"],
    "integration": ["source"],
    "filter": ["entity_id"],
    "switch_as_x": ["entity_id"],
    "trend": ["entity_id"],
    "history_stats": ["entity_id"],
    "statistics": ["entity_id"],
    "mold_indicator": ["indoor_temp_sensor", "outdoor_temp_sensor", "indoor_humidity_sensor"],
}
# Same idea, but the option value is a list of entity_ids rather than one.
_HELPER_LIST_FIELDS: dict[str, list[str]] = {
    "min_max": ["entity_ids"],
}


# -- Generic structure walkers (automations/scripts/scenes/dashboards) ------


def _exact_replace(value: Any, old_id: str, new_id: str) -> tuple[Any, int]:
    """Recursively replace exact-match entity_id strings.

    Only an exact string match is replaced — never a substring. This is
    what makes it safe against Jinja templates: `{{ states('sensor.old')
    }}` never equals `sensor.old`, so it passes through untouched, while
    a structured `entity_id: sensor.old` or `entities: [sensor.old, ...]`
    field does get rewritten. Returns (new_value, count_replaced).
    """
    if isinstance(value, str):
        return (new_id, 1) if value == old_id else (value, 0)
    if isinstance(value, list):
        count = 0
        out = []
        for item in value:
            new_item, c = _exact_replace(item, old_id, new_id)
            out.append(new_item)
            count += c
        return out, count
    if isinstance(value, dict):
        count = 0
        out = {}
        for key, val in value.items():
            new_val, c = _exact_replace(val, old_id, new_id)
            out[key] = new_val
            count += c
        return out, count
    return value, 0


def _contains_exact(value: Any, entity_id: str) -> bool:
    if isinstance(value, str):
        return value == entity_id
    if isinstance(value, list):
        return any(_contains_exact(v, entity_id) for v in value)
    if isinstance(value, dict):
        return any(_contains_exact(v, entity_id) for v in value.values())
    return False


def _mentions_substring(value: Any, entity_id: str) -> bool:
    """Detect-only: entity_id appears as a substring anywhere (e.g. inside
    a Jinja template), even where it's not a structured exact match.
    Never used to decide what gets rewritten.
    """
    if isinstance(value, str):
        return entity_id in value
    if isinstance(value, list):
        return any(_mentions_substring(v, entity_id) for v in value)
    if isinstance(value, dict):
        return any(_mentions_substring(v, entity_id) for v in value.values())
    return False


# -- Automations / scripts / scenes ------------------------------------------
# All three are edited the same way: read the whole YAML file, find the one
# entry, rewrite it in memory, write the whole file back atomically, then
# call that domain's reload service — replicating exactly what
# homeassistant.components.config's own EditIdBasedConfigView /
# EditKeyBasedConfigView do internally (there's no importable library
# function for this; those views are tied to the HTTP layer).


def _find_automation_refs(hass: HomeAssistant, entity_id: str, known_ids: set[str]) -> list[dict[str, Any]]:
    from homeassistant.components.automation import DATA_COMPONENT, automations_with_entity

    component = hass.data.get(DATA_COMPONENT)
    if component is None:
        return []
    referencing_ids = set(automations_with_entity(hass, entity_id))
    items: list[dict[str, Any]] = []
    for entity in component.entities:
        if entity.entity_id in referencing_ids:
            items.append(_ref_item(REFERENCE_KIND_AUTOMATION, entity, entity_id, template_only=False, known_ids=known_ids))
        elif entity.raw_config and _mentions_substring(entity.raw_config, entity_id):
            items.append(_ref_item(REFERENCE_KIND_AUTOMATION, entity, entity_id, template_only=True, known_ids=known_ids))
    return items


def _find_script_refs(hass: HomeAssistant, entity_id: str, known_ids: set[str]) -> list[dict[str, Any]]:
    from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN, scripts_with_entity

    component = hass.data.get(SCRIPT_DOMAIN)
    if component is None:
        return []
    referencing_ids = set(scripts_with_entity(hass, entity_id))
    items: list[dict[str, Any]] = []
    for entity in component.entities:
        if entity.entity_id in referencing_ids:
            items.append(_ref_item(REFERENCE_KIND_SCRIPT, entity, entity_id, template_only=False, known_ids=known_ids))
        elif entity.raw_config and _mentions_substring(entity.raw_config, entity_id):
            items.append(_ref_item(REFERENCE_KIND_SCRIPT, entity, entity_id, template_only=True, known_ids=known_ids))
    return items


def _find_scene_refs(hass: HomeAssistant, entity_id: str, known_ids: set[str]) -> list[dict[str, Any]]:
    from homeassistant.components.homeassistant.scene import DATA_PLATFORM

    platform = hass.data.get(DATA_PLATFORM)
    if platform is None:
        return []
    items: list[dict[str, Any]] = []
    for entity in platform.entities.values():
        states = getattr(entity.scene_config, "states", None) or {}
        if entity_id in states:
            in_flat_file = entity.unique_id is not None and entity.unique_id in known_ids
            reason = None
            if entity.unique_id is None:
                reason = "Not YAML-defined — no config id."
            elif not in_flat_file:
                reason = _NOT_IN_FLAT_FILE_REASON.format(file="scenes.yaml")
            items.append(
                {
                    "kind": REFERENCE_KIND_SCENE,
                    "id": entity.unique_id,
                    "name": entity.name or entity.entity_id,
                    "editable": in_flat_file,
                    "reason": reason,
                    "template_only": False,
                }
            )
    return items


_NOT_IN_FLAT_FILE_REASON = (
    "Not found in the standard {file} — likely split across multiple files "
    "(!include_dir_merge_list) or defined via a package. Home Assistant's own UI "
    "editor has this exact same limitation; edit it manually."
)


def _ref_item(kind: str, entity: Any, entity_id: str, *, template_only: bool, known_ids: set[str]) -> dict[str, Any]:
    in_flat_file = entity.unique_id is not None and entity.unique_id in known_ids
    editable = in_flat_file and not template_only
    reason = None
    if entity.unique_id is None:
        reason = "No config id — not editable here."
    elif not in_flat_file:
        file_name = "automations.yaml" if kind == REFERENCE_KIND_AUTOMATION else "scripts.yaml"
        reason = _NOT_IN_FLAT_FILE_REASON.format(file=file_name)
    elif template_only:
        reason = f"Only mentioned inside a template — review and edit {entity.entity_id} manually."
    return {
        "kind": kind,
        "id": entity.unique_id,
        "name": getattr(entity, "name", None) or entity.entity_id,
        "editable": editable,
        "reason": reason,
        "template_only": template_only,
    }


async def _apply_yaml_list_fix(
    hass: HomeAssistant, path: str, config_id: str, old_id: str, new_id: str, *, key_based: bool
) -> int:
    """Shared apply path for automations.yaml/scenes.yaml (id-based list) and
    scripts.yaml (key-based dict). Mirrors config.view.BaseEditConfigView's
    own read -> mutate -> atomic write sequence."""
    from homeassistant.const import CONF_ID
    from homeassistant.util.file import write_utf8_file_atomic

    def _read() -> Any:
        try:
            return load_yaml(path)
        except FileNotFoundError:
            return {} if key_based else []

    def _write(data: Any) -> None:
        write_utf8_file_atomic(path, yaml_dump(data))

    data = await hass.async_add_executor_job(_read)
    if not data:
        return 0

    if key_based:
        entry = data.get(config_id)
    else:
        entry = next((item for item in data if item.get(CONF_ID) == config_id), None)
    if entry is None:
        # async_find_references already filters to ids confirmed present
        # in this exact file, so this should be unreachable in normal
        # operation — kept as a loud failure (not a silent 0) for the
        # narrow race where the file changed between find and apply,
        # rather than reporting a false "nothing to fix".
        raise LookupError(f"{config_id!r} not found in {path}")

    new_entry, count = _exact_replace(entry, old_id, new_id)
    if count == 0:
        return 0

    if key_based:
        data[config_id] = new_entry
    else:
        for index, item in enumerate(data):
            if item.get(CONF_ID) == config_id:
                data[index] = new_entry
                break

    await hass.async_add_executor_job(_write, data)
    return count


async def _apply_scene_fix(hass: HomeAssistant, path: str, config_id: str, old_id: str, new_id: str) -> int:
    """Scenes are id-based like automations, but the entity_id lives as a
    DICT KEY under `entities:` (`{sensor.old: "on"}`), not a value — the
    generic exact-value walker can't rename a key, so this handles that
    one field specially and reuses the same read/write primitives."""
    from homeassistant.const import CONF_ID
    from homeassistant.util.file import write_utf8_file_atomic

    def _read() -> Any:
        try:
            return load_yaml(path)
        except FileNotFoundError:
            return []

    def _write(data: Any) -> None:
        write_utf8_file_atomic(path, yaml_dump(data))

    data = await hass.async_add_executor_job(_read)
    if not data:
        return 0

    entry = next((item for item in data if item.get(CONF_ID) == config_id), None)
    if entry is None:
        raise LookupError(f"{config_id!r} not found in {path}")

    entities = entry.get("entities")
    if not isinstance(entities, dict) or old_id not in entities:
        return 0

    entities[new_id] = entities.pop(old_id)
    await hass.async_add_executor_job(_write, data)
    return 1


# -- Lovelace dashboards ("Views") -------------------------------------------


def _iter_dashboards(hass: HomeAssistant):
    from homeassistant.components.lovelace import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import MODE_STORAGE

    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return
    for url_path, config in lovelace_data.dashboards.items():
        yield url_path, config, config.mode == MODE_STORAGE


async def _find_dashboard_refs(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for url_path, config, is_storage in _iter_dashboards(hass):
        try:
            loaded = await config.async_load(False)
        except Exception:  # noqa: BLE001 - a dashboard that fails to load isn't this module's problem
            continue
        if not _contains_exact(loaded, entity_id):
            continue
        items.append(
            {
                "kind": REFERENCE_KIND_DASHBOARD,
                "id": url_path or "lovelace",
                "name": (url_path or "Overview") if url_path else "Overview",
                "editable": is_storage,
                "reason": None if is_storage else "YAML-mode dashboard — edit its file manually.",
                "template_only": False,
            }
        )
    return items


async def _apply_dashboard_fix(hass: HomeAssistant, url_path: str, old_id: str, new_id: str) -> int:
    from homeassistant.components.lovelace import LOVELACE_DATA

    key = None if url_path in (None, "lovelace") else url_path
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return 0
    config = lovelace_data.dashboards.get(key)
    if config is None:
        return 0
    loaded = await config.async_load(True)
    new_config, count = _exact_replace(loaded, old_id, new_id)
    if count:
        await config.async_save(new_config)
    return count


# -- Helpers (config-entry-backed) -------------------------------------------


def _find_helper_refs(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries():
        options = entry.options or {}
        matched = False

        for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
            if options.get(field) == entity_id:
                matched = True
        for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
            if entity_id in (options.get(field) or []):
                matched = True

        if matched:
            items.append(
                {
                    "kind": REFERENCE_KIND_HELPER,
                    "id": entry.entry_id,
                    "name": f"{entry.title} ({entry.domain})",
                    "editable": True,
                    "reason": None,
                    "template_only": False,
                }
            )
            continue

        if entry.domain in _HELPER_SCALAR_FIELDS or entry.domain in _HELPER_LIST_FIELDS:
            continue  # already checked structurally above; don't double-report as "other"

        haystack = f"{entry.data}{entry.options}"
        if entity_id in haystack:
            items.append(
                {
                    "kind": REFERENCE_KIND_OTHER,
                    "id": entry.entry_id,
                    "name": f"{entry.title} ({entry.domain})",
                    "editable": False,
                    "reason": (
                        "Mentioned in this config entry's stored data — likely a template or "
                        "an unmodeled field. Review and edit manually."
                    ),
                    "template_only": True,
                }
            )
    return items


async def _apply_helper_fix(hass: HomeAssistant, entry_id: str, old_id: str, new_id: str) -> bool:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return False
    options = dict(entry.options or {})
    changed = False

    for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
        if options.get(field) == old_id:
            options[field] = new_id
            changed = True
    for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
        values = options.get(field)
        if isinstance(values, list) and old_id in values:
            options[field] = [new_id if v == old_id else v for v in values]
            changed = True

    if not changed:
        return False
    hass.config_entries.async_update_entry(entry, options=options)
    hass.config_entries.async_schedule_reload(entry.entry_id)
    return True


# -- Public API ---------------------------------------------------------------


async def _load_flat_file_ids(hass: HomeAssistant, path: str, *, key_based: bool) -> set[str]:
    """Which config ids are actually present in the flat automations.yaml/
    scripts.yaml/scenes.yaml file the apply step reads and writes.

    An automation/script/scene can have a config `id:` and still not live
    here at all — split across multiple files via `!include_dir_merge_list`,
    or defined inside a package. Home Assistant's own UI editor can't edit
    those either (it only ever reads/writes this exact file); checking this
    upfront is what keeps the "will fix" label in the preview honest,
    instead of promising a fix that silently no-ops at apply time.
    """
    from homeassistant.const import CONF_ID

    def _read() -> Any:
        try:
            return load_yaml(path)
        except FileNotFoundError:
            return {} if key_based else []

    data = await hass.async_add_executor_job(_read)
    if not data:
        return set()
    if key_based:
        return set(data.keys())
    return {item.get(CONF_ID) for item in data if isinstance(item, dict) and item.get(CONF_ID)}


async def async_find_references(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Everything referencing entity_id, grouped by kind, for the Entity
    ReMap page's preview. Every item is labeled editable/not — nothing here
    implies a fix will happen until async_apply_remap is actually called."""
    from homeassistant.config import (
        AUTOMATION_CONFIG_PATH,
        SCENE_CONFIG_PATH,
        SCRIPT_CONFIG_PATH,
    )

    automation_ids = await _load_flat_file_ids(hass, hass.config.path(AUTOMATION_CONFIG_PATH), key_based=False)
    script_ids = await _load_flat_file_ids(hass, hass.config.path(SCRIPT_CONFIG_PATH), key_based=True)
    scene_ids = await _load_flat_file_ids(hass, hass.config.path(SCENE_CONFIG_PATH), key_based=False)

    automations = _find_automation_refs(hass, entity_id, automation_ids)
    scripts = _find_script_refs(hass, entity_id, script_ids)
    scenes = _find_scene_refs(hass, entity_id, scene_ids)
    dashboards = await _find_dashboard_refs(hass, entity_id)
    helpers = _find_helper_refs(hass, entity_id)

    all_items = automations + scripts + scenes + dashboards + helpers
    editable_count = sum(1 for item in all_items if item["editable"])
    return {
        "entity_id": entity_id,
        "automation": automations,
        "script": scripts,
        "scene": scenes,
        "dashboard": dashboards,
        "helper": [i for i in helpers if i["kind"] == REFERENCE_KIND_HELPER],
        "other": [i for i in helpers if i["kind"] == REFERENCE_KIND_OTHER],
        "total_count": len(all_items),
        "editable_count": editable_count,
        "paths": {
            "automation": AUTOMATION_CONFIG_PATH,
            "script": SCRIPT_CONFIG_PATH,
            "scene": SCENE_CONFIG_PATH,
        },
    }


async def async_apply_remap(hass: HomeAssistant, old_id: str, new_id: str) -> dict[str, Any]:
    """Re-scans (never trusts a stale prior preview) and rewrites every
    editable reference found. Returns per-kind counts so the caller can
    audit-log and the frontend can show exactly what changed."""
    report = await async_find_references(hass, old_id)
    fixed: dict[str, int] = {"automation": 0, "script": 0, "scene": 0, "dashboard": 0, "helper": 0}
    errors: list[str] = []

    for item in report["automation"]:
        if not item["editable"]:
            continue
        try:
            from homeassistant.config import AUTOMATION_CONFIG_PATH

            count = await _apply_yaml_list_fix(
                hass, hass.config.path(AUTOMATION_CONFIG_PATH), item["id"], old_id, new_id, key_based=False
            )
            if count:
                await hass.services.async_call("automation", "reload", {"id": item["id"]})
                fixed["automation"] += 1
        except Exception as err:  # noqa: BLE001 - one bad item must not stop the rest
            _LOGGER.warning("Entity ReMap: failed to fix automation %s", item["id"], exc_info=True)
            errors.append(f"automation {item['name']}: {err}")

    for item in report["script"]:
        if not item["editable"]:
            continue
        try:
            from homeassistant.config import SCRIPT_CONFIG_PATH

            count = await _apply_yaml_list_fix(
                hass, hass.config.path(SCRIPT_CONFIG_PATH), item["id"], old_id, new_id, key_based=True
            )
            if count:
                await hass.services.async_call("script", "reload")
                fixed["script"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix script %s", item["id"], exc_info=True)
            errors.append(f"script {item['name']}: {err}")

    for item in report["scene"]:
        if not item["editable"]:
            continue
        try:
            from homeassistant.config import SCENE_CONFIG_PATH

            count = await _apply_scene_fix(hass, hass.config.path(SCENE_CONFIG_PATH), item["id"], old_id, new_id)
            if count:
                await hass.services.async_call("scene", "reload")
                fixed["scene"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix scene %s", item["id"], exc_info=True)
            errors.append(f"scene {item['name']}: {err}")

    for item in report["dashboard"]:
        if not item["editable"]:
            continue
        try:
            count = await _apply_dashboard_fix(hass, item["id"], old_id, new_id)
            if count:
                fixed["dashboard"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix dashboard %s", item["id"], exc_info=True)
            errors.append(f"dashboard {item['name']}: {err}")

    for item in report["helper"]:
        try:
            if await _apply_helper_fix(hass, item["id"], old_id, new_id):
                fixed["helper"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix helper %s", item["id"], exc_info=True)
            errors.append(f"helper {item['name']}: {err}")

    return {"old_entity_id": old_id, "new_entity_id": new_id, "fixed": fixed, "errors": errors}


async def async_scan_broken_references(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Spook-inspired proactive scan: every entity_id referenced by an
    automation, script, or scene (or a structured helper field) that
    doesn't correspond to any currently known entity. One linear pass
    over every automation/script/scene/helper (not one search per
    entity), collecting every reference and checking each once — the
    inverse direction from async_find_references, and much cheaper for
    "scan everything" than calling that once per entity would be.

    Deliberately does not walk Lovelace dashboards here: there's no core
    helper enumerating "every entity_id any card anywhere references"
    the way referenced_entities does for automations/scripts, and a full
    recursive walk of every dashboard for every possible entity_id is
    real, recurring work this periodic sweep doesn't take on. Views are
    still fully covered by the interactive Entity ReMap search for one
    specific entity_id — this scan is only the "what needs attention"
    proactive half.
    """
    known = set(hass.states.async_entity_ids())
    from homeassistant.helpers import entity_registry as er

    known |= set(er.async_get(hass).entities)

    broken: dict[str, list[dict[str, str]]] = {}

    from homeassistant.components.automation import DATA_COMPONENT as AUTOMATION_DATA

    automation_component = hass.data.get(AUTOMATION_DATA)
    if automation_component is not None:
        for entity in automation_component.entities:
            for ref in entity.referenced_entities:
                if ref not in known:
                    broken.setdefault(ref, []).append(
                        {"kind": REFERENCE_KIND_AUTOMATION, "name": entity.name or entity.entity_id}
                    )

    from homeassistant.components.script import DOMAIN as SCRIPT_DOMAIN

    script_component = hass.data.get(SCRIPT_DOMAIN)
    if script_component is not None:
        for entity in script_component.entities:
            for ref in entity.referenced_entities:
                if ref not in known:
                    broken.setdefault(ref, []).append(
                        {"kind": REFERENCE_KIND_SCRIPT, "name": entity.name or entity.entity_id}
                    )

    from homeassistant.components.homeassistant.scene import DATA_PLATFORM as SCENE_PLATFORM

    scene_platform = hass.data.get(SCENE_PLATFORM)
    if scene_platform is not None:
        for entity in scene_platform.entities.values():
            states = getattr(entity.scene_config, "states", None) or {}
            for ref in states:
                if ref not in known:
                    broken.setdefault(ref, []).append(
                        {"kind": REFERENCE_KIND_SCENE, "name": entity.name or entity.entity_id}
                    )

    for entry in hass.config_entries.async_entries():
        options = entry.options or {}
        for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
            ref = options.get(field)
            if ref and ref not in known:
                broken.setdefault(ref, []).append({"kind": REFERENCE_KIND_HELPER, "name": entry.title})
        for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
            for ref in options.get(field) or []:
                if ref not in known:
                    broken.setdefault(ref, []).append({"kind": REFERENCE_KIND_HELPER, "name": entry.title})

    return [
        {"entity_id": entity_id, "referenced_by": referenced_by}
        for entity_id, referenced_by in sorted(broken.items())
    ]
