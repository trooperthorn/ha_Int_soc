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
a guess. Results are cached in the store keyed by "owner/repo", and a repo
whose cached signals are younger than INTEGRATION_SECURITY_CACHE_TTL_HOURS
is not re-fetched by a refresh (work plan item 4.10); the GitHub endpoint
is a hardcoded constant and the token is a header, never spliced into a
URL string.

Hardening (work plan item 4.10, GH-1): the "owner/repo" slug comes out of
a third-party manifest's documentation/issue_tracker URLs, and yarl
normalizes ``..`` path segments before sending (verified in the work
plan's section 6.1), so an unvalidated slug like ``../../user/repos``
would redirect the owner's token to an arbitrary GitHub API path and
cache the response. Every slug is therefore validated against
``^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$`` with ``.`` and ``..`` components
rejected outright before any URL is built; an invalid slug is skipped
and counted, never fetched. A 403 whose X-RateLimit-Remaining header is
0 stops the whole refresh and reports ``rate_limited``, so a big install
does not burn its remaining quota discovering the limit one repo at a
time. Obvious false positive of the slug validation: a legitimately
renamed repo whose manifest still carries a malformed URL stays "not
collected" until the manifest is fixed.

The token lives in the private secret store (secrets_store.py) and is
fetched immediately before each per-repo lookup, then dropped with that
call frame (work item SEC-3): no parameter threading, attribute, or module
global carries the token across the refresh loop.
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
# Cap how many repos a single refresh will look up, so one refresh can't
# blow a whole hour's rate budget on a huge install; the rest keep their
# cached values (or stay "not collected") until the next refresh.
_MAX_REPOS_PER_REFRESH = 60

# The only slug shape ever allowed into a request path (work plan item
# 4.10). Dot-only components are rejected separately below because "." and
# ".." match this character class while still being path-traversal tokens.
_REPO_SLUG_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _valid_repo_slug(owner_repo: str) -> bool:
    """Whether the string is safe to place into the /repos/{owner}/{repo}
    path: matches the allowed character set AND neither component is a
    dot segment (yarl collapses those before sending, which would point
    the token at a different API path entirely)."""
    if not isinstance(owner_repo, str) or not _REPO_SLUG_RE.match(owner_repo):
        return False
    owner, repo = owner_repo.split("/", 1)
    return owner not in (".", "..") and repo not in (".", "..")


class _RateLimited(Exception):
    """GitHub answered 403 with X-RateLimit-Remaining: 0 - the token's
    quota is exhausted, so the refresh must stop rather than burn the
    error budget one repo at a time."""


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def _fetch_repo_signals(
    session: aiohttp.ClientSession, owner_repo: str, secrets: HaSocSecretStore
) -> dict[str, Any] | None:
    """Two calls per repo: the repo object (stars/forks/archived/pushed_at)
    and the default-branch head commit (verification). Returns a signal
    dict, or None on any error (the caller keeps that repo 'not collected').

    The token is fetched from the secret store here, right before the
    requests it authenticates, and goes out of scope when this function
    returns (SEC-3).
    """
    token = await secrets.async_get(CONF_GITHUB_TOKEN)
    if not token:
        # The caller checked presence before starting the loop; the token
        # being cleared mid-refresh just leaves the rest "not collected".
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
        # ValueError covers json.JSONDecodeError (work plan item 4.10): a
        # bad body from one repository leaves that repo "not collected"
        # instead of aborting the whole refresh loop.
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
    a summary; the per-repo data lands in the store cache. A no-op (with a
    clear reason) when no token is configured. Invalid slugs are skipped
    and counted, cache entries younger than the TTL are kept as-is, and an
    exhausted rate limit stops the loop with reason "rate_limited" while
    keeping everything fetched so far (work plan item 4.10)."""
    # Presence check only; the value is fetched per repo inside
    # _fetch_repo_signals and never held across the loop (SEC-3).
    if not await secrets.async_get(CONF_GITHUB_TOKEN):
        return {"ok": False, "reason": "no_github_token", "refreshed": 0}

    unique = [r for r in dict.fromkeys(repo_urls) if r]
    invalid = [r for r in unique if not _valid_repo_slug(r)]
    if invalid:
        # Slug names only are logged; they came from third-party
        # manifests and are exactly the values being refused a request.
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
                # Honor INTEGRATION_SECURITY_CACHE_TTL_HOURS (work plan
                # item 4.10): recently collected signals are kept, and
                # the rate budget goes to stale or missing repos.
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
