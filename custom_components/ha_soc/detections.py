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
 5. New-IP login: IMPLEMENTED as `new_ip_login`.
 6. Off-hours anomaly: IMPLEMENTED as `off_hours_anomaly`.
 7. Dormant account revival: IMPLEMENTED as `dormant_revival`.
 8. Privilege escalation: IMPLEMENTED as `privilege_escalation`.
 9. Mass entity control burst: IMPLEMENTED as `mass_entity_burst`.
10. Token minting anomaly: IMPLEMENTED as `token_minting_anomaly`.
11. Disabled-user activity attempt: IMPLEMENTED as
    `disabled_user_activity`.
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

Detection records are additive and explainable: every detection this
engine writes down states plainly which rule fired and why (`detail`),
and every rule's docstring below names its dominant false-positive shape
so an analyst reading the alert already knows how to sanity-check it.

Stability / idempotency: `async_run_pass` runs on a timer (every few
minutes, per __init__.py). Each rule computes a deterministic
`detection_id` as sha256(f"{rule_id}:{subject}:{bucket}")[:24], where
`bucket` is an hour-floor timestamp. Re-running the pass while the same
episode is still ongoing therefore updates the SAME store row (bumping
`last_seen` and `recurrence_count`) instead of forking a new one every
five minutes; a still-ongoing episode that crosses an hour boundary
intentionally opens a new row for the new hour, since "this has now gone
on for another hour" is itself worth surfacing. A detection's `status`
is never downgraded by re-detection: once an analyst has marked a row
`ack`/`resolved`, later re-detections only touch `last_seen` and
`recurrence_count`, never flip `status` back to `open`.
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

# -- Rule 2: brute_force_ip ----------------------------------------------
BRUTE_FORCE_IP_LOOKBACK_DAYS = 7
BRUTE_FORCE_IP_WINDOW_MINUTES = 15
BRUTE_FORCE_IP_THRESHOLD = 10
BRUTE_FORCE_IP_QUERY_LIMIT = 10000

# -- Rule 4: success_after_failures ---------------------------------------
SUCCESS_AFTER_FAILURES_LOOKBACK_HOURS = 24
SUCCESS_AFTER_FAILURES_WINDOW_MINUTES = 30
SUCCESS_AFTER_FAILURES_THRESHOLD = 5
SUCCESS_AFTER_FAILURES_QUERY_LIMIT = 5000

# -- Rule 5: new_ip_login --------------------------------------------------
NEW_IP_LOGIN_MIN_HISTORY_DAYS = 14
NEW_IP_LOGIN_BASELINE_LOOKBACK_DAYS = 30
NEW_IP_LOGIN_QUERY_LIMIT = 10000

# -- Rule 6: off_hours_anomaly ---------------------------------------------
OFF_HOURS_MIN_HISTORY_DAYS = 14
OFF_HOURS_INITIAL_SCAN_LOOKBACK_DAYS = 30
OFF_HOURS_BURST_THRESHOLD = 10
OFF_HOURS_RATIO_THRESHOLD = 0.01
OFF_HOURS_START_HOUR = 6  # local time, inclusive
OFF_HOURS_END_HOUR = 23  # local time, exclusive
OFF_HOURS_QUERY_LIMIT = 5000

# -- Rule 7: dormant_revival -----------------------------------------------
DORMANT_REVIVAL_GAP_DAYS = 60
DORMANT_REVIVAL_MIN_ACCOUNT_AGE_DAYS = 90
DORMANT_REVIVAL_LOOKBACK_DAYS = 400
DORMANT_REVIVAL_QUERY_LIMIT = 10000

# -- Rule 8: privilege_escalation ------------------------------------------
ADMIN_GROUP_ID = "system-admin"
PRIVILEGE_ESCALATION_ACTOR_LOOKBACK_MINUTES = 15
PRIVILEGE_ESCALATION_ACTOR_QUERY_LIMIT = 200

# -- Rule 9: mass_entity_burst ----------------------------------------------
MASS_ENTITY_BURST_LOOKBACK_MINUTES = 30
MASS_ENTITY_BURST_WINDOW_MINUTES = 5
MASS_ENTITY_BURST_EVENT_THRESHOLD = 30
MASS_ENTITY_BURST_ENTITY_THRESHOLD = 10
MASS_ENTITY_BURST_QUERY_LIMIT = 10000

# -- Rule 10: token_minting_anomaly -----------------------------------------
TOKEN_MINTING_LOOKBACK_HOURS = 24
TOKEN_MINTING_WINDOW_HOURS = 24
TOKEN_MINTING_THRESHOLD = 3
TOKEN_MINTING_QUERY_LIMIT = 2000

