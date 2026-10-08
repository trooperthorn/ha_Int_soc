"""Golden and limit tests for the OTLP JSON mapper (custom_components/ha_soc/otlp_mapper.py).

The golden files in tests/fixtures/observe_otlp/ were checked against Observe's own decoder
and normaliser; docs/OBSERVE-VALIDATION.md records that run. The limit checks here repeat
Observe's rules (observe/otlp/normalize.py, observe/ingest/schema.py) so a drift in the
mapper fails in this repository without needing the Observe source.

To regenerate the golden files after an intended mapping change, run the tests once with
the environment variable UPDATE_GOLDEN=1, review the diff, and re-run the Observe check.
"""
import gzip
import json
import os
import re
from pathlib import Path

import pytest

from custom_components.ha_soc import otlp_mapper as om

FIXTURES = Path(__file__).parent / "fixtures" / "observe_otlp"
METRIC_RE = re.compile(r"^[a-z][a-z0-9_.]{0,127}$")
UNIT_RE = re.compile(r"^[A-Za-z0-9%/.{}_\[\]^*()' -]{0,32}$")
MAX_BODY = 1_048_576
MAX_POINTS, MAX_RECORDS = 5000, 500


def _load():
    raw = json.loads((FIXTURES / "snapshot.json").read_text(encoding="utf-8"))
    return om.Identity(**raw["identity"]), raw["snapshot"], raw["now"]


