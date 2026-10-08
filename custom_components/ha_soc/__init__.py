"""HA SOC: centralized user security and NOC/SOC visibility for Home Assistant.

Wiring only: composes the feature managers and owns the periodic analysis loop.
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from functools import partial
from dataclasses import dataclass, field
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration

from .audit import AuditLog
from .const import DOMAIN, PLATFORMS, SIGNAL_UPDATE
from .crash_forensics import CrashForensics
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
from .terminal import (
    TerminalSessions,
    async_register_pairing_service,
    async_unregister_pairing_service,
)
from .repairs import (
    async_sync_admin_mfa_issues,
    async_sync_stale_token_issues,
    async_sync_tls_verify_issue,
    async_sync_vuln_issues,
)
from .risk import RiskEngine
from .scanner import IntegrationScanner
from .secrets_store import HaSocSecretStore, async_migrate_legacy_secrets
from .resource_watchdog import ResourceWatchdog
from .observe_push import DATA_QUEUE_CARRY, ObservePusher, SnapshotCollector
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
# Core waits at most 10 seconds for a failed setup's unload tasks. The stops after
# the audit log and before the store write share this budget so the write starts
# inside that window. Terminal sessions have a budget of their own, and the audit
# log stop has none: cancelling it would lose records, so it is never starved.
SERVICE_STOP_BUDGET = 7.0
TERMINAL_CLOSE_BUDGET = 3.0
# The ledger records transitions, not samples, so a slow cadence loses
# nothing: a change that persists is still caught on the next pass.
UNIFI_LEDGER_INTERVAL = timedelta(hours=6)


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
    terminal: TerminalSessions
    crash_forensics: CrashForensics
    observe: ObservePusher
    _stopped: bool = field(default=False, init=False, repr=False)

    async def async_stop_services(self) -> None:
        """Stop every service this entry started, in dependency order, once.

        Called from the unload path and registered with ``entry.async_on_unload``
        before the first service starts, so a setup that fails or is retried
        leaves no timer, listener or log handler behind. Every stop is safe on a
        service that never started. A stop that raises is logged and the rest
        still run.
        """
        if self._stopped:
            return
        self._stopped = True
        # The audit log stops before the exporter so its last flush still reaches
        # the exporter's drain; the store is written last because the stops above
        # (the audit head mirror, the health records) change it.
        loop = asyncio.get_running_loop()
        await self._stop_one("terminal sessions", self.terminal.async_close_all, TERMINAL_CLOSE_BUDGET)
        # No time limit: the stop flushes buffered records, and a cancelled flush
        # drops them and leaves a writer thread running that the next AuditLog
        # could race. Its own work is bounded by the disk write.
        await self._stop_one("audit log", self.audit.async_stop, None)
        deadline = loop.time() + SERVICE_STOP_BUDGET
        for label, stop in (
            ("syslog exporter", partial(self.syslog.async_stop, drain=True)),
            ("health", self.health.async_stop),
            ("scanner", self.scanner.async_stop),
            ("resource watchdog", self.watchdog.async_stop),
            ("resource watchdog history", self.watchdog.async_flush_history),
            ("Observe push", self.observe.async_stop),
        ):
            await self._stop_one(label, stop, max(deadline - loop.time(), 0.1))
        await self._stop_one("store", self.store.async_flush, None)

    @staticmethod
    async def _stop_one(label: str, stop, budget: float | None) -> None:
        """Run one stop, bounded by ``budget`` seconds when given, logging any failure.

        A stop cancelled by its budget is not retried (the runtime is already
        marked stopped), so that service may be left half-stopped.
        """
        try:
            result = stop()
            if inspect.isawaitable(result):
                if budget is None:
                    await result
                else:
                    async with asyncio.timeout(budget):
                        await result
        except TimeoutError:
            _LOGGER.error("HA SOC gave up waiting for %s to stop", label)
        except Exception:  # noqa: BLE001 - one failed stop must not strand the others
            _LOGGER.exception("HA SOC could not stop %s", label)


# Plain alias, not a PEP 695 type statement: keeps Python 3.11 importable.
HaSocConfigEntry = ConfigEntry[HaSocRuntimeData]


def get_runtime_data(hass: HomeAssistant) -> HaSocRuntimeData:
    """HA SOC is single-instance; fetch the one loaded entry's runtime data.

    Raises ``RuntimeError("HA SOC is not set up")`` when there is no entry or it
    is not loaded (never set up, failed setup, or unloaded).
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    # Core deletes the attribute on unload, so a plain read raises AttributeError.
    runtime = getattr(entries[0], "runtime_data", None) if entries else None
    if runtime is None:
        raise RuntimeError("HA SOC is not set up")
    return runtime


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
    # Before anything can arm a delayed save (the secret migration re-arms one when
    # its write fails): a setup that fails from here on writes it out and clears
    # its timer instead of leaving it to overwrite the retry's data.
    entry.async_on_unload(store.async_flush)

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
    terminal = TerminalSessions(hass, audit, secrets)
    crash_forensics = CrashForensics(hass, store, audit, watchdog)
    observe = ObservePusher(
        hass,
        store,
        secrets,
        SnapshotCollector(
            hass, store, health=health, watchdog=watchdog, crash_forensics=crash_forensics
        ).async_collect,
    )

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
        terminal=terminal,
        crash_forensics=crash_forensics,
        observe=observe,
    )

    # Registered before anything starts: core runs these callbacks when this setup
    # fails or is retried as well as on unload, so no service outlives a failed
    # attempt. Core starts them in reverse order as eager tasks, so the synchronous
    # runtime drop completes before the stop finishes awaiting.
    entry.async_on_unload(lambda: _async_forget_runtime(entry))
    entry.async_on_unload(entry.runtime_data.async_stop_services)

    # Core does not unload config entries when Home Assistant stops, so the stop path
    # above never runs on a restart. Write the throttled history ring on the stop event
    # as well; it is a plain listener so removing it on unload is always safe.
    async def _async_flush_history_on_stop(_event: Event) -> None:
        await entry.runtime_data.watchdog.async_flush_history()

    entry.async_on_unload(
        hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, _async_flush_history_on_stop)
    )
    entry.async_on_unload(lambda: _async_unregister_everything(hass))

    async_sync_tls_verify_issue(hass, store.settings)
    await audit.async_start()
    syslog.async_start(entry)
    await health.async_start()
    scanner.async_start(hass)
    # Load the persisted ring (and snapshot it to .prev) before the watchdog
    # can write a sample of its own for this boot.
    await watchdog.async_load_history()
    watchdog.async_start()
    crash_forensics.async_start(entry)
    # Off by default: a no-op unless the owner enabled it and filled in the options.
    await observe.async_start(entry)

    async_register_websocket_api(hass)
    async_register_probe_service(hass, store, audit, secrets)
    async_register_external_audit_service(hass, store, audit, secrets)
    async_register_pairing_service(hass, store, audit, secrets)
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
    async def _async_unifi_ledger_check(_now=None) -> None:
        """Record a UniFi configuration drift transition, if there is one.

        Only the periodic pass writes history and audits; reading the ledger
        from the panel never does, so the record says when the change was
        observed rather than when someone happened to look.
        """
        try:
            from . import config_ledger

            state = await config_ledger.async_ledger_state(hass, store, secrets)
            if config_ledger.record_drift(store, audit, state):
                async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_network_security")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("HA SOC UniFi configuration ledger check failed")

    entry.async_on_unload(
        async_track_time_interval(hass, _async_config_check, CONFIG_CHECK_INTERVAL)
    )
    entry.async_on_unload(
        async_track_time_interval(
            hass, _async_unifi_ledger_check, UNIFI_LEDGER_INTERVAL
        )
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


@callback
def _async_forget_runtime(entry: HaSocConfigEntry) -> None:
    """Drop the runtime of an entry whose setup failed, so lookups see "not set up".

    Core deletes it itself after a successful unload; it does not after a failed setup.
    """
    if hasattr(entry, "runtime_data"):
        object.__delattr__(entry, "runtime_data")


async def _async_unregister_everything(hass: HomeAssistant) -> None:
    """Remove the services and the panel; each call is safe when nothing is registered."""
    async_unregister_probe_service(hass)
    async_unregister_external_audit_service(hass)
    async_unregister_pairing_service(hass)
    await async_unregister_panel(hass)


async def async_unload_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None:
        await runtime.async_stop_services()

    if entry.disabled_by is not None:
        # A disabled entry is not coming back with a reload; do not hold its queue for nothing.
        hass.data.get(DATA_QUEUE_CARRY, {}).pop(entry.entry_id, None)

    await _async_unregister_everything(hass)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: HaSocConfigEntry) -> None:
    """Forget the Observe queue a stopped push left for a reload; the entry is gone for good."""
    hass.data.get(DATA_QUEUE_CARRY, {}).pop(entry.entry_id, None)
