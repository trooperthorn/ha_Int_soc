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


def _resource(identity: Identity) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "host.name": identity.host_name,
        "service.name": SERVICE_NAME,
        "observe.producer": PRODUCER,
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
        self, source: str, name: str, unit: str, value: Any, **attrs: Any
    ) -> None:
        number = _number(value)
        if number is None:
            return
        if self.count >= MAX_POINTS:
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


def _containers(m: _Metrics, overview: Any) -> None:
    if not isinstance(overview, dict) or not overview.get("available"):
        return
    for row in _capped(m, "containers", _rows(overview.get("containers"))):
        slug = row.get("slug")
        if not isinstance(slug, str) or not slug:
            continue
        cpu, mem = _number(row.get("cpu_percent")), _number(row.get("memory_percent"))
        m.gauge("containers", "container.cpu.utilization", "1",
                None if cpu is None else round(cpu / 100, 6), container__name=slug)
        m.gauge("containers", "container.memory.utilization", "1",
                None if mem is None else round(mem / 100, 6), container__name=slug)
        m.gauge("containers", "container.memory.usage", "By",
                row.get("memory_usage"), container__name=slug)
        running = 1 if row.get("state") in ("started", None) else 0
        m.gauge("containers", "observe.ha.container.running", "1", running,
                container__name=slug)


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


def _integrations(m: _Metrics, overview: Any) -> None:
    if not isinstance(overview, dict):
        return
    counts = overview.get("category_counts")
    if isinstance(counts, dict):
        for category in sorted(counts):
            m.gauge("integrations", "observe.ha.integration.count", "{integration}",
                    counts[category], observe__ha__integration__category=str(category))
    # Several config entries of one domain (three ESPHome devices) would otherwise write
    # identical series, which Observe keeps only one of. Sum them per domain and category.
    grouped: dict[tuple[str, str], float] = {}
    for row in _rows(overview.get("integrations")):
        domain = row.get("domain")
        if isinstance(domain, str) and domain:
            key = (domain, str(row.get("issue_category", "")))
            grouped[key] = grouped.get(key, 0) + (_number(row.get("error_count_24h")) or 0)
    for domain, category in _capped(m, "integrations", sorted(grouped)):
        m.gauge("integrations", "observe.ha.integration.errors", "{error}",
                grouped[(domain, category)], observe__ha__integration=domain,
                observe__ha__integration__category=category)


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
    for domain in _capped(m, "repair_domains", sorted(by_domain)):
        m.gauge("repairs", "observe.ha.repair.issues", "{issue}", by_domain[domain],
                observe__ha__repair__state="open", observe__ha__repair__domain=domain)


def _backup(m: _Metrics, finding: Any, checked: bool) -> None:
    """One gauge: 1 while the unprotected-backup finding is open, 0 when the check ran clean."""
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
    m.gauge("supervisor", "observe.ha.supervisor.unhealthy_reasons", "{reason}", len(unhealthy))
    for reason in _capped(m, "unhealthy_reasons", sorted(unhealthy)):
        m.gauge("supervisor", "observe.ha.supervisor.unhealthy_reasons", "{reason}", 1,
                observe__ha__supervisor__reason=reason)


def build_metrics(
    identity: Identity, snapshot: dict[str, Any], now: float,
    dropped: dict[str, int] | None = None,
) -> dict[str, Any]:
    """The ExportMetricsServiceRequest for one snapshot taken at `now` (unix seconds).

    Rows and points past the caps are left out; if `dropped` is given, it receives the
    count left out per kind ("containers", "integrations", "repair_domains",
    "unhealthy_reasons", "points") so the sender can log it.
    """
    m = _Metrics(now, dropped)
    _containers(m, snapshot.get("containers"))
    _watchdog(m, snapshot.get("detections"))
    _integrations(m, snapshot.get("integration_overview"))
    _repairs(m, snapshot.get("repairs"))
    _backup(m, snapshot.get("backup_finding"), bool(snapshot.get("backup_checked")))
    _supervisor(m, snapshot.get("resolution"))
    return {
        "resourceMetrics": [
            {"resource": _resource(identity), "scopeMetrics": m.scope_metrics()}
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
    return {"resourceLogs": [{"resource": _resource(identity), "scopeLogs": scopes}]}


def _event_name(record: dict[str, Any]) -> str:
    for kv in record["attributes"]:
        if kv["key"] == "event.name":
            return kv["value"]["stringValue"]
    return ""


def has_records(request: dict[str, Any]) -> bool:
    return any(sl["logRecords"] for rl in request["resourceLogs"] for sl in rl["scopeLogs"])


def has_points(request: dict[str, Any]) -> bool:
    return any(sm["metrics"] for rm in request["resourceMetrics"] for sm in rm["scopeMetrics"])
