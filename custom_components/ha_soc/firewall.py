"""Host firewall rules — read AND write, via the optional HA SOC Probe
add-on's NET_ADMIN capability. Everything else in this project is
advisory: it observes and reports, never mutates a host security control.
This module is the one deliberate exception, so it earns extra care.

The whole feature exists to answer one question safely: "let me change
which ports are reachable from where, without risking locking myself out
of my own Home Assistant instance." The design that makes that safe:

  1. Every rule this project ever applies lives in ONE dedicated iptables
     chain, HA_SOC_RULES_CHAIN (see const.py) — never the raw INPUT chain,
     never anything Docker itself manages. A full ruleset backup
     (`iptables-save`) is still taken before every apply as defense in
     depth, but day-to-day this project's own footprint is exactly one
     chain it owns outright.
  2. A proposed ruleset is never permanent on arrival. It's "testing" for
     a fixed window (DEFAULT_FIREWALL_TEST_WINDOW_SECONDS) and only
     becomes permanent if a human explicitly confirms it within that
     window.
  3. The auto-revert-if-not-confirmed timer lives ENTIRELY inside the
     add-on process that applied the change — a local `sleep N &&
     restore-unless-confirmed` watcher, armed the instant the rules are
     applied. This is the one property that actually matters: if the new
     rules break the very channel HA Core uses to reach the add-on (or
     break Core's own reachability entirely), nothing here depends on
     that channel working again to trigger the revert. Core is told what
     happened after the fact, on the add-on's next report — it is never
     the thing that has to reach back out to make the revert happen.

This module is Core's half of that contract: the pending-test state
machine, rule validation, and the two-message protocol
(ha_soc.poll_firewall_command / the extended ha_soc.ingest_probe_result
payload) the add-on uses to pick up work and report what it actually did.
Core proposes and displays; the add-on is the only thing that ever
actually touches iptables, and its own report is always the final word on
what's really active — never Core's optimistic guess at what should have
happened.

One test at a time, enforced: while ``pending`` is occupied, whatever its
status, a new proposal is refused with ``test_pending_unreported``. Only
two paths ever clear ``pending`` into history: the add-on's own report
(async_report_from_addon), and the owner's explicit discard
(async_discard_pending, decision D-5). The lazy expiry that runs on
status reads is display-only and merely relabels a timed-out test
``expired_unreported``. When the add-on later polls while holding no
current test, that poll is the evidence its local timer reverted the
expired test, and the record is archived as ``reverted`` by
``addon_timer``. When the add-on instead goes silent for good (stopped,
reinstalled, crashed), the owner, and only the owner, can archive the
record as ``discarded_unreported`` once the countdown has lapsed; nothing
ever unblocks automatically. A poll that arrives holding a DIFFERENT test
id than ``pending`` is answered ``none`` with reason
``addon_holds_other_test`` so Core never asks the add-on to apply test B
while test A is still armed on the host. Whenever a test moves to history,
an audit record is written: ``firewall_resolved`` with actor_source
``addon`` for the report path (work item 1.4), because the add-on's
report is the event that actually settled host firewall state, and
``firewall_pending_discarded`` naming the owner for the discard path.

The countdown is re-anchored at apply time (recorded intent statement,
work plan section 2): ``expires_at`` starts as propose time plus the
window, which bounds a stale proposal the add-on never picks up, and is
recomputed to ``applied_at`` plus the window the moment the apply command
is handed to the add-on, because that is when the add-on arms its own
local revert timer. The panel countdown therefore tracks the add-on's
real timer instead of running up to one poll interval ahead of it.

Rules are dual-stack by default (work item 2.4, decision D-3): every rule
carries a ``family`` of "4", "6", or "both". A rule with a source address
is pinned to that address's family (derived by the schema; a
contradicting explicit value is rejected), a rule with no source defaults
to "both", and the add-on writes family 4 with iptables, 6 with
ip6tables, and both with both, into a chain named HA_SOC_RULES in each
table, with per-family backups and an atomic apply: a failure in either
table reverts both. The add-on's reports carry two additions for this:
``firewall_ipv6_supported`` (whether ``ip6tables -S`` works on the host,
stored here and returned by async_get_status; when False, every "6" and
"both" rule is surfaced ``partially_applied`` so an IPv4-only apply is
never shown as a clean success) and a bounded free-text
``firewall_resolved_reason`` (carried protocol item), stored on the
archived record so ``backup_failed`` and per-family apply failures are
visible in the panel instead of only in the add-on log.

Authentication of the add-on's inbound calls is two-layered as of the
Supervisor-context change in probe.py: the service handlers there reject
any call whose context user is not the Supervisor system user BEFORE this
module's shared-secret check runs, so the secret here is defense in depth,
not the only gate. A call that presents no secret is always rejected; the
old "nothing pinned and nothing presented" acceptance is gone. The pinned
secret itself is stored in the dedicated private secret store
(secrets_store.py) rather than the general HA SOC store, so the pairing
credential never sits in a world-readable storage file (work item SEC-1).
"""
from __future__ import annotations

