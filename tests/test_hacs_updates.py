"""Tests for hacs_updates.py and the ha_soc/hacs/* commands.

HACS is never installed in this harness, so it is faked at the boundary the
module reads: ``hass.data["hacs"]`` with the attributes HACS's own refresh
command uses (``repositories.list_downloaded``, ``update_repository``,
``data.async_write``, ``coordinators``), an update entity in the registry
with platform ``hacs`` and the repository id as unique id, and a fake
``update.install`` service. What is pinned down: refresh is forced per
repository and one failure does not stop the rest, install goes only to
pending repositories through the entity, both actions are audited, a missing
or disabled HACS is reported rather than guessed, and the two writes are
owner-only.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er

from custom_components.ha_soc import hacs_updates as hu
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import (
    ws_hacs_refresh_all,
    ws_hacs_status,
    ws_hacs_update_all,
)


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> str:
    hass.config.config_dir = str(tmp_path)
    return str(tmp_path)


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _repo(repo_id: int, full_name: str, installed: str, available: str, *, category: str = "integration", fail: bool = False) -> Any:
    repo = SimpleNamespace(
        data=SimpleNamespace(id=repo_id, full_name=full_name, category=category, installed=True),
        display_installed_version=installed,
        display_available_version=available,
        update_repository=AsyncMock(side_effect=RuntimeError("github down") if fail else None),
    )
    # HACS derives pending_update from the two versions; the fake does the same.
    repo.pending_update = installed != available
    return repo


@pytest.fixture
def hacs(hass: HomeAssistant):
    """Three downloaded repositories: one pending, one current, one whose refresh fails."""
    repos = [
        _repo(101, "trooperthorn/ha_int_elkm1", "2026.09.05.1", "2026.09.06.1"),
        _repo(102, "trooperthorn/ha_int_davis", "2026.09.04.1", "2026.09.04.1"),
        _repo(103, "someone/broken", "1.0.0", "1.1.0", fail=True),
    ]
    coordinator = MagicMock()
    fake = SimpleNamespace(
        system=SimpleNamespace(disabled=False, disabled_reason=None),
        repositories=SimpleNamespace(list_downloaded=repos),
        data=SimpleNamespace(async_write=AsyncMock()),
        coordinators={"integration": coordinator},
    )
    hass.data["hacs"] = fake
    registry = er.async_get(hass)
    for repo in repos:
        entity_id = registry.async_get_or_create("update", "hacs", str(repo.data.id)).entity_id
        hass.states.async_set(
            entity_id,
            "on" if repo.pending_update else "off",
            {"installed_version": repo.display_installed_version, "latest_version": repo.display_available_version},
        )
    return fake


@pytest.fixture
def install_service(hass: HomeAssistant):
    """A fake update.install that records the entity ids it was asked for."""
    calls: list[str] = []

    async def _install(call: ServiceCall) -> None:
        calls.extend(call.data["entity_id"] if isinstance(call.data["entity_id"], list) else [call.data["entity_id"]])

    hass.services.async_register("update", "install", _install)
    return calls


def _connection(is_owner: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=is_owner, id="owner1")
    return connection


async def _call(hass: HomeAssistant, handler, connection: MagicMock, msg: dict) -> MagicMock:
    connection.send_result.reset_mock()
    connection.send_error.reset_mock()
    handler(hass, connection, msg)
    for _ in range(300):
        await hass.async_block_till_done()
        if connection.send_result.called or connection.send_error.called:
            return connection
        await asyncio.sleep(0.01)
    raise AssertionError(f"no reply to {msg['type']}")


async def test_status_without_hacs_is_honest(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = await _call(hass, ws_hacs_status, _connection(), {"id": 1, "type": "ha_soc/hacs/status"})
    status = connection.send_result.call_args[0][1]
    assert status["available"] is False
    assert "not installed" in status["reason"]
    assert status["repositories"] == [] and status["pending"] == 0


async def test_status_lists_downloaded_repositories_and_pending(hass: HomeAssistant, entry: MockConfigEntry, hacs) -> None:
    connection = await _call(hass, ws_hacs_status, _connection(), {"id": 1, "type": "ha_soc/hacs/status"})
    status = connection.send_result.call_args[0][1]
    assert status["available"] is True
    assert [r["full_name"] for r in status["repositories"]] == [
        "someone/broken",
        "trooperthorn/ha_int_davis",
        "trooperthorn/ha_int_elkm1",
    ]
    elk = next(r for r in status["repositories"] if r["id"] == "101")
    assert elk["pending_update"] is True
    assert elk["entity_id"] == "update.hacs_101"
    assert elk["entity_state"] == "on"
    assert status["pending"] == 2
    assert status["last_refresh"] is None


async def test_disabled_hacs_is_reported(hass: HomeAssistant, entry: MockConfigEntry, hacs) -> None:
    hacs.system.disabled = True
    hacs.system.disabled_reason = "rate_limit"
    connection = await _call(hass, ws_hacs_status, _connection(), {"id": 1, "type": "ha_soc/hacs/status"})
    assert "rate_limit" in connection.send_result.call_args[0][1]["reason"]
    connection = await _call(hass, ws_hacs_refresh_all, _connection(), {"id": 2, "type": "ha_soc/hacs/refresh_all"})
    assert connection.send_error.call_args[0][1] == "hacs_unavailable"


async def test_refresh_forces_every_repository_and_survives_a_failure(
    hass: HomeAssistant, entry: MockConfigEntry, hacs
) -> None:
    connection = await _call(hass, ws_hacs_refresh_all, _connection(), {"id": 1, "type": "ha_soc/hacs/refresh_all"})
    result = connection.send_result.call_args[0][1]
    assert sorted(result["refreshed"]) == ["trooperthorn/ha_int_davis", "trooperthorn/ha_int_elkm1"]
    assert result["failed"] == [{"full_name": "someone/broken", "error": "github down"}]
    assert sorted(result["pending_after"]) == ["someone/broken", "trooperthorn/ha_int_elkm1"]
    for repo in hacs.repositories.list_downloaded:
        repo.update_repository.assert_awaited_once_with(ignore_issues=True, force=True)
    hacs.data.async_write.assert_awaited_once()
    hacs.coordinators["integration"].async_update_listeners.assert_called_once()

    records = await entry.runtime_data.audit.async_query(category=hu.AUDIT_CATEGORY_REFRESH, limit=5)
    assert records and records[0]["detail"]["refreshed"] == 2
    assert records[0]["user_id"] == "owner1"
    assert entry.runtime_data.store.data["hacs_updates"]["last_refresh"] == result["at"]


async def test_update_installs_only_pending_through_the_entity(
    hass: HomeAssistant, entry: MockConfigEntry, hacs, install_service
) -> None:
    connection = await _call(hass, ws_hacs_update_all, _connection(), {"id": 1, "type": "ha_soc/hacs/update_all"})
    result = connection.send_result.call_args[0][1]
    assert sorted(install_service) == ["update.hacs_101", "update.hacs_103"]
    assert [i["full_name"] for i in result["installed"]] == ["someone/broken", "trooperthorn/ha_int_elkm1"]
    assert result["installed"][1] == {
        "full_name": "trooperthorn/ha_int_elkm1",
        "from": "2026.09.05.1",
        "to": "2026.09.06.1",
        "entity_id": "update.hacs_101",
    }
    assert result["failed"] == [] and result["skipped"] == []
    assert result["restart_needed"] is True
    records = await entry.runtime_data.audit.async_query(category=hu.AUDIT_CATEGORY_UPDATE, limit=5)
    assert records and len(records[0]["detail"]["installed"]) == 2


async def test_update_can_be_limited_to_named_repositories(
    hass: HomeAssistant, entry: MockConfigEntry, hacs, install_service
) -> None:
    connection = await _call(
        hass, ws_hacs_update_all, _connection(), {"id": 1, "type": "ha_soc/hacs/update_all", "repository_ids": ["101", "102"]}
    )
    result = connection.send_result.call_args[0][1]
    assert install_service == ["update.hacs_101"]
    assert result["skipped"] == [{"full_name": "trooperthorn/ha_int_davis", "reason": "no update pending"}]


async def test_a_failing_install_is_reported_per_repository(
    hass: HomeAssistant, entry: MockConfigEntry, hacs
) -> None:
    async def _install(call: ServiceCall) -> None:
        if call.data["entity_id"] == "update.hacs_103":
            raise RuntimeError("download failed")

    hass.services.async_register("update", "install", _install)
    connection = await _call(hass, ws_hacs_update_all, _connection(), {"id": 1, "type": "ha_soc/hacs/update_all"})
    result = connection.send_result.call_args[0][1]
    assert [i["full_name"] for i in result["installed"]] == ["trooperthorn/ha_int_elkm1"]
    assert result["failed"][0]["full_name"] == "someone/broken"
    assert "download failed" in result["failed"][0]["error"]


async def test_the_two_writes_are_owner_only(hass: HomeAssistant, entry: MockConfigEntry, hacs) -> None:
    admin = _connection(is_owner=False)
    for handler, msg in (
        (ws_hacs_refresh_all, {"type": "ha_soc/hacs/refresh_all"}),
        (ws_hacs_update_all, {"type": "ha_soc/hacs/update_all"}),
    ):
        with pytest.raises(Unauthorized):
            handler(hass, admin, {"id": 1, **msg})
    for repo in hacs.repositories.list_downloaded:
        repo.update_repository.assert_not_awaited()