def _golden(name: str, actual: dict) -> dict:
    path = FIXTURES / f"{name}.json"
    text = json.dumps(actual, indent=2, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_GOLDEN"):
        path.write_text(text, encoding="utf-8", newline="\n")
        pytest.fail(f"UPDATE_GOLDEN wrote {path.name}; review the diff and re-run without it")
    return json.loads(path.read_text(encoding="utf-8"))


def _points(request):
    for rm in request["resourceMetrics"]:
        for sm in rm["scopeMetrics"]:
            for metric in sm["metrics"]:
                for dp in metric["gauge"]["dataPoints"]:
                    yield sm["scope"]["name"], metric, dp


def _records(request):
    return [r for rl in request["resourceLogs"] for sl in rl["scopeLogs"] for r in sl["logRecords"]]


def _attr_map(item):
    return {kv["key"]: next(iter(kv["value"].values())) for kv in item["attributes"]}


def _by_name(request, name):
    return [(_attr_map(dp), dp["asDouble"]) for _s, m, dp in _points(request) if m["name"] == name]


def test_metrics_golden():
    identity, snap, now = _load()
    out = om.build_metrics(identity, snap, now)
    assert out == _golden("metrics", out)


def test_logs_golden():
    identity, snap, now = _load()
    out = om.build_logs(identity, snap, now)
    assert out == _golden("logs", out)


def test_containers_units_and_ratios():
    identity, snap, now = _load()
    out = om.build_metrics(identity, snap, now)
    cpu = {a["container.name"]: v for a, v in _by_name(out, "container.cpu.utilization")}
    assert cpu["core"] == 0.125 and cpu["a0d7b954_probe"] == 0.91
    # A stopped add-on has no stats: no utilization point, but a running=0 point.
    assert "core_samba" not in cpu
    running = {a["container.name"]: v for a, v in _by_name(out, "observe.ha.container.running")}
    assert running["core_samba"] == 0.0 and running["core"] == 1.0
    units = {m["name"]: m["unit"] for _s, m, _d in _points(out)}
    assert units["container.memory.usage"] == "By"
    assert units["container.cpu.utilization"] == "1"


def test_watchdog_counts_only_open_breaches_and_logs_every_breach():
    identity, snap, now = _load()
    metrics = om.build_metrics(identity, snap, now)
    assert _by_name(metrics, "observe.ha.watchdog.breaches") == [
        ({"observe.ha.watchdog.rule": "container_resource_breach"}, 1.0)
    ]
    records = _records(om.build_logs(identity, snap, now))
    breaches = [r for r in records if _attr_map(r)["event.name"] == "observe.ha.watchdog.breach"]
    assert len(breaches) == 2
    assert {_attr_map(r)["container.name"] for r in breaches} == {"a0d7b954_probe", "core_samba"}


def test_crash_classification_severity():
    identity, snap, now = _load()
    crash = [r for r in _records(om.build_logs(identity, snap, now))
             if _attr_map(r)["event.name"] == "observe.ha.crash"]
    sev = {_attr_map(r)["observe.ha.crash.classification"]: r["severityNumber"] for r in crash}
    assert sev == {"silent_stop": 17, "core_restart": 13, "clean_reboot": 9}
    silent = next(r for r in crash if _attr_map(r)["observe.ha.crash.classification"] == "silent_stop")
    assert _attr_map(silent)["observe.ha.crash.suspects"].count(";") == 2  # three suspects at most
    assert _attr_map(silent)["observe.boot_id"] == "crash-2026-09-19T031500Z"


def test_integration_repair_backup_supervisor_points():
    identity, snap, now = _load()
    out = om.build_metrics(identity, snap, now)
    counts = {a["observe.ha.integration.category"]: v
              for a, v in _by_name(out, "observe.ha.integration.count")}
    assert counts["credential"] == 1.0 and counts["failing"] == 0.0
    repairs = _by_name(out, "observe.ha.repair.issues")
    assert ({"observe.ha.repair.state": "open"}, 3.0) in repairs
    assert _by_name(out, "observe.ha.backup.unprotected")[0][1] == 1.0
    assert _by_name(out, "observe.ha.supervisor.healthy")[0][1] == 0.0
    assert _by_name(out, "observe.ha.supervisor.supported")[0][1] == 0.0
    assert _by_name(out, "observe.ha.supervisor.unhealthy_reasons")[0][1] == 2.0
    # The per-domain and per-reason breakdowns have their own names.
    assert all(a == {"observe.ha.repair.state": "open"} for a, _v in repairs)
    by_domain = _by_name(out, "observe.ha.repair.domain_issues")
    assert sum(v for _a, v in by_domain) == 3.0
    assert len(_by_name(out, "observe.ha.supervisor.unhealthy_reason")) == 2


def test_clean_backup_and_healthy_supervisor():
    identity, snap, now = _load()
    snap = {**snap, "backup_finding": None, "resolution": {"unhealthy": [], "unsupported": []}}
    out = om.build_metrics(identity, snap, now)
    assert _by_name(out, "observe.ha.backup.unprotected") == [({}, 0.0)]
    assert _by_name(out, "observe.ha.supervisor.healthy") == [({}, 1.0)]


def test_unknown_sources_produce_no_points():
    identity, _snap, now = _load()
    assert not om.has_points(om.build_metrics(identity, {}, now))
    assert not om.has_records(om.build_logs(identity, {}, now))
    # Unusable values never become points.
    bad = {"containers": {"available": True, "containers": [
        {"slug": "x", "cpu_percent": float("nan"), "memory_percent": "a", "memory_usage": None}]}}
    names = [m["name"] for _s, m, _d in _points(om.build_metrics(identity, bad, now))
             if m["name"] != "observe.source.available"]
    assert names == []


def _check_limits(metrics, logs):
    n = 0
    for _scope, metric, dp in _points(metrics):
        n += 1
        assert METRIC_RE.match(metric["name"]), metric["name"]
        assert UNIT_RE.match(metric["unit"]), metric["unit"]
        assert len(dp["attributes"]) <= 32
        assert dp["timeUnixNano"].isdigit()
        assert isinstance(dp["asDouble"], float)
        for kv in dp["attributes"]:
            assert 0 < len(kv["key"]) <= 128
            assert len(str(next(iter(kv["value"].values())))) <= 1024
    assert n <= MAX_POINTS
    records = _records(logs)
    assert len(records) <= MAX_RECORDS
    for r in records:
        attrs = _attr_map(r)
        assert attrs["event.name"].startswith("observe.ha.")
        assert attrs["observe.dedup_key"]
        assert r["severityNumber"] in (9, 13, 17)
        assert len(r["attributes"]) <= 32
    for req, key in ((metrics, "resourceMetrics"), (logs, "resourceLogs")):
        for item in req[key]:
            keys = _attr_map(item["resource"])
            assert keys["host.name"] == "haos-lab"
            assert keys["service.name"] == "home-assistant"
            assert keys["observe.producer"] == "ha_Int_soc"
            assert len(item["resource"]["attributes"]) <= 64


def test_golden_files_obey_observe_limits():
    identity, snap, now = _load()
    _check_limits(om.build_metrics(identity, snap, now), om.build_logs(identity, snap, now))


def _large_snapshot():
    containers = [{"slug": f"addon_{i:03d}", "name": f"Add-on {i}", "kind": "addon",
                   "state": "started", "cpu_percent": 1.5, "memory_percent": 2.5,
                   "memory_usage": 1_000_000 + i} for i in range(80)]
    detections = [{"id": f"d{i}", "rule_id": "container_resource_breach", "status": "open",
                   "last_seen": f"2026-09-21T14:{i % 60:02d}:00+00:00", "title": "t" * 2000,
                   "detail": {"slug": f"addon_{i:03d}", "action_taken": "alerted"}}
                  for i in range(300)]
    bundles = [{"id": f"crash-{i:04d}", "ts": "2026-09-19T03:15:00+00:00",
                "classification": "silent_stop", "gap_seconds": 1.0,
                "suspects": [{"kind": "container", "subject": "s" * 200}] * 3}
               for i in range(300)]
    integrations = [{"domain": f"dom{i}", "error_count_24h": i, "issue_category": "errors"}
                    for i in range(400)]
    repairs = [{"domain": f"dom{i}", "issue_id": f"i{i}"} for i in range(400)]
    return {
        "containers": {"available": True, "containers": containers},
        "detections": detections, "crash_bundles": bundles,
        "integration_overview": {"category_counts": {"errors": 400}, "integrations": integrations},
        "repairs": repairs, "backup_checked": True, "backup_finding": None,
        "resolution": {"unhealthy": [f"r{i}" for i in range(300)], "unsupported": []},
    }


@pytest.mark.parametrize("compressed", [False, True])
def test_large_install_payload_is_within_observe_limits(compressed):
    identity, _snap, now = _load()
    snap = _large_snapshot()
    metrics = om.build_metrics(identity, snap, now)
    logs = om.build_logs(identity, snap, now)
    _check_limits(metrics, logs)
    for req in (metrics, logs):
        body = json.dumps(req, separators=(",", ":")).encode("utf-8")
        if compressed:
            body = gzip.compress(body)
        assert len(body) <= MAX_BODY, len(body)
    assert len(_records(logs)) == MAX_RECORDS


def test_resolution_with_null_lists_does_not_raise():
    req = om.build_metrics(om.Identity(host_name="h"),
                           {"resolution": {"unhealthy": None, "unsupported": 5}}, 1.0)
    assert om.has_points(req)


def test_crash_records_survive_a_watchdog_flood_and_drops_are_reported():
    dets = [{"rule_id": om.WATCHDOG_RULE, "id": str(i), "last_seen": f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}+00:00",
             "detail": {"slug": f"c{i}"}} for i in range(600)]
    crashes = [{"id": "boot1", "classification": "kernel_fault", "ts": "2026-01-01T00:00:00+00:00"}]
    dropped = {}
    req = om.build_logs(om.Identity(host_name="h"),
                        {"detections": dets, "crash_bundles": crashes}, 1.0, dropped)
    recs = _records(req)
    assert len(recs) == om.MAX_RECORDS
    assert any(_attr_map(r)["event.name"] == "observe.ha.crash" for r in recs)
    assert dropped == {"watchdog": 101}


