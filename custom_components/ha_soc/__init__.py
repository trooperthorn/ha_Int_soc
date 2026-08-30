"""HA SOC — centralized user security & NOC/SOC visibility for Home Assistant.

Wiring only: this module composes the feature managers defined in the other
files and owns the periodic analysis loop. Each manager is independently
testable and knows nothing about the others except through the plain data
it reads from HaSocData (see store.py) — see each module's docstring for
its own contract.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

from .audit import AuditLog
from .const import DOMAIN, PLATFORMS, SIGNAL_UPDATE
from .detections import DetectionEngine
from .health import IntegrationHealth
from .mfa_policy import async_enforce_mfa_policy
from .panel import async_register_panel, async_unregister_panel
from .permissions import PermissionsMatrix
from .probe import async_register_probe_service, async_unregister_probe_service
from .repairs import (
    async_sync_admin_mfa_issues,
    async_sync_stale_token_issues,
    async_sync_vuln_issues,
)
from .risk import RiskEngine
from .scanner import IntegrationScanner
from .resource_watchdog import ResourceWatchdog
from .store import HaSocData, SettingsData
from .users import LiveSessionRegistry, UsersManager
from .vulns import DeviceVulnerabilityTracker
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

ANALYSIS_INTERVAL = timedelta(minutes=5)
VULN_SCAN_INTERVAL = timedelta(hours=24)
SCANNER_SWEEP_INTERVAL = timedelta(days=7)
CONFIG_CHECK_INTERVAL = timedelta(hours=6)


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
    watchdog: "ResourceWatchdog"


# Plain generic alias rather than a PEP 695 `type` statement — keeps this
# module importable on Python 3.11, not just 3.12+.
HaSocConfigEntry = ConfigEntry[HaSocRuntimeData]


def get_runtime_data(hass: HomeAssistant) -> HaSocRuntimeData:
    """HA SOC is single-instance — fetch the one loaded entry's runtime data."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries or entries[0].runtime_data is None:
        raise RuntimeError("HA SOC is not set up")
    return entries[0].runtime_data


def _seed_settings_from_options_once(
    store: HaSocData, options: Mapping[str, Any], *, had_stored_data: bool
) -> None:
    """Seed store.settings from entry.options, but only on the very first run.

    The options flow can be reached before the integration has ever
    finished setup, and `entry.options` is written on every save
    regardless — so on a genuinely fresh install, a save made before first
    load still needs to take effect. After that first load, store.settings
    is the sole source of truth: every writer (options flow, in-panel
    Settings tab) updates it live, and entry.options becomes a snapshot
    copy for pre-load prefill only, never read again — re-seeding on every
    restart would let a stale entry.options value clobber a setting the
    user only ever changed from the panel.
    """
    if had_stored_data or not options:
        return
    known_keys = SettingsData.__annotations__.keys()
    seed = {k: v for k, v in options.items() if k in known_keys}
    if seed:
        store.async_update_settings(**seed)


async def async_setup_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    store = HaSocData(hass)
    had_stored_data = await store.async_load()
    _seed_settings_from_options_once(store, entry.options, had_stored_data=had_stored_data)

    users = UsersManager(hass)
    live_sessions = LiveSessionRegistry()
    audit = AuditLog(hass, store)
    permissions = PermissionsMatrix(hass, store)
    health = IntegrationHealth(hass, store)
    vulns = DeviceVulnerabilityTracker(hass, store)
    scanner = IntegrationScanner(hass, store)
    risk = RiskEngine(hass, store, users=users)
    detections = DetectionEngine(hass, store, audit=audit, users=users)
    watchdog = ResourceWatchdog(hass, store, audit)

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
        watchdog=watchdog,
    )

    await audit.async_start()
    await permissions.async_start()
    await health.async_start()
    scanner.async_start(hass)
    watchdog.async_start()

    async_register_websocket_api(hass)
    # The audit log is handed over so a rejected Probe callback can be
    # recorded as probe_auth_rejected; on non-Supervisor installs the call
    # registers nothing (see probe.py).
    async_register_probe_service(hass, store, audit)
    await async_register_panel(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_periodic_analysis(_now=None) -> None:
        try:
            await health.async_run_misconfig_checks()
            await detections.async_run_pass()
            await risk.async_recompute_all()
            await risk.async_compute_posture()
            user_list = await users.async_list_users()
            await async_sync_admin_mfa_issues(hass, user_list)
            await async_sync_stale_token_issues(hass)
            await async_enforce_mfa_policy(store, users, audit, user_list)
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

    async def _async_config_check(_now=None) -> None:
        try:
            await health.async_run_config_check()
        except Exception:  # noqa: BLE001
            _LOGGER.exception("HA SOC config-validity check failed")
        finally:
            async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_dashboard")

    entry.async_on_unload(
        async_track_time_interval(hass, _async_periodic_analysis, ANALYSIS_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_vuln_scan, VULN_SCAN_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_scanner_sweep, SCANNER_SWEEP_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(hass, _async_config_check, CONFIG_CHECK_INTERVAL)
    )

    # Kick off a first pass shortly after startup rather than waiting a full
    # interval, so the dashboard isn't empty on a fresh install.
    hass.async_create_task(_async_periodic_analysis())
    hass.async_create_task(_async_config_check())
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
        runtime.watchdog.async_stop()

    async_unregister_probe_service(hass)
    await async_unregister_panel(hass)
    return True
