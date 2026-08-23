"""Versioned persistence for HA SOC's configuration and finding state.

This Store holds everything EXCEPT the audit log itself: settings, the
permissions matrix, and the lifecycle state (new/confirmed/dismissed/
resolved) of vulnerability, misconfiguration, scanner, and detection
findings. It deliberately excludes the audit log and raw event history,
which are high-volume and live in their own rotating JSONL files
(see audit.py) — rewriting one Store file on every audit event would mean
serializing the whole history on every write.
"""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_ACCESS_LEVEL,
    DEFAULT_AUDIT_MAX_BYTES,
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_MFA_GRACE_PERIOD_DAYS,
    DEFAULT_MFA_POLICY,
    DEFAULT_RISK_LEARNING_PERIOD_DAYS,
    DEFAULT_SCANNER_ENABLED,
    DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
    DEFAULT_SECURITY_SOURCES_ENABLED,
    STORAGE_KEY,
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION_MAJOR,
    STORAGE_VERSION_MINOR,
)

_LOGGER = logging.getLogger(__name__)


class SettingsData(TypedDict):
    audit_retention_days: int
    audit_max_bytes: int
    scanner_enabled: bool
    scanner_network_checks_enabled: bool
    nvd_api_key: str | None
    risk_learning_period_days: int
    access_level: str
    mfa_policy: str
    mfa_grace_period_days: int
    # domain (integration or entity-platform) -> included in the
    # Security Integrations Health dashboard section. See const.py's
    # SECURITY_INTEGRATION_DOMAINS/SECURITY_ENTITY_DOMAINS for the known
    # set — a domain missing from this dict is treated as enabled (opt-out,
    # not opt-in), so a future addition to the known set doesn't silently
    # start dark for an existing install.
    security_sources_enabled: dict[str, bool]


class StoreData(TypedDict):
    """Shape of the JSON persisted under .storage/ha_soc.storage."""

    settings: SettingsData
    # user_id -> dashboard url_path -> {"views": {view_path: bool}, "sidebar_hidden": bool}
    permissions_matrix: dict[str, dict[str, Any]]
    # finding_id -> finding record (see vulns.py / health.py / scanner.py for field shapes)
    vuln_findings: dict[str, dict[str, Any]]
    misconfig_findings: dict[str, dict[str, Any]]
    scanner_findings: dict[str, dict[str, Any]]
    # detection_id -> detection record (see detections.py)
    detections: dict[str, dict[str, Any]]
    # per-user behavioral baselines the detection engine has learned
    # (hour-of-day histograms, seen /24 prefixes, seen destructive domains,
    # per-user learning-period start timestamp)
    user_baselines: dict[str, dict[str, Any]]
    # daily posture-score snapshots for the dashboard's 30d sparkline
    posture_history: list[dict[str, Any]]
    # config_entry_id -> rolling 24h health counters, written by health.py and
    # read by risk.py for the P_integration posture term:
    # {state, error_count_24h, unavailable_ratio, retry_transitions_24h, domain, title}
    integration_health: dict[str, dict[str, Any]]
    # user_id -> ISO timestamp of when mfa_policy.py first observed this
    # admin out of MFA compliance (active, admin, no MFA module). Cleared
    # the moment they become compliant again, so a future lapse restarts
    # the grace-period clock rather than reusing a stale start time.
    mfa_grace_started: dict[str, str]
    # Latest result ingested from the optional HA SOC Probe add-on (see
    # probe.py) via the ha_soc.ingest_probe_result service. None until the
    # add-on has reported at least once.
    host_probe: dict[str, Any] | None
    # Stable device key (vid:pid:serial_number, see peripherals.py) ->
    # {ignored_at, ignored_by, raw_name} for a USB/serial device an admin
    # has confirmed is intentionally unassigned, so it stops being flagged
    # on the Local Peripherals tab and dashboard summary.
    peripheral_ignored: dict[str, dict[str, Any]]
    # See firewall.py's module docstring for the full state machine.
    # known_rules/known_rules_reported_at mirror the add-on's last report
    # of the actual HA_SOC_RULES chain contents; pending is the single
    # in-flight test (None once resolved); history is a capped log of past
    # applies for the Audit Log-adjacent record of who changed what.
    firewall: dict[str, Any]


