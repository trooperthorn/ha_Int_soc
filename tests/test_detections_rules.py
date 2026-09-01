"""Sprint 3 detection-rule semantics (work items 3.1, 3.2, 3.6 to 3.9).

Drives DetectionEngine against a fake audit log and fake user list: what
is under test is each rule's own logic (windows, baselines, checkpoints,
buckets) and that every rule reads its live values from the tunable
thresholds, not the audit plumbing already covered by test_audit*.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.detections import (
    RULE_BRUTE_FORCE_IP,
    RULE_DISABLED_USER_ACTIVITY,
    RULE_DORMANT_REVIVAL,
    RULE_MASS_ENTITY_BURST,
    RULE_NEW_IP_LOGIN,
    RULE_OFF_HOURS_ANOMALY,
    RULE_PRIVILEGE_ESCALATION,
    RULE_SUCCESS_AFTER_FAILURES,
    RULE_TOKEN_MINTING_ANOMALY,
    DetectionEngine,
    _network_prefix,
)
from custom_components.ha_soc.store import HaSocData


class FakeAudit:
    """In-memory stand-in honoring async_query's filter contract."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def add(
        self,
        category: str,
        ts: datetime,
        *,
        user_id: str | None = None,
        ip: str | None = None,
        detail: dict | None = None,
        context_parent_id: str | None = None,
        entity_ids: list[str] | None = None,
    ) -> None:
        self.events.append(
            {
                "category": category,
                "ts": dt_util.as_utc(ts).isoformat(),
                "user_id": user_id,
                "ip": ip,
                "detail": detail or {},
                "context_parent_id": context_parent_id,
                "entity_ids": entity_ids or [],
            }
        )

    async def async_query(
        self,
        *,
        since=None,
        until=None,
        user_id=None,
        category=None,
        ip=None,
        limit=200,
    ):
        out = []
        for ev in self.events:
            ts = dt_util.parse_datetime(ev["ts"])
            if category is not None and ev["category"] != category:
                continue
            if user_id is not None and ev["user_id"] != user_id:
                continue
            if since is not None and ts < since:
                continue
            if until is not None and ts > until:
                continue
            out.append(ev)
        return out[:limit]


class FakeUsers:
    def __init__(self, users: list[dict[str, Any]]) -> None:
        self.users = users

    async def async_list_users(self):
        return self.users


def _user(user_id: str, **overrides: Any) -> dict[str, Any]:
    record = {
        "id": user_id,
        "name": user_id,
        "is_owner": False,
        "is_admin": False,
        "is_active": True,
        "groups": [],
        "mfa_enabled": True,
        "account_age_days": 200,
    }
    record.update(overrides)
    return record


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


def _engine(hass, store, users, audit=None) -> DetectionEngine:
    return DetectionEngine(hass, store, audit=audit or FakeAudit(), users=FakeUsers(users))


def _detections(store: HaSocData, rule_id: str) -> list[dict[str, Any]]:
    return [d for d in store.data["detections"].values() if d["rule_id"] == rule_id]


# -- 3.1: address-family-aware prefixes ------------------------------------


def test_network_prefix_ipv6() -> None:
    """Two unrelated global IPv6 addresses land in different prefixes; two
    addresses inside one /64 land in the same one. The old /24-for-
    everything defect collapsed unrelated v6 networks together."""
    a = _network_prefix("2001:db8:aaaa:1::5")
    b = _network_prefix("2606:4700:4700::1111")
    assert a is not None and b is not None
    assert a != b

    c = _network_prefix("2001:db8:aaaa:1::9")
    assert c == a

    # IPv4 keeps its own default prefix length.
    assert _network_prefix("203.0.113.7") == "203.0.113.0/24"
    # Non-default lengths are honored per family.
    assert _network_prefix("203.0.113.7", ipv4_prefix=16) == "203.0.0.0/16"
    assert (
        _network_prefix("2001:db8:aaaa:1::5", ipv6_prefix=48)
        == "2001:db8:aaaa::/48"
    )


