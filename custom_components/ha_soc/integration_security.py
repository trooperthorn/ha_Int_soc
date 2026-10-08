"""Integration Security: a provenance view of every installed integration.

This measures provenance, not safety. Nothing here proves code is safe to
run, and the frontend never renders "Safe", "Verified", or "Trusted"
(signal design: docs/design.md).
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CONF_GITHUB_TOKEN,
    INTEGRATION_FLAG_CUSTOM_REPO,
    INTEGRATION_TIER_CORE,
    INTEGRATION_TIER_CUSTOM,
    INTEGRATION_TIER_HACS,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
# owner/repo out of a GitHub URL, tolerating trailing /issues, .git, slashes.
_GITHUB_REPO_RE = re.compile(r"github\.com/([^/\s]+)/([^/\s#?]+)")


def _license_present_sync(path: str) -> bool:
    return any(os.path.isfile(os.path.join(path, name)) for name in _LICENSE_NAMES)


# root path -> (signature, domains, licenses). The signature is the modification time of the
# root and of every entry in it. Adding, removing or replacing an integration, or a manifest
# or license inside one, changes the directory's time, so an unchanged signature means the
# previous answer still holds and the six file probes per integration can be skipped.
_SCAN_CACHE: dict[str, tuple[tuple[Any, ...], list[str], dict[str, bool]]] = {}
# A scan is cached only when nothing in the directory changed in the last two seconds.
_SCAN_SETTLE_NS = 2_000_000_000


def _scan_custom_components_sync(root: str) -> tuple[list[str], dict[str, bool]]:
    """One pass over custom_components/: every directory with a manifest.json,
    plus whether each carries a license file.

    Synchronous disk I/O: executor only, never the event loop. The result is cached
    by directory modification times; see _SCAN_CACHE.
    """
    try:
        root_mtime = os.stat(root).st_mtime_ns
        names: list[tuple[str, int]] = []
        with os.scandir(root) as it:
            for entry in it:
                if entry.name.startswith((".", "_")):
                    continue
                try:
                    mtime = entry.stat().st_mtime_ns
                except OSError:
                    # A dangling link or an unreadable entry: keep scanning the rest and
                    # let the manifest probe below decide whether it counts.
                    try:
                        mtime = entry.stat(follow_symlinks=False).st_mtime_ns
                    except OSError:
                        mtime = 0
                names.append((entry.name, mtime))
    except OSError:
        _SCAN_CACHE.pop(root, None)
        return [], {}
    signature = (root_mtime, tuple(sorted(names)))
    cached = _SCAN_CACHE.get(root)
    if cached is not None and cached[0] == signature:
        return list(cached[1]), dict(cached[2])
    domains: list[str] = []
    licenses: dict[str, bool] = {}
    for name, _mtime in names:
        path = os.path.join(root, name)
        if os.path.isfile(os.path.join(path, "manifest.json")):
            domains.append(name)
            licenses[name] = _license_present_sync(path)
    domains.sort()
    # A change in the same clock tick as this scan could leave a time unchanged, so a
    # directory touched in the last moments is scanned again next time rather than trusted.
    newest = max([root_mtime, *(mtime for _name, mtime in names)])
    if time.time_ns() - newest > _SCAN_SETTLE_NS:
        _SCAN_CACHE[root] = (signature, domains, licenses)
    else:
        _SCAN_CACHE.pop(root, None)
    return list(domains), dict(licenses)


def _repo_url_from_integration(documentation: str | None, issue_tracker: str | None) -> str | None:
    """Best-effort GitHub owner/repo discovery from the manifest's own URLs."""
    for candidate in (issue_tracker, documentation):
        if not candidate:
            continue
        match = _GITHUB_REPO_RE.search(candidate)
        if match:
            owner, repo = match.group(1), match.group(2)
            return f"{owner}/{repo.removesuffix('.git')}"
    return None


def _hacs_domain_origins(hass: HomeAssistant) -> dict[str, str] | None:
    """Best-effort {domain: origin} from HACS runtime data ('default' or the
    custom-repo flag); None when HACS is absent or not introspectable."""
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
    hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
) -> dict[str, Any]:
    """Everything the Integration Security view needs. Local signals only;
    GitHub-derived signals are merged from the store cache and are None
    when not collected. Only the token's presence is checked; its value
    never enters this function.
    """
    github_configured = bool(await secrets.async_get(CONF_GITHUB_TOKEN))
    hacs_origins = _hacs_domain_origins(hass)
    hacs_installed = hacs_origins is not None or "hacs" in hass.config.components

    # Disk I/O off the event loop.
    custom_domains, license_map = await hass.async_add_executor_job(
        _scan_custom_components_sync, hass.config.path("custom_components")
    )
    # Core domains with an active config entry are included so the view is not custom-only.
    entry_domains = {entry.domain for entry in hass.config_entries.async_entries()}
    all_domains = sorted(set(custom_domains) | entry_domains)

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

        # Only the custom-repo HACS origin is flagged.
        flags: list[str] = []
        if hacs_origins is not None and domain in hacs_origins:
            origin = hacs_origins[domain]
            if origin == INTEGRATION_FLAG_CUSTOM_REPO:
                flags.append(origin)

        repo_url = _repo_url_from_integration(
            integration.documentation, integration.issue_tracker
        )

        license_present: bool | None
        if is_custom:
            # Fallback covers a custom domain resolved from outside custom_components/.
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
                # None means not collected, never a guess.
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
