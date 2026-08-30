"""Rule-based detection engine over the HA SOC audit log.

Honesty principle (non-negotiable for this module): every rule below is
built only from signals `audit.py` actually captures. Where the "obvious"
version of a rule needs a signal Home Assistant does not expose anywhere,
it is NOT approximated with a guess. It is either re-derived from the
closest real signal available, or left unimplemented and documented as a
coverage gap here. Concretely, against the 12-rule spec this module was
designed against:

 1. Brute force - per USERNAME: NOT IMPLEMENTED. A per-user brute-force
    rule needs the attempted username on a failed login, and Home
    Assistant's ban middleware never logs one anywhere reachable from an
    integration (see audit.py's module docstring). `rule_id
    "brute_force_user"` is intentionally never emitted. Instead, rule 2
    below implements the closest real signal: brute force grouped by
    source IP.
 2. Brute force - per source IP: IMPLEMENTED as `brute_force_ip`.
 3. Password spraying (many usernames, one/few passwords, one attacker):
    NOT IMPLEMENTED, same missing-username reason as (1). Approximating
    it off IP alone would just be brute_force_ip again wearing a
    different name, so it is skipped rather than faked.
 4. Success after a failure burst: IMPLEMENTED as
    `success_after_failures`, using the successful login's IP to
    cross-reference recent failures from that same IP - this is the one
    place IP correlation legitimately substitutes for the missing
    username, because the successful event itself supplies the user_id.
    With `require_new_token` (secure default: on) the success must be a
    genuinely NEW refresh token - audit.py tags each login_ok record with
    whether it came from the previous-is-None branch of its token poll -
    so an ordinary token refresh can never satisfy the rule. With
    `derate_shared_ip` (secure default: on) the severity de-rates from
    CRITICAL to HIGH when the source IP carried logins from more than one
    user inside the window, because a shared household NAT explains the
    correlation as well as an attacker does.
 5. New-IP login: IMPLEMENTED as `new_ip_login`, WITHOUT amnesty: every
    `login_ok` since the per-user checkpoint is evaluated, not just the
    newest one. A prefix joins the trusted baseline only after being seen
    on `baseline_days_required` distinct days, baseline entries expire
    after `prefix_expiry_days` without a sighting, and a prefix is never
    consulted as trusted in the same pass that flagged it (trust is
    evaluated against the pre-pass snapshot). The very first pass for a
    user seeds the baseline silently, exactly like off_hours below,
    because on day one every prefix in the history would otherwise be
    "new".
 6. Off-hours anomaly: IMPLEMENTED as `off_hours_anomaly`. The first
    pass for a user fills the histogram and sets the checkpoint WITHOUT
    emitting; on later passes the burst threshold scales with the scanned
    span so a catch-up pass covering several intervals cannot fake a
    burst, and the pass `now` is used as both the query `until` and the
    checkpoint so no event is ever counted twice.
 7. Dormant account revival: IMPLEMENTED as `dormant_revival`.
 8. Privilege escalation: IMPLEMENTED as `privilege_escalation`. The
    per-user group snapshot is persisted in `user_baselines` (work item
    3.10), so an escalation that happens while HA SOC is stopped is
    detected on the first pass after restart instead of being silently
    re-baselined; only a user never observed before is baselined
    silently.
 9. Mass entity control burst: IMPLEMENTED as `mass_entity_burst`.
10. Token minting anomaly: IMPLEMENTED as `token_minting_anomaly`.
11. Disabled-user activity attempt: IMPLEMENTED as
    `disabled_user_activity`, bounded to one detection per
    (user, category) per pass (work item 3.2); the matching risk factor
    is capped in risk.py via the rule's `risk_cap_points` threshold.
12. Config/diagnostics exfiltration pattern: NOT IMPLEMENTED. `audit.py`
    has no capture path for diagnostics or backup downloads in this
    version (no bus event, no log hook) - this is a known coverage gap,
    not a silent omission.

Beyond that 12-rule spec, one rule watches HA SOC's own attack surface:
`probe_auth_rejected` (HIGH) fires from the audit category of the same
name, which probe.py writes whenever a call to the Probe callback
services fails the Supervisor-context or shared-secret check. At most one
detection is opened per (caller, hour); every underlying rejection stays
individually queryable in the audit log.

Tunable thresholds (work item 3.0, decision D-9): every rule parameter an
operator may reasonably tune lives in THRESHOLD_SPECS below - the secure
default, the inclusive allowed range, and the type. "Secure default"
means the most sensitive value that does not alert on ordinary
same-network activity: it misses the fewest attacks, at the cost of more
alerts, and the Settings tab says so next to the controls. Rules read
their live values through the one helper `thresholds(store, rule)`, which
merges the owner's stored overrides over the secure defaults - a missing
key therefore always means "secure default", never "off". Changing a
threshold is owner-only (the Settings path), audited as
`soc_config_change` with a per-field diff, and reversible in one action
via the "Reset to secure defaults" control
(`ha_soc/detections/thresholds_reset`).

Detection records are additive and explainable: every detection this
engine writes down states plainly which rule fired and why (`detail`),
and every rule's docstring below names its dominant false-positive shape
so an analyst reading the alert already knows how to sanity-check it.

Stability / idempotency: `async_run_pass` runs on a timer (every few
minutes, per __init__.py). Each rule computes a deterministic
`detection_id` as sha256(f"{rule_id}:{subject}:{bucket}")[:24], where
`bucket` is an hour-floor timestamp. Re-running the pass while the same
episode is still ongoing therefore updates the SAME store row instead of
forking a new one every five minutes; a still-ongoing episode that
crosses an hour boundary intentionally opens a new row for the new hour,
since "this has now gone on for another hour" is itself worth surfacing.
Closed episodes stay closed (work item 3.9): `_upsert_detection` bumps
`last_seen` only when the TRIGGERING EVENT's timestamp is newer than the
stored one - re-scanning the same stale events on a later pass changes
nothing - and `recurrence_count` counts distinct triggering events, not
how many passes happened to re-observe the same one. A detection's
`status` is never downgraded by re-detection: once an analyst has marked
a row `ack`/`resolved`, later re-detections never flip `status` back to
`open` (store.async_upsert_detection enforces the same rule for every
other writer, e.g. the resource watchdog).

Evidence retention (work item 3.3, decision D-6): at the end of every
pass the engine asks the store to prune `resolved` detections and
`resolved`/`dismissed` findings older than the `evidence_retention_days`
setting (default 365). Open and acknowledged items never expire.
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from .const import (
    DETECTION_OPEN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
)
from .store import HaSocData

if TYPE_CHECKING:
    # Deliberately not imported at runtime: this module stays independently
    # importable/testable even before audit.py / users.py exist, matching
    # the module-boundary convention used elsewhere in HA SOC (see
    # audit.py's comment on why it duplicates rather than imports from
    # users.py).
    from .audit import AuditLog
    from .users import UsersManager

_LOGGER = logging.getLogger(__name__)

# -- Rule identifiers ---------------------------------------------------
RULE_BRUTE_FORCE_IP = "brute_force_ip"
RULE_SUCCESS_AFTER_FAILURES = "success_after_failures"
RULE_NEW_IP_LOGIN = "new_ip_login"
RULE_OFF_HOURS_ANOMALY = "off_hours_anomaly"
RULE_DORMANT_REVIVAL = "dormant_revival"
RULE_PRIVILEGE_ESCALATION = "privilege_escalation"
RULE_MASS_ENTITY_BURST = "mass_entity_burst"
RULE_TOKEN_MINTING_ANOMALY = "token_minting_anomaly"
RULE_DISABLED_USER_ACTIVITY = "disabled_user_activity"
RULE_PROBE_AUTH_REJECTED = "probe_auth_rejected"

# -- Tunable thresholds (work item 3.0, decision D-9) ----------------------
# The single source of truth for every tunable detection parameter: its
# secure default, its inclusive allowed range, and (implicitly, via the
# default's type) whether it is an int, float, or bool. websocket_api.py
# derives the voluptuous validation schema and the Settings tab's rendered
# ranges from this table, so a value can never be stored outside its range
# and the UI can never drift from what the server enforces. Kept
# module-level here rather than in const.py on purpose: const.py's own
# docstring says module-local constants live next to the code that uses
# them, and only detections.py and risk.py read these.
#
# Ranges are inclusive. The table transcribes the work plan's item 3.0
# parameter set exactly; the plan is the review-approved authority on both
# the secure defaults and the bounds.
THRESHOLD_SPECS: dict[str, dict[str, dict[str, Any]]] = {
    RULE_BRUTE_FORCE_IP: {
        "failures": {"default": 5, "min": 3, "max": 100},
        "window_minutes": {"default": 15, "min": 5, "max": 120},
    },
    RULE_SUCCESS_AFTER_FAILURES: {
        "failures": {"default": 3, "min": 2, "max": 50},
        "window_minutes": {"default": 30, "min": 5, "max": 240},
        "require_new_token": {"default": True},
        "derate_shared_ip": {"default": True},
    },
    RULE_NEW_IP_LOGIN: {
        "ipv4_prefix": {"default": 24, "min": 16, "max": 32},
        "ipv6_prefix": {"default": 64, "min": 32, "max": 128},
        "baseline_days_required": {"default": 3, "min": 1, "max": 30},
        "prefix_expiry_days": {"default": 90, "min": 30, "max": 730},
        "learning_days": {"default": 7, "min": 1, "max": 90},
    },
    RULE_OFF_HOURS_ANOMALY: {
        "quiet_start_hour": {"default": 23, "min": 0, "max": 23},
        "quiet_end_hour": {"default": 6, "min": 0, "max": 23},
        "burst_threshold": {"default": 5, "min": 2, "max": 100},
        "ratio_threshold": {"default": 0.01, "min": 0.001, "max": 0.2},
        "learning_days": {"default": 7, "min": 1, "max": 90},
    },
    RULE_DORMANT_REVIVAL: {
        "dormant_days": {"default": 30, "min": 7, "max": 365},
        "min_account_age_days": {"default": 60, "min": 7, "max": 365},
    },
    RULE_MASS_ENTITY_BURST: {
        "calls": {"default": 20, "min": 5, "max": 500},
        "distinct_entities": {"default": 10, "min": 2, "max": 200},
        "window_minutes": {"default": 5, "min": 1, "max": 60},
    },
    RULE_TOKEN_MINTING_ANOMALY: {
        "tokens": {"default": 2, "min": 2, "max": 20},
        "window_hours": {"default": 24, "min": 1, "max": 168},
    },
    RULE_DISABLED_USER_ACTIVITY: {
        "risk_cap_points": {"default": 40, "min": 10, "max": 100},
    },
    RULE_PRIVILEGE_ESCALATION: {
        "risk_cap_points": {"default": 24, "min": 8, "max": 100},
    },
}


def secure_default_thresholds(rule: str) -> dict[str, Any]:
    """The secure defaults for one rule, as a plain {param: value} dict."""
    return {name: spec["default"] for name, spec in THRESHOLD_SPECS[rule].items()}


def thresholds(store: HaSocData, rule: str) -> dict[str, Any]:
    """Effective thresholds for `rule`: stored overrides over secure defaults.

    The merge direction is the whole point (work item 3.0): a key missing
    from the stored settings always resolves to its secure default, so a
    partially-written or older settings blob can never silently turn a
    rule off or leave a parameter undefined. Unknown stored keys (from a
    future version, or a hand-edited store) are ignored rather than
    trusted.
    """
    effective = secure_default_thresholds(rule)
    stored = (store.settings.get("detection_thresholds") or {}).get(rule) or {}
    for key, value in stored.items():
        if key in effective:
            effective[key] = value
    return effective


# -- Non-tunable per-rule query bounds -------------------------------------
# Lookbacks and query limits are deliberately NOT in THRESHOLD_SPECS: they
# bound how much history a pass reads, not what the rule considers
# suspicious, and letting an operator shrink them would quietly blind a
# rule rather than tune it.
BRUTE_FORCE_IP_LOOKBACK_DAYS = 7
BRUTE_FORCE_IP_QUERY_LIMIT = 10000

SUCCESS_AFTER_FAILURES_LOOKBACK_HOURS = 24
SUCCESS_AFTER_FAILURES_QUERY_LIMIT = 5000

NEW_IP_LOGIN_BASELINE_LOOKBACK_DAYS = 30
NEW_IP_LOGIN_QUERY_LIMIT = 10000
# Distinct sighting days retained per baseline prefix. Only
# baseline_days_required (max 30) of them ever matter for trust, and
# expiry keys off last_seen, so the list is capped to keep a long-lived
# prefix entry from growing without bound.
NEW_IP_LOGIN_MAX_TRACKED_DAYS = 90

OFF_HOURS_INITIAL_SCAN_LOOKBACK_DAYS = 30
OFF_HOURS_QUERY_LIMIT = 5000

DORMANT_REVIVAL_LOOKBACK_DAYS = 400
DORMANT_REVIVAL_QUERY_LIMIT = 10000

ADMIN_GROUP_ID = "system-admin"
PRIVILEGE_ESCALATION_ACTOR_LOOKBACK_MINUTES = 15
PRIVILEGE_ESCALATION_ACTOR_QUERY_LIMIT = 200

MASS_ENTITY_BURST_LOOKBACK_MINUTES = 30
MASS_ENTITY_BURST_QUERY_LIMIT = 10000

TOKEN_MINTING_LOOKBACK_HOURS = 24
TOKEN_MINTING_QUERY_LIMIT = 2000

DISABLED_USER_ACTIVITY_LOOKBACK_HOURS = 24
DISABLED_USER_ACTIVITY_CATEGORIES = ("login_ok", "service_call", "token_created")
DISABLED_USER_ACTIVITY_QUERY_LIMIT = 5000

PROBE_AUTH_REJECTED_LOOKBACK_HOURS = 24
PROBE_AUTH_REJECTED_QUERY_LIMIT = 5000

# Distinct triggering-event timestamps kept per detection row, for the
# recurrence_count dedup (work item 3.9). Old entries fall off the front;
# an episode with more than this many distinct triggers within one hour
# bucket would merely undercount recurrences, never re-open or re-bump.
MAX_TRIGGER_EVENTS_TRACKED = 200


def _hour_bucket(moment: datetime) -> str:
    """Floor `moment` to the hour, as a stable string for detection ids."""
    return dt_util.as_utc(moment).replace(minute=0, second=0, microsecond=0).isoformat()


def _make_detection_id(rule_id: str, subject: str, bucket: str) -> str:
    raw = f"{rule_id}:{subject}:{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _network_prefix(
    ip: str, *, ipv4_prefix: int = 24, ipv6_prefix: int = 64
) -> str | None:
    """The baseline network prefix for an address, per address family.

    Work item 3.1: the old implementation applied /24 to everything, which
    is a defect for IPv6 - a /24 of a global IPv6 address lumps entire
    registries together, so every v6 login looked like it came from one
    "network". The prefix length now follows the address family, with the
    secure defaults /24 (IPv4) and /64 (IPv6, the standard end-site subnet
    size) supplied by the new_ip_login thresholds.
    """
    try:
        addr = ipaddress.ip_address(ip)
        prefix = ipv6_prefix if addr.version == 6 else ipv4_prefix
        return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False))
    except ValueError:
        return None


def _is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        # Not a parseable IP at all - treat conservatively as "private" so
        # it never gets flagged off garbage input.
        return True


def _analysis_interval() -> timedelta:
    """The periodic pass interval, read from __init__ at call time.

    Imported lazily because __init__ imports this module at load time; by
    the time a pass actually runs the package is fully loaded. The
    fallback matches the value __init__ has shipped with since the first
    release and only exists so an isolated unit import can never crash a
    rule.
    """
    try:
        from . import ANALYSIS_INTERVAL

        return ANALYSIS_INTERVAL
    except ImportError:  # pragma: no cover - package always importable in HA
        return timedelta(minutes=5)


def _in_quiet_window(hour: int, quiet_start: int, quiet_end: int) -> bool:
    """True when `hour` falls inside the [quiet_start, quiet_end) window.

    The window may wrap midnight (the secure default 23 -> 6 does). Equal
    start and end means a zero-length window - no hour is quiet - which is
    an explicit owner choice within the allowed range, not a failure mode.
    """
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= hour < quiet_end
    return hour >= quiet_start or hour < quiet_end


class DetectionEngine:
    """Runs all implemented detection rules against the audit log and store.

    Every rule call reuses the SAME `users.async_list_users()` snapshot and
    the SAME `now` for the whole pass, so results are internally consistent
    even though the pass takes a little wall-clock time to run.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        store: HaSocData,
        *,
        audit: "AuditLog",
        users: "UsersManager",
    ) -> None:
        self.hass = hass
        self.store = store
        self.audit = audit
        self.users = users

    async def async_run_pass(self) -> list[dict[str, Any]]:
        now = dt_util.utcnow()
        users = await self.users.async_list_users()
        users_by_id = {u["id"]: u for u in users}

        touched: list[dict[str, Any]] = []
        for rule in (
            self._rule_brute_force_ip,
            self._rule_success_after_failures,
            self._rule_new_ip_login,
            self._rule_off_hours_anomaly,
            self._rule_dormant_revival,
            self._rule_privilege_escalation,
            self._rule_mass_entity_burst,
            self._rule_token_minting_anomaly,
            self._rule_disabled_user_activity,
            self._rule_probe_auth_rejected,
        ):
            try:
                touched.extend(await rule(now, users, users_by_id))
            except Exception:  # noqa: BLE001 - one bad rule must not sink the pass
                _LOGGER.exception("HA SOC detection rule %s failed", rule.__name__)

        # Work item 3.3 (D-6): the periodic pass is where resolved
        # detections and resolved/dismissed findings past the evidence
        # retention period get pruned. Kept out of the rule loop so a rule
        # failure never blocks retention and vice versa.
        try:
            self.store.async_prune_evidence(now)
        except Exception:  # noqa: BLE001 - retention must never sink the pass
            _LOGGER.exception("HA SOC evidence retention sweep failed")

        # Work item 3.4 (D-10): record that a detection pass has completed,
        # so the posture engine can honestly claim its detection term has
        # computed at least once. Written even when individual rules failed
        # above - the term reflects that the engine ran, not that every
        # rule succeeded, and a partially-failed pass still evaluated the
        # open-detection state the term is built from.
        self.store.async_note_detection_pass_completed(
            dt_util.as_utc(now).isoformat()
        )

        return touched

    # -- Upsert helper --------------------------------------------------

    def _upsert_detection(
        self,
        *,
        rule_id: str,
        subject: str,
        bucket: str,
        severity: str,
        title: str,
        user_id: str | None,
        ip: str | None,
        detail: dict[str, Any],
        now: datetime,
        event_ts: datetime | None = None,
    ) -> dict[str, Any]:
        """Create or update the detection row for (rule, subject, bucket).

        `event_ts` is the timestamp of the TRIGGERING EVENT (work item
        3.9), not of the pass observing it. `last_seen` only ever advances
        to a newer event timestamp - a later pass re-reading the same
        stale events leaves the row untouched - and `recurrence_count`
        counts distinct triggering events via the recorded timestamp set.
        A rule with no single natural trigger event (an observation made
        at pass time, like a group-membership diff) omits `event_ts` and
        the pass `now` stands in for it.
        """
        detection_id = _make_detection_id(rule_id, subject, bucket)
        now_iso = dt_util.as_utc(now).isoformat()
        event_iso = dt_util.as_utc(event_ts or now).isoformat()
        existing = self.store.data["detections"].get(detection_id)

        if existing is not None:
            triggers = existing.setdefault(
                # A row written by an older build has no trigger list; its
                # stored last_seen is the only honest stand-in for the one
                # trigger it is known to have had.
                "trigger_event_ts",
                [existing.get("last_seen") or existing.get("ts")],
            )
            if event_iso not in triggers:
                triggers.append(event_iso)
                if len(triggers) > MAX_TRIGGER_EVENTS_TRACKED:
                    del triggers[: len(triggers) - MAX_TRIGGER_EVENTS_TRACKED]
                existing["recurrence_count"] = existing.get("recurrence_count", 1) + 1
                if event_iso > (existing.get("last_seen") or ""):
                    existing["last_seen"] = event_iso
                existing["detail"] = detail
            # status intentionally left untouched - never downgrade
            # ack/resolved back to open on re-detection.
            detection = existing
        else:
            detection = {
                "id": detection_id,
                "rule_id": rule_id,
                "severity": severity,
                "user_id": user_id,
                "ip": ip,
                "ts": now_iso,
                "last_seen": event_iso,
                "status": DETECTION_OPEN,
                "recurrence_count": 1,
                "trigger_event_ts": [event_iso],
                "title": title,
                "detail": detail,
            }

        self.store.async_upsert_detection(detection["id"], detection)
        return detection

    # -- Rule 2: brute_force_ip -------------------------------------------

    async def _rule_brute_force_ip(self, now, users, users_by_id):
        # False positive: a household's shared NAT/public IP (or a busy
        # guest network) can rack up failed logins from unrelated people
        # fat-fingering passwords, not one attacker.
        th = thresholds(self.store, RULE_BRUTE_FORCE_IP)
        since = now - timedelta(days=BRUTE_FORCE_IP_LOOKBACK_DAYS)
        events = await self.audit.async_query(
            since=since, category="login_fail", limit=BRUTE_FORCE_IP_QUERY_LIMIT
        )

        by_ip: dict[str, list[datetime]] = defaultdict(list)
        for ev in events:
            ip = ev.get("ip")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if ip and ts is not None:
                by_ip[ip].append(ts)

        window = timedelta(minutes=th["window_minutes"])
        results = []
        for ip, timestamps in by_ip.items():
            timestamps.sort()
            start = 0
            for end in range(len(timestamps)):
                while timestamps[end] - timestamps[start] > window:
                    start += 1
                count = end - start + 1
                if count >= th["failures"]:
                    trigger_ts = timestamps[end]
                    detail = {
                        "ip": ip,
                        "count_in_window": count,
                        "window_minutes": th["window_minutes"],
                        "failures_threshold": th["failures"],
                    }
                    results.append(
                        self._upsert_detection(
                            rule_id=RULE_BRUTE_FORCE_IP,
                            subject=ip,
                            bucket=_hour_bucket(trigger_ts),
                            severity=SEVERITY_HIGH,
                            title=f"Brute-force login attempts from {ip}",
                            user_id=None,
                            ip=ip,
                            detail=detail,
                            now=now,
                            event_ts=trigger_ts,
                        )
                    )
                    break  # one flag per ip per pass; bucket dedups anyway
        return results

    # -- Rule 4: success_after_failures ------------------------------------

    async def _rule_success_after_failures(self, now, users, users_by_id):
        # False positive: the account owner mistypes their password a
        # handful of times, then remembers it and logs in fine - same
        # shape as a real compromise but with intent instead of attack.
        # require_new_token (D-9, work item 3.8) removes the noisiest
        # sub-case: a background token refresh that merely happened to
        # share an IP with someone else's failures.
        th = thresholds(self.store, RULE_SUCCESS_AFTER_FAILURES)
        window = timedelta(minutes=th["window_minutes"])
        since = now - timedelta(hours=SUCCESS_AFTER_FAILURES_LOOKBACK_HOURS)
        fail_since = since - window

        ok_events = await self.audit.async_query(
            since=since, category="login_ok", limit=SUCCESS_AFTER_FAILURES_QUERY_LIMIT
        )
        fail_events = await self.audit.async_query(
            since=fail_since,
            category="login_fail",
            limit=SUCCESS_AFTER_FAILURES_QUERY_LIMIT,
        )

        fails_by_ip: dict[str, list[datetime]] = defaultdict(list)
        for ev in fail_events:
            ip = ev.get("ip")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if ip and ts is not None:
                fails_by_ip[ip].append(ts)
        for ip in fails_by_ip:
            fails_by_ip[ip].sort()

        # (user_id, ts) pairs per IP across the whole lookback, for the
        # derate_shared_ip check: an IP that carried logins from more than
        # one user around the same time is a shared egress (household NAT,
        # office network), which weakens the IP-correlation this rule
        # rests on - hence HIGH instead of CRITICAL, never a suppression.
        logins_by_ip: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
        for ev in ok_events:
            ip = ev.get("ip")
            uid = ev.get("user_id")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if ip and uid and ts is not None:
                logins_by_ip[ip].append((uid, ts))

        results = []
        for ev in ok_events:
            user_id = ev.get("user_id")
            ip = ev.get("ip")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if not user_id or not ip or ts is None:
                continue
            if th["require_new_token"] and not (ev.get("detail") or {}).get(
                "new_token"
            ):
                # Only a login_ok audit.py explicitly tagged as a NEW
                # refresh token qualifies. Records from before the tag
                # existed carry no field and are skipped the same way: the
                # rule's stated semantics are "a new token appeared", and
                # that cannot be proven for an untagged record.
                continue
            candidates = fails_by_ip.get(ip, [])
            count = sum(1 for f in candidates if ts - window <= f < ts)
            if count >= th["failures"]:
                severity = SEVERITY_CRITICAL
                if th["derate_shared_ip"]:
                    other_users = {
                        uid
                        for uid, login_ts in logins_by_ip.get(ip, [])
                        if uid != user_id and abs(login_ts - ts) <= window
                    }
                    if other_users:
                        severity = SEVERITY_HIGH
                detail = {
                    "ip": ip,
                    "fail_count": count,
                    "window_minutes": th["window_minutes"],
                    "new_token": bool((ev.get("detail") or {}).get("new_token")),
                    "shared_ip": severity == SEVERITY_HIGH,
                }
                name = users_by_id.get(user_id, {}).get("name", user_id)
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_SUCCESS_AFTER_FAILURES,
                        subject=f"{user_id}:{ip}",
                        bucket=_hour_bucket(ts),
                        severity=severity,
                        title=f"{name} logged in after {count} failed attempts from {ip}",
                        user_id=user_id,
                        ip=ip,
                        detail=detail,
                        now=now,
                        event_ts=ts,
                    )
                )
        return results

    # -- Rule 5: new_ip_login -----------------------------------------------

    async def _rule_new_ip_login(self, now, users, users_by_id):
        # False positive: mobile carrier CGNAT or a VPN hands out a
        # different public-looking prefix on every session even though it
        # is the same person on the same phone. The distinct-days baseline
        # requirement means such a user is flagged for the first
        # baseline_days_required days on each prefix - noisy, but that is
        # the recorded secure-default trade (D-9): amnesty for it would
        # also grant amnesty to an attacker's first login.
        th = thresholds(self.store, RULE_NEW_IP_LOGIN)
        now_iso = dt_util.as_utc(now).isoformat()
        since = now - timedelta(days=NEW_IP_LOGIN_BASELINE_LOOKBACK_DAYS)
        events = await self.audit.async_query(
            since=since, until=now, category="login_ok", limit=NEW_IP_LOGIN_QUERY_LIMIT
        )

        by_user: dict[str, list[dict]] = defaultdict(list)
        for ev in events:
            uid = ev.get("user_id")
            if uid:
                by_user[uid].append(ev)

        results = []
        expiry = timedelta(days=th["prefix_expiry_days"])
        for user_id, user_events in by_user.items():
            baseline = self.store.data["user_baselines"].setdefault(user_id, {})
            prefix_baseline = self._prefix_baseline(baseline, now_iso)

            checkpoint_raw = baseline.get("new_ip_checkpoint")
            checkpoint = (
                dt_util.parse_datetime(checkpoint_raw) if checkpoint_raw else None
            )
            seeding = checkpoint is None

            # Expire baseline entries not sighted within prefix_expiry_days
            # (D-9): a prefix trusted last winter is a stranger again.
            for prefix in list(prefix_baseline):
                last_seen = dt_util.parse_datetime(
                    prefix_baseline[prefix].get("last_seen") or ""
                )
                if last_seen is None or now - last_seen > expiry:
                    del prefix_baseline[prefix]

            # Trust is evaluated against this PRE-PASS snapshot, which is
            # exactly what "never baseline a prefix in the pass that
            # flagged it" means: sightings recorded below can only make a
            # prefix trusted from the NEXT pass onward.
            required_days = th["baseline_days_required"]
            trusted = {
                prefix
                for prefix, entry in prefix_baseline.items()
                if entry.get("legacy_trusted")
                or len(set(entry.get("days") or [])) >= required_days
            }

            # Maturity gate: no flags until the user has learning_days of
            # observed login history (per-rule learning_days replaced the
            # old hard-coded 14-day constant, work items 3.0/3.5).
            first_seen_raw = baseline.get("first_login_seen_at")
            first_seen = (
                dt_util.parse_datetime(first_seen_raw) if first_seen_raw else None
            )

            # Work item 3.6: EVERY login since the checkpoint is evaluated,
            # not just the newest - the old code granted amnesty to all but
            # the last event of a burst.
            flagged: dict[str, tuple[datetime, str]] = {}
            for ev in sorted(user_events, key=lambda e: e.get("ts") or ""):
                ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
                if ts is None or (checkpoint is not None and ts <= checkpoint):
                    continue
                if first_seen is None or ts < first_seen:
                    first_seen = ts
                    baseline["first_login_seen_at"] = dt_util.as_utc(ts).isoformat()
                ip = ev.get("ip")
                if not ip or _is_private_ip(ip):
                    continue
                prefix = _network_prefix(
                    ip,
                    ipv4_prefix=th["ipv4_prefix"],
                    ipv6_prefix=th["ipv6_prefix"],
                )
                if prefix is None:
                    continue

                mature = (
                    first_seen is not None
                    and (now - first_seen).days >= th["learning_days"]
                )
                if not seeding and mature and prefix not in trusted:
                    # One detection per (user, prefix) per pass, anchored
                    # to the newest triggering login.
                    prev = flagged.get(prefix)
                    if prev is None or ts > prev[0]:
                        flagged[prefix] = (ts, ip)

                # Record the sighting AFTER trust evaluation. Flagged
                # prefixes accrue distinct days too: continued use across
                # baseline_days_required days is what eventually earns
                # trust, but never within the pass that flagged it.
                entry = prefix_baseline.setdefault(
                    prefix, {"days": [], "last_seen": None}
                )
                day = dt_util.as_utc(ts).date().isoformat()
                days = entry.setdefault("days", [])
                if day not in days:
                    days.append(day)
                    if len(days) > NEW_IP_LOGIN_MAX_TRACKED_DAYS:
                        del days[: len(days) - NEW_IP_LOGIN_MAX_TRACKED_DAYS]
                ts_iso = dt_util.as_utc(ts).isoformat()
                if ts_iso > (entry.get("last_seen") or ""):
                    entry["last_seen"] = ts_iso

            # The pass `now` is both the query `until` and the checkpoint,
            # so no login is ever evaluated twice (same contract as
            # off_hours, work item 3.7).
            baseline["new_ip_checkpoint"] = now_iso
            self.store.async_schedule_save()

            for prefix, (ts, ip) in flagged.items():
                name = users_by_id.get(user_id, {}).get("name", user_id)
                entry = prefix_baseline.get(prefix, {})
                detail = {
                    "ip": ip,
                    "prefix": prefix,
                    "distinct_days_seen": len(set(entry.get("days") or [])),
                    "baseline_days_required": required_days,
                }
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_NEW_IP_LOGIN,
                        subject=f"{user_id}:{prefix}",
                        bucket=_hour_bucket(ts),
                        severity=SEVERITY_MEDIUM,
                        title=f"Login from a new network for {name}",
                        user_id=user_id,
                        ip=ip,
                        detail=detail,
                        now=now,
                        event_ts=ts,
                    )
                )

        return results

    @staticmethod
    def _prefix_baseline(
        baseline: dict[str, Any], now_iso: str
    ) -> dict[str, dict[str, Any]]:
        """This user's prefix baseline, migrating the legacy flat list once.

        Pre-3.6 builds stored `seen_prefixes` as a plain list with no day
        tracking and no expiry. Those prefixes WERE the operative baseline
        under the old regime, so they are grandfathered as trusted
        (`legacy_trusted`) rather than re-flagged: re-alerting an owner
        about every network they have used for months would be noise, not
        sensitivity. They still expire like any other entry once unused
        for prefix_expiry_days, at which point re-earning trust takes the
        full distinct-days baseline like everything else.
        """
        prefix_baseline = baseline.get("prefix_baseline")
        if prefix_baseline is None:
            prefix_baseline = {}
            for prefix in baseline.pop("seen_prefixes", None) or []:
                prefix_baseline[prefix] = {
                    "days": [],
                    "last_seen": now_iso,
                    "legacy_trusted": True,
                }
            baseline["prefix_baseline"] = prefix_baseline
        return prefix_baseline

    # -- Rule 6: off_hours_anomaly -------------------------------------------

    async def _rule_off_hours_anomaly(self, now, users, users_by_id):
        # False positive: the account owner is travelling, jet-lagged, or
        # just can't sleep, and genuinely operates the house at 3am.
        th = thresholds(self.store, RULE_OFF_HOURS_ANOMALY)
        results = []
        baselines = self.store.data["user_baselines"]
        interval = _analysis_interval()

        for user in users:
            user_id = user["id"]
            baseline = baselines.setdefault(user_id, {})
            histogram = baseline.setdefault("hour_histogram", [0] * 24)

            checkpoint_raw = baseline.get("hour_histogram_updated_through")
            checkpoint = (
                dt_util.parse_datetime(checkpoint_raw) if checkpoint_raw else None
            )
            first_pass = checkpoint is None
            scan_since = checkpoint or (
                now - timedelta(days=OFF_HOURS_INITIAL_SCAN_LOOKBACK_DAYS)
            )

            # `until=now` matches the checkpoint written below (work item
            # 3.7): the next pass starts exactly where this one stopped,
            # so no event is ever histogrammed or burst-counted twice.
            events = await self.audit.async_query(
                since=scan_since,
                until=now,
                category="service_call",
                user_id=user_id,
                limit=OFF_HOURS_QUERY_LIMIT,
            )
            # context_parent_id is None => a direct user action, never an
            # automation acting under this user's context - automations
            # must never poison the learned baseline.
            direct_events = [e for e in events if e.get("context_parent_id") is None]

            if not baseline.get("learning_started_at") and direct_events:
                baseline["learning_started_at"] = min(
                    e["ts"] for e in direct_events if e.get("ts")
                )

            this_pass_counts = [0] * 24
            for ev in direct_events:
                ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
                if ts is None:
                    continue
                local_hour = dt_util.as_local(ts).hour
                histogram[local_hour] += 1
                this_pass_counts[local_hour] += 1

            baseline["hour_histogram_updated_through"] = dt_util.as_utc(now).isoformat()
            self.store.async_schedule_save()

            if first_pass:
                # Work item 3.7: the seeding pass fills the histogram and
                # sets the checkpoint SILENTLY. Its scan spans up to 30
                # days, so "count this pass" is meaningless as a burst
                # signal and emitting from it would flag a month of normal
                # life at once.
                continue

            learning_started_raw = baseline.get("learning_started_at")
            if not learning_started_raw:
                continue
            learning_started = dt_util.parse_datetime(learning_started_raw)
            if (
                learning_started is None
                or (now - learning_started).days < th["learning_days"]
            ):
                continue  # not mature yet - do nothing for this user

            total_activity = sum(histogram)
            if total_activity == 0:
                continue

            # A pass that covers more than one analysis interval (missed
            # timer ticks, a restart) sees proportionally more events, so
            # the burst threshold scales with the span (work item 3.7) -
            # otherwise a catch-up pass would fake a burst out of a normal
            # rate.
            span = now - scan_since
            scale = max(1.0, span / interval)
            effective_burst = th["burst_threshold"] * scale

            name = users_by_id.get(user_id, {}).get("name", user_id)
            for hour, count in enumerate(this_pass_counts):
                if count < effective_burst:
                    continue
                if not _in_quiet_window(
                    hour, th["quiet_start_hour"], th["quiet_end_hour"]
                ):
                    continue
                # Ratio includes this pass's own burst, which slightly
                # under-counts how rare the hour "historically" was - an
                # intentional, conservative simplification rather than
                # tracking a separate pre-burst snapshot.
                historical_ratio = histogram[hour] / total_activity
                if historical_ratio >= th["ratio_threshold"]:
                    continue

                detail = {
                    "hour": hour,
                    "count_this_pass": count,
                    "burst_threshold_effective": round(effective_burst, 1),
                    "historical_ratio": round(historical_ratio, 4),
                }
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_OFF_HOURS_ANOMALY,
                        subject=f"{user_id}:{hour}",
                        bucket=_hour_bucket(now),
                        severity=SEVERITY_MEDIUM,
                        title=f"Off-hours activity burst for {name}",
                        user_id=user_id,
                        ip=None,
                        detail=detail,
                        now=now,
                    )
                )

        return results

    # -- Rule 7: dormant_revival ---------------------------------------------

    async def _rule_dormant_revival(self, now, users, users_by_id):
        # False positive: a seasonal resident (vacation home, college kid
        # home for the summer) genuinely disappears for months at a time.
        th = thresholds(self.store, RULE_DORMANT_REVIVAL)
        since = now - timedelta(days=DORMANT_REVIVAL_LOOKBACK_DAYS)
        events = await self.audit.async_query(
            since=since, category="login_ok", limit=DORMANT_REVIVAL_QUERY_LIMIT
        )

        by_user: dict[str, list[dict]] = defaultdict(list)
        for ev in events:
            uid = ev.get("user_id")
            if uid:
                by_user[uid].append(ev)

        results = []
        for user in users:
            user_id = user["id"]
            account_age_days = user.get("account_age_days")
            if (
                account_age_days is None
                or account_age_days <= th["min_account_age_days"]
            ):
                continue

            user_events = by_user.get(user_id, [])
            if len(user_events) < 2:
                continue
            user_events.sort(key=lambda e: e["ts"])
            prev_ts = dt_util.parse_datetime(user_events[-2]["ts"])
            latest_ts = dt_util.parse_datetime(user_events[-1]["ts"])
            if prev_ts is None or latest_ts is None:
                continue

            gap_days = (latest_ts - prev_ts).days
            if gap_days > th["dormant_days"]:
                name = user.get("name", user_id)
                detail = {
                    "gap_days": gap_days,
                    "dormant_days_threshold": th["dormant_days"],
                    "previous_login_at": prev_ts.isoformat(),
                    "revival_login_at": latest_ts.isoformat(),
                }
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_DORMANT_REVIVAL,
                        subject=user_id,
                        bucket=_hour_bucket(latest_ts),
                        severity=SEVERITY_MEDIUM,
                        title=f"Dormant account active again: {name}",
                        user_id=user_id,
                        ip=None,
                        detail=detail,
                        now=now,
                        event_ts=latest_ts,
                    )
                )

        return results

    # -- Rule 8: privilege_escalation -----------------------------------------

    async def _rule_privilege_escalation(self, now, users, users_by_id):
        # False positive: none, by design - a legitimate promotion to admin
        # looks identical to an attacker granting themselves admin. This
        # rule is always logged as an audit trail entry, not treated as
        # proof of compromise; that judgment call belongs to whoever
        # reviews it.
        #
        # The per-user group snapshot is PERSISTED in user_baselines (work
        # item 3.10): an escalation performed while HA SOC (or all of Home
        # Assistant) was stopped is caught on the first pass after
        # restart, instead of being silently re-baselined the way the old
        # in-memory snapshot forced. Only a user with no stored snapshot
        # at all (never observed before) is baselined without comparison.
        results = []
        baselines = self.store.data["user_baselines"]

        for user in users:
            user_id = user["id"]
            current_groups = set(user.get("groups") or [])
            baseline = baselines.setdefault(user_id, {})
            previous_raw = baseline.get("groups_snapshot")
            previous_groups = set(previous_raw) if previous_raw is not None else None

            if (
                previous_groups is not None
                and ADMIN_GROUP_ID in current_groups
                and ADMIN_GROUP_ID not in previous_groups
            ):
                actor_user_id = await self._find_privilege_escalation_actor(user_id, now)
                name = user.get("name", user_id)
                detail = {"gained_group": ADMIN_GROUP_ID, "actor_user_id": actor_user_id}
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_PRIVILEGE_ESCALATION,
                        subject=user_id,
                        bucket=_hour_bucket(now),
                        severity=SEVERITY_HIGH,
                        title=f"{name} was granted admin privileges",
                        user_id=user_id,
                        ip=None,
                        detail=detail,
                        now=now,
                    )
                )

            if previous_groups != current_groups:
                baseline["groups_snapshot"] = sorted(current_groups)
                self.store.async_schedule_save()

        # Snapshots of deleted users are garbage-collected by
        # store.async_purge_user together with the rest of their baseline,
        # so no sweep is needed here.
        return results

    async def _find_privilege_escalation_actor(
        self, user_id: str, now: datetime
    ) -> str | None:
        """Best-effort: who performed the user_updated that granted admin.

        `user_updated` events' `detail` shape isn't guaranteed to carry the
        target user id at all - if it can't be resolved, this returns None
        rather than guessing.
        """
        since = now - timedelta(minutes=PRIVILEGE_ESCALATION_ACTOR_LOOKBACK_MINUTES)
        events = await self.audit.async_query(
            since=since,
            category="user_updated",
            limit=PRIVILEGE_ESCALATION_ACTOR_QUERY_LIMIT,
        )
        matches = [
            e
            for e in events
            if (e.get("detail") or {}).get("user_id") == user_id
            or (e.get("detail") or {}).get("target_user_id") == user_id
        ]
        if not matches:
            return None
        matches.sort(key=lambda e: e.get("ts", ""))
        return matches[-1].get("user_id")

    # -- Rule 9: mass_entity_burst --------------------------------------------

    async def _rule_mass_entity_burst(self, now, users, users_by_id):
        # False positive: a human manually tapping through many tiles for
        # a "goodnight"/"everyone's home" scene by hand instead of a script.
        th = thresholds(self.store, RULE_MASS_ENTITY_BURST)
        since = now - timedelta(minutes=MASS_ENTITY_BURST_LOOKBACK_MINUTES)
        events = await self.audit.async_query(
            since=since, category="service_call", limit=MASS_ENTITY_BURST_QUERY_LIMIT
        )

        by_user: dict[str, list[tuple[datetime, list[str]]]] = defaultdict(list)
        for ev in events:
            if ev.get("context_parent_id") is not None:
                continue  # automations must not count toward a human's burst
            uid = ev.get("user_id")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if uid and ts is not None:
                by_user[uid].append((ts, ev.get("entity_ids") or []))

        window = timedelta(minutes=th["window_minutes"])
        results = []
        for user_id, items in by_user.items():
            items.sort(key=lambda item: item[0])
            start = 0
            for end in range(len(items)):
                while items[end][0] - items[start][0] > window:
                    start += 1
                windowed = items[start : end + 1]
                if len(windowed) >= th["calls"]:
                    entities: set[str] = set()
                    for _, ent_ids in windowed:
                        entities.update(ent_ids)
                    if len(entities) >= th["distinct_entities"]:
                        name = users_by_id.get(user_id, {}).get("name", user_id)
                        detail = {
                            "event_count": len(windowed),
                            "distinct_entities": len(entities),
                            "window_minutes": th["window_minutes"],
                        }
                        results.append(
                            self._upsert_detection(
                                rule_id=RULE_MASS_ENTITY_BURST,
                                subject=user_id,
                                bucket=_hour_bucket(items[end][0]),
                                severity=SEVERITY_CRITICAL,
                                title=f"Mass entity control burst by {name}",
                                user_id=user_id,
                                ip=None,
                                detail=detail,
                                now=now,
                                event_ts=items[end][0],
                            )
                        )
                        break
        return results

    # -- Rule 10: token_minting_anomaly ---------------------------------------

    async def _rule_token_minting_anomaly(self, now, users, users_by_id):
        # False positive: the user is legitimately setting up several new
        # devices/integrations in one sitting (new phone, new add-on, etc).
        th = thresholds(self.store, RULE_TOKEN_MINTING_ANOMALY)
        since = now - timedelta(hours=TOKEN_MINTING_LOOKBACK_HOURS)
        events = await self.audit.async_query(
            since=since, category="token_created", limit=TOKEN_MINTING_QUERY_LIMIT
        )

        by_user: dict[str, list[datetime]] = defaultdict(list)
        for ev in events:
            uid = ev.get("user_id")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if uid and ts is not None:
                by_user[uid].append(ts)

        window = timedelta(hours=th["window_hours"])
        results = []
        for user_id, timestamps in by_user.items():
            timestamps.sort()
            start = 0
            for end in range(len(timestamps)):
                while timestamps[end] - timestamps[start] > window:
                    start += 1
                count = end - start + 1
                if count >= th["tokens"]:
                    name = users_by_id.get(user_id, {}).get("name", user_id)
                    detail = {"count_in_window": count, "window_hours": th["window_hours"]}
                    results.append(
                        self._upsert_detection(
                            rule_id=RULE_TOKEN_MINTING_ANOMALY,
                            subject=user_id,
                            bucket=_hour_bucket(timestamps[end]),
                            severity=SEVERITY_HIGH,
                            title=f"Multiple new tokens created for {name}",
                            user_id=user_id,
                            ip=None,
                            detail=detail,
                            now=now,
                            event_ts=timestamps[end],
                        )
                    )
                    break
        return results

    # -- Rule 11: disabled_user_activity --------------------------------------

    async def _rule_disabled_user_activity(self, now, users, users_by_id):
        # False positive: a forgotten wall tablet or an old script still
        # holding a token, quietly retrying against a since-deactivated
        # account - not necessarily anyone actively trying to get back in.
        #
        # Bounded (work item 3.2): ONE detection per (user, category) per
        # pass, bucketed by the pass rather than per event, so a retry
        # loop firing every few seconds cannot mint hundreds of rows out
        # of one stuck tablet. The matching risk factor is additionally
        # capped via this rule's risk_cap_points threshold in risk.py.
        disabled_ids = {u["id"] for u in users if u.get("is_active") is False}
        if not disabled_ids:
            return []

        since = now - timedelta(hours=DISABLED_USER_ACTIVITY_LOOKBACK_HOURS)
        results = []
        for category in DISABLED_USER_ACTIVITY_CATEGORIES:
            events = await self.audit.async_query(
                since=since, category=category, limit=DISABLED_USER_ACTIVITY_QUERY_LIMIT
            )
            per_user: dict[str, dict[str, Any]] = {}
            for ev in events:
                uid = ev.get("user_id")
                if uid not in disabled_ids:
                    continue
                ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
                if ts is None:
                    continue
                agg = per_user.setdefault(
                    uid, {"count": 0, "newest_ts": ts, "ip": ev.get("ip")}
                )
                agg["count"] += 1
                if ts > agg["newest_ts"]:
                    agg["newest_ts"] = ts
                    agg["ip"] = ev.get("ip")

            for uid, agg in per_user.items():
                name = users_by_id.get(uid, {}).get("name", uid)
                detail = {
                    "category": category,
                    "event_count": agg["count"],
                    "ip": agg["ip"],
                }
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_DISABLED_USER_ACTIVITY,
                        subject=f"{uid}:{category}",
                        bucket=_hour_bucket(now),
                        severity=SEVERITY_HIGH,
                        title=f"Activity attempt by disabled account {name}",
                        user_id=uid,
                        ip=agg["ip"],
                        detail=detail,
                        now=now,
                        event_ts=agg["newest_ts"],
                    )
                )
        return results

    # -- Extra rule: probe_auth_rejected --------------------------------------

    async def _rule_probe_auth_rejected(self, now, users, users_by_id):
        # False positive: an outdated Probe add-on build that predates the
        # probe_secret field keeps reporting without one and is rejected
        # with reason no_secret until it is updated - noisy, but honest,
        # since Core genuinely cannot tell it from a forger.
        since = now - timedelta(hours=PROBE_AUTH_REJECTED_LOOKBACK_HOURS)
        events = await self.audit.async_query(
            since=since,
            category="probe_auth_rejected",
            limit=PROBE_AUTH_REJECTED_QUERY_LIMIT,
        )

        # At most one detection per (caller, hour): the deterministic
        # detection id already collapses re-runs of the pass onto the same
        # row, and this in-pass set keeps a burst of rejections within one
        # hour from producing multiple upsert calls for that row.
        emitted: set[tuple[str, str]] = set()
        results = []
        for ev in events:
            detail_in = ev.get("detail") or {}
            caller = detail_in.get("caller_user_id") or "no_user_context"
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if ts is None:
                continue
            bucket = _hour_bucket(ts)
            if (caller, bucket) in emitted:
                continue
            emitted.add((caller, bucket))

            caller_user_id = detail_in.get("caller_user_id")
            name = users_by_id.get(caller_user_id, {}).get("name", caller)
            detail = {
                "service": detail_in.get("service"),
                "caller_user_id": caller_user_id,
                "reason": detail_in.get("reason"),
            }
            results.append(
                self._upsert_detection(
                    rule_id=RULE_PROBE_AUTH_REJECTED,
                    subject=caller,
                    bucket=bucket,
                    severity=SEVERITY_HIGH,
                    title=f"Probe callback rejected for {name}",
                    user_id=caller_user_id,
                    ip=None,
                    detail=detail,
                    now=now,
                    event_ts=ts,
                )
            )
        return results