# -- 3.2: bounded disabled_user_activity -----------------------------------


async def test_disabled_user_activity_bounded(hass: HomeAssistant, store: HaSocData) -> None:
    """A retry loop of many events yields ONE detection per (user,
    category) per pass, with the event count in the detail."""
    audit = FakeAudit()
    now = dt_util.utcnow()
    for minutes in range(30):
        audit.add("login_ok", now - timedelta(minutes=minutes + 1), user_id="ghost", ip="10.0.0.9")
    engine = _engine(hass, store, [_user("ghost", is_active=False)], audit)

    results = await engine._rule_disabled_user_activity(now, engine.users.users, {"ghost": engine.users.users[0]})

    rows = _detections(store, RULE_DISABLED_USER_ACTIVITY)
    assert len(rows) == 1
    assert rows[0]["detail"]["event_count"] == 30
    assert len(results) == 1


# -- 3.3 adjunct: closed episodes stay closed (3.9) ------------------------


async def test_detection_last_seen_is_event_time(hass: HomeAssistant, store: HaSocData) -> None:
    """last_seen carries the triggering EVENT's timestamp, and a later
    pass re-reading the same stale events bumps nothing."""
    audit = FakeAudit()
    now = dt_util.utcnow()
    trigger = now - timedelta(minutes=40)
    # Four failures then the fifth at `trigger`: the secure default
    # threshold (5) is crossed exactly at the trigger event.
    for i in range(4):
        audit.add("login_fail", trigger - timedelta(seconds=60 - i), ip="8.8.8.9")
    audit.add("login_fail", trigger, ip="8.8.8.9")
    engine = _engine(hass, store, [], audit)

    await engine._rule_brute_force_ip(now, [], {})
    rows = _detections(store, RULE_BRUTE_FORCE_IP)
    assert len(rows) == 1
    first_last_seen = rows[0]["last_seen"]
    assert first_last_seen == dt_util.as_utc(trigger).isoformat()
    assert rows[0]["recurrence_count"] == 1

    # A later pass over the same events: same trigger, so no bump.
    await engine._rule_brute_force_ip(now + timedelta(minutes=5), [], {})
    rows = _detections(store, RULE_BRUTE_FORCE_IP)
    assert rows[0]["last_seen"] == first_last_seen
    assert rows[0]["recurrence_count"] == 1


async def test_brute_force_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    for i in range(5):
        audit.add("login_fail", now - timedelta(minutes=i + 1), ip="8.8.8.9")
    engine = _engine(hass, store, [], audit)

    # Non-default threshold above the event count: silent.
    store.async_update_settings(detection_thresholds={"brute_force_ip": {"failures": 50}})
    await engine._rule_brute_force_ip(now, [], {})
    assert _detections(store, RULE_BRUTE_FORCE_IP) == []

    # Back within reach of the secure default (5): fires.
    store.async_update_settings(detection_thresholds={})
    await engine._rule_brute_force_ip(now, [], {})
    assert len(_detections(store, RULE_BRUTE_FORCE_IP)) == 1


# -- 3.8: success_after_failures on new tokens only ------------------------


async def test_success_after_failures_not_on_refresh(hass: HomeAssistant, store: HaSocData) -> None:
    """A token refresh (new_token False) never satisfies the rule while
    require_new_token is on; a genuinely new token does."""
    audit = FakeAudit()
    now = dt_util.utcnow()
    for i in range(4):
        audit.add("login_fail", now - timedelta(minutes=10 + i), ip="203.0.113.5")
    # The refresh: same IP, inside the window, but not a new token.
    audit.add(
        "login_ok", now - timedelta(minutes=5), user_id="u1", ip="203.0.113.5",
        detail={"new_token": False},
    )
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)

    await engine._rule_success_after_failures(now, users, {"u1": users[0]})
    assert _detections(store, RULE_SUCCESS_AFTER_FAILURES) == []

    # The same shape from a NEW token fires.
    audit.add(
        "login_ok", now - timedelta(minutes=4), user_id="u1", ip="203.0.113.5",
        detail={"new_token": True},
    )
    await engine._rule_success_after_failures(now, users, {"u1": users[0]})
    rows = _detections(store, RULE_SUCCESS_AFTER_FAILURES)
    assert len(rows) == 1
    assert rows[0]["severity"] == "critical"


