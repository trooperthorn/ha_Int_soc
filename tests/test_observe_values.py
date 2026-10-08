"""End to end value checks for the Observe payload (audit probes p03 and p09).

The mapper unit tests live in test_otlp_mapper.py. These run the real health and
containers code and feed their output to the mapper, so a change in either producer
that breaks a value in the payload fails here.
"""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import otlp_mapper
from custom_components.ha_soc.health import IntegrationHealth
from custom_components.ha_soc.store import HaSocData

# Private config directory per test; see tests/conftest.py. The store writes its file there.
ISOLATED_CONFIG_DIR = True


async def test_three_entries_of_one_domain_push_the_real_error_count(hass) -> None:
    store = HaSocData(hass)
    await store.async_load()
    health = IntegrationHealth(hass, store)
    entries = []
    for i in range(3):
        entry = MockConfigEntry(domain="esphome", title=f"esp{i}", data={})
        entry.add_to_hass(hass)
        entries.append(entry)
    await health._async_refresh_attribution_maps()
    for entry in entries:
        store.data["integration_health"][entry.entry_id] = health._build_health_record(entry)
    for _ in range(5):
        health._handle_log_record("homeassistant.components.esphome")
    for entry in entries:
        store.data["integration_health"][entry.entry_id]["state"] = "setup_retry"

    overview = await health.async_integration_overview()
    assert [r["error_count_24h"] for r in overview["integrations"]] == [5, 5, 5]
    request = otlp_mapper.build_metrics(
        otlp_mapper.Identity("h"), {"integration_overview": overview}, 1.0
    )
    errors = [
        dp["asDouble"]
        for rm in request["resourceMetrics"]
        for sm in rm["scopeMetrics"]
        for m in sm["metrics"]
        if m["name"] == "observe.ha.integration.errors"
        for dp in m["gauge"]["dataPoints"]
    ]
    assert errors == [5.0]
