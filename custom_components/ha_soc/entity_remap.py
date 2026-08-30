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
  mold_indicator) store their source entity_id(s) as plain fields in
  the entry's options (or, for imported/older entries, its data),
  actively rewritten via `config_entries.async_update_entry` +
  `async_schedule_reload`. Template helpers store a Jinja string with no
  structured field to rewrite — same detect-only treatment as automation
  templates. Any other config entry gets a best-effort substring check
  across the allowlisted locator fields of its stored data and options
  (const.INTEGRATION_LOCATOR_KEYS, via the same helper peripherals.py
  uses for USB-path matching); a hit is reported, never rewritten.
  Credentials in other integrations' entries are deliberately never
  read (work plan item SEC-4), so an entity_id that only appears inside
  a stored password is not reported, and that is correct.

Safety rails around apply (work plan item 1.9, decision D-13 (a) plus
(b)): comment, anchor, and key-order loss in rewritten YAML is accepted
and stated up front, exactly as core's own config editor behaves; every
YAML config file is copied aside before its first rewrite; storage-mode
dashboards and helper config entries get a JSON snapshot of their
previous state under `.storage/ha_soc_remap/` (files 0o600, directory
0o700, pruned after 30 days) before they are rewritten; the backup
paths are returned in the apply result; and a YAML file whose text
contains `!include` or `!secret` is refused entirely, with every item
in it reported as "manual edit required" (see _yaml_text_tainted for
the verified platform behavior that makes the refusal necessary).

Nothing here performs an entity registry rename. This module's job is
strictly the *consuming configuration* — the old entity_id, whether it
still exists in the registry or not, is left alone; if the user also
wants it renamed, that's Home Assistant's own existing Settings > Entities
rename, unrelated to and safe to combine with what this module does.
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

# JSON snapshots of storage dashboards and helper entries land here before
# each rewrite (work plan item 1.9). Relative to the config directory.
REMAP_BACKUP_DIR = os.path.join(".storage", "ha_soc_remap")
_BACKUP_RETENTION_DAYS = 30

# The one reason string D-13 (b) prescribes for a refused YAML file.
YAML_TAINT_REASON = "contains !include or !secret; manual edit required"

# Per-file locks so two overlapping remaps (or a remap racing our own
# re-scan) can't interleave a read-modify-write on the same config file and
# silently drop one write. This coordinates HA SOC's OWN writers; it cannot
# share Home Assistant core's config-editor view locks (those are tied to
# the HTTP view instances and aren't importable), so a simultaneous edit
# through HA's native UI is still a theoretical race — but that's a much
# narrower window than the previous no-lock state, and every write here is
# preceded by a backup (see _backup_file_once).
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
    """Does this YAML text carry a tag the rewrite pipeline must refuse?

    Decision D-13 (b): a file containing ``!include`` or ``!secret`` is
    never rewritten. The platform behavior that makes this necessary was
    verified against core 2026.2.3 (work plan section 6.1): ``load_yaml``
    without a Secrets object raises HomeAssistantError ("Secrets not
    supported in this YAML file") on ``!secret``, so such a file fails
    loudly and nothing is written; ``!include`` is worse, because it is
    resolved at load time and a write-back would INLINE the included
    content into the parent file, destroying the include structure. The
    check is a plain text scan, so a quoted literal "!include" in, say,
    an alias also refuses the file; over-refusing is safe, silently
    inlining an include is not.
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

    The directory is created (and re-chmodded, migrating any existing
    wider-mode directory) 0o700 and the file is opened 0o600, matching
    the audit store's file-mode posture: the previous config of a
    dashboard or helper is operator data, not world-readable data. A
    serialization failure propagates so the caller skips the rewrite; a
    rewrite must never proceed without its backup on disk.
    """
    os.makedirs(dir_path, mode=0o700, exist_ok=True)
    os.chmod(dir_path, 0o700)
    # A url_path is a slug and an entry_id is hex, so the separator strip
    # is defense in depth, not an expected code path.
    safe_stem = stem.replace(os.sep, "_")
    path = os.path.join(dir_path, f"{safe_stem}-{stamp}.json")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
    os.chmod(path, 0o600)
    return path


