"""Tests for the Technitium DNS Server direct API client (technitium.py).

Mirrors test_pihole.py's coverage shape:

1. **Host validation** — same http/https-only, no-userinfo, real-hostname
   rules as pihole._validate_host.
2. **Overview fetch** — token-as-query-param auth (no session lifecycle to
   pin, unlike Pi-hole's sid/X-FTL-SID flow), zone/record collection, and
   graceful degradation to reachable=False on error.

No real network call is ever made — aioclient_mock intercepts every
request the way test_pihole.py already does.
"""
from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import (
    CONF_TECHNITIUM_API_TOKEN,
)
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.technitium import (
    TechnitiumError,
    _normalize_record,
    _normalize_zone,
    _validate_host,
    async_technitium_overview,
)


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


@pytest.fixture
async def secrets(hass: HomeAssistant) -> HaSocSecretStore:
    data = HaSocSecretStore(hass)
    await data.async_load()
    return data


def test_validate_host_accepts_bare_hostname() -> None:
    _validate_host("dns.local")  # does not raise


def test_validate_host_rejects_bad_scheme() -> None:
    with pytest.raises(TechnitiumError):
        _validate_host("ftp://dns.local")


def test_validate_host_rejects_userinfo() -> None:
    with pytest.raises(TechnitiumError):
        _validate_host("https://user:pass@dns.local")


def test_validate_host_rejects_missing_hostname() -> None:
    with pytest.raises(TechnitiumError):
        _validate_host("https://")


def test_normalize_zone() -> None:
    row = _normalize_zone({"name": "example.com", "type": "Primary", "disabled": False})
    assert row == {"name": "example.com", "type": "Primary", "disabled": False}


def test_normalize_record() -> None:
    row = _normalize_record(
        {"name": "host.example.com", "type": "A", "ttl": 3600, "disabled": False, "rData": {"ipAddress": "1.2.3.4"}}
    )
    assert row == {
        "name": "host.example.com",
        "type": "A",
        "ttl": 3600,
        "disabled": False,
        "data": {"ipAddress": "1.2.3.4"},
    }


async def test_overview_unconfigured(hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore) -> None:
    out = await async_technitium_overview(hass, store, secrets)
    assert out["configured"] is False
    assert out["reachable"] is False


async def test_overview_token_rejected(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    store.async_update_settings(technitium_host="dns.local")
    await secrets.async_set(CONF_TECHNITIUM_API_TOKEN, "wrong-token")
    aioclient_mock.get(
        "https://dns.local/api/settings/get",
        status=401,
    )

    out = await async_technitium_overview(hass, store, secrets)
    assert out["configured"] is True
    assert out["reachable"] is False
    assert "rejected" in out["error"]


async def test_overview_full_snapshot(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    store.async_update_settings(technitium_host="dns.local")
    await secrets.async_set(CONF_TECHNITIUM_API_TOKEN, "good-token")

    aioclient_mock.get(
        "https://dns.local/api/settings/get",
        json={"response": {"enableBlocking": True}},
    )
    aioclient_mock.get(
        "https://dns.local/api/dashboard/stats/get",
        json={
            "response": {
                "stats": {"totalQueries": 1000, "totalBlocked": 100, "totalClients": 12},
                "topBlockedDomains": [{"name": "telemetry.example.com", "hits": 42}],
            }
        },
    )
    aioclient_mock.get(
        "https://dns.local/api/zones/list",
        json={"response": {"zones": [{"name": "home.arpa", "type": "Primary", "disabled": False}]}},
    )
    aioclient_mock.get(
        "https://dns.local/api/zones/records/get",
        json={
            "response": {
                "records": [
                    {"name": "host.home.arpa", "type": "A", "ttl": 3600, "disabled": False, "rData": {"ipAddress": "192.168.1.10"}}
                ]
            }
        },
    )
    aioclient_mock.get(
        "https://dns.local/api/logs/query",
        json={"response": {"entries": [{"qName": "ads.example.com"}]}},
    )

    out = await async_technitium_overview(hass, store, secrets)

    assert out["configured"] is True
    assert out["reachable"] is True
    assert out["error"] is None
    assert out["blocking_enabled"] is True
    assert out["summary"] == {
        "total": 1000,
        "blocked": 100,
        "percent_blocked": 10.0,
        "unique_domains": 12,
    }
    assert out["zones"] == [{"name": "home.arpa", "type": "Primary", "disabled": False}]
    assert "home.arpa" in out["records"]
    assert out["records"]["home.arpa"][0]["name"] == "host.home.arpa"
    assert out["top_blocked_domains"] == [{"domain": "telemetry.example.com", "count": 42}]
    assert out["recent_blocked"] == ["ads.example.com"]

    # Token rides as a query parameter on every call; no session/auth call is made.
    gets = [c for c in aioclient_mock.mock_calls if c[0] == "GET"]
    assert all("token=good-token" in str(c[1]) for c in gets)
