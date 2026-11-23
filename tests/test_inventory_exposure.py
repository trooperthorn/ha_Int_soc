"""Tests for phase 3 of the network inventory: cleartext service and certificate
expiry findings, from the pure row builders in inventory.py through the health
checks that store them and mirror them to Repairs.
"""
from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
MAC_A = "00:11:22:33:44:55"
IP_A = "192.0.2.10"


def _device(state, device_id, ports, *, verdict="unacknowledged"):
    """A record with the given open ports: {port: {"service": ..., "cert_sha256": ...}}."""
    state["devices"][device_id] = {
        "id": device_id,
        "identity": "mac",
        "macs": [MAC_A],
        "addresses": [{"ip": IP_A, "since": T0.isoformat()}],
        "names": [{"value": "hallway-nas", "source": "unifi", "ts": T0.isoformat()}],
        "verdict": verdict,
        "ports": {
            str(port): {"first_seen": T0.isoformat(), "last_seen": T0.isoformat(), **record}
            for port, record in ports.items()
        },
    }
    return state["devices"][device_id]


def _cert(state, name, expires: datetime, **extra):
    state["certs"][name] = {"sha256": name, "not_after": expires.isoformat(), "unreadable": False, **extra}
    return name


# --------------------------------------------------------------------------
# Row builders
# --------------------------------------------------------------------------


def test_cleartext_services_are_found_by_banner_and_by_port():
    state = inv.empty_state()
    _device(state, "d_1", {2323: {"service": "telnet"}, 23: {"service": None}, 21: {"service": "ftp"}})
    rows = {(r["port"], r["service"], r["basis"], r["severity"]) for r in inv.cleartext_exposures(state)}
    assert rows == {
        (2323, "telnet", "banner", "high"),
        (23, "telnet", "port", "high"),
        (21, "ftp", "banner", "medium"),
    }


def test_a_different_service_on_a_cleartext_port_is_not_reported():
    state = inv.empty_state()
    _device(state, "d_1", {23: {"service": "ssh"}, 5900: {"service": None, "cert_sha256": "a" * 64}})
    assert inv.cleartext_exposures(state) == []


def test_closed_ports_and_ignored_devices_are_left_out():
    state = inv.empty_state()
    _device(state, "d_1", {23: {"service": None, "closed_at": T0.isoformat()}})
    _device(state, "d_2", {23: {"service": None}}, verdict="ignored")
    assert inv.cleartext_exposures(state) == []


def test_http_is_reported_only_beside_https():
    state = inv.empty_state()
    _device(state, "d_1", {80: {"service": None}})
    _device(state, "d_2", {80: {"service": None}, 443: {"service": "tls"}})
    rows = inv.cleartext_exposures(state)
    assert [(r["device_id"], r["port"], r["service"], r["severity"]) for r in rows] == [
        ("d_2", 80, "http", "info")
    ]


@pytest.mark.parametrize(
    ("days", "severity"),
    [(-1, "medium"), (0, "medium"), (3, "low"), (14, "low"), (15, "info"), (30, "info"), (31, None)],
)
def test_certificate_expiry_bands(days, severity):
    state = inv.empty_state()
    fingerprint = _cert(state, "c1", T0 + timedelta(days=days, hours=1 if days > 0 else 0))
    _device(state, "d_1", {443: {"service": "tls", "cert_sha256": fingerprint}})
    rows = inv.certificate_expiries(state, T0)
    assert [r["severity"] for r in rows] == ([severity] if severity else [])
    if rows:
        assert rows[0]["expired"] is (days <= 0)


def test_unreadable_unknown_and_closed_certificates_are_left_out():
    state = inv.empty_state()
    state["certs"]["bad"] = {"sha256": "bad", "not_after": None, "unreadable": True}
    expired = _cert(state, "old", T0 - timedelta(days=5))
    _device(state, "d_1", {443: {"cert_sha256": "bad"}, 8443: {"cert_sha256": "never-delivered"}})
    _device(state, "d_2", {443: {"cert_sha256": expired, "closed_at": T0.isoformat()}})
    _device(state, "d_3", {443: {"cert_sha256": expired}}, verdict="ignored")
    assert inv.certificate_expiries(state, T0) == []


# --------------------------------------------------------------------------
# Health checks
# --------------------------------------------------------------------------


class _Inventory:
    def __init__(self):
        self.state = inv.empty_state()