def _prune_backups_sync(dir_path: str) -> None:
    """Delete remap backups older than the retention period; sync,
    executor-only. Runs at the start of every apply so the directory is
    bounded by use, without a background timer to maintain.
    """
    if not os.path.isdir(dir_path):
        return
    cutoff = time.time() - _BACKUP_RETENTION_DAYS * 24 * 3600
    for name in os.listdir(dir_path):
        path = os.path.join(dir_path, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            # A file that vanished or resists deletion must not block the
            # apply that triggered the pruning pass.
            continue

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
    """Exact match in dict KEY position (a scene-style ``entities:`` map
    keys on entity_ids). _exact_replace never renames a key, so a key-only
    hit is reported detect-only rather than promised as fixable."""
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
        # Re-check D-13 (b) taint on the raw text inside the lock: the
        # find step already marked a tainted file's items non-editable,
        # but the file can change between find and apply, and a load of
        # an !include here would hand back content that a write would
        # inline. Raising turns that race into a reported per-item error
        # with nothing written. See _yaml_text_tainted for the verified
        # !secret/!include load behavior.
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
    """Scenes are id-based like automations, but the entity_id lives as a
    DICT KEY under `entities:` (`{sensor.old: "on"}`), not a value — the
    generic exact-value walker can't rename a key, so this handles that
    one field specially and reuses the same read/write primitives."""
    from homeassistant.const import CONF_ID
    from homeassistant.util.file import write_utf8_file_atomic

    def _read() -> Any:
        # Same in-lock D-13 (b) taint re-check as _apply_yaml_list_fix,
        # for the same find-to-apply race.
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

        # Collision: the scene already configures state for new_id too.
        # Silently overwriting new_id's existing state would be data loss,
        # so refuse and let the caller surface it rather than clobbering.
        if new_id in entities:
            raise ValueError(
                f"scene {config_id!r} already has state for {new_id!r}; "
                "remapping would overwrite it"
            )

        entities[new_id] = entities.pop(old_id)
        await _backup_file_once(hass, path, stamp, backed_up)
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
        value_hit = _contains_exact_value(loaded, entity_id)
        key_hit = _contains_exact_key(loaded, entity_id)
        if not value_hit and not key_hit:
            continue
        # A dict-KEY occurrence is detect-only: _exact_replace rewrites
        # values, never keys, so promising a fix for a key-only hit would
        # be a silent no-op at apply time. When values and keys both hit,
        # the values are fixed and the remaining key occurrence is called
        # out so the operator knows the fix is partial.
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
        # Work plan item 1.9: snapshot the previous config before the save.
        # _exact_replace builds new containers rather than mutating, so
        # ``loaded`` still holds the pre-rewrite state here. A backup
        # failure raises and the save never happens.
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


# -- Helpers (config-entry-backed) -------------------------------------------


def _find_helper_refs(hass: HomeAssistant, entity_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries():
        matched = False

        # Helpers created through the UI store their source fields in
        # entry.options; imported or older entries can carry the same
        # fields in entry.data instead (work plan item 1.9), so both
        # mappings are checked structurally.
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

        # Allowlisted detect-only fallback (work plan item SEC-4). Only
        # the locator fields in const.INTEGRATION_LOCATOR_KEYS are read;
        # credentials in other integrations' entries are deliberately
        # never read, so a mention that only exists inside a password no
        # longer matches, and that is correct. This fallback also runs
        # for helper domains whose structural fields did not match, so a
        # helper whose locator field holds a template (rather than a bare
        # entity_id) is still surfaced for manual review instead of being
        # skipped by the structural check above.
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

    # Item 1.9 reads entry.data as well as entry.options: whichever
    # mapping holds the structural field gets the rewrite. Pristine
    # copies for the backup are taken before rewriting; _rewritten only
    # reassigns top-level slots, so the shallow copies stay intact.
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

    # Work plan item 1.9: snapshot the previous entry state before the
    # update. The snapshot carries both mappings because this same item
    # extends rewriting into entry.data. A backup failure raises and the
    # entry is never updated.
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


def _mark_manual_for_taint(items: list[dict[str, Any]]) -> None:
    """Decision D-13 (b): every item from a tainted YAML file becomes
    detect-only with the one prescribed reason, whatever it was before."""
    for item in items:
        item["editable"] = False
        item["reason"] = YAML_TAINT_REASON


async def async_find_references(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Everything referencing entity_id, grouped by kind, for the Entity
    ReMap page's preview. Every item is labeled editable/not — nothing here
    implies a fix will happen until async_apply_remap is actually called."""
    from homeassistant.config import (
        AUTOMATION_CONFIG_PATH,
        SCENE_CONFIG_PATH,
        SCRIPT_CONFIG_PATH,
    )

    automation_path = hass.config.path(AUTOMATION_CONFIG_PATH)
    script_path = hass.config.path(SCRIPT_CONFIG_PATH)
    scene_path = hass.config.path(SCENE_CONFIG_PATH)

    # D-13 (b) taint check on the raw text, BEFORE any load_yaml: a file
    # with !secret would make load_yaml raise, and one with !include
    # would load with the include silently resolved (see
    # _yaml_text_tainted). A tainted file's item ids are unknowable
    # without loading it, so its known-ids set stays empty and every item
    # for that kind is marked manual below.
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

    This bulk-rewrites production automations, scripts, scenes, dashboards,
    and helper config in one pass, so — matching the firewall feature's own
    safety pattern — it refuses to run unless the caller has acknowledged
    that a backup will be taken. Every write is preceded by a backup: each
    YAML config file is copied aside (``<file>.ha_soc-<timestamp>.bak``)
    before its first rewrite, and each storage dashboard and helper entry
    gets a pre-rewrite JSON snapshot under ``.storage/ha_soc_remap/`` (work
    plan item 1.9). All backup paths come back in the result's ``backups``
    list, and backups older than 30 days are pruned at the start of each
    apply. A server-side gate, not a client-only one.
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
    # Millisecond stamp (work plan item 4.14) so two applies inside the
    # same second cannot collide on a backup filename.
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

    # Reload once per domain after the loop, not once per item. The
    # script.reload and scene.reload services are registered with an
    # EMPTY schema (verified against core 2026.2.3, work plan section
    # 6.1), so these calls must carry no data; automation.reload above
    # stays per-item with {"id": ...}, which core's schema
    # (vol.Schema({vol.Optional(CONF_ID): str})) accepts and which is
    # the cheaper call.
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
        # Structural helper fields can live in entry.options or, for
        # imported/older entries, entry.data (work plan item 1.9). The
        # per-entry set de-duplicates a value present in both mappings.
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