def test_row_cap_drops_are_reported():
    rows = [{"slug": f"c{i}", "cpu_percent": 1.0} for i in range(om.MAX_ROWS + 3)]
    dropped = {}
    om.build_metrics(om.Identity(host_name="h"),
                     {"containers": {"available": True, "containers": rows}}, 1.0, dropped)
    assert dropped == {"containers": 3}


def _series_keys(request):
    return [(m["name"], tuple(sorted((k, str(v)) for k, v in _attr_map(dp).items())))
            for _s, m, dp in _points(request)]


def test_entries_of_one_integration_make_one_distinct_series():
    identity, snap, now = _load()
    out = om.build_metrics(identity, snap, now)
    esphome = [(a, v) for a, v in _by_name(out, "observe.ha.integration.errors")
               if a["observe.ha.integration"] == "esphome"]
    assert esphome == [({"observe.ha.integration": "esphome",
                         "observe.ha.integration.category": "errors"}, 12.0)]
    keys = _series_keys(out)
    assert len(keys) == len(set(keys)), "two points share a series; Observe would keep one"


def test_a_domain_in_two_categories_is_one_series_with_the_first_category():
    rows = [{"domain": "esphome", "error_count_24h": 4, "issue_category": "errors"},
            {"domain": "esphome", "error_count_24h": 4, "issue_category": "communication"}]
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"integration_overview": {"integrations": rows}}, 1.0)
    assert _by_name(out, "observe.ha.integration.errors") == [
        ({"observe.ha.integration": "esphome",
          "observe.ha.integration.category": "communication"}, 4.0)]


