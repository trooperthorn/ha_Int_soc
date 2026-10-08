"""The Observe queue across reloads and long outages, and trust for a private certificate.

Covers docs/design.md, "Observe push": the queue survives an options reload, an outage of
hours resends each log record once and keeps the whole outage as metrics inside the memory
bound, and a server with a self-signed certificate is trusted only when the owner pasted its
CA or pinned its fingerprint. Time is injected, so nothing sleeps.
"""
from __future__ import annotations

import asyncio
import datetime
import gzip
import hashlib
import ipaddress
import json
import ssl
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from custom_components.ha_soc import observe_push as op
from custom_components.ha_soc.const import (
    CONF_OBSERVE_CA_PEM,
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_FINGERPRINT,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
)

from .test_observe_push import (  # noqa: F401 - fixtures and helpers shared with that module
    HOST,
    KEY,
    FakeObserve,
    _open,
    _pusher,
    _snapshot,
    entry,
    observe,
)

ISOLATED_CONFIG_DIR = True

OUTAGE = (503, {}, "")
HELD = (503, {"Retry-After": "3600"}, "")


# --------------------------------------------------------------------------- reload


async def _enable(entry, url: str, host: str = HOST) -> None:
    runtime = entry.runtime_data
    # One open watchdog breach, so the real snapshot carries a log record as well as metrics.
    runtime.store.data["detections"]["watchdog_probe"] = {
        "id": "watchdog_probe",
        "rule_id": "container_resource_breach",
        "status": "open",
        "last_seen": "2026-09-21T14:10:00+00:00",
        "title": "Container probe breach",
        "detail": {"slug": "probe", "episode_start": "2026-09-21T13:50:00+00:00"},
    }
    runtime.store.async_update_settings(
        **{
            CONF_OBSERVE_ENABLED: True,
            CONF_OBSERVE_URL: url,
            CONF_OBSERVE_HOST_NAME: host,
            CONF_OBSERVE_INTERVAL: 60,
        }
    )
    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)


async def _reload(hass, entry) -> None:
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()


async def test_reload_keeps_queued_payloads(hass, entry, observe) -> None:
    """Probe observe-queue-discarded-on-reload: an options reload used to empty the queue."""
    await _enable(entry, observe.url)
    observe.script = [HELD]
    await _reload(hass, entry)
    queued = [p.idempotency_key for p in entry.runtime_data.observe._queue]
    assert len(queued) == 2  # the metrics payload that failed and the logs payload behind it
    assert [r["path"] for r in observe.requests] == ["/v1/metrics"]

    await _reload(hass, entry)

    # The wait the server asked for (Retry-After) survives the reload: nothing was sent.
    pusher = entry.runtime_data.observe
    assert [r["path"] for r in observe.requests] == ["/v1/metrics"]
    assert set(queued) <= {p.idempotency_key for p in pusher._queue}
    assert pusher._retry_at > 0.0

    pusher._retry_at = 0.0  # the wait is over
    await pusher.async_push_once()

    assert pusher.status["queue_length"] == 0  # taken over and delivered
    sent = [r["headers"]["Idempotency-Key"] for r in observe.requests]
    assert set(queued) <= set(sent)
    # The logs went out once, although the second collection saw the same records.
    assert [r["path"] for r in observe.requests].count("/v1/logs") == 1


async def test_reload_retries_at_once_after_a_rejected_key(hass, entry, observe) -> None:
    """An auth backoff is not carried: the owner reloads because the key was just fixed."""
    await _enable(entry, observe.url)
    observe.script = [(401, {}, "")]
    await _reload(hass, entry)
    assert entry.runtime_data.observe.status["auth_rejected"] is True
    observe.requests.clear()
    await _reload(hass, entry)
    assert observe.requests  # sent again straight away


async def test_reload_with_a_new_destination_drops_the_queue(hass, entry, observe, caplog) -> None:
    await _enable(entry, observe.url)
    observe.script = [HELD]
    await _reload(hass, entry)
    queued = {p.idempotency_key for p in entry.runtime_data.observe._queue}
    assert queued

    observe.requests.clear()
    entry.runtime_data.store.async_update_settings(**{CONF_OBSERVE_HOST_NAME: "another-host"})
    await _reload(hass, entry)

    sent = {r["headers"]["Idempotency-Key"] for r in observe.requests}
    assert not queued & sent  # nothing queued for the old host name reached the server
    assert "dropped 2 queued payload(s)" in caplog.text


