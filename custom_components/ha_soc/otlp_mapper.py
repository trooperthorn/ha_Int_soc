"""Map the system detail HA SOC already collects to OTLP JSON for Observe.

Pure functions: no Home Assistant import, no I/O, no clock. The caller passes a snapshot
of data it already holds and the time to stamp it with, and gets back two JSON-ready
dicts, an ExportMetricsServiceRequest and an ExportLogsServiceRequest. The names, units
and attributes follow section 3.4 of Observe's DATA-API-DESIGN.md; the limits follow
Observe's decoder (observe/otlp/normalize.py). See docs/design.md, "Observe push".
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

SCOPE_PREFIX = "ha_soc.collector."
SERVICE_NAME = "home-assistant"
PRODUCER = "ha_Int_soc"
# Observe's name for the platform of a host that runs Home Assistant (observe/otlp/normalize.py).
OS_TYPE = "homeassistant"

# Observe's per-request and per-field limits (observe/ingest/schema.py, otlp/normalize.py).
MAX_POINTS = 5000
MAX_RECORDS = 500
MAX_ATTR_VALUE = 1024
MAX_POINT_ATTRS = 32
MAX_ROWS = 100

SEVERITY_INFO = (9, "INFO")
SEVERITY_WARN = (13, "WARN")
SEVERITY_ERROR = (17, "ERROR")

WATCHDOG_RULE = "container_resource_breach"
CRASH_SEVERITY = {
    "kernel_fault": SEVERITY_ERROR,
    "silent_stop": SEVERITY_ERROR,
    "core_restart": SEVERITY_WARN,
    "clean_reboot": SEVERITY_INFO,
}
CRASH_SUMMARY = {
    "kernel_fault": "Host stopped after a kernel fault",
    "silent_stop": "Host stopped without a clean shutdown",
    "core_restart": "Home Assistant Core restarted inside one host boot",
    "clean_reboot": "Host rebooted cleanly",
}


@dataclass(frozen=True)
class Identity:
    """The resource the payloads describe."""

    host_name: str
    instance_id: str = ""
    version: str = ""
    installation_type: str = ""


def _val(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value} if math.isfinite(value) else None
    if isinstance(value, str):
        return {"stringValue": value[:MAX_ATTR_VALUE]}
    return None


def _attrs(items: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for key, value in items.items():
        converted = _val(value)
        if converted is not None:
            out.append({"key": key, "value": converted})
    return out[:MAX_POINT_ATTRS]


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def _ns(ts: float) -> str:
    return str(int(round(ts * 1_000_000_000)))


def _resource(identity: Identity, now: float) -> dict[str, Any]:
    """The resource of one request. `observe.agent.sent_at` is `now` in whole unix seconds."""
    attrs: dict[str, Any] = {
        "host.name": identity.host_name,
        "service.name": SERVICE_NAME,
        "observe.producer": PRODUCER,
        "os.type": OS_TYPE,
        "observe.agent.sent_at": int(now),
    }
    for key, value in (
        ("service.instance.id", identity.instance_id),
        ("service.version", identity.version),
        ("observe.ha.installation_type", identity.installation_type),
    ):
        if value:
            attrs[key] = value
    return {"attributes": _attrs(attrs)}


class _Metrics:
    """Collects gauge points grouped by scope and metric, in insertion order."""

    def __init__(self, now: float, dropped: dict[str, int] | None = None) -> None:
        self._time = _ns(now)
        self.dropped = dropped if dropped is not None else {}
        self._scopes: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = {}
        self.count = 0

    def gauge(
        self, source: str, name: str, unit: str, value: Any, *, force: bool = False,
        **attrs: Any
    ) -> None:
        number = _number(value)
        if number is None:
            return
        if self.count >= MAX_POINTS and not force:
            self.drop("points")
            return
        point = {
            "attributes": _attrs({k.replace("__", "."): v for k, v in attrs.items()}),
            "timeUnixNano": self._time,
            "asDouble": number,
        }
        self._scopes.setdefault(source, {}).setdefault((name, unit), []).append(point)
        self.count += 1

    def drop(self, what: str, n: int = 1) -> None:
        if n > 0:
            self.dropped[what] = self.dropped.get(what, 0) + n

    def scope_metrics(self) -> list[dict[str, Any]]:
        return [
            {
                "scope": {"name": SCOPE_PREFIX + source},
                "metrics": [
                    {"name": name, "unit": unit, "gauge": {"dataPoints": points}}
                    for (name, unit), points in metrics.items()
                ],
            }
            for source, metrics in self._scopes.items()
        ]


def _rows(items: Any) -> list[dict[str, Any]]:
    return [i for i in items if isinstance(i, dict)] if isinstance(items, Iterable) else []


def _strings(items: Any) -> list[str]:
    """The string members of a list; anything else (null, a scalar) is an empty list."""
    return [i for i in items if isinstance(i, str)] if isinstance(items, (list, tuple)) else []


def _capped(m: _Metrics, what: str, items: list[Any]) -> list[Any]:
    m.drop(what, len(items) - MAX_ROWS)
    return items[:MAX_ROWS]


def _ratio(percent: Any) -> float | None:
    """A Supervisor percentage as a 0 to 1 ratio, clamped into that range.

    The Supervisor documents `cpu_percent` only as the percentage of the CPU that is used
    (developers docs, api/supervisor/models.md) and aiohasupervisor types it as a bare float.
    Docker's own formula can give more than 100 for a container on several cores, so the
    value is clamped: the unit `1` promises a ratio, and Observe grades it at 0.85 and 0.95.
    See docs/decisions.md, "Observe payload values".
    """
    number = _number(percent)
    if number is None:
        return None
    return round(min(1.0, max(0.0, number / 100)), 6)


def _containers(m: _Metrics, overview: Any) -> None:
    if not isinstance(overview, dict) or not overview.get("available"):
        return
    for row in _capped(m, "containers", _rows(overview.get("containers"))):
        slug = row.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        m.gauge("containers", "container.cpu.utilization", "1",
                _ratio(row.get("cpu_percent")), container__name=slug)
        m.gauge("containers", "container.memory.utilization", "1",
                _ratio(row.get("memory_percent")), container__name=slug)
        m.gauge("containers", "container.memory.usage", "By",
                row.get("memory_usage"), container__name=slug)
        # Only a container the Supervisor reports as started is running. A stopped, errored
        # or unknown state is 0; a row with no state at all says nothing, so it has no point.
        state = row.get("state")
        if isinstance(state, str) and state:
            m.gauge("containers", "observe.ha.container.running", "1",
                    int(state == "started"), container__name=slug)


def _watchdog(m: _Metrics, detections: Any) -> None:
    if detections is None:
        return
    open_by_rule: dict[str, int] = {WATCHDOG_RULE: 0}
    for det in _rows(detections):
        rule = det.get("rule_id")
        if isinstance(rule, str) and rule.startswith("container_") and det.get("status") == "open":
            open_by_rule[rule] = open_by_rule.get(rule, 0) + 1
    for rule, count in open_by_rule.items():
        m.gauge("watchdog", "observe.ha.watchdog.breaches", "{breach}", count,
                observe__ha__watchdog__rule=rule)


# The order health.py gives a record when it has several reasons; an unknown name sorts last.
CATEGORY_PRIORITY = ("credential", "failing", "communication", "collection", "errors",
                     "debug_logging", "disabled")


def _priority(category: str) -> int:
    if category in CATEGORY_PRIORITY:
        return CATEGORY_PRIORITY.index(category)
    return len(CATEGORY_PRIORITY)


def _integrations(
    m: _Metrics, overview: Any, series: set[tuple[str, str]] | None = None
) -> None:
    """Counts per category and one error series per domain.

    `series` is the (domain, category) pairs the previous payload sent, updated in place. A
    pair that is gone now (the entry was removed or unloaded, or the domain moved to another
    category) is sent once as 0, because Observe would otherwise keep showing its last value
    for ever. A domain that is still present but cut by the row cap is not zeroed.
    """
    if not isinstance(overview, dict):
        return
    counts = overview.get("category_counts")
    if isinstance(counts, dict):
        for category in sorted(counts):
            m.gauge("integrations", "observe.ha.integration.count", "{integration}",
                    counts[category], observe__ha__integration__category=str(category))
    # The health record of every config entry carries the error count of its whole domain
    # (the logger is per domain), so three ESPHome entries repeat one number. Take the
    # domain's count once, not the sum, and send one series per domain. A domain with entries
    # in several categories is labelled with the first of them in CATEGORY_PRIORITY, so
    # summing the series of this metric never counts an error twice.
    errors: dict[str, float] = {}
    category_of: dict[str, str] = {}
    for row in _rows(overview.get("integrations")):
        domain = row.get("domain")
        if not (isinstance(domain, str) and domain):
            continue
        errors[domain] = max(errors.get(domain, 0.0), _number(row.get("error_count_24h")) or 0.0)
        category = str(row.get("issue_category", ""))
        if domain not in category_of or _priority(category) < _priority(category_of[domain]):
            category_of[domain] = category
    # The domains with the most errors are the ones to keep when the cap cuts the list.
    ranked = sorted(errors, key=lambda d: (-errors[d], d))
    sent: set[tuple[str, str]] = set()
    for domain in _capped(m, "integrations", ranked):
        m.gauge("integrations", "observe.ha.integration.errors", "{error}",
                errors[domain], observe__ha__integration=domain,
                observe__ha__integration__category=category_of[domain])
        sent.add((domain, category_of[domain]))
    if series is None:
        return
    keep = set(sent)
    for domain, category in sorted(series - sent):
        if domain in errors and category_of[domain] == category:
            keep.add((domain, category))  # Cut by the cap, not recovered.
            continue
        m.gauge("integrations", "observe.ha.integration.errors", "{error}", 0, force=True,
                observe__ha__integration=domain, observe__ha__integration__category=category)
    series.clear()
    series.update(keep)


def _repairs(m: _Metrics, issues: Any) -> None:
    if issues is None:
        return
    by_domain: dict[str, int] = {}
    for issue in _rows(issues):
        domain = issue.get("domain")
        key = domain if isinstance(domain, str) and domain else "unknown"
        by_domain[key] = by_domain.get(key, 0) + 1
    m.gauge("repairs", "observe.ha.repair.issues", "{issue}", sum(by_domain.values()),
            observe__ha__repair__state="open")
    # The per-domain breakdown has its own metric name: a series of `observe.ha.repair.issues`
    # for each domain next to the total would make any sum of that name count every issue twice.
    for domain in _capped(m, "repair_domains", sorted(by_domain)):
        m.gauge("repairs", "observe.ha.repair.domain_issues", "{issue}", by_domain[domain],
                observe__ha__repair__state="open", observe__ha__repair__domain=domain)


def _backup(m: _Metrics, finding: Any, checked: bool, unreadable: Any) -> None:
    """One gauge: 1 while the unprotected-backup finding is open, 0 when the check ran clean.

    When the backup store could not be read the answer is unknown, so no gauge is sent at
    all; `_source_status` reports the source as unavailable with the reason instead.
    """
    if isinstance(unreadable, str) and unreadable:
        return
    if isinstance(finding, dict):
        detail = finding.get("detail") if isinstance(finding.get("detail"), dict) else {}
        m.gauge("backup", "observe.ha.backup.unprotected", "1", 1,
                observe__ha__backup__password_set=bool(detail.get("password_set")))
    elif checked:
        m.gauge("backup", "observe.ha.backup.unprotected", "1", 0)


def _supervisor(m: _Metrics, resolution: Any) -> None:
    if not isinstance(resolution, dict):
        return
    data = resolution.get("data") if isinstance(resolution.get("data"), dict) else resolution
    unhealthy = _strings(data.get("unhealthy"))
    unsupported = _strings(data.get("unsupported"))
    m.gauge("supervisor", "observe.ha.supervisor.healthy", "1", int(not unhealthy))
    m.gauge("supervisor", "observe.ha.supervisor.supported", "1", int(not unsupported))
    m.gauge("supervisor", "observe.ha.supervisor.unhealthy_reasons", "{reason}",
            len(set(unhealthy)))
    # One flag per reason under its own name, for the same reason as the repair breakdown.
    for reason in _capped(m, "unhealthy_reasons", sorted(set(unhealthy))):
        m.gauge("supervisor", "observe.ha.supervisor.unhealthy_reason", "1", 1,
                observe__ha__supervisor__reason=reason)


def _source_status(m: _Metrics, snapshot: dict[str, Any]) -> None:
    """`observe.source.available` per source: 1 when its data was collected, else 0 with why.

    A source with nothing to report (no breach, no repair issue) is available and sends its
    own zeroes, so Observe can tell a quiet source from one that could not be read. Sent only
    for a snapshot that holds something, so an empty snapshot stays an empty request.
    """
    if not snapshot:
        return
    containers = snapshot.get("containers")
    if isinstance(containers, dict) and containers.get("available"):
        containers_reason = ""
    elif isinstance(containers, dict) and containers.get("reason"):
        containers_reason = str(containers["reason"])
    else:
        containers_reason = "container statistics were not available"
    unreadable = snapshot.get("backup_unreadable")
    if isinstance(unreadable, str) and unreadable:
        backup = unreadable
    elif snapshot.get("backup_finding") is None and not snapshot.get("backup_checked"):
        backup = "the backup check has not run yet"
    else:
        backup = ""
    statuses = (
        ("containers", containers_reason),
        ("watchdog", "" if snapshot.get("detections") is not None else
         "the detections were not collected"),
        ("integrations", "" if isinstance(snapshot.get("integration_overview"), dict) else
         "the integration overview could not be collected"),
        ("repairs", "" if snapshot.get("repairs") is not None else
         "the repair issues could not be read"),
        ("backup", backup),
        ("supervisor", "" if isinstance(snapshot.get("resolution"), dict) else
         "the Supervisor resolution info was not available"),
        ("crash_forensics", "" if snapshot.get("crash_bundles") is not None else
         "the crash bundle list was not available"),
    )
    for source, reason in statuses:
        extra = {"observe__source__reason": reason} if reason else {}
        m.gauge(source, "observe.source.available", "1", int(not reason), force=True,
                observe__source=source, **extra)


ROW_KINDS = ("containers", "integrations", "repair_domains", "unhealthy_reasons", "points")


def _dropped(m: _Metrics) -> None:
    """How many rows each cap left out of this payload, 0 when none, so a cut is never silent.

    Sent every time (a gauge Observe last saw at 5 would otherwise stay at 5 after the cut
    ended) and exempt from the point cap, which would be the one cut that could hide itself.
    """
    if not m.count:
        return  # An empty snapshot stays an empty request.
    for kind in ROW_KINDS:
        m.gauge("push", "observe.ha.push.rows_dropped", "{row}", m.dropped.get(kind, 0),
                force=True, observe__ha__push__kind=kind)


def build_metrics(
    identity: Identity, snapshot: dict[str, Any], now: float,
    dropped: dict[str, int] | None = None,
    integration_series: set[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """The ExportMetricsServiceRequest for one snapshot taken at `now` (unix seconds).

    `integration_series` is the caller's memory of the integration error series already sent;
    see `_integrations`. Leave it out and no zero is ever sent for a series that went away.

    Rows and points past the caps are left out; if `dropped` is given, it receives the
    count left out per kind ("containers", "integrations", "repair_domains",
    "unhealthy_reasons", "points") so the sender can log it. The same counts are sent as the
    gauge `observe.ha.push.rows_dropped`, one point per kind.
    """
    m = _Metrics(now, dropped)
    _containers(m, snapshot.get("containers"))
    _watchdog(m, snapshot.get("detections"))
    _integrations(m, snapshot.get("integration_overview"), integration_series)
    _repairs(m, snapshot.get("repairs"))
    _backup(m, snapshot.get("backup_finding"), bool(snapshot.get("backup_checked")),
            snapshot.get("backup_unreadable"))
    _supervisor(m, snapshot.get("resolution"))
    _dropped(m)
    _source_status(m, snapshot)
    return {
        "resourceMetrics": [
            {"resource": _resource(identity, now), "scopeMetrics": m.scope_metrics()}
        ]
    }


def _record(
    ts: float, severity: tuple[int, str], body: str, event: str, dedup: str, **attrs: Any
) -> dict[str, Any]:
    return {
        "timeUnixNano": _ns(ts),
        "severityNumber": severity[0],
        "severityText": severity[1],
        "body": {"stringValue": body[:MAX_ATTR_VALUE]},
        "attributes": _attrs(
            {"event.name": event, "observe.dedup_key": dedup,
             **{k.replace("__", "."): v for k, v in attrs.items()}}
        ),
    }


def _iso_to_ts(value: Any, default: float) -> float:
    if not isinstance(value, str):
        return default
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return default


def _watchdog_records(detections: Any, now: float) -> list[dict[str, Any]]:
    out = []
    for det in _rows(detections):
        if det.get("rule_id") != WATCHDOG_RULE:
            continue
        detail = det.get("detail") if isinstance(det.get("detail"), dict) else {}
        slug = str(detail.get("slug") or det.get("id") or "unknown")
        # One record per breach episode: the dedup key carries the episode start, which
        # stays the same across re-trips inside one continuous breach, so they and any
        # resend are no-ops in Observe. Rows from before the field existed fall back to
        # the last-seen time.
        episode = detail.get("episode_start") or det.get("last_seen")
        last_seen = _iso_to_ts(episode, now)
        out.append(_record(
            last_seen, SEVERITY_WARN, str(det.get("title") or f"Container {slug} breach"),
            "observe.ha.watchdog.breach", f"watchdog:{slug}:{episode}",
            observe__source="watchdog",
            container__name=slug,
            observe__ha__watchdog__rule=WATCHDOG_RULE,
            observe__ha__watchdog__action=str(detail.get("action_taken") or ""),
            observe__ha__watchdog__restart_loop=bool(detail.get("restart_loop_suspected")),
            observe__ha__watchdog__cpu_percent=_number(detail.get("cpu_percent")),
            observe__ha__watchdog__memory_percent=_number(detail.get("memory_percent")),
        ))
    return out


def _crash_records(bundles: Any, now: float) -> list[dict[str, Any]]:
    out = []
    for bundle in _rows(bundles):
        bundle_id = bundle.get("id")
        classification = bundle.get("classification")
        if not isinstance(bundle_id, str) or not isinstance(classification, str):
            continue
        if bundle.get("dry_run"):
            continue  # A dry run is a drill triggered from the panel, not a host stop.
        severity = CRASH_SEVERITY.get(classification, SEVERITY_WARN)
        suspects = [
            f"{s.get('kind')}:{s.get('subject')}"
            for s in _rows(bundle.get("suspects"))[:3]
        ]
        body = CRASH_SUMMARY.get(classification, f"Unplanned stop ({classification})")
        out.append(_record(
            _iso_to_ts(bundle.get("ts"), now), severity, body, "observe.ha.crash",
            f"crash:{bundle_id}",
            observe__source="crash_forensics",
            observe__boot_id=bundle_id,
            observe__ha__crash__classification=classification,
            observe__ha__crash__gap_seconds=_number(bundle.get("gap_seconds")),
            observe__ha__crash__suspects="; ".join(suspects),
        ))
    return out


def build_logs(
    identity: Identity, snapshot: dict[str, Any], now: float,
    dropped: dict[str, int] | None = None,
) -> dict[str, Any]:
    """The ExportLogsServiceRequest for one snapshot: watchdog breaches and crash bundles.

    Crash records are rare and the more serious, so they are kept first and watchdog
    records fill the rest of the cap. If `dropped` is given, it receives the count of
    records left out per source ("watchdog", "crash_forensics").
    """
    crashes = _crash_records(snapshot.get("crash_bundles"), now)
    keep_crashes = crashes[:MAX_RECORDS]
    watchdog = _watchdog_records(snapshot.get("detections"), now)
    keep_watchdog = watchdog[: MAX_RECORDS - len(keep_crashes)]
    if dropped is not None:
        for source, all_, kept in (("watchdog", watchdog, keep_watchdog),
                                   ("crash_forensics", crashes, keep_crashes)):
            if len(all_) > len(kept):
                dropped[source] = dropped.get(source, 0) + len(all_) - len(kept)
    records = keep_watchdog + keep_crashes
    scopes = []
    for source, event in (("watchdog", "observe.ha.watchdog.breach"),
                          ("crash_forensics", "observe.ha.crash")):
        mine = [r for r in records if _event_name(r) == event]
        if mine:
            scopes.append({"scope": {"name": SCOPE_PREFIX + source}, "logRecords": mine})
    return {"resourceLogs": [{"resource": _resource(identity, now), "scopeLogs": scopes}]}


def _event_name(record: dict[str, Any]) -> str:
    for kv in record["attributes"]:
        if kv["key"] == "event.name":
            return kv["value"]["stringValue"]
    return ""


def has_records(request: dict[str, Any]) -> bool:
    return any(sl["logRecords"] for rl in request["resourceLogs"] for sl in rl["scopeLogs"])


def has_points(request: dict[str, Any]) -> bool:
    return any(sm["metrics"] for rm in request["resourceMetrics"] for sm in rm["scopeMetrics"])
