"""Tests for the add-on-facing firewall protocol: ha_soc.poll_firewall_command
(the add-on's fast ~5s poll for pending work) and ingest_probe_result's
extended firewall report fields (known_rules / resolved_test_id /
resolved_status), both registered in probe.py.
"""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import DOMAIN

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": None}]


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_poll_firewall_command_returns_none_with_no_pending(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    response = await hass.services.async_call(
        DOMAIN, "poll_firewall_command", {}, blocking=True, return_response=True
    )
    assert response == {"action": "none"}


async def test_poll_firewall_command_returns_apply_for_new_test(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )

    response = await hass.services.async_call(
        DOMAIN, "poll_firewall_command", {}, blocking=True, return_response=True
    )
    assert response["action"] == "apply"
    assert response["test_id"] == pending["test_id"]
    assert response["rules"] == RULES


async def test_poll_firewall_command_returns_confirm_after_ws_confirm(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    # First poll: add-on picks up the apply instruction.
    await hass.services.async_call(
        DOMAIN, "poll_firewall_command", {}, blocking=True, return_response=True
    )

    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    response = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"current_test_id": test_id},
        blocking=True,
        return_response=True,
    )
    assert response == {"action": "confirm", "test_id": test_id}


async def test_ingest_probe_result_reports_known_rules_and_resolves_test(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "open_ports": [{"port": 8123, "proto": "tcp"}],
            "firewall_known_rules": RULES,
            "firewall_resolved_test_id": test_id,
            "firewall_resolved_status": "confirmed",
        },
        blocking=True,
    )

    fw = store.data["firewall"]
    assert fw["pending"] is None
    assert fw["known_rules"] == RULES
    assert len(fw["history"]) == 1
    assert fw["history"][0]["test_id"] == test_id
    assert fw["history"][0]["status"] == "confirmed"


async def test_ingest_probe_result_firewall_only_report_does_not_touch_host_probe(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """The firewall poller reports on its own ~5s cadence and must never
    stomp the port scanner's own, much slower-cadence host_probe data by
    omitting open_ports entirely — open_ports is optional precisely so a
    firewall-only report can leave it alone.
    """
    store = entry.runtime_data.store
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "scanner_version": "1.0"},
        blocking=True,
    )
    assert store.data["host_probe"]["open_ports"] == [{"port": 22, "proto": "tcp"}]

    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "firewall_known_rules": RULES,
            "firewall_resolved_test_id": test_id,
            "firewall_resolved_status": "confirmed",
        },
        blocking=True,
    )

    # host_probe from the earlier port-scanner report is untouched.
    assert store.data["host_probe"]["open_ports"] == [{"port": 22, "proto": "tcp"}]
    assert store.data["host_probe"]["scanner_version"] == "1.0"
    # ...while the firewall report still went through.
    assert store.data["firewall"]["pending"] is None
    assert store.data["firewall"]["history"][0]["status"] == "confirmed"


async def test_ingest_probe_result_without_firewall_fields_is_a_noop_for_firewall(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )

    # Older/base add-on report shape — no firewall_* fields at all. Must
    # not disturb an in-flight pending test.
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}]},
        blocking=True,
    )

    fw = store.data["firewall"]
    assert fw["pending"]["test_id"] == pending["test_id"]
    assert fw["known_rules"] is None
