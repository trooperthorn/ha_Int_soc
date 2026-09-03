"""Entity ReMap: find and fix broken or stale entity_id references.

Structured references in automations, scripts, scenes, storage dashboards,
and config-entry helpers are rewritten in place; template references are
detect-only. Nothing here renames an entity in the registry. Scope,
limits, and safety rails are in docs/design.md and docs/decisions.md.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from itertools import chain
from typing import Any

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util
from homeassistant.util.yaml import dump as yaml_dump, load_yaml, parse_yaml

from .peripherals import iter_locator_strings
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

REMAP_BACKUP_DIR = os.path.join(".storage", "ha_soc_remap")
_BACKUP_RETENTION_DAYS = 30

YAML_TAINT_REASON = "contains !include or !secret; manual edit required"

# Coordinates HA SOC's own writers only; core's config-editor view locks are not importable.
_FILE_LOCKS: dict[str, asyncio.Lock] = {}


def _lock_for(path: str) -> asyncio.Lock:
    lock = _FILE_LOCKS.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _FILE_LOCKS[path] = lock
    return lock


def _backup_file_sync(path: str, stamp: str) -> str | None:
    """Copy a config file aside before the first rewrite of this apply run.
    Returns the backup path, or None if the source doesn't exist yet."""
    if not os.path.exists(path):
        return None
    backup_path = f"{path}.ha_soc-{stamp}.bak"
    shutil.copy2(path, backup_path)
    return backup_path


async def _backup_file_once(
    hass: HomeAssistant, path: str, stamp: str, backed_up: dict[str, str | None]
) -> None:
    """Back up ``path`` at most once per apply run (keyed in ``backed_up``)."""
    if path in backed_up:
        return
    backed_up[path] = await hass.async_add_executor_job(_backup_file_sync, path, stamp)


def _yaml_text_tainted(text: str) -> bool:
    """Whether the YAML text carries ``!include`` or ``!secret``; such a file is
    never rewritten. Plain text scan: over-refusing is safe, inlining an
    include is not.
    """
    return "!include" in text or "!secret" in text


def _yaml_file_tainted_sync(path: str) -> bool:
    """Text-level D-13 (b) taint check for one file; sync, executor-only."""
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read()
    except FileNotFoundError:
        return False
    return _yaml_text_tainted(text)


