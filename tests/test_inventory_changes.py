"""Tests for phase 2 of the network inventory: the Probe's certificate read,
certificate delivery and parsing, port and certificate change events, and the
three change detections.

The Probe tests load the Probe's own netscan.py and run its handshake against
a TLS server on loopback, because the defect this phase fixes (an empty
certificate from an unverified handshake) only shows in a real handshake.
"""
import asyncio
import base64
import hashlib
import importlib.util
import ssl
import sys
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from unittest.mock import patch

import pytest
import voluptuous as vol
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.detections import (
    RULE_NETWORK_CERT_CHANGED,
    RULE_NETWORK_IDENTITY_SHIFT,
    RULE_NETWORK_PORT_OPENED,
)
from custom_components.ha_soc.netscan import (
    NETSCAN_HOST_SCHEMA,
    parse_certificate,
    strip_der,
)

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

PROBE_SECRET = "unit-test-probe-secret"
T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
CYCLE = timedelta(minutes=5)
MAC_A = "00:11:22:33:44:55"
IP_A = "192.0.2.10"
PROBE_NETSCAN = (
    Path(__file__).parents[1] / "ha_soc_probe" / "rootfs" / "usr" / "lib" / "ha_soc" / "netscan.py"
)


def _certificate(common_name: str, *, issuer: str | None = None, days_left: int = 365):
    """A throwaway certificate: (DER bytes, PEM certificate, PEM key)."""
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    issuer_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer or common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(T0 - timedelta(days=30))
        .not_valid_after(T0 + timedelta(days=days_left))
        .sign(key, hashes.SHA256())
    )
    der = cert.public_bytes(serialization.Encoding.DER)
    pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return der, pem, key_pem


def _sha(der: bytes) -> str:
    return hashlib.sha256(der).hexdigest()


def _b64(der: bytes) -> str:
    return base64.b64encode(der).decode("ascii")


# --------------------------------------------------------------------------
# The Probe's own scanner
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def probe_netscan():
    pytest.importorskip("fcntl", reason="the Probe scanner is Linux only")
    sys.path.insert(0, str(PROBE_NETSCAN.parent))
    try:
        spec = importlib.util.spec_from_file_location("ha_soc_probe_netscan", PROBE_NETSCAN)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROBE_NETSCAN.parent))
    return module


@pytest.mark.usefixtures("socket_enabled")
async def test_probe_reads_the_certificate_from_an_unverified_handshake(probe_netscan, tmp_path):
    der, pem, key_pem = _certificate("device.example")
    (tmp_path / "cert.pem").write_bytes(pem)
    (tmp_path / "key.pem").write_bytes(key_pem)
    server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_ctx.load_cert_chain(tmp_path / "cert.pem", tmp_path / "key.pem")

    async def _serve(_reader, writer):
        writer.close()

    server = await asyncio.start_server(_serve, "127.0.0.1", 0, ssl=server_ctx)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await probe_netscan._read_tls_cert("127.0.0.1", port)
    finally:
        server.close()
        await server.wait_closed()

    assert result == {"sha256": _sha(der), "_der": der}


def _probe_hosts(*ders: bytes):
    return [
        {
            "ip": f"192.0.2.{10 + index}",
            "open_ports": [{"port": 443, "tls": {"sha256": _sha(der), "_der": der}}],
        }
        for index, der in enumerate(ders)
    ]


def test_probe_reports_the_old_shape_to_an_integration_that_sent_no_list(probe_netscan):
    der, _pem, _key = _certificate("device.example")
    hosts = _probe_hosts(der)
    probe_netscan._attach_certificates(hosts, None)
    assert hosts[0]["open_ports"][0]["tls"] == {
        "subject": None,
        "issuer": None,
        "not_after": None,
        "self_signed": None,
    }


def test_probe_sends_der_once_and_only_for_unknown_fingerprints(probe_netscan):
    known_der, _pem, _key = _certificate("known.example")
    new_der, _pem, _key = _certificate("new.example")
    hosts = _probe_hosts(known_der, new_der, new_der)
    probe_netscan._attach_certificates(hosts, {_sha(known_der)})
    tls = [host["open_ports"][0]["tls"] for host in hosts]
    assert tls[0] == {"sha256": _sha(known_der)}
    assert tls[1] == {"sha256": _sha(new_der), "der": _b64(new_der)}
    assert tls[2] == {"sha256": _sha(new_der)}
    # What the Probe reports must be what the integration's schema accepts.
    for host in hosts:
        NETSCAN_HOST_SCHEMA(host)


