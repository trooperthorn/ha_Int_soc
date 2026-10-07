"""The Observe push: options validation, delivery rules against a fake Observe, redaction.

The fake server is a real aiohttp server on loopback (aiohttp.test_utils), so the push goes
through Home Assistant's shared client session exactly as in production. Time is injected
(a list-backed clock), so back-off and Retry-After are checked without sleeping.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import homeassistant.helpers.issue_registry as ir
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import observe_push as op
from custom_components.ha_soc.const import (
    CONF_OBSERVE_ENABLED,
    CONF_OBSERVE_HOST_NAME,
    CONF_OBSERVE_INGEST_KEY,
    CONF_OBSERVE_INTERVAL,
    CONF_OBSERVE_URL,
    DOMAIN,
    REDACTED_PLACEHOLDER,
)
from custom_components.ha_soc.diagnostics import async_get_config_entry_diagnostics

FIXTURES = Path(__file__).parent / "fixtures" / "observe_otlp"
KEY = "wpi_0123456789ab_" + "S3cretS3cretS3cretS3cretS3cretS3cretS3cret0"
HOST = "haos-lab"


# --------------------------------------------------------------------------- helpers


class FakeObserve:
    """Scripted Observe. Each request pops the next scripted reply, then falls back to 200."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.script: list[Any] = []
        self.server: TestServer | None = None

    async def _handle(self, request: web.Request) -> web.Response:
        # aiohttp's server inflates a Content-Encoding: gzip body before handing it over.
        body = await request.read()
        self.requests.append(
            {
                "path": request.path,
                "headers": dict(request.headers),
                "json": json.loads(body),
            }
        )
        reply = self.script.pop(0) if self.script else (200, {}, "")
        status, headers, text = reply
        return web.Response(status=status, headers=headers, text=text)

    async def start(self) -> str:
        app = web.Application()
        app.router.add_post("/v1/metrics", self._handle)
        app.router.add_post("/v1/logs", self._handle)
        self.server = TestServer(app)
        await self.server.start_server()
        return f"http://127.0.0.1:{self.server.port}"

    async def close(self) -> None:
        if self.server is not None:
            await self.server.close()


@pytest.fixture
async def observe(socket_enabled):
    fake = FakeObserve()
    fake.url = await fake.start()
    yield fake
    await fake.close()


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _own_log(caplog) -> str:
    """The messages HA SOC itself logged; the test harness separately logs storage writes."""
    return "\n".join(
        r.getMessage() for r in caplog.records if r.name.startswith("custom_components.ha_soc")
    )


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _snapshot() -> dict[str, Any]:
    return json.loads((FIXTURES / "snapshot.json").read_text(encoding="utf-8"))["snapshot"]


async def _pusher(hass, entry, url: str, clock: Clock | None = None, **settings):
    """A pusher with the fixture snapshot, started the way setup starts it."""
    runtime = entry.runtime_data
    runtime.store.async_update_settings(
        **{
            CONF_OBSERVE_ENABLED: True,
            CONF_OBSERVE_URL: url,
            CONF_OBSERVE_HOST_NAME: HOST,
            CONF_OBSERVE_INTERVAL: 60,
            **settings,
        }
    )
    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)

    async def collect() -> dict[str, Any]:
        return _snapshot()

    clock = clock or Clock()
    pusher = op.ObservePusher(
        hass, runtime.store, runtime.secrets, collect, wall=lambda: 1_790_000_000.0, clock=clock
    )
    await pusher.async_start(entry)
    await hass.async_block_till_done()  # the initial push
    return pusher, clock


