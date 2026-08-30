"""Tests for probe.py: Supervisor/add-on detection and the two callback
services (ingest_probe_result / poll_firewall_command).

The test harness never runs under real Supervisor, so is_hassio(hass) is
always False here unless patched, which is itself the first thing worth
proving: this module must degrade honestly (not silently) off Supervisor,
and since the Supervisor-context authentication change that includes not
registering the callback services at all on a Core/Container install.

Service-call tests therefore run against a "Supervisor install" fixture:
is_hassio is patched True for the config-entry setup (the same way the
overview tests fake hassio presence), the Supervisor system user is
created through hass.auth exactly the way core's hassio component creates
it, and every legitimate call passes that user's context plus the shared
probe secret.
"""
from unittest.mock import patch

import pytest
import voluptuous as vol
from pytest_homeassistant_custom_component.common import MockConfigEntry, MockUser

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant

from custom_components.ha_soc.const import DOMAIN, PROBE_ADDON_NAME
from custom_components.ha_soc.probe import _async_supervisor_user_id, async_probe_overview
from custom_components.ha_soc.secrets_store import PROBE_PAIRING_SECRET_KEY
from custom_components.ha_soc.store import HaSocData

# The secret the fake add-on presents. The first Supervisor-context call
# pins it; later calls must match it.
PROBE_SECRET = "unit-test-probe-secret"


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


async def test_off_supervisor_is_honestly_unavailable(hass: HomeAssistant, store: HaSocData) -> None:
    overview = await async_probe_overview(hass, store)
    assert overview == {
        "supervisor": False,
        "installed": False,
        "running": False,
        "version": None,
        "update_available": False,
        "result": None,
    }


async def test_on_supervisor_addon_not_installed(hass: HomeAssistant, store: HaSocData) -> None:
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value={}),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["supervisor"] is True
    assert overview["installed"] is False
    assert overview["running"] is False


async def test_on_supervisor_addon_installed_and_running(hass: HomeAssistant, store: HaSocData) -> None:
    fake_addons = {
        "local_ha_soc_probe": {
            "name": PROBE_ADDON_NAME,
            "state": "started",
            "version": "1.2.0",
            "update_available": False,
        },
        "core_ssh": {"name": "Terminal & SSH", "state": "started"},
    }
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["supervisor"] is True
    assert overview["installed"] is True
    assert overview["running"] is True
    assert overview["version"] == "1.2.0"


async def test_on_supervisor_addon_installed_but_stopped(hass: HomeAssistant, store: HaSocData) -> None:
    fake_addons = {
        "local_ha_soc_probe": {
            "name": PROBE_ADDON_NAME,
            "state": "stopped",
            "version": "1.2.0",
            "update_available": True,
        },
    }
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("homeassistant.components.hassio.get_addons_info", return_value=fake_addons),
    ):
        overview = await async_probe_overview(hass, store)
    assert overview["installed"] is True
    assert overview["running"] is False
    assert overview["update_available"] is True


# -- Fixtures for the service-call tests -----------------------------------


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    """A plain (non-Supervisor) install: services must NOT be registered."""
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    """The Supervisor system user, created exactly the way core's hassio
    component creates it (async_create_system_user with the admin group,
    verified against core 2026.2.3, components/hassio/__init__.py:357-358).
    """
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    """A simulated Supervisor install: is_hassio is patched True while the
    entry sets up, so the callback services register.
    """
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def supervisor_context(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


# -- Legitimate add-on calls (Supervisor context + secret) ------------------


async def test_ingest_service_stores_result(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "open_ports": [
                {"port": 22, "proto": "tcp", "process": "sshd"},
                {"port": 8123, "proto": "tcp"},
            ],
            "scanner_version": "0.1.0",
            "probe_secret": PROBE_SECRET,
        },
        blocking=True,
        context=supervisor_context,
    )
    result = supervisor_entry.runtime_data.store.data["host_probe"]
    assert result is not None
    assert result["scanner_version"] == "0.1.0"
    assert result["open_ports"][0]["port"] == 22
    assert result["reported_at"]


async def test_ingest_service_accepts_address_and_interface(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "open_ports": [
                {"port": 8123, "proto": "tcp", "address": "0.0.0.0", "interface": "(all interfaces)"},
                {"port": 22, "proto": "tcp", "address": "192.168.10.5", "interface": "eth0.10"},
                {"port": 5353, "proto": "udp"},  # older report shape, no address/interface at all
            ],
            "probe_secret": PROBE_SECRET,
        },
        blocking=True,
        context=supervisor_context,
    )
    ports = supervisor_entry.runtime_data.store.data["host_probe"]["open_ports"]
    assert ports[0]["address"] == "0.0.0.0"
    assert ports[0]["interface"] == "(all interfaces)"
    assert ports[1]["address"] == "192.168.10.5"
    assert ports[1]["interface"] == "eth0.10"
    assert ports[2].get("address") is None


