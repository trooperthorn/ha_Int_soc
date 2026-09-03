"""Host firewall rules, read AND write, via the optional HA SOC Probe add-on's
NET_ADMIN capability.

The one module in this project that mutates a host security control. Core
proposes and displays; the add-on is the only thing that touches iptables,
and its own report is always the final word on what is active. The state
machine, wire protocol, and authentication are in docs/design.md,
docs/protocol.md, and docs/security.md.
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
    """None/empty = any source; otherwise a real IP address or CIDR network,
    validated here so a malformed value never reaches iptables."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise vol.Invalid("source must be an IP address or CIDR string")
    try:
        # strict=False allows host bits set (192.168.1.5/24), which iptables accepts and normalizes.
        ipaddress.ip_network(value, strict=False)
    except ValueError as err:
        raise vol.Invalid(f"invalid source (not an IP/CIDR): {value!r}") from err
    return value


def _derive_rule_family(rule: dict[str, Any]) -> dict[str, Any]:
    """Settle a validated rule's address family: derived from the source when
    present, "both" when there is no source; a contradicting explicit value
    is rejected. Runs after field validation, so ``source`` is already valid.
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
            # None = any source; validated as a real IP/CIDR by _valid_source.
            vol.Optional("source"): _valid_source,
            # "4" iptables, "6" ip6tables, "both" mirrored into both; settled by _derive_rule_family.
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

    The local import avoids the circular import with __init__.py at module load.
    """
    from . import get_runtime_data

    try:
        return get_runtime_data(hass).audit
    except RuntimeError:
        return None


async def async_verify_or_pin_secret(
    secrets: HaSocSecretStore, presented: str | None
) -> bool:
    """Shared-secret check for the add-on's inbound calls, defense in depth
    behind probe.py's Supervisor-context gate.

    Returns True when the call is trusted (matches, or pins a fresh secret),
    False when it must be rejected. A missing secret is always rejected.
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
    ``partially_applied``; called only when the add-on reported
    ``ipv6_supported: false``. Copies, because the flag is computed at read
    time and is not part of the frozen record.
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
    """Everything the Firewall Rules card needs: known rules per the add-on's
    last report, any in-flight test, and ``ipv6_supported``.
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
    """Relabel a pending test whose window passed with no report as
    "expired_unreported". Display-only: never touches iptables and never
    clears the pending slot.
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

    The backup acknowledgement is enforced here, not only in the frontend.
    """
    if not backup_acknowledged:
        return False, "backup_not_acknowledged", None

    try:
        rules = RULES_SCHEMA(rules)
    except vol.Invalid as err:
        return False, f"invalid_rules: {err}", None

    fw = store.data["firewall"]
    if fw.get("pending") is not None:
        # One test at a time, whatever its status, until the add-on's report or the owner's discard archives it.
        return False, "test_pending_unreported", None

    pending = {
        "test_id": uuid4().hex,
        "proposed_rules": rules,
        "status": FIREWALL_TEST_TESTING,
        "requested_by": user_id,
        "requested_at": _iso_now(),
        # None until the add-on's poll actually applies it.
        "applied_at": None,
        # Re-anchored to applied_at plus the window when async_next_addon_command hands the apply out.
        "expires_at": (dt_util.utcnow() + timedelta(seconds=window_seconds)).isoformat(),
        "window_seconds": window_seconds,
    }
    fw["pending"] = pending
    store.async_schedule_save()
    return True, None, pending


async def async_confirm_test(
    hass: HomeAssistant, store: HaSocData, *, test_id: str, user_id: str
) -> tuple[bool, str | None]:
    """User clicked Apply: make the change permanent.

    Marks intent only; the add-on's local revert timer is cancelled on its next poll.
    """
    fw = store.data["firewall"]
    pending = fw.get("pending")
    if not pending or pending.get("test_id") != test_id:
        return False, "no_matching_test"
    if pending.get("status") not in (FIREWALL_TEST_TESTING, FIREWALL_TEST_EXPIRED_UNREPORTED):
        return False, f"test_not_pending (status={pending.get('status')})"

    # Intent only; async_report_from_addon is the one place a test moves into history.
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

    current_test_id is what the add-on itself has armed; it is compared
    against rather than trusting Core's own pending record.
    """
    fw = store.data["firewall"]
    pending = fw.get("pending")

    if not pending:
        return {"action": "none"}

    test_id = pending["test_id"]
    status = pending.get("status")
    addon_holds_test = current_test_id not in (None, "")

    if addon_holds_test and current_test_id != test_id:
        # Add-on still armed for another test; an apply here would overlap two tests on the same chain.
        return {"action": "none", "reason": "addon_holds_other_test"}

    if not addon_holds_test and status == FIREWALL_TEST_EXPIRED_UNREPORTED:
        # An empty poll after the window lapsed is the evidence the add-on's timer reverted; archive it.
        await async_report_from_addon(
            hass, store, known_rules=None, addon_reports_no_current_test=True
        )
        return {"action": "none"}

    if status == FIREWALL_TEST_TESTING and pending.get("applied_at") is None:
        window_seconds = pending.get(
            "window_seconds", DEFAULT_FIREWALL_TEST_WINDOW_SECONDS
        )
        pending["applied_at"] = _iso_now()
        # Re-anchor: the add-on arms its local revert timer only now, at apply.
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
        # The add-on is not tracking this test (already resolved, or a stale poll).
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
    """The add-on's report is always the final word on what is actually active.

    This is where the report path clears a pending test into history; the
    only other path is the owner's async_discard_pending.
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
            pending["reason"] = resolved_reason
        # A copy: history entries are frozen, and fw["pending"] is about to be cleared.
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
        # No explicit resolution arrived, but the add-on holds no test after the window: reverted by its timer.
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
            # user_id stays None on purpose: the add-on's timer, not a person, resolved this.
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
    """Owner-only escape hatch for an add-on gone silent mid-test.

    Archives the pending record as ``discarded_unreported``. Refused with
    ``no_pending_test`` or ``window_not_lapsed``; a record without a
    parseable expires_at is discardable immediately.
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
    # A copy, not the live reference: history entries are frozen.
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
