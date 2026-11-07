"""One reader for the Home Assistant Marketplace and the HACS it replaces.

Home Assistant 2026.11 ships HACS as the built-in Marketplace integration and
blocks the custom ``hacs`` integration. The manager object moved from
``hass.data["hacs"]`` to the ``runtime_data`` of the ``marketplace`` config
entry, the update entities moved to the ``marketplace`` platform, and the
repository list ``list_downloaded`` became ``list_installed``. Older cores
still run HACS, so every reader here accepts both shapes and returns None or
an empty list when neither is present.

Verified against core 2026.11.0: components/marketplace/__init__.py
(``config_entry.runtime_data = MarketplaceManager``), base.py
(``Repositories.list_all``, ``list_installed``, ``is_default``) and
repositories/base.py (``RepositoryData`` fields).
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

MARKETPLACE_DOMAIN = "marketplace"
HACS_DOMAIN = "hacs"

# Update entity platforms, newest first. The unique id is the repository id on both.
UPDATE_PLATFORMS = (MARKETPLACE_DOMAIN, HACS_DOMAIN)

# Dashboard resource prefixes. The Marketplace serves /local/community/; the
# old /hacsfiles/ path keeps working, so a resource under either one is loaded.
HACSFILES_PREFIX = "/hacsfiles/"
COMMUNITY_PREFIX = "/local/community/"


def get_manager(hass: HomeAssistant) -> Any | None:
    """The Marketplace manager, else the legacy HACS object, else None."""
    for entry in hass.config_entries.async_entries(MARKETPLACE_DOMAIN):
        manager = getattr(entry, "runtime_data", None)
        if manager is not None:
            return manager
    return hass.data.get(HACS_DOMAIN)


def manager_label(hass: HomeAssistant) -> str:
    """Name to show in messages: Marketplace when it is loaded, else HACS."""
    return "Marketplace" if MARKETPLACE_DOMAIN in hass.config.components else "HACS"


def installed_repositories(manager: Any) -> list[Any]:
    """Installed repositories. Raises AttributeError when neither list exists."""
    repositories = manager.repositories
    if hasattr(repositories, "list_installed"):
        return list(repositories.list_installed)
    return list(repositories.list_downloaded)


def is_default_repository(manager: Any, repo: Any) -> bool:
    """True for a repository from the default catalog, False for a custom one."""
    data = getattr(repo, "data", None)
    checker = getattr(manager.repositories, "is_default", None)
    if callable(checker) and data is not None:
        try:
            return bool(checker(data.id))
        except Exception:  # noqa: BLE001 - internals are not a stable API
            pass
    return bool(getattr(data, "default", False)) or bool(getattr(repo, "is_default", False))


def update_entity_id(hass: HomeAssistant, repo: Any) -> str | None:
    """The update entity of a repository, whichever platform registered it."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    for platform in UPDATE_PLATFORMS:
        entity_id = registry.async_get_entity_id("update", platform, str(repo.data.id))
        if entity_id:
            return entity_id
    return None


def resource_markers(repo_name: str) -> tuple[str, str]:
    """URL fragments that show a dashboard resource loads this repository."""
    return f"{HACSFILES_PREFIX}{repo_name}/", f"{COMMUNITY_PREFIX}{repo_name}/"