async def test_ingest_service_rejects_bad_port(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    with pytest.raises(vol.MultipleInvalid):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {"open_ports": [{"port": 999999, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
            blocking=True,
            context=supervisor_context,
        )


async def test_supervisor_user_id_prefers_hassio_config_store(
    hass: HomeAssistant, supervisor_user
) -> None:
    """When the hassio component's config store is loaded, its recorded id
    wins over the auth-registry fallback."""
    from types import SimpleNamespace

    from homeassistant.components.hassio.const import DATA_CONFIG_STORE

    hass.data[DATA_CONFIG_STORE] = SimpleNamespace(
        data=SimpleNamespace(hassio_user="preferred-id-from-config-store")
    )
    try:
        assert await _async_supervisor_user_id(hass) == "preferred-id-from-config-store"
    finally:
        del hass.data[DATA_CONFIG_STORE]

    # Without the config store, the system-generated user named Supervisor
    # is found through the public auth registry.
    assert await _async_supervisor_user_id(hass) == supervisor_user.id


# -- Rejections: wrong or missing context, missing secret -------------------


async def test_probe_requires_supervisor_context(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry
) -> None:
    """A call from any non-Supervisor account, and a call with no user
    context at all (an automation), are both rejected before the payload
    is processed."""
    store = supervisor_entry.runtime_data.store
    admin = MockUser()
    admin.add_to_hass(hass)

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=admin.id),
    )
    assert store.data["host_probe"] is None

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": PROBE_SECRET},
        blocking=True,
        context=Context(user_id=None),
    )
    assert store.data["host_probe"] is None

    response = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=Context(user_id=admin.id),
    )
    assert response == {"action": "none"}


async def test_missing_secret_is_rejected_even_from_supervisor(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """The shared secret is defense in depth BEHIND the context check, but
    it is still mandatory: a Supervisor-context call with no secret is
    rejected (the old nothing-pinned-nothing-presented acceptance is gone).
    """
    store = supervisor_entry.runtime_data.store
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}]},
        blocking=True,
        context=supervisor_context,
    )
    assert store.data["host_probe"] is None
    events = await supervisor_entry.runtime_data.audit.async_query(
        category="probe_auth_rejected", limit=10
    )
    assert events
    assert events[0]["detail"]["reason"] == "no_secret"


async def test_unauthenticated_ingest_is_rejected_before_pinning(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry
) -> None:
    """Guarantee (inverts the old first-boot race): with nothing pinned
    yet, an ingest call without the Supervisor context neither gets its
    payload processed nor pins its own secret. The pin lives in the
    private secret store since SEC-1, so that is where absence is proven."""
    store = supervisor_entry.runtime_data.store
    secrets = supervisor_entry.runtime_data.secrets
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) is None

    attacker = MockUser()
    attacker.add_to_hass(hass)
    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": "attacker-secret"},
        blocking=True,
        context=Context(user_id=attacker.id),
    )
    assert store.data["host_probe"] is None
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) is None


async def test_first_poll_caller_cannot_pin_without_supervisor_context(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """Guarantee (inverts the old first-poll pin): with nothing pinned yet,
    a non-Supervisor poll gets no work and pins nothing; the real add-on's
    first Supervisor-context poll afterwards still pins its own secret,
    into the private secret store (SEC-1), never the general store."""
    secrets = supervisor_entry.runtime_data.secrets
    attacker = MockUser()
    attacker.add_to_hass(hass)

    response = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": "attacker-secret"},
        blocking=True,
        return_response=True,
        context=Context(user_id=attacker.id),
    )
    assert response == {"action": "none"}
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) is None

    response = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": PROBE_SECRET},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response == {"action": "none"}
    assert await secrets.async_get(PROBE_PAIRING_SECRET_KEY) == PROBE_SECRET
    # The general store's firewall dict carries no copy of the pin.
    assert "addon_secret" not in supervisor_entry.runtime_data.store.data["firewall"]


async def test_probe_rejection_is_audited_and_detected(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, tmp_path
) -> None:
    runtime = supervisor_entry.runtime_data
    # The harness shares one config dir across tests, so audit day files
    # accumulate there; point this test's audit log at a private directory
    # (the same isolation test_audit.py uses) and drop any detections the
    # startup analysis pass derived from the shared files, so the counts
    # below are this test's own.
    runtime.audit._dir_path = str(tmp_path / "audit")
    runtime.store.data["detections"].clear()
    attacker = MockUser()
    attacker.add_to_hass(hass)

    # Two rejected calls in the same hour: both audited, ONE detection.
    for _ in range(2):
        await hass.services.async_call(
            DOMAIN,
            "ingest_probe_result",
            {"open_ports": [{"port": 22, "proto": "tcp"}], "probe_secret": "forged"},
            blocking=True,
            context=Context(user_id=attacker.id),
        )

    events = await runtime.audit.async_query(category="probe_auth_rejected", limit=10)
    assert len(events) == 2
    assert events[0]["detail"] == {
        "service": "ingest_probe_result",
        "caller_user_id": attacker.id,
        "reason": "not_supervisor",
    }

    await runtime.detections.async_run_pass()
    detections = [
        d
        for d in runtime.store.data["detections"].values()
        if d["rule_id"] == "probe_auth_rejected"
    ]
    assert len(detections) == 1
    assert detections[0]["severity"] == "high"
    assert detections[0]["user_id"] == attacker.id
    assert detections[0]["detail"]["reason"] == "not_supervisor"


async def test_probe_services_absent_on_core_install(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """On a Core/Container install nothing can legitimately call the two
    services (there is no Supervisor proxy), so they are not registered at
    all, and unloading tolerates their absence."""
    assert not hass.services.has_service(DOMAIN, "ingest_probe_result")
    assert not hass.services.has_service(DOMAIN, "poll_firewall_command")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_ws_probe_status_returns_overview(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    from unittest.mock import MagicMock

    from custom_components.ha_soc.websocket_api import ws_probe_status

    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True)

    ws_probe_status(hass, connection, {"id": 1})
    await hass.async_block_till_done()

    result = connection.send_result.call_args[0][1]
    assert result["supervisor"] is False
    assert result["installed"] is False