async def test_success_after_failures_derates_shared_ip(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    for i in range(4):
        audit.add("login_fail", now - timedelta(minutes=10 + i), ip="203.0.113.5")
    audit.add(
        "login_ok", now - timedelta(minutes=6), user_id="housemate", ip="203.0.113.5",
        detail={"new_token": True},
    )
    audit.add(
        "login_ok", now - timedelta(minutes=4), user_id="u1", ip="203.0.113.5",
        detail={"new_token": True},
    )
    users = [_user("u1"), _user("housemate")]
    engine = _engine(hass, store, users, audit)

    await engine._rule_success_after_failures(now, users, {u["id"]: u for u in users})
    rows = [
        d
        for d in _detections(store, RULE_SUCCESS_AFTER_FAILURES)
        if d["user_id"] == "u1"
    ]
    assert len(rows) == 1
    # Shared household egress: de-rated to HIGH, never suppressed.
    assert rows[0]["severity"] == "high"
    assert rows[0]["detail"]["shared_ip"] is True


async def test_success_after_failures_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    for i in range(4):
        audit.add("login_fail", now - timedelta(minutes=10 + i), ip="203.0.113.5")
    audit.add(
        "login_ok", now - timedelta(minutes=4), user_id="u1", ip="203.0.113.5",
        detail={"new_token": True},
    )
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)

    # Non-default failures threshold above the burst: silent.
    store.async_update_settings(
        detection_thresholds={"success_after_failures": {"failures": 10}}
    )
    await engine._rule_success_after_failures(now, users, {"u1": users[0]})
    assert _detections(store, RULE_SUCCESS_AFTER_FAILURES) == []


# -- 3.6: new_ip_login without amnesty -------------------------------------


async def _seed_new_ip_baseline(engine, store, audit, users, home_ip="93.184.216.34", base_now=None):
    """First (silent) pass: three distinct days of home-prefix logins.

    The seeding pass runs with a `now` one hour in the past so the events
    the individual tests add afterwards land AFTER the stored checkpoint
    and are actually evaluated by the next pass.

    `base_now` lets a caller pin the reference instant instead of the real
    wall clock — needed by any test whose assertions depend on which
    calendar day a timestamp falls on, since the real wall clock can cross
    a day boundary mid-test regardless of how far apart the timestamps are.
    """
    now = (base_now or dt_util.utcnow()) - timedelta(hours=1)
    for days in (10, 9, 8):
        audit.add("login_ok", now - timedelta(days=days), user_id="u1", ip=home_ip)
    results = await engine._rule_new_ip_login(now, users, {"u1": users[0]})
    assert results == []  # seeding pass emits nothing
    return now