from datetime import timedelta
import hmac
import ipaddress
import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import (
    DEFAULT_FIREWALL_TEST_WINDOW_SECONDS,
    FIREWALL_RULE_ACTIONS,
    FIREWALL_RULE_FAMILIES,
    FIREWALL_RULE_FAMILY_BOTH,
    FIREWALL_RULE_FAMILY_V4,
    FIREWALL_RULE_FAMILY_V6,
    FIREWALL_RULE_PROTOS,
    FIREWALL_TEST_CONFIRMED,
    FIREWALL_TEST_DISCARDED_UNREPORTED,
    FIREWALL_TEST_EXPIRED_UNREPORTED,
    FIREWALL_TEST_REVERTED,
    FIREWALL_TEST_TESTING,
)
from .secrets_store import PROBE_PAIRING_SECRET_KEY, HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_MAX_HISTORY = 50

def _valid_source(value: Any) -> Any:
    """None/empty = any source. Otherwise it must be a real IP address or
    CIDR network — validated here (not just as a free string) so a typo
    like a missing prefix length can't sail through to the add-on, where a
    malformed `iptables -s` argument would silently fail to apply and leave
    the operator believing a restrictive rule is live when it never was.
    """
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise vol.Invalid("source must be an IP address or CIDR string")
    try:
        # strict=False allows host bits set (e.g. 192.168.1.5/24), which
        # iptables itself accepts and normalizes.
        ipaddress.ip_network(value, strict=False)
    except ValueError as err:
        raise vol.Invalid(f"invalid source (not an IP/CIDR): {value!r}") from err
    return value


def _derive_rule_family(rule: dict[str, Any]) -> dict[str, Any]:
    """Settle a validated rule's address family (work item 2.4, D-3).

    A rule with a source address can only ever match traffic of that
    address's own family, so the family is DERIVED from the source and an
    explicit value that contradicts it is rejected outright rather than
    silently corrected: a rule that claims family 6 with an IPv4 source
    is a misunderstanding the operator needs to see, not a value to guess
    around. A rule with no source defaults to "both", because the verified
    host's LAN and VLAN carry global IPv6 (recorded D-21 facts) and an
    IPv4-only deny on a dual-stack host silently leaves the IPv6 path
    open. Runs after field validation, so ``source`` is already a real
    IP/CIDR (or None) here.
    """
    source = rule.get("source")
    if source is not None:
        derived = (
            FIREWALL_RULE_FAMILY_V6
            if ipaddress.ip_network(source, strict=False).version == 6
            else FIREWALL_RULE_FAMILY_V4
        )
        explicit = rule.get("family")
        if explicit is not None and explicit != derived:
            raise vol.Invalid(
                f"family {explicit!r} contradicts the source's address "
                f"family (source {source!r} is IPv{derived})"
            )
        rule["family"] = derived
    else:
        rule.setdefault("family", FIREWALL_RULE_FAMILY_BOTH)
    return rule


RULE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("action"): vol.In(FIREWALL_RULE_ACTIONS),
            vol.Required("proto"): vol.In(FIREWALL_RULE_PROTOS),
            vol.Required("port"): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            # None/omitted = applies to traffic from any source. Set to scope
            # a rule to one VLAN/subnet, the natural pairing with the Host
            # Probe's per-interface bind-address visibility. Validated as a real
            # IP/CIDR, not just any string (see _valid_source).
            vol.Optional("source"): _valid_source,
            # "4" = iptables, "6" = ip6tables, "both" = mirrored into both
            # tables' HA_SOC_RULES chain. Optional on the wire; settled by
            # _derive_rule_family above, which also validates it against
            # the source's own address family. known_rules entries reported
            # by the add-on carry "4" or "6" per chain the rule was read
            # from, through this same schema.
            vol.Optional("family"): vol.In(FIREWALL_RULE_FAMILIES),
        }
    ),
    _derive_rule_family,
)

