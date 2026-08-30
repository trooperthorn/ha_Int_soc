"""Tests for the Container Resource Watchdog + Docker hard-cap plumbing.

The rules pinned here are the ones that make the feature safe, not just the
happy path:

- Only a SUSTAINED breach (N consecutive samples) trips the watchdog.
- Core/Supervisor are NEVER auto-restarted/stopped, whatever the config.
- The per-hour enforcement budget downgrades a restart loop to alert-only.
- The hard-caps block rides the firewall poll response, and the Probe's
  applied-state report lands in the store.
- Watchdog/cap configuration mutation is owner-only at the WS layer.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.resource_watchdog import (
    ResourceWatchdog,
    async_resource_limits_for_probe,
    async_store_limit_report,
)
from custom_components.ha_soc.secrets_store import PROBE_PAIRING_SECRET_KEY
from custom_components.ha_soc.store import HaSocData


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    """The Supervisor system user, needed because the two Probe callback
    services now require its context (see probe.py)."""
    return await hass.auth.async_create_system_user(
        HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN]
    )


@pytest.fixture
async def entry(hass: HomeAssistant, supervisor_user) -> MockConfigEntry:
    # Simulate a Supervisor install during setup so the Probe callback
    # services register at all; the hard-cap plumbing under test rides on
    # their poll channel.
    with patch("custom_components.ha_soc.probe.is_hassio", return_value=True):
        config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def supervisor_context(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


def _overview(containers):
    return {"available": True, "containers": containers, "generated_at": "x", "reason": None}


def _addon(slug, cpu=10.0, mem=10.0, state="started", kind="addon"):
    return {
        "slug": slug,
        "name": slug,
        "kind": kind,
        "state": state,
        "cpu_percent": cpu,
        "memory_percent": mem,
        "memory_usage": 1,
    }


def _watchdog(entry, **cfg) -> ResourceWatchdog:
    wd = entry.runtime_data.watchdog
    wd.config.update({"enabled": True, "sustained_samples": 2, **cfg})
    return wd


async def test_sustained_breach_required_before_action(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    wd = _watchdog(entry, default_action="restart")
    client = MagicMock()
    client.addons.restart_addon = AsyncMock()

    with (
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(return_value=_overview([_addon("music_assistant", mem=99.0)])),
        ),
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
    ):
        await wd.async_run_once()  # breach sample 1 of 2 — no action yet
        client.addons.restart_addon.assert_not_called()
        await wd.async_run_once()  # sustained — acts
        client.addons.restart_addon.assert_awaited_once_with("music_assistant")

    detection = entry.runtime_data.store.data["detections"]["watchdog_music_assistant"]
    assert detection["rule_id"] == "container_resource_breach"
    assert detection["detail"]["action_taken"] == "add-on restarted"


async def test_breach_counter_resets_when_usage_recovers(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    wd = _watchdog(entry, default_action="restart")
    client = MagicMock()
    client.addons.restart_addon = AsyncMock()

    samples = [
        _overview([_addon("ok_addon", mem=99.0)]),  # breach 1
        _overview([_addon("ok_addon", mem=20.0)]),  # recovered — counter resets
        _overview([_addon("ok_addon", mem=99.0)]),  # breach 1 again
    ]
    with (
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(side_effect=samples),
        ),
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
    ):
        for _ in samples:
            await wd.async_run_once()

    client.addons.restart_addon.assert_not_called()  # never reached 2 in a row


async def test_core_and_supervisor_never_enforced(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    wd = _watchdog(entry, default_action="stop")
    client = MagicMock()
    client.addons.stop_addon = AsyncMock()
    client.addons.restart_addon = AsyncMock()

    overview = _overview(
        [
            _addon("core", mem=99.0, kind="core"),
            _addon("supervisor", mem=99.0, kind="supervisor"),
        ]
    )
    with (
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(return_value=overview),
        ),
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
    ):
        await wd.async_run_once()
        await wd.async_run_once()  # sustained for both

    client.addons.stop_addon.assert_not_called()
    client.addons.restart_addon.assert_not_called()
    # But the breach WAS detected (alert-only), for both.
    assert "watchdog_core" in entry.runtime_data.store.data["detections"]
    assert "watchdog_supervisor" in entry.runtime_data.store.data["detections"]


async def test_action_budget_downgrades_restart_loop(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    wd = _watchdog(entry, default_action="restart", sustained_samples=1)
    client = MagicMock()
    client.addons.restart_addon = AsyncMock()

    with (
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(return_value=_overview([_addon("loopy", mem=99.0)])),
        ),
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
    ):
        for _ in range(5):  # budget is 3/hour
            await wd.async_run_once()

    assert client.addons.restart_addon.await_count == 3
    detection = entry.runtime_data.store.data["detections"]["watchdog_loopy"]
    assert detection["detail"]["restart_loop_suspected"] is True


async def test_per_container_override_and_disable(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    wd = _watchdog(entry, default_action="restart", default_memory_percent=85)
    wd.config["overrides"] = {
        "quiet": {"enabled": False},  # watchdog off for this one
        "strict": {"memory_percent": 50, "action": "alert"},  # tighter, alert-only
    }
    client = MagicMock()
    client.addons.restart_addon = AsyncMock()

    overview = _overview([_addon("quiet", mem=99.0), _addon("strict", mem=60.0)])
    with (
        patch(
            "custom_components.ha_soc.resource_watchdog.async_container_resources",
            new=AsyncMock(return_value=overview),
        ),
        patch("homeassistant.components.hassio.get_supervisor_client", return_value=client),
    ):
        await wd.async_run_once()
        await wd.async_run_once()

    client.addons.restart_addon.assert_not_called()
    assert "watchdog_quiet" not in entry.runtime_data.store.data["detections"]
    assert "watchdog_strict" in entry.runtime_data.store.data["detections"]  # alerted


# -- Hard-cap plumbing --------------------------------------------------------


async def test_limits_for_probe_and_report_roundtrip(hass: HomeAssistant) -> None:
    store = HaSocData(hass)
    await store.async_load()

    assert async_resource_limits_for_probe(store) is None  # nothing configured

    store.data["resource_watchdog"]["hard_limits"] = {
        "music_assistant": {"memory_mb": 1024, "cpus": 1.5},
        "cleared": {"memory_mb": None, "cpus": None},  # empty entry -> excluded
    }
    block = async_resource_limits_for_probe(store)
    assert block == {"limits": {"music_assistant": {"memory_mb": 1024, "cpus": 1.5}}}

    async_store_limit_report(
        store, {"music_assistant": {"status": "applied", "detail": None}}
    )
    state = store.data["resource_watchdog"]["hard_limit_state"]["music_assistant"]
    assert state["status"] == "applied"
    assert state["at"]


async def test_poll_response_carries_limits(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    """The firewall poll answer piggybacks the caps for the Probe."""
    store = entry.runtime_data.store
    # Pin the shared secret so the poll is accepted. Since SEC-1 the pin
    # lives in the private secret store, not the firewall dict.
    await entry.runtime_data.secrets.async_set(PROBE_PAIRING_SECRET_KEY, "s3cret")
    store.data["resource_watchdog"]["hard_limits"] = {"ma": {"memory_mb": 512, "cpus": None}}

    response = await hass.services.async_call(
        DOMAIN,
        "poll_firewall_command",
        {"probe_secret": "s3cret"},
        blocking=True,
        return_response=True,
        context=supervisor_context,
    )
    assert response["resource_limits"] == {"limits": {"ma": {"memory_mb": 512, "cpus": None}}}


async def test_ingest_stores_limit_report(
    hass: HomeAssistant, entry: MockConfigEntry, supervisor_context: Context
) -> None:
    store = entry.runtime_data.store
    await entry.runtime_data.secrets.async_set(PROBE_PAIRING_SECRET_KEY, "s3cret")

    await hass.services.async_call(
        DOMAIN,
        "ingest_probe_result",
        {
            "probe_secret": "s3cret",
            "resource_limit_state": {"ma": {"status": "denied", "detail": "protection on"}},
        },
        blocking=True,
        context=supervisor_context,
    )
    state = store.data["resource_watchdog"]["hard_limit_state"]["ma"]
    assert state["status"] == "denied"
    assert state["detail"] == "protection on"


# -- WS layer -----------------------------------------------------------------


def _connection(*, owner: bool) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=owner, id="u1")
    return connection


async def test_ws_set_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    from custom_components.ha_soc.websocket_api import ws_watchdog_set

    with pytest.raises(Unauthorized):
        ws_watchdog_set(hass, _connection(owner=False), {"id": 1, "enabled": True})

    connection = _connection(owner=True)
    # The stored slugs must name installed add-ons since work item 2.2;
    # this test is about the owner gate and the write path, so the
    # Supervisor lookup is stubbed to report "ma" as installed.
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_installed_addon_slugs",
        return_value={"ma"},
    ):
        ws_watchdog_set(
            hass,
            connection,
            {
                "id": 2,
                "enabled": True,
                "default_memory_percent": 70,
                "override": {"slug": "ma", "action": "alert"},
                "hard_limit": {"slug": "ma", "memory_mb": 1024},
            },
        )
        await hass.async_block_till_done(wait_background_tasks=True)

    connection.send_error.assert_not_called()
    cfg = entry.runtime_data.store.data["resource_watchdog"]
    assert cfg["enabled"] is True
    assert cfg["default_memory_percent"] == 70
    assert cfg["overrides"]["ma"]["action"] == "alert"
    assert cfg["hard_limits"]["ma"] == {"memory_mb": 1024, "cpus": None}
    # Timer armed since enabled=True.
    assert entry.runtime_data.watchdog._unsub is not None
    entry.runtime_data.watchdog.async_stop()


async def test_ws_clear_hard_limit(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    # Deliberately NO installed-add-on stub and no Supervisor here: a clear
    # is exempt from the work-item-2.2 installed check, precisely so a cap
    # left behind by a since-uninstalled add-on (or set before a move off
    # Supervisor) stays removable.
    from custom_components.ha_soc.websocket_api import ws_watchdog_set

    cfg = entry.runtime_data.store.data["resource_watchdog"]
    cfg["hard_limits"] = {"ma": {"memory_mb": 1024, "cpus": None}}
    cfg["hard_limit_state"] = {"ma": {"status": "applied", "detail": None, "at": "x"}}

    connection = _connection(owner=True)
    ws_watchdog_set(hass, connection, {"id": 1, "hard_limit": {"slug": "ma", "memory_mb": None, "cpus": None}})
    await hass.async_block_till_done(wait_background_tasks=True)

    connection.send_error.assert_not_called()
    assert "ma" not in cfg["hard_limits"]
    assert "ma" not in cfg["hard_limit_state"]  # stale "applied" state dropped too


async def test_watchdog_slug_validation(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Work item 2.2, Core half: the slug schema regex, the installed-add-on
    requirement, and the not_supervisor refusal, end to end at the WS layer."""
    import voluptuous as vol

    from custom_components.ha_soc.websocket_api import ws_watchdog_set

    # Schema shape: the registered command schema refuses anything outside
    # ^[a-z0-9][a-z0-9_-]{0,63}$ for both override.slug and hard_limit.slug.
    schema = ws_watchdog_set._ws_schema
    for bad_slug in ("Bad Slug", "UPPER", "../etc", "a" * 65, "", "-leading", "a?b"):
        with pytest.raises(vol.Invalid):
            schema(
                {"id": 1, "type": "ha_soc/watchdog/set", "override": {"slug": bad_slug}}
            )
        with pytest.raises(vol.Invalid):
            schema(
                {
                    "id": 1,
                    "type": "ha_soc/watchdog/set",
                    "hard_limit": {"slug": bad_slug, "memory_mb": 512},
                }
            )
    schema(
        {
            "id": 1,
            "type": "ha_soc/watchdog/set",
            "override": {"slug": "a0d7b954_zwavejs", "action": "alert"},
        }
    )

    cfg = entry.runtime_data.store.data["resource_watchdog"]

    # Not a Supervisor install (the harness never is one at handler time):
    # storing an override or cap is refused as not_supervisor.
    connection = _connection(owner=True)
    ws_watchdog_set(
        hass, connection, {"id": 2, "override": {"slug": "ma", "action": "alert"}}
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1] == "not_supervisor"
    assert "ma" not in (cfg.get("overrides") or {})

    # Supervisor install, but the slug names no installed add-on: refused,
    # and nothing is stored.
    with patch(
        "custom_components.ha_soc.resource_watchdog.async_installed_addon_slugs",
        return_value={"core_mosquitto"},
    ):
        connection = _connection(owner=True)
        ws_watchdog_set(
            hass, connection, {"id": 3, "hard_limit": {"slug": "ma", "memory_mb": 512}}
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        connection.send_error.assert_called_once()
        assert connection.send_error.call_args[0][1] == "addon_not_installed"
        assert "ma" not in (cfg.get("hard_limits") or {})

        # The same slug installed: stored normally.
        connection = _connection(owner=True)
        ws_watchdog_set(
            hass,
            connection,
            {"id": 4, "hard_limit": {"slug": "core_mosquitto", "memory_mb": 512}},
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        connection.send_error.assert_not_called()
        assert cfg["hard_limits"]["core_mosquitto"] == {"memory_mb": 512, "cpus": None}
    entry.runtime_data.watchdog.async_stop()
