"""Tests for peripherals.py — USB/serial device visibility.

Mocks scan_serial_ports() (no real hardware in this sandbox) but exercises
the real by-id/realpath resolution logic against actual symlinks created
under tmp_path, and the real config-entry-substring assignment matching
against a real MockConfigEntry, rather than mocking those parts too.

peripherals.py imports scan_serial_ports/human_readable_device_name
*locally* inside the function (so it can degrade honestly if the usb
component is ever unavailable) — the same pattern health.py uses for its
Supervisor-dependent checks. That means patches must target the source
module (homeassistant.components.usb[.utils]), not peripherals.py's own
namespace: a local `from X import Y` re-resolves Y from X on every call.
"""
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.usb.models import USBDevice
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.peripherals import async_peripheral_overview, async_set_peripheral_ignored
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


def _usb_device(device: str, *, vid="0403", pid="6001", serial="ABC123", manufacturer="FTDI", description="FT232R USB UART") -> USBDevice:
    return USBDevice(
        device=device, vid=vid, pid=pid, serial_number=serial, manufacturer=manufacturer, description=description
    )


async def test_no_devices_found(hass: HomeAssistant, store: HaSocData) -> None:
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[]):
        overview = await async_peripheral_overview(hass, store)
    assert overview == {"available": True, "devices": [], "total_count": 0, "unassigned_count": 0}


async def test_unassigned_device_is_flagged(hass: HomeAssistant, store: HaSocData) -> None:
    device = _usb_device("/dev/ttyUSB0")
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)

    assert overview["total_count"] == 1
    assert overview["unassigned_count"] == 1
    row = overview["devices"][0]
    assert row["tty_path"] == "/dev/ttyUSB0"
    assert row["assigned_integration"] is None
    assert row["ignored"] is False
    assert "FT232R USB UART" in row["raw_name"]
    assert row["key"] == "0403:6001:ABC123"


async def test_device_matched_to_owning_integration(hass: HomeAssistant, store: HaSocData) -> None:
    entry = MockConfigEntry(domain="zwave_js", data={"usb_path": "/dev/ttyUSB0"}, title="Z-Wave")
    entry.add_to_hass(hass)

    device = _usb_device("/dev/ttyUSB0")
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)

    assert overview["unassigned_count"] == 0
    row = overview["devices"][0]
    assert row["assigned_integration"] == {"entry_id": entry.entry_id, "domain": "zwave_js", "title": "Z-Wave"}


async def test_by_id_symlink_resolved_to_real_tty_path(hass: HomeAssistant, store: HaSocData, tmp_path) -> None:
    # Real symlink on disk, exactly like /dev/serial/by-id/usb-FTDI... -> ../../ttyUSB0,
    # so os.path.realpath() genuinely resolves it rather than being mocked.
    tty_dir = tmp_path / "dev"
    tty_dir.mkdir()
    tty_node = tty_dir / "ttyUSB0"
    tty_node.write_text("")
    by_id_dir = tmp_path / "dev" / "serial" / "by-id"
    by_id_dir.mkdir(parents=True)
    by_id_link = by_id_dir / "usb-FTDI_FT232R-if00-port0"
    by_id_link.symlink_to(tty_node)

    device = _usb_device(str(by_id_link))
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)

    row = overview["devices"][0]
    assert row["tty_path"] == str(tty_node)
    assert row["by_id_path"] == str(by_id_link)


async def test_ignoring_a_device_removes_it_from_unassigned_count(hass: HomeAssistant, store: HaSocData) -> None:
    device = _usb_device("/dev/ttyUSB0")
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        before = await async_peripheral_overview(hass, store)
    assert before["unassigned_count"] == 1
    key = before["devices"][0]["key"]

    async_set_peripheral_ignored(store, key, True, by_user_id="u1", raw_name="FT232R USB UART")

    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        after = await async_peripheral_overview(hass, store)
    assert after["unassigned_count"] == 0
    assert after["devices"][0]["ignored"] is True

    async_set_peripheral_ignored(store, key, False, by_user_id="u1", raw_name="FT232R USB UART")
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        restored = await async_peripheral_overview(hass, store)
    assert restored["unassigned_count"] == 1
    assert restored["devices"][0]["ignored"] is False


