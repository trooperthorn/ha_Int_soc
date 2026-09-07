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

import voluptuous as vol

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import (
    DOMAIN,
    FIREWALL_TEST_CONFIRMED,
    FIREWALL_TEST_EXPIRED_UNREPORTED,
    FIREWALL_TEST_REVERTED,
    FIREWALL_TEST_TESTING,
)

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": "192.168.10.0/24"}]
# What RULES looks like after RULE_SCHEMA settles the family: an IPv4
# source pins family "4" (work item 2.4). Proposed rules are stored and
# handed to the add-on in this normalized shape.
RULES_NORMALIZED = [
    {
        "action": "allow",
        "proto": "tcp",
        "ports": "8123",
        "icmp_type": None,
        "source": "192.168.10.0/24",
        "destination": None,
        "interface": None,
        "log": False,
        "comment": None,
        "family": "4",
    }
]


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
    bad_rules = [{"action": "allow", "proto": "gre", "port": 8123}]
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
    assert pending["proposed_rules"] == RULES_NORMALIZED
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
        "rules": RULES_NORMALIZED,
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
    assert fw["known_rules"] == RULES_NORMALIZED
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
    # Mutate the former fw["pending"] object; a stored reference instead of a copy would corrupt history.
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
    assert fw["known_rules"] == RULES_NORMALIZED  # known_rules still updates unconditionally
    assert fw["history"] == []


async def test_get_status_lazily_expires_stale_pending(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=-1
    )
    status = await firewall.async_get_status(hass, store)
    assert status["pending"]["status"] == "expired_unreported"


