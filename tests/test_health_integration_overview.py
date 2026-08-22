"""Real dynamic check of IntegrationHealth's issue-category classification."""
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.health import (
    COLLECTION_UNAVAILABLE_RATIO_THRESHOLD,
    ERROR_COUNT_ISSUE_THRESHOLD,
    ISSUE_CATEGORY_COLLECTION,
    ISSUE_CATEGORY_COMMUNICATION,
    ISSUE_CATEGORY_CREDENTIAL,
    ISSUE_CATEGORY_DEBUG_LOGGING,
    ISSUE_CATEGORY_DISABLED,
    ISSUE_CATEGORY_ERRORS,
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
        "disabled_by": None,
        "error_count_24h": 0,
        "unavailable_ratio": 0.0,
        "retry_transitions_24h": 0,
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _category(record: dict, reauth_entry_ids: set[str] = frozenset(), debug_domains: set[str] = frozenset()) -> str:
    return IntegrationHealth._issue_category(record, reauth_entry_ids, debug_domains)


def test_issue_category_priority_order() -> None:
    # Credential wins even over a failing state — a broken credential is
    # usually the root cause.
    assert (
        _category(_record(state=ConfigEntryState.SETUP_ERROR.value), reauth_entry_ids={"entry1"})
        == ISSUE_CATEGORY_CREDENTIAL
    )

    assert _category(_record(state=ConfigEntryState.SETUP_ERROR.value)) == ISSUE_CATEGORY_FAILING
    assert _category(_record(state=ConfigEntryState.MIGRATION_ERROR.value)) == ISSUE_CATEGORY_FAILING
    assert _category(_record(state=ConfigEntryState.SETUP_RETRY.value)) == ISSUE_CATEGORY_COMMUNICATION

    # Loaded + high unavailable ratio -> collection.
    over_threshold = COLLECTION_UNAVAILABLE_RATIO_THRESHOLD + 0.1
    assert (
        _category(_record(state=ConfigEntryState.LOADED.value, unavailable_ratio=over_threshold))
        == ISSUE_CATEGORY_COLLECTION
    )

    # Loaded + high error count (but not collection) -> errors.
    assert (
        _category(
            _record(
                state=ConfigEntryState.LOADED.value,
                error_count_24h=ERROR_COUNT_ISSUE_THRESHOLD + 1,
            )
        )
        == ISSUE_CATEGORY_ERRORS
    )
    # Collection still wins over errors when both apply.
    assert (
        _category(
            _record(
                state=ConfigEntryState.LOADED.value,
                unavailable_ratio=over_threshold,
                error_count_24h=ERROR_COUNT_ISSUE_THRESHOLD + 1,
            )
        )
        == ISSUE_CATEGORY_COLLECTION
    )

    # Debug logging -> flagged even when otherwise healthy.
    assert (
        _category(_record(state=ConfigEntryState.LOADED.value), debug_domains={"some_integration"})
        == ISSUE_CATEGORY_DEBUG_LOGGING
    )
    # But a real failure still outranks debug logging.
    assert (
        _category(_record(state=ConfigEntryState.SETUP_ERROR.value), debug_domains={"some_integration"})
        == ISSUE_CATEGORY_FAILING
    )

    # Disabled -> flagged, lowest priority.
    assert (
        _category(_record(state=ConfigEntryState.NOT_LOADED.value, disabled_by="user"))
        == ISSUE_CATEGORY_DISABLED
    )
    assert (
        _category(
            _record(state=ConfigEntryState.NOT_LOADED.value, disabled_by="user"),
            debug_domains={"some_integration"},
        )
        == ISSUE_CATEGORY_DEBUG_LOGGING
    )

    # Loaded + low unavailable ratio/error count -> no category at all.
    assert _category(_record(state=ConfigEntryState.LOADED.value, unavailable_ratio=0.01)) == ISSUE_CATEGORY_NONE


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
        ISSUE_CATEGORY_ERRORS,
        ISSUE_CATEGORY_DEBUG_LOGGING,
        ISSUE_CATEGORY_DISABLED,
    }

    assert await hass.config_entries.async_unload(entry.entry_id)
