"""Full setup/unload integration test — exercises every manager together."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    DOMAIN,
)


async def test_full_setup_and_unload(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data is not None
    assert hass.states.get("sensor.ha_soc_security_posture_score") is not None
    assert hass.states.get("sensor.ha_soc_open_detections") is not None
    assert hass.states.get("sensor.ha_soc_users_at_risk") is not None
    assert hass.states.get("binary_sensor.ha_soc_suspicious_activity") is not None

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_first_load_seeds_settings_from_entry_options(hass: HomeAssistant) -> None:
    """A pre-existing options-flow save must take effect on first-ever load."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        title="HA SOC",
        options={"access_level": ACCESS_LEVEL_OWNER_AND_ADMINS},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.store.settings["access_level"] == ACCESS_LEVEL_OWNER_AND_ADMINS


async def test_stale_entry_options_never_reseed_after_first_load(hass: HomeAssistant) -> None:
    """Once the store has been saved once, entry.options must never clobber it again.

    Exercises the seeding helper directly at the HaSocData level rather
    than through a second full config-entry setup — reloading this
    integration's panel registration within a single test HA instance hits
    an unrelated aiohttp "route already registered" limitation in
    panel.py that has nothing to do with the seeding logic under test.
    """
    from custom_components.ha_soc import _seed_settings_from_options_once
    from custom_components.ha_soc.store import HaSocData

    store = HaSocData(hass)
    had_stored_data = await store.async_load()
    _seed_settings_from_options_once(
        store,
        {"access_level": ACCESS_LEVEL_OWNER_AND_ADMINS},
        had_stored_data=had_stored_data,
    )
    assert store.settings["access_level"] == ACCESS_LEVEL_OWNER_AND_ADMINS

    # Simulate the user flipping the setting from the panel's Settings tab
    # (task 30) — only the live store changes, entry.options is left stale.
    store.async_update_settings(access_level=ACCESS_LEVEL_OWNER_ONLY)
    await store.async_save_now()

    # Reload from disk (simulating a restart) and run the seed step again
    # with the same stale entry.options — it must be a no-op this time.
    store2 = HaSocData(hass)
    had_stored_data2 = await store2.async_load()
    assert had_stored_data2 is True
    _seed_settings_from_options_once(
        store2,
        {"access_level": ACCESS_LEVEL_OWNER_AND_ADMINS},
        had_stored_data=had_stored_data2,
    )

    assert store2.settings["access_level"] == ACCESS_LEVEL_OWNER_ONLY