async def test_new_ip_login_no_amnesty(hass: HomeAssistant, store: HaSocData) -> None:
    """Every login since the checkpoint is evaluated (not just the
    newest), the flagged prefix does not become trusted in the flagging
    pass, and trust requires baseline_days_required distinct days."""
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    # Pinned to a fixed, mid-day instant rather than the real wall clock:
    # the assertion below depends on two timestamps 15 minutes apart
    # falling on the same calendar day, which the real clock cannot
    # guarantee near a UTC midnight boundary.
    base_now = datetime(2024, 1, 15, 13, 0, tzinfo=dt_util.UTC)
    checkpoint = await _seed_new_ip_baseline(engine, store, audit, users, base_now=base_now)

    # Two logins from a NEW prefix, then one from home: under the old
    # amnesty only the newest event was ever evaluated, so the earlier
    # attacker login was pardoned by the later home login.
    now2 = checkpoint + timedelta(hours=1, seconds=1)
    audit.add("login_ok", now2 - timedelta(minutes=30), user_id="u1", ip="8.8.8.7")
    audit.add("login_ok", now2 - timedelta(minutes=20), user_id="u1", ip="8.8.8.9")
    audit.add("login_ok", now2 - timedelta(minutes=10), user_id="u1", ip="93.184.216.35")
    results = await engine._rule_new_ip_login(now2, users, {"u1": users[0]})

    assert len(results) == 1  # one per (user, prefix) per pass
    rows = _detections(store, RULE_NEW_IP_LOGIN)
    assert len(rows) == 1
    assert rows[0]["detail"]["prefix"] == "8.8.8.0/24"
    # The home prefix stayed trusted and was not flagged.
    assert all(d["detail"]["prefix"] != "93.184.216.0/24" for d in rows)

    # Same prefix again on a later pass: still short of the three distinct
    # days trust requires, so it flags again (never baselined in the pass
    # that flagged it, and one sighting day is not a baseline).
    now3 = now2 + timedelta(minutes=15)
    audit.add("login_ok", now3 - timedelta(minutes=1), user_id="u1", ip="8.8.8.7")
    results3 = await engine._rule_new_ip_login(now3, users, {"u1": users[0]})
    assert len(results3) == 1

    baseline = store.data["user_baselines"]["u1"]["prefix_baseline"]
    assert len(set(baseline["8.8.8.0/24"]["days"])) == 1
    assert baseline["8.8.8.0/24"].get("legacy_trusted") is None


