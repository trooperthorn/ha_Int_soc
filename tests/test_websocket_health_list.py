"""ha_soc/health/list sorts misconfig_findings most-severe-first."""
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import ws_health_list


def _connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True)
    return connection


def _finding(finding_id: str, severity: str) -> dict:
    return {
        "id": finding_id,
        "check": "some_check",
        "severity": severity,
        "title": "t",
        "summary": "s",
        "detail": {},
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


async def test_misconfig_findings_sorted_most_severe_first(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    # Insert deliberately out of severity order.
    store.async_upsert_finding("misconfig_findings", "f-low", _finding("f-low", "low"))
    store.async_upsert_finding("misconfig_findings", "f-critical", _finding("f-critical", "critical"))
    store.async_upsert_finding("misconfig_findings", "f-medium", _finding("f-medium", "medium"))
    store.async_upsert_finding("misconfig_findings", "f-info", _finding("f-info", "info"))
    store.async_upsert_finding("misconfig_findings", "f-high", _finding("f-high", "high"))

    connection = _connection()
    ws_health_list(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    # Real startup checks (e.g. cloud_egress_inventory) also populate
    # findings in this fixture's real config-entry setup — filter to just
    # the ones this test controls, preserving relative order.
    mine = {"f-low", "f-critical", "f-medium", "f-info", "f-high"}
    ordered_ids = [f["id"] for f in result["misconfig_findings"] if f["id"] in mine]
    assert ordered_ids == ["f-critical", "f-high", "f-medium", "f-low", "f-info"]
