"""Tests for netscan.py: schema validation, config generation, capability
gating, and owner-only access on the netscan status command.

Follows test_probe.py's Supervisor-context fixture pattern for the
ingest/poll service tests, and test_probe.py's ws_probe_status pattern for
the WebSocket owner-only check.
"""
from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from custom_components.ha_soc.const import CONF_NETSCAN_ENABLED, DOMAIN
from custom_components.ha_soc.netscan import (
    NETSCAN_HOST_SCHEMA,
    async_config_for_probe,
    validate_mac,
    validate_max_concurrency,
    validate_port_list,
)
from custom_components.ha_soc.store import HaSocData

PROBE_SECRET = "unit-test-probe-secret"


# --------------------------------------------------------------------------
# Schema validation
# --------------------------------------------------------------------------


def test_valid_host_minimal():
    doc = NETSCAN_HOST_SCHEMA({"ip": "192.168.1.10"})
    assert doc["ip"] == "192.168.1.10"


def test_valid_host_with_ports_and_tls():
    doc = NETSCAN_HOST_SCHEMA(
        {
            "ip": "192.168.1.10",
            "mac": "AA:BB:CC:DD:EE:FF",
            "vendor": "Example Corp",
            "open_ports": [
                {"port": 22, "banner": "SSH-2.0-OpenSSH_9.6", "service_guess": "ssh"},
                {
                    "port": 443,
                    "service_guess": "tls",
                    "tls": {
                        "subject": "CN=router.local",
                        "issuer": "CN=router.local",
                        "not_after": "Jan  1 00:00:00 2030 GMT",
                        "self_signed": True,
                    },
                },
            ],
        }
    )
    assert doc["mac"] == "aa:bb:cc:dd:ee:ff"  # lower-cased by validate_mac
    assert doc["open_ports"][1]["tls"]["self_signed"] is True


def test_invalid_host_bad_mac_rejected():
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"ip": "192.168.1.10", "mac": "not-a-mac"})


def test_invalid_host_missing_ip_rejected():
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"mac": "aa:bb:cc:dd:ee:ff"})


def test_invalid_host_bad_port_rejected():
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA({"ip": "192.168.1.10", "open_ports": [{"port": 99999}]})


def test_invalid_host_oversized_banner_rejected():
    with pytest.raises(vol.Invalid):
        NETSCAN_HOST_SCHEMA(
            {"ip": "192.168.1.10", "open_ports": [{"port": 22, "banner": "x" * 1000}]}
        )


def test_validate_mac_accepts_none_and_normalizes_case():
    assert validate_mac(None) is None
    assert validate_mac("AA:11:BB:22:CC:33") == "aa:11:bb:22:cc:33"


def test_validate_port_list_dedupes_and_defaults():
    assert validate_port_list(None) == [22, 23, 80, 443, 445, 3389, 8080, 8443]
    assert validate_port_list([443, 443, 80]) == [443, 80]


def test_validate_port_list_rejects_oversized_list():
    with pytest.raises(vol.Invalid):
        validate_port_list(list(range(1, 200)))


def test_validate_port_list_rejects_non_list():
    with pytest.raises(vol.Invalid):
        validate_port_list("443")


def test_validate_max_concurrency_bounds():
    assert validate_max_concurrency(32) == 32
    with pytest.raises(vol.Invalid):
        validate_max_concurrency(0)
    with pytest.raises(vol.Invalid):
        validate_max_concurrency(129)


# --------------------------------------------------------------------------
# Config generation for the Probe
# --------------------------------------------------------------------------


async def test_config_for_probe_disabled_by_default():
    config = await async_config_for_probe({})
    assert config["enabled"] is False
    assert config["port_list"] == [22, 23, 80, 443, 445, 3389, 8080, 8443]
    assert config["max_concurrency"] == 32
    assert config["generation"]


async def test_config_for_probe_generation_changes_with_settings():
    base = await async_config_for_probe({CONF_NETSCAN_ENABLED: False})
    changed = await async_config_for_probe(
        {CONF_NETSCAN_ENABLED: True, "netscan_port_list": [22]}
    )
    assert base["generation"] != changed["generation"]
    assert changed["enabled"] is True
    assert changed["port_list"] == [22]


# --------------------------------------------------------------------------
# Capability gating and ingest, mirroring test_probe.py's Supervisor fixtures
# --------------------------------------------------------------------------


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def supervisor_context(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


async def test_poll_netscan_config_registered_and_gated(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context, tmp_path
) -> None:
    # Isolate the audit dir: the intruder call below is a real audited
    # rejection and must not leak into the shared default audit path other
    # tests in the same session may inspect (see test_probe.py's twin note).
    supervisor_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    assert hass.services.has_service(DOMAIN, "poll_netscan_config")

    # A non-Supervisor caller gets the empty/disabled answer, never real config.
    intruder = MockUser()
    intruder.add_to_hass(hass)
    response = await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=Context(user_id=intruder.id),
    )
    assert response == {"enabled": False}

    # The real Probe, once its secret is pinned by a prior call, gets the
    # full generation-tagged config.
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=supervisor_context,
    )
    response = await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response["enabled"] is False  # default; owner never enabled it in this test
    assert "generation" in response
    assert "port_list" in response


