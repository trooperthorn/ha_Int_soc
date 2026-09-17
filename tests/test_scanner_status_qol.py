"""Phase 6 QoL rework tests:

- The previously-broken ha_soc/scanner/set_status websocket command (it used
  to route through ha_soc/vulns/set_status against the wrong store table,
  where it silently no-op'd — see websocket_api.py ws_scanner_set_status).
- health.py's two inventory checks (cloud_egress_inventory, ssh_addon_inventory)
  now reconciling stale rows via _async_finalize_check instead of upsert-only.
- scanner.py's new ConfigEntryChange.REMOVED listener resolving a removed
  domain's findings.
- vulns.py's two new auto-resolve cases: firmware no longer outdated, and
  device removed from the registry.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryChange
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import device_registry as dr

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.vulns import DeviceVulnerabilityTracker
from custom_components.ha_soc.websocket_api import ws_scanner_set_status


def _connection(*, is_admin: bool = True, is_owner: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner, id="user-1")
    return connection


def _scanner_finding(finding_id: str, domain: str, status: str = "new") -> dict:
    return {
        "id": finding_id,
        "domain": domain,
        "pattern": "some_pattern",
        "severity": "medium",
        "file": "x.py",
        "line": 1,
        "confidence": "high",
        "cwe": "CWE-1",
        "status": status,
        "first_seen": "now",
        "last_seen": "now",
    }


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


# ---------------------------------------------------------------------------
# Task A: ha_soc/scanner/set_status (the actual bug fix)
# ---------------------------------------------------------------------------


async def test_ws_scanner_set_status_updates_scanner_findings_table(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    store.async_upsert_finding(
        "scanner_findings", "my_int:abc123", _scanner_finding("my_int:abc123", "my_int")
    )

    connection = _connection()
    ws_scanner_set_status(
        hass, connection, {"id": 1, "finding_id": "my_int:abc123", "status": "resolved"}
    )
    await hass.async_block_till_done()

    assert store.data["scanner_findings"]["my_int:abc123"]["status"] == "resolved"
    assert store.data["scanner_findings"]["my_int:abc123"]["status_by"] == "user-1"
    connection.send_result.assert_called_once()


async def test_old_vulns_set_status_does_not_touch_scanner_findings(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Documents the pre-fix bug directly: the old wiring called
    ha_soc/vulns/set_status against a scanner_findings id, which
    async_set_finding_status silently no-ops on since the id is looked
    up in the wrong table (vuln_findings)."""
    from custom_components.ha_soc.websocket_api import ws_vulns_set_status

    store = entry.runtime_data.store
    store.async_upsert_finding(
        "scanner_findings", "my_int:abc123", _scanner_finding("my_int:abc123", "my_int")
    )

    connection = _connection()
    ws_vulns_set_status(
        hass, connection, {"id": 1, "finding_id": "my_int:abc123", "status": "resolved"}
    )
    await hass.async_block_till_done()

    # Still "new": the wrong-table command could not find it, so it silently no-op'd.
    assert store.data["scanner_findings"]["my_int:abc123"]["status"] == "new"