def test_three_entries_of_one_domain_do_not_multiply_the_errors():
    """Audit probe p09: every entry of a domain carries the domain's whole count."""
    rows = [{"domain": "esphome", "error_count_24h": 5, "issue_category": "communication"}
            for _ in range(3)]
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"integration_overview": {"integrations": rows}}, 1.0)
    errors = _by_name(out, "observe.ha.integration.errors")
    assert [v for _a, v in errors] == [5.0]


def test_stopped_and_unknown_containers_are_not_running():
    """Audit probe p04: a None, unknown or error state used to count as running."""
    states = {"s": "started", "t": "stopped", "u": "unknown", "e": "error", "n": None}
    rows = [{"slug": slug, "state": state} for slug, state in states.items()]
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"containers": {"available": True, "containers": rows}}, 1.0)
    running = {a["container.name"]: v for a, v in _by_name(out, "observe.ha.container.running")}
    assert running == {"s": 1.0, "t": 0.0, "u": 0.0, "e": 0.0}


def test_utilization_is_a_ratio_clamped_into_zero_to_one():
    """Audit probe p04: 230 percent became 2.3 under the unit 1."""
    rows = [{"slug": "x", "state": "started", "cpu_percent": 230.0, "memory_percent": 10.0},
            {"slug": "y", "state": "started", "cpu_percent": -3.0, "memory_percent": 100.5}]
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"containers": {"available": True, "containers": rows}}, 1.0)
    cpu = {a["container.name"]: v for a, v in _by_name(out, "container.cpu.utilization")}
    mem = {a["container.name"]: v for a, v in _by_name(out, "container.memory.utilization")}
    assert cpu == {"x": 1.0, "y": 0.0} and mem == {"x": 0.1, "y": 1.0}


def test_no_metric_has_a_total_series_beside_labelled_series():
    """A sum over any one metric name must not count an item twice."""
    identity, snap, now = _load()
    snap = {**snap, "repairs": [{"domain": "a"}, {"domain": "a"}, {"domain": "b"}],
            "resolution": {"data": {"unhealthy": ["privileged", "docker"], "unsupported": []}}}
    out = om.build_metrics(identity, snap, now)
    series: dict[str, list[dict]] = {}
    for _s, m, dp in _points(out):
        series.setdefault(m["name"], []).append(_attr_map(dp))
    for name, attrs in series.items():
        if name in ("observe.ha.integration.count", "observe.ha.push.rows_dropped",
                    "observe.ha.watchdog.breaches"):
            continue  # one series per distinct label value, never a total next to them
        if len(attrs) > 1:
            assert all(a for a in attrs), f"{name} has an unlabelled total beside labelled series"
    repairs = [v for _a, v in _by_name(out, "observe.ha.repair.issues")]
    assert repairs == [3.0]
    assert sum(v for _a, v in _by_name(out, "observe.ha.repair.domain_issues")) == 3.0


def test_integration_cap_keeps_the_domains_with_the_most_errors_and_reports_the_rest():
    """Audit probe p09: the alphabetical cap dropped zwave_js (50 errors) and zha."""
    rows = [{"domain": f"{c}{i:03d}", "issue_category": "errors", "error_count_24h": 1}
            for i in range(60) for c in "ab"]
    rows += [{"domain": "zwave_js", "issue_category": "errors", "error_count_24h": 50},
             {"domain": "zha", "issue_category": "errors", "error_count_24h": 9}]
    dropped: dict[str, int] = {}
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"integration_overview": {"integrations": rows}}, 1.0, dropped)
    names = {a["observe.ha.integration"] for a, _v in _by_name(out, "observe.ha.integration.errors")}
    assert {"zwave_js", "zha"} <= names and len(names) == om.MAX_ROWS
    assert dropped == {"integrations": 22}
    # The cut is visible in the payload itself, one point per kind, zero when nothing was cut.
    sent = {a["observe.ha.push.kind"]: v for a, v in _by_name(out, "observe.ha.push.rows_dropped")}
    assert sent == {"containers": 0.0, "integrations": 22.0, "repair_domains": 0.0,
                    "unhealthy_reasons": 0.0, "points": 0.0}


