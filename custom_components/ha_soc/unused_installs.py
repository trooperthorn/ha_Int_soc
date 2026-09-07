"""Unused installs: code that is present on this instance but that nothing uses.

Every helper answers one question, reports only what it can prove, and
returns a HygieneResult so health.py can tell "nothing unused" from "could
not evaluate". Scope, limits, and the YAML scan trust boundary are in
docs/design.md and docs/security.md.
"""
from __future__ import annotations

import os
import re
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .config_hygiene import HygieneResult, _could_not_evaluate
from .integration_security import _scan_custom_components_sync

# Integration types that legitimately own no entity or device.
_ENTITYLESS_INTEGRATION_TYPES = frozenset({"system", "hardware", "service", "virtual"})

_CUSTOM_ELEMENT_DEFINE_RE = re.compile(
    r"""customElements\s*\.\s*define\s*\(\s*["']([a-z][a-z0-9._-]*)["']"""
)
# window.customCards.push({type: "my-card", ...}) registrations.
_CUSTOM_CARDS_TYPE_RE = re.compile(
    r"""customCards\s*\.\s*push\s*\(\s*\{[^}]*?\btype\s*:\s*["']([a-z][a-z0-9._-]*)["']""",
    re.DOTALL,
)
_CUSTOM_TYPE_PREFIX = "custom:"
_LOCAL_PREFIX = "/local/"
_HACSFILES_PREFIX = "/hacsfiles/"
_MAX_RESOURCE_BYTES = 8 * 1024 * 1024


async def async_integrations_without_entry(hass: HomeAssistant) -> HygieneResult:
    """Custom integrations on disk that no config entry, YAML block, or loaded
    integration's dependency list brings in."""
    from homeassistant.loader import async_get_integration

    custom_domains, _licenses = await hass.async_add_executor_job(
        _scan_custom_components_sync, hass.config.path("custom_components")
    )
    if not custom_domains:
        return HygieneResult()

    loaded: set[str] = set()
    for component in hass.config.components:
        # Legacy platforms register as "<platform_domain>.<integration>".
        loaded.add(component.rsplit(".", 1)[-1])
        loaded.add(component)
    entry_domains = {entry.domain for entry in hass.config_entries.async_entries()}

    required_by_loaded: set[str] = set()
    for domain in list(loaded):
        try:
            integration = await async_get_integration(hass, domain)
        except Exception:  # noqa: BLE001 - a domain we can't resolve constrains nothing
            continue
        required_by_loaded.update(integration.dependencies)
        required_by_loaded.update(integration.after_dependencies)

    found: list[dict[str, Any]] = []
    for domain in custom_domains:
        if domain in loaded or domain in entry_domains or domain in required_by_loaded:
            continue
        found.append(
            {
                "domain": domain,
                "reason": "no config entry, no YAML setup, and no loaded integration depends on it",
            }
        )
    return HygieneResult(found)


async def async_entries_without_entities_or_devices(hass: HomeAssistant) -> HygieneResult:
    """Loaded config entries that own neither an entity nor a device."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.loader import async_get_integration

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    found: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries():
        # A disabled or failed entry is a different finding, not an unused one.
        if entry.disabled_by is not None or entry.state is not ConfigEntryState.LOADED:
            continue
        try:
            integration = await async_get_integration(hass, entry.domain)
        except Exception:  # noqa: BLE001
            continue
        if integration.integration_type in _ENTITYLESS_INTEGRATION_TYPES:
            continue
        if er.async_entries_for_config_entry(entity_registry, entry.entry_id):
            continue
        if dr.async_entries_for_config_entry(device_registry, entry.entry_id):
            continue
        found.append(
            {
                "entry_id": entry.entry_id,
                "domain": entry.domain,
                "title": entry.title,
                "integration_type": integration.integration_type,
            }
        )
    return HygieneResult(found)


def _hacs_installed_repositories(hass: HomeAssistant) -> list[dict[str, Any]] | None:
    """Best-effort rows from HACS runtime data, or None when HACS is present
    but its internals are not readable. HACS attribute names are unverified
    against a local source; see docs/design.md."""
    hacs = hass.data.get("hacs")
    if hacs is None:
        return []
    try:
        repositories = hacs.repositories.list_all  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - HACS internals are not a stable API
        return None
    rows: list[dict[str, Any]] = []
    try:
        for repo in repositories:
            data = getattr(repo, "data", None)
            if data is None or not bool(getattr(data, "installed", False)):
                continue
            rows.append(
                {
                    "full_name": str(getattr(data, "full_name", "") or ""),
                    "category": str(getattr(data, "category", "") or ""),
                    "domain": getattr(data, "domain", None),
                    "file_name": getattr(data, "file_name", None),
                }
            )
    except Exception:  # noqa: BLE001
        return None
    return rows


async def _lovelace_resource_urls(hass: HomeAssistant) -> list[str] | None:
    """Every dashboard resource URL, or None when Lovelace's resources cannot be read."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    ll_data = hass.data.get(LOVELACE_DATA)
    if ll_data is None:
        return None
    resources = ll_data.resources
    if hasattr(resources, "loaded") and not resources.loaded:
        try:
            await resources.async_get_info()
        except Exception:  # noqa: BLE001
            return None
    return [str(item.get("url", "")) for item in resources.async_items()]