def _write_json_backup_sync(dir_path: str, stem: str, stamp: str, payload: Any) -> str:
    """Write one pre-rewrite JSON snapshot; sync, executor-only.

    A serialization failure propagates so the caller skips the rewrite.
    """
    os.makedirs(dir_path, mode=0o700, exist_ok=True)
    os.chmod(dir_path, 0o700)
    # Defense in depth: a url_path is a slug and an entry_id is hex.
    safe_stem = stem.replace(os.sep, "_")
    path = os.path.join(dir_path, f"{safe_stem}-{stamp}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    os.chmod(path, 0o600)
    return path


def _prune_backups_sync(dir_path: str) -> None:
    """Delete remap backups older than the retention period; sync, executor-only."""
    if not os.path.isdir(dir_path):
        return
    cutoff = time.time() - _BACKUP_RETENTION_DAYS * 24 * 3600
    for name in os.listdir(dir_path):
        path = os.path.join(dir_path, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            # A vanished or undeletable file must not block the apply.
            continue

REFERENCE_KIND_AUTOMATION = "automation"
REFERENCE_KIND_SCRIPT = "script"
REFERENCE_KIND_SCENE = "scene"
REFERENCE_KIND_DASHBOARD = "dashboard"
REFERENCE_KIND_HELPER = "helper"
REFERENCE_KIND_OTHER = "other"

# Field names verified against each domain's const.py/config_flow.py in the installed core.
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


def _exact_replace(value: Any, old_id: str, new_id: str) -> tuple[Any, int]:
    """Recursively replace exact-match entity_id strings; never a substring, so
    Jinja templates pass through untouched. Returns (new_value, count_replaced).
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


def _contains_exact_value(value: Any, entity_id: str) -> bool:
    """Exact match in VALUE position only: the positions _exact_replace can
    actually rewrite."""
    if isinstance(value, str):
        return value == entity_id
    if isinstance(value, list):
        return any(_contains_exact_value(v, entity_id) for v in value)
    if isinstance(value, dict):
        return any(_contains_exact_value(v, entity_id) for v in value.values())
    return False


def _contains_exact_key(value: Any, entity_id: str) -> bool:
    """Exact match in dict KEY position; _exact_replace never renames a key,
    so a key-only hit is reported detect-only."""
    if isinstance(value, list):
        return any(_contains_exact_key(v, entity_id) for v in value)
    if isinstance(value, dict):
        return entity_id in value or any(_contains_exact_key(v, entity_id) for v in value.values())
    return False


def _contains_exact(value: Any, entity_id: str) -> bool:
    """Exact match anywhere: value position or dict-key position."""
    return _contains_exact_value(value, entity_id) or _contains_exact_key(value, entity_id)


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
    hass: HomeAssistant,
    path: str,
    config_id: str,
    old_id: str,
    new_id: str,
    *,
    key_based: bool,
    stamp: str,
    backed_up: dict[str, str | None],
) -> int:
    """Shared apply path for automations.yaml/scenes.yaml (id-based list) and
    scripts.yaml (key-based dict). Mirrors config.view.BaseEditConfigView's
    own read -> mutate -> atomic write sequence, under a per-file lock and
    behind a one-time backup."""
    from homeassistant.const import CONF_ID
    from homeassistant.util.file import write_utf8_file_atomic

    def _read() -> Any:
        # Re-check taint inside the lock: the file can change between find and apply.
        try:
            with open(path, encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError:
            return {} if key_based else []
        if _yaml_text_tainted(text):
            raise ValueError(f"{os.path.basename(path)} {YAML_TAINT_REASON}")
        return parse_yaml(text)

    def _write(data: Any) -> None:
        write_utf8_file_atomic(path, yaml_dump(data))

    async with _lock_for(path):
        data = await hass.async_add_executor_job(_read)
        if not data:
            return 0

        if key_based:
            entry = data.get(config_id)
        else:
            entry = next((item for item in data if item.get(CONF_ID) == config_id), None)
        if entry is None:
            # Loud failure for the find-to-apply race, never a silent 0.
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

        await _backup_file_once(hass, path, stamp, backed_up)
        await hass.async_add_executor_job(_write, data)
        return count


async def _apply_scene_fix(
    hass: HomeAssistant,
    path: str,
    config_id: str,
    old_id: str,
    new_id: str,
    *,
    stamp: str,
    backed_up: dict[str, str | None],
) -> int:
    """Scenes are id-based like automations, but the entity_id is a DICT KEY
    under `entities:`, which the generic value walker cannot rename."""
    from homeassistant.const import CONF_ID
    from homeassistant.util.file import write_utf8_file_atomic

    def _read() -> Any:
        # Same in-lock taint re-check as _apply_yaml_list_fix.
        try:
            with open(path, encoding="utf-8") as file:
                text = file.read()
        except FileNotFoundError:
            return []
        if _yaml_text_tainted(text):
            raise ValueError(f"{os.path.basename(path)} {YAML_TAINT_REASON}")
        return parse_yaml(text)

    def _write(data: Any) -> None:
        write_utf8_file_atomic(path, yaml_dump(data))

    async with _lock_for(path):
        data = await hass.async_add_executor_job(_read)
        if not data:
            return 0

        entry = next((item for item in data if item.get(CONF_ID) == config_id), None)
        if entry is None:
            raise LookupError(f"{config_id!r} not found in {path}")

        entities = entry.get("entities")
        if not isinstance(entities, dict) or old_id not in entities:
            return 0

        # Refuse when the scene already configures new_id; overwriting it would be data loss.
        if new_id in entities:
            raise ValueError(
                f"scene {config_id!r} already has state for {new_id!r}; "
                "remapping would overwrite it"
            )

        entities[new_id] = entities.pop(old_id)
        await _backup_file_once(hass, path, stamp, backed_up)
        await hass.async_add_executor_job(_write, data)
        return 1


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
        value_hit = _contains_exact_value(loaded, entity_id)
        key_hit = _contains_exact_key(loaded, entity_id)
        if not value_hit and not key_hit:
            continue
        # A key-only occurrence is detect-only; _exact_replace rewrites values, never keys.
        if not is_storage:
            reason = "YAML-mode dashboard; edit its file manually."
        elif not value_hit:
            reason = (
                "Referenced only as a dictionary key (for example an entities map keyed on "
                "entity_ids); key positions are detected but never rewritten. Edit manually."
            )
        elif key_hit:
            reason = (
                "Value references will be fixed, but this dashboard also uses the entity_id as "
                "a dictionary key, which is never rewritten. Review the key manually."
            )
        else:
            reason = None
        items.append(
            {
                "kind": REFERENCE_KIND_DASHBOARD,
                "id": url_path or "lovelace",
                "name": (url_path or "Overview") if url_path else "Overview",
                "editable": is_storage and value_hit,
                "reason": reason,
                "template_only": not value_hit,
            }
        )
    return items


async def _apply_dashboard_fix(
    hass: HomeAssistant,
    url_path: str,
    old_id: str,
    new_id: str,
    *,
    stamp: str,
    backups: list[str],
) -> int:
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
        # ``loaded`` still holds the pre-rewrite state; a backup failure raises before the save.
        backup_path = await hass.async_add_executor_job(
            _write_json_backup_sync,
            hass.config.path(REMAP_BACKUP_DIR),
            key or "default",
            stamp,
            loaded,
        )
        backups.append(backup_path)
        await config.async_save(new_config)
    return count


def _find_helper_refs(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries():
        matched = False

        # UI-created helpers store fields in options; imported/older entries in data. Check both.
        for mapping in (entry.options or {}, entry.data or {}):
            for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
                if mapping.get(field) == entity_id:
                    matched = True
            for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
                if entity_id in (mapping.get(field) or []):
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

        # Allowlisted detect-only fallback: only INTEGRATION_LOCATOR_KEYS are read, never credentials.
        locator_values = chain(
            iter_locator_strings(entry.data or {}), iter_locator_strings(entry.options or {})
        )
        if any(entity_id in value for value in locator_values):
            items.append(
                {
                    "kind": REFERENCE_KIND_OTHER,
                    "id": entry.entry_id,
                    "name": f"{entry.title} ({entry.domain})",
                    "editable": False,
                    "reason": (
                        "Mentioned in a locator field of this config entry's stored data, "
                        "likely a template or an unmodeled field. Review and edit manually."
                    ),
                    "template_only": True,
                }
            )
    return items


async def _apply_helper_fix(
    hass: HomeAssistant,
    entry_id: str,
    old_id: str,
    new_id: str,
    *,
    stamp: str,
    backups: list[str],
) -> bool:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None:
        return False

    def _rewritten(mapping: dict[str, Any]) -> bool:
        changed = False
        for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
            if mapping.get(field) == old_id:
                mapping[field] = new_id
                changed = True
        for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
            values = mapping.get(field)
            if isinstance(values, list) and old_id in values:
                mapping[field] = [new_id if v == old_id else v for v in values]
                changed = True
        return changed

    # Shallow copies stay intact because _rewritten only reassigns top-level slots.
    previous = {
        "entry_id": entry.entry_id,
        "domain": entry.domain,
        "title": entry.title,
        "data": dict(entry.data or {}),
        "options": dict(entry.options or {}),
    }
    options = dict(entry.options or {})
    data = dict(entry.data or {})
    changed_options = _rewritten(options)
    changed_data = _rewritten(data)
    if not changed_options and not changed_data:
        return False

    # Snapshot both mappings before the update; a backup failure raises first.
    backup_path = await hass.async_add_executor_job(
        _write_json_backup_sync,
        hass.config.path(REMAP_BACKUP_DIR),
        entry.entry_id,
        stamp,
        previous,
    )
    backups.append(backup_path)

    update_kwargs: dict[str, Any] = {}
    if changed_options:
        update_kwargs["options"] = options
    if changed_data:
        update_kwargs["data"] = data
    hass.config_entries.async_update_entry(entry, **update_kwargs)
    hass.config_entries.async_schedule_reload(entry.entry_id)
    return True


async def _load_flat_file_ids(hass: HomeAssistant, path: str, *, key_based: bool) -> set[str]:
    """Which config ids are actually present in the flat automations.yaml/
    scripts.yaml/scenes.yaml file the apply step reads and writes."""
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


def _mark_manual_for_taint(items: list[dict[str, Any]]) -> None:
    """Every item from a tainted YAML file becomes detect-only with the one prescribed reason."""
    for item in items:
        item["editable"] = False
        item["reason"] = YAML_TAINT_REASON


async def async_find_references(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Everything referencing entity_id, grouped by kind, for the Entity
    ReMap page's preview. Every item is labeled editable/not; nothing here
    implies a fix will happen until async_apply_remap is actually called."""
    from homeassistant.config import (
        AUTOMATION_CONFIG_PATH,
        SCENE_CONFIG_PATH,
        SCRIPT_CONFIG_PATH,
    )

    automation_path = hass.config.path(AUTOMATION_CONFIG_PATH)
    script_path = hass.config.path(SCRIPT_CONFIG_PATH)
    scene_path = hass.config.path(SCENE_CONFIG_PATH)

    # Taint check on the raw text before any load_yaml; a tainted file's ids are unknowable.
    def _taints() -> dict[str, bool]:
        return {
            "automation": _yaml_file_tainted_sync(automation_path),
            "script": _yaml_file_tainted_sync(script_path),
            "scene": _yaml_file_tainted_sync(scene_path),
        }

    taints = await hass.async_add_executor_job(_taints)

    automation_ids = (
        set() if taints["automation"] else await _load_flat_file_ids(hass, automation_path, key_based=False)
    )
    script_ids = set() if taints["script"] else await _load_flat_file_ids(hass, script_path, key_based=True)
    scene_ids = set() if taints["scene"] else await _load_flat_file_ids(hass, scene_path, key_based=False)

    automations = _find_automation_refs(hass, entity_id, automation_ids)
    scripts = _find_script_refs(hass, entity_id, script_ids)
    scenes = _find_scene_refs(hass, entity_id, scene_ids)
    if taints["automation"]:
        _mark_manual_for_taint(automations)
    if taints["script"]:
        _mark_manual_for_taint(scripts)
    if taints["scene"]:
        _mark_manual_for_taint(scenes)
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


async def async_apply_remap(
    hass: HomeAssistant, old_id: str, new_id: str, *, backup_acknowledged: bool = False
) -> dict[str, Any]:
    """Re-scans (never trusts a stale prior preview) and rewrites every
    editable reference found. Returns per-kind counts so the caller can
    audit-log and the frontend can show exactly what changed.

    Refuses to run unless the caller acknowledged the backup (a server-side
    gate); every write is preceded by a backup whose path is returned.
    """
    if not backup_acknowledged:
        return {
            "old_entity_id": old_id,
            "new_entity_id": new_id,
            "fixed": {"automation": 0, "script": 0, "scene": 0, "dashboard": 0, "helper": 0},
            "errors": [],
            "backups": [],
            "error": "backup_not_acknowledged",
        }

    await hass.async_add_executor_job(_prune_backups_sync, hass.config.path(REMAP_BACKUP_DIR))

    report = await async_find_references(hass, old_id)
    fixed: dict[str, int] = {"automation": 0, "script": 0, "scene": 0, "dashboard": 0, "helper": 0}
    errors: list[str] = []
    # Millisecond stamp so two applies inside the same second cannot collide on a filename.
    stamp = dt_util.utcnow().strftime("%Y%m%dT%H%M%S%f")[:-3]
    backed_up: dict[str, str | None] = {}
    json_backups: list[str] = []

    for item in report["automation"]:
        if not item["editable"]:
            continue
        try:
            from homeassistant.config import AUTOMATION_CONFIG_PATH

            count = await _apply_yaml_list_fix(
                hass, hass.config.path(AUTOMATION_CONFIG_PATH), item["id"], old_id, new_id,
                key_based=False, stamp=stamp, backed_up=backed_up,
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
                hass, hass.config.path(SCRIPT_CONFIG_PATH), item["id"], old_id, new_id,
                key_based=True, stamp=stamp, backed_up=backed_up,
            )
            if count:
                fixed["script"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix script %s", item["id"], exc_info=True)
            errors.append(f"script {item['name']}: {err}")

    for item in report["scene"]:
        if not item["editable"]:
            continue
        try:
            from homeassistant.config import SCENE_CONFIG_PATH

            count = await _apply_scene_fix(
                hass, hass.config.path(SCENE_CONFIG_PATH), item["id"], old_id, new_id,
                stamp=stamp, backed_up=backed_up,
            )
            if count:
                fixed["scene"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix scene %s", item["id"], exc_info=True)
            errors.append(f"scene {item['name']}: {err}")

    for item in report["dashboard"]:
        if not item["editable"]:
            continue
        try:
            count = await _apply_dashboard_fix(
                hass, item["id"], old_id, new_id, stamp=stamp, backups=json_backups
            )
            if count:
                fixed["dashboard"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix dashboard %s", item["id"], exc_info=True)
            errors.append(f"dashboard {item['name']}: {err}")

    for item in report["helper"]:
        try:
            if await _apply_helper_fix(hass, item["id"], old_id, new_id, stamp=stamp, backups=json_backups):
                fixed["helper"] += 1
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Entity ReMap: failed to fix helper %s", item["id"], exc_info=True)
            errors.append(f"helper {item['name']}: {err}")

    # script.reload and scene.reload are registered with an empty schema: pass no data.
    if fixed["script"]:
        await hass.services.async_call("script", "reload")
    if fixed["scene"]:
        await hass.services.async_call("scene", "reload")

    backups = [path for path in backed_up.values() if path] + json_backups
    return {
        "old_entity_id": old_id,
        "new_entity_id": new_id,
        "fixed": fixed,
        "errors": errors,
        "backups": backups,
    }


async def async_scan_broken_references(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Spook-inspired proactive scan: every entity_id referenced by an
    automation, script, scene, or structured helper field that does not
    correspond to any currently known entity. One linear pass; Lovelace
    dashboards are deliberately not walked here.
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
        # Fields may live in options or data; the set de-duplicates a value present in both.
        refs: set[str] = set()
        for mapping in (entry.options or {}, entry.data or {}):
            for field in _HELPER_SCALAR_FIELDS.get(entry.domain, []):
                value = mapping.get(field)
                if isinstance(value, str) and value:
                    refs.add(value)
            for field in _HELPER_LIST_FIELDS.get(entry.domain, []):
                for value in mapping.get(field) or []:
                    if isinstance(value, str) and value:
                        refs.add(value)
        for ref in sorted(refs):
            if ref not in known:
                broken.setdefault(ref, []).append({"kind": REFERENCE_KIND_HELPER, "name": entry.title})

    return [
        {"entity_id": entity_id, "referenced_by": referenced_by}
        for entity_id, referenced_by in sorted(broken.items())
    ]