async def test_ingest_netscan_result_stores_hosts_and_capabilities(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "netscan_result": [
                {
                    "ip": "192.168.1.10",
                    "mac": "aa:bb:cc:dd:ee:ff",
                    "vendor": "Example Corp",
                    "open_ports": [{"port": 22, "banner": "SSH-2.0", "service_guess": "ssh"}],
                }
            ],
            "netscan_capabilities": {"tcp_connect": True, "bogus_capability": True},
            "scanner_version": "netscan/1.0",
            "probe_secret": PROBE_SECRET,
        },
        blocking=True,
        context=supervisor_context,
    )
    result = supervisor_entry.runtime_data.store.data["netscan_result"]
    assert result is not None
    assert result["hosts"][0]["ip"] == "192.168.1.10"
    assert result["hosts"][0]["vendor"] == "Example Corp"
    # Only the known capability allowlist survives, same pattern as firewall_capabilities.
    assert result["capabilities"] == {"tcp_connect": True}
    assert result["scanner_version"] == "netscan/1.0"
    assert result["reported_at"]


async def test_ingest_netscan_result_rejects_malformed_host(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {
                "netscan_result": [{"ip": "192.168.1.10", "open_ports": [{"port": "not-a-port"}]}],
                "probe_secret": PROBE_SECRET,
            },
            blocking=True,
            context=supervisor_context,
        )


async def test_unauthenticated_netscan_ingest_is_rejected(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, tmp_path
) -> None:
    # Per-test audit dir, same reasoning as test_probe.py's
    # test_probe_rejection_is_audited_and_detected: the rejection this test
    # provokes is a real audited event, and without an isolated directory it
    # would land in the shared default audit path and leak into any other
    # test in the same session that inspects "probe_auth_rejected" events.
    supervisor_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")
    store = supervisor_entry.runtime_data.store
    attacker = MockUser()
    attacker.add_to_hass(hass)
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "netscan_result": [{"ip": "192.168.1.10"}],
            "probe_secret": "attacker-secret",
        },
        blocking=True,
        context=Context(user_id=attacker.id),
    )
    assert store.data["netscan_result"] is None


# --------------------------------------------------------------------------
# Owner-only WebSocket gating on ha_soc/netscan/status
# --------------------------------------------------------------------------


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


async def test_ws_netscan_status_requires_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_netscan_status

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=False)

    with pytest.raises(Unauthorized):
        ws_netscan_status(hass, connection, {"id": 1})


async def test_ws_netscan_status_returns_result_for_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_netscan_status

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    config_entry.runtime_data.store.async_set_netscan_result(
        {"hosts": [{"ip": "192.168.1.10"}], "capabilities": {"tcp_connect": True}}
    )

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True)

    ws_netscan_status(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["enabled"] is False
    assert result["result"]["hosts"][0]["ip"] == "192.168.1.10"


# --------------------------------------------------------------------------
# On-demand rescan: ha_soc/netscan/rescan, its audit trail, and the Probe's
# poll response carrying the request.
# --------------------------------------------------------------------------


async def test_ws_netscan_rescan_requires_owner(hass: HomeAssistant) -> None:
    from custom_components.ha_soc.websocket_api import ws_netscan_rescan

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=False)

    with pytest.raises(Unauthorized):
        ws_netscan_rescan(hass, connection, {"id": 1})


async def test_ws_netscan_rescan_sets_request_and_audits(hass: HomeAssistant, tmp_path) -> None:
    from custom_components.ha_soc.websocket_api import ws_netscan_rescan

    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    config_entry.runtime_data.audit._dir_path = str(tmp_path / "audit")

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")

    assert config_entry.runtime_data.store.data["netscan_rescan_requested_at"] is None

    ws_netscan_rescan(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["ok"] is True
    requested_at = result["requested_at"]
    assert requested_at
    assert config_entry.runtime_data.store.data["netscan_rescan_requested_at"] == requested_at

    events = await config_entry.runtime_data.audit.async_query(limit=50)
    matching = [e for e in events if e["detail"].get("action") == "netscan_rescan_requested"]
    assert len(matching) == 1
    assert matching[0]["user_id"] == "owner-id"
    assert matching[0]["detail"]["requested_at"] == requested_at


async def test_poll_netscan_config_carries_rescan_request(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = supervisor_entry.runtime_data.store
    assert store.data["netscan_rescan_requested_at"] is None

    # Pin the probe secret first, same as test_poll_netscan_config_registered_and_gated.
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=supervisor_context,
    )

    response = await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response["rescan_requested_at"] is None

    store.async_request_netscan_rescan("2026-09-15T00:00:00+00:00")
    response = await hass.services.async_call(
        DOMAIN,
        "poll_netscan_config",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response["rescan_requested_at"] == "2026-09-15T00:00:00+00:00"
