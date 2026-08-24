"""Tests for per-container CPU/memory resource collection.

Never touches a real Supervisor: get_supervisor_client / get_supervisor_info
are patched. Pins the not-Supervisor degradation, the on-demand stat fetch
(only for started add-ons), the high-memory/high-cpu flagging, and the
suspicious-first sort.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.containers import async_container_resources


def _stats(cpu, mem_pct, mem_usage=100, mem_limit=1000):
    return SimpleNamespace(
        cpu_percent=cpu,
        memory_usage=mem_usage,
        memory_limit=mem_limit,
        memory_percent=mem_pct,
        network_rx=1,
        network_tx=2,
        blk_read=3,
        blk_write=4,
    )


async def test_not_supervisor(hass: HomeAssistant) -> None:
    out = await async_container_resources(hass)
    assert out["available"] is False
    assert out["reason"] == "not_supervisor"
    assert out["containers"] == []


async def test_resources_flags_and_sort(hass: HomeAssistant) -> None:
    hass.config.components.add("hassio")

    supervisor_info = {
        "addons": [
            {"slug": "crashy", "name": "Crashy Add-on", "state": "started", "update_available": False},
            {"slug": "idle", "name": "Idle Add-on", "state": "stopped", "update_available": True},
        ]
    }

    addon_stats = {"crashy": _stats(cpu=20.0, mem_pct=95.0)}
    client = MagicMock()
    client.addons.addon_stats = AsyncMock(side_effect=lambda slug: addon_stats[slug])
    client.homeassistant.stats = AsyncMock(return_value=_stats(cpu=10.0, mem_pct=30.0))
    client.supervisor.stats = AsyncMock(return_value=_stats(cpu=5.0, mem_pct=15.0))

    with (
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
        patch("homeassistant.components.hassio.get_supervisor_info", return_value=supervisor_info),
    ):
        out = await async_container_resources(hass)

    assert out["available"] is True
    by_slug = {c["slug"]: c for c in out["containers"]}
    assert set(by_slug) == {"crashy", "idle", "core", "supervisor"}

    # High-memory add-on flagged and sorted to the very top.
    assert out["containers"][0]["slug"] == "crashy"
    assert "high_memory" in by_slug["crashy"]["flags"]
    assert by_slug["crashy"]["memory_percent"] == 95.0

    # Stopped add-on: flagged not_running, and no stats call was made for it.
    assert "not_running" in by_slug["idle"]["flags"]
    assert by_slug["idle"]["cpu_percent"] is None
    client.addons.addon_stats.assert_awaited_once_with("crashy")

    # Core + Supervisor always present, unflagged here.
    assert by_slug["core"]["kind"] == "core"
    assert by_slug["supervisor"]["kind"] == "supervisor"
    assert by_slug["core"]["flags"] == []


async def test_ws_handler_returns_result(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_containers_resources

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="u1")
    ws_containers_resources(hass, connection, {"id": 1})
    await hass.async_block_till_done(wait_background_tasks=True)

    connection.send_error.assert_not_called()
    result = connection.send_result.call_args[0][1]
    assert "available" in result and "containers" in result
