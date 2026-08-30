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


async def test_entry_options_never_reach_settings_and_are_scrubbed(
    hass: HomeAssistant,
) -> None:
    """The entry.options mirror and its seed path are gone (SEC-2): a
    legacy options blob neither leaks into settings nor survives setup.
    It is rewritten to {} once, so the world-readable config-entries file
    stops carrying a copy of HA SOC's configuration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        title="HA SOC",
        options={"access_level": ACCESS_LEVEL_OWNER_AND_ADMINS},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Settings keep their own default; the stale options value is ignored.
    assert entry.runtime_data.store.settings["access_level"] == ACCESS_LEVEL_OWNER_ONLY
    # And the legacy mirror itself was emptied.
    assert entry.options == {}

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