async def test_ws_scanner_set_status_requires_admin(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection(is_admin=False, is_owner=False)
    with pytest.raises(Unauthorized):
        ws_scanner_set_status(
            hass, connection, {"id": 1, "finding_id": "does-not-matter", "status": "resolved"}
        )


async def test_ws_scanner_set_status_non_owner_admin_blocked_by_default_access_level(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    # DEFAULT_ACCESS_LEVEL is owner_only, so a non-owner admin is blocked
    # unless the owner has explicitly widened access to owner_and_admins.
    connection = _connection(is_admin=True, is_owner=False)
    with pytest.raises(Unauthorized):
        ws_scanner_set_status(
            hass, connection, {"id": 1, "finding_id": "does-not-matter", "status": "resolved"}
        )


async def test_ws_scanner_set_status_non_owner_admin_allowed_when_widened(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    store.data["settings"]["access_level"] = "owner_and_admins"
    store.async_upsert_finding(
        "scanner_findings", "my_int:abc123", _scanner_finding("my_int:abc123", "my_int")
    )
    connection = _connection(is_admin=True, is_owner=False)
    ws_scanner_set_status(
        hass, connection, {"id": 1, "finding_id": "my_int:abc123", "status": "resolved"}
    )
    await hass.async_block_till_done()
    assert store.data["scanner_findings"]["my_int:abc123"]["status"] == "resolved"


# ---------------------------------------------------------------------------
# Task A: health.py inventory checks now reconcile stale rows
# ---------------------------------------------------------------------------


async def test_ssh_addon_inventory_reflects_current_addons_each_sweep(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The aggregate row is always re-upserted with the current SSH-addon
    list, so a removed add-on already drops out of its detail on the very
    next sweep — this is the mechanism that answers the user's "removed
    integrations don't clear from the list" complaint for this check."""
    from custom_components.ha_soc.health import IntegrationHealth

    monitor: IntegrationHealth = entry.runtime_data.health
    store = entry.runtime_data.store

    with patch(
        "homeassistant.helpers.hassio.is_hassio", return_value=True
    ), patch(
        "homeassistant.components.hassio.get_addons_info",
        return_value={"core_ssh": {"name": "Terminal & SSH", "state": "started"}},
    ):
        await monitor._check_ssh_addon_inventory()

    finding = store.data["misconfig_findings"]["misconfig:ssh_addon_inventory"]
    assert finding["status"] == "new"
    assert len(finding["detail"]["addons"]) == 1

    # The add-on is uninstalled.
    with patch(
        "homeassistant.helpers.hassio.is_hassio", return_value=True
    ), patch(
        "homeassistant.components.hassio.get_addons_info",
        return_value={},
    ):
        await monitor._check_ssh_addon_inventory()

    finding = store.data["misconfig_findings"]["misconfig:ssh_addon_inventory"]
    assert finding["status"] == "new"
    assert finding["detail"]["addons"] == []


async def test_ssh_addon_inventory_resolves_when_supervisor_goes_away(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Before this fix, `not is_hassio(self.hass)` returned `[]` directly,
    bypassing _async_finalize_check entirely, so a row created while on
    Supervisor would linger forever once Supervisor became unreachable.
    Now it's routed through _async_finalize_check with no active items,
    which resolves it via _async_resolve_missing."""
    from custom_components.ha_soc.health import IntegrationHealth

    monitor: IntegrationHealth = entry.runtime_data.health
    store = entry.runtime_data.store

    with patch(
        "homeassistant.helpers.hassio.is_hassio", return_value=True
    ), patch(
        "homeassistant.components.hassio.get_addons_info",
        return_value={"core_ssh": {"name": "Terminal & SSH", "state": "started"}},
    ):
        await monitor._check_ssh_addon_inventory()

    assert store.data["misconfig_findings"]["misconfig:ssh_addon_inventory"]["status"] == "new"

    with patch("homeassistant.helpers.hassio.is_hassio", return_value=False):
        await monitor._check_ssh_addon_inventory()

    finding = store.data["misconfig_findings"]["misconfig:ssh_addon_inventory"]
    assert finding["status"] == "resolved"


async def test_cloud_egress_inventory_routes_through_finalize_check(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Confirms the check no longer bypasses _async_finalize_check: a manually
    confirmed status on the aggregate row must survive the next sweep instead
    of being silently overwritten by the old upsert-only path."""
    from custom_components.ha_soc.health import IntegrationHealth

    monitor: IntegrationHealth = entry.runtime_data.health
    store = entry.runtime_data.store

    await monitor._check_cloud_egress_inventory()
    assert "misconfig:cloud_egress_inventory" in store.data["misconfig_findings"]

    store.async_set_finding_status(
        "misconfig_findings", "misconfig:cloud_egress_inventory", "confirmed",
        by_user_id="user-1", note=None, at="now",
    )

    await monitor._check_cloud_egress_inventory()
    finding = store.data["misconfig_findings"]["misconfig:cloud_egress_inventory"]
    assert finding["status"] == "confirmed"


# ---------------------------------------------------------------------------
# Task A: scanner.py ConfigEntryChange.REMOVED reconciliation
# ---------------------------------------------------------------------------


@pytest.fixture
async def scanner_store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


async def test_config_entry_removed_resolves_domain_findings(
    hass: HomeAssistant, scanner_store: HaSocData
) -> None:
    from custom_components.ha_soc.scanner import IntegrationScanner

    scanner = IntegrationScanner(hass, scanner_store)
    scanner_store.async_upsert_finding(
        "scanner_findings", "gone_domain:f1", _scanner_finding("gone_domain:f1", "gone_domain")
    )
    scanner_store.async_upsert_finding(
        "scanner_findings", "gone_domain:f2", _scanner_finding("gone_domain:f2", "gone_domain", status="dismissed")
    )
    scanner_store.async_upsert_finding(
        "scanner_findings", "other_domain:f1", _scanner_finding("other_domain:f1", "other_domain")
    )

    entry = SimpleNamespace(domain="gone_domain")
    scanner._on_config_entry_changed(ConfigEntryChange.REMOVED, entry)
    await hass.async_block_till_done()

    assert scanner_store.data["scanner_findings"]["gone_domain:f1"]["status"] == "resolved"
    assert scanner_store.data["scanner_findings"]["gone_domain:f1"]["resolved_reason"] == "integration_removed"
    # Already-dismissed findings are preserved, not overwritten.
    assert scanner_store.data["scanner_findings"]["gone_domain:f2"]["status"] == "dismissed"
    # A different domain's findings are untouched.
    assert scanner_store.data["scanner_findings"]["other_domain:f1"]["status"] == "new"


# ---------------------------------------------------------------------------
# Task A: vulns.py new auto-resolve cases
# ---------------------------------------------------------------------------


@pytest.fixture
async def tracker(hass: HomeAssistant) -> DeviceVulnerabilityTracker:
    store = HaSocData(hass)
    await store.async_load()
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    return DeviceVulnerabilityTracker(hass, store, secrets)


async def test_firmware_outdated_finding_resolves_when_no_longer_outdated(
    hass: HomeAssistant, tracker: DeviceVulnerabilityTracker
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "dev-1")}, name="Dev"
    )

    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)
    fw_entity = entity_registry.async_get_or_create(
        "update", DOMAIN, "dev-1-fw", device_id=device.id, config_entry=entry
    )
    hass.states.async_set(
        fw_entity.entity_id, "on",
        {"device_class": "firmware", "installed_version": "1.0", "latest_version": "2.0"},
    )

    with patch.object(tracker, "_async_correlate_cves", AsyncMock(return_value=[])):
        await tracker.async_run_scan()

    finding_id = f"{device.id}:firmware_outdated"
    assert tracker.store.data["vuln_findings"][finding_id]["status"] == "new"

    # Firmware caught up: the update entity flips off "on".
    hass.states.async_set(
        fw_entity.entity_id, "off",
        {"device_class": "firmware", "installed_version": "2.0", "latest_version": "2.0"},
    )
    with patch.object(tracker, "_async_correlate_cves", AsyncMock(return_value=[])):
        await tracker.async_run_scan()

    assert tracker.store.data["vuln_findings"][finding_id]["status"] == "resolved"


async def test_finding_resolves_when_device_removed_from_registry(
    hass: HomeAssistant, tracker: DeviceVulnerabilityTracker
) -> None:
    tracker.store.async_upsert_finding(
        "vuln_findings",
        "ghost-device:CVE-2024-1234",
        {
            "id": "ghost-device:CVE-2024-1234",
            "device_id": "ghost-device",
            "device_name": "Ghost",
            "cve_id": "CVE-2024-1234",
            "cvss": 7.5,
            "severity": "high",
            "confidence": "exact_cpe",
            "summary": "s",
            "source": "nvd",
            "match_string": "m",
            "first_seen": "now",
            "last_seen": "now",
            "status": "new",
        },
    )

    with patch.object(tracker, "_async_correlate_cves", AsyncMock(return_value=[])):
        await tracker.async_run_scan()

    finding = tracker.store.data["vuln_findings"]["ghost-device:CVE-2024-1234"]
    assert finding["status"] == "resolved"
    assert finding["resolved_reason"] == "device_removed"


async def test_dismissed_finding_survives_device_removal(
    hass: HomeAssistant, tracker: DeviceVulnerabilityTracker
) -> None:
    tracker.store.async_upsert_finding(
        "vuln_findings",
        "ghost-device:CVE-2024-9999",
        {
            "id": "ghost-device:CVE-2024-9999",
            "device_id": "ghost-device",
            "device_name": "Ghost",
            "cve_id": "CVE-2024-9999",
            "cvss": 7.5,
            "severity": "high",
            "confidence": "exact_cpe",
            "summary": "s",
            "source": "nvd",
            "match_string": "m",
            "first_seen": "now",
            "last_seen": "now",
            "status": "dismissed",
        },
    )

    with patch.object(tracker, "_async_correlate_cves", AsyncMock(return_value=[])):
        await tracker.async_run_scan()

    finding = tracker.store.data["vuln_findings"]["ghost-device:CVE-2024-9999"]
    assert finding["status"] == "dismissed"
    assert "resolved_reason" not in finding
