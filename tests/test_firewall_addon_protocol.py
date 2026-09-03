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

import voluptuous as vol

from custom_components.ha_soc import firewall
from custom_components.ha_soc.const import (
    DOMAIN,
    FIREWALL_REPORT_REASON_MAX,
    FIREWALL_TEST_EXPIRED_UNREPORTED,
)
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
_SCANNER_SERVICE_DIR = _SERVICE_DIR.parent / "ha_soc_probe"

RULES = [{"action": "allow", "proto": "tcp", "port": 8123, "source": None}]
# The same rules after the schema settles the family: no source means the
# dual-stack default "both" (work item 2.4). Everything the service layer
# stores or hands to the add-on is in this normalized shape.
RULES_NORMALIZED = [{**RULES[0], "family": "both"}]
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
    assert response["rules"] == RULES_NORMALIZED


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
    # firewall_known_rules passes through RULE_SCHEMA at the service
    # layer, so the stored entries carry the settled family.
    assert fw["known_rules"] == RULES_NORMALIZED
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

    # Older/base add-on report shape, no firewall_* fields at all. Must
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


async def test_report_reason_is_stored_and_bounded(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """Carried protocol item: the ingest schema accepts a bounded optional
    firewall_resolved_reason, the reason lands on the archived history
    record (where the card shows it), and an overlong reason is rejected
    by the schema rather than stored. The add-on truncates to the same
    bound before sending, so the rejection only ever catches a caller that
    ignored the contract."""
    store = entry.runtime_data.store
    _, _, pending = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    test_id = pending["test_id"]
    await _poll(hass, supervisor_context)

    await _ingest(
        hass,
        supervisor_context,
        firewall_known_rules=[],
        firewall_resolved_test_id=test_id,
        firewall_resolved_status="reverted",
        firewall_resolved_reason="backup_failed",
    )
    fw = store.data["firewall"]
    assert fw["pending"] is None
    assert fw["history"][0]["status"] == "reverted"
    assert fw["history"][0]["reason"] == "backup_failed"

    # A reason at exactly the bound passes; one past it fails the schema.
    _, _, pending2 = await firewall.async_propose_test(
        hass, store, rules=RULES, backup_acknowledged=True, user_id="u1"
    )
    with pytest.raises(vol.Invalid):
        await _ingest(
            hass,
            supervisor_context,
            firewall_resolved_test_id=pending2["test_id"],
            firewall_resolved_status="reverted",
            firewall_resolved_reason="x" * (FIREWALL_REPORT_REASON_MAX + 1),
        )
    # The rejected call changed nothing: the second test is still pending.
    assert store.data["firewall"]["pending"]["test_id"] == pending2["test_id"]

    await _ingest(
        hass,
        supervisor_context,
        firewall_resolved_test_id=pending2["test_id"],
        firewall_resolved_status="reverted",
        firewall_resolved_reason="y" * FIREWALL_REPORT_REASON_MAX,
    )
    assert store.data["firewall"]["history"][-1]["reason"] == "y" * FIREWALL_REPORT_REASON_MAX


async def test_ingest_ipv6_supported_reaches_status(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """Work item 2.4: firewall_ipv6_supported travels the ingest protocol
    into the stored firewall state and out through async_get_status, and
    an older report that omits it leaves the last known answer alone."""
    store = entry.runtime_data.store
    await _ingest(hass, supervisor_context, firewall_ipv6_supported=False)
    status = await firewall.async_get_status(hass, store)
    assert status["ipv6_supported"] is False

    # A report without the field (older add-on build) does not erase it.
    await _ingest(hass, supervisor_context, open_ports=[{"port": 22, "proto": "tcp"}])
    status = await firewall.async_get_status(hass, store)
    assert status["ipv6_supported"] is False

    await _ingest(hass, supervisor_context, firewall_ipv6_supported=True)
    status = await firewall.async_get_status(hass, store)
    assert status["ipv6_supported"] is True


def _script_text(name: str) -> str:
    return (_SERVICE_DIR / name).read_text(encoding="utf-8")


def _scanner_script_text(name: str) -> str:
    return (_SCANNER_SERVICE_DIR / name).read_text(encoding="utf-8")


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
    """bash -n on all four service scripts (both services' run and
    finish): a syntax error in any of them would brick that half of the
    add-on at start or stop."""
    for service_dir in (_SERVICE_DIR, _SCANNER_SERVICE_DIR):
        for name in ("run", "finish"):
            result = subprocess.run(
                ["bash", "-n", str(service_dir / name)],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, (
                f"{service_dir.name}/{name} failed bash -n: {result.stderr}"
            )


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
    """Work items 2.3 and 2.4: backups are taken for BOTH address families
    and every exit status is checked before anything is applied; a revert
    flushes the dedicated chain and replays the chain snapshot per family;
    no executable line anywhere in either script runs iptables-restore or
    ip6tables-restore."""
    run = _script_text("run")
    code_lines = _code_lines(run)
    code = "\n".join(code_lines)
    # The full-table dumps are filter-scoped and their exit statuses are
    # checked, as are both chain snapshots' (the IPv6 pair is guarded by
    # the per-cycle ip6tables support probe).
    assert 'iptables-save -t filter > "$(backup_path_for' in code
    assert 'ip6tables-save -t filter > "$(backup6_path_for' in code
    assert "|| backups_ok=0" in code
    assert 'iptables -S "${CHAIN}" > "$(chain_backup_path_for' in code
    assert 'ip6tables -S "${CHAIN}" > "$(chain6_backup_path_for' in code
    # The chain-scoped replay: flush the chain (per family, via the
    # binary-selecting helper), replay -A lines, skip -N (the case
    # pattern only ever matches append lines for the chain).
    assert 'iptables -F "${CHAIN}"' in code
    assert '"${bin}" -F "${CHAIN}"' in code
    assert '"-A ${CHAIN} "*' in code
    # The apply-failure rollback is atomic across families: both chain
    # snapshots are replayed before the failure is reported.
    assert 'replay_chain_backup 4 "$(chain_backup_path_for' in code
    assert 'replay_chain_backup 6 "$(chain6_backup_path_for' in code
    # Never a whole-table restore, in either script, for either family.
    for name in ("run", "finish"):
        for line in _code_lines(_script_text(name)):
            assert "iptables-restore" not in line, f"{name}: {line!r}"
            assert "ip6tables-restore" not in line, f"{name}: {line!r}"


def test_addon_finish_runs_stop_time_recovery() -> None:
    """Work item 2.6: the finish script reverts an unresolved test before
    exiting, so a deliberate add-on stop restores the pre-test chains
    immediately instead of leaving it to a startup that may never come."""
    finish = _script_text("finish")
    code = "\n".join(_code_lines(finish))
    # It reads the armed-test state file, checks the resolved marker, and
    # reverts through the same chain-scoped, dual-family machinery as the
    # run script.
    assert 'CURRENT_TEST_FILE="${STATE_DIR}/ha_soc_fw_current_test_id"' in code
    assert "resolved_marker_for" in code
    assert 'revert_test "${stale_test_id}"' in code
    assert '"${bin}" -F "${CHAIN}"' in code
    assert "chain6_backup_path_for" in code
    # And it reports the revert with the shared probe secret, so Core's
    # record resolves promptly when the network path still exists.
    assert "firewall_resolved_status" in code


def test_addon_validates_delivered_rule_fields() -> None:
    """Work item 2.5: the run script revalidates every Core-delivered rule
    field (action, proto, port, source shape, family) and the window
    bounds locally, BEFORE any iptables argument is built, with value sets
    that match the integration's own schema vocabulary, so a compromised
    Core cannot use the add-on as an arbitrary iptables client. Textual
    parity pins, like the slug test above."""
    run = _script_text("run")
    code = "\n".join(_code_lines(run))
    # The allowlists mirror const.py's FIREWALL_RULE_ACTIONS /
    # FIREWALL_RULE_PROTOS / FIREWALL_RULE_FAMILIES vocabularies.
    assert 'valid_action() { [ "$1" = "allow" ] || [ "$1" = "deny" ]; }' in code
    assert 'valid_proto() { [ "$1" = "tcp" ] || [ "$1" = "udp" ]; }' in code
    assert 'valid_family() { [ "$1" = "4" ] || [ "$1" = "6" ] || [ "$1" = "both" ]; }' in code
    for fn in ("valid_port", "valid_window", "valid_source_for_family"):
        assert f"{fn}()" in code, fn
    # The whole ruleset is validated before the chain is touched, and both
    # a bounds failure and a field failure refuse with a reported reason.
    assert "validate_ruleset" in code
    assert "rejected by add-on" in run
    # Delivered test ids become /data file names; they pass the same token
    # allowlist as add-on slugs before any path is built from them.
    assert 'valid_slug "${test_id}"' in code


def test_addon_reason_bound_matches_core_schema() -> None:
    """Carried protocol item: the add-on truncates its resolution reason
    to the same bound Core's ingest schema enforces
    (FIREWALL_REPORT_REASON_MAX), so an honest long reason is shortened
    rather than making Core reject the entire report."""
    run = _script_text("run")
    assert f"REASON_MAX_CHARS={FIREWALL_REPORT_REASON_MAX}" in run
    code = "\n".join(_code_lines(run))
    assert 'head -c "${REASON_MAX_CHARS}"' in code
    # The finish script reports through the same field and bound.
    finish_code = "\n".join(_code_lines(_script_text("finish")))
    assert f"head -c {FIREWALL_REPORT_REASON_MAX}" in finish_code
    for name in ("run", "finish"):
        assert "firewall_resolved_reason" in _script_text(name), name
        assert "firewall_ipv6_supported" in _script_text(name), name


def test_addon_dual_family_chain_and_known_rules() -> None:
    """Work item 2.4: ensure_chain creates and jumps the chain in both
    tables (the IPv6 half guarded by the support probe), and known_rules
    is built as the union of both chains with a family per entry."""
    run = _script_text("run")
    code = "\n".join(_code_lines(run))
    assert 'ip6tables -N "${CHAIN}"' in code
    assert 'ip6tables -I INPUT -j "${CHAIN}"' in code
    assert "probe_ipv6_supported" in code
    assert 'ip6tables -S >/dev/null 2>&1' in code
    # The known-rules builder emits family per chain and unions the two.
    assert "chain_rules_lines 4" in code
    assert "chain_rules_lines 6" in code
    assert '\\"family\\":\\"%s\\"' in run


def test_addon_graceful_stop_and_clean_finish() -> None:
    """Carried item (open-items report section 5): both run scripts trap
    TERM/INT and exit 0 through an interruptible sleep, and both finish
    scripts log a zero exit as a clean stop instead of a restart warning,
    so a routine add-on stop or update no longer reads as a crash loop.
    The firewall run script's trap must NOT revert anything itself: the
    finish script owns stop-time recovery, and the resolved marker keeps
    the revert exactly-once between them."""
    for text in (_script_text("run"), _scanner_script_text("run")):
        code = "\n".join(_code_lines(text))
        assert "trap on_stop_signal TERM INT" in code
        assert "STOP_REQUESTED=1" in code
        assert "interruptible_sleep" in code
        assert "exit 0" in code
    # The firewall trap handler only sets the flag; revert_test appears
    # nowhere between the handler's braces (it is a one-liner by design).
    run = _script_text("run")
    assert "on_stop_signal() {\n    STOP_REQUESTED=1\n}" in run
    for text in (_script_text("finish"), _scanner_script_text("finish")):
        code = "\n".join(_code_lines(text))
        assert '-eq 0 ]' in code
        assert "stopped cleanly" in code


def test_addon_scanner_service_drops_privileges() -> None:
    """Work item 2.5: the port-scanner service re-execs itself under
    s6-setuidgid nobody after its two root-only setup steps (secret
    creation, options.json read), and the root-owned 0600 secret file is
    handed down by value in the environment rather than loosened on disk.
    The firewall service, by contrast, must NOT drop: iptables needs root
    plus NET_ADMIN."""
    scanner = _scanner_script_text("run")
    code = "\n".join(_code_lines(scanner))
    assert 's6-setuidgid nobody' in code
    assert '[ "$(id -u)" -eq 0 ]' in code
    # The secret's value travels via the environment; the dropped half
    # never needs to read the root-owned file.
    assert "HA_SOC_PROBE_SECRET" in code
    assert "HA_SOC_SCAN_INTERVAL_HOURS" in code
    # The firewall poller stays root: no privilege drop anywhere in it.
    fw_code = "\n".join(_code_lines(_script_text("run")))
    assert "s6-setuidgid" not in fw_code
