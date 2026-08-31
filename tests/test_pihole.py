"""Tests for the Pi-hole v6 direct API client (pihole.py).

Two concerns are pinned here:

1. **The auth session lifecycle** — POST /auth to get a sid, that sid riding
   on X-FTL-SID for every read, and DELETE /auth on the way out (success or
   failure), matching the verified pi-hole/FTL OpenAPI auth flow.
2. **Normalization** — group/client shaping and the IoT-CIDR client-group
   scoping check, which network_security.py's Pi-hole findings depend on.

No real network call is ever made — aioclient_mock intercepts every
request the way test_integration_security.py already does for the GitHub
client.
"""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.const import CONF_PIHOLE_API_KEY, CONF_PIHOLE_HOST, CONF_PIHOLE_IOT_CIDR
from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.pihole import (
    PiHoleError,
    _client_matches_cidr,
    _normalize_client,
    _normalize_group,
    async_pihole_overview,
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


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_normalize_group() -> None:
    row = _normalize_group({"id": 1, "name": "IoT", "enabled": True, "comment": "iot devices"})
    assert row == {"id": 1, "name": "IoT", "enabled": True, "comment": "iot devices"}


def test_normalize_client_flags_default_group_only() -> None:
    names = {0: "Default", 3: "IoT"}
    scoped = _normalize_client({"client": "192.168.50.10", "groups": [3]}, names)
    assert scoped["group_names"] == ["IoT"]
    assert scoped["default_group_only"] is False

    unscoped = _normalize_client({"client": "192.168.50.11", "groups": [0]}, names)
    assert unscoped["default_group_only"] is True


def test_client_matches_cidr() -> None:
    assert _client_matches_cidr("192.168.50.10", "192.168.50.0/24") is True
    assert _client_matches_cidr("192.168.60.10", "192.168.50.0/24") is False
    # A MAC/hostname/interface client id never matches an IP-shaped CIDR.
    assert _client_matches_cidr("aa:bb:cc:dd:ee:ff", "192.168.50.0/24") is False
    assert _client_matches_cidr(":eth0", "192.168.50.0/24") is False


# ---------------------------------------------------------------------------
# async_pihole_overview
# ---------------------------------------------------------------------------


async def test_overview_unconfigured(hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore) -> None:
    out = await async_pihole_overview(hass, store, secrets)
    assert out["configured"] is False
    assert out["reachable"] is False


async def test_overview_auth_rejected(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    store.async_update_settings(pihole_host="pi.hole")
    await secrets.async_set(CONF_PIHOLE_API_KEY, "wrong-password")
    aioclient_mock.post(
        "https://pi.hole/api/auth",
        json={"session": {"valid": False, "sid": None, "message": "invalid password"}},
    )

    out = await async_pihole_overview(hass, store, secrets)
    assert out["configured"] is True
    assert out["reachable"] is False
    assert "invalid password" in out["error"]


async def test_overview_full_snapshot_and_logout(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    store.async_update_settings(pihole_host="pi.hole", pihole_iot_cidr="192.168.50.0/24")
    await secrets.async_set(CONF_PIHOLE_API_KEY, "app-password")

    aioclient_mock.post(
        "https://pi.hole/api/auth",
        json={"session": {"valid": True, "sid": "sid-123", "validity": 1800}},
    )
    aioclient_mock.get("https://pi.hole/api/dns/blocking", json={"blocking": "enabled"})
    aioclient_mock.get(
        "https://pi.hole/api/stats/summary",
        json={
            "queries": {
                "total": 1000,
                "blocked": 120,
                "percent_blocked": 12.0,
                "unique_domains": 300,
            }
        },
    )
    aioclient_mock.get(
        "https://pi.hole/api/groups",
        json={"groups": [{"id": 0, "name": "Default", "enabled": True}, {"id": 5, "name": "IoT", "enabled": True}]},
    )
    aioclient_mock.get(
        "https://pi.hole/api/clients",
        json={
            "clients": [
                {"client": "192.168.50.0/24", "groups": [5]},
                {"client": "192.168.1.10", "groups": [0]},
            ]
        },
    )
    aioclient_mock.get(
        "https://pi.hole/api/stats/top_domains?blocked=true&count=15",
        json={"domains": [{"domain": "telemetry.example.com", "count": 42}]},
    )
    aioclient_mock.get(
        "https://pi.hole/api/stats/recent_blocked?count=15",
        json={"blocked": ["ads.example.com"]},
    )
    aioclient_mock.delete("https://pi.hole/api/auth")

    out = await async_pihole_overview(hass, store, secrets)

    assert out["configured"] is True
    assert out["reachable"] is True
    assert out["error"] is None
    assert out["blocking_enabled"] is True
    assert out["summary"] == {
        "total": 1000,
        "blocked": 120,
        "percent_blocked": 12.0,
        "unique_domains": 300,
    }
    assert {g["name"] for g in out["groups"]} == {"Default", "IoT"}
    assert out["iot_cidr"] == "192.168.50.0/24"
    assert out["iot_clients_scoped"] is True  # the /24 entry has a non-default group
    assert out["top_blocked_domains"] == [{"domain": "telemetry.example.com", "count": 42}]
    assert out["recent_blocked"] == ["ads.example.com"]

    # The session was created and explicitly torn down, sid riding on the
    # X-FTL-SID header for the logout call same as every other read.
    posts = [c for c in aioclient_mock.mock_calls if c[0] == "POST"]
    deletes = [c for c in aioclient_mock.mock_calls if c[0] == "DELETE"]
    assert len(posts) == 1
    assert len(deletes) == 1
    _method, _url, _data, delete_headers = deletes[0]
    assert delete_headers.get("X-FTL-SID") == "sid-123"


async def test_overview_iot_cidr_with_no_matching_client_is_unscoped(
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore, aioclient_mock
) -> None:
    """No client entry at all for the IoT subnet means every device on it
    falls through to Pi-hole's global Default group — reported as
    unscoped, the same as an entry that explicitly names only group 0."""
    store.async_update_settings(pihole_host="pi.hole", pihole_iot_cidr="192.168.50.0/24")
    await secrets.async_set(CONF_PIHOLE_API_KEY, "app-password")

    aioclient_mock.post(
        "https://pi.hole/api/auth", json={"session": {"valid": True, "sid": "sid-1", "validity": 1800}}
    )
    aioclient_mock.get("https://pi.hole/api/dns/blocking", json={"blocking": "enabled"})
    aioclient_mock.get("https://pi.hole/api/stats/summary", json={"queries": {}})
    aioclient_mock.get("https://pi.hole/api/groups", json={"groups": []})
    aioclient_mock.get("https://pi.hole/api/clients", json={"clients": []})
    aioclient_mock.get(
        "https://pi.hole/api/stats/top_domains?blocked=true&count=15", json={"domains": []}
    )
    aioclient_mock.get(
        "https://pi.hole/api/stats/recent_blocked?count=15", json={"blocked": []}
    )
    aioclient_mock.delete("https://pi.hole/api/auth")

    out = await async_pihole_overview(hass, store, secrets)
    assert out["iot_clients_scoped"] is False