def test_probe_bounds_the_der_it_sends_in_one_cycle(probe_netscan, monkeypatch):
    first, _pem, _key = _certificate("first.example")
    second, _pem, _key = _certificate("second.example")
    monkeypatch.setattr(probe_netscan, "MAX_DER_BYTES_PER_CYCLE", len(first))
    hosts = _probe_hosts(first, second)
    probe_netscan._attach_certificates(hosts, set())
    assert "der" in hosts[0]["open_ports"][0]["tls"]
    assert hosts[1]["open_ports"][0]["tls"] == {"sha256": _sha(second)}

    monkeypatch.setattr(probe_netscan, "MAX_DER_BYTES", len(first) - 1)
    hosts = _probe_hosts(first)
    probe_netscan._attach_certificates(hosts, set())
    assert hosts[0]["open_ports"][0]["tls"] == {"sha256": _sha(first)}


def test_probe_known_list_absent_is_not_the_same_as_empty(probe_netscan):
    assert probe_netscan._parse_known_certs(None) is None
    assert probe_netscan._parse_known_certs("[]") == set()
    assert probe_netscan._parse_known_certs("not json") == set()
    good = "a" * 64
    assert probe_netscan._parse_known_certs(f'["{good}", "short", 7]') == {good}


# --------------------------------------------------------------------------
# Parsing and the schema
# --------------------------------------------------------------------------


def test_parse_certificate_reads_subject_issuer_and_validity():
    der, _pem, _key = _certificate("device.example", issuer="Home CA", days_left=90)
    parsed = parse_certificate(_b64(der))
    assert parsed["sha256"] == _sha(der)
    assert parsed["subject"] == "CN=device.example"
    assert parsed["issuer"] == "CN=Home CA"
    assert parsed["self_signed"] is False
    assert parsed["unreadable"] is False
    assert parsed["not_after"] == (T0 + timedelta(days=90)).isoformat()

    own, _pem, _key = _certificate("device.example")
    assert parse_certificate(_b64(own))["self_signed"] is True


def test_parse_certificate_never_raises_on_hostile_input():
    assert parse_certificate("not base64 !!") is None
    assert parse_certificate("") is None
    garbage = parse_certificate(_b64(b"\x30\x82 not a certificate"))
    assert garbage["unreadable"] is True
    assert garbage["subject"] is None
    assert parse_certificate(_b64(b"x" * 9000)) is None


def test_schema_bounds_the_fingerprint_and_the_der():
    port = {"port": 443, "tls": {"sha256": "a" * 64, "der": "QUJD"}}
    NETSCAN_HOST_SCHEMA({"ip": IP_A, "open_ports": [port]})
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"ip": IP_A, "open_ports": [{"port": 443, "tls": {"sha256": "A" * 64}}]})
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA(
            {"ip": IP_A, "open_ports": [{"port": 443, "tls": {"sha256": "a" * 64, "der": "A" * 20000}}]}
        )


def test_strip_der_removes_only_the_der():
    hosts = [{"ip": IP_A, "open_ports": [{"port": 443, "tls": {"sha256": "a" * 64, "der": "QUJD"}}]}]
    assert strip_der(hosts) == [{"ip": IP_A, "open_ports": [{"port": 443, "tls": {"sha256": "a" * 64}}]}]
    assert "der" in hosts[0]["open_ports"][0]["tls"]


# --------------------------------------------------------------------------
# Pure merge: port and certificate changes
# --------------------------------------------------------------------------


class _Replay:
    """Replays cycles for one device through merge_cycle with a fixed clock."""

    def __init__(self, port_list=None):
        self.state = inv.empty_state()
        self.port_list = port_list
        self.now = T0
        ids = count(1)
        self._new_id = lambda: f"d_{next(ids):04d}"

    def cycle(self, ports=(), *, ip=IP_A, extra_hosts=(), tls=None, port_list=None):
        open_ports = []
        for port in ports:
            entry = {"port": port}
            if tls and port in tls:
                entry["tls"] = {"sha256": tls[port]}
            open_ports.append(entry)
        hosts = [{"ip": ip, "mac": MAC_A, "open_ports": open_ports}, *extra_hosts]
        inv.merge_cycle(
            self.state,
            hosts,
            self.now,
            new_id=self._new_id,
            port_list=port_list if port_list is not None else self.port_list,
        )
        self.now += CYCLE

    def settle(self, ports=(), **kwargs):
        for _ in range(inv.PORT_QUIET_CYCLES + 1):
            self.cycle(ports, **kwargs)

    @property
    def device(self):
        return self.state["devices"]["d_0001"]

    def acknowledge(self):
        self.device["verdict"] = inv.VERDICT_ACKNOWLEDGED

    def events(self, *kinds):
        return [e for e in self.state["events"] if e["kind"] in (kinds or inv.CHANGE_EVENT_KINDS)]

    def add_cert(self, common_name, **kwargs):
        der, _pem, _key = _certificate(common_name, **kwargs)
        parsed = parse_certificate(_b64(der))
        self.state["certs"][parsed["sha256"]] = parsed
        return parsed["sha256"]