async def test_rule_family_derivation(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Work item 2.4 (D-3): a rule's family is derived from its source's
    address family, an explicit value that contradicts the source is
    rejected, an explicit family without a source is honored as the
    operator's scoping choice, and no source at all defaults to both."""
    store = entry.runtime_data.store

    # No source, no explicit family: dual-stack default.
    rule = firewall.RULE_SCHEMA({"action": "deny", "proto": "tcp", "port": 22})
    assert rule["family"] == "both"

    # An IPv4 source pins family 4; an IPv6 source pins family 6.
    rule = firewall.RULE_SCHEMA(
        {"action": "deny", "proto": "tcp", "port": 22, "source": "192.168.10.0/24"}
    )
    assert rule["family"] == "4"
    rule = firewall.RULE_SCHEMA(
        {"action": "deny", "proto": "tcp", "port": 22, "source": "fd00::/8"}
    )
    assert rule["family"] == "6"

    # A matching explicit value passes; a contradicting one is rejected.
    rule = firewall.RULE_SCHEMA(
        {"action": "deny", "proto": "tcp", "port": 22, "source": "fd00::/8", "family": "6"}
    )
    assert rule["family"] == "6"
    with pytest.raises(vol.Invalid):
        firewall.RULE_SCHEMA(
            {"action": "deny", "proto": "tcp", "port": 22, "source": "192.168.10.0/24", "family": "6"}
        )

    # An explicit family with no source stands as given.
    rule = firewall.RULE_SCHEMA({"action": "deny", "proto": "tcp", "port": 22, "family": "6"})
    assert rule["family"] == "6"

    # End to end: the propose path surfaces the mismatch as invalid_rules,
    # exactly like any other schema failure.
    ok, reason, pending = await firewall.async_propose_test(
        hass,
        store,
        rules=[
            {"action": "deny", "proto": "tcp", "port": 22, "source": "192.168.10.0/24", "family": "6"}
        ],
        backup_acknowledged=True,
        user_id="u1",
    )
    assert ok is False
    assert reason.startswith("invalid_rules")
    assert pending is None


async def test_partial_ipv6_is_visible(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Work item 2.4: when the add-on reports ipv6_supported false, every
    "6" and "both" rule (in the pending test and in known_rules, an absent
    family counting as both) is surfaced partially_applied and the status
    carries ipv6_supported for the card's banner, never a silent
    IPv4-only success. The marking is computed at read time on copies; the
    stored records stay unflagged."""
    store = entry.runtime_data.store
    mixed = [
        {"action": "deny", "proto": "tcp", "port": 22},  # derives family both
        {"action": "deny", "proto": "tcp", "port": 23, "source": "192.168.1.0/24"},  # family 4
        {"action": "deny", "proto": "udp", "port": 53, "family": "6"},  # explicit 6
    ]
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=mixed, backup_acknowledged=True, user_id="u1"
    )

    await firewall.async_report_from_addon(
        hass,
        store,
        known_rules=[
            {"action": "deny", "proto": "tcp", "port": 22, "source": None, "family": "4"},
            # A record persisted before the dual-stack change carries no
            # family at all; that reads as "both" and must be marked too.
            {"action": "deny", "proto": "tcp", "port": 8123, "source": None},
        ],
        ipv6_supported=False,
    )

    status = await firewall.async_get_status(hass, store)
    assert status["ipv6_supported"] is False

    proposed = status["pending"]["proposed_rules"]
    assert proposed[0]["partially_applied"] is True  # both
    assert "partially_applied" not in proposed[1]  # pure IPv4 is fully live
    assert proposed[2]["partially_applied"] is True  # IPv6-only

    known = status["known_rules"]
    assert "partially_applied" not in known[0]  # family 4
    assert known[1]["partially_applied"] is True  # legacy record, reads as both

    # Read-time marking only: the stored records are untouched.
    stored = store.data["firewall"]
    assert all("partially_applied" not in r for r in stored["pending"]["proposed_rules"])
    assert all("partially_applied" not in r for r in stored["known_rules"])

    # A later report that IPv6 works again clears the marking entirely.
    await firewall.async_report_from_addon(hass, store, known_rules=None, ipv6_supported=True)
    status = await firewall.async_get_status(hass, store)
    assert status["ipv6_supported"] is True
    assert all("partially_applied" not in r for r in status["pending"]["proposed_rules"])
    assert all("partially_applied" not in r for r in status["known_rules"])


def _rule(**overrides):
    base = {"action": "allow", "proto": "tcp", "ports": "443"}
    base.update(overrides)
    return firewall.RULE_SCHEMA(base)


def test_ports_grammar_single_range_and_list() -> None:
    assert _rule(ports="443")["ports"] == "443"
    assert _rule(ports="8000:8100")["ports"] == "8000:8100"
    assert _rule(ports="80,443,8000:8100")["ports"] == "80,443,8000:8100"
    # The legacy integer port is still accepted and normalized.
    assert _rule(ports=None, port=8123)["ports"] == "8123"
    for bad in ("0", "65536", "8100:8000", "80:80", "a", "80;443", ",".join(["1"] * 16)):
        with pytest.raises(vol.Invalid):
            _rule(ports=bad)
    with pytest.raises(vol.Invalid):
        _rule(ports=None)


def test_icmp_rules_take_a_type_not_ports() -> None:
    rule = _rule(proto="icmp", ports=None)
    assert rule["icmp_type"] == "any" and rule["ports"] is None and rule["family"] == "both"
    assert _rule(proto="icmp", ports=None, icmp_type="echo-request")["family"] == "both"
    # A type that exists in one family only pins the rule to that family.
    assert _rule(proto="icmp", ports=None, icmp_type="neighbour-solicitation")["family"] == "6"
    with pytest.raises(vol.Invalid):
        _rule(proto="icmp", ports=None, icmp_type="neighbour-solicitation", family="4")
    with pytest.raises(vol.Invalid):
        _rule(proto="icmp", ports="443")
    with pytest.raises(vol.Invalid):
        _rule(proto="tcp", icmp_type="echo-request")
    with pytest.raises(vol.Invalid):
        _rule(proto="icmp", ports=None, icmp_type="made-up")


def test_destination_interface_comment_log_and_reject() -> None:
    rule = _rule(
        action="reject",
        destination="192.168.10.5",
        interface="eth0.10",
        comment="ha_web",
        log=True,
    )
    assert rule["action"] == "reject" and rule["family"] == "4"
    assert rule["destination"] == "192.168.10.5" and rule["interface"] == "eth0.10"
    assert rule["comment"] == "ha_web" and rule["log"] is True
    with pytest.raises(vol.Invalid):
        _rule(source="192.168.10.0/24", destination="fd00::1")
    for bad_iface in ("eth 0", "a" * 16, "eth0;"):
        with pytest.raises(vol.Invalid):
            _rule(interface=bad_iface)
    for bad_comment in ("has space", "a" * 23, 'quote"'):
        with pytest.raises(vol.Invalid):
            _rule(comment=bad_comment)


def test_required_capabilities_and_addon_wire_shape() -> None:
    plain = _rule()
    assert firewall.rule_required_capabilities(plain) == set()
    fancy = _rule(action="reject", ports="80,443", comment="x", log=True)
    assert firewall.rule_required_capabilities(fancy) == {"multiport", "comment", "log", "limit", "reject"}
    icmp = _rule(proto="icmp", ports=None, icmp_type="echo-request")
    assert firewall.rule_required_capabilities(icmp) == {"icmp"}
    assert firewall.rule_for_addon(icmp)["icmp_codes"] == {"4": 8, "6": 128}
    assert firewall.rule_for_addon(_rule(proto="icmp", ports=None))["icmp_codes"] == {"4": "any", "6": "any"}
    v6_only = _rule(proto="icmp", ports=None, icmp_type="packet-too-big")
    assert firewall.rule_for_addon(v6_only)["icmp_codes"] == {"4": None, "6": 2}
    assert "icmp_codes" not in firewall.rule_for_addon(plain)


def test_normalize_known_rule_maps_codes_back_to_names() -> None:
    read_back = {"action": "deny", "proto": "icmp", "ports": None, "icmp_code": "128", "family": "6"}
    assert firewall.normalize_known_rule(read_back)["icmp_type"] == "echo-request"
    unknown = {"action": "deny", "proto": "icmp", "icmp_code": "200", "family": "4"}
    assert firewall.normalize_known_rule(unknown)["icmp_type"] == "200"
    legacy = {"action": "allow", "proto": "tcp", "port": 22, "source": None}
    normalized = firewall.normalize_known_rule(legacy)
    assert normalized["ports"] == "22" and normalized["family"] == "both" and normalized["log"] is False


async def test_propose_refuses_capabilities_the_addon_lacks(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    needs_multiport = [{"action": "allow", "proto": "tcp", "ports": "80,443"}]
    # No report yet: nothing is refused on capability grounds.
    ok, _, _ = await firewall.async_propose_test(
        hass, store, rules=needs_multiport, backup_acknowledged=True, user_id="u1"
    )
    assert ok is True
    store.data["firewall"]["pending"] = None

    await firewall.async_report_from_addon(
        hass, store, known_rules=[], capabilities={"multiport": False, "comment": True}
    )
    ok, reason, _ = await firewall.async_propose_test(
        hass, store, rules=needs_multiport, backup_acknowledged=True, user_id="u1"
    )
    assert ok is False and reason == "unsupported_capabilities: multiport"
    status = await firewall.async_get_status(hass, store)
    assert status["capabilities"] == {"multiport": False, "comment": True}
