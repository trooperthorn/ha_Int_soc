"""Tests for permissions.py's async_get_dashboard_config — specifically that
a dashboard registered but never actually saved (ConfigNotFound, a normal
state, not a failure) is handled quietly and doesn't propagate/crash.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.ha_soc.permissions import PermissionsMatrix
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def matrix(hass: HomeAssistant) -> PermissionsMatrix:
    store = HaSocData(hass)
    await store.async_load()
    return PermissionsMatrix(hass, store)


class _RaisingDashboardConfig:
    def __init__(self, error: Exception) -> None:
        self._error = error

    async def async_load(self, force: bool):
        raise self._error


async def test_config_not_found_returns_none_quietly(
    hass: HomeAssistant, matrix: PermissionsMatrix, caplog
) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA
    from homeassistant.components.lovelace.const import ConfigNotFound

    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: _RaisingDashboardConfig(ConfigNotFound())})

    with caplog.at_level(logging.DEBUG, logger="custom_components.ha_soc.permissions"):
        config = await matrix.async_get_dashboard_config(None)

    assert config is None
    # Handled as an expected, quiet state (debug), never the alarming
    # warning+traceback line — that's the exact thing a real user mistook
    # for a crash and reported.
    assert "has no saved configuration yet" in caplog.text
    assert "Failed to load dashboard config" not in caplog.text
    assert not any(record.levelno >= logging.WARNING for record in caplog.records)


async def test_other_home_assistant_error_returns_none_and_warns(
    hass: HomeAssistant, matrix: PermissionsMatrix, caplog
) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    hass.data[LOVELACE_DATA] = SimpleNamespace(
        dashboards={None: _RaisingDashboardConfig(HomeAssistantError("boom"))}
    )

    with caplog.at_level(logging.DEBUG, logger="custom_components.ha_soc.permissions"):
        config = await matrix.async_get_dashboard_config(None)

    assert config is None
    assert "Failed to load dashboard config" in caplog.text
    assert any(record.levelno >= logging.WARNING for record in caplog.records)


async def test_successful_load_returns_config(hass: HomeAssistant, matrix: PermissionsMatrix) -> None:
    from homeassistant.components.lovelace import LOVELACE_DATA

    class _Config:
        async def async_load(self, force: bool):
            return {"views": []}

    hass.data[LOVELACE_DATA] = SimpleNamespace(dashboards={None: _Config()})

    config = await matrix.async_get_dashboard_config(None)

    assert config == {"views": []}
