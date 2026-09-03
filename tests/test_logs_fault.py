"""Tests for logs.py's home-assistant.log.fault reader."""
import os

import pytest

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.logs import async_fault_log_overview


@pytest.fixture(autouse=True)
def _no_fault_log_leaks_between_tests(hass: HomeAssistant):
    # The harness config dir is not fresh per test; clean up before and after so the fault file never leaks.
    path = hass.config.path("home-assistant.log.fault")
    if os.path.exists(path):
        os.remove(path)
    yield
    if os.path.exists(path):
        os.remove(path)


async def test_missing_fault_log_reports_no_crash(hass: HomeAssistant) -> None:
    overview = await async_fault_log_overview(hass)
    assert overview == {
        "exists": False,
        "content": None,
        "size_bytes": 0,
        "modified_at": None,
        "truncated": False,
    }


async def test_existing_fault_log_is_read(hass: HomeAssistant) -> None:
    path = hass.config.path("home-assistant.log.fault")
    with open(path, "w") as f:
        f.write("Fatal Python error: Segmentation fault\n\nThread 0x1234 (most recent call first):\n")

    overview = await async_fault_log_overview(hass)

    assert overview["exists"] is True
    assert "Segmentation fault" in overview["content"]
    assert overview["size_bytes"] > 0
    assert overview["modified_at"] is not None
    assert overview["truncated"] is False


async def test_large_fault_log_is_truncated_to_tail(hass: HomeAssistant) -> None:
    path = hass.config.path("home-assistant.log.fault")
    with open(path, "w") as f:
        f.write("OLD-CRASH-MARKER\n")
        f.write("x" * (70 * 1024))
        f.write("\nNEW-CRASH-MARKER\n")

    overview = await async_fault_log_overview(hass)

    assert overview["truncated"] is True
    assert "NEW-CRASH-MARKER" in overview["content"]
    assert "OLD-CRASH-MARKER" not in overview["content"]
