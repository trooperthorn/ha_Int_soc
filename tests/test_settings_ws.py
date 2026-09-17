"""Tests for ha_soc/settings/get and ha_soc/settings/set.

Calls the sync wrappers directly against a fake connection (same approach
as test_access_control.py) rather than a full websocket_api HTTP
roundtrip. What needs proving here is that /set actually mutates the live
store, routes secret values into the private secret store (SEC-1), and
leaves entry.options alone (SEC-2), not the generic auth plumbing already
covered by test_access_control.py.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN, SYSLOG_FORMAT_CEF
from custom_components.ha_soc.websocket_api import (
    ws_containers_discover_candidates,
    ws_pihole_test_connection,
    ws_probe_restart,
    ws_settings_get,
    ws_settings_set,
    ws_technitium_test_connection,
    ws_unifi_network_test_connection,
    ws_unifi_protect_test_connection,
)


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner1")
    return connection


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_get_returns_live_settings(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_settings_get(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["scanner_enabled"] is True
    assert result["access_level"] == "owner_only"


async def test_set_updates_store_and_leaves_entry_options_empty(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The pre-SEC-2 build mirrored every save into entry.options; the
    mirror is gone, so a save changes the live store and nothing else."""
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/settings/set", "scanner_enabled": False, "evidence_retention_days": 400},
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["scanner_enabled"] is False
    assert entry.runtime_data.store.settings["evidence_retention_days"] == 400
    assert entry.options == {}

    result = connection.send_result.call_args[0][1]
    assert result["scanner_enabled"] is False


