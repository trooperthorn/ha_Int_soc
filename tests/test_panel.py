"""Regression tests for the HA SOC panel registration lifecycle."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from custom_components.ha_soc import panel


class _FakeHass:
    """Small Home Assistant surface needed by panel.async_register_panel."""

    def __init__(self, register_static_paths: AsyncMock) -> None:
        self.data: dict[str, object] = {}
        self.http = SimpleNamespace(
            async_register_static_paths=register_static_paths,
        )

    async def async_add_executor_job(self, target, *args):
        return target(*args)


@pytest.fixture
def panel_mocks(monkeypatch):
    register_panel = AsyncMock()
    remove_panel = Mock()
    monkeypatch.setattr(panel.panel_custom, "async_register_panel", register_panel)
    monkeypatch.setattr(panel, "async_remove_panel", remove_panel)
    monkeypatch.setattr(panel, "_bundle_mtime_sync", lambda _path: 1_725_244_800.0)
    return register_panel, remove_panel


async def test_static_route_is_registered_once_across_reload(panel_mocks) -> None:
    register_panel, remove_panel = panel_mocks
    register_static_paths = AsyncMock()
    hass = _FakeHass(register_static_paths)

    await panel.async_register_panel(hass)
    await panel.async_unregister_panel(hass)
    await panel.async_register_panel(hass)

    register_static_paths.assert_awaited_once()
    assert register_panel.await_count == 2
    assert remove_panel.call_count == 3
    assert hass.data[panel._DATA_STATIC_PATH_REGISTERED] is True


async def test_existing_route_from_older_build_is_reused(panel_mocks) -> None:
    register_panel, _remove_panel = panel_mocks
    register_static_paths = AsyncMock(
        side_effect=RuntimeError(
            "Added route will never be executed, method GET is already registered"
        )
    )
    hass = _FakeHass(register_static_paths)

    await panel.async_register_panel(hass)

    register_panel.assert_awaited_once()
    assert hass.data[panel._DATA_STATIC_PATH_REGISTERED] is True


async def test_unrelated_static_route_failure_is_not_hidden(panel_mocks) -> None:
    register_panel, _remove_panel = panel_mocks
    register_static_paths = AsyncMock(side_effect=RuntimeError("router is frozen"))
    hass = _FakeHass(register_static_paths)

    with pytest.raises(RuntimeError, match="router is frozen"):
        await panel.async_register_panel(hass)

    register_panel.assert_not_awaited()
    assert panel._DATA_STATIC_PATH_REGISTERED not in hass.data
