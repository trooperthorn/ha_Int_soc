"""Device vulnerability tracking: CVE correlation and firmware currency.

This module never verifies a vulnerability. CVE correlation matches on
(often noisy) device manufacturer/model strings pulled from the device
registry — not on verified serial numbers, hardware revisions, or firmware
hashes. Every match produced here is a candidate for a human to confirm or
dismiss, never an automatic verdict. The inverse is just as important:
absence of a CVE match is NOT evidence a device is secure — NVD's coverage
of consumer/prosumer IoT firmware is inherently incomplete, and a device
with no findings may simply never have had a CVE filed against it, or may
not yet have been correlated by the (deliberately conservative) curated
table or the noisier keyword fallback below.

Two independent checks feed the same "vuln_findings" table:

- Firmware currency (Part 2): reads `update` entities with
  device_class == "firmware" — no network involved, always runs.
- CVE correlation (Part 3): queries the NVD API 2.0 per device, gated by
  a curated manufacturer->CPE table first and a noisier keyword search as
  fallback — network, best-effort, independently fails per device.

The optional NVD API key lives in the private secret store
(secrets_store.py) and is fetched immediately before each HTTP request,
then dropped when the request completes (work item SEC-3): no parameter,
attribute, or module global carries the key between requests.
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
NVD_TIMEOUT_SECONDS = 15
# Without a key NVD allows ~5 req/30s; with a key, ~50/30s. These sleeps are
# applied after every real HTTP call (not on cache hits) and are chosen with
# headroom rather than cutting it exactly to the published limit.
NVD_DELAY_NO_KEY = 6
NVD_DELAY_WITH_KEY = 0.7

# Re-fetch the same match_string at most once per this window. Backed by an
# in-memory dict on the tracker instance rather than anything persisted: a
# HA restart just costs one extra full re-fetch on the next scan, which is
# an acceptable trade for not having to reconcile a second cache format
# against the finding store.
MATCH_STRING_CACHE_TTL = timedelta(days=7)

# Findings persisted per device per scan, taking the highest CVSS scores
# first, so one device with a very active CPE entry can't flood the store.
MAX_FINDINGS_PER_DEVICE = 10

MAX_SUMMARY_CHARS = 500

# Device-overview status buckets for the SOC Dashboard's "All Devices" table
# and status tiles. Distinct from the finding-lifecycle STATUS_* vocabulary
# in const.py — these describe a device's actual HA availability, not a
# finding's lifecycle. Deliberately NOT derived from vulnerability severity
# (that's a separate axis, shown in its own donut/gauge) — this is purely
# "is Home Assistant actually hearing from this device right now", straight
# off the device/entity registries and live entity states:
#   disabled     - device.disabled_by is set (by a user, its integration, or
#                   its config entry) — intentionally turned off, not a fault.
#   no_entities  - no (enabled) entities registered for this device at all,
#                   so there is nothing to report a live state from.
#   unavailable  - every one of its entities is currently unavailable/unknown.
#   partial      - some but not all of its entities are unavailable/unknown.
#   available    - none of its entities are unavailable/unknown.
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

# Proxy risk score (0-10, the same scale as CVSS) for a device whose only
# open finding is the network-free firmware-currency heuristic, which has
# no CVSS of its own to report.
FIRMWARE_ONLY_RISK_SCORE = 5.0

# Starter manufacturer -> NVD virtualMatchString table. Deliberately small
# and manufacturer-only (model substrings are left blank below); this is
# meant to be extended over time with more vendors and, eventually,
# model-specific CPEs rather than whole-vendor wildcards.
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


def _match_curated_cpe(manufacturer: str, model: str) -> str | None:
    manufacturer_lower = manufacturer.lower()
    model_lower = model.lower()
    for (mfr_substr, model_substr), cpe_prefix in CURATED_CPE_MAP.items():
        if mfr_substr not in manufacturer_lower:
            continue
        if model_substr and model_substr not in model_lower:
            continue
        return cpe_prefix
    return None


def _extract_cvss(cve: dict[str, Any]) -> float | None:
    metrics = cve.get("metrics", {})
    # Prefer the newest CVSS version present; fall back progressively rather
    # than averaging or picking the highest, so the score reflects a single
    # coherent scoring methodology.
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for entry in metrics.get(key) or []:
            score = entry.get("cvssData", {}).get("baseScore")
            if score is not None:
                return float(score)
    return None


def _severity_for_score(score: float | None) -> str:
    if score is None:
        # Absent != low: an unscored CVE is not a confirmed-low-severity
        # claim, so it gets its own bucket rather than being folded into
        # "low".
        return SEVERITY_INFO
    if score >= 9.0:
        return SEVERITY_CRITICAL
    if score >= 7.0:
        return SEVERITY_HIGH
    if score >= 4.0:
        return SEVERITY_MEDIUM
    return SEVERITY_LOW


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

    Combines a network-free firmware-currency check (Part 2) with a
    best-effort NVD CVE correlation (Part 3). A scan never raises out of
    `async_run_scan`: firmware-currency findings are saved even if CVE
    correlation fails entirely, and a single device's NVD failure never
    aborts the rest of the scan.
    """

    def __init__(
        self, hass: HomeAssistant, store: HaSocData, secrets: HaSocSecretStore
    ) -> None:
        self.hass = hass
        self.store = store
        # The secret store reference, not the key: the key itself is asked
        # for one request at a time inside _async_query_nvd (SEC-3).
        self._secrets = secrets
        # match_string -> last time it was actually sent to NVD (see
        # MATCH_STRING_CACHE_TTL). In-memory only; see module docstring.
        self._last_fetched: dict[str, datetime] = {}

    async def async_run_scan(self) -> list[dict]:
        registry = dr.async_get(self.hass)
        physical_devices = [
            device
            for device in registry.devices.values()
            if device.entry_type != dr.DeviceEntryType.SERVICE
        ]
        devices_by_id = {device.id: device for device in physical_devices}

        findings: list[dict] = []
        findings.extend(self._check_firmware_currency(devices_by_id))

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

        Pure read/aggregate over device_registry + the existing
        vuln_findings table — never triggers a scan itself (call
        `async_run_scan` separately for that, e.g. from the periodic loop
        or a "scan now" action).

        Risk score is deliberately kept on the same 0-10 scale as CVSS
        itself: the highest CVSS among that device's open (non-dismissed)
        findings. A device whose only open finding is the firmware-currency
        heuristic (which carries no CVSS) gets a fixed proxy score instead
        of being scored as risk-free — see FIRMWARE_ONLY_RISK_SCORE.

        `status` is intentionally a SEPARATE axis from risk score/severity —
        see the DEVICE_STATUS_* constants above. It reflects only whether
        Home Assistant is actually hearing from the device right now, not
        whether it has a known vulnerability.
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
                    # Folded into "low" for this 4-column view — an
                    # unscored CVE still belongs somewhere on the table,
                    # and a 5th column for a rare case isn't worth it here.
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
            # Intentionally turned off (by a user, its integration, or its
            # config entry) — not a fault, so it must never look like one.
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
        # Presence only, never the value: the pacing between NVD calls
        # depends on whether a key exists (50 req/30s with one, ~5 without),
        # and a boolean is all that decision needs. The value itself is
        # fetched per request inside _async_query_nvd.
        has_api_key = bool(await self._secrets.async_get(CONF_NVD_API_KEY))
        findings: list[dict] = []
        # Reused across devices that share a match_string within this one
        # scan (e.g. every Shelly device hits the same curated wildcard),
        # independent of the multi-day MATCH_STRING_CACHE_TTL gate below.
        run_cache: dict[str, list[dict[str, Any]] | None] = {}

        for device in devices:
            manufacturer = device.manufacturer
            if not manufacturer:
                continue
            model = device.model or ""

            cpe_prefix = _match_curated_cpe(manufacturer, model)
            if cpe_prefix is not None:
                confidence = CONFIDENCE_CURATED_MAP
                query_param = "virtualMatchString"
                match_string = cpe_prefix
            elif model:
                # keywordSearch matches free-text description fields, not
                # confirmed affected-product (CPE) entries, so it is much
                # noisier than the curated table above — hence the lower
                # confidence tier.
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
                # Only a successful fetch earns the multi-day cache entry —
                # a transient failure should be retried on the next scan
                # (hours away), not blocked for a full week. Still recorded
                # in run_cache either way so a second device sharing this
                # match_string within the *same* run doesn't re-hit NVD.
                if vulnerabilities is not None:
                    self._last_fetched[match_string] = now
                run_cache[match_string] = vulnerabilities
                await asyncio.sleep(
                    NVD_DELAY_WITH_KEY if has_api_key else NVD_DELAY_NO_KEY
                )

            if not vulnerabilities:
                continue

            for finding in self._build_findings_for_device(
                device, vulnerabilities, confidence, match_string, now_iso
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
        session = async_get_clientsession(self.hass)
        params = {query_param: match_string, "resultsPerPage": str(NVD_RESULTS_PER_PAGE)}
        # Fetched immediately before the request and dropped with this
        # frame when it returns (SEC-3); no attribute holds it between
        # requests.
        api_key = await self._secrets.async_get(CONF_NVD_API_KEY)
        headers = {"apiKey": api_key} if api_key else None

        try:
            async with asyncio.timeout(NVD_TIMEOUT_SECONDS):
                async with session.get(
                    NVD_API_URL, params=params, headers=headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.warning(
                "NVD query failed for %s=%s: %s", query_param, match_string, err
            )
            return None

        return data.get("vulnerabilities", [])

    def _build_findings_for_device(
        self,
        device: dr.DeviceEntry,
        vulnerabilities: list[dict[str, Any]],
        confidence: str,
        match_string: str,
        now_iso: str,
    ) -> list[dict]:
        device_name = _device_name(device)

        candidates: list[tuple[float, str, float | None, str, str]] = []
        for vuln in vulnerabilities:
            cve = vuln.get("cve", {})
            cve_id = cve.get("id")
            if not cve_id:
                continue
            cvss = _extract_cvss(cve)
            severity = _severity_for_score(cvss)
            summary = _cve_summary(cve, cvss)
            # Sort key only: unscored CVEs sort after every scored one
            # rather than being dropped, since they're still real findings.
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