@pytest.fixture
async def health(hass: HomeAssistant) -> IntegrationHealth:
    store = HaSocData(hass)
    await store.async_load()
    health = IntegrationHealth(hass, store)
    health.inventory = _Inventory()
    return health


async def test_checks_do_nothing_without_an_inventory(hass: HomeAssistant, health) -> None:
    health.inventory = None
    assert await health._check_network_cleartext_service() == []
    assert await health._check_network_cert_expiry() == []


async def test_telnet_finding_names_the_device_by_id_only_and_reaches_repairs(
    hass: HomeAssistant, health
) -> None:
    _device(health.inventory.state, "d_1", {23: {"service": None}})
    findings = await health._check_network_cleartext_service()

    assert [f["id"] for f in findings] == ["misconfig:network_cleartext_service:d_1:23"]
    finding = findings[0]
    assert finding["severity"] == "high"
    assert finding["detail"] == {"device_id": "d_1", "port": 23, "service": "telnet", "basis": "port"}
    assert "guess from the port number" in finding["summary"]
    flat = repr(finding)
    assert MAC_A not in flat and IP_A not in flat and "hallway-nas" not in flat
    assert ir.async_get(hass).async_get_issue(DOMAIN, finding["id"]) is not None


async def test_finding_resolves_when_the_port_closes(hass: HomeAssistant, health) -> None:
    device = _device(health.inventory.state, "d_1", {23: {"service": None}})
    await health._check_network_cleartext_service()
    device["ports"]["23"]["closed_at"] = T0.isoformat()
    assert await health._check_network_cleartext_service() == []

    stored = health._store.data["misconfig_findings"]["misconfig:network_cleartext_service:d_1:23"]
    assert stored["status"] == "resolved"
    assert ir.async_get(hass).async_get_issue(DOMAIN, stored["id"]) is None


async def test_http_beside_https_is_one_informational_row_without_a_repair(
    hass: HomeAssistant, health
) -> None:
    for device_id in ("d_1", "d_2"):
        _device(health.inventory.state, device_id, {80: {"service": None}, 443: {"service": "tls"}})
    findings = await health._check_network_cleartext_service()
    assert [(f["id"], f["severity"]) for f in findings] == [
        ("misconfig:network_cleartext_service:http", "info")
    ]
    assert findings[0]["detail"] == {"device_ids": ["d_1", "d_2"], "total_count": 2}
    assert ir.async_get(hass).async_get_issue(DOMAIN, findings[0]["id"]) is None


async def test_cleartext_findings_are_capped(hass: HomeAssistant, health, monkeypatch) -> None:
    monkeypatch.setattr("custom_components.ha_soc.health.NETWORK_FINDINGS_CAP", 3)
    for index in range(5):
        _device(health.inventory.state, f"d_{index}", {23: {"service": None}})
    assert len(await health._check_network_cleartext_service()) == 3


async def test_expired_certificate_is_a_medium_finding_without_the_subject(
    hass: HomeAssistant, health
) -> None:
    state = health.inventory.state
    now = datetime.now(timezone.utc)
    fingerprint = _cert(state, "c1", now - timedelta(days=2), subject="CN=hallway-nas.example")
    _device(state, "d_1", {443: {"service": "tls", "cert_sha256": fingerprint}})
    findings = await health._check_network_cert_expiry()

    assert [f["id"] for f in findings] == ["misconfig:network_cert_expiry:d_1:443"]
    finding = findings[0]
    assert finding["severity"] == "medium"
    assert finding["title"] == "Certificate expired on network device d_1"
    assert set(finding["detail"]) == {"device_id", "port", "not_after", "days_left"}
    assert "hallway-nas" not in repr(finding)


async def test_certificate_near_expiry_is_low_and_far_from_expiry_is_nothing(
    hass: HomeAssistant, health
) -> None:
    state = health.inventory.state
    now = datetime.now(timezone.utc)
    soon = _cert(state, "soon", now + timedelta(days=7, hours=1))
    later = _cert(state, "later", now + timedelta(days=200))
    _device(state, "d_1", {443: {"cert_sha256": soon}, 8443: {"cert_sha256": later}})
    findings = await health._check_network_cert_expiry()
    assert [(f["detail"]["port"], f["severity"]) for f in findings] == [(443, "low")]
    assert "in 7 day(s)" in findings[0]["summary"]
