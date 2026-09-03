"""Device vulnerability tracking: CVE correlation and firmware currency.

Every CVE match is a candidate for a human to confirm or dismiss, never a
verdict, and the absence of a match is not evidence a device is secure
(data disclosure and design: docs/security.md, docs/design.md).
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.util.dt as dt_util

from .const import (
    CONF_NVD_API_KEY,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    STATUS_CONFIRMED,
    STATUS_DISMISSED,
    STATUS_NEW,
    STATUS_RESOLVED,
)
from .secrets_store import HaSocSecretStore
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

FINDINGS_TABLE = "vuln_findings"

_VALID_STATUSES = {STATUS_NEW, STATUS_CONFIRMED, STATUS_DISMISSED, STATUS_RESOLVED}

CONFIDENCE_EXACT_CPE = "exact_cpe"  # reserved: no path in this module produces it yet
CONFIDENCE_CURATED_MAP = "curated_map"
CONFIDENCE_KEYWORD = "keyword"
CONFIDENCE_HEURISTIC = "heuristic"

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_RESULTS_PER_PAGE = 20
# Bounded paging: a vendor with more CVEs than this covers has its oldest tail unexamined.
NVD_MAX_PAGES = 5
NVD_TIMEOUT_SECONDS = 15
# NVD allows ~5 req/30s without a key and ~50/30s with one; sleeps apply after real HTTP calls only.
NVD_DELAY_NO_KEY = 6
NVD_DELAY_WITH_KEY = 0.7
# One bounded retry on 429, honoring Retry-After when present.
NVD_MAX_RATE_LIMIT_RETRIES = 1
NVD_RATE_LIMIT_FALLBACK_DELAY = NVD_DELAY_NO_KEY * 2

# Per-match_string refetch window; in-memory only, so a restart just costs one re-fetch.
MATCH_STRING_CACHE_TTL = timedelta(days=7)

# Highest CVSS first, so one very active CPE entry cannot flood the store.
MAX_FINDINGS_PER_DEVICE = 10

MAX_SUMMARY_CHARS = 500

# Device availability buckets, a separate axis from vulnerability severity and finding status.
DEVICE_STATUS_AVAILABLE = "available"
DEVICE_STATUS_PARTIAL = "partial"
DEVICE_STATUS_UNAVAILABLE = "unavailable"
DEVICE_STATUS_DISABLED = "disabled"
DEVICE_STATUS_NO_ENTITIES = "no_entities"
DEVICE_STATUSES = (
    DEVICE_STATUS_AVAILABLE,
    DEVICE_STATUS_PARTIAL,
    DEVICE_STATUS_UNAVAILABLE,
    DEVICE_STATUS_DISABLED,
    DEVICE_STATUS_NO_ENTITIES,
)
_UNAVAILABLE_STATES = ("unavailable", "unknown")

# CVSS-scale proxy score for a device whose only open finding is the firmware heuristic.
FIRMWARE_ONLY_RISK_SCORE = 5.0

# Manufacturer-only wildcards; an empty model substring means vendor-wide.
CURATED_CPE_MAP: dict[tuple[str, str], str] = {
    ("shelly", ""): "cpe:2.3:o:shelly:*",
    ("tp-link", ""): "cpe:2.3:o:tp-link:*",
    ("kasa", ""): "cpe:2.3:o:tp-link:*",
    ("tapo", ""): "cpe:2.3:o:tp-link:*",
    ("tuya", ""): "cpe:2.3:o:tuya:*",
    ("sonoff", ""): "cpe:2.3:o:itead:*",
    ("itead", ""): "cpe:2.3:o:itead:*",
    ("reolink", ""): "cpe:2.3:o:reolink:*",
    ("ubiquiti", ""): "cpe:2.3:o:ubiquiti:*",
    ("unifi", ""): "cpe:2.3:o:ubiquiti:*",
    ("philips", ""): "cpe:2.3:o:signify:*",
    ("signify", ""): "cpe:2.3:o:signify:*",
    ("hue", ""): "cpe:2.3:o:signify:*",
    ("avm", ""): "cpe:2.3:o:avm:*",
    ("fritz", ""): "cpe:2.3:o:avm:*",
    ("synology", ""): "cpe:2.3:o:synology:*",
    ("xiaomi", ""): "cpe:2.3:o:xiaomi:*",
    ("aqara", ""): "cpe:2.3:o:xiaomi:*",
    ("netgear", ""): "cpe:2.3:o:netgear:*",
    ("d-link", ""): "cpe:2.3:o:d-link:*",
    ("home assistant", ""): "cpe:2.3:a:home-assistant:home-assistant:*",
}


def _device_name(device: dr.DeviceEntry) -> str:
    return device.name_by_user or device.name or device.id


def _match_curated_cpe(manufacturer: str, model: str) -> tuple[str, bool] | None:
    """The curated CPE match plus whether it was vendor-only (an empty model
    substring in the table)."""
    manufacturer_lower = manufacturer.lower()
    model_lower = model.lower()
    for (mfr_substr, model_substr), cpe_prefix in CURATED_CPE_MAP.items():
        if mfr_substr not in manufacturer_lower:
            continue
        if model_substr and model_substr not in model_lower:
            continue
        return cpe_prefix, not model_substr
    return None


def _extract_cvss(cve: dict[str, Any]) -> float | None:
    metrics = cve.get("metrics", {})
    # Newest CVSS version present wins; never averaged or maxed across versions.
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for entry in metrics.get(key) or []:
            score = entry.get("cvssData", {}).get("baseScore")
            if score is not None:
                return float(score)
    return None


def _severity_for_score(score: float | None) -> str:
    if score is None:
        # Unscored is not low; it gets its own bucket.
        return SEVERITY_INFO
    if score >= 9.0:
        return SEVERITY_CRITICAL
    if score >= 7.0:
        return SEVERITY_HIGH
    if score >= 4.0:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


def _parse_retry_after(value: str | None, default: float) -> float:
    """Parse an HTTP Retry-After header in seconds form, the only form NVD sends."""
    if value is None:
        return default
    try:
        return max(float(value), 0.0)
    except ValueError:
        return default


def _cve_description(cve: dict[str, Any]) -> str:
    for desc in cve.get("descriptions", []):
        if desc.get("lang") == "en" and desc.get("value"):
            return desc["value"]
    return "No description available."


def _cve_summary(cve: dict[str, Any], cvss: float | None) -> str:
    description = _cve_description(cve)
    summary = (
        description
        if cvss is not None
        else f"CVSS not yet assigned. {description}"
    )
    if len(summary) > MAX_SUMMARY_CHARS:
        summary = summary[: MAX_SUMMARY_CHARS - 1].rstrip() + "…"
    return summary


class DeviceVulnerabilityTracker:
    """Correlates HA's device registry against known firmware issues.

    A scan never raises out of `async_run_scan`.
    """

    def __init__(
        self, hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
    ) -> None:
        self.hass = hass
        self.store = store
        # Store reference only; the key is fetched per request inside _async_query_nvd.
        self._secrets = secrets
        # match_string -> last real NVD fetch; in-memory only.
        self._last_fetched: dict[str, datetime] = {}
        # Serializes scans so the periodic loop and a manual scan never overlap.
        self._scan_lock = asyncio.Lock()

    async def async_run_scan(self) -> list[dict]:
        async with self._scan_lock:
            return await self._async_run_scan_locked()

    async def _async_run_scan_locked(self) -> list[dict]:
        registry = dr.async_get(self.hass)
        physical_devices = [
            device
            for device in registry.devices.values()
            if device.entry_type != dr.DeviceEntryType.SERVICE
        ]
        devices_by_id = {device.id: device for device in physical_devices}

        findings: list[dict] = []
        findings.extend(self._check_firmware_currency(devices_by_id))

        # The owner's toggle governs the whole outbound pass; a missing key means on.
        if not self.store.settings.get("nvd_lookups_enabled", True):
            _LOGGER.debug(
                "HA SOC: NVD lookups are disabled; only the network-free "
                "firmware-currency check ran"
            )
            return findings

        try:
            findings.extend(await self._async_correlate_cves(physical_devices))
        except Exception:  # noqa: BLE001 - firmware findings above must survive this
            _LOGGER.exception(
                "HA SOC CVE correlation pass failed; firmware-currency findings "
                "were already saved"
            )

        return findings

    async def async_device_overview(self) -> dict[str, Any]:
        """Per-device rows for the SOC Dashboard's device-centric widgets.

        Pure read over the registries and stored findings; never triggers
        a scan.
        """
        registry = dr.async_get(self.hass)
        entity_registry = er.async_get(self.hass)
        physical_devices = [
            device
            for device in registry.devices.values()
            if device.entry_type != dr.DeviceEntryType.SERVICE
        ]

        findings_by_device: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for finding in self.store.data.get(FINDINGS_TABLE, {}).values():
            if finding.get("status") == STATUS_DISMISSED:
                continue
            findings_by_device[finding["device_id"]].append(finding)

        devices_overview: list[dict[str, Any]] = []
        status_counts = dict.fromkeys(DEVICE_STATUSES, 0)
        by_vendor: dict[str, int] = defaultdict(int)

        for device in physical_devices:
            device_findings = findings_by_device.get(device.id, [])

            severity_counts = {
                SEVERITY_CRITICAL: 0,
                SEVERITY_HIGH: 0,
                SEVERITY_MEDIUM: 0,
                SEVERITY_LOW: 0,
            }
            for finding in device_findings:
                band = finding.get("severity")
                if band == SEVERITY_INFO:
                    # INFO folds into low for this 4-column view.
                    band = SEVERITY_LOW
                if band in severity_counts:
                    severity_counts[band] += 1

            scored = [f["cvss"] for f in device_findings if f.get("cvss") is not None]
            if scored:
                risk_score = round(max(scored), 1)
            elif device_findings:
                risk_score = FIRMWARE_ONLY_RISK_SCORE
            else:
                risk_score = 0.0

            status = self._device_status(device, entity_registry)
            status_counts[status] += 1

            vendor = device.manufacturer or "Unknown"
            by_vendor[vendor] += len(device_findings)

            devices_overview.append(
                {
                    "device_id": device.id,
                    "name": _device_name(device),
                    "vendor": vendor,
                    "os": device.model or vendor,
                    "risk_score": risk_score,
                    "total_findings": len(device_findings),
                    "severity_counts": severity_counts,
                    "status": status,
                }
            )

        devices_overview.sort(key=lambda d: d["risk_score"], reverse=True)

        return {
            "devices": devices_overview,
            "status_counts": status_counts,
            "by_vendor": dict(by_vendor),
        }

    def _device_status(
        self,
        device: dr.DeviceEntry,
        entity_registry: er.EntityRegistry,
    ) -> str:
        if device.disabled_by is not None:
            # Intentionally turned off, not a fault.
            return DEVICE_STATUS_DISABLED

        entities = er.async_entries_for_device(
            entity_registry, device.id, include_disabled_entities=False
        )
        if not entities:
            return DEVICE_STATUS_NO_ENTITIES

        states = [self.hass.states.get(entry.entity_id) for entry in entities]
        known_states = [s for s in states if s is not None]
        if not known_states:
            return DEVICE_STATUS_NO_ENTITIES

        unavailable_count = sum(1 for s in known_states if s.state in _UNAVAILABLE_STATES)
        if unavailable_count == len(known_states):
            return DEVICE_STATUS_UNAVAILABLE
        if unavailable_count > 0:
            return DEVICE_STATUS_PARTIAL
        return DEVICE_STATUS_AVAILABLE

    def _check_firmware_currency(
        self, devices_by_id: dict[str, dr.DeviceEntry]
    ) -> list[dict]:
        entity_registry = er.async_get(self.hass)
        now_iso = dt_util.utcnow().isoformat()
        findings: list[dict] = []

        for state in self.hass.states.async_all("update"):
            if state.attributes.get("device_class") != "firmware":
                continue
            if state.state != "on":
                continue

            entity_entry = entity_registry.async_get(state.entity_id)
            if entity_entry is None or entity_entry.device_id is None:
                continue

            device = devices_by_id.get(entity_entry.device_id)
            if device is None:
                continue

            installed = state.attributes.get("installed_version")
            latest = state.attributes.get("latest_version")

            finding_id = f"{device.id}:firmware_outdated"
            finding = {
                "id": finding_id,
                "device_id": device.id,
                "device_name": _device_name(device),
                "cve_id": None,
                "cvss": None,
                "severity": SEVERITY_MEDIUM,
                "confidence": CONFIDENCE_HEURISTIC,
                "summary": f"Update available: installed {installed}, latest {latest}",
                "source": "heuristic",
                "match_string": None,
                "first_seen": now_iso,
                "last_seen": now_iso,
                "status": STATUS_NEW,
            }
            self.store.async_upsert_finding(FINDINGS_TABLE, finding_id, finding)
            findings.append(finding)

        return findings

    async def _async_correlate_cves(self, devices: list[dr.DeviceEntry]) -> list[dict]:
        now = dt_util.utcnow()
        now_iso = now.isoformat()
        # Presence only; the value is fetched per request inside _async_query_nvd.
        has_api_key = bool(await self._secrets.async_get(CONF_NVD_API_KEY))
        findings: list[dict] = []
        # Shared within one run, independent of the MATCH_STRING_CACHE_TTL gate.
        run_cache: dict[str, list[dict[str, Any]] | None] = {}

        for device in devices:
            manufacturer = device.manufacturer
            if not manufacturer:
                continue
            model = device.model or ""

            curated = _match_curated_cpe(manufacturer, model)
            vendor_only = False
            if curated is not None:
                cpe_prefix, vendor_only = curated
                confidence = CONFIDENCE_CURATED_MAP
                query_param = "virtualMatchString"
                match_string = cpe_prefix
            elif model:
                # keywordSearch matches free-text descriptions, hence the lower confidence tier.
                confidence = CONFIDENCE_KEYWORD
                query_param = "keywordSearch"
                match_string = f"{manufacturer} {model}"
            else:
                continue

            if match_string in run_cache:
                vulnerabilities = run_cache[match_string]
            elif self._is_recently_fetched(match_string, now):
                _LOGGER.debug(
                    "Skipping NVD query for %s: fetched within the last %s",
                    match_string,
                    MATCH_STRING_CACHE_TTL,
                )
                continue
            else:
                vulnerabilities = await self._async_query_nvd(query_param, match_string)
                # Only a successful fetch earns the multi-day cache entry; run_cache records either way.
                if vulnerabilities is not None:
                    self._last_fetched[match_string] = now
                run_cache[match_string] = vulnerabilities
                await asyncio.sleep(
                    NVD_DELAY_WITH_KEY if has_api_key else NVD_DELAY_NO_KEY
                )

            if not vulnerabilities:
                continue

            for finding in self._build_findings_for_device(
                device, vulnerabilities, confidence, match_string, now_iso,
                vendor_only=vendor_only,
            ):
                self.store.async_upsert_finding(
                    FINDINGS_TABLE, finding["id"], finding
                )
                findings.append(finding)

        return findings

    def _is_recently_fetched(self, match_string: str, now: datetime) -> bool:
        last = self._last_fetched.get(match_string)
        return last is not None and (now - last) < MATCH_STRING_CACHE_TTL

    async def _async_query_nvd(
        self, query_param: str, match_string: str
    ) -> list[dict[str, Any]] | None:
        """All pages (bounded by NVD_MAX_PAGES) for one match string; a
        failure on a later page returns the pages already fetched."""
        session = async_get_clientsession(self.hass)
        # Fetched immediately before the request and dropped with this frame.
        api_key = await self._secrets.async_get(CONF_NVD_API_KEY)
        headers = {"apiKey": api_key} if api_key else None
        page_delay = NVD_DELAY_WITH_KEY if api_key else NVD_DELAY_NO_KEY

        collected: list[dict[str, Any]] = []
        start_index = 0
        for page in range(NVD_MAX_PAGES):
            params = {
                query_param: match_string,
                "resultsPerPage": str(NVD_RESULTS_PER_PAGE),
                "startIndex": str(start_index),
            }
            for attempt in range(NVD_MAX_RATE_LIMIT_RETRIES + 1):
                try:
                    async with asyncio.timeout(NVD_TIMEOUT_SECONDS):
                        async with session.get(
                            NVD_API_URL, params=params, headers=headers
                        ) as response:
                            if response.status == 429:
                                if attempt < NVD_MAX_RATE_LIMIT_RETRIES:
                                    wait = _parse_retry_after(
                                        response.headers.get("Retry-After"),
                                        NVD_RATE_LIMIT_FALLBACK_DELAY,
                                    )
                                    _LOGGER.debug(
                                        "NVD rate limit (429) for %s=%s; retrying in %ss",
                                        query_param, match_string, wait,
                                    )
                                    await asyncio.sleep(wait)
                                    continue
                                # Retries exhausted: return what was collected; never parse a 429 body.
                                _LOGGER.warning(
                                    "NVD rate limit persisted for %s=%s after retrying",
                                    query_param, match_string,
                                )
                                return collected if collected else None
                            response.raise_for_status()
                            data = await response.json()
                            break
                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    _LOGGER.warning(
                        "NVD query failed for %s=%s: %s", query_param, match_string, err
                    )
                    return collected if collected else None

            batch = data.get("vulnerabilities", [])
            collected.extend(batch)
            total = data.get("totalResults")
            start_index += len(batch)
            if not batch or total is None or start_index >= int(total):
                break
            if page < NVD_MAX_PAGES - 1:
                # Same rate-limit pacing between pages as between devices.
                await asyncio.sleep(page_delay)

        return collected

    def _build_findings_for_device(
        self,
        device: dr.DeviceEntry,
        vulnerabilities: list[dict[str, Any]],
        confidence: str,
        match_string: str,
        now_iso: str,
        *,
        vendor_only: bool = False,
    ) -> list[dict]:
        device_name = _device_name(device)

        candidates: list[tuple[float, str, float | None, str, str]] = []
        for vuln in vulnerabilities:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id")
            if not cve_id:
                continue
            cvss = _extract_cvss(cve)
            # A vendor-only wildcard says nothing about the model, so the finding is INFO.
            severity = SEVERITY_INFO if vendor_only else _severity_for_score(cvss)
            summary = _cve_summary(cve, cvss)
            if vendor_only:
                summary = (
                    "Vendor-wide match only (no model-specific CPE): "
                    "confirm the model is affected before acting. " + summary
                )
            # Unscored CVEs sort last rather than being dropped.
            sort_key = cvss if cvss is not None else -1.0
            candidates.append((sort_key, cve_id, cvss, severity, summary))

        candidates.sort(key=lambda item: item[0], reverse=True)

        findings = []
        for _, cve_id, cvss, severity, summary in candidates[:MAX_FINDINGS_PER_DEVICE]:
            finding_id = f"{device.id}:{cve_id}"
            findings.append(
                {
                    "id": finding_id,
                    "device_id": device.id,
                    "device_name": device_name,
                    "cve_id": cve_id,
                    "cvss": cvss,
                    "severity": severity,
                    "confidence": confidence,
                    "summary": summary,
                    "source": "nvd",
                    "match_string": match_string,
                    "first_seen": now_iso,
                    "last_seen": now_iso,
                    "status": STATUS_NEW,
                }
            )
        return findings

    async def async_set_status(
        self,
        finding_id: str,
        status: str,
        *,
        user_id: str | None,
        note: str | None = None,
    ) -> None:
        if status not in _VALID_STATUSES:
            raise ValueError(f"Invalid finding status: {status!r}")

        self.store.async_set_finding_status(
            FINDINGS_TABLE,
            finding_id,
            status,
            by_user_id=user_id,
            note=note,
            at=dt_util.utcnow().isoformat(),
        )
