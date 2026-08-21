"""Config flow tests — the Bronze quality-scale `config-flow-test-coverage` rule."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

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
