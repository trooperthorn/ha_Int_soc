"""Tests for logs.py's container (add-on / Core / Supervisor / host) log access.

The Supervisor is never present in this harness, so the transport is faked at
the same boundary logs.py uses for the real thing: hass.data[DATA_COMPONENT]
.send_command. What these tests pin down is the part that must not regress:
slug validation against the Supervisor's own add-on list (the slug is
interpolated into a Supervisor URL), ANSI stripping, and the tail-cap.
"""
from types import SimpleNamespace

import pytest

from homeassistant.components.hassio.const import DATA_COMPONENT
from homeassistant.core import HomeAssistant

from custom_components.ha_soc import logs as logs_mod
from custom_components.ha_soc.logs import (
    async_container_log_targets,
    async_fetch_container_log,
)


class _FakeHassio:
    """Stands in for the hassio component's HassIO handler."""

    def __init__(self, text="line one\nline two\n", raises=None):
        self.text = text
        self.raises = raises
        self.calls: list[str] = []

    async def send_command(self, path, method="get", return_text=False, timeout=None):
        self.calls.append(path)
        if self.raises is not None:
            raise self.raises
        return self.text


@pytest.fixture
def supervisor(hass: HomeAssistant, monkeypatch):
    """A pretend Supervisor install with two add-ons."""
    hass.config.components.add("hassio")
    fake = _FakeHassio()
    hass.data[DATA_COMPONENT] = fake
    monkeypatch.setattr(
        logs_mod,
        "_addons_by_slug",
        lambda _hass: {"a0d7b954_zwavejs": "Z-Wave JS UI", "core_mosquitto": "Mosquitto broker"},
    )
    return fake


async def test_targets_unavailable_without_supervisor(hass: HomeAssistant) -> None:
    result = await async_container_log_targets(hass)
    assert result == {"available": False, "targets": []}


async def test_targets_list_system_then_addons_sorted_by_name(
    hass: HomeAssistant, supervisor
) -> None:
    result = await async_container_log_targets(hass)
    assert result["available"] is True
    ids = [t["id"] for t in result["targets"]]
    # System targets first, then add-ons ordered by display name
    # (Mosquitto before Z-Wave), not by slug.
    assert ids == [
        "core",
        "supervisor",
        "host",
        "addon:core_mosquitto",
        "addon:a0d7b954_zwavejs",
    ]


async def test_fetch_refused_without_supervisor(hass: HomeAssistant) -> None:
    result = await async_fetch_container_log(hass, "core")
    assert result["available"] is False
    assert "Supervisor" in result["error"]


async def test_fetch_rejects_unknown_target_and_uninstalled_slug(
    hass: HomeAssistant, supervisor
) -> None:
    for bad in ("nonsense", "addon:../../supervisor", "addon:not_installed"):
        result = await async_fetch_container_log(hass, bad)
        assert result["available"] is False, bad
        assert result["error"], bad
    # Nothing may reach the Supervisor for a rejected target.
    assert supervisor.calls == []


async def test_fetch_system_and_addon_paths(hass: HomeAssistant, supervisor) -> None:
    for target, path in (
        ("core", "/core/logs"),
        ("supervisor", "/supervisor/logs"),
        ("host", "/host/logs"),
        ("addon:core_mosquitto", "/addons/core_mosquitto/logs"),
    ):
        result = await async_fetch_container_log(hass, target)
        assert result["available"] is True, target
        assert supervisor.calls[-1] == path


async def test_fetch_strips_ansi_colors(hass: HomeAssistant, supervisor) -> None:
    supervisor.text = "\x1b[32mINFO\x1b[0m started\n\x1b[31mERROR\x1b[0m boom\n"
    result = await async_fetch_container_log(hass, "core")
    assert result["content"] == "INFO started\nERROR boom\n"


async def test_fetch_tail_caps_on_line_boundary(hass: HomeAssistant, supervisor) -> None:
    supervisor.text = "OLD-MARKER\n" + ("x" * 200_000) + "\nNEW-MARKER\n"
    result = await async_fetch_container_log(hass, "core")
    assert result["truncated"] is True
    assert "NEW-MARKER" in result["content"]
    assert "OLD-MARKER" not in result["content"]
    # The cap cuts at a newline so the first kept line is whole, which for
    # this input means the torn run of x's is dropped entirely.
    assert result["content"].startswith("NEW-MARKER")


async def test_fetch_failure_is_reported_not_raised(hass: HomeAssistant, supervisor) -> None:
    supervisor.raises = OSError("Supervisor unreachable")
    result = await async_fetch_container_log(hass, "supervisor")
    assert result["available"] is False
    assert "Supervisor unreachable" in result["error"]


async def test_fetch_non_text_response_is_an_error(hass: HomeAssistant, supervisor) -> None:
    async def _send(path, method="get", return_text=False, timeout=None):
        return {"unexpected": "json"}

    hass.data[DATA_COMPONENT] = SimpleNamespace(send_command=_send)
    result = await async_fetch_container_log(hass, "core")
    assert result["available"] is False
    assert "non-text" in result["error"]
