"""HA SOC: centralized user security and NOC/SOC visibility for Home Assistant.

Wiring only: composes the feature managers and owns the periodic analysis loop.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration

from .audit import AuditLog
from .const import DOMAIN, PLATFORMS, SIGNAL_UPDATE
from .detections import DetectionEngine
from .health import IntegrationHealth
from .mfa_policy import async_enforce_mfa_policy
from .panel import async_register_panel, async_unregister_panel
from .permissions import PermissionsMatrix
from .external_audit import (
    async_register_external_audit_service,
    async_unregister_external_audit_service,
)
from .probe import async_register_probe_service, async_unregister_probe_service
from .repairs import (
    async_sync_admin_mfa_issues,
    async_sync_stale_token_issues,
    async_sync_vuln_issues,
)
from .risk import RiskEngine
from .scanner import IntegrationScanner
from .secrets_store import HaSocSecretStore, async_migrate_legacy_secrets
from .resource_watchdog import ResourceWatchdog
from .store import HaSocData
from .syslog_export import SyslogExporter
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
    """Everything a WebSocket command or entity platform needs to reach.

    ``secrets`` lives here only; it is never placed in hass.data.
    """

    store: HaSocData
    secrets: HaSocSecretStore
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
    syslog: SyslogExporter


# Plain alias, not a PEP 695 type statement: keeps Python 3.11 importable.
HaSocConfigEntry = ConfigEntry[HaSocRuntimeData]


def get_runtime_data(hass: HomeAssistant) -> HaSocRuntimeData:
    """HA SOC is single-instance; fetch the one loaded entry's runtime data."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries or entries[0].runtime_data is None:
        raise RuntimeError("HA SOC is not set up")
    return entries[0].runtime_data


def _scrub_entry_options_once(hass: HomeAssistant, entry: HaSocConfigEntry) -> None:
    """Empty a legacy entry.options mirror, once. Key names only are logged."""
    if not entry.options:
        return
    _LOGGER.info(
        "HA SOC: clearing the legacy entry.options settings mirror "
        "(keys removed: %s). Settings live in the HA SOC store; secrets "
        "live in the private secret store.",
        ", ".join(sorted(entry.options)),
    )
    hass.config_entries.async_update_entry(entry, options={})


async def async_setup_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    store = HaSocData(hass)
    await store.async_load()

    # Loaded before anything else can want a credential.
    secrets = HaSocSecretStore(hass)
    await secrets.async_load()
    await async_migrate_legacy_secrets(secrets, store)
    _scrub_entry_options_once(hass, entry)

    users = UsersManager(hass)
    live_sessions = LiveSessionRegistry()
    audit = AuditLog(hass, store)
    integration = await async_get_integration(hass, DOMAIN)
    syslog = SyslogExporter(
        hass,
        store,
        integration_version=str(integration.version) if integration.version else "-",
    )
    audit.async_set_syslog_exporter(syslog)
    permissions = PermissionsMatrix(hass, store)
    health = IntegrationHealth(hass, store)
    vulns = DeviceVulnerabilityTracker(hass, store, secrets)
    scanner = IntegrationScanner(hass, store)
    risk = RiskEngine(hass, store, users=users)
    detections = DetectionEngine(hass, store, audit=audit, users=users)
    watchdog = ResourceWatchdog(hass, store, audit)

    entry.runtime_data = HaSocRuntimeData(
        store=store,
        secrets=secrets,
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
        syslog=syslog,
    )

    await audit.async_start()
    syslog.async_start(entry)
    await permissions.async_start()
    await health.async_start()
    scanner.async_start(hass)
    watchdog.async_start()

    async_register_websocket_api(hass)
    async_register_probe_service(hass, store, audit, secrets)
    async_register_external_audit_service(hass, store, audit, secrets)
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
            findings = await vulns.async_run_scan()
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

    # First pass right after startup so a fresh install's dashboard is not empty.
    entry.async_create_task(
        hass, _async_periodic_analysis(), "HA SOC initial analysis"
    )
    entry.async_create_task(hass, _async_config_check(), "HA SOC initial config check")
    if store.settings.get("scanner_enabled", True):
        entry.async_create_task(
            hass, _async_scanner_sweep(), "HA SOC initial integration scan"
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime = entry.runtime_data
    if runtime is not None:
        await runtime.audit.async_stop()
        await runtime.syslog.async_stop(drain=True)
        await runtime.permissions.async_stop()
        await runtime.health.async_stop()
        runtime.scanner.async_stop()
        runtime.watchdog.async_stop()

    async_unregister_probe_service(hass)
    async_unregister_external_audit_service(hass)
    await async_unregister_panel(hass)
    return True