def default_store_data() -> StoreData:
    """Return a fresh, empty StoreData structure."""
    return StoreData(
        settings=SettingsData(
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            audit_max_bytes=DEFAULT_AUDIT_MAX_BYTES,
            scanner_enabled=DEFAULT_SCANNER_ENABLED,
            scanner_network_checks_enabled=DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
            nvd_api_key=None,
            risk_learning_period_days=DEFAULT_RISK_LEARNING_PERIOD_DAYS,
            access_level=DEFAULT_ACCESS_LEVEL,
            mfa_policy=DEFAULT_MFA_POLICY,
            mfa_grace_period_days=DEFAULT_MFA_GRACE_PERIOD_DAYS,
            security_sources_enabled=dict(DEFAULT_SECURITY_SOURCES_ENABLED),
        ),
        permissions_matrix={},
        vuln_findings={},
        misconfig_findings={},
        scanner_findings={},
        detections={},
        user_baselines={},
        posture_history=[],
        integration_health={},
        mfa_grace_started={},
        host_probe=None,
        peripheral_ignored={},
        firewall={
            "known_rules": None,
            "known_rules_reported_at": None,
            "pending": None,
            "history": [],
            # Trust-on-first-use secret shared with the add-on. Pinned to the
            # first non-empty probe_secret Core sees; thereafter every
            # ingest/poll call must present a match or it's rejected. See
            # firewall.async_verify_or_pin_secret.
            "addon_secret": None,
        },
    )