async def test_syslog_format_is_selectable_and_reported(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_settings_set(
        hass,
        connection,
        {
            "id": 1,
            "type": "ha_soc/settings/set",
            "syslog_format": SYSLOG_FORMAT_CEF,
        },
    )
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["syslog_format"] == SYSLOG_FORMAT_CEF
    result = connection.send_result.call_args[0][1]
    assert result["syslog_format"] == SYSLOG_FORMAT_CEF
    assert result["syslog_status"]["format"] == SYSLOG_FORMAT_CEF


async def test_set_with_no_changes_is_a_no_op_read(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    before = dict(entry.runtime_data.store.settings)

    ws_settings_set(hass, connection, {"id": 1, "type": "ha_soc/settings/set"})
    await hass.async_block_till_done()

    # The live store is untouched...
    assert entry.runtime_data.store.settings == before
    # ...and the returned view is the masked form (secrets never sent raw).
    result = connection.send_result.call_args[0][1]
    assert result["nvd_api_key"] in ("", "[redacted]")
    assert result["nvd_api_key_set"] is False
    assert result["github_token_set"] is False


async def test_external_connections_default_enabled_and_unstamped(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_settings_get(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["external_connections_enabled"] is True
    assert result["external_connections_changed_at"] is None


async def test_external_connections_toggle_stamps_changed_at(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()

    # Same value as the current default: no change, so no stamp.
    ws_settings_set(
        hass,
        connection,
        {"id": 1, "type": "ha_soc/settings/set", "external_connections_enabled": True},
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.store.settings["external_connections_changed_at"] is None

    # An actual flip is server-stamped with a timestamp the client never supplied.
    ws_settings_set(
        hass,
        connection,
        {"id": 2, "type": "ha_soc/settings/set", "external_connections_enabled": False},
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.store.settings["external_connections_enabled"] is False
    stamped_at = entry.runtime_data.store.settings["external_connections_changed_at"]
    assert stamped_at is not None

    result = connection.send_result.call_args[0][1]
    assert result["external_connections_enabled"] is False
    assert result["external_connections_changed_at"] == stamped_at

    # Flipping back changes the stamp again rather than reusing the old one.
    ws_settings_set(
        hass,
        connection,
        {"id": 3, "type": "ha_soc/settings/set", "external_connections_enabled": True},
    )
    await hass.async_block_till_done()
    assert entry.runtime_data.store.settings["external_connections_changed_at"] != stamped_at


async def test_get_and_set_are_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    from homeassistant.exceptions import Unauthorized

    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")

    with pytest.raises(Unauthorized):
        ws_settings_get(hass, non_owner, {"id": 1})
    with pytest.raises(Unauthorized):
        ws_settings_set(hass, non_owner, {"id": 2, "type": "ha_soc/settings/set", "scanner_enabled": False})


async def test_secret_masking_and_passthrough(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    # Set a real secret value: it lands in the private secret store, never
    # in the settings dict (SEC-1).
    ws_settings_set(
        hass, connection, {"id": 1, "type": "ha_soc/settings/set", "nvd_api_key": "SECRET123"}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") == "SECRET123"
    assert "nvd_api_key" not in entry.runtime_data.store.settings

    # Reading back never returns the raw value.
    ws_settings_get(hass, connection, {"id": 2})
    await hass.async_block_till_done()
    got = connection.send_result.call_args[0][1]
    assert got["nvd_api_key"] == "[redacted]"
    assert got["nvd_api_key_set"] is True

    # Sending the placeholder back is treated as "unchanged", not an overwrite.
    ws_settings_set(
        hass, connection, {"id": 3, "type": "ha_soc/settings/set", "nvd_api_key": "[redacted]"}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") == "SECRET123"

    # An empty string clears the secret, and the flag reads false again.
    ws_settings_set(
        hass, connection, {"id": 4, "type": "ha_soc/settings/set", "nvd_api_key": ""}
    )
    await hass.async_block_till_done()
    assert await entry.runtime_data.secrets.async_get("nvd_api_key") is None
    got = connection.send_result.call_args[0][1]
    assert got["nvd_api_key"] == ""
    assert got["nvd_api_key_set"] is False


# --------------------------------------------------------------------------
# Phase 2: Test Connection buttons (ha_soc/<service>/test_connection)
# --------------------------------------------------------------------------


async def test_unifi_network_test_connection_requires_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_unifi_network_test_connection(hass, non_owner, {"id": 1})


async def test_unifi_network_test_connection_unconfigured_is_not_reachable(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_unifi_network_test_connection(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": False, "error": "not configured"}


async def test_unifi_network_test_connection_reachable(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    with patch(
        "custom_components.ha_soc.unifi.async_network_overview",
        return_value={"configured": True, "reachable": True, "error": None},
    ):
        ws_unifi_network_test_connection(hass, connection, {"id": 1})
        await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": True, "error": None}


async def test_unifi_network_test_connection_never_raises_on_unexpected_error(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    with patch(
        "custom_components.ha_soc.unifi.async_network_overview",
        side_effect=RuntimeError("boom"),
    ):
        ws_unifi_network_test_connection(hass, connection, {"id": 1})
        await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result["ok"] is True
    assert result["reachable"] is False
    assert "boom" in result["error"]


async def test_unifi_protect_test_connection_requires_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_unifi_protect_test_connection(hass, non_owner, {"id": 1})


async def test_unifi_protect_test_connection_unconfigured(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_unifi_protect_test_connection(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": False, "error": "not configured"}


async def test_pihole_test_connection_requires_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_pihole_test_connection(hass, non_owner, {"id": 1})


async def test_pihole_test_connection_unconfigured(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_pihole_test_connection(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": False, "error": "not configured"}


async def test_pihole_test_connection_reachable(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    with patch(
        "custom_components.ha_soc.pihole.async_pihole_overview",
        return_value={"configured": True, "reachable": True, "error": None},
    ):
        ws_pihole_test_connection(hass, connection, {"id": 1})
        await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": True, "error": None}


async def test_technitium_test_connection_requires_owner(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_technitium_test_connection(hass, non_owner, {"id": 1})


async def test_technitium_test_connection_unconfigured(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    ws_technitium_test_connection(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": False, "error": "not configured"}


async def test_technitium_test_connection_error_surfaces(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    with patch(
        "custom_components.ha_soc.technitium.async_technitium_overview",
        return_value={"configured": True, "reachable": False, "error": "connection refused"},
    ):
        ws_technitium_test_connection(hass, connection, {"id": 1})
        await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True, "reachable": False, "error": "connection refused"}


# --------------------------------------------------------------------------
# Phase 2: local container discovery (ha_soc/containers/discover_candidates)
# --------------------------------------------------------------------------


async def test_discover_candidates_requires_owner(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_containers_discover_candidates(hass, non_owner, {"id": 1})


async def test_discover_candidates_empty_when_no_netscan_result(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    assert entry.runtime_data.store.data.get("netscan_result") is None
    ws_containers_discover_candidates(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"pihole": [], "technitium": []}


async def test_discover_candidates_matches_service_guess(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    entry.runtime_data.store.async_set_netscan_result(
        {
            "hosts": [
                {
                    "ip": "192.168.1.20",
                    "open_ports": [
                        {"port": 5380, "service_guess": "technitium", "service_confidence": "low"}
                    ],
                },
                {
                    "ip": "192.168.1.21",
                    "open_ports": [
                        {"port": 80, "service_guess": "pihole", "service_confidence": "high"}
                    ],
                },
            ]
        }
    )
    ws_containers_discover_candidates(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {
        "pihole": [{"ip": "192.168.1.21", "confidence": "high"}],
        "technitium": [{"ip": "192.168.1.20", "confidence": "low"}],
    }


# --------------------------------------------------------------------------
# Phase 3: SNMP probe-error notice — restart the Probe add-on
# (ha_soc/probe/restart)
# --------------------------------------------------------------------------


async def test_probe_restart_requires_owner(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    non_owner = MagicMock()
    non_owner.user = MagicMock(is_admin=True, is_owner=False, id="admin2")
    with pytest.raises(Unauthorized):
        ws_probe_restart(hass, non_owner, {"id": 1})


async def test_probe_restart_not_supervisor(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """hass.config.components has no "hassio" entry outside a Supervisor install."""
    connection = _connection()
    ws_probe_restart(hass, connection, {"id": 1})
    await hass.async_block_till_done()
    result = connection.send_result.call_args[0][1]
    assert result == {"ok": False, "reason": "not_supervisor"}


async def test_probe_restart_success(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Mocked the same way test_containers.py mocks a live Supervisor:
    patch get_supervisor_client to return a MagicMock whose
    addons.restart_addon is an AsyncMock."""
    connection = _connection()
    hass.config.components.add("hassio")
    client = MagicMock()
    client.addons.restart_addon = AsyncMock(return_value=None)

    with patch("homeassistant.components.hassio.get_supervisor_client", return_value=client):
        ws_probe_restart(hass, connection, {"id": 1})
        await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"ok": True}
    client.addons.restart_addon.assert_awaited_once_with("ha_soc_probe")


async def test_probe_restart_failure_surfaces_error(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    hass.config.components.add("hassio")
    client = MagicMock()
    client.addons.restart_addon = AsyncMock(side_effect=RuntimeError("addon not found"))

    with patch("homeassistant.components.hassio.get_supervisor_client", return_value=client):
        ws_probe_restart(hass, connection, {"id": 1})
        await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["ok"] is False
    assert result["reason"] == "restart_failed"
    assert "addon not found" in result["error"]


async def test_probe_restart_no_supervisor_client(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    connection = _connection()
    hass.config.components.add("hassio")

    with patch("homeassistant.components.hassio.get_supervisor_client", return_value=None):
        ws_probe_restart(hass, connection, {"id": 1})
        await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result == {"ok": False, "reason": "no_supervisor_client"}
