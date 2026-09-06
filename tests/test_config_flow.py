"""Config flow tests — the Bronze quality-scale `config-flow-test-coverage` rule."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc.const import DOMAIN


async def test_single_instance(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"

    result2 = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result2["type"] == "create_entry"
    assert result2["title"] == "HA SOC"
    assert result2["data"] == {}

    result3 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result3["type"] == "abort"
    assert result3["reason"] == "single_instance_allowed"


async def test_options_flow_submit_reloads_entry(hass: HomeAssistant) -> None:
    """Options stay empty, so core would never reload on its own; the flow schedules it."""
    entry = MockConfigEntry(domain=DOMAIN, title="HA SOC", data={})
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"

    with patch.object(hass.config_entries, "async_schedule_reload") as schedule_reload:
        result2 = await hass.config_entries.options.async_configure(result["flow_id"], {})

    assert result2["type"] == "create_entry"
    assert result2["data"] == {}
    assert entry.options == {}
    schedule_reload.assert_called_once_with(entry.entry_id)