RULES_SCHEMA = vol.All([RULE_SCHEMA], vol.Length(max=200))


def _iso_now() -> str:
    return dt_util.utcnow().isoformat()


def _async_runtime_audit(hass: HomeAssistant):
    """The runtime's AuditLog, or None when HA SOC is not set up.

    async_report_from_addon audits every test that moves to history (work
    item 1.4), but its callers - probe.py's service closures and
    async_next_addon_command below - carry only hass and the store, so the
    audit log is fetched from the entry's runtime data at use time. The
    local import avoids the circular import with __init__.py at module load
    (the same pattern websocket_api._runtime uses). In production the
    services that reach this module only exist while the entry is set up,
    so None here happens only in tests that drive this module without a
    config entry; those calls simply go unaudited rather than crashing the
    add-on's report path.
    """
    from . import get_runtime_data

    try:
        return get_runtime_data(hass).audit
    except RuntimeError:
        return None


async def async_verify_or_pin_secret(
    secrets: HaSocSecretStore, presented: str | None
) -> bool:
    """Shared-secret check for the add-on's inbound calls, defense in depth.

    The add-on generates a random secret once, persists it in its own /data,
    and sends it on every ingest/poll call. Core pins the first non-empty
    secret it sees, then requires an exact match forever after. Since the
    Supervisor-context change in probe.py, this is the SECOND gate, not the
    only one: the service handlers reject any call that did not arrive with
    the Supervisor system user's context before this function is ever
    called, so pinning can only happen on a call that already passed that
    check. The first-caller-pins race the old trust-on-first-use design had
    is therefore closed to anything that cannot call through the Supervisor
    proxy.

    The pinned value lives in the dedicated private secret store under
    secrets_store.PROBE_PAIRING_SECRET_KEY (work item SEC-1), never in the
    general HA SOC store, so the world-readable storage file carries no
    copy of it. That is why this function takes the secret store and is
    async: the pin is fetched at use time and written through the store's
    own immediate atomic save.

    A missing secret is a rejection, always. The old branch that accepted a
    call with nothing pinned and nothing presented is gone, because it let
    any local caller through until the real add-on's first report. An
    add-on build too old to send a secret is rejected until it is updated,
    and the panel's pairing reset (async_reset_addon_secret) remains the
    recovery for a lost or rotated secret.

    Returns True if the call is trusted (matches, or pins a fresh secret),
    False if it must be rejected. The comparison uses hmac.compare_digest
    so a forged caller cannot learn the pinned value byte by byte through
    timing.
    """
    presented = presented or None
    if presented is None:
        return False
    pinned = await secrets.async_get(PROBE_PAIRING_SECRET_KEY)
    if pinned is None:
        await secrets.async_set(PROBE_PAIRING_SECRET_KEY, presented)
        _LOGGER.info("HA SOC firewall: pinned the add-on's probe secret (first Supervisor-context call).")
        return True
    return hmac.compare_digest(presented, pinned)


async def async_reset_addon_secret(secrets: HaSocSecretStore) -> None:
    """Clear the pinned secret so the next non-empty one re-pins. Owner-only
    recovery for a lost/rotated add-on secret or a bad first-boot pin."""
    await secrets.async_set(PROBE_PAIRING_SECRET_KEY, None)