def test_ports_found_while_a_device_settles_are_not_changes():
    replay = _Replay()
    replay.cycle([22])
    replay.acknowledge()
    replay.cycle([22, 80])
    replay.cycle([22, 80, 443])
    assert replay.events() == []
    assert sorted(replay.device["ports"]) == ["22", "443", "80"]


def test_new_port_on_an_acknowledged_device_is_an_alerting_change():
    replay = _Replay()
    replay.settle([22])
    replay.acknowledge()
    replay.cycle([22, 8443])
    assert replay.events() == [
        {
            "ts": (replay.now - CYCLE).isoformat(),
            "device_id": "d_0001",
            "kind": "port_opened",
            "alert": True,
            "port": 8443,
        }
    ]
    replay.cycle([22, 8443])
    assert len(replay.events()) == 1


def test_new_port_on_an_unacknowledged_device_is_recorded_without_alert():
    replay = _Replay()
    replay.settle([22])
    replay.cycle([22, 8443])
    assert [(e["kind"], e["alert"]) for e in replay.events()] == [("port_opened", False)]


def test_port_newly_added_to_the_scan_list_is_not_a_change():
    replay = _Replay(port_list=[22])
    replay.settle([22])
    replay.acknowledge()
    replay.port_list = [22, 8443]
    replay.settle([22, 8443])
    assert replay.events() == []
    # Once the scan has looked at the port for a while, a later opening does count.
    replay.port_list = [22, 8443, 9000]
    replay.settle([22, 8443])
    replay.cycle([22, 8443, 9000])
    assert [e["port"] for e in replay.events("port_opened")] == [9000]


def test_a_port_that_misses_a_few_cycles_neither_closes_nor_reopens():
    replay = _Replay()
    replay.settle([22, 80])
    replay.acknowledge()
    for _ in range(inv.PORT_QUIET_CYCLES):
        replay.cycle([22])
    replay.cycle([22, 80])
    assert replay.events() == []


def test_a_port_shut_for_longer_closes_quietly_and_reopening_alerts():
    replay = _Replay()
    replay.settle([22, 80])
    replay.acknowledge()
    for _ in range(inv.PORT_QUIET_CYCLES + 1):
        replay.cycle([22])
    assert [(e["kind"], e["port"], e["alert"]) for e in replay.events()] == [("port_closed", 80, False)]
    assert replay.device["ports"]["80"]["closed_at"] is not None
    replay.cycle([22, 80])
    assert [(e["kind"], e["alert"]) for e in replay.events()][-1] == ("port_opened", True)
    assert replay.device["ports"]["80"]["closed_at"] is None


def test_a_port_removed_from_the_scan_list_is_not_closed():
    replay = _Replay(port_list=[22, 80])
    replay.settle([22, 80])
    replay.port_list = [22]
    replay.settle([22])
    assert replay.events() == []


def test_first_fingerprint_on_a_port_is_not_a_change():
    replay = _Replay()
    replay.settle([443])
    replay.acknowledge()
    first = replay.add_cert("device.example")
    replay.cycle([443], tls={443: first})
    assert replay.events() == []
    assert replay.device["ports"]["443"]["cert_sha256"] == first


def test_changed_certificate_alerts_and_a_renewal_does_not():
    replay = _Replay()
    old = replay.add_cert("device.example", issuer="Home CA", days_left=10)
    renewed = replay.add_cert("device.example", issuer="Home CA", days_left=400)
    other = replay.add_cert("someone.example", issuer="Other CA")
    replay.settle([443], tls={443: old})
    replay.acknowledge()

    replay.cycle([443], tls={443: renewed})
    assert [(e["kind"], e["alert"]) for e in replay.events()] == [("cert_renewed", False)]

    replay.cycle([443], tls={443: other})
    last = replay.events()[-1]
    assert (last["kind"], last["alert"]) == ("cert_changed", True)
    assert (last["previous"], last["sha256"]) == (renewed, other)


