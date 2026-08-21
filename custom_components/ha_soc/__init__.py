"""HA SOC — centralized user security & NOC/SOC visibility for Home Assistant.

Wiring only: this module composes the feature managers defined in the other
files and owns the periodic analysis loop. Each manager is independently
testable and knows nothing about the others except through the plain data
it reads from HaSocData (see store.py) — see each module's docstring for
its own contract.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .audit import AuditLog
from .const import DOMAIN, PLATFORMS, SIGNAL_UPDATE
from .detections import DetectionEngine
from .health import IntegrationHealth
from .panel import async_register_panel, async_unregister_panel
from .permissions import PermissionsMatrix
from .repairs import async_sync_admin_mfa_issues, async_sync_vuln_issues
from .risk import RiskEngine
from .scanner import IntegrationScanner
from .store import HaSocData
from .users import LiveSessionRegistry, UsersManager
from .vulns import DeviceVulnerabilityTracker
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

ANALYSIS_INTERVAL = timedelta(minutes=5)
VULN_SCAN_INTERVAL = timedelta(hours=24)
SCANNER_SWEEP_INTERVAL = timedelta(days=7)


@dataclass
class HaSocRuntimeData:
    """Everything a WebSocket command or entity platform needs to reach."""

    store: HaSocData
    users: UsersManager
    live_sessions: LiveSessionRegistry
    audit: AuditLog
    permissions: PermissionsMatrix
    health: IntegrationHealth
    vulns: DeviceVulnerabilityTracker
    scanner: IntegrationScanner
    risk: RiskEngine
    detections: DetectionEngine


# Plain generic alias rather than a PEP 695 `type` statement — keeps this
# module importable on Python 3.11, not just 3.12+.
HaSocConfigEntry = ConfigEntry[HaSocRuntimeData]


def get_runtime_data(hass: HomeAssistant) -> HaSocRuntimeData:
    """HA SOC is single-instance — fetch the one loaded entry's runtime data."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries or entries[0].runtime_data is None:
        raise RuntimeError("HA SOC is not set up")
    return entries[0].runtime_data


async def async_setup_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    store = HaSocData(hass)
    await store.async_load()

    users = UsersManager(hass)
    live_sessions = LiveSessionRegistry()
    audit = AuditLog(hass, store)
    permissions = PermissionsMatrix(hass, store)
    health = IntegrationHealth(hass, store)
    vulns = DeviceVulnerabilityTracker(hass, store)
    scanner = IntegrationScanner(hass, store)
    risk = RiskEngine(hass, store, users=users)
    detections = DetectionEngine(hass, store, audit=audit, users=users)

    entry.runtime_data = HaSocRuntimeData(
        store=store,
        users=users,
        live_sessions=live_sessions,
        audit=audit,
        permissions=permissions,
        health=health,
        vulns=vulns,
        scanner=scanner,
        risk=risk,
        detections=detections,
    )

    await audit.async_start()
    await permissions.async_start()
    await health.async_start()
    scanner.async_start(hass)

    async_register_websocket_api(hass)
    await async_register_panel(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_periodic_analysis(_now=None) -> None:
        try:
            await health.async_run_misconfig_checks()
            await detections.async_run_pass()
            await risk.async_recompute_all()
            await risk.async_compute_posture()
            await async_sync_admin_mfa_issues(hass, await users.async_list_users())
        except Exception:  # noqa: BLE001 - never let the analysis loop die silently
            _LOGGER.exception("HA SOC periodic analysis pass failed")
        else:
            async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_dashboard")
        finally:
            async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_detections")

    async def _async_vuln_scan(_now=None) -> None:
        try:
            findings = await vulns.async_run_scan(api_key=store.settings.get("nvd_api_key") or None)
            await async_sync_vuln_issues(hass, findings)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("HA SOC vulnerability scan failed")
        finally:
            async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_vulns")

    async def _async_scanner_sweep(_now=None) -> None:
        if not store.settings.get("scanner_enabled", True):
            return
        try:
            await scanner.async_scan_all()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("HA SOC integration scanner sweep failed")
        finally:
            async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_scanner")

    entry.async_on_unload(
        async_track_time_interval(hass, _async_periodic_analysis, ANALYSIS_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_vuln_scan, VULN_SCAN_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_scanner_sweep, SCANNER_SWEEP_INTERVAL)
    )

    # Kick off a first pass shortly after startup rather than waiting a full
    # interval, so the dashboard isn't empty on a fresh install.
    hass.async_create_task(_async_periodic_analysis())
    if store.settings.get("scanner_enabled", True):
        hass.async_create_task(_async_scanner_sweep())

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime = entry.runtime_data
    if runtime is not None:
        await runtime.audit.async_stop()
        await runtime.permissions.async_stop()
        await runtime.health.async_stop()
        runtime.scanner.async_stop()

    await async_unregister_panel(hass)
    return True
