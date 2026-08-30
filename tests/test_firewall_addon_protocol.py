"""Tests for the add-on-facing firewall protocol: ha_soc.poll_firewall_command
(the add-on's fast ~5s poll for pending work) and ingest_probe_result's
extended firewall report fields (known_rules / resolved_test_id /
resolved_status), both registered in probe.py.

Since the Supervisor-context authentication change, every call here runs
the way the real add-on's calls arrive: through a simulated Supervisor
install, in the Supervisor system user's context, carrying the shared
probe secret (pinned on the first call).

The tests at the bottom pin the add-on's own shell half of the contract
(work items 2.2, 2.3, 2.6): both service scripts must parse, the slug
regex the run script revalidates locally must match the integration's,
the jq slug loops must be the quoted while-read form, reverts must be
chain-scoped (no executable iptables-restore anywhere), and the finish
script must carry the stop-time recovery. Textual pins, not execution:
the scripts need bashio and iptables, so what CAN be checked here is that
the properties the plan names are present in the shipped text and cannot
silently regress.
"""
import re
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import DOMAIN, FIREWALL_TEST_EXPIRED_UNREPORTED
from custom_components.ha_soc.resource_watchdog import ADDON_SLUG_PATTERN
from custom_components.ha_soc.secrets_store import PROBE_PAIRING_SECRET_KEY

_SERVICE_DIR = (
    Path(__file__).resolve().parent.parent
    / "ha_soc_probe"
    / "rootfs"
    / "etc"
    / "services.d"
    / "ha_soc_probe_firewall"
)

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


# ---------------------------------------------------------------------------
# The add-on's shell half of the contract (work items 2.2, 2.3, 2.6).
# ---------------------------------------------------------------------------


def _script_text(name: str) -> str:
    return (_SERVICE_DIR / name).read_text(encoding="utf-8")


def _code_lines(text: str) -> list[str]:
    """The script's non-comment lines, so a mention in a comment (for
    example the explanation of WHY iptables-restore is banned) does not
    satisfy or violate an assertion about executable code."""
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_addon_scripts_parse() -> None:
    """bash -n on both service scripts: a syntax error in either would
    brick the firewall feature at add-on start."""
    for name in ("run", "finish"):
        result = subprocess.run(
            ["bash", "-n", str(_SERVICE_DIR / name)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{name} failed bash -n: {result.stderr}"


def test_addon_slug_validation_matches_core_regex() -> None:
    """Work item 2.2, add-on half: the run script revalidates every slug
    with the SAME regex the WS schema enforces, before any Docker URL is
    built, and every jq slug iteration is the quoted while-read form."""
    run = _script_text("run")
    # The regex in valid_slug is the integration's ADDON_SLUG_PATTERN
    # verbatim; comparing against the imported constant catches drift on
    # either side.
    assert f"grep -Eq '{ADDON_SLUG_PATTERN}'" in run
    code = "\n".join(_code_lines(run))
    # No unquoted for-loop over jq output is left anywhere; the quoted
    # form both prevents word-split/glob surprises and feeds valid_slug.
    assert "for slug in $(" not in code
    assert code.count("while IFS= read -r slug") == 3
    assert code.count("valid_slug ") >= 3
    # Each Docker URL is built from the fixed addon_ prefix plus the
    # validated slug, never from a raw delivered string.
    for line in _code_lines(run):
        if "containers/" in line and "docker" in line.lower():
            assert "${container}" in line


def test_addon_revert_is_chain_scoped_with_checked_backups() -> None:
    """Work item 2.3: both backups are taken and both exit statuses are
    checked before anything is applied; a revert flushes the dedicated
    chain and replays the chain snapshot; no executable line anywhere in
    either script runs iptables-restore."""
    run = _script_text("run")
    code_lines = _code_lines(run)
    code = "\n".join(code_lines)
    # The full-table dump is filter-scoped and its exit status is checked,
    # as is the chain snapshot's.
    assert 'iptables-save -t filter > "$(backup_path_for' in code
    assert "|| backups_ok=0" in code
    assert 'iptables -S "${CHAIN}" > "$(chain_backup_path_for' in code
    # The chain-scoped replay: flush the chain, replay -A lines, skip -N
    # (the case pattern only ever matches append lines for the chain).
    assert 'iptables -F "${CHAIN}"' in code
    assert '"-A ${CHAIN} "*' in code
    # Never a whole-table restore, in either script.
    for name in ("run", "finish"):
        for line in _code_lines(_script_text(name)):
            assert "iptables-restore" not in line, f"{name}: {line!r}"


def test_addon_finish_runs_stop_time_recovery() -> None:
    """Work item 2.6: the finish script reverts an unresolved test before
    exiting, so a deliberate add-on stop restores the pre-test chain
    immediately instead of leaving it to a startup that may never come."""
    finish = _script_text("finish")
    code = "\n".join(_code_lines(finish))
    # It reads the armed-test state file, checks the resolved marker, and
    # reverts through the same chain-scoped machinery as the run script.
    assert 'CURRENT_TEST_FILE="${STATE_DIR}/ha_soc_fw_current_test_id"' in code
    assert "resolved_marker_for" in code
    assert 'revert_test "${stale_test_id}"' in code
    assert 'iptables -F "${CHAIN}"' in code
    # And it reports the revert with the shared probe secret, so Core's
    # record resolves promptly when the network path still exists.
    assert "firewall_resolved_status" in code