def test_dry_run_bundle_is_never_sent_as_a_crash():
    identity, snap, now = _load()
    ids = {_attr_map(r)["observe.boot_id"] for r in _records(om.build_logs(identity, snap, now))
           if _attr_map(r)["event.name"] == "observe.ha.crash"}
    assert "crash-2026-09-21T120000Z" not in ids and len(ids) == 3
    only = om.build_logs(om.Identity(host_name="h"), {"crash_bundles": [
        {"id": "crash-x", "classification": "silent_stop", "dry_run": True}]}, 1.0)
    assert _records(only) == []


def test_watchdog_record_key_is_the_episode_start_not_the_last_seen_time():
    def det(last_seen):
        return {"rule_id": om.WATCHDOG_RULE, "id": "watchdog_c", "status": "open",
                "last_seen": last_seen,
                "detail": {"slug": "c", "episode_start": "2026-01-01T00:00:00+00:00"}}
    keys = {_attr_map(r)["observe.dedup_key"] for t in ("2026-01-01T00:03:00+00:00",
                                                         "2026-01-01T00:06:00+00:00")
            for r in _records(om.build_logs(om.Identity(host_name="h"),
                                            {"detections": [det(t)]}, 1.0))}
    assert len(keys) == 1


# -- availability, identity and honest gaps (October audit, slice s8) -------------------------


def _resource_map(request, key):
    return _attr_map(request[key][0]["resource"])


def _normalise_like_observe(request, key):
    """The platform, agent version and send time Observe's normaliser reads from a resource.

    Repeats observe/otlp/normalize.py: os.type is the platform when it is a string,
    service.version the agent version, and observe.agent.sent_at must decode to unix seconds
    between 0 and 253402300800 (an intValue string is accepted).
    """
    res = _resource_map(request, key)
    sent = res.get("observe.agent.sent_at")
    sent = int(sent) if isinstance(sent, str) and re.fullmatch(r"-?[0-9]{1,19}", sent) else sent
    assert isinstance(sent, (int, float)) and not isinstance(sent, bool)
    assert 0 <= sent < 253_402_300_800
    assert isinstance(res["os.type"], str) and res["os.type"]
    assert isinstance(res["service.version"], str) and res["service.version"]
    return res["os.type"], res["service.version"], float(sent)


def test_both_requests_carry_platform_version_and_send_time():
    identity, snap, now = _load()
    metrics, logs = om.build_metrics(identity, snap, now), om.build_logs(identity, snap, now)
    for request, key in ((metrics, "resourceMetrics"), (logs, "resourceLogs")):
        platform, version, sent = _normalise_like_observe(request, key)
        assert (platform, version, sent) == ("homeassistant", "2026.9.3", now)


def _sources(request):
    return {a["observe.source"]: (v, a.get("observe.source.reason"))
            for a, v in _by_name(request, "observe.source.available")}


def test_every_source_is_available_in_the_golden_snapshot():
    identity, snap, now = _load()
    out = om.build_metrics(identity, snap, now)
    assert _sources(out) == {s: (1.0, None) for s in (
        "containers", "watchdog", "integrations", "repairs", "backup", "supervisor",
        "crash_forensics")}


def test_a_source_that_could_not_be_read_is_unavailable_with_a_reason():
    identity, snap, now = _load()
    snap = {k: v for k, v in snap.items() if k not in ("containers", "resolution", "crash_bundles")}
    snap["repairs"] = []  # quiet, not broken
    out = om.build_metrics(identity, snap, now)
    status = _sources(out)
    for source in ("containers", "supervisor", "crash_forensics"):
        assert status[source][0] == 0.0 and status[source][1]
    # A quiet source is available and still sends its zero.
    assert status["repairs"] == (1.0, None)
    assert _by_name(out, "observe.ha.repair.issues") == [({"observe.ha.repair.state": "open"}, 0.0)]