class HaSocStore(Store[StoreData]):
    """Store subclass carrying HA SOC's migration history."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        # No migrations yet — v1.0 is the first shape ever shipped. Future
        # migrations key off (old_major_version, old_minor_version) exactly
        # like Alarmo's store.py does.
        _LOGGER.debug(
            "No migration needed from %s.%s", old_major_version, old_minor_version
        )
        return old_data


class HaSocData:
    """Thin manager around the Store: load-once, mutate-in-memory, debounced save."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._store = HaSocStore(
            hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
            minor_version=STORAGE_VERSION_MINOR,
        )
        self.data: StoreData = default_store_data()

    async def async_load(self) -> bool:
        """Load persisted state. Returns True if a prior save existed.

        The return value lets the caller distinguish "this is the very
        first time HA SOC has ever run" (nothing on disk yet) from a normal
        restart — used once, in __init__.py, to decide whether a pre-setup
        options-flow save should be seeded into settings.
        """
        stored = await self._store.async_load()
        if stored is not None:
            # Merge onto defaults so a Store written by an older minor
            # version (missing a newly-added top-level key) doesn't KeyError.
            defaults = default_store_data()
            defaults.update(stored)  # type: ignore[typeddict-item]
            # `settings` is itself a nested dict that has grown new keys
            # over time (most recently security_sources_enabled) — the
            # top-level update() above only merges one level deep, so it
            # replaces defaults["settings"] wholesale with whatever settings
            # blob was actually on disk, silently dropping any key added
            # after that blob was first written. Re-merge settings
            # specifically so an existing install upgrading to a newer
            # minor version never ends up missing a key the rest of the
            # code (and the frontend) assumes is always present.
            settings_defaults = default_store_data()["settings"]
            settings_defaults.update(stored.get("settings") or {})  # type: ignore[typeddict-item]
            defaults["settings"] = settings_defaults
            self.data = defaults
        return stored is not None

    def async_schedule_save(self) -> None:
        """Debounced save — safe to call after every small mutation."""
        self._store.async_delay_save(lambda: self.data, STORAGE_SAVE_DELAY)

    async def async_save_now(self) -> None:
        await self._store.async_save(self.data)

    # -- Settings ---------------------------------------------------------
    @property
    def settings(self) -> SettingsData:
        return self.data["settings"]

    def async_update_settings(self, **changes: Any) -> None:
        self.data["settings"].update(changes)  # type: ignore[typeddict-item]
        self.async_schedule_save()

    # -- Permissions matrix -------------------------------------------------
    def get_user_dashboard_policy(self, user_id: str, url_path: str) -> dict[str, Any]:
        return (
            self.data["permissions_matrix"]
            .get(user_id, {})
            .get(url_path, {"views": {}, "sidebar_hidden": False})
        )

    def async_set_user_dashboard_policy(
        self, user_id: str, url_path: str, policy: dict[str, Any]
    ) -> None:
        self.data["permissions_matrix"].setdefault(user_id, {})[url_path] = policy
        self.async_schedule_save()

    def async_purge_user(self, user_id: str) -> None:
        """Garbage-collect stale matrix entries for a deleted user."""
        self.data["permissions_matrix"].pop(user_id, None)
        self.data["user_baselines"].pop(user_id, None)
        self.data["mfa_grace_started"].pop(user_id, None)
        self.async_schedule_save()

    # -- Generic finding-table helpers (vulns / misconfig / scanner) ------
    def _findings_table(self, table: str) -> dict[str, dict[str, Any]]:
        return self.data[table]  # type: ignore[literal-required]

    def async_upsert_finding(self, table: str, finding_id: str, finding: dict[str, Any]) -> None:
        existing = self._findings_table(table).get(finding_id)
        if existing is not None:
            # Preserve analyst-set lifecycle fields across a re-scan. Every
            # producer (vulns.py, scanner.py) sets "status": "new" on the
            # incoming dict unconditionally, so this must overwrite rather
            # than setdefault — setdefault is a no-op when the key is
            # already present, which silently reset a confirmed/dismissed
            # finding back to "new" on every re-scan.
            finding["status"] = existing.get("status", "new")
            finding["status_by"] = existing.get("status_by")
            finding["status_at"] = existing.get("status_at")
            finding["note"] = existing.get("note")
            finding["first_seen"] = existing.get("first_seen", finding.get("first_seen"))
        self._findings_table(table)[finding_id] = finding
        self.async_schedule_save()

    def async_set_finding_status(
        self, table: str, finding_id: str, status: str, *, by_user_id: str | None, note: str | None, at: str
    ) -> None:
        finding = self._findings_table(table).get(finding_id)
        if finding is None:
            return
        finding["status"] = status
        finding["status_by"] = by_user_id
        finding["status_at"] = at
        if note is not None:
            finding["note"] = note
        self.async_schedule_save()

    # -- Detections ---------------------------------------------------------
    def async_upsert_detection(self, detection_id: str, detection: dict[str, Any]) -> None:
        self.data["detections"][detection_id] = detection
        self.async_schedule_save()

    def async_set_detection_status(self, detection_id: str, status: str) -> None:
        detection = self.data["detections"].get(detection_id)
        if detection is None:
            return
        detection["status"] = status
        self.async_schedule_save()

    # -- Posture history ------------------------------------------------
    def async_append_posture_snapshot(self, snapshot: dict[str, Any], *, max_days: int = 90) -> None:
        history = self.data["posture_history"]
        history.append(snapshot)
        if len(history) > max_days:
            del history[: len(history) - max_days]
        self.async_schedule_save()

    # -- Host probe (optional add-on) ----------------------------------------
    def async_set_host_probe_result(self, result: dict[str, Any]) -> None:
        self.data["host_probe"] = result
        self.async_schedule_save()

    # -- USB/serial peripherals ----------------------------------------------
    def async_set_peripheral_ignored(
        self, key: str, ignored: bool, *, by_user_id: str | None, raw_name: str, at: str
    ) -> None:
        if ignored:
            self.data["peripheral_ignored"][key] = {
                "ignored_at": at,
                "ignored_by": by_user_id,
                "raw_name": raw_name,
            }
        else:
            self.data["peripheral_ignored"].pop(key, None)
        self.async_schedule_save()
