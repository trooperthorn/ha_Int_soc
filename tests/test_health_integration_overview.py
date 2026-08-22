"""Real dynamic check of IntegrationHealth's issue-category classification."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import (
    COLLECTION_UNAVAILABLE_RATIO_THRESHOLD,
    ISSUE_CATEGORY_COLLECTION,
    ISSUE_CATEGORY_COMMUNICATION,
    ISSUE_CATEGORY_CREDENTIAL,
    ISSUE_CATEGORY_FAILING,
    ISSUE_CATEGORY_NONE,
    IntegrationHealth,
)


def _record(**overrides) -> dict:
    base = {
        "entry_id": "entry1",
        "domain": "some_integration",
        "title": "Some Integration",
        "state": ConfigEntryState.LOADED.value,
        "reason": None,
        "error_count_24h": 0,
        "unavailable_ratio": 0.0,
        "retry_transitions_24h": 0,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_issue_category_priority_order() -> None:
    # Credential wins even over a failing state — a broken credential is
    # usually the root cause.
    assert (
        IntegrationHealth._issue_category(
            _record(state=ConfigEntryState.SETUP_ERROR.value), {"entry1"}
        )
        == ISSUE_CATEGORY_CREDENTIAL
    )

    assert (
        IntegrationHealth._issue_category(_record(state=ConfigEntryState.SETUP_ERROR.value), set())
        == ISSUE_CATEGORY_FAILING
    )
    assert (
        IntegrationHealth._issue_category(_record(state=ConfigEntryState.MIGRATION_ERROR.value), set())
        == ISSUE_CATEGORY_FAILING
    )
    assert (
        IntegrationHealth._issue_category(_record(state=ConfigEntryState.SETUP_RETRY.value), set())
        == ISSUE_CATEGORY_COMMUNICATION
    )

    # Loaded + high unavailable ratio -> collection.
    over_threshold = COLLECTION_UNAVAILABLE_RATIO_THRESHOLD + 0.1
    assert (
        IntegrationHealth._issue_category(
            _record(state=ConfigEntryState.LOADED.value, unavailable_ratio=over_threshold), set()
        )
        == ISSUE_CATEGORY_COLLECTION
    )

    # Loaded + low unavailable ratio -> no category at all.
    assert (
        IntegrationHealth._issue_category(
            _record(state=ConfigEntryState.LOADED.value, unavailable_ratio=0.01), set()
        )
        == ISSUE_CATEGORY_NONE
    )


async def test_integration_overview_excludes_healthy_entries(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    overview = await entry.runtime_data.health.async_integration_overview()
    # Our own freshly-loaded entry is healthy — it must not appear.
    assert all(i["entry_id"] != entry.entry_id for i in overview["integrations"])
    assert set(overview["category_counts"]) == {
        ISSUE_CATEGORY_CREDENTIAL,
        ISSUE_CATEGORY_FAILING,
        ISSUE_CATEGORY_COMMUNICATION,
        ISSUE_CATEGORY_COLLECTION,
    }

    assert await hass.config_entries.async_unload(entry.entry_id)
