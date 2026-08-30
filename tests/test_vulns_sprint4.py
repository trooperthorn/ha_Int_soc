"""Sprint 4 vulns.py behaviors (work plan item 4.9, decision D-12): the
NVD toggle, scan serialization, result paging before ranking, and the
vendor-only-match INFO severity.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant

from custom_components.ha_soc.secrets_store import HaSocSecretStore
from custom_components.ha_soc.store import HaSocData
from custom_components.ha_soc.vulns import (
    NVD_MAX_PAGES,
    NVD_RESULTS_PER_PAGE,
    DeviceVulnerabilityTracker,
    _match_curated_cpe,
)


@pytest.fixture
async def tracker(hass: HomeAssistant) -> DeviceVulnerabilityTracker:
    store = HaSocData(hass)
    await store.async_load()
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    return DeviceVulnerabilityTracker(hass, store, secrets)


async def test_cve_pass_respects_toggle(hass: HomeAssistant, tracker: DeviceVulnerabilityTracker) -> None:
    correlate = AsyncMock(return_value=[])
    with patch.object(tracker, "_async_correlate_cves", correlate):
        # Off: only the network-free firmware pass runs; NVD is never hit.
        tracker.store.data["settings"]["nvd_lookups_enabled"] = False
        await tracker.async_run_scan()
        correlate.assert_not_called()

        # On (and the on-by-default fallback when the key is absent).
        tracker.store.data["settings"].pop("nvd_lookups_enabled", None)
        await tracker.async_run_scan()
        correlate.assert_awaited_once()


async def test_vuln_scan_is_serialized(hass: HomeAssistant, tracker: DeviceVulnerabilityTracker) -> None:
    active = 0
    max_active = 0

    async def _slow_correlate(devices):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        # Yield a few times so a genuinely concurrent second scan would
        # be observed overlapping.
        for _ in range(3):
            await asyncio.sleep(0)
        active -= 1
        return []

    with patch.object(tracker, "_async_correlate_cves", new=_slow_correlate):
        await asyncio.gather(tracker.async_run_scan(), tracker.async_run_scan())

    assert max_active == 1


async def test_nvd_query_pages_before_ranking(
    hass: HomeAssistant, tracker: DeviceVulnerabilityTracker
) -> None:
    """The query walks NVD's startIndex pagination (bounded by
    NVD_MAX_PAGES) instead of ranking only the first page."""
    total = NVD_RESULTS_PER_PAGE * 2 + 3
    calls: list[int] = []

    class _FakeResponse:
        def __init__(self, start: int) -> None:
            self._start = start

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        def raise_for_status(self) -> None:
            return None

        async def json(self):
            batch = [
                {"cve": {"id": f"CVE-2026-{n:04}"}}
                for n in range(self._start, min(self._start + NVD_RESULTS_PER_PAGE, total))
            ]
            return {"totalResults": total, "vulnerabilities": batch}

    class _FakeSession:
        def get(self, url, params=None, headers=None):
            start = int(params["startIndex"])
            calls.append(start)
            return _FakeResponse(start)

    with (
        patch(
            "custom_components.ha_soc.vulns.async_get_clientsession",
            return_value=_FakeSession(),
        ),
        patch("custom_components.ha_soc.vulns.asyncio.sleep", new=AsyncMock()),
    ):
        results = await tracker._async_query_nvd("keywordSearch", "acme widget")

    assert len(results) == total
    assert calls == [0, NVD_RESULTS_PER_PAGE, NVD_RESULTS_PER_PAGE * 2]
    assert len(calls) <= NVD_MAX_PAGES


def test_vendor_only_curated_match_is_flagged_as_such() -> None:
    match = _match_curated_cpe("Shelly Europe", "Plus 1PM")
    assert match is not None
    cpe, vendor_only = match
    assert cpe.startswith("cpe:2.3:o:shelly")
    assert vendor_only is True


async def test_vendor_only_match_findings_are_info(
    hass: HomeAssistant, tracker: DeviceVulnerabilityTracker
) -> None:
    device = SimpleNamespace(id="dev1", name_by_user=None, name="Shelly Plug")
    vulnerabilities = [
        {
            "cve": {
                "id": "CVE-2026-0001",
                "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": 9.8}}]},
                "descriptions": [{"lang": "en", "value": "Critical RCE."}],
            }
        }
    ]
    findings = tracker._build_findings_for_device(
        device, vulnerabilities, "curated_map", "cpe:2.3:o:shelly:*", "now",
        vendor_only=True,
    )
    assert len(findings) == 1
    # The CVSS still rides along for the analyst, but a vendor-wide
    # wildcard match is informational, never a paged severity.
    assert findings[0]["cvss"] == 9.8
    assert findings[0]["severity"] == "info"
    assert "Vendor-wide match only" in findings[0]["summary"]

    # A model-specific match keeps the CVSS-derived severity.
    findings = tracker._build_findings_for_device(
        device, vulnerabilities, "curated_map", "cpe:2.3:o:shelly:plus1pm", "now",
        vendor_only=False,
    )
    assert findings[0]["severity"] == "critical"
