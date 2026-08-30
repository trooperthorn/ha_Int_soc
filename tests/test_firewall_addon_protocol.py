"""Tests for the add-on-facing firewall protocol: ha_soc.poll_firewall_command
(the add-on's fast ~5s poll for pending work) and ingest_probe_result's
extended firewall report fields (known_rules / resolved_test_id /
resolved_status), both registered in probe.py.

Since the Supervisor-context authentication change, every call here runs
the way the real add-on's calls arrive: through a simulated Supervisor
install, in the Supervisor system user's context, carrying the shared
probe secret (pinned on the first call).
"""
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import DOMAIN, FIREWALL_TEST_EXPIRED_UNREPORTED
from custom_components.ha_soc.secrets_store import PROBE_PAIRING_SECRET_KEY

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": None}]
PROBE_SECRET = "unit-test-probe-secret"


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def supervisor_context(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


async def _poll(hass: HomeAssistant, context: Context, **data) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": PROBE_SECRET, **data},
        blocking=True,
        return_response=True,
        context=context,
    )


async def _ingest(hass: HomeAssistant, context: Context, **data) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"probe_secret": PROBE_SECRET, **data},
        blocking=True,
        context=context,
    )


async def test_poll_firewall_command_returns_none_with_no_pending(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    response = await _poll(hass, supervisor_context)
    assert response == {"action": "none"}


async def test_poll_firewall_command_returns_apply_for_new_test(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )

    response = await _poll(hass, supervisor_context)
    assert response["action"] == "apply"
    assert response["test_id"] == pending["test_id"]
    assert response["rules"] == RULES


async def test_poll_firewall_command_returns_confirm_after_ws_confirm(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]

    # First poll: add-on picks up the apply instruction.
    await _poll(hass, supervisor_context)

    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    response = await _poll(hass, supervisor_context, current_test_id=test_id)
    assert response == {"action": "confirm", "test_id": test_id}


async def test_poll_with_other_test_id_gets_none(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """A poll whose current_test_id names a DIFFERENT test than the one
    Core has pending never receives "apply": the add-on is still armed for
    the other test, and stacking a second ruleset on the shared chain and
    revert path is exactly the overlap the one-at-a-time rule forbids."""
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )

    response = await _poll(hass, supervisor_context, current_test_id="some-older-armed-test")
    assert response["action"] == "none"
    assert response["reason"] == "addon_holds_other_test"
    # The pending test was NOT handed out: it still awaits its apply.
    assert store.data["firewall"]["pending"]["test_id"] == pending["test_id"]
    assert store.data["firewall"]["pending"]["applied_at"] is None


async def test_unreported_expired_test_archives_on_empty_poll(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """A pending test that expired without any resolution report is
    archived as reverted-by-timer once the add-on polls holding no test at
    all: that empty poll after the window is the evidence the add-on's
    local timer (or its startup recovery) reverted the rules. The first
    test therefore always reaches history, never silently vanishes."""
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1", window_seconds=-1
    )
    test_id = pending["test_id"]

    # The add-on picked the test up, then lost it (crash/restart) and its
    # resolution report never arrived.
    response = await _poll(hass, supervisor_context)
    assert response["action"] == "apply"

    # The status read is what relabels the timed-out test (display-only).
    status = await firewall.async_get_status(hass, store)
    assert status["pending"]["status"] == FIREWALL_TEST_EXPIRED_UNREPORTED

    response = await _poll(hass, supervisor_context, current_test_id="")
    assert response == {"action": "none"}

    fw = store.data["firewall"]
    assert fw["pending"] is None
    assert len(fw["history"]) == 1
    assert fw["history"][0]["test_id"] == test_id
    assert fw["history"][0]["status"] == "reverted"
    assert fw["history"][0]["resolved_by"] == "addon_timer"


async def test_ingest_probe_result_reports_known_rules_and_resolves_test(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    await _ingest(
        hass,
        supervisor_context,
        open_ports=[{"port": 8123, "proto": "tcp"}],
        firewall_known_rules=RULES,
        firewall_resolved_test_id=test_id,
        firewall_resolved_status="confirmed",
    )

    fw = store.data["firewall"]
    assert fw["pending"] is None
    assert fw["known_rules"] == RULES
    assert len(fw["history"]) == 1
    assert fw["history"][0]["test_id"] == test_id
    assert fw["history"][0]["status"] == "confirmed"


async def test_ingest_probe_result_firewall_only_report_does_not_touch_host_probe(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """The firewall poller reports on its own ~5s cadence and must never
    stomp the port scanner's own, much slower-cadence host_probe data by
    omitting open_ports entirely — open_ports is optional precisely so a
    firewall-only report can leave it alone.
    """
    store = entry.runtime_data.store
    await _ingest(
        hass,
        supervisor_context,
        open_ports=[{"port": 22, "proto": "tcp"}],
        scanner_version="1.0",
    )
    assert store.data["host_probe"]["open_ports"] == [{"port": 22, "proto": "tcp"}]

    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await firewall.async_confirm_test(hass, store, test_id=test_id, user_id="u1")

    await _ingest(
        hass,
        supervisor_context,
        firewall_known_rules=RULES,
        firewall_resolved_test_id=test_id,
        firewall_resolved_status="confirmed",
    )

    # host_probe from the earlier port-scanner report is untouched.
    assert store.data["host_probe"]["open_ports"] == [{"port": 22, "proto": "tcp"}]
    assert store.data["host_probe"]["scanner_version"] == "1.0"
    # ...while the firewall report still went through.
    assert store.data["firewall"]["pending"] is None
    assert store.data["firewall"]["history"][0]["status"] == "confirmed"


async def test_ingest_probe_result_without_firewall_fields_is_a_noop_for_firewall(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )

    # Older/base add-on report shape — no firewall_* fields at all. Must
    # not disturb an in-flight pending test.
    await _ingest(hass, supervisor_context, open_ports=[{"port": 22, "proto": "tcp"}])

    fw = store.data["firewall"]
    assert fw["pending"]["test_id"] == pending["test_id"]
    assert fw["known_rules"] is None


async def test_pairing_secret_lives_in_secret_store_end_to_end(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """The pin created by the add-on's first authenticated call lands in
    the private secret store (SEC-1) and keeps gating the protocol: the
    same secret keeps working, a forged one is rejected without leaking
    pending work, and the owner's pairing reset re-opens pinning."""
    runtime = entry.runtime_data
    secrets = runtime.secrets

    # First authenticated poll pins into the secret store; the general
    # store's firewall dict holds no copy.
    await _poll(hass, supervisor_context)
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) == PROBE_SECRET
    assert "addon_secret" not in runtime.store.data["firewall"]

    # With a test pending, the right secret gets the apply and a wrong one
    # gets a bare none (a forger learns nothing about pending work).
    _, _, pending = await firewall.async_propose_test(
        hass, runtime.store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    forged = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": "forged-secret"},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert forged == {"action": "none"}
    # The pending test was not handed out to the forger.
    assert runtime.store.data["firewall"]["pending"]["applied_at"] is None

    good = await _poll(hass, supervisor_context)
    assert good["action"] == "apply"
    assert good["test_id"] == pending["test_id"]

    # Owner reset clears the pin in the secret store; the next non-empty
    # Supervisor-context secret re-pins.
    await firewall.async_reset_addon_secret(secrets)
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) is None
    await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": "rotated-secret"},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) == "rotated-secret"
