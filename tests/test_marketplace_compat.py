"""Tests for marketplace_compat.py: the Marketplace of core 2026.11 and legacy HACS.

The Marketplace is faked at the shape core 2026.11.0 uses: a manager in the
``runtime_data`` of a ``marketplace`` config entry, ``repositories.list_installed``
and ``repositories.is_default``, and update entities on the ``marketplace``
platform. Legacy HACS keeps ``hass.data["hacs"]`` and ``list_downloaded``.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import hacs_updates as hu
from custom_components.ha_soc import marketplace_compat as mc
from custom_components.ha_soc import unused_installs as ui
from tests.test_unused_installs import _install_lovelace


def _manager(*, default_ids: tuple[int, ...] = ()) -> SimpleNamespace:
    repo = SimpleNamespace(
        data=SimpleNamespace(
            id=7, full_name="someone/ha-thing", category="integration", domain="thing", installed=True
        )
    )
    repositories = SimpleNamespace(
        list_installed=[repo],
        list_all=[repo],
        is_default=lambda repo_id: repo_id in default_ids,
    )
    return SimpleNamespace(repositories=repositories, system=SimpleNamespace(disabled=False))


def _add_marketplace(hass: HomeAssistant, manager: object) -> MockConfigEntry:
    entry = MockConfigEntry(domain=mc.MARKETPLACE_DOMAIN)
    entry.add_to_hass(hass)
    entry.runtime_data = manager
    return entry


async def test_get_manager_prefers_marketplace_over_hacs(hass: HomeAssistant) -> None:
    manager = _manager()
    _add_marketplace(hass, manager)
    hass.data["hacs"] = object()
    assert mc.get_manager(hass) is manager


async def test_get_manager_falls_back_to_hacs(hass: HomeAssistant) -> None:
    legacy = object()
    hass.data["hacs"] = legacy
    assert mc.get_manager(hass) is legacy


async def test_get_manager_none_when_neither(hass: HomeAssistant) -> None:
    assert mc.get_manager(hass) is None
    assert mc.manager_label(hass) == "HACS"


def test_installed_repositories_uses_list_installed_then_list_downloaded() -> None:
    new = _manager()
    assert len(mc.installed_repositories(new)) == 1
    old = SimpleNamespace(repositories=SimpleNamespace(list_downloaded=["a", "b"]))
    assert mc.installed_repositories(old) == ["a", "b"]
    with pytest.raises(AttributeError):
        mc.installed_repositories(SimpleNamespace(repositories=SimpleNamespace()))


def test_is_default_repository_uses_catalog_lookup() -> None:
    manager = _manager(default_ids=(7,))
    repo = manager.repositories.list_all[0]
    assert mc.is_default_repository(manager, repo) is True
    assert mc.is_default_repository(_manager(), repo) is False


async def test_update_entity_id_finds_marketplace_and_hacs_platforms(hass: HomeAssistant) -> None:
    registry = er.async_get(hass)
    registry.async_get_or_create("update", "marketplace", "7", suggested_object_id="thing")
    registry.async_get_or_create("update", "hacs", "8", suggested_object_id="old")
    assert mc.update_entity_id(hass, SimpleNamespace(data=SimpleNamespace(id=7))) == "update.thing"
    assert mc.update_entity_id(hass, SimpleNamespace(data=SimpleNamespace(id=8))) == "update.old"
    assert mc.update_entity_id(hass, SimpleNamespace(data=SimpleNamespace(id=9))) is None


async def test_hacs_updates_reads_marketplace_manager(hass: HomeAssistant) -> None:
    manager = _manager()
    _add_marketplace(hass, manager)
    assert hu._hacs(hass) is manager
    assert [r.data.id for r in hu._downloaded(manager)] == [7]


async def test_hacs_updates_message_names_the_marketplace(hass: HomeAssistant) -> None:
    hass.config.components.add(mc.MARKETPLACE_DOMAIN)
    with pytest.raises(hu.HacsUnavailable, match="Marketplace is not installed"):
        hu._hacs(hass)


async def test_unused_installs_reads_marketplace_and_community_path(hass: HomeAssistant) -> None:
    repo = SimpleNamespace(
        data=SimpleNamespace(
            installed=True, full_name="someone/used-card", category="plugin", domain=None, file_name="used-card.js"
        )
    )
    stale = SimpleNamespace(
        data=SimpleNamespace(
            installed=True, full_name="someone/stale-card", category="plugin", domain=None, file_name="stale-card.js"
        )
    )
    _add_marketplace(hass, SimpleNamespace(repositories=SimpleNamespace(list_all=[repo, stale])))
    _install_lovelace(hass, {}, ["/local/community/used-card/used-card.js?v=1"])
    found = await ui.async_hacs_not_loaded(hass)
    assert [f["full_name"] for f in found] == ["someone/stale-card"]


def test_resource_markers_cover_both_prefixes() -> None:
    assert mc.resource_markers("x") == ("/hacsfiles/x/", "/local/community/x/")
