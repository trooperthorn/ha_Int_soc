"""Tests for firewall.py's pending-test state machine.

Covers the properties that actually make the feature safe: the backup
checkbox is enforced server-side, a test can't be double-proposed, the
add-on only ever gets told to "apply" once per test, confirm/cancel don't
touch history (only the add-on's own report does), and an archived
history entry is a genuinely independent copy of the pending record it
came from.
"""
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import (
    DOMAIN,
    FIREWALL_TEST_CONFIRMED,
    FIREWALL_TEST_EXPIRED_UNREPORTED,
    FIREWALL_TEST_REVERTED,
    FIREWALL_TEST_TESTING,
)

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": "192.168.10.0/24"}]


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


async def test_propose_without_backup_ack_fails(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    ok, reason, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=False, user_id="u1"
    )
    assert ok is False
    assert reason == "backup_not_acknowledged"
    assert pending is None
    assert store.data["firewall"]["pending"] is None


async def test_propose_with_invalid_rules_fails(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    bad_rules = [{"action": "allow", "proto": "icmp", "port": 8123}]
    ok, reason, pending = await firewall.async_propose_test(
        hass, store, rules=bad_rules, backup_acknowledged=True, user_id="u1"
    )
    assert ok is False
    assert reason.startswith("invalid_rules")
    assert pending is None


async def test_propose_happy_path(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    ok, reason, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=45
    )
    assert ok is True
    assert reason is None
    assert pending["status"] == FIREWALL_TEST_TESTING
    assert pending["applied_at"] is None
    assert pending["proposed_rules"] == RULES
    assert pending["window_seconds"] == 45
    assert store.data["firewall"]["pending"] is pending


async def test_propose_while_already_testing_fails(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    ok, _, _ = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    assert ok is True

    ok2, reason2, pending2 = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    assert ok2 is False
    assert reason2 == "test_pending_unreported"
    assert pending2 is None


async def test_second_proposal_refused_while_pending_unreported(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Guarantee (inverts the old overwrite defect): even after the test
    window has lapsed and the display shows expired_unreported, the slot
    stays occupied and a second proposal is refused until the add-on's own
    report archives the first test. The first test can therefore never be
    silently overwritten out of existence."""
    store = entry.runtime_data.store
    _, _, first = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=-1
    )

    # The status read runs the display-only lazy expiry.
    status = await firewall.async_get_status(hass, store)
    assert status["pending"]["status"] == FIREWALL_TEST_EXPIRED_UNREPORTED

    ok, reason, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    assert ok is False
    assert reason == "test_pending_unreported"
    assert pending is None
    assert store.data["firewall"]["pending"]["test_id"] == first["test_id"]


async def test_next_addon_command_returns_apply_once(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    command = await firewall.async_next_addon_command(hass, store, current_test_id=None)
    assert command == {
        "action": "apply",
        "test_id": test_id,
        "rules": RULES,
        "window_seconds": 45,
    }
    # applied_at is now set on the live pending record.
    assert store.data["firewall"]["pending"]["applied_at"] is not None

    # Second poll, add-on now reports it's tracking this test_id: no
    # further action until the user (or the window) resolves it.
    command2 = await firewall.async_next_addon_command(hass, store, current_test_id=test_id)
    assert command2 == {"action": "none"}


async def test_next_addon_command_none_when_no_pending(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    command = await firewall.async_next_addon_command(hass, store, current_test_id=None)
    assert command == {"action": "none"}


async def test_expires_at_reanchored_on_apply(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Recorded intent statement (work plan section 2): the propose-time
    expires_at is only the staleness bound for a proposal the add-on never
    picks up; the moment the apply is handed out (applied_at set), the
    countdown is re-anchored to applied_at + window_seconds so the panel
    tracks the add-on's real local timer instead of running up to one poll
    interval ahead of it."""
    import homeassistant.util.dt as dt_util

    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=45
    )
    requested_at = dt_util.parse_datetime(pending["requested_at"])
    pre_apply_expires = dt_util.parse_datetime(pending["expires_at"])
    # Before the apply: the proposal-staleness bound, propose time + window.
    assert (pre_apply_expires - requested_at).total_seconds() == pytest.approx(45, abs=1)

    command = await firewall.async_next_addon_command(hass, store, current_test_id=None)
    assert command["action"] == "apply"

    live = store.data["firewall"]["pending"]
    applied_at = dt_util.parse_datetime(live["applied_at"])
    reanchored_expires = dt_util.parse_datetime(live["expires_at"])
    # After the apply: exactly applied_at + window_seconds, to the second.
    assert (reanchored_expires - applied_at).total_seconds() == pytest.approx(45, abs=1)
    assert reanchored_expires >= pre_apply_expires


async def test_confirm_updates_status_without_touching_history(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    ok, reason = await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")
    assert ok is True
    assert reason is None
    assert store.data["firewall"]["pending"]["status"] == FIREWALL_TEST_CONFIRMED
    assert store.data["firewall"]["history"] == []

    # Add-on hasn't reported yet, so it should now be told to confirm.
    command = await firewall.async_next_addon_command(hass, store, current_test_id=test_id)
    assert command == {"action": "confirm", "test_id": test_id}


async def test_confirm_with_wrong_test_id_fails(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    await firewall.async_propose_test(hass, store, rules=RULES, backup_acknowledged=True, user_id="u1")

    ok, reason = await firewall.async_confirm_test(hass, store, test_id="not-a-real-id", user_id="u1")
    assert ok is False
    assert reason == "no_matching_test"


async def test_cancel_updates_status_without_touching_history(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    ok, reason = await firewall.async_cancel_test(hass, store, test_id=test_id, user_id="u1")
    assert ok is True
    assert reason is None
    assert store.data["firewall"]["pending"]["status"] == FIREWALL_TEST_REVERTED
    assert store.data["firewall"]["history"] == []

    command = await firewall.async_next_addon_command(hass, store, current_test_id=test_id)
    assert command == {"action": "revert", "test_id": test_id}


async def test_report_from_addon_archives_and_clears_pending(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    await firewall.async_report_from_addon(
        hass,
        store,
        known_rules=RULES,
        resolved_test_id=test_id,
        resolved_status=FIREWALL_TEST_CONFIRMED,
    )

    fw = store.data["firewall"]
    assert fw["pending"] is None
    assert fw["known_rules"] == RULES
    assert fw["known_rules_reported_at"] is not None
    assert len(fw["history"]) == 1
    assert fw["history"][0]["test_id"] == test_id
    assert fw["history"][0]["status"] == FIREWALL_TEST_CONFIRMED


async def test_report_from_addon_history_entry_is_independent_copy(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Mutating the (now-cleared) live pending state after archiving must
    never reach back into the already-archived history entry — this is
    the shallow-copy-aliasing bug fixed during development.
    """
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    # Grab the live pending dict reference before it's cleared, exactly
    # as async_report_from_addon internally does.
    live_pending_ref = store.data["firewall"]["pending"]

    await firewall.async_report_from_addon(
        hass,
        store,
        known_rules=RULES,
        resolved_test_id=test_id,
        resolved_status=FIREWALL_TEST_CONFIRMED,
    )

    archived = store.data["firewall"]["history"][0]
    # Mutate the object that used to be fw["pending"] — if history stored
    # the same reference instead of a copy, this would corrupt it.
    live_pending_ref["status"] = "corrupted-by-test"
    assert archived["status"] == FIREWALL_TEST_CONFIRMED


async def test_report_from_addon_ignores_mismatched_test_id(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    # A report for some other (stale/unrelated) test_id must not touch
    # the current pending record.
    await firewall.async_report_from_addon(
        hass,
        store,
        known_rules=RULES,
        resolved_test_id="some-other-test-id",
        resolved_status=FIREWALL_TEST_CONFIRMED,
    )

    fw = store.data["firewall"]
    assert fw["pending"]["test_id"] == test_id
    assert fw["pending"]["status"] == FIREWALL_TEST_TESTING
    assert fw["known_rules"] == RULES  # known_rules still updates unconditionally
    assert fw["history"] == []


async def test_get_status_lazily_expires_stale_pending(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=-1
    )
    status = await firewall.async_get_status(hass, store)
    assert status["pending"]["status"] == "expired_unreported"
