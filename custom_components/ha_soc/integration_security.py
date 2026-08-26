"""Integration Security — a PROVENANCE view of every installed integration.

Read integration_security's companion design doc for the full rationale.
The one rule that governs everything here: **this measures provenance, not
safety.** A Home Assistant integration is arbitrary Python running
in-process with no sandbox — nothing measured here proves the code is safe
to run. It measures how much is known about where the code came from and
how it's maintained. Every surface that shows this MUST say so; the
frontend never renders "Safe"/"Verified"/"Trusted" or a bare shield.

What this module computes locally, with no network call and no new
privilege (signals 1/4/8/9 of the design):

- **Tier** — how vetted the source is. Core (ships inside HA, hassfest-
  validated) vs. custom (anything under custom_components/). Where HACS is
  installed we make a best-effort attempt to tell HACS-managed content
  apart from truly unmanaged custom code, and — per the feature request's
  variance on signal 4 — flag only the two lowest-provenance HACS origins
  (a custom repository, or a custom source-list), never default-store HACS
  content. When HACS internals aren't introspectable we say so (source
  "unverified") rather than guessing.
- **quality_scale / integration_type** — read straight from the manifest
  (core integrations carry a real quality_scale today).
- **License present** (signal 8) — a local file check in the integration's
  own directory; core inherits HA's own license.
- **Scanner findings** (signal 9) — reuses this project's existing
  AST-based integration scanner; no new detection, just surfacing.

The GitHub-derived signals (2/5/6/7/10 — release vs branch, identity
assurance, recency, popularity, archived) need an outbound API call and an
optional token; they're gathered by github_provenance.py and cached in the
store, and merged in here as a per-integration ``github`` block that is
None/"not collected" whenever no token is set or a repo URL can't be
discovered. This module never blocks on the network.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CONF_GITHUB_TOKEN,
    INTEGRATION_FLAG_CUSTOM_REPO,
    INTEGRATION_FLAG_CUSTOM_SOURCE_LIST,
    INTEGRATION_TIER_CORE,
    INTEGRATION_TIER_CUSTOM,
    INTEGRATION_TIER_HACS,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
# owner/repo out of a GitHub URL, tolerating trailing /issues, .git, slashes.
_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)")


def _license_present_sync(path: str) -> bool:
    return any(os.path.isfile(os.path.join(path, name)) for name in _LICENSE_NAMES)


def _scan_custom_components_sync(root: str) -> tuple[list[str], dict[str, bool]]:
    """One pass over custom_components/: every directory that looks like an
    integration (has a manifest.json) — the population that most needs a
    provenance view — plus whether each carries a license file (signal 8).

    Synchronous disk I/O, so this must ONLY ever run in the executor (the
    overview below calls it via async_add_executor_job), never on the event
    loop: Home Assistant's asyncio protection rightly flags a bare listdir
    there, and on a slow SD card it would stall the entire loop every time
    the Integration Security tab is opened. Doing the license check in the
    same pass also collapses what used to be one executor hop per custom
    integration into a single scan.
    """
    if not os.path.isdir(root):
        return [], {}
    domains: list[str] = []
    licenses: dict[str, bool] = {}
    for name in os.listdir(root):
        if name.startswith((".", "_")):
            continue
        path = os.path.join(root, name)
        if os.path.isfile(os.path.join(path, "manifest.json")):
            domains.append(name)
            licenses[name] = _license_present_sync(path)
    return sorted(domains), licenses


def _repo_url_from_integration(documentation: str | None, issue_tracker: str | None) -> str | None:
    """Best-effort GitHub owner/repo discovery from the manifest's own URLs.
    issue_tracker is usually a github issues link; documentation often is
    too for custom integrations (core points at home-assistant.io, which
    yields nothing — honestly reported as no repo URL)."""
    for candidate in (issue_tracker, documentation):
        if not candidate:
            continue
        match = _GITHUB_REPO_RE.search(candidate)
        if match:
            owner, repo = match.group(1), match.group(2)
            return f"{owner}/{repo.removesuffix('.git')}"
    return None


def _hacs_domain_origins(hass: HomeAssistant) -> dict[str, str] | None:
    """Best-effort map of {domain: origin} from HACS's own runtime data,
    where origin is 'default' (curated store), 'custom_repo', or
    'custom_source_list'. Returns None when HACS isn't installed or its
    internals aren't introspectable — in which case we DON'T guess a tier
    or a flag, we report the source as unverified. HACS internals aren't a
    stable API, so every access is defensive.
    """
    hacs = hass.data.get("hacs")
    if hacs is None:
        return None
    try:
        repositories = hacs.repositories.list_all  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - HACS internals are not a stable API
        return None
    origins: dict[str, str] = {}
    try:
        for repo in repositories:
            data = getattr(repo, "data", None)
            if data is None:
                continue
            domain = getattr(data, "domain", None) or getattr(data, "full_name", None)
            if not domain:
                continue
            # HACS marks curated-store repos; anything else is user-added.
            is_default = bool(getattr(data, "default", False)) or bool(
                getattr(repo, "is_default", False)
            )
            origins[str(domain)] = "default" if is_default else INTEGRATION_FLAG_CUSTOM_REPO
    except Exception:  # noqa: BLE001
        return None
    return origins


async def async_integration_security_overview(
    hass: HomeAssistant, store: HaSocData
) -> dict[str, Any]:
    """Everything the Integration Security view needs. Local signals only;
    GitHub-derived signals are merged from the store cache (populated
    out-of-band by github_provenance.py) and are None when not collected."""
    github_configured = bool(store.settings.get(CONF_GITHUB_TOKEN))
    hacs_origins = _hacs_domain_origins(hass)
    hacs_installed = hacs_origins is not None or "hacs" in hass.config.components

    # Disk I/O off the event loop — see _scan_custom_components_sync.
    custom_domains, license_map = await hass.async_add_executor_job(
        _scan_custom_components_sync, hass.config.path("custom_components")
    )
    # Also include core domains that have an active config entry, so the
    # view isn't custom-only — a user should see their whole surface.
    entry_domains = {entry.domain for entry in hass.config_entries.async_entries()}
    all_domains = sorted(set(custom_domains) | entry_domains)

    # Scanner findings per domain (signal 9) — reuse what's already stored.
    scanner_counts: dict[str, int] = {}
    for finding in store.data.get("scanner_findings", {}).values():
        domain = finding.get("domain")
        if domain:
            scanner_counts[domain] = scanner_counts.get(domain, 0) + 1

    github_cache = store.data.get("integration_security", {}).get("github", {})

    rows: list[dict[str, Any]] = []
    for domain in all_domains:
        try:
            integration = await async_get_integration(hass, domain)
        except Exception:  # noqa: BLE001 - a domain we can't resolve is skipped, not fatal
            continue

        is_custom = not integration.is_built_in
        if not is_custom:
            tier = INTEGRATION_TIER_CORE
        elif hacs_origins is not None and domain in hacs_origins:
            tier = INTEGRATION_TIER_HACS
        else:
            tier = INTEGRATION_TIER_CUSTOM

        # Variance on signal 4: flag ONLY custom-repo / custom-source-list
        # HACS origins. Default-store HACS content is not flagged, and an
        # unmanaged custom_components/ drop is its own tier (not a "flag").
        flags: list[str] = []
        if hacs_origins is not None and domain in hacs_origins:
            origin = hacs_origins[domain]
            if origin in (INTEGRATION_FLAG_CUSTOM_REPO, INTEGRATION_FLAG_CUSTOM_SOURCE_LIST):
                flags.append(origin)

        repo_url = _repo_url_from_integration(
            integration.documentation, integration.issue_tracker
        )

        license_present: bool | None
        if is_custom:
            # Precomputed by the single executor scan above for anything that
            # actually lives under custom_components/; the fallback covers a
            # custom domain resolved from elsewhere (shouldn't happen, but a
            # wrong answer here would be worse than one extra executor hop).
            license_present = license_map.get(domain)
            if license_present is None:
                path = hass.config.path("custom_components", domain)
                license_present = await hass.async_add_executor_job(_license_present_sync, path)
        else:
            license_present = True  # core inherits HA's own license

        version = integration.version
        rows.append(
            {
                "domain": domain,
                "name": integration.name,
                "tier": tier,
                "is_custom": is_custom,
                "quality_scale": integration.quality_scale,
                "integration_type": integration.integration_type,
                "version": str(version) if version is not None else None,
                "license_present": license_present,
                "repo_url": repo_url,
                "flags": flags,
                "scanner_findings": scanner_counts.get(domain, 0),
                # None => not collected (no token, or no repo URL). Never a
                # guess. Populated from the store cache when available.
                "github": github_cache.get(repo_url) if (github_configured and repo_url) else None,
            }
        )

    tier_counts = {
        INTEGRATION_TIER_CORE: sum(1 for r in rows if r["tier"] == INTEGRATION_TIER_CORE),
        INTEGRATION_TIER_HACS: sum(1 for r in rows if r["tier"] == INTEGRATION_TIER_HACS),
        INTEGRATION_TIER_CUSTOM: sum(1 for r in rows if r["tier"] == INTEGRATION_TIER_CUSTOM),
    }

    return {
        "github_configured": github_configured,
        "hacs_installed": hacs_installed,
        "hacs_source_introspectable": hacs_origins is not None,
        "tier_counts": tier_counts,
        "integrations": rows,
    }
