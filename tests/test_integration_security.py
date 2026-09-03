"""Tests for the Integration Security (provenance) view.

Two modules under test: integration_security.py (the local-signals overview
builder) and github_provenance.py (the optional GitHub client). The one rule
the whole feature enforces is that GitHub-derived signals are NEVER guessed:
with no token nothing hits the network and every ``github`` block is None.
These tests pin exactly that, plus the store-cache round-trip and the two
WebSocket handlers — never making a real network call (``_fetch_repo_signals``
is always patched).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    CONF_GITHUB_TOKEN,
    DOMAIN,
    INTEGRATION_TIER_CORE,
    INTEGRATION_TIER_CUSTOM,
)
from custom_components.ha_soc.github_provenance import async_refresh_github_signals
from custom_components.ha_soc.integration_security import (
    async_integration_security_overview,
)
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData

# A stand-in for what github_provenance._fetch_repo_signals returns for one
# repo, shape mirrors the real signal dict, values are arbitrary.
FAKE_SIGNALS = {
    "stars": 42,
    "forks": 3,
    "archived": False,
    "pushed_at": "2026-01-02T03:04:05Z",
    "commit_verified": True,
    "has_release": True,
    "latest_release_tag": "v1.0.0",
    "collected_at": "2026-08-23T00:00:00+00:00",
}


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


@pytest.fixture
async def secrets(hass: HomeAssistant) -> HaSocSecretStore:
    # The private secret store is where the GitHub token lives since SEC-1;
    # the overview and refresh functions take it explicitly.
    data = HaSocSecretStore(hass)
    await data.async_load()
    return data


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    """A live ha_soc config entry — this repo's own (custom) integration.

    Setting one up puts "ha_soc" into config_entries, which is how it shows
    up as a row in the overview (the harness's config dir has no
    custom_components/ listing of its own). It also wires up
    entry.runtime_data.store, the store the WS handlers read.
    """
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _owner_connection() -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="u1")
    return connection


async def test_overview_shape_and_no_github_without_token(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    secrets = entry.runtime_data.secrets
    assert await secrets.async_get(CONF_GITHUB_TOKEN) is None  # no token configured

    overview = await async_integration_security_overview(hass, store, secrets)

    assert set(overview) == {
        "github_configured",
        "hacs_installed",
        "hacs_source_introspectable",
        "tier_counts",
        "integrations",
    }
    assert overview["github_configured"] is False
    assert set(overview["tier_counts"]) == {
        INTEGRATION_TIER_CORE,
        "hacs",
        INTEGRATION_TIER_CUSTOM,
    }
    assert isinstance(overview["integrations"], list)
    assert overview["integrations"]  # at least the ha_soc row is present
    # With no token, every row's GitHub block is None ("not collected"),
    # never a guess.
    assert all(row["github"] is None for row in overview["integrations"])


async def test_ha_soc_itself_is_a_custom_row(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    overview = await async_integration_security_overview(
        hass, entry.runtime_data.store, entry.runtime_data.secrets
    )

    row = next(r for r in overview["integrations"] if r["domain"] == DOMAIN)
    assert row["tier"] == INTEGRATION_TIER_CUSTOM
    assert row["is_custom"] is True
    # The check runs against the harness config dir, which has no LICENSE, so False here and True on a real install.
    assert row["license_present"] is False


async def test_core_rows_are_consistent(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    overview = await async_integration_security_overview(
        hass, entry.runtime_data.store, entry.runtime_data.secrets
    )

    core_rows = [r for r in overview["integrations"] if r["tier"] == INTEGRATION_TIER_CORE]
    # The harness may surface zero core rows; this stays robust to that. Any
    # that ARE present must be internally consistent.
    for row in core_rows:
        assert row["is_custom"] is False
        assert row["license_present"] is True


async def test_refresh_without_token_is_noop(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    assert await secrets.async_get(CONF_GITHUB_TOKEN) is None

    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(),
    ) as mock_fetch:
        result = await async_refresh_github_signals(hass, store, ["owner/repo"], secrets)

    assert result == {"ok": False, "reason": "no_github_token", "refreshed": 0}
    mock_fetch.assert_not_called()  # never reached the network layer


async def test_refresh_with_token_caches_and_merges(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    store = entry.runtime_data.store
    secrets = entry.runtime_data.secrets
    await secrets.async_set(CONF_GITHUB_TOKEN, "ghp_fake_token")

    # Discover the ha_soc row's real repo_url (from its manifest) so the
    # cache we write actually merges back onto that row.
    pre = await async_integration_security_overview(hass, store, secrets)
    ha_soc_row = next(r for r in pre["integrations"] if r["domain"] == DOMAIN)
    repo_url = ha_soc_row["repo_url"]
    assert repo_url  # ha_soc's manifest points at a github repo

    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(return_value=dict(FAKE_SIGNALS)),
    ) as mock_fetch:
        result = await async_refresh_github_signals(hass, store, [repo_url], secrets)

    mock_fetch.assert_awaited_once()
    assert result["ok"] is True
    assert result["refreshed"] == 1
    assert result["skipped"] == 0

    # Cache landed in the store keyed by owner/repo, and refreshed_at is set.
    cache = store.data["integration_security"]["github"]
    assert cache[repo_url] == FAKE_SIGNALS
    assert store.data["integration_security"]["refreshed_at"] is not None

    # A subsequent overview merges the cached signals onto the matching row.
    post = await async_integration_security_overview(hass, store, secrets)
    merged_row = next(r for r in post["integrations"] if r["domain"] == DOMAIN)
    assert merged_row["github"] == FAKE_SIGNALS


async def test_ws_list_returns_overview(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from custom_components.ha_soc.websocket_api import ws_integration_security_list

    connection = _owner_connection()
    ws_integration_security_list(hass, connection, {"id": 1})
    # async_response schedules the handler as a background task, which
    # async_block_till_done only awaits when asked to.
    await hass.async_block_till_done(wait_background_tasks=True)

    connection.send_error.assert_not_called()
    result = connection.send_result.call_args[0][1]
    assert "integrations" in result
    assert result["github_configured"] is False


async def test_ws_refresh_without_token_reports_noop(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    from custom_components.ha_soc.websocket_api import ws_integration_security_refresh

    connection = _owner_connection()
    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(),
    ) as mock_fetch:
        ws_integration_security_refresh(hass, connection, {"id": 1})
        await hass.async_block_till_done(wait_background_tasks=True)

    connection.send_error.assert_not_called()
    result = connection.send_result.call_args[0][1]
    assert result["ok"] is False
    assert result["reason"] == "no_github_token"
    mock_fetch.assert_not_called()


# The custom_components disk scan must never run on the event loop (regression for a real blocking-call log).


async def test_custom_components_scan_runs_in_executor(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    import threading

    from custom_components.ha_soc import integration_security as mod

    loop_thread = threading.get_ident()
    scan_threads: list[int] = []
    real_scan = mod._scan_custom_components_sync

    def _spy(root: str):
        scan_threads.append(threading.get_ident())
        return real_scan(root)

    # patch with new= (a bare function), not side_effect=: the harness runs Mock targets inline on the loop.
    with patch.object(mod, "_scan_custom_components_sync", new=_spy):
        await async_integration_security_overview(
            hass, entry.runtime_data.store, entry.runtime_data.secrets
        )

    assert scan_threads, "the custom_components scan was never invoked"
    assert all(tid != loop_thread for tid in scan_threads), (
        "disk scan executed on the event-loop thread — must go through "
        "async_add_executor_job"
    )


def test_repo_slug_validation() -> None:
    from custom_components.ha_soc.github_provenance import _valid_repo_slug

    assert _valid_repo_slug("trooperthorn/ha_Int_soc") is True
    assert _valid_repo_slug("owner-1/repo.name_2") is True
    # Dot segments are the token-redirection vector (yarl collapses them
    # before sending), so they are rejected even though the character
    # class alone would admit them.
    assert _valid_repo_slug("../../user/repos") is False
    assert _valid_repo_slug("../repo") is False
    assert _valid_repo_slug("owner/..") is False
    assert _valid_repo_slug("owner/.") is False
    # Extra path components, spaces, and empty parts never pass.
    assert _valid_repo_slug("a/b/c") is False
    assert _valid_repo_slug("a b/c") is False
    assert _valid_repo_slug("/repo") is False
    assert _valid_repo_slug("owner/") is False
    assert _valid_repo_slug("") is False
    assert _valid_repo_slug(None) is False  # type: ignore[arg-type]


async def test_refresh_skips_invalid_slugs(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    await secrets.async_set(CONF_GITHUB_TOKEN, "ghp_fake_token")
    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(return_value=dict(FAKE_SIGNALS)),
    ) as mock_fetch:
        result = await async_refresh_github_signals(
            hass, store, ["../../user/repos", "good/repo"], secrets
        )
    mock_fetch.assert_awaited_once()
    assert mock_fetch.call_args[0][1] == "good/repo"
    assert result["refreshed"] == 1
    assert result["invalid_slugs"] == 1
    assert "../../user/repos" not in store.data["integration_security"]["github"]


async def test_github_refresh_survives_bad_json(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    """One repository answering garbage instead of JSON leaves that repo
    "not collected" and the rest of the refresh completes."""
    await secrets.async_set(CONF_GITHUB_TOKEN, "ghp_fake_token")
    aioclient_mock.get(
        "https://api.github.com/repos/bad/repo",
        text="<html>not json</html>",
    )
    aioclient_mock.get(
        "https://api.github.com/repos/good/repo",
        json={"default_branch": "main", "stargazers_count": 1, "forks_count": 0,
              "archived": False, "pushed_at": "2026-01-01T00:00:00Z"},
    )
    aioclient_mock.get(
        "https://api.github.com/repos/good/repo/commits/main",
        json={"commit": {"verification": {"verified": True}}},
    )
    aioclient_mock.get(
        "https://api.github.com/repos/good/repo/releases/latest",
        json={"tag_name": "v1.0.0"},
    )

    result = await async_refresh_github_signals(
        hass, store, ["bad/repo", "good/repo"], secrets
    )

    assert result["ok"] is True
    assert result["refreshed"] == 1
    cache = store.data["integration_security"]["github"]
    assert "bad/repo" not in cache
    assert cache["good/repo"]["stars"] == 1
    assert cache["good/repo"]["commit_verified"] is True


async def test_github_cache_ttl_honored(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> None:
    import homeassistant.util.dt as dt_util
    from datetime import timedelta

    await secrets.async_set(CONF_GITHUB_TOKEN, "ghp_fake_token")
    fresh_at = (dt_util.utcnow() - timedelta(hours=1)).isoformat()
    store.data["integration_security"]["github"]["cached/repo"] = {
        **FAKE_SIGNALS, "collected_at": fresh_at,
    }

    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(return_value=dict(FAKE_SIGNALS)),
    ) as mock_fetch:
        result = await async_refresh_github_signals(hass, store, ["cached/repo"], secrets)
    mock_fetch.assert_not_called()
    assert result["refreshed"] == 0
    assert result["cache_fresh"] == 1

    # Past the TTL the same repo is re-fetched.
    stale_at = (dt_util.utcnow() - timedelta(hours=25)).isoformat()
    store.data["integration_security"]["github"]["cached/repo"]["collected_at"] = stale_at
    with patch(
        "custom_components.ha_soc.github_provenance._fetch_repo_signals",
        new=AsyncMock(return_value=dict(FAKE_SIGNALS)),
    ) as mock_fetch:
        result = await async_refresh_github_signals(hass, store, ["cached/repo"], secrets)
    mock_fetch.assert_awaited_once()
    assert result["refreshed"] == 1


async def test_github_refresh_stops_on_rate_limit(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    await secrets.async_set(CONF_GITHUB_TOKEN, "ghp_fake_token")
    aioclient_mock.get(
        "https://api.github.com/repos/first/repo",
        status=403,
        headers={"X-RateLimit-Remaining": "0"},
        json={"message": "rate limited"},
    )

    result = await async_refresh_github_signals(
        hass, store, ["first/repo", "second/repo"], secrets
    )

    assert result["ok"] is False
    assert result["reason"] == "rate_limited"
    assert result["refreshed"] == 0
    # The loop stopped instead of burning the quota on second/repo.
    assert aioclient_mock.call_count == 1


def test_scan_custom_components_sync_behavior(tmp_path) -> None:
    """The scan itself: manifest-bearing dirs only, dot/underscore skipped,
    license presence computed in the same pass."""
    from custom_components.ha_soc.integration_security import (
        _scan_custom_components_sync,
    )

    root = tmp_path / "custom_components"
    (root / "with_license").mkdir(parents=True)
    (root / "with_license" / "manifest.json").write_text("{}")
    (root / "with_license" / "LICENSE").write_text("MIT")
    (root / "no_license").mkdir()
    (root / "no_license" / "manifest.json").write_text("{}")
    (root / "not_an_integration").mkdir()  # no manifest -> skipped
    (root / "__pycache__").mkdir()  # underscore prefix -> skipped

    domains, licenses = _scan_custom_components_sync(str(root))
    assert domains == ["no_license", "with_license"]
    assert licenses == {"no_license": False, "with_license": True}

    # Missing root: empty result, never an exception.
    assert _scan_custom_components_sync(str(tmp_path / "nope")) == ([], {})