# --------------------------------------------------------------------------- validation


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("https://observe.example.com", True),
        ("https://observe.example.com:8443/base/", True),
        ("http://192.168.1.20:8080", True),
        ("http://10.0.0.5", True),
        ("http://172.16.4.4", True),
        ("http://127.0.0.1:9", True),
        ("http://localhost:8000", True),
        ("http://[fd00::1]:8000", True),
        ("http://[fc00::1]", True),
        ("http://[::1]:8000", True),
        ("http://[::ffff:192.168.1.5]", True),
        ("http://169.254.10.10", True),
        ("http://[2002:0808:0808::1]", False),
        ("http://[2002:c0a8:0101::1]", False),
        ("http://[::ffff:8.8.8.8]", False),
        ("http://[2001:db8::1]", False),
        ("http://0.0.0.0", False),
        ("http://0.0.0.0:8000", False),
        ("http://240.0.0.1", False),
        ("http://255.255.255.255", False),
        ("http://100.64.0.1", False),
        ("http://224.0.0.1", False),
        ("http://[::]", False),
        ("http://observe.example.com", False),
        ("http://8.8.8.8", False),
        ("http://192.168.1.20.example.com", False),
        ("http://observe.local", False),
        ("ftp://192.168.1.20", False),
        ("observe.example.com", False),
        ("https://user:pw@observe.example.com", False),
        ("https://observe.example.com/?key=1", False),
        ("https://observe.example.com/#x", False),
        ("https://observe.example.com:99999", False),
        ("", False),
        (None, False),
    ],
)
def test_validate_url(url, ok) -> None:
    normalised, error = op.validate_url(url)
    assert (error is None) is ok
    assert (normalised is not None) is ok


def test_validate_url_distinguishes_insecure_from_malformed() -> None:
    assert op.validate_url("http://observe.example.com")[1] == op.ERROR_INSECURE_URL
    assert op.validate_url("nonsense")[1] == op.ERROR_INVALID_URL
    assert op.validate_url("https://observe.example.com/")[0] == "https://observe.example.com"


def test_validate_key_and_host_name() -> None:
    assert op.validate_ingest_key(KEY) == KEY
    assert op.validate_ingest_key("wpf_abc") is None
    assert op.validate_ingest_key("wpi_has space") is None
    assert op.validate_ingest_key("wpi_" + "x" * 300) is None
    assert op.validate_host_name(" haos-lab ") == "haos-lab"
    assert op.validate_host_name("bad name") is None
    assert op.validate_host_name("") is None
    assert op.validate_host_name("h" * 300) is None


def test_validate_options_requires_fields_only_when_enabled() -> None:
    errors, changes, key = op.validate_options({}, key_already_set=False)
    assert errors == {}
    assert changes[CONF_OBSERVE_ENABLED] is False
    assert key is None

    errors, _, _ = op.validate_options({CONF_OBSERVE_ENABLED: True}, key_already_set=False)
    assert set(errors) == {CONF_OBSERVE_URL, CONF_OBSERVE_HOST_NAME, CONF_OBSERVE_INGEST_KEY}

    # A filled-in field must be valid even while disabled.
    errors, _, _ = op.validate_options(
        {CONF_OBSERVE_URL: "http://example.com"}, key_already_set=False
    )
    assert errors == {CONF_OBSERVE_URL: op.ERROR_INSECURE_URL}

    errors, _, _ = op.validate_options({CONF_OBSERVE_INTERVAL: 29}, key_already_set=False)
    assert errors == {CONF_OBSERVE_INTERVAL: op.ERROR_INVALID_INTERVAL}
    errors, _, _ = op.validate_options({CONF_OBSERVE_INTERVAL: 3601}, key_already_set=False)
    assert errors == {CONF_OBSERVE_INTERVAL: op.ERROR_INVALID_INTERVAL}
    errors, changes, _ = op.validate_options({CONF_OBSERVE_INTERVAL: 30.0}, key_already_set=False)
    assert errors == {} and changes[CONF_OBSERVE_INTERVAL] == 30


def test_validate_options_keeps_stored_key_when_blank() -> None:
    errors, _, key = op.validate_options(
        {
            CONF_OBSERVE_ENABLED: True,
            CONF_OBSERVE_URL: "https://observe.example.com",
            CONF_OBSERVE_HOST_NAME: HOST,
        },
        key_already_set=True,
    )
    assert errors == {} and key is None


# --------------------------------------------------------------------------- options flow