async def test_disabling_the_push_forgets_the_queue(hass, entry, observe) -> None:
    await _enable(entry, observe.url)
    observe.script = [HELD]
    await _reload(hass, entry)
    assert entry.runtime_data.observe._queue

    entry.runtime_data.store.async_update_settings(**{CONF_OBSERVE_ENABLED: False})
    await _reload(hass, entry)
    assert not hass.data.get(op.DATA_QUEUE_CARRY)

    entry.runtime_data.store.async_update_settings(**{CONF_OBSERVE_ENABLED: True})
    observe.script = [HELD]
    await _reload(hass, entry)
    # Only what the new start queued itself; the old payloads are gone.
    assert len(entry.runtime_data.observe._queue) == 2


async def test_removing_the_entry_forgets_the_queue(hass, entry, observe) -> None:
    await _enable(entry, observe.url)
    observe.script = [HELD]
    await _reload(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.data[op.DATA_QUEUE_CARRY][entry.entry_id].queue
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(op.DATA_QUEUE_CARRY, {})


# --------------------------------------------------------------------------- log dedup


def _crash(n: int) -> dict[str, Any]:
    return {"id": f"crash-new-{n}", "ts": "2026-09-19T03:15:00+00:00", "classification": "silent_stop"}


def _log_keys(request: dict[str, Any]) -> list[str]:
    return [
        k
        for rl in request["resourceLogs"]
        for sl in rl["scopeLogs"]
        for rec in sl["logRecords"]
        if (k := op._log_key(rec))
    ]


async def test_queued_log_keys_are_not_queued_again(hass, entry, observe) -> None:
    """Probe observe-outage-duplicate-log-records: every payload repeated every record."""
    extra: list[dict[str, Any]] = []

    async def collect() -> dict[str, Any]:
        snapshot = _snapshot()
        snapshot["crash_bundles"] = list(snapshot["crash_bundles"]) + extra
        return snapshot

    observe.script = [HELD] * 50
    pusher, clock = await _pusher(hass, entry, observe.url, collect=collect)
    try:
        for n in range(3):
            extra.append(_crash(n))
            clock.now += 4000
            await pusher.async_push_once()
        logs = [p for p in pusher._queue if p.signal == "logs"]
        assert len(logs) == 4  # the first cycle's records, then one new record per cycle
        seen: list[str] = []
        for payload in logs:
            keys = _log_keys(json.loads(gzip.decompress(payload.body)))
            assert set(keys) == set(payload.dedup_keys)  # the payload holds exactly its keys
            seen += keys
        assert len(seen) == len(set(seen))  # no record twice
        assert [len(p.dedup_keys) for p in logs][1:] == [1, 1, 1]
    finally:
        pusher.async_stop()


# --------------------------------------------------------------------------- long outage


async def test_two_hour_outage_resends_each_record_once_and_keeps_the_metrics(
    hass, entry, observe
) -> None:
    wall = {"now": 1_790_000_000.0}
    start = wall["now"]
    observe.script = [OUTAGE] * 400
    pusher, clock = await _pusher(hass, entry, observe.url, wall=lambda: wall["now"])
    try:
        longest = 0
        biggest = 0
        for _ in range(130):  # a little over two hours at one push a minute
            wall["now"] += 60
            clock.now += op.BACKOFF_MAX_SECONDS + 1
            await pusher.async_push_once()
            longest = max(longest, len(pusher._queue))
            biggest = max(biggest, pusher.status["queue_bytes"])
        status = pusher.status
        assert longest <= op.MAX_QUEUE
        assert biggest <= op.MAX_QUEUE_BYTES
        assert status["dropped_overflow"] == 0
        assert status["compactions"] >= 1
        assert [p.signal for p in pusher._queue].count("logs") == 1

        observe.requests.clear()
        observe.script = []
        clock.now += op.BACKOFF_MAX_SECONDS + 1
        await pusher.async_push_once()
        assert pusher.status["queue_length"] == 0

        keys: list[str] = []
        times: dict[str, list[int]] = {}
        for request in observe.requests:
            body = request["json"]
            if request["path"].endswith("/logs"):
                keys += _log_keys(body)
                continue
            for rm in body["resourceMetrics"]:
                for sm in rm["scopeMetrics"]:
                    for metric in sm["metrics"]:
                        for point in metric["gauge"]["dataPoints"]:
                            ident = json.dumps([sm["scope"]["name"], metric["name"], point["attributes"]])
                            times.setdefault(ident, []).append(int(point["timeUnixNano"]) // 10**9)
        expected = op._dedup_keys(
            op.otlp_mapper.build_logs(op.otlp_mapper.Identity(HOST), _snapshot(), start)
        )
        assert expected
        assert sorted(keys) == sorted(expected)  # each record exactly once

        cpu = [sorted(series) for ident, series in times.items() if "container.cpu.utilization" in ident]
        assert cpu
        step = op.COMPACT_INTERVALS_SECONDS[0]
        for series in cpu:
            assert series[0] <= start + 60 + step
            assert series[-1] >= wall["now"] - 60
            assert series[-1] - series[0] >= 2 * 3600
            gaps = [b - a for a, b in zip(series, series[1:])]
            assert max(gaps) <= 2 * step
    finally:
        pusher.async_stop()


def _metrics_request(ts: int, value: float, name: str = "m") -> dict[str, Any]:
    point = {"attributes": [], "timeUnixNano": str(ts * 10**9), "asDouble": value}
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": [{"key": "sent_at", "value": {"intValue": ts}}]},
                "scopeMetrics": [
                    {
                        "scope": {"name": "s"},
                        "metrics": [{"name": name, "unit": "1", "gauge": {"dataPoints": [point]}}],
                    }
                ],
            }
        ]
    }