# -- Rule 11: disabled_user_activity -----------------------------------------
DISABLED_USER_ACTIVITY_LOOKBACK_HOURS = 24
DISABLED_USER_ACTIVITY_CATEGORIES = ("login_ok", "service_call", "token_created")
DISABLED_USER_ACTIVITY_QUERY_LIMIT = 5000

# -- Extra rule: probe_auth_rejected ------------------------------------------
PROBE_AUTH_REJECTED_LOOKBACK_HOURS = 24
PROBE_AUTH_REJECTED_QUERY_LIMIT = 5000


def _hour_bucket(moment: datetime) -> str:
    """Floor `moment` to the hour, as a stable string for detection ids."""
    return dt_util.as_utc(moment).replace(minute=0, second=0, microsecond=0).isoformat()


def _make_detection_id(rule_id: str, subject: str, bucket: str) -> str:
    raw = f"{rule_id}:{subject}:{bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _network_prefix(ip: str) -> str | None:
    try:
        return str(ipaddress.ip_network(f"{ip}/24", strict=False))
    except ValueError:
        return None


def _is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        # Not a parseable IP at all - treat conservatively as "private" so
        # it never gets flagged off garbage input.
        return True


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

        # In-memory only, by design (see rule 8 below): lost on restart,
        # which just means the pass right after a restart cannot detect an
        # escalation that happened while HA SOC was down - it re-baselines
        # instead of flagging every existing admin as "newly escalated".
        self._group_snapshot: dict[str, set[str]] = {}

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
    ) -> dict[str, Any]:
        detection_id = _make_detection_id(rule_id, subject, bucket)
        now_iso = dt_util.as_utc(now).isoformat()
        existing = self.store.data["detections"].get(detection_id)

        if existing is not None:
            existing["last_seen"] = now_iso
            existing["recurrence_count"] = existing.get("recurrence_count", 1) + 1
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
                "last_seen": now_iso,
                "status": DETECTION_OPEN,
                "recurrence_count": 1,
                "title": title,
                "detail": detail,
            }

        self.store.async_upsert_detection(detection_id, detection)
        return detection

    # -- Rule 2: brute_force_ip -------------------------------------------

    async def _rule_brute_force_ip(self, now, users, users_by_id):
        # False positive: a household's shared NAT/public IP (or a busy
        # guest network) can rack up 10+ failed logins from unrelated
        # people fat-fingering passwords, not one attacker.
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

        window = timedelta(minutes=BRUTE_FORCE_IP_WINDOW_MINUTES)
        results = []
        for ip, timestamps in by_ip.items():
            timestamps.sort()
            start = 0
            for end in range(len(timestamps)):
                while timestamps[end] - timestamps[start] > window:
                    start += 1
                count = end - start + 1
                if count >= BRUTE_FORCE_IP_THRESHOLD:
                    trigger_ts = timestamps[end]
                    detail = {
                        "ip": ip,
                        "count_in_window": count,
                        "window_minutes": BRUTE_FORCE_IP_WINDOW_MINUTES,
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
                        )
                    )
                    break  # one flag per ip per pass; bucket dedups anyway
        return results

    # -- Rule 4: success_after_failures ------------------------------------

    async def _rule_success_after_failures(self, now, users, users_by_id):
        # False positive: the account owner mistypes their password a
        # handful of times, then remembers it and logs in fine - same
        # shape as a real compromise but with intent instead of attack.
        since = now - timedelta(hours=SUCCESS_AFTER_FAILURES_LOOKBACK_HOURS)
        fail_since = since - timedelta(minutes=SUCCESS_AFTER_FAILURES_WINDOW_MINUTES)

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

        window = timedelta(minutes=SUCCESS_AFTER_FAILURES_WINDOW_MINUTES)
        results = []
        for ev in ok_events:
            user_id = ev.get("user_id")
            ip = ev.get("ip")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if not user_id or not ip or ts is None:
                continue
            candidates = fails_by_ip.get(ip, [])
            count = sum(1 for f in candidates if ts - window <= f < ts)
            if count >= SUCCESS_AFTER_FAILURES_THRESHOLD:
                detail = {
                    "ip": ip,
                    "fail_count": count,
                    "window_minutes": SUCCESS_AFTER_FAILURES_WINDOW_MINUTES,
                }
                name = users_by_id.get(user_id, {}).get("name", user_id)
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_SUCCESS_AFTER_FAILURES,
                        subject=f"{user_id}:{ip}",
                        bucket=_hour_bucket(ts),
                        severity=SEVERITY_CRITICAL,
                        title=f"{name} logged in after {count} failed attempts from {ip}",
                        user_id=user_id,
                        ip=ip,
                        detail=detail,
                        now=now,
                    )
                )
        return results

    # -- Rule 5: new_ip_login -----------------------------------------------

    async def _rule_new_ip_login(self, now, users, users_by_id):
        # False positive: mobile carrier CGNAT or a VPN hands out a
        # different public-looking /24 on every session even though it is
        # the same person on the same phone.
        since = now - timedelta(days=NEW_IP_LOGIN_BASELINE_LOOKBACK_DAYS)
        events = await self.audit.async_query(
            since=since, category="login_ok", limit=NEW_IP_LOGIN_QUERY_LIMIT
        )

        by_user: dict[str, list[dict]] = defaultdict(list)
        for ev in events:
            uid = ev.get("user_id")
            if uid:
                by_user[uid].append(ev)

        results = []
        for user_id, user_events in by_user.items():
            user_events.sort(key=lambda e: e["ts"])
            oldest_ts = dt_util.parse_datetime(user_events[0]["ts"])
            latest_ev = user_events[-1]
            latest_ts = dt_util.parse_datetime(latest_ev["ts"])
            if oldest_ts is None or latest_ts is None:
                continue
            # Approximation: "history span" is measured within the 30-day
            # baseline query window, not the user's entire lifetime - a
            # deliberate simplification to keep this a single bounded query.
            if (now - oldest_ts).days < NEW_IP_LOGIN_MIN_HISTORY_DAYS:
                continue

            ip = latest_ev.get("ip")
            if not ip or _is_private_ip(ip):
                continue
            latest_prefix = _network_prefix(ip)
            if latest_prefix is None:
                continue

            baseline = self.store.data["user_baselines"].setdefault(user_id, {})
            seen_prefixes = set(baseline.get("seen_prefixes", []))

            prior_prefixes = set()
            for ev in user_events[:-1]:
                prior_ip = ev.get("ip")
                if not prior_ip or _is_private_ip(prior_ip):
                    continue
                prefix = _network_prefix(prior_ip)
                if prefix is not None:
                    prior_prefixes.add(prefix)

            known_prefixes = seen_prefixes | prior_prefixes

            if latest_prefix not in known_prefixes:
                name = users_by_id.get(user_id, {}).get("name", user_id)
                detail = {"ip": ip, "prefix": latest_prefix}
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_NEW_IP_LOGIN,
                        subject=f"{user_id}:{latest_prefix}",
                        bucket=_hour_bucket(latest_ts),
                        severity=SEVERITY_MEDIUM,
                        title=f"Login from a new network for {name}",
                        user_id=user_id,
                        ip=ip,
                        detail=detail,
                        now=now,
                    )
                )

            baseline["seen_prefixes"] = sorted(known_prefixes | {latest_prefix})
            self.store.async_schedule_save()

        return results

    # -- Rule 6: off_hours_anomaly -------------------------------------------

    async def _rule_off_hours_anomaly(self, now, users, users_by_id):
        # False positive: the account owner is travelling, jet-lagged, or
        # just can't sleep, and genuinely operates the house at 3am.
        results = []
        baselines = self.store.data["user_baselines"]

        for user in users:
            user_id = user["id"]
            baseline = baselines.setdefault(user_id, {})
            histogram = baseline.setdefault("hour_histogram", [0] * 24)

            checkpoint_raw = baseline.get("hour_histogram_updated_through")
            checkpoint = (
                dt_util.parse_datetime(checkpoint_raw) if checkpoint_raw else None
            )
            scan_since = checkpoint or (
                now - timedelta(days=OFF_HOURS_INITIAL_SCAN_LOOKBACK_DAYS)
            )

            events = await self.audit.async_query(
                since=scan_since,
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

            learning_started_raw = baseline.get("learning_started_at")
            if not learning_started_raw:
                continue
            learning_started = dt_util.parse_datetime(learning_started_raw)
            if (
                learning_started is None
                or (now - learning_started).days < OFF_HOURS_MIN_HISTORY_DAYS
            ):
                continue  # not mature yet - do nothing for this user

            total_activity = sum(histogram)
            if total_activity == 0:
                continue

            name = users_by_id.get(user_id, {}).get("name", user_id)
            for hour, count in enumerate(this_pass_counts):
                if count < OFF_HOURS_BURST_THRESHOLD:
                    continue
                if OFF_HOURS_START_HOUR <= hour < OFF_HOURS_END_HOUR:
                    continue  # inside normal daytime hours
                # Ratio includes this pass's own burst, which slightly
                # under-counts how rare the hour "historically" was - an
                # intentional, conservative simplification rather than
                # tracking a separate pre-burst snapshot.
                historical_ratio = histogram[hour] / total_activity
                if historical_ratio >= OFF_HOURS_RATIO_THRESHOLD:
                    continue

                detail = {
                    "hour": hour,
                    "count_this_pass": count,
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
            if account_age_days is None or account_age_days <= DORMANT_REVIVAL_MIN_ACCOUNT_AGE_DAYS:
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
            if gap_days > DORMANT_REVIVAL_GAP_DAYS:
                name = user.get("name", user_id)
                detail = {
                    "gap_days": gap_days,
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
        results = []
        current_ids = {u["id"] for u in users}

        for user in users:
            user_id = user["id"]
            current_groups = set(user.get("groups") or [])
            previous_groups = self._group_snapshot.get(user_id)

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

            self._group_snapshot[user_id] = current_groups

        # Garbage-collect users that no longer exist so the snapshot dict
        # doesn't grow forever across deletions.
        for stale_id in [uid for uid in self._group_snapshot if uid not in current_ids]:
            del self._group_snapshot[stale_id]

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

        window = timedelta(minutes=MASS_ENTITY_BURST_WINDOW_MINUTES)
        results = []
        for user_id, items in by_user.items():
            items.sort(key=lambda item: item[0])
            start = 0
            for end in range(len(items)):
                while items[end][0] - items[start][0] > window:
                    start += 1
                windowed = items[start : end + 1]
                if len(windowed) >= MASS_ENTITY_BURST_EVENT_THRESHOLD:
                    entities: set[str] = set()
                    for _, ent_ids in windowed:
                        entities.update(ent_ids)
                    if len(entities) >= MASS_ENTITY_BURST_ENTITY_THRESHOLD:
                        name = users_by_id.get(user_id, {}).get("name", user_id)
                        detail = {
                            "event_count": len(windowed),
                            "distinct_entities": len(entities),
                            "window_minutes": MASS_ENTITY_BURST_WINDOW_MINUTES,
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
                            )
                        )
                        break
        return results

    # -- Rule 10: token_minting_anomaly ---------------------------------------

    async def _rule_token_minting_anomaly(self, now, users, users_by_id):
        # False positive: the user is legitimately setting up several new
        # devices/integrations in one sitting (new phone, new add-on, etc).
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

        window = timedelta(hours=TOKEN_MINTING_WINDOW_HOURS)
        results = []
        for user_id, timestamps in by_user.items():
            timestamps.sort()
            start = 0
            for end in range(len(timestamps)):
                while timestamps[end] - timestamps[start] > window:
                    start += 1
                count = end - start + 1
                if count >= TOKEN_MINTING_THRESHOLD:
                    name = users_by_id.get(user_id, {}).get("name", user_id)
                    detail = {"count_in_window": count, "window_hours": TOKEN_MINTING_WINDOW_HOURS}
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
                        )
                    )
                    break
        return results

    # -- Rule 11: disabled_user_activity --------------------------------------

    async def _rule_disabled_user_activity(self, now, users, users_by_id):
        # False positive: a forgotten wall tablet or an old script still
        # holding a token, quietly retrying against a since-deactivated
        # account - not necessarily anyone actively trying to get back in.
        disabled_ids = {u["id"] for u in users if u.get("is_active") is False}
        if not disabled_ids:
            return []

        since = now - timedelta(hours=DISABLED_USER_ACTIVITY_LOOKBACK_HOURS)
        results = []
        for category in DISABLED_USER_ACTIVITY_CATEGORIES:
            events = await self.audit.async_query(
                since=since, category=category, limit=DISABLED_USER_ACTIVITY_QUERY_LIMIT
            )
            for ev in events:
                uid = ev.get("user_id")
                if uid not in disabled_ids:
                    continue
                ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
                if ts is None:
                    continue
                name = users_by_id.get(uid, {}).get("name", uid)
                detail = {"category": category, "ip": ev.get("ip")}
                results.append(
                    self._upsert_detection(
                        rule_id=RULE_DISABLED_USER_ACTIVITY,
                        subject=f"{uid}:{category}",
                        bucket=_hour_bucket(ts),
                        severity=SEVERITY_HIGH,
                        title=f"Activity attempt by disabled account {name}",
                        user_id=uid,
                        ip=ev.get("ip"),
                        detail=detail,
                        now=now,
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
        # hour from inflating that row's recurrence_count per event.
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
                )
            )
        return results