def test_same_names_far_from_expiry_is_a_change_not_a_renewal():
    replay = _Replay()
    old = replay.add_cert("device.example", issuer="Home CA", days_left=300)
    new = replay.add_cert("device.example", issuer="Home CA", days_left=400)
    replay.settle([443], tls={443: old})
    replay.acknowledge()
    replay.cycle([443], tls={443: new})
    assert [e["kind"] for e in replay.events()] == ["cert_changed"]


def test_unparsed_certificate_is_never_a_renewal():
    replay = _Replay()
    old = replay.add_cert("device.example", days_left=5)
    replay.settle([443], tls={443: old})
    replay.cycle([443], tls={443: "f" * 64})
    assert [e["kind"] for e in replay.events()] == ["cert_changed"]


def test_ports_and_certificate_changing_together_is_one_identity_shift():
    replay = _Replay()
    old = replay.add_cert("device.example")
    other = replay.add_cert("someone.example")
    replay.settle([443], tls={443: old})
    replay.acknowledge()
    replay.cycle([443, 8080], tls={443: other})
    assert [(e["kind"], e["alert"]) for e in replay.events()] == [
        ("cert_changed", False),
        ("port_opened", False),
        ("identity_shift", True),
    ]
    assert replay.events("identity_shift")[0]["reasons"] == ["ports_and_certificate"]


def test_one_mac_at_two_addresses_is_an_identity_shift_once():
    replay = _Replay()
    replay.settle([22])
    replay.acknowledge()
    second = {"ip": "192.0.2.99", "mac": MAC_A, "open_ports": []}
    replay.cycle([22], extra_hosts=[second])
    assert [(e["kind"], e["reasons"]) for e in replay.events()] == [
        ("identity_shift", ["two_addresses"])
    ]
    replay.cycle([22], extra_hosts=[second])
    replay.cycle([22], extra_hosts=[second])
    assert len(replay.events()) == 1
    # The first address stays current, and the pair does not flip on every cycle.
    assert [a["ip"] for a in replay.device["addresses"]] == [IP_A, "192.0.2.99"]
    assert [e for e in replay.state["events"] if e["kind"] == "address_changed"] == []
    assert len(replay.state["devices"]) == 1


def test_device_first_seen_with_two_addresses_raises_nothing():
    replay = _Replay()
    second = {"ip": "192.0.2.99", "mac": MAC_A, "open_ports": []}
    replay.cycle([22], extra_hosts=[second])
    replay.acknowledge()
    replay.settle([22], extra_hosts=[second])
    assert replay.events() == []


def test_a_record_from_before_this_phase_settles_instead_of_alerting():
    replay = _Replay()
    replay.cycle([22])
    replay.acknowledge()
    # What phase 1 stored: no cycle counters anywhere.
    del replay.device["seen_cycles"]
    for record in replay.device["ports"].values():
        record.pop("last_seen_cycle", None)
    replay.state["meta"].pop("scan_ports", None)
    replay.state.pop("certs")
    replay.cycle([22, 80])
    assert replay.events() == []


# --------------------------------------------------------------------------
# Ingest, poll and the detections
# --------------------------------------------------------------------------


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


async def _ingest(hass: HomeAssistant, supervisor_user, hosts) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"netscan_result": hosts, "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=supervisor_user.id),
    )


async def _poll(hass: HomeAssistant, supervisor_user) -> dict:
    return await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=Context(user_id=supervisor_user.id),
    )