async def _open(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    return result


async def test_options_flow_saves_settings_and_key_privately(hass, entry) -> None:
    result = await _open(hass, entry)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload_:
        done = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "http://192.168.1.20:8080/",
                CONF_OBSERVE_INGEST_KEY: KEY,
                CONF_OBSERVE_HOST_NAME: HOST,
                CONF_OBSERVE_INTERVAL: 45,
            },
        )
    assert done["type"] == "create_entry"
    reload_.assert_called_once_with(entry.entry_id)

    runtime = entry.runtime_data
    settings = runtime.store.settings
    assert settings[CONF_OBSERVE_ENABLED] is True
    assert settings[CONF_OBSERVE_URL] == "http://192.168.1.20:8080"
    assert settings[CONF_OBSERVE_HOST_NAME] == HOST
    assert settings[CONF_OBSERVE_INTERVAL] == 45
    assert await runtime.secrets.async_get(CONF_OBSERVE_INGEST_KEY) == KEY
    # The key is in neither the settings, the config entry nor the world-readable options.
    assert CONF_OBSERVE_INGEST_KEY not in settings
    assert entry.options == {} and KEY not in json.dumps(dict(entry.data))


async def test_options_flow_rejects_bad_input_and_saves_nothing(hass, entry) -> None:
    result = await _open(hass, entry)
    with patch.object(hass.config_entries, "async_schedule_reload") as reload_:
        again = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "http://observe.example.com",
                CONF_OBSERVE_INGEST_KEY: "not-a-key",
                CONF_OBSERVE_HOST_NAME: "bad host",
            },
        )
    assert again["type"] == "form"
    assert again["errors"] == {
        CONF_OBSERVE_URL: "insecure_url",
        CONF_OBSERVE_INGEST_KEY: "invalid_key",
        CONF_OBSERVE_HOST_NAME: "invalid_host_name",
    }
    reload_.assert_not_called()
    runtime = entry.runtime_data
    assert runtime.store.settings[CONF_OBSERVE_ENABLED] is False
    assert await runtime.secrets.async_get(CONF_OBSERVE_INGEST_KEY) is None


async def test_options_flow_blank_key_keeps_and_clear_removes(hass, entry) -> None:
    runtime = entry.runtime_data
    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)
    base = {
        CONF_OBSERVE_ENABLED: True,
        CONF_OBSERVE_URL: "https://observe.example.com",
        CONF_OBSERVE_HOST_NAME: HOST,
    }
    with patch.object(hass.config_entries, "async_schedule_reload"):
        result = await _open(hass, entry)
        done = await hass.config_entries.options.async_configure(result["flow_id"], dict(base))
        assert done["type"] == "create_entry"
        assert await runtime.secrets.async_get(CONF_OBSERVE_INGEST_KEY) == KEY

        # Clearing the key while the push stays enabled leaves nothing to send with.
        result = await _open(hass, entry)
        bad = await hass.config_entries.options.async_configure(
            result["flow_id"], {**base, "observe_clear_key": True}
        )
        assert bad["errors"] == {CONF_OBSERVE_INGEST_KEY: "key_required"}

        done = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {**base, CONF_OBSERVE_ENABLED: False, "observe_clear_key": True},
        )
    assert done["type"] == "create_entry"
    assert await runtime.secrets.async_get(CONF_OBSERVE_INGEST_KEY) is None


async def test_options_flow_audit_entry_never_holds_the_key(hass, entry) -> None:
    runtime = entry.runtime_data
    with patch.object(hass.config_entries, "async_schedule_reload"), patch.object(
        runtime.audit, "async_log"
    ) as audit_log:
        result = await _open(hass, entry)
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_OBSERVE_ENABLED: True,
                CONF_OBSERVE_URL: "https://observe.example.com",
                CONF_OBSERVE_INGEST_KEY: KEY,
                CONF_OBSERVE_HOST_NAME: HOST,
            },
        )
    detail = audit_log.call_args.kwargs["detail"]
    assert KEY not in json.dumps(detail)
    assert detail["changes"][CONF_OBSERVE_INGEST_KEY] == REDACTED_PLACEHOLDER


async def test_options_flow_aborts_when_not_loaded(hass) -> None:
    unloaded = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    unloaded.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(unloaded.entry_id)
    assert result["type"] == "abort" and result["reason"] == "not_loaded"


# --------------------------------------------------------------------------- off by default


async def test_disabled_by_default_sends_nothing(hass, entry) -> None:
    runtime = entry.runtime_data
    assert runtime.store.settings[CONF_OBSERVE_ENABLED] is False
    assert runtime.observe.status["active"] is False

    with patch.object(op, "async_get_clientsession", side_effect=AssertionError("no session")):
        await runtime.observe.async_push_once()
        await runtime.observe.async_start(entry)
        await runtime.observe.async_push_once()
    assert runtime.observe.status["sent_ok"] == 0
    assert runtime.observe.status["queue_length"] == 0