async def async_hacs_not_loaded(hass: HomeAssistant) -> HygieneResult:
    """HACS-managed downloads that Home Assistant never loads: integrations
    with no loaded domain, dashboard elements with no resource entry."""
    rows = _hacs_installed_repositories(hass)
    if rows is None:
        return _could_not_evaluate()
    if not rows:
        return HygieneResult()

    resource_urls = await _lovelace_resource_urls(hass)
    loaded = set(hass.config.components) | {
        entry.domain for entry in hass.config_entries.async_entries()
    }

    found: list[dict[str, Any]] = []
    for row in rows:
        category = row["category"]
        if category == "integration":
            domain = row["domain"]
            if domain and domain not in loaded:
                found.append({**row, "reason": "downloaded by HACS but not set up"})
        elif category == "plugin":
            if resource_urls is None:
                return _could_not_evaluate()
            repo_name = row["full_name"].rsplit("/", 1)[-1].lower()
            marker = f"{_HACSFILES_PREFIX}{repo_name}/"
            if repo_name and not any(marker in url.lower() for url in resource_urls):
                found.append({**row, "reason": "downloaded by HACS but no dashboard resource loads it"})
    return HygieneResult(found)


def _resource_path(hass: HomeAssistant, url: str) -> tuple[str, str] | None:
    """(file path, base directory) for a resource URL this instance serves
    from disk, or None for anything else."""
    clean = url.split("?", 1)[0]
    if clean.startswith(_LOCAL_PREFIX):
        base = hass.config.path("www")
        return hass.config.path("www", clean.removeprefix(_LOCAL_PREFIX)), base
    if clean.startswith(_HACSFILES_PREFIX):
        base = hass.config.path("www", "community")
        return hass.config.path("www", "community", clean.removeprefix(_HACSFILES_PREFIX)), base
    return None


def _defined_elements_sync(path: str, base: str) -> set[str] | None:
    """Custom element names a bundle registers, by static regex; None when the
    file is unreadable or outside its base directory."""
    real_base = os.path.realpath(base)
    real_path = os.path.realpath(path)
    if real_path != real_base and not real_path.startswith(real_base + os.sep):
        return None
    try:
        if os.path.getsize(real_path) > _MAX_RESOURCE_BYTES:
            return None
        with open(real_path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return None
    names = set(_CUSTOM_ELEMENT_DEFINE_RE.findall(text))
    names.update(_CUSTOM_CARDS_TYPE_RE.findall(text))
    return names


def _walk_custom_types(node: Any, out: set[str]) -> None:
    if isinstance(node, dict):
        value = node.get("type")
        if isinstance(value, str) and value.startswith(_CUSTOM_TYPE_PREFIX):
            out.add(value[len(_CUSTOM_TYPE_PREFIX):])
        for child in node.values():
            _walk_custom_types(child, out)
    elif isinstance(node, list):
        for child in node:
            _walk_custom_types(child, out)


async def async_used_custom_types(
    hass: HomeAssistant, *, scan_yaml: bool
) -> tuple[set[str], int, bool]:
    """(custom element types used by any dashboard, YAML dashboards skipped,
    every dashboard loaded). Only ``type`` values are read; a YAML dashboard
    is loaded through core's own loader and only when scan_yaml is on."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.dashboard import MODE_YAML

    ll_data = hass.data.get(LOVELACE_DATA)
    used: set[str] = set()
    if ll_data is None:
        return used, 0, False

    skipped = 0
    complete = True
    for config in ll_data.dashboards.values():
        if config.mode == MODE_YAML and not scan_yaml:
            skipped += 1
            continue
        try:
            loaded = await config.async_load(False)
        except Exception:  # noqa: BLE001 - an unloadable dashboard proves nothing about usage
            complete = False
            continue
        _walk_custom_types(loaded, used)
    return used, skipped, complete


async def async_unused_dashboard_resources(
    hass: HomeAssistant, *, scan_yaml: bool
) -> HygieneResult:
    """Dashboard resources served from this instance whose registered custom
    elements no dashboard references. The result carries ``undeterminable``
    (resources whose element names could not be read) and
    ``yaml_dashboards_skipped``; with any dashboard skipped or unloadable the
    status is could_not_evaluate, because absence of a reference is then not
    evidence."""
    resource_urls = await _lovelace_resource_urls(hass)
    if resource_urls is None:
        return _could_not_evaluate()

    used, skipped, complete = await async_used_custom_types(hass, scan_yaml=scan_yaml)

    found: list[dict[str, Any]] = []
    undeterminable: list[dict[str, Any]] = []
    for url in resource_urls:
        located = _resource_path(hass, url)
        if located is None:
            continue
        names = await hass.async_add_executor_job(_defined_elements_sync, *located)
        if not names:
            undeterminable.append({"url": url, "reason": "element names not statically determinable"})
            continue
        if names & used:
            continue
        found.append({"url": url, "elements": sorted(names), "reason": "no dashboard references these elements"})

    if skipped or not complete:
        result = _could_not_evaluate()
    else:
        result = HygieneResult(found)
    result.undeterminable = undeterminable  # type: ignore[attr-defined]
    result.yaml_dashboards_skipped = skipped  # type: ignore[attr-defined]
    return result
