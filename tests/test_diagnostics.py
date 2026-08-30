"""Diagnostics must be attachable to a public issue without leaking anything.

The assertions here are the redaction contract, not the exact layout: no
secret value, no UniFi host address, and no row-level user or audit content
may ever appear in the output, while presence flags and counts must.
"""
import json

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN, REDACTED_PLACEHOLDER
from custom_components.ha_soc.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics_redacts_secrets_and_hosts(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = entry.runtime_data.store
    store.async_update_settings(
        github_token="ghp_supersecret123",
        unifi_network_host="192.168.30.2",
        unifi_network_api_key="unifi-key-value",
    )

    diag = await async_get_config_entry_diagnostics(hass, entry)

    dumped = json.dumps(diag)
    assert "ghp_supersecret123" not in dumped
    assert "192.168.30.2" not in dumped
    assert "unifi-key-value" not in dumped

    settings = diag["settings"]
    assert settings["github_token"] == REDACTED_PLACEHOLDER
    assert settings["github_token_set"] is True
    assert settings["unifi_network_host"] == REDACTED_PLACEHOLDER
    assert settings["unifi_network_host_set"] is True
    assert settings["nvd_api_key"] is None
    assert settings["nvd_api_key_set"] is False

    # Tables come back as counts only; the settings table is excluded
    # because it is reported (masked) under its own key.
    counts = diag["store_table_counts"]
    assert "settings" not in counts
    assert isinstance(counts["detections"], int)

    assert diag["host_probe"]["reported"] is False
    assert diag["firewall"]["addon_paired"] is False
    assert "enabled" in diag["resource_watchdog"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