async def test_serial_device_without_vid_pid_does_not_crash(hass: HomeAssistant, store: HaSocData) -> None:
    # A real, dynamically-confirmed HA core behavior change: newer
    # scan_serial_ports() versions (backed by the `serialx` library)
    # return a USBDevice | SerialDevice union — native/platform serial
    # ports with no USB vendor/product descriptor come back as
    # SerialDevice, which has no vid/pid attributes at all. The installed
    # HA core in this dev venv predates that split (USBDevice only), so
    # this uses a duck-typed stand-in matching the real SerialDevice shape
    # (device, resolved_device, serial_number, manufacturer, description,
    # interface_description, interface_num — confirmed against HA core's
    # actual homeassistant/components/usb/models.py) rather than the real
    # class, which genuinely isn't importable here yet.
    serial_device = SimpleNamespace(
        device="/dev/ttyS0",
        resolved_device="/dev/ttyS0",
        serial_number=None,
        manufacturer=None,
        description=None,
        interface_description=None,
        interface_num=None,
    )
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[serial_device]):
        overview = await async_peripheral_overview(hass, store)

    assert overview["total_count"] == 1
    row = overview["devices"][0]
    assert row["vid"] is None
    assert row["pid"] is None
    assert row["key"] == "native:/dev/ttyS0"
    assert row["tty_path"] == "/dev/ttyS0"


async def test_resolved_device_field_used_when_present(hass: HomeAssistant, store: HaSocData) -> None:
    # Newer HA core computes the realpath itself (resolved_device) rather
    # than this module doing its own os.path.realpath — verify it's used
    # directly instead of falling back to the realpath computation.
    device = SimpleNamespace(
        device="/dev/serial/by-id/usb-FTDI_FT232R-if00-port0",
        resolved_device="/dev/ttyUSB0",
        vid="0403",
        pid="6001",
        serial_number="ABC123",
        manufacturer="FTDI",
        description="FT232R USB UART",
    )
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)

    row = overview["devices"][0]
    assert row["tty_path"] == "/dev/ttyUSB0"
    assert row["by_id_path"] == "/dev/serial/by-id/usb-FTDI_FT232R-if00-port0"
    assert row["key"] == "0403:6001:ABC123"


async def test_peripherals_reads_only_locator_keys(hass: HomeAssistant, store: HaSocData) -> None:
    # SEC-4: the device path appearing inside credential values must never
    # produce a match; only INTEGRATION_LOCATOR_KEYS values are read out
    # of another integration's config entry.
    secret_entry = MockConfigEntry(
        domain="evil_cloud",
        title="Cloudy",
        data={"password": "x-/dev/ttyUSB0-x"},
        options={"token": "/dev/ttyUSB0"},
    )
    secret_entry.add_to_hass(hass)

    device = _usb_device("/dev/ttyUSB0")
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)
    assert overview["devices"][0]["assigned_integration"] is None
    assert overview["unassigned_count"] == 1

    # A locator-key value still matches (behavior parity), including one
    # nested under another locator key.
    owner = MockConfigEntry(domain="zwave_js", title="Z-Wave", data={"device": {"path": "/dev/ttyUSB0"}})
    owner.add_to_hass(hass)
    with patch("homeassistant.components.usb.utils.scan_serial_ports", return_value=[device]):
        overview = await async_peripheral_overview(hass, store)
    assert overview["devices"][0]["assigned_integration"] == {
        "entry_id": owner.entry_id,
        "domain": "zwave_js",
        "title": "Z-Wave",
    }


async def test_usb_component_unavailable_degrades_honestly(hass: HomeAssistant, store: HaSocData) -> None:
    # Simulate the `usb` component genuinely not being importable (e.g. its
    # aiousbwatcher/pyserial requirements missing) by blanking the module
    # out of sys.modules — a standard technique to force the next `from X
    # import Y` to raise ImportError, exercising the real except branch
    # rather than one only reachable by mocking peripherals.py itself.
    with patch.dict(sys.modules, {"homeassistant.components.usb": None, "homeassistant.components.usb.utils": None}):
        overview = await async_peripheral_overview(hass, store)
    assert overview == {"available": False, "devices": [], "total_count": 0, "unassigned_count": 0}
