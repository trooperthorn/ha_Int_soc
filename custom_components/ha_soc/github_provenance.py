"""GitHub-derived provenance signals for the Integration Security view.

With no token configured nothing here runs and every signal stays "not
collected" (signals, slug hardening, and caching: docs/security.md).
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.util.dt as dt_util

from .const import (
    CONF_GITHUB_TOKEN,
    GITHUB_API_BASE,
    INTEGRATION_SECURITY_CACHE_TTL_HOURS,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
# Caps rate-budget use per refresh; the rest keep cached values until the next one.
_MAX_REPOS_PER_REFRESH = 60

# Dot-only components match this class and are rejected separately in _valid_repo_slug.
_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _valid_repo_slug(owner_repo: str) -> bool:
    """Whether the string is safe to place into the /repos/{owner}/{repo}
    path: allowed character set and neither component is a dot segment."""
    if not isinstance(owner_repo, str) or not _REPO_SLUG_RE.match(owner_repo):
        return False
    owner, repo = owner_repo.split("/", 1)
    return owner not in (".", "..") and repo not in (".", "..")


class _RateLimited(Exception):
    """GitHub answered 403 with X-RateLimit-Remaining: 0; the refresh must stop."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _fetch_repo_signals(
    session: aiohttp.ClientSession, owner_repo: str, secrets: HaSocSecretStore
) -> dict[str, Any] | None:
    """Fetch the repo object and the default-branch head commit for one repo.
    Returns a signal dict, or None on any error. The token is fetched here
    and goes out of scope when this function returns.
    """
    token = await secrets.async_get(CONF_GITHUB_TOKEN)
    if not token:
        # A token cleared mid-refresh leaves the rest "not collected".
        return None
    base = f"{GITHUB_API_BASE}/repos/{owner_repo}"
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(base, headers=_headers(token)) as resp:
                if resp.status == 404:
                    return {"error": "not_found"}
                if (
                    resp.status == 403
                    and resp.headers.get("X-RateLimit-Remaining") == "0"
                ):
                    raise _RateLimited
                resp.raise_for_status()
                repo = await resp.json()

            default_branch = repo.get("default_branch") or "main"
            verified = None
            try:
                commit_url = f"{base}/commits/{default_branch}"
                async with session.get(commit_url, headers=_headers(token)) as cresp:
                    if cresp.status == 200:
                        commit = await cresp.json()
                        verified = bool(
                            commit.get("commit", {})
                            .get("verification", {})
                            .get("verified", False)
                        )
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                verified = None  # signal 5 unavailable, others still returned

            # signal 2: is there at least one published release?
            has_release = None
            latest_tag = None
            try:
                async with session.get(
                    f"{base}/releases/latest", headers=_headers(token)
                ) as rresp:
                    if rresp.status == 200:
                        has_release = True
                        latest_tag = (await rresp.json()).get("tag_name")
                    elif rresp.status == 404:
                        has_release = False
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                has_release = None

    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
        # ValueError covers json.JSONDecodeError so one bad body does not abort the loop.
        _LOGGER.warning("GitHub provenance lookup failed for %s: %s", owner_repo, err)
        return None

    return {
        "stars": repo.get("stargazers_count"),
        "forks": repo.get("forks_count"),
        "archived": bool(repo.get("archived", False)),
        "pushed_at": repo.get("pushed_at"),
        "commit_verified": verified,
        "has_release": has_release,
        "latest_release_tag": latest_tag,
        "collected_at": dt_util.utcnow().isoformat(),
    }


async def async_refresh_github_signals(
    hass: HomeAssistant,
    store: HaSocData,
    repo_urls: list[str],
    secrets: HaSocSecretStore,
) -> dict[str, Any]:
    """Refresh cached GitHub signals for the given owner/repo list. Returns
    a summary; the per-repo data lands in the store cache."""
    # Presence check only; the value is fetched per repo and never held across the loop.
    if not await secrets.async_get(CONF_GITHUB_TOKEN):
        return {"ok": False, "reason": "no_github_token", "refreshed": 0}

    unique = [r for r in dict.fromkeys(repo_urls) if r]
    invalid = [r for r in unique if not _valid_repo_slug(r)]
    if invalid:
        # Only slug names are logged; they are the values being refused a request.
        _LOGGER.warning(
            "GitHub provenance refresh skipped %d invalid repo slug(s): %s",
            len(invalid),
            ", ".join(repr(r) for r in invalid[:10]),
        )
    unique = [r for r in unique if _valid_repo_slug(r)]
    dropped = max(0, len(unique) - _MAX_REPOS_PER_REFRESH)
    unique = unique[:_MAX_REPOS_PER_REFRESH]

    session = async_get_clientsession(hass)
    cache = dict(store.data["integration_security"].get("github") or {})
    now = dt_util.utcnow()
    ttl = timedelta(hours=INTEGRATION_SECURITY_CACHE_TTL_HOURS)
    refreshed = 0
    fresh_skipped = 0
    rate_limited = False
    for owner_repo in unique:
        cached = cache.get(owner_repo)
        if cached is not None:
            collected_at = dt_util.parse_datetime(str(cached.get("collected_at") or ""))
            if collected_at is not None and now - collected_at < ttl:
                # Cache entries younger than the TTL are kept.
                fresh_skipped += 1
                continue
        try:
            signals = await _fetch_repo_signals(session, owner_repo, secrets)
        except _RateLimited:
            rate_limited = True
            _LOGGER.warning(
                "GitHub provenance refresh stopped: the API rate limit is "
                "exhausted (403 with X-RateLimit-Remaining: 0)"
            )
            break
        if signals is not None:
            cache[owner_repo] = signals
            refreshed += 1

    store.data["integration_security"]["github"] = cache
    store.data["integration_security"]["refreshed_at"] = dt_util.utcnow().isoformat()
    store.async_schedule_save()

    if dropped:
        _LOGGER.info(
            "GitHub provenance refresh capped at %d repos; %d not refreshed this pass.",
            _MAX_REPOS_PER_REFRESH,
            dropped,
        )
    result: dict[str, Any] = {
        "ok": not rate_limited,
        "refreshed": refreshed,
        "skipped": dropped + len(invalid),
        "cache_fresh": fresh_skipped,
        "invalid_slugs": len(invalid),
    }
    if rate_limited:
        result["reason"] = "rate_limited"
    return result
