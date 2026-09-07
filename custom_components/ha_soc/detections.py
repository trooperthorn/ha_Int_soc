"""Rule-based detection engine over the HA SOC audit log.

Every rule is built only from signals audit.py actually captures; rules
whose signal Home Assistant does not expose are left unimplemented rather
than approximated (coverage gaps and rule semantics: docs/security.md).
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
    # Not imported at runtime so this module stays importable without audit.py/users.py.
    from .audit import AuditLog
    from .users import UsersManager

_LOGGER = logging.getLogger(__name__)

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
RULE_EXTERNAL_AUDIT_CHAIN_BREAK = "external_audit_chain_break"

# websocket_api.py derives its validation schema and the Settings ranges from this table.
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
    """Effective thresholds for `rule`: stored overrides over secure defaults."""
    effective = secure_default_thresholds(rule)
    stored = (store.settings.get("detection_thresholds") or {}).get(rule) or {}
    for key, value in stored.items():
        if key in effective:
            effective[key] = value
    return effective


# Query bounds are deliberately not operator-tunable: shrinking them would blind a rule.
BRUTE_FORCE_IP_LOOKBACK_DAYS = 7
BRUTE_FORCE_IP_QUERY_LIMIT = 10000

SUCCESS_AFTER_FAILURES_LOOKBACK_HOURS = 24
SUCCESS_AFTER_FAILURES_QUERY_LIMIT = 5000

NEW_IP_LOGIN_BASELINE_LOOKBACK_DAYS = 30
NEW_IP_LOGIN_QUERY_LIMIT = 10000
# Caps the per-prefix sighting-day list so a long-lived entry cannot grow without bound.
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

# Oldest trigger timestamps fall off the front; overflow only undercounts recurrences.
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
    """The baseline network prefix for an address, per address family."""
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
        # Unparseable input counts as private so garbage is never flagged.
        return True


def _analysis_interval() -> timedelta:
    """The periodic pass interval, read lazily from __init__ to avoid the import cycle."""
    try:
        from . import ANALYSIS_INTERVAL

        return ANALYSIS_INTERVAL
    except ImportError:  # pragma: no cover - package always importable in HA
        return timedelta(minutes=5)


def _in_quiet_window(hour: int, quiet_start: int, quiet_end: int) -> bool:
    """True when `hour` falls inside the [quiet_start, quiet_end) window, which
    may wrap midnight; equal start and end means no hour is quiet."""
    if quiet_start == quiet_end:
        return False
    if quiet_start < quiet_end:
        return quiet_start <= hour < quiet_end
    return hour >= quiet_start or hour < quiet_end


class DetectionEngine:
    """Runs all implemented detection rules against the audit log and store."""

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
            self._rule_external_audit_chain_break,
        ):
            try:
                touched.extend(await rule(now, users, users_by_id))
            except Exception:  # noqa: BLE001 - one bad rule must not sink the pass
                _LOGGER.exception("HA SOC detection rule %s failed", rule.__name__)

        # Retention runs outside the rule loop so neither can block the other.
        try:
            self.store.async_prune_evidence(now)
        except Exception:  # noqa: BLE001 - retention must never sink the pass
            _LOGGER.exception("HA SOC evidence retention sweep failed")

        # Recorded even when rules failed: the posture term reflects that the engine ran.
        self.store.async_note_detection_pass_completed(
            dt_util.as_utc(now).isoformat()
        )

        return touched

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

        `event_ts` is the triggering event's timestamp; when omitted the
        pass `now` stands in for it.
        """
        detection_id = _make_detection_id(rule_id, subject, bucket)
        now_iso = dt_util.as_utc(now).isoformat()
        event_iso = dt_util.as_utc(event_ts or now).isoformat()
        existing = self.store.data["detections"].get(detection_id)

        if existing is not None:
            triggers = existing.setdefault(
                # Rows from older builds have no trigger list; last_seen stands in.
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
            # status is never downgraded here: ack/resolved must survive re-detection.
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

    async def _rule_brute_force_ip(self, now, users, users_by_id):
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

    async def _rule_success_after_failures(self, now, users, users_by_id):
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

        # For derate_shared_ip: a multi-user IP is a shared egress, so HIGH rather than CRITICAL.
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
                # Untagged (pre-tag) records are skipped too: a new token cannot be proven for them.
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

    async def _rule_new_ip_login(self, now, users, users_by_id):
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

            for prefix in list(prefix_baseline):
                last_seen = dt_util.parse_datetime(
                    prefix_baseline[prefix].get("last_seen") or ""
                )
                if last_seen is None or now - last_seen > expiry:
                    del prefix_baseline[prefix]

            # Trust is evaluated against the pre-pass snapshot; sightings below count from the next pass.
            required_days = th["baseline_days_required"]
            trusted = {
                prefix
                for prefix, entry in prefix_baseline.items()
                if entry.get("legacy_trusted")
                or len(set(entry.get("days") or [])) >= required_days
            }

            # Maturity gate: no flags until learning_days of observed login history.
            first_seen_raw = baseline.get("first_login_seen_at")
            first_seen = (
                dt_util.parse_datetime(first_seen_raw) if first_seen_raw else None
            )

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
                    # One detection per (user, prefix) per pass, anchored to the newest login.
                    prev = flagged.get(prefix)
                    if prev is None or ts > prev[0]:
                        flagged[prefix] = (ts, ip)

                # Recorded after trust evaluation so a flagged prefix never earns trust in the same pass.
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

            # `now` is both the query `until` and the checkpoint, so no login is evaluated twice.
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
        """This user's prefix baseline, migrating the legacy flat list once."""
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

    async def _rule_off_hours_anomaly(self, now, users, users_by_id):
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

            # `until=now` matches the checkpoint written below, so no event is counted twice.
            events = await self.audit.async_query(
                since=scan_since,
                until=now,
                category="service_call",
                user_id=user_id,
                limit=OFF_HOURS_QUERY_LIMIT,
            )
            # context_parent_id None means a direct user action; automations must not shape the baseline.
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
                # Seeding pass fills the histogram silently; its 30-day scan is no burst signal.
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

            # Burst threshold scales with the scanned span so a catch-up pass cannot fake a burst.
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
                # Ratio includes this pass's own burst, a deliberate conservative simplification.
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

    async def _rule_dormant_revival(self, now, users, users_by_id):
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

    async def _rule_privilege_escalation(self, now, users, users_by_id):
        # Group snapshot is persisted so an escalation during downtime is caught after restart.
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

        # Deleted users' snapshots are purged by store.async_purge_user.
        return results

    async def _find_privilege_escalation_actor(
        self, user_id: str, now: datetime
    ) -> str | None:
        """Best-effort: who performed the user_updated that granted admin.

        Returns None rather than guessing when the target user cannot be
        resolved from the event detail.
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

    async def _rule_mass_entity_burst(self, now, users, users_by_id):
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

    async def _rule_token_minting_anomaly(self, now, users, users_by_id):
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

    async def _rule_disabled_user_activity(self, now, users, users_by_id):
        # One detection per (user, category) per pass, bucketed by the pass, so a retry loop cannot mint rows.
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

    async def _rule_probe_auth_rejected(self, now, users, users_by_id):
        since = now - timedelta(hours=PROBE_AUTH_REJECTED_LOOKBACK_HOURS)
        events = await self.audit.async_query(
            since=since,
            category="probe_auth_rejected",
            limit=PROBE_AUTH_REJECTED_QUERY_LIMIT,
        )

        # At most one detection per (caller, hour).
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

    async def _rule_external_audit_chain_break(self, now, users, users_by_id):
        """A tool's hash-chained audit log arrived broken or rewritten: HIGH, one per (source, hour)."""
        since = now - timedelta(hours=PROBE_AUTH_REJECTED_LOOKBACK_HOURS)
        events = await self.audit.async_query(
            since=since,
            category="external_audit_chain_break",
            limit=PROBE_AUTH_REJECTED_QUERY_LIMIT,
        )
        emitted: set[tuple[str, str]] = set()
        results = []
        for ev in events:
            detail_in = ev.get("detail") or {}
            source = str(detail_in.get("source") or "unknown")
            ts = dt_util.parse_datetime(ev["ts"]) if ev.get("ts") else None
            if ts is None:
                continue
            bucket = _hour_bucket(ts)
            if (source, bucket) in emitted:
                continue
            emitted.add((source, bucket))
            results.append(
                self._upsert_detection(
                    rule_id=RULE_EXTERNAL_AUDIT_CHAIN_BREAK,
                    subject=source,
                    bucket=bucket,
                    severity=SEVERITY_HIGH,
                    title=f"External audit chain from {source} broken",
                    user_id=ev.get("user_id"),
                    ip=None,
                    detail={
                        "source": source,
                        "reason": detail_in.get("reason"),
                        "accepted_before_break": detail_in.get("accepted_before_break"),
                        "head_seq": detail_in.get("head_seq"),
                    },
                    now=now,
                    event_ts=ts,
                )
            )
        return results