async def test_enabled_but_incomplete_sends_nothing(hass, entry, observe, caplog) -> None:
    runtime = entry.runtime_data
    runtime.store.async_update_settings(
        **{CONF_OBSERVE_ENABLED: True, CONF_OBSERVE_URL: observe.url}
    )
    pusher = op.ObservePusher(hass, runtime.store, runtime.secrets, lambda: None)
    await pusher.async_start(entry)
    await pusher.async_push_once()
    assert pusher.status["active"] is False
    assert observe.requests == []
    assert "incomplete or invalid" in caplog.text


# --------------------------------------------------------------------------- delivery


async def test_push_sends_metrics_then_logs_with_auth_and_idempotency(
    hass, entry, observe
) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        assert [r["path"] for r in observe.requests] == ["/v1/metrics", "/v1/logs"]
        for request in observe.requests:
            headers = request["headers"]
            assert headers["Authorization"] == f"Bearer {KEY}"
            assert headers["Content-Encoding"] == "gzip"
            assert headers["Content-Type"] == "application/json"
        keys = [r["headers"]["Idempotency-Key"] for r in observe.requests]
        assert len(set(keys)) == 2 and all(0 < len(k) <= 128 and k.isascii() for k in keys)

        metrics = observe.requests[0]["json"]["resourceMetrics"][0]
        attrs = {a["key"]: a["value"]["stringValue"] for a in metrics["resource"]["attributes"]}
        assert attrs["host.name"] == HOST
        assert metrics["scopeMetrics"]
        assert observe.requests[1]["json"]["resourceLogs"][0]["scopeLogs"]
        assert pusher.status["sent_ok"] == 2 and pusher.status["last_status"] == 200

        # Logs already accepted are not sent again; the metrics always go.
        observe.requests.clear()
        await pusher.async_push_once()
        assert [r["path"] for r in observe.requests] == ["/v1/metrics"]
    finally:
        pusher.async_stop()


async def test_partial_success_is_counted_and_logged(hass, entry, observe, caplog) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        body = json.dumps(
            {"partialSuccess": {"rejectedDataPoints": "3", "errorMessage": f"bad point {KEY}"}}
        )
        observe.script = [(200, {"Content-Type": "application/json"}, body)]
        observe.requests.clear()
        with caplog.at_level(logging.WARNING):
            await pusher.async_push_once()
        assert pusher.status["rejected_items"] == 3
        # Accepted overall: the payload is not retried and the push carries on.
        assert pusher.status["queue_length"] == 0
        assert "rejected 3 item(s)" in caplog.text
        assert REDACTED_PLACEHOLDER in _own_log(caplog)  # the key echoed by the server is masked
        assert KEY not in _own_log(caplog)
    finally:
        pusher.async_stop()


async def test_401_raises_repairs_issue_drops_payload_and_success_clears_it(
    hass, entry, observe
) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        registry = ir.async_get(hass)
        observe.script = [(401, {}, "")]
        await pusher.async_push_once()
        assert registry.async_get_issue(DOMAIN, "observe_key_rejected") is not None
        assert pusher.status["auth_rejected"] is True
        assert pusher.status["dropped_rejected"] == 1

        # A rejected key is not hammered: nothing goes out until the back-off passes.
        observe.requests.clear()
        await pusher.async_push_once()
        assert observe.requests == []

        clock.now += op.AUTH_BACKOFF_SECONDS + 1
        await pusher.async_push_once()
        assert observe.requests  # probed again with fresh payloads, accepted
        assert registry.async_get_issue(DOMAIN, "observe_key_rejected") is None
        assert pusher.status["auth_rejected"] is False
    finally:
        pusher.async_stop()


async def test_403_is_treated_as_a_rejected_key(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(403, {}, "")]
        await pusher.async_push_once()
        assert ir.async_get(hass).async_get_issue(DOMAIN, "observe_key_rejected") is not None
    finally:
        pusher.async_stop()


