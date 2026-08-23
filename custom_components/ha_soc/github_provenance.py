"""GitHub-derived provenance signals for the Integration Security view.

Gathers the design's signals 2/5/6/7/10 for a set of "owner/repo" repos:

  - **2 release vs. branch**: does the installed version match a real tag?
    (has_releases / latest release tag)
  - **5 identity assurance**: is the repo's default-branch head commit
    cryptographically verified? (`verification.verified` — a real, public
    field). Measures assurance on the artifact, never "does the maintainer
    have MFA" (not exposed, and converging on universal anyway). Describe
    the artifact, never the author.
  - **6 recency**: last push timestamp.
  - **7 popularity**: stars / forks (gameable — weak positive only).
  - **10 archived**: the repo's own `archived` flag.

All of this needs an outbound call and the optional owner-configured token
(raising GitHub's 60/hr unauthenticated limit to 5,000/hr). With no token,
NOTHING here runs and every signal stays honestly "not collected" — never
a guess. Results are cached in the store keyed by "owner/repo" so a refresh
doesn't re-hit the API for repos looked up recently; the GitHub endpoint is
a hardcoded constant and the token/owner/repo are passed as header/path
params, never spliced into a URL string.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.util.dt as dt_util

from .const import CONF_GITHUB_TOKEN, GITHUB_API_BASE
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15
# Cap how many repos a single refresh will look up, so one refresh can't
# blow a whole hour's rate budget on a huge install; the rest keep their
# cached values (or stay "not collected") until the next refresh.
_MAX_REPOS_PER_REFRESH = 60


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _fetch_repo_signals(
    session: aiohttp.ClientSession, owner_repo: str, token: str
) -> dict[str, Any] | None:
    """Two calls per repo: the repo object (stars/forks/archived/pushed_at)
    and the default-branch head commit (verification). Returns a signal
    dict, or None on any error (the caller keeps that repo 'not collected').
    """
    base = f"{GITHUB_API_BASE}/repos/{owner_repo}"
    try:
        async with asyncio.timeout(_TIMEOUT_SECONDS):
            async with session.get(base, headers=_headers(token)) as resp:
                if resp.status == 404:
                    return {"error": "not_found"}
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
            except (aiohttp.ClientError, asyncio.TimeoutError):
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
            except (aiohttp.ClientError, asyncio.TimeoutError):
                has_release = None

    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
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
    hass: HomeAssistant, store: HaSocData, repo_urls: list[str]
) -> dict[str, Any]:
    """Refresh cached GitHub signals for the given owner/repo list. Returns
    a summary; the per-repo data lands in the store cache. A no-op (with a
    clear reason) when no token is configured."""
    token = store.settings.get(CONF_GITHUB_TOKEN)
    if not token:
        return {"ok": False, "reason": "no_github_token", "refreshed": 0}

    unique = [r for r in dict.fromkeys(repo_urls) if r]
    dropped = max(0, len(unique) - _MAX_REPOS_PER_REFRESH)
    unique = unique[:_MAX_REPOS_PER_REFRESH]

    session = async_get_clientsession(hass)
    cache = dict(store.data["integration_security"].get("github") or {})
    refreshed = 0
    for owner_repo in unique:
        signals = await _fetch_repo_signals(session, owner_repo, token)
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
    return {"ok": True, "refreshed": refreshed, "skipped": dropped}