async def test_ingested_certificate_is_parsed_stored_without_der_and_offered_back(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    der, _pem, _key = _certificate("device.example", issuer="Home CA")
    host = {
        "ip": IP_A,
        "mac": MAC_A,
        "open_ports": [{"port": 443, "tls": {"sha256": _sha(der), "der": _b64(der)}}],
    }
    await _ingest(hass, supervisor_user, [host])

    stored = runtime.store.data["netscan_result"]["hosts"][0]["open_ports"][0]["tls"]
    assert stored == {
        "sha256": _sha(der),
        "subject": "CN=device.example",
        "issuer": "CN=Home CA",
        "not_after": (T0 + timedelta(days=365)).isoformat(),
        "self_signed": False,
    }
    device = next(iter(runtime.inventory.state["devices"].values()))
    assert device["ports"]["443"]["cert_sha256"] == _sha(der)
    overview = runtime.inventory.overview()
    assert overview["certs"][_sha(der)]["subject"] == "CN=device.example"

    response = await _poll(hass, supervisor_user)
    assert response["known_cert_sha256"] == [_sha(der)]


async def test_poll_offers_an_empty_list_before_any_certificate(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    await _ingest(hass, supervisor_user, [{"ip": IP_A, "mac": MAC_A}])
    response = await _poll(hass, supervisor_user)
    assert response["known_cert_sha256"] == []


async def test_der_that_does_not_match_its_fingerprint_is_dropped(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    runtime = supervisor_entry.runtime_data
    der, _pem, _key = _certificate("device.example")
    claimed = "b" * 64
    host = {"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": 443, "tls": {"sha256": claimed, "der": _b64(der)}}]}
    await _ingest(hass, supervisor_user, [host])
    assert runtime.inventory.state["certs"] == {}
    stored = runtime.store.data["netscan_result"]["hosts"][0]["open_ports"][0]["tls"]
    assert stored["sha256"] == claimed
    assert stored["subject"] is None
    assert "der" not in stored


async def test_old_probe_result_without_fingerprints_still_ingests(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_user
) -> None:
    legacy = {"subject": None, "issuer": None, "not_after": None, "self_signed": None}
    await _ingest(
        hass, supervisor_user, [{"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": 443, "tls": legacy}]}]
    )
    runtime = supervisor_entry.runtime_data
    assert runtime.store.data["netscan_result"]["hosts"][0]["open_ports"][0]["tls"] == legacy
    device = next(iter(runtime.inventory.state["devices"].values()))
    assert "cert_sha256" not in device["ports"]["443"]


async def _entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


CHANGE_RULES = (RULE_NETWORK_PORT_OPENED, RULE_NETWORK_CERT_CHANGED, RULE_NETWORK_IDENTITY_SHIFT)


def _change_detections(runtime):
    return [d for d in runtime.store.data["detections"].values() if d["rule_id"] in CHANGE_RULES]


async def _settled_device(runtime, ports):
    inventory = runtime.inventory
    host = {"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": port} for port in ports]}
    for _ in range(inv.PORT_QUIET_CYCLES + 1):
        inventory.async_merge_cycle([host])
    device = next(iter(inventory.state["devices"].values()))
    device["verdict"] = inv.VERDICT_ACKNOWLEDGED
    return device


async def test_opened_port_raises_one_detection_that_names_only_the_device(
    hass: HomeAssistant,
) -> None:
    runtime = (await _entry(hass)).runtime_data
    device = await _settled_device(runtime, [22])
    runtime.inventory.async_merge_cycle(
        [{"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": 22}, {"port": 8443}]}]
    )
    await runtime.detections.async_run_pass()
    await runtime.detections.async_run_pass()

    detections = _change_detections(runtime)
    assert [d["rule_id"] for d in detections] == [RULE_NETWORK_PORT_OPENED]
    detection = detections[0]
    assert detection["severity"] == "medium"
    assert set(detection["detail"]) == {"device_id", "changed_at"}
    assert detection["detail"]["device_id"] == device["id"]
    flat = repr(detection)
    assert MAC_A not in flat and IP_A not in flat and "8443" not in flat


async def test_identity_shift_raises_one_high_detection(hass: HomeAssistant) -> None:
    runtime = (await _entry(hass)).runtime_data
    await _settled_device(runtime, [22])
    runtime.inventory.async_merge_cycle(
        [
            {"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": 22}]},
            {"ip": "192.0.2.99", "mac": MAC_A, "open_ports": []},
        ]
    )
    await runtime.detections.async_run_pass()
    detections = _change_detections(runtime)
    assert [(d["rule_id"], d["severity"]) for d in detections] == [
        (RULE_NETWORK_IDENTITY_SHIFT, "high")
    ]
    assert detections[0]["detail"]["reasons"] == ["two_addresses"]


async def test_change_on_a_device_no_longer_acknowledged_raises_nothing(
    hass: HomeAssistant,
) -> None:
    runtime = (await _entry(hass)).runtime_data
    device = await _settled_device(runtime, [22])
    runtime.inventory.async_merge_cycle(
        [{"ip": IP_A, "mac": MAC_A, "open_ports": [{"port": 22}, {"port": 8443}]}]
    )
    device["verdict"] = inv.VERDICT_UNACKNOWLEDGED
    await runtime.detections.async_run_pass()
    assert _change_detections(runtime) == []


async def test_old_change_event_raises_nothing(hass: HomeAssistant) -> None:
    runtime = (await _entry(hass)).runtime_data
    device = await _settled_device(runtime, [22])
    runtime.inventory.state["events"].append(
        {
            "ts": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat(),
            "device_id": device["id"],
            "kind": "port_opened",
            "alert": True,
            "port": 8443,
        }
    )
    await runtime.detections.async_run_pass()
    assert _change_detections(runtime) == []