async def test_disabling_removes_the_repairs_issue(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(401, {}, "")]
        await pusher.async_push_once()
        entry.runtime_data.store.async_update_settings(**{CONF_OBSERVE_ENABLED: False})
        await pusher.async_start(entry)
        assert ir.async_get(hass).async_get_issue(DOMAIN, "observe_key_rejected") is None
        assert pusher.status["active"] is False
    finally:
        pusher.async_stop()


async def test_413_drops_the_payload_without_retrying(hass, entry, observe, caplog) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.requests.clear()
        observe.script = [(413, {}, "")]
        with caplog.at_level(logging.WARNING):
            await pusher.async_push_once()
        # The oversized metrics payload is gone; the logs payload behind it still went.
        assert pusher.status["dropped_rejected"] == 1
        assert pusher.status["queue_length"] == 0
        assert "payload too large" in caplog.text
        assert ir.async_get(hass).async_get_issue(DOMAIN, "observe_key_rejected") is None
    finally:
        pusher.async_stop()


async def test_persistent_404_backs_off_raises_one_issue_and_clears_on_success(
    hass, entry, observe
) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        registry = ir.async_get(hass)
        observe.requests.clear()
        observe.script = [(404, {}, "")] * 500
        for _ in range(60):
            await pusher.async_push_once()
        # Bounded: three rejections reach the threshold, then the clock-based back-off holds.
        assert len(observe.requests) == op.REJECT_THRESHOLD
        assert pusher.status["queue_length"] <= op.MAX_QUEUE
        issues = [i for i in registry.issues.values() if i.domain == DOMAIN]
        rejected = [i for i in issues if i.issue_id == "observe_rejected"]
        assert len(rejected) == 1
        assert rejected[0].translation_placeholders == {"status": "404"}
        assert registry.async_get_issue(DOMAIN, "observe_key_rejected") is None

        # Back-off grows: the next probe is allowed after the base delay, then twice that.
        clock.now += op.BACKOFF_BASE_SECONDS + 1
        await pusher.async_push_once()
        assert len(observe.requests) == op.REJECT_THRESHOLD + 1
        await pusher.async_push_once()
        assert len(observe.requests) == op.REJECT_THRESHOLD + 1

        observe.script = []
        clock.now += op.BACKOFF_MAX_SECONDS + 1
        await pusher.async_push_once()
        assert registry.async_get_issue(DOMAIN, "observe_rejected") is None
        assert pusher.status["rejected_streak"] == 0
        assert pusher.status["queue_length"] == 0
    finally:
        pusher.async_stop()


@pytest.mark.parametrize("status", [400, 409, 413, 415, 422])
async def test_persistent_payload_errors_name_the_status(hass, entry, observe, status) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(status, {}, "")] * 20
        for _ in range(5):
            await pusher.async_push_once()
        issue = ir.async_get(hass).async_get_issue(DOMAIN, "observe_rejected")
        assert issue is not None
        assert issue.translation_placeholders == {"status": str(status)}
    finally:
        pusher.async_stop()


async def test_one_stray_rejection_raises_no_issue(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(422, {}, "")]
        await pusher.async_push_once()
        assert ir.async_get(hass).async_get_issue(DOMAIN, "observe_rejected") is None
    finally:
        pusher.async_stop()


async def test_429_honours_retry_after_and_reuses_the_idempotency_key(
    hass, entry, observe
) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        observe.requests.clear()
        observe.script = [(429, {"Retry-After": "120"}, "")]
        await pusher.async_push_once()
        first = observe.requests[0]["headers"]["Idempotency-Key"]
        assert len(observe.requests) == 1
        assert pusher.status["queue_length"] >= 1

        # Still inside Retry-After: nothing is sent, the queue only grows.
        clock.now += 119
        await pusher.async_push_once()
        assert len(observe.requests) == 1

        clock.now += 2
        await pusher.async_push_once()
        assert observe.requests[1]["headers"]["Idempotency-Key"] == first
        assert observe.requests[1]["json"] == observe.requests[0]["json"]
        assert pusher.status["queue_length"] == 0
    finally:
        pusher.async_stop()


