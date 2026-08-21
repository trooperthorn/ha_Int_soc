"""Full setup/unload integration test — exercises every manager together."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN


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