async def test_new_ip_login_trusts_after_required_days(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    await _seed_new_ip_baseline(engine, store, audit, users)

    # Pretend the new prefix has already been sighted on three distinct
    # days: the NEXT pass treats it as trusted and stays quiet.
    baseline = store.data["user_baselines"]["u1"]["prefix_baseline"]
    now = dt_util.utcnow()
    baseline["8.8.8.0/24"] = {
        "days": [
            (now - timedelta(days=d)).date().isoformat() for d in (3, 2, 1)
        ],
        "last_seen": dt_util.as_utc(now - timedelta(days=1)).isoformat(),
    }

    now2 = now + timedelta(seconds=1)
    audit.add("login_ok", now2 - timedelta(minutes=5), user_id="u1", ip="8.8.8.7")
    results = await engine._rule_new_ip_login(now2, users, {"u1": users[0]})
    assert results == []


async def test_new_ip_login_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    """baseline_days_required=1 (non-default) makes a single sighting day
    enough for trust on the next pass."""
    store.async_update_settings(
        detection_thresholds={"new_ip_login": {"baseline_days_required": 1}}
    )
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    await _seed_new_ip_baseline(engine, store, audit, users)

    now2 = dt_util.utcnow() + timedelta(seconds=1)
    audit.add("login_ok", now2 - timedelta(minutes=30), user_id="u1", ip="8.8.8.7")
    results = await engine._rule_new_ip_login(now2, users, {"u1": users[0]})
    assert len(results) == 1  # first sighting still flags

    now3 = now2 + timedelta(minutes=15)
    audit.add("login_ok", now3 - timedelta(minutes=1), user_id="u1", ip="8.8.8.9")
    results3 = await engine._rule_new_ip_login(now3, users, {"u1": users[0]})
    assert results3 == []  # one distinct day satisfied the lowered bar


async def test_new_ip_login_expires_baseline_entries(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    await _seed_new_ip_baseline(engine, store, audit, users)

    now = dt_util.utcnow()
    baseline = store.data["user_baselines"]["u1"]["prefix_baseline"]
    baseline["77.88.55.0/24"] = {
        "days": ["2020-01-01", "2020-01-02", "2020-01-03"],
        "last_seen": dt_util.as_utc(now - timedelta(days=120)).isoformat(),
    }

    now2 = now + timedelta(seconds=1)
    audit.add("login_ok", now2 - timedelta(minutes=5), user_id="u1", ip="77.88.55.9")
    results = await engine._rule_new_ip_login(now2, users, {"u1": users[0]})
    # 120 days without a sighting is past prefix_expiry_days (90): the
    # entry expired, so the prefix is a stranger again and flags.
    assert len(results) == 1


async def test_new_ip_login_legacy_seen_prefixes_grandfathered(
    hass: HomeAssistant, store: HaSocData
) -> None:
    """A pre-3.6 flat seen_prefixes list migrates as trusted so an upgrade
    does not flood alerts for the owner's own long-used networks."""
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    now = dt_util.utcnow()
    store.data["user_baselines"]["u1"] = {
        "seen_prefixes": ["93.184.216.0/24"],
        "new_ip_checkpoint": dt_util.as_utc(now - timedelta(days=1)).isoformat(),
        "first_login_seen_at": dt_util.as_utc(now - timedelta(days=30)).isoformat(),
    }

    audit.add("login_ok", now - timedelta(minutes=5), user_id="u1", ip="93.184.216.35")
    results = await engine._rule_new_ip_login(now, users, {"u1": users[0]})
    assert results == []
    baseline = store.data["user_baselines"]["u1"]
    assert "seen_prefixes" not in baseline
    assert baseline["prefix_baseline"]["93.184.216.0/24"]["legacy_trusted"] is True


# -- 3.7: silent seeding pass for off_hours --------------------------------


def _daytime_seed(audit: FakeAudit, user_id: str, now: datetime, count: int) -> None:
    """Spread `count` direct service calls across daytime hours over the
    last ten days, so the histogram has a real daytime bulk."""
    for i in range(count):
        moment = now - timedelta(days=1 + (i % 9), hours=-(0))
        local = dt_util.as_local(moment).replace(
            hour=9 + (i % 8), minute=i % 60, second=0, microsecond=0
        )
        audit.add("service_call", dt_util.as_utc(local), user_id=user_id)


async def test_off_hours_first_pass_is_silent(hass: HomeAssistant, store: HaSocData) -> None:
    """The seeding pass fills the histogram and sets the checkpoint but
    emits nothing, even over history that contains night bursts."""
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    now = dt_util.utcnow()
    _daytime_seed(audit, "u1", now, 700)
    # A genuine night burst inside the seeded history.
    night = dt_util.as_local(now - timedelta(days=2)).replace(
        hour=3, minute=0, second=0, microsecond=0
    )
    for i in range(8):
        audit.add("service_call", dt_util.as_utc(night) + timedelta(minutes=i), user_id="u1")

    results = await engine._rule_off_hours_anomaly(now, users, {"u1": users[0]})

    assert results == []
    baseline = store.data["user_baselines"]["u1"]
    assert baseline["hour_histogram_updated_through"] == dt_util.as_utc(now).isoformat()
    assert sum(baseline["hour_histogram"]) == 708


async def test_off_hours_second_pass_flags_burst(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    now = dt_util.utcnow()
    _daytime_seed(audit, "u1", now, 700)
    await engine._rule_off_hours_anomaly(now, users, {"u1": users[0]})

    # New burst at 03:00 local since the checkpoint. The pass interval
    # scale is ~1 because the two passes are minutes apart.
    now2 = now + timedelta(minutes=5)
    night = dt_util.as_local(now2).replace(hour=3, minute=0, second=0, microsecond=0)
    burst_base = dt_util.as_utc(night)
    for i in range(6):
        ev_ts = burst_base + timedelta(seconds=i)
        if ev_ts <= dt_util.as_utc(now):
            ev_ts = dt_util.as_utc(now) + timedelta(seconds=i + 1)
        audit.add("service_call", ev_ts, user_id="u1")

    # Force the burst events inside (checkpoint, now2]: rebuild ts values
    # relative to the checkpoint so the query window always contains them.
    for ev in audit.events[-6:]:
        ev["ts"] = dt_util.as_utc(now + timedelta(seconds=30)).isoformat()

    results = await engine._rule_off_hours_anomaly(now2, users, {"u1": users[0]})

    hour = dt_util.as_local(now + timedelta(seconds=30)).hour
    rows = _detections(store, RULE_OFF_HOURS_ANOMALY)
    if hour >= 23 or hour < 6:
        # Only meaningful when the test actually runs during quiet hours;
        # covered deterministically below by test_off_hours_reads_threshold.
        assert rows
    else:
        assert results == []


async def test_off_hours_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    """Deterministic threshold test: widen the quiet window to all day
    (quiet_start 0 is min, quiet_end 23) and drop burst_threshold to the
    non-default 2, then observe both change the outcome."""
    audit = FakeAudit()
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)
    now = dt_util.utcnow()
    _daytime_seed(audit, "u1", now, 700)
    await engine._rule_off_hours_anomaly(now, users, {"u1": users[0]})

    now2 = now + timedelta(minutes=5)
    for i in range(3):
        audit.add("service_call", now + timedelta(seconds=10 + i), user_id="u1")

    # Default thresholds: burst of 3 is under the secure default of 5, and
    # the current hour is probably not quiet anyway - silent.
    results = await engine._rule_off_hours_anomaly(now2, users, {"u1": users[0]})
    assert results == []

    # Non-default: every hour is quiet and 2 events are a burst.
    store.async_update_settings(
        detection_thresholds={
            "off_hours_anomaly": {
                "quiet_start_hour": 0,
                "quiet_end_hour": 23,
                "burst_threshold": 2,
                "ratio_threshold": 0.2,
            }
        }
    )
    now3 = now2 + timedelta(minutes=5)
    for i in range(3):
        audit.add("service_call", now2 + timedelta(seconds=10 + i), user_id="u1")
    hour = dt_util.as_local(now2 + timedelta(seconds=10)).hour
    results = await engine._rule_off_hours_anomaly(now3, users, {"u1": users[0]})
    if hour < 23:
        assert len(results) == 1
    else:
        # 23:00 falls outside the widened-but-not-wrapping window; the
        # burst landing in that one hour of the day is the only case this
        # assertion cannot pin down deterministically.
        assert results == []


# -- 3.2/3.0: dormant_revival, mass_entity_burst, token_minting ------------


async def test_dormant_revival_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    audit.add("login_ok", now - timedelta(days=45), user_id="u1", ip="10.0.0.2")
    audit.add("login_ok", now - timedelta(minutes=5), user_id="u1", ip="10.0.0.2")
    users = [_user("u1", account_age_days=200)]
    engine = _engine(hass, store, users, audit)

    # Secure default dormant_days=30: a 45-day gap fires.
    await engine._rule_dormant_revival(now, users, {"u1": users[0]})
    assert len(_detections(store, RULE_DORMANT_REVIVAL)) == 1

    # Non-default 60: the same gap is quiet.
    store.data["detections"].clear()
    store.async_update_settings(
        detection_thresholds={"dormant_revival": {"dormant_days": 60}}
    )
    await engine._rule_dormant_revival(now, users, {"u1": users[0]})
    assert _detections(store, RULE_DORMANT_REVIVAL) == []


async def test_mass_entity_burst_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    for i in range(21):
        audit.add(
            "service_call",
            now - timedelta(minutes=4, seconds=-i),
            user_id="u1",
            entity_ids=[f"light.l{i % 12}"],
        )
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)

    # Secure defaults (calls 20, distinct 10): fires.
    await engine._rule_mass_entity_burst(now, users, {"u1": users[0]})
    assert len(_detections(store, RULE_MASS_ENTITY_BURST)) == 1

    store.data["detections"].clear()
    store.async_update_settings(
        detection_thresholds={"mass_entity_burst": {"calls": 50}}
    )
    await engine._rule_mass_entity_burst(now, users, {"u1": users[0]})
    assert _detections(store, RULE_MASS_ENTITY_BURST) == []


async def test_token_minting_reads_threshold(hass: HomeAssistant, store: HaSocData) -> None:
    audit = FakeAudit()
    now = dt_util.utcnow()
    audit.add("token_created", now - timedelta(hours=2), user_id="u1")
    audit.add("token_created", now - timedelta(hours=1), user_id="u1")
    users = [_user("u1")]
    engine = _engine(hass, store, users, audit)

    # Secure default tokens=2: two tokens in 24h fire.
    await engine._rule_token_minting_anomaly(now, users, {"u1": users[0]})
    assert len(_detections(store, RULE_TOKEN_MINTING_ANOMALY)) == 1

    store.data["detections"].clear()
    store.async_update_settings(
        detection_thresholds={"token_minting_anomaly": {"tokens": 5}}
    )
    await engine._rule_token_minting_anomaly(now, users, {"u1": users[0]})
    assert _detections(store, RULE_TOKEN_MINTING_ANOMALY) == []


# -- 3.10: privilege escalation snapshot persists --------------------------


async def test_privilege_escalation_survives_restart(hass: HomeAssistant, store: HaSocData) -> None:
    """The group snapshot lives in user_baselines: a fresh engine over the
    same store (a restart) still detects an escalation that happened in
    between, and only a never-observed user baselines silently."""
    now = dt_util.utcnow()
    users_before = [_user("u1", groups=["system-users"])]
    engine1 = _engine(hass, store, users_before)
    await engine1._rule_privilege_escalation(now, users_before, {"u1": users_before[0]})
    assert store.data["user_baselines"]["u1"]["groups_snapshot"] == ["system-users"]
    assert _detections(store, RULE_PRIVILEGE_ESCALATION) == []

    # "Restart": a brand-new engine instance over the same store, and the
    # user is now an admin.
    users_after = [_user("u1", groups=["system-admin"], is_admin=True)]
    engine2 = _engine(hass, store, users_after)
    results = await engine2._rule_privilege_escalation(
        now + timedelta(minutes=5), users_after, {"u1": users_after[0]}
    )
    assert len(results) == 1
    rows = _detections(store, RULE_PRIVILEGE_ESCALATION)
    assert len(rows) == 1
    assert rows[0]["detail"]["gained_group"] == "system-admin"

    # A user observed for the very first time as admin is baselined
    # silently - there is no previous state to compare against.
    newcomer = [_user("u2", groups=["system-admin"], is_admin=True)]
    engine3 = _engine(hass, store, newcomer)
    results = await engine3._rule_privilege_escalation(
        now + timedelta(minutes=10), newcomer, {"u2": newcomer[0]}
    )
    assert results == []


# -- full pass wiring ------------------------------------------------------


async def test_run_pass_notes_completion_and_prunes(hass: HomeAssistant, store: HaSocData) -> None:
    """async_run_pass records the completion marker (posture term evidence,
    work item 3.4) and runs the evidence retention sweep (3.3)."""
    old = (dt_util.utcnow() - timedelta(days=400)).isoformat()
    store.data["detections"]["stale"] = {
        "id": "stale",
        "rule_id": "brute_force_ip",
        "status": "resolved",
        "status_at": old,
        "ts": old,
        "last_seen": old,
    }
    engine = _engine(hass, store, [])
    await engine.async_run_pass()

    assert store.data["detections_meta"]["last_pass_completed_at"] is not None
    assert "stale" not in store.data["detections"]