async def test_retry_after_is_capped(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        assert pusher._retry_after("999999") == op.MAX_RETRY_AFTER_SECONDS
        assert pusher._retry_after("0") == 0.0
        assert pusher._retry_after("soon") is None
        assert pusher._retry_after(None) is None
        date = "Wed, 21 Oct 2015 07:28:00 GMT"
        assert pusher._retry_after(date) == 0.0  # in the past
    finally:
        pusher.async_stop()


async def test_5xx_backs_off_exponentially_and_retries_the_same_payload(
    hass, entry, observe
) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        observe.requests.clear()
        observe.script = [(503, {}, ""), (502, {}, "")]
        await pusher.async_push_once()
        assert len(observe.requests) == 1
        key = observe.requests[0]["headers"]["Idempotency-Key"]

        clock.now += op.BACKOFF_BASE_SECONDS - 1
        await pusher.async_push_once()
        assert len(observe.requests) == 1  # still backing off

        clock.now += 2  # first back-off (10 s) has passed; this attempt fails again
        await pusher.async_push_once()
        assert len(observe.requests) == 2
        assert observe.requests[1]["headers"]["Idempotency-Key"] == key

        clock.now += op.BACKOFF_BASE_SECONDS + 1  # second back-off is 20 s, not 10
        await pusher.async_push_once()
        assert len(observe.requests) == 2

        clock.now += op.BACKOFF_BASE_SECONDS  # now past 20 s: recovers
        await pusher.async_push_once()
        assert observe.requests[2]["headers"]["Idempotency-Key"] == key
        assert pusher.status["queue_length"] == 0
    finally:
        pusher.async_stop()


async def test_backoff_is_capped() -> None:
    delays = [min(op.BACKOFF_BASE_SECONDS * 2 ** (n - 1), op.BACKOFF_MAX_SECONDS) for n in range(1, 30)]
    assert max(delays) == op.BACKOFF_MAX_SECONDS


async def test_connection_failure_is_retried_not_dropped(hass, entry, observe, caplog) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        await observe.close()
        observe.server = None
        with caplog.at_level(logging.WARNING):
            await pusher.async_push_once()
        assert pusher.status["queue_length"] == 1
        assert pusher.status["dropped_rejected"] == 0
        assert "will be retried" in _own_log(caplog)
        assert KEY not in _own_log(caplog)
    finally:
        pusher.async_stop()


async def test_redirects_are_not_followed(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.requests.clear()
        observe.script = [(302, {"Location": "http://127.0.0.1:1/elsewhere"}, "")]
        await pusher.async_push_once()
        assert len(observe.requests) == 1  # refused once, dropped, not followed or retried
        assert pusher.status["dropped_rejected"] == 1
    finally:
        pusher.async_stop()


# --------------------------------------------------------------------------- bounded queue


async def test_queue_is_bounded_drops_oldest_and_counts(hass, entry, observe, caplog) -> None:
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(503, {"Retry-After": "3600"}, "")]
        await pusher.async_push_once()
        first_key = pusher._queue[0].idempotency_key
        observe.requests.clear()

        # Observe stays unreachable (Retry-After); every cycle still queues new data.
        with caplog.at_level(logging.WARNING):
            for _ in range(op.MAX_QUEUE + 10):
                await pusher.async_push_once()
        assert observe.requests == []
        status = pusher.status
        assert status["queue_length"] == op.MAX_QUEUE
        assert status["dropped_overflow"] > 0
        assert all(p.idempotency_key != first_key for p in pusher._queue)
        assert "dropped the" in caplog.text and "dropped since start" in caplog.text
        assert str(status["dropped_overflow"]) in caplog.text
    finally:
        pusher.async_stop()


async def test_queue_overflow_keeps_the_newest(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        observe.script = [(503, {"Retry-After": "3600"}, "")]
        await pusher.async_push_once()
        for _ in range(op.MAX_QUEUE + 5):
            await pusher.async_push_once()
        before = [p.idempotency_key for p in pusher._queue]
        await pusher.async_push_once()
        after = [p.idempotency_key for p in pusher._queue]
        added = [k for k in after if k not in before]
        # Oldest out, newest in: the survivors are the tail of everything queued so far.
        assert after == (before + added)[-op.MAX_QUEUE :]
        assert len(added) >= 1
    finally:
        pusher.async_stop()


# --------------------------------------------------------------------------- redaction


async def test_key_never_appears_in_diagnostics_or_status(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        runtime = entry.runtime_data
        runtime.observe = pusher  # diagnostics reports the live pusher's status
        diag = await async_get_config_entry_diagnostics(hass, entry)
        dumped = json.dumps(diag)
        assert KEY not in dumped and "S3cretS3cret" not in dumped
        assert observe.url not in dumped and "127.0.0.1" not in dumped
        assert HOST not in dumped

        settings = diag["settings"]
        assert settings[CONF_OBSERVE_INGEST_KEY] == REDACTED_PLACEHOLDER
        assert settings[f"{CONF_OBSERVE_INGEST_KEY}_set"] is True
        assert settings[CONF_OBSERVE_URL] == REDACTED_PLACEHOLDER
        assert settings[CONF_OBSERVE_HOST_NAME] == REDACTED_PLACEHOLDER
        assert settings[CONF_OBSERVE_ENABLED] is True
        assert diag["observe_push"]["active"] is True
        assert diag["observe_push"]["sent_ok"] >= 2
    finally:
        pusher.async_stop()


async def test_key_is_masked_by_the_settings_api_path(hass, entry) -> None:
    from custom_components.ha_soc.websocket_api import _masked_settings

    runtime = entry.runtime_data
    await runtime.secrets.async_set(CONF_OBSERVE_INGEST_KEY, KEY)
    masked = await _masked_settings(runtime.store.settings, runtime.secrets)
    assert masked[CONF_OBSERVE_INGEST_KEY] == REDACTED_PLACEHOLDER
    assert KEY not in json.dumps(masked)


async def test_pusher_repr_and_config_repr_hide_the_key(hass, entry, observe) -> None:
    pusher, _ = await _pusher(hass, entry, observe.url)
    try:
        assert KEY not in repr(pusher) and KEY not in repr(pusher._config)
    finally:
        pusher.async_stop()


async def test_no_log_line_at_any_level_holds_the_key(hass, entry, observe, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    pusher, clock = await _pusher(hass, entry, observe.url)
    try:
        for reply in ((401, {}, ""), (413, {}, ""), (429, {"Retry-After": "5"}, ""), (503, {}, "")):
            observe.script = [reply]
            clock.now += 10_000
            await pusher.async_push_once()
        assert KEY not in _own_log(caplog)
    finally:
        pusher.async_stop()


async def test_unexpected_cycle_error_is_logged_without_traceback_or_key(
    hass, entry, observe, caplog
) -> None:
    caplog.set_level(logging.DEBUG)
    pusher, _clock = await _pusher(hass, entry, observe.url)
    try:
        async def boom() -> dict[str, Any]:
            raise RuntimeError(f"collector failed for {KEY}")

        pusher._collector = boom
        await pusher.async_push_once()
        records = [r for r in caplog.records if r.name.startswith("custom_components.ha_soc")]
        assert any("cycle failed" in r.getMessage() for r in records)
        assert all(r.exc_info is None for r in records)
        assert KEY not in _own_log(caplog)
    finally:
        pusher.async_stop()


def test_websocket_settings_schema_rejects_observe_keys() -> None:
    from custom_components.ha_soc.websocket_api import ws_settings_set

    for key in (CONF_OBSERVE_URL, CONF_OBSERVE_ENABLED, CONF_OBSERVE_HOST_NAME):
        with pytest.raises(Exception):
            ws_settings_set._ws_schema({"id": 1, "type": "ha_soc/settings/set", key: "http://x"})


# --------------------------------------------------------------------------- collector


async def test_collector_builds_a_snapshot_the_mapper_accepts(hass, entry) -> None:
    from custom_components.ha_soc import otlp_mapper

    runtime = entry.runtime_data
    collector = op.SnapshotCollector(
        hass,
        runtime.store,
        health=runtime.health,
        watchdog=runtime.watchdog,
        crash_forensics=runtime.crash_forensics,
    )
    snapshot = await collector.async_collect()
    assert {"detections", "repairs", "backup_checked", "integration_overview"} <= set(snapshot)
    # Core install in the test harness: no Supervisor, so no container or resolution series.
    assert "containers" not in snapshot and "resolution" not in snapshot
    metrics = otlp_mapper.build_metrics(
        otlp_mapper.Identity(host_name=HOST), snapshot, 1_790_000_000.0
    )
    assert otlp_mapper.has_points(metrics)


async def test_collector_reuses_a_fresh_watchdog_sample(hass, entry) -> None:
    runtime = entry.runtime_data
    clock = Clock()
    sample = {"available": True, "containers": [], "reason": None}
    runtime.watchdog.last_overview = sample
    runtime.watchdog.last_overview_at = clock.now - 10
    collector = op.SnapshotCollector(
        hass,
        runtime.store,
        health=runtime.health,
        watchdog=runtime.watchdog,
        crash_forensics=runtime.crash_forensics,
        clock=clock,
    )
    with patch("custom_components.ha_soc.containers.async_container_resources") as fresh:
        assert (await collector.async_collect())["containers"] is sample
        fresh.assert_not_called()
        clock.now += op.WATCHDOG_SAMPLE_MAX_AGE_SECONDS
        fresh.return_value = {"available": False}
        assert "containers" not in await collector.async_collect()
        fresh.assert_called_once()


async def test_watchdog_off_push_fetches_at_most_once_per_watchdog_interval(hass, entry) -> None:
    """Audit push-polls-supervisor-when-watchdog-off: 100 add-ons, watchdog off."""
    runtime = entry.runtime_data
    clock = Clock()
    runtime.watchdog.last_overview = None
    runtime.watchdog.last_overview_at = None
    runtime.store.data["resource_watchdog"]["interval_seconds"] = 60
    collector = op.SnapshotCollector(
        hass,
        runtime.store,
        health=runtime.health,
        watchdog=runtime.watchdog,
        crash_forensics=runtime.crash_forensics,
        clock=clock,
    )
    sample = {"available": True, "containers": [], "reason": None, "truncated": 0}
    with patch(
        "custom_components.ha_soc.containers.async_container_resources", return_value=sample
    ) as fresh:
        for _ in range(5):
            assert (await collector.async_collect())["containers"] is sample
            clock.now += 10
        assert fresh.call_count == 1
        clock.now += 60
        await collector.async_collect()
        assert fresh.call_count == 2


async def test_watchdog_off_100_add_ons_call_count_is_bounded(hass, entry) -> None:
    runtime = entry.runtime_data
    clock = Clock()
    runtime.watchdog.last_overview = None
    runtime.watchdog.last_overview_at = None
    hass.config.components.add("hassio")
    info = {"addons": [{"slug": f"a{i}", "name": f"A{i}", "state": "started"} for i in range(100)]}
    stat = SimpleNamespace(
        cpu_percent=1.0, memory_usage=1, memory_limit=2, memory_percent=50.0,
        network_rx=1, network_tx=1, blk_read=1, blk_write=1,
    )
    client = MagicMock()
    client.addons.addon_stats = AsyncMock(return_value=stat)
    client.homeassistant.stats = AsyncMock(return_value=stat)
    client.supervisor.stats = AsyncMock(return_value=stat)
    collector = op.SnapshotCollector(
        hass,
        runtime.store,
        health=runtime.health,
        watchdog=runtime.watchdog,
        crash_forensics=runtime.crash_forensics,
        clock=clock,
    )
    with (
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
        patch("homeassistant.components.hassio.get_supervisor_info", return_value=info),
    ):
        for _ in range(3):
            snap = await collector.async_collect()
            clock.now += 10
    assert len(snap["containers"]["containers"]) == 102
    assert client.addons.addon_stats.await_count == 100
    assert client.homeassistant.stats.await_count == 1


async def test_collector_reports_backup_state(hass, entry) -> None:
    runtime = entry.runtime_data
    collector = op.SnapshotCollector(
        hass,
        runtime.store,
        health=runtime.health,
        watchdog=runtime.watchdog,
        crash_forensics=runtime.crash_forensics,
    )
    finding_id = "misconfig:backup_unprotected"
    runtime.store.data["misconfig_findings"][finding_id] = {
        "id": finding_id,
        "check": "backup_unprotected",
        "status": "new",
        "detail": {"password_set": False},
    }
    assert collector._backup()[0]["id"] == finding_id
    runtime.store.data["misconfig_findings"][finding_id]["status"] = "dismissed"
    assert collector._backup()[0] is None