def test_a_collector_reason_is_passed_on():
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"containers": {"available": False, "reason": "no Supervisor"}}, 1.0)
    assert _sources(out)["containers"] == (0.0, "no Supervisor")


def test_unreadable_backup_store_is_unavailable_not_zero():
    """Audit: an unreadable .storage/backup was sent as observe.ha.backup.unprotected 0."""
    identity, snap, now = _load()
    snap = {**snap, "backup_finding": None, "backup_checked": True,
            "backup_unreadable": "the backup store could not be read"}
    out = om.build_metrics(identity, snap, now)
    assert _by_name(out, "observe.ha.backup.unprotected") == []
    assert _sources(out)["backup"] == (0.0, "the backup store could not be read")
    # Read again later: the gauge and the available status come back.
    snap["backup_unreadable"] = None
    out = om.build_metrics(identity, snap, now)
    assert _by_name(out, "observe.ha.backup.unprotected") == [({}, 0.0)]
    assert _sources(out)["backup"] == (1.0, None)


def test_backup_before_the_first_sweep_is_unavailable():
    out = om.build_metrics(om.Identity(host_name="h"),
                           {"repairs": [], "backup_finding": None, "backup_checked": False}, 1.0)
    assert _by_name(out, "observe.ha.backup.unprotected") == []
    assert _sources(out)["backup"][0] == 0.0


def test_an_empty_snapshot_still_sends_no_source_status():
    assert not om.has_points(om.build_metrics(om.Identity(host_name="h"), {}, 1.0))


def _overview(*rows):
    return {"integration_overview": {"integrations": [
        {"domain": d, "issue_category": c, "error_count_24h": n} for d, c, n in rows]}}


def _errors(request):
    return {(a["observe.ha.integration"], a["observe.ha.integration.category"]): v
            for a, v in _by_name(request, "observe.ha.integration.errors")}


def test_a_recovered_integration_is_zeroed_once():
    """Audit: a removed or re-categorised integration kept its last error count in Observe."""
    ident, series = om.Identity(host_name="h"), set()
    first = om.build_metrics(ident, _overview(("hue", "errors", 7), ("zha", "errors", 2)),
                             1.0, None, series)
    assert _errors(first) == {("hue", "errors"): 7.0, ("zha", "errors"): 2.0}
    second = om.build_metrics(ident, _overview(("zha", "errors", 2)), 2.0, None, series)
    assert _errors(second) == {("zha", "errors"): 2.0, ("hue", "errors"): 0.0}
    third = om.build_metrics(ident, _overview(("zha", "errors", 2)), 3.0, None, series)
    assert _errors(third) == {("zha", "errors"): 2.0}


def test_a_domain_that_changes_category_zeroes_its_old_series():
    ident, series = om.Identity(host_name="h"), set()
    om.build_metrics(ident, _overview(("hue", "failing", 7)), 1.0, None, series)
    out = om.build_metrics(ident, _overview(("hue", "errors", 7)), 2.0, None, series)
    assert _errors(out) == {("hue", "errors"): 7.0, ("hue", "failing"): 0.0}


def test_a_domain_cut_by_the_row_cap_is_not_zeroed():
    ident, series = om.Identity(host_name="h"), set()
    rows = [(f"d{i:03d}", "errors", i + 1) for i in range(om.MAX_ROWS)]
    om.build_metrics(ident, _overview(*rows), 1.0, None, series)
    assert ("d000", "errors") in series
    out = om.build_metrics(ident, _overview(("zz", "errors", 1000), *rows), 2.0, None, series)
    assert ("d000", "errors") not in _errors(out)  # the lowest count was cut
    assert ("d000", "errors") in series  # still remembered, and no zero was sent for it
    assert 0.0 not in _errors(out).values()


def test_no_series_memory_means_no_zero():
    ident = om.Identity(host_name="h")
    om.build_metrics(ident, _overview(("hue", "errors", 7)), 1.0)
    out = om.build_metrics(ident, _overview(("zha", "errors", 2)), 2.0)
    assert _errors(out) == {("zha", "errors"): 2.0}


def test_a_failed_overview_keeps_the_series_memory():
    ident, series = om.Identity(host_name="h"), set()
    om.build_metrics(ident, _overview(("hue", "errors", 7)), 1.0, None, series)
    om.build_metrics(ident, {"repairs": []}, 2.0, None, series)
    assert series == {("hue", "errors")}
