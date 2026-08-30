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
the add-on's own report (async_report_from_addon) ever clears ``pending``
into history; the lazy expiry that runs on status reads is display-only
and merely relabels a timed-out test ``expired_unreported``. When the
add-on later polls while holding no current test, that poll is the
evidence its local timer reverted the expired test, and the record is
archived as ``reverted`` by ``addon_timer``. A poll that arrives holding a
DIFFERENT test id than ``pending`` is answered ``none`` with reason
``addon_holds_other_test`` so Core never asks the add-on to apply test B
while test A is still armed on the host.

Authentication of the add-on's inbound calls is two-layered as of the
Supervisor-context change in probe.py: the service handlers there reject
any call whose context user is not the Supervisor system user BEFORE this
module's shared-secret check runs, so the secret here is defense in depth,
not the only gate. A call that presents no secret is always rejected; the
old "nothing pinned and nothing presented" acceptance is gone.
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
    FIREWALL_RULE_PROTOS,
    FIREWALL_TEST_CONFIRMED,
    FIREWALL_TEST_EXPIRED_UNREPORTED,
    FIREWALL_TEST_REVERTED,
    FIREWALL_TEST_TESTING,
)
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


RULE_SCHEMA = vol.Schema(
    {
        vol.Required("action"): vol.In(FIREWALL_RULE_ACTIONS),
        vol.Required("proto"): vol.In(FIREWALL_RULE_PROTOS),
        vol.Required("port"): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        # None/omitted = applies to traffic from any source. Set to scope
        # a rule to one VLAN/subnet — the natural pairing with the Host
        # Probe's per-interface bind-address visibility. Validated as a real
        # IP/CIDR, not just any string (see _valid_source).
        vol.Optional("source"): _valid_source,
    }
)

RULES_SCHEMA = vol.All([RULE_SCHEMA], vol.Length(max=200))


def _iso_now() -> str:
    return dt_util.utcnow().isoformat()


def async_verify_or_pin_secret(store: HaSocData, presented: str | None) -> bool:
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
    fw = store.data["firewall"]
    pinned = fw.get("addon_secret")
    presented = presented or None
    if presented is None:
        return False
    if pinned is None:
        fw["addon_secret"] = presented
        store.async_schedule_save()
        _LOGGER.info("HA SOC firewall: pinned the add-on's probe secret (first Supervisor-context call).")
        return True
    return hmac.compare_digest(presented, pinned)


def async_reset_addon_secret(store: HaSocData) -> None:
    """Clear the pinned secret so the next non-empty one re-pins. Owner-only
    recovery for a lost/rotated add-on secret or a bad first-boot pin."""
    store.data["firewall"]["addon_secret"] = None
    store.async_schedule_save()


async def async_get_status(hass: HomeAssistant, store: HaSocData) -> dict[str, Any]:
    """Everything the Firewall Rules card needs: what's actually active
    (per the add-on's last report — the only source of truth for that),
    and any in-flight test.
    """
    fw = store.data["firewall"]
    _lazily_expire_if_stale(fw)
    return {
        "known_rules": fw.get("known_rules"),
        "known_rules_reported_at": fw.get("known_rules_reported_at"),
        "pending": fw.get("pending"),
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
        # the slot occupied: until the add-on's own report (or the future
        # owner discard) archives it, Core does not know what is actually
        # live on the host, and proposing test B on top of an unaccounted
        # test A is exactly the overlap this feature exists to prevent.
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
        # Started at propose time, not at confirmed-applied time: the
        # add-on polls every ~5s, so the gap is small and this avoids an
        # extra round trip before the countdown can even start.
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
        pending["applied_at"] = _iso_now()
        store.async_schedule_save()
        return {
            "action": "apply",
            "test_id": test_id,
            "rules": pending["proposed_rules"],
            "window_seconds": pending.get("window_seconds", DEFAULT_FIREWALL_TEST_WINDOW_SECONDS),
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
    addon_reports_no_current_test: bool = False,
) -> None:
    """The add-on's report is always the final word on what's actually
    active — this never gets second-guessed against Core's own optimistic
    pending-state updates.

    This function is the ONLY place a pending test is ever cleared into
    history. Two report shapes archive it: an explicit resolution for the
    pending test's own id, and (via addon_reports_no_current_test, set by
    async_next_addon_command) the add-on polling with an empty
    current_test_id while the pending record has already aged into
    expired_unreported, which is the timer-ran evidence described there.
    """
    fw = store.data["firewall"]
    if known_rules is not None:
        fw["known_rules"] = known_rules
        fw["known_rules_reported_at"] = _iso_now()

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
        # A copy, not the live reference — fw["pending"] is about to be
        # cleared, but nothing should keep mutating a record that's
        # supposed to be a frozen point-in-time history entry from here on.
        history = list(fw.get("history") or [])
        history.append(dict(pending))
        fw["history"] = history[-_MAX_HISTORY:]
        fw["pending"] = None
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

    store.async_schedule_save()