def test_compact_metrics_keeps_the_newest_point_per_series_per_interval() -> None:
    requests = [_metrics_request(1000 + 60 * i, float(i)) for i in range(12)]
    requests.append(_metrics_request(1000, 9.0, "other"))
    merged = op.compact_metrics(requests, 300)
    assert merged["resourceMetrics"][0]["resource"] == requests[-1]["resourceMetrics"][0]["resource"]
    by_name = {
        m["name"]: [(int(p["timeUnixNano"]) // 10**9, p["asDouble"]) for p in m["gauge"]["dataPoints"]]
        for sm in merged["resourceMetrics"][0]["scopeMetrics"]
        for m in sm["metrics"]
    }
    assert by_name["other"] == [(1000, 9.0)]
    # 1000..1660 falls into the buckets 900-1199, 1200-1499 and 1500-1799.
    assert by_name["m"] == [(1180, 3.0), (1480, 8.0), (1660, 11.0)]
    # Merging a merged request again changes nothing.
    assert op.compact_metrics([merged], 300) == merged


async def test_log_payloads_cannot_be_merged_so_the_oldest_is_dropped(hass, entry, observe) -> None:
    counter = {"n": 0}

    async def collect() -> dict[str, Any]:
        counter["n"] += 1
        snapshot = _snapshot()
        snapshot["crash_bundles"] = [_crash(counter["n"])]
        return snapshot

    observe.script = [HELD]
    pusher, _ = await _pusher(hass, entry, observe.url, collect=collect)
    try:
        for _ in range(op.MAX_QUEUE + 5):
            await pusher.async_push_once()
        assert pusher.status["queue_length"] <= op.MAX_QUEUE
        assert pusher.status["dropped_overflow"] > 0
    finally:
        pusher.async_stop()


async def test_the_merge_interval_widens_until_the_result_fits(hass, entry, observe) -> None:
    wall = {"now": 1_790_000_000.0}
    observe.script = [OUTAGE] * 400
    with patch.object(op, "MAX_MERGED_BYTES", 1):
        pusher, clock = await _pusher(hass, entry, observe.url, wall=lambda: wall["now"])
        try:
            for _ in range(op.MAX_QUEUE + 2):
                wall["now"] += 60
                clock.now += op.BACKOFF_MAX_SECONDS + 1
                await pusher.async_push_once()
            # A cap nothing can meet walks through every interval and still stays bounded.
            assert pusher.status["compactions"] >= len(op.COMPACT_INTERVALS_SECONDS)
            assert pusher.status["queue_length"] <= op.MAX_QUEUE
        finally:
            pusher.async_stop()


# --------------------------------------------------------------------------- certificate trust


def _certificate(tmp_path: Path, name: str, ip: str = "127.0.0.1"):
    """A self-signed server certificate that is its own CA: (pem, der, cert file, key file)."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    usage = x509.KeyUsage(
        digital_signature=True,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=True,
        crl_sign=False,
        encipher_only=False,
        decipher_only=False,
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]), False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), True)
        .add_extension(usage, True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), False)
        .sign(key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    der = cert.public_bytes(serialization.Encoding.DER)
    cert_file = tmp_path / f"{name}.pem"
    key_file = tmp_path / f"{name}.key"
    cert_file.write_text(pem)
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return pem, der, cert_file, key_file


@pytest.fixture
async def tls_observe(socket_enabled, tmp_path):
    pem, der, cert_file, key_file = _certificate(tmp_path, "observe-private")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    fake = FakeObserve()
    fake.url = await fake.start(context)
    fake.pem = pem
    fake.fingerprint = hashlib.sha256(der).hexdigest()
    fake.other_pem = _certificate(tmp_path, "somebody-else")[0]
    yield fake
    await fake.close()


@pytest.fixture
async def handshake_aborts(hass):
    """Let the fake server see a client abort the TLS handshake without failing the test.

    A client that refuses the certificate resets the connection, which asyncio reports on the
    server side as an unhandled error; the Home Assistant test plugin would fail the test on it.
    """
    loop = asyncio.get_running_loop()
    inner = loop.get_exception_handler()

    def handler(loop, context):
        if context.get("message", "").startswith("Error on transport creation") and isinstance(
            context.get("exception"), ConnectionResetError
        ):
            return
        inner(loop, context)

    loop.set_exception_handler(handler)
    yield
    loop.set_exception_handler(inner)


async def test_a_self_signed_server_is_refused_without_the_configured_ca(
    hass, entry, tls_observe, handshake_aborts
) -> None:
    pusher, _ = await _pusher(hass, entry, tls_observe.url)
    try:
        assert tls_observe.requests == []
        assert pusher.status["sent_ok"] == 0
        assert pusher.status["last_status"] == "ClientConnectorCertificateError"
    finally:
        pusher.async_stop()


async def test_a_self_signed_server_is_trusted_with_its_ca(hass, entry, tls_observe) -> None:
    pusher, _ = await _pusher(hass, entry, tls_observe.url, **{CONF_OBSERVE_CA_PEM: tls_observe.pem})
    try:
        assert [r["path"] for r in tls_observe.requests] == ["/v1/metrics", "/v1/logs"]
        assert pusher.status["sent_ok"] == 2
        assert KEY in tls_observe.requests[0]["headers"]["Authorization"]
    finally:
        pusher.async_stop()


async def test_another_ca_does_not_make_the_server_trusted(
    hass, entry, tls_observe, handshake_aborts
) -> None:
    pusher, _ = await _pusher(
        hass, entry, tls_observe.url, **{CONF_OBSERVE_CA_PEM: tls_observe.other_pem}
    )
    try:
        assert tls_observe.requests == []
        assert pusher.status["last_status"] == "ClientConnectorCertificateError"
    finally:
        pusher.async_stop()


async def test_a_pinned_fingerprint_trusts_exactly_that_certificate(hass, entry, tls_observe) -> None:
    pusher, _ = await _pusher(
        hass, entry, tls_observe.url, **{CONF_OBSERVE_FINGERPRINT: tls_observe.fingerprint}
    )
    try:
        assert pusher.status["sent_ok"] == 2
    finally:
        pusher.async_stop()
    tls_observe.requests.clear()
    wrong, _ = await _pusher(hass, entry, tls_observe.url, **{CONF_OBSERVE_FINGERPRINT: "ab" * 32})
    try:
        assert wrong.status["sent_ok"] == 0
        assert tls_observe.requests == []
        assert wrong.status["last_status"] == "ServerFingerprintMismatch"
    finally:
        wrong.async_stop()


async def test_an_unloadable_ca_stops_the_push(hass, entry, observe, caplog) -> None:
    broken = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
    pusher, _ = await _pusher(hass, entry, observe.url, **{CONF_OBSERVE_CA_PEM: broken})
    try:
        assert pusher.status["active"] is False
        assert "could not load the configured CA" in caplog.text
        assert observe.requests == []
    finally:
        pusher.async_stop()


# --------------------------------------------------------------------------- trust validation


def test_validate_ca_pem(tmp_path) -> None:
    pem = _certificate(tmp_path, "v")[0]
    assert op.validate_ca_pem("") == (None, None)
    assert op.validate_ca_pem(None) == (None, None)
    ok, error = op.validate_ca_pem("  # my CA\n" + pem.replace("\n", "\r\n") + "\n")
    assert error is None and ok == pem  # re-wrapped to the canonical form, comment dropped
    assert op.validate_ca_pem(pem + pem)[0] == pem + pem
    assert op.validate_ca_pem("not a certificate") == (None, op.ERROR_INVALID_CA)
    with_key = pem + "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----"
    assert op.validate_ca_pem(with_key) == (None, op.ERROR_INVALID_CA)
    assert op.validate_ca_pem(pem * (op.MAX_CA_CERTIFICATES + 1)) == (None, op.ERROR_INVALID_CA)
    assert op.validate_ca_pem("x" * (op.MAX_CA_PEM_LENGTH + 1)) == (None, op.ERROR_INVALID_CA)
    assert op.validate_ca_pem(5) == (None, None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", (None, None)),
        (None, (None, None)),
        ("AB" * 32, ("ab" * 32, None)),
        (":".join(["AB"] * 32), ("ab" * 32, None)),
        ("sha256:" + "cd" * 32, ("cd" * 32, None)),
        ("ab" * 31, (None, op.ERROR_INVALID_FINGERPRINT)),
        ("zz" * 32, (None, op.ERROR_INVALID_FINGERPRINT)),
    ],
)
def test_validate_fingerprint(raw, expected) -> None:
    assert op.validate_fingerprint(raw) == expected


def test_validate_options_refuses_both_ways_of_trusting(tmp_path) -> None:
    pem = _certificate(tmp_path, "v")[0]
    base = {
        CONF_OBSERVE_ENABLED: True,
        CONF_OBSERVE_URL: "https://observe.example.com",
        CONF_OBSERVE_HOST_NAME: HOST,
        CONF_OBSERVE_INGEST_KEY: KEY,
    }
    errors, changes, _ = op.validate_options({**base, CONF_OBSERVE_CA_PEM: pem}, key_already_set=False)
    assert errors == {} and changes[CONF_OBSERVE_CA_PEM] == pem
    assert changes[CONF_OBSERVE_FINGERPRINT] is None
    both = {**base, CONF_OBSERVE_CA_PEM: pem, CONF_OBSERVE_FINGERPRINT: "ab" * 32}
    errors, _, _ = op.validate_options(both, key_already_set=False)
    assert errors == {CONF_OBSERVE_FINGERPRINT: op.ERROR_TRUST_CONFLICT}
    errors, _, _ = op.validate_options({**base, CONF_OBSERVE_CA_PEM: "junk"}, key_already_set=False)
    assert errors == {CONF_OBSERVE_CA_PEM: op.ERROR_INVALID_CA}


async def test_options_flow_stores_the_ca_and_audits_only_that_it_is_set(hass, entry, tmp_path) -> None:
    pem = _certificate(tmp_path, "flow")[0]
    runtime = entry.runtime_data
    form = {
        CONF_OBSERVE_ENABLED: True,
        CONF_OBSERVE_URL: "https://observe.example.com",
        CONF_OBSERVE_INGEST_KEY: KEY,
        CONF_OBSERVE_HOST_NAME: HOST,
        CONF_OBSERVE_INTERVAL: 60,
    }
    broken = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"
    with patch.object(hass.config_entries, "async_schedule_reload"), patch.object(
        runtime.audit, "async_log"
    ) as audit_log:
        result = await _open(hass, entry)
        for bad_input in ("junk", broken):  # not PEM at all, and PEM the TLS library refuses
            bad = await hass.config_entries.options.async_configure(
                result["flow_id"], {**form, CONF_OBSERVE_CA_PEM: bad_input}
            )
            assert bad["errors"] == {CONF_OBSERVE_CA_PEM: "invalid_ca"}
        done = await hass.config_entries.options.async_configure(
            result["flow_id"], {**form, CONF_OBSERVE_CA_PEM: pem}
        )
    assert done["type"] == "create_entry"
    assert runtime.store.settings[CONF_OBSERVE_CA_PEM] == pem
    detail = audit_log.call_args.kwargs["detail"]
    assert detail["changes"][CONF_OBSERVE_CA_PEM] == "set"
    assert "BEGIN CERTIFICATE" not in json.dumps(detail)


# --------------------------------------------------------------------------- review findings


def _big_metrics(ts: float, series: int = 420) -> dict[str, Any]:
    """One snapshot's metrics for a large install: ``series`` gauge series."""
    points = [
        {
            "attributes": [{"key": "container", "value": {"stringValue": f"c{n}"}}],
            "timeUnixNano": str(int(ts * 10**9)),
            "asDouble": float(n),
        }
        for n in range(series)
    ]
    metric = {"name": "container.cpu.utilization", "unit": "1", "gauge": {"dataPoints": points}}
    return {
        "resourceMetrics": [
            {
                "resource": {"attributes": []},
                "scopeMetrics": [{"scope": {"name": "ha_soc"}, "metrics": [metric]}],
            }
        ]
    }


def _point_total(request: dict[str, Any]) -> int:
    return sum(
        len(m["gauge"]["dataPoints"])
        for rm in request["resourceMetrics"]
        for sm in rm["scopeMetrics"]
        for m in sm["metrics"]
    )


def test_a_merge_of_a_large_install_is_split_inside_observes_limits() -> None:
    """About 420 series for 59 minutes is 12 buckets and 5,040 points: more than one request."""
    requests = [_big_metrics(1_790_000_000 + 60 * i) for i in range(59)]
    one = op.compact_metrics(requests, 300)
    assert _point_total(one) > op.otlp_mapper.MAX_POINTS  # the unsplit merge would be refused

    parts = op.compact_metrics_requests(requests, 300)
    assert len(parts) >= 2
    assert sum(_point_total(r) for r in parts) == _point_total(one)  # nothing lost by splitting
    for part in parts:
        assert _point_total(part) <= op.otlp_mapper.MAX_POINTS
        assert len(json.dumps(part, separators=(",", ":"))) <= 1024 * 1024


def test_a_merge_over_the_plain_size_cap_is_halved() -> None:
    requests = [_big_metrics(1_790_000_000 + 60 * i, 50) for i in range(10)]
    with patch.object(op, "MAX_MERGED_PLAIN_BYTES", 8000):
        parts = op.compact_metrics_requests(requests, 300)
    assert len(parts) > 1
    assert all(len(json.dumps(p, separators=(",", ":"))) <= 8000 for p in parts)
    assert sum(_point_total(p) for p in parts) == _point_total(op.compact_metrics(requests, 300))


async def test_a_two_hour_outage_on_a_large_install_sends_only_valid_requests(
    hass, entry, observe
) -> None:
    wall = {"now": 1_790_000_000.0}
    observe.script = [OUTAGE] * 400
    with patch.object(
        op.otlp_mapper,
        "build_metrics",
        lambda identity, snapshot, now, dropped, series: _big_metrics(now),
    ):
        pusher, clock = await _pusher(hass, entry, observe.url, wall=lambda: wall["now"])
        try:
            for _ in range(130):
                wall["now"] += 60
                clock.now += op.BACKOFF_MAX_SECONDS + 1
                await pusher.async_push_once()
            assert pusher.status["dropped_overflow"] == 0
            assert pusher.status["queue_bytes"] <= op.MAX_QUEUE_BYTES
            observe.requests.clear()
            observe.script = []
            clock.now += op.BACKOFF_MAX_SECONDS + 1
            await pusher.async_push_once()
            assert pusher.status["queue_length"] == 0
            metrics = [r["json"] for r in observe.requests if r["path"].endswith("/metrics")]
            assert metrics
            assert all(_point_total(m) <= op.otlp_mapper.MAX_POINTS for m in metrics)
            assert pusher.status["dropped_rejected"] == 0
            stamps = {
                int(p["timeUnixNano"]) // 10**9
                for m in metrics
                for rm in m["resourceMetrics"]
                for sm in rm["scopeMetrics"]
                for mt in sm["metrics"]
                for p in mt["gauge"]["dataPoints"]
            }
            assert max(stamps) - min(stamps) >= 2 * 3600
        finally:
            pusher.async_stop()


async def test_a_flood_of_log_payloads_drops_logs_before_the_merged_metrics(
    hass, entry, observe
) -> None:
    counter = {"n": 0}

    async def collect() -> dict[str, Any]:
        counter["n"] += 1
        snapshot = _snapshot()
        snapshot["crash_bundles"] = [_crash(counter["n"])]
        return snapshot

    wall = {"now": 1_790_000_000.0}
    observe.script = [HELD]
    with patch.object(op, "MAX_QUEUE", 6):
        pusher, _ = await _pusher(
            hass, entry, observe.url, collect=collect, wall=lambda: wall["now"]
        )
        try:
            for _ in range(40):
                wall["now"] += 60
                await pusher.async_push_once()
            assert pusher.status["dropped_overflow"] > 0
            assert any(p.compacted for p in pusher._queue)  # the merged outage history is kept
        finally:
            pusher.async_stop()


async def test_sent_keys_forget_the_oldest_first(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        pusher._sent_log_keys = {}
        with patch.object(op, "SENT_KEYS_LIMIT", 3):
            for n in range(5):
                pusher._note_log_keys(
                    op._Payload("logs", b"", f"i{n}", dedup_keys=frozenset({f"k{n}"}))
                )
        assert list(pusher._sent_log_keys) == ["k2", "k3", "k4"]  # not a reset to the last one
    finally:
        pusher.async_stop()


async def test_changing_the_trust_asks_for_the_ingest_key_again(hass, entry, tmp_path) -> None:
    pem = _certificate(tmp_path, "trust")[0]
    runtime = entry.runtime_data
    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)
    runtime.store.async_update_settings(**{CONF_OBSERVE_URL: "https://observe.example.com"})
    form = {
        CONF_OBSERVE_ENABLED: True,
        CONF_OBSERVE_URL: "https://observe.example.com",
        CONF_OBSERVE_HOST_NAME: HOST,
        CONF_OBSERVE_INTERVAL: 60,
    }
    for trust in ({CONF_OBSERVE_CA_PEM: pem}, {CONF_OBSERVE_FINGERPRINT: "ab" * 32}):
        result = await _open(hass, entry)
        refused = await hass.config_entries.options.async_configure(
            result["flow_id"], {**form, **trust}
        )
        assert refused["errors"] == {CONF_OBSERVE_INGEST_KEY: "key_required_for_trust_change"}
        with patch.object(hass.config_entries, "async_schedule_reload"):
            done = await hass.config_entries.options.async_configure(
                result["flow_id"], {**form, **trust, CONF_OBSERVE_INGEST_KEY: KEY}
            )
            assert done["type"] == "create_entry"
            # Saving the same trust again, or removing it, needs no key.
            result = await _open(hass, entry)
            again = await hass.config_entries.options.async_configure(
                result["flow_id"], {**form, **trust}
            )
            assert again["type"] == "create_entry"
            result = await _open(hass, entry)
            cleared = await hass.config_entries.options.async_configure(result["flow_id"], form)
            assert cleared["type"] == "create_entry"


async def test_a_store_saved_before_the_trust_settings_still_starts(hass, entry, observe) -> None:
    await _enable(entry, observe.url)
    settings = entry.runtime_data.store.settings
    settings.pop(CONF_OBSERVE_CA_PEM, None)
    settings.pop(CONF_OBSERVE_FINGERPRINT, None)
    await entry.runtime_data.store.async_save_now()
    await _reload(hass, entry)
    pusher = entry.runtime_data.observe
    assert pusher.status["active"] is True
    assert pusher.status["sent_ok"] >= 1
    result = await _open(hass, entry)
    assert result["type"] == "form"


async def test_disabling_the_entry_forgets_the_queue(hass, entry, observe) -> None:
    from homeassistant.config_entries import ConfigEntryDisabler

    await _enable(entry, observe.url)
    observe.script = [HELD]
    await _reload(hass, entry)
    assert entry.runtime_data.observe._queue
    await hass.config_entries.async_set_disabled_by(entry.entry_id, ConfigEntryDisabler.USER)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data.get(op.DATA_QUEUE_CARRY, {})