def _mark_rules_partial_ipv6(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copies of the given rules with every "6" and "both" rule flagged
    ``partially_applied`` (work item 2.4). Called only when the add-on has
    reported ``ipv6_supported: false``: on such a host the IPv6 half of a
    dual-stack rule (and the whole of a family-6 rule) was never written,
    and the card must show that instead of a silent IPv4-only success.
    This is the only surviving use of the old D-3 "IPv4 only" label.
    Copies, not the stored dicts, because the flag is a statement about the
    host's CURRENT capability, computed at read time, not part of the
    frozen record.
    """
    marked = []
    for rule in rules:
        rule = dict(rule)
        if rule.get("family", FIREWALL_RULE_FAMILY_BOTH) in (
            FIREWALL_RULE_FAMILY_V6,
            FIREWALL_RULE_FAMILY_BOTH,
        ):
            rule["partially_applied"] = True
        marked.append(rule)
    return marked


async def async_get_status(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the Firewall Rules card needs: what's actually active
    (per the add-on's last report — the only source of truth for that),
    any in-flight test, and whether the host kernel supports ip6tables at
    all (``ipv6_supported``: True/False as last reported by the add-on,
    None until any report has carried the field). When the add-on has
    reported False, every "6" and "both" rule in known_rules and in the
    pending test's proposed rules is returned with ``partially_applied``
    set, so the panel can never show a dual-stack rule as cleanly live on
    a host that only applied its IPv4 half.
    """
    fw = store.data["firewall"]
    _lazily_expire_if_stale(fw)
    ipv6_supported = fw.get("ipv6_supported")
    known_rules = fw.get("known_rules")
    pending = fw.get("pending")
    if ipv6_supported is False:
        if known_rules:
            known_rules = _mark_rules_partial_ipv6(known_rules)
        if pending:
            pending = dict(pending)
            pending["proposed_rules"] = _mark_rules_partial_ipv6(
                pending.get("proposed_rules") or []
            )
    return {
        "known_rules": known_rules,
        "known_rules_reported_at": fw.get("known_rules_reported_at"),
        "ipv6_supported": ipv6_supported,
        "pending": pending,
        "history": list(fw.get("history") or [])[-10:],
    }


def _lazily_expire_if_stale(fw: dict[str, Any]) -> None:
    """A pending test whose window has passed with no confirm/revert
    report yet is shown as "expired_unreported", not still "testing". The
    add-on's own local timer is what actually reverted it (or will,
    imminently), and the "unreported" half tells the panel to say the
    add-on has not confirmed the revert yet. This only keeps the UI honest
    about a countdown that's already hit zero; it is display-only, never
    touches iptables, and never clears the pending slot. The slot is
    cleared exclusively by async_report_from_addon.
    """
    pending = fw.get("pending")
    if not pending or pending.get("status") != FIREWALL_TEST_TESTING:
        return
    expires_at = dt_util.parse_datetime(pending["expires_at"])
    if expires_at is not None and dt_util.utcnow() >= expires_at:
        pending["status"] = FIREWALL_TEST_EXPIRED_UNREPORTED


async def async_propose_test(
    hass: HomeAssistant,
    store: HaSocData,
    *,
    rules: list[dict[str, Any]],
    backup_acknowledged: bool,
    user_id: str,
    window_seconds: int = DEFAULT_FIREWALL_TEST_WINDOW_SECONDS,
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Queue a ruleset for the add-on to apply and test. Returns
    (ok, error_reason, pending_record).

    The backup checkbox is enforced here too, not just in the frontend —
    a client-side-only gate on a destructive action is not a gate.
    """
    if not backup_acknowledged:
        return False, "backup_not_acknowledged", None

    try:
        rules = RULES_SCHEMA(rules)
    except vol.Invalid as err:
        return False, f"invalid_rules: {err}", None

    fw = store.data["firewall"]
    if fw.get("pending") is not None:
        # One test at a time, whatever its status. Even a pending record
        # the lazy expiry has already relabeled expired_unreported keeps
        # the slot occupied: until the add-on's own report (or the owner's
        # async_discard_pending) archives it, Core does not know what is
        # actually live on the host, and proposing test B on top of an
        # unaccounted test A is exactly the overlap this feature exists to
        # prevent.
        return False, "test_pending_unreported", None

    pending = {
        "test_id": uuid4().hex,
        "proposed_rules": rules,
        "status": FIREWALL_TEST_TESTING,
        "requested_by": user_id,
        "requested_at": _iso_now(),
        # Set once the add-on's poll picks this up and actually applies
        # it (async_next_addon_command below) — None means "queued, not
        # yet applied by the add-on".
        "applied_at": None,
        # Starts at propose time as the staleness bound for a proposal the
        # add-on never picks up, then gets re-anchored to applied_at plus
        # the window the moment async_next_addon_command hands the apply
        # out, because that is when the add-on arms its real local timer
        # (recorded intent statement, work plan section 2).
        "expires_at": (dt_util.utcnow() + timedelta(seconds=window_seconds)).isoformat(),
        "window_seconds": window_seconds,
    }
    fw["pending"] = pending
    store.async_schedule_save()
    return True, None, pending


async def async_confirm_test(
    hass: HomeAssistant, store: HaSocData, *, test_id: str, user_id: str
) -> tuple[bool, str | None]:
    """User clicked the renamed Apply button — make the change permanent.

    Marks intent immediately so the UI reflects it right away; the actual
    cancellation of the add-on's local revert timer happens on its next
    poll (async_next_addon_command), independent of this call.
    """
    fw = store.data["firewall"]
    pending = fw.get("pending")
    if not pending or pending.get("test_id") != test_id:
        return False, "no_matching_test"
    if pending.get("status") not in (FIREWALL_TEST_TESTING, FIREWALL_TEST_EXPIRED_UNREPORTED):
        return False, f"test_not_pending (status={pending.get('status')})"

    # Intent only — NOT archived here. The add-on's own report
    # (async_report_from_addon) is the one and only place a test gets
    # moved into history, so it's never archived twice (once optimistically
    # here, again when the add-on actually acknowledges it). Until that
    # report arrives, this pending record just sits here with an updated
    # status — harmless, and async_next_addon_command below already keys
    # off status + test_id, not "pending is None", to decide what to tell
    # the add-on next.
    pending["status"] = FIREWALL_TEST_CONFIRMED
    pending["resolved_at"] = _iso_now()
    pending["resolved_by"] = user_id
    store.async_schedule_save()
    return True, None


async def async_cancel_test(
    hass: HomeAssistant, store: HaSocData, *, test_id: str, user_id: str
) -> tuple[bool, str | None]:
    """User wants an immediate revert rather than waiting out the window."""
    fw = store.data["firewall"]
    pending = fw.get("pending")
    if not pending or pending.get("test_id") != test_id:
        return False, "no_matching_test"
    if pending.get("status") not in (FIREWALL_TEST_TESTING, FIREWALL_TEST_EXPIRED_UNREPORTED):
        return False, f"test_not_pending (status={pending.get('status')})"

    pending["status"] = FIREWALL_TEST_REVERTED
    pending["resolved_at"] = _iso_now()
    pending["resolved_by"] = user_id
    store.async_schedule_save()
    return True, None


async def async_next_addon_command(
    hass: HomeAssistant, store: HaSocData, *, current_test_id: str | None
) -> dict[str, Any]:
    """Answer the add-on's poll: apply / confirm / revert / none.

    current_test_id is whatever the add-on itself currently has an active
    local revert-timer armed for (or None) — comparing against that,
    rather than blindly trusting Core's own pending record, is what keeps
    this correct even if a poll cycle was missed or arrived out of order.
    Two consequences of that comparison are enforced here rather than left
    to the add-on's goodwill: an "apply" is never issued while the poll
    says a different test is still armed on the host, and an empty poll
    arriving for a pending test the display has already marked
    expired_unreported is treated as the add-on's evidence that its local
    timer reverted the test, which archives it.
    """
    fw = store.data["firewall"]
    pending = fw.get("pending")

    if not pending:
        return {"action": "none"}

    test_id = pending["test_id"]
    status = pending.get("status")
    addon_holds_test = current_test_id not in (None, "")

    if addon_holds_test and current_test_id != test_id:
        # The add-on is still armed for some OTHER test. Whatever Core
        # wants done with the current pending record must wait until the
        # add-on has resolved what it is holding; in particular, issuing
        # "apply" here would put test B live while test A's revert timer
        # is still running against the same chain.
        return {"action": "none", "reason": "addon_holds_other_test"}

    if not addon_holds_test and status == FIREWALL_TEST_EXPIRED_UNREPORTED:
        # The window lapsed with no resolution report, and now the add-on
        # itself says it holds no current test. That empty report after
        # the window is the evidence the add-on's local timer ran (or its
        # startup recovery reverted the leftover), so the record can be
        # archived honestly as reverted by the timer. async_report_from_addon
        # stays the single place a pending record moves into history.
        await async_report_from_addon(
            hass, store, known_rules=None, addon_reports_no_current_test=True
        )
        return {"action": "none"}

    if status == FIREWALL_TEST_TESTING and pending.get("applied_at") is None:
        window_seconds = pending.get(
            "window_seconds", DEFAULT_FIREWALL_TEST_WINDOW_SECONDS
        )
        pending["applied_at"] = _iso_now()
        # Re-anchor the countdown (recorded intent statement, work plan
        # section 2): the add-on arms its local revert timer only when it
        # actually applies the rules, so from this hand-off onward the
        # honest expiry is applied_at plus the window. The propose-time
        # expires_at that stood until now remains the staleness bound for
        # a proposal the add-on never picked up; recomputing here is what
        # keeps the panel countdown aligned with the add-on's real local
        # timer instead of up to one poll interval ahead of it.
        pending["expires_at"] = (
            dt_util.utcnow() + timedelta(seconds=window_seconds)
        ).isoformat()
        store.async_schedule_save()
        return {
            "action": "apply",
            "test_id": test_id,
            "rules": pending["proposed_rules"],
            "window_seconds": window_seconds,
        }

    if current_test_id != test_id:
        # Add-on isn't tracking this test (already applied+resolved on a
        # prior cycle, or this is a stale/unrelated poll) — nothing to do.
        return {"action": "none"}

    if status == FIREWALL_TEST_CONFIRMED:
        return {"action": "confirm", "test_id": test_id}
    if status == FIREWALL_TEST_REVERTED:
        return {"action": "revert", "test_id": test_id}

    return {"action": "none"}


async def async_report_from_addon(
    hass: HomeAssistant,
    store: HaSocData,
    *,
    known_rules: list[dict[str, Any]] | None,
    resolved_test_id: str | None = None,
    resolved_status: str | None = None,
    resolved_reason: str | None = None,
    ipv6_supported: bool | None = None,
    addon_reports_no_current_test: bool = False,
) -> None:
    """The add-on's report is always the final word on what's actually
    active — this never gets second-guessed against Core's own optimistic
    pending-state updates.

    ``resolved_reason`` is the add-on's bounded free-text explanation for
    a resolution (carried protocol item): ``backup_failed`` when a
    pre-test backup could not be written, or the failing rule and family
    when an apply failed in either table. It is stored on the archived
    record (and echoed in the audit detail) so the operator sees WHY a
    test came back ``reverted`` instead of having to read the add-on log.
    ``ipv6_supported`` is the add-on's per-cycle statement of whether
    ``ip6tables -S`` works on this host; it is stored whenever present so
    async_get_status can render partial IPv6 state honestly (item 2.4).

    This function is where the REPORT path clears a pending test into
    history; the only other path is the owner's explicit
    async_discard_pending below (decision D-5), which exists precisely for
    the case where no report will ever arrive. Two report shapes archive
    it here: an explicit resolution for the pending test's own id, and
    (via addon_reports_no_current_test, set by async_next_addon_command)
    the add-on polling with an empty current_test_id while the pending
    record has already aged into expired_unreported, which is the
    timer-ran evidence described there.
    Every archive writes a firewall_resolved audit record with
    actor_source "addon" (work item 1.4): the add-on's report - not any
    person's click - is what actually moved host firewall state to its
    final form, and the chain must say so.
    """
    fw = store.data["firewall"]
    if known_rules is not None:
        fw["known_rules"] = known_rules
        fw["known_rules_reported_at"] = _iso_now()
    if ipv6_supported is not None:
        fw["ipv6_supported"] = ipv6_supported

    archived = False
    pending = fw.get("pending")
    if (
        pending
        and resolved_test_id == pending.get("test_id")
        and resolved_status in (FIREWALL_TEST_CONFIRMED, FIREWALL_TEST_REVERTED)
    ):
        if pending.get("status") != resolved_status:
            _LOGGER.info(
                "Firewall test %s actually resolved as %s (Core had recorded %s)",
                resolved_test_id,
                resolved_status,
                pending.get("status"),
            )
        pending["status"] = resolved_status
        pending.setdefault("resolved_at", _iso_now())
        if resolved_reason:
            # The add-on's own explanation of the outcome (already
            # length-bounded by the ingest schema); stored on the record
            # the panel's history shows so a backup_failed or a per-family
            # apply failure is visible where the operator looks first.
            pending["reason"] = resolved_reason
        # A copy, not the live reference — fw["pending"] is about to be
        # cleared, but nothing should keep mutating a record that's
        # supposed to be a frozen point-in-time history entry from here on.
        history = list(fw.get("history") or [])
        history.append(dict(pending))
        fw["history"] = history[-_MAX_HISTORY:]
        fw["pending"] = None
        archived = True
    elif (
        pending
        and addon_reports_no_current_test
        and pending.get("status") == FIREWALL_TEST_EXPIRED_UNREPORTED
    ):
        # No explicit resolution ever arrived (the add-on's out-of-cycle
        # report was lost, or the add-on restarted), but the add-on now
        # reports it holds no test at all after the window lapsed. Its
        # local timer, or its startup recovery, reverted the rules; the
        # net effect on the host is the pre-test state, so the honest
        # archive status is "reverted", attributed to the add-on's timer
        # rather than to any person.
        _LOGGER.info(
            "Firewall test %s expired unreported and the add-on now polls "
            "empty-handed; archiving it as reverted by the add-on timer.",
            pending.get("test_id"),
        )
        pending["status"] = FIREWALL_TEST_REVERTED
        pending.setdefault("resolved_at", _iso_now())
        pending["resolved_by"] = "addon_timer"
        history = list(fw.get("history") or [])
        history.append(dict(pending))
        fw["history"] = history[-_MAX_HISTORY:]
        fw["pending"] = None
        archived = True

    if archived:
        audit = _async_runtime_audit(hass)
        if audit is not None:
            # user_id stays None on purpose: no Home Assistant user
            # performed this resolution, the add-on (or its timer) did,
            # and actor_source says so. reported_rule_count is the size of
            # the known-rules snapshot this same report carried, or None
            # when the report carried none (the timer-evidence archive
            # path always carries none).
            audit.async_log(
                "firewall_resolved",
                detail={
                    "actor_source": "addon",
                    "test_id": pending.get("test_id"),
                    "status": pending.get("status"),
                    "reason": pending.get("reason"),
                    "reported_rule_count": len(known_rules)
                    if known_rules is not None
                    else None,
                },
            )

    store.async_schedule_save()


async def async_discard_pending(
    hass: HomeAssistant, store: HaSocData, *, user_id: str
) -> tuple[bool, str | None]:
    """Owner-only escape hatch for an add-on gone silent mid-test (D-5).

    If the add-on is stopped, reinstalled, or crashes without recovering,
    its resolution report never arrives and the pending slot would stay
    occupied forever, blocking every future proposal. This is the one
    deliberate way out: the OWNER (enforced at the WS layer) archives the
    record into history as ``discarded_unreported`` with themselves as
    ``resolved_by``, which clears the slot. The status is honest about
    what Core knows: the outcome on the host was never reported, so the
    record does not claim the rules were reverted, only that the owner
    gave up waiting.

    Two refusals keep this from becoming an accidental bypass of the
    one-test-at-a-time rule:

    - ``no_pending_test`` when there is nothing to discard.
    - ``window_not_lapsed`` while the countdown is still running. Because
      expires_at is re-anchored to applied_at plus the window when the
      apply is handed out (see async_next_addon_command), a lapsed
      countdown here means the add-on's own local revert timer has also
      already fired if the add-on is alive at all; discarding earlier
      would race a report that may still arrive seconds later.

    A pending record without a parseable expires_at cannot be waited out,
    so it is discardable immediately rather than wedging the slot forever,
    which would defeat the escape hatch this function exists to be.

    Nothing here touches iptables and nothing ever calls this
    automatically; the add-on's report path (async_report_from_addon) and
    this owner action are the only two ways ``pending`` is ever cleared.
    Every discard writes a ``firewall_pending_discarded`` audit record
    (flushed immediately via the ``firewall_`` prefix).
    """
    fw = store.data["firewall"]
    _lazily_expire_if_stale(fw)
    pending = fw.get("pending")
    if not pending:
        return False, "no_pending_test"

    expires_at = dt_util.parse_datetime(pending.get("expires_at") or "")
    if expires_at is not None and dt_util.utcnow() < expires_at:
        return False, "window_not_lapsed"

    previous_status = pending.get("status")
    pending["status"] = FIREWALL_TEST_DISCARDED_UNREPORTED
    pending["resolved_at"] = _iso_now()
    pending["resolved_by"] = user_id
    # A copy, not the live reference, for the same aliasing reason as the
    # archive in async_report_from_addon: history entries are frozen.
    history = list(fw.get("history") or [])
    history.append(dict(pending))
    fw["history"] = history[-_MAX_HISTORY:]
    fw["pending"] = None

    audit = _async_runtime_audit(hass)
    if audit is not None:
        audit.async_log(
            "firewall_pending_discarded",
            user_id=user_id,
            detail={
                "test_id": pending.get("test_id"),
                "previous_status": previous_status,
                "requested_by": pending.get("requested_by"),
            },
        )
    store.async_schedule_save()
    return True, None
