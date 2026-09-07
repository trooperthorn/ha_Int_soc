"""Versioned persistence for HA SOC's configuration and finding state.

This Store holds settings, the permissions matrix, and finding lifecycle
state. It never holds the audit log (audit.py) or any secret value
(secrets_store.py).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, TypedDict

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    DEFAULT_ACCESS_LEVEL,
    DEFAULT_AUDIT_MAX_BYTES,
    DEFAULT_AUDIT_RETENTION_DAYS,
    DEFAULT_MFA_GRACE_PERIOD_DAYS,
    DEFAULT_MFA_POLICY,
    DEFAULT_SCANNER_ENABLED,
    DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
    DEFAULT_SNMP_ENABLED,
    DEFAULT_SNMP_PORT,
    DEFAULT_PIHOLE_VERIFY_SSL,
    DEFAULT_SECURITY_SOURCES_ENABLED,
    DEFAULT_SYSLOG_FACILITY,
    DEFAULT_SYSLOG_FORMAT,
    DEFAULT_SYSLOG_PORT,
    DEFAULT_SYSLOG_TLS_VERIFY,
    DEFAULT_SYSLOG_TRANSPORT,
    DEFAULT_UNIFI_VERIFY_SSL,
    DETECTION_RESOLVED,
    STATUS_DISMISSED,
    STATUS_RESOLVED,
    STORAGE_KEY,
    STORAGE_SAVE_DELAY,
    STORAGE_VERSION_MAJOR,
    STORAGE_VERSION_MINOR,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_EVIDENCE_RETENTION_DAYS = 365

DEFAULT_NVD_LOOKUPS_ENABLED = True

_EVIDENCE_FINDING_TABLES = ("vuln_findings", "misconfig_findings", "scanner_findings")


class SettingsData(TypedDict):
    # Secret values never live here; they are in secrets_store.py.
    audit_retention_days: int
    audit_max_bytes: int
    syslog_transport: str
    syslog_format: str
    syslog_host: str | None
    syslog_port: int
    syslog_tls_verify: bool
    syslog_facility: int
    evidence_retention_days: int
    scanner_enabled: bool
    scanner_network_checks_enabled: bool
    nvd_lookups_enabled: bool
    # Sparse rule id -> {parameter: value}; read effective values via detections.thresholds().
    detection_thresholds: dict[str, dict[str, Any]]
    access_level: str
    mfa_policy: str
    mfa_grace_period_days: int
    # domain -> included in Security Integrations Health; a missing domain means enabled.
    security_sources_enabled: dict[str, bool]
    # Empty host means "not configured"; API keys live in the secret store.
    unifi_network_host: str | None
    unifi_network_verify_ssl: bool
    unifi_protect_host: str | None
    unifi_protect_verify_ssl: bool
    # Empty host means "not configured"; the app password lives in the secret store.
    pihole_host: str | None
    pihole_verify_ssl: bool
    pihole_iot_cidr: str | None
    # SNMP credentials live in the secret store.
    snmp_enabled: bool
    snmp_listen_address: str | None
    snmp_port: int
    snmp_username: str | None


class StoreData(TypedDict):
    """Shape of the JSON persisted under .storage/ha_soc.storage."""

    settings: SettingsData
    # {seq, hash, at} mirror of the audit chain's last flushed head; None until the first flush.
    audit_head: dict[str, Any] | None
    # user_id -> dashboard url_path -> {"views": {view_path: bool}, "sidebar_hidden": bool}
    permissions_matrix: dict[str, dict[str, Any]]
    # finding_id -> finding record (see vulns.py / health.py / scanner.py for field shapes)
    vuln_findings: dict[str, dict[str, Any]]
    misconfig_findings: dict[str, dict[str, Any]]
    scanner_findings: dict[str, dict[str, Any]]
    # detection_id -> detection record (see detections.py)
    detections: dict[str, dict[str, Any]]
    # user_id -> behavioral baselines learned by the detection engine
    user_baselines: dict[str, dict[str, Any]]
    # daily posture-score snapshots for the dashboard's 30d sparkline
    posture_history: list[dict[str, Any]]
    # posture term -> ISO timestamp of the FIRST time it computed from real data
    posture_terms: dict[str, str]
    # {"last_pass_completed_at": ISO}, written by detections.py, read by risk.py
    detections_meta: dict[str, Any]
    # config_entry_id -> rolling 24h health counters (health.py writes, risk.py reads)
    integration_health: dict[str, dict[str, Any]]
    # user_id -> ISO timestamp MFA non-compliance was first observed; cleared on compliance
    mfa_grace_started: dict[str, str]
    # latest result from the HA SOC Probe add-on; None until it has reported once
    host_probe: dict[str, Any] | None
    # vid:pid:serial_number -> {ignored_at, ignored_by, raw_name} (see peripherals.py)
    peripheral_ignored: dict[str, dict[str, Any]]
    # See firewall.py's module docstring for the state machine.
    firewall: dict[str, Any]
    # "github": per-repo provenance cache keyed "owner/repo"; "refreshed_at": last refresh
    integration_security: dict[str, Any]
    # Config only; breach counters and usage history are never persisted.
    resource_watchdog: dict[str, Any]
    # user_id -> view_id -> {"order": [section_id, ...], "hidden": [section_id, ...]}
    panel_layout: dict[str, dict[str, dict[str, Any]]]
    # last bounded, non-secret runtime report from the Probe's snmpd supervisor
    snmp_status: dict[str, Any] | None
    # source slug -> {"seq", "hash", "at"}: the last external audit record accepted per source
    external_audit_heads: dict[str, dict[str, Any]]


def default_store_data() -> StoreData:
    """Return a fresh, empty StoreData structure."""
    return StoreData(
        settings=SettingsData(
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            audit_max_bytes=DEFAULT_AUDIT_MAX_BYTES,
            syslog_transport=DEFAULT_SYSLOG_TRANSPORT,
            syslog_format=DEFAULT_SYSLOG_FORMAT,
            syslog_host=None,
            syslog_port=DEFAULT_SYSLOG_PORT,
            syslog_tls_verify=DEFAULT_SYSLOG_TLS_VERIFY,
            syslog_facility=DEFAULT_SYSLOG_FACILITY,
            evidence_retention_days=DEFAULT_EVIDENCE_RETENTION_DAYS,
            scanner_enabled=DEFAULT_SCANNER_ENABLED,
            scanner_network_checks_enabled=DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED,
            nvd_lookups_enabled=DEFAULT_NVD_LOOKUPS_ENABLED,
            detection_thresholds={},
            access_level=DEFAULT_ACCESS_LEVEL,
            mfa_policy=DEFAULT_MFA_POLICY,
            mfa_grace_period_days=DEFAULT_MFA_GRACE_PERIOD_DAYS,
            security_sources_enabled=dict(DEFAULT_SECURITY_SOURCES_ENABLED),
            unifi_network_host=None,
            unifi_network_verify_ssl=DEFAULT_UNIFI_VERIFY_SSL,
            unifi_protect_host=None,
            unifi_protect_verify_ssl=DEFAULT_UNIFI_VERIFY_SSL,
            pihole_host=None,
            pihole_verify_ssl=DEFAULT_PIHOLE_VERIFY_SSL,
            pihole_iot_cidr=None,
            snmp_enabled=DEFAULT_SNMP_ENABLED,
            snmp_listen_address=None,
            snmp_port=DEFAULT_SNMP_PORT,
            snmp_username=None,
        ),
        audit_head=None,
        permissions_matrix={},
        vuln_findings={},
        misconfig_findings={},
        scanner_findings={},
        detections={},
        user_baselines={},
        posture_history=[],
        posture_terms={},
        detections_meta={},
        integration_health={},
        mfa_grace_started={},
        host_probe=None,
        peripheral_ignored={},
        firewall={
            "known_rules": None,
            "known_rules_reported_at": None,
            "pending": None,
            "history": [],
        },
        integration_security={"github": {}, "refreshed_at": None},
        resource_watchdog={
            "enabled": False,
            "default_cpu_percent": 85,
            "default_memory_percent": 85,
            "default_action": "restart",
            "sustained_samples": 3,
            "interval_seconds": 60,
            # slug -> {cpu_percent, memory_percent, action, enabled}; missing keys inherit the defaults
            "overrides": {},
            # slug -> {"memory_mb": int|None, "cpus": float|None} Docker caps for the Probe to apply
            "hard_limits": {},
            # slug -> {"status": applied|failed|denied, "detail", "at"}, the Probe's last report
            "hard_limit_state": {},
        },
        panel_layout={},
        snmp_status=None,
        external_audit_heads={},
    )


class HaSocStore(Store[StoreData]):
    """Store subclass carrying HA SOC's migration history."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        _LOGGER.debug(
            "No migration needed from %s.%s", old_major_version, old_minor_version
        )
        return old_data


class HaSocData:
    """Thin manager around the Store: load-once, mutate-in-memory, debounced save."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        # private + atomic: the file is written 0o600 via temp file and rename, like core's auth store.
        self._store = HaSocStore(
            hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
            private=True,
            atomic_writes=True,
            minor_version=STORAGE_VERSION_MINOR,
        )
        self.data: StoreData = default_store_data()
        # Runtime-only cache resolved lazily by probe.py; never persisted.
        self.supervisor_user_id: str | None = None

    async def async_load(self) -> bool:
        """Load persisted state. Returns True if a prior save existed."""
        stored = await self._store.async_load()
        if stored is not None:
            # Merge onto defaults so a Store from an older minor version cannot KeyError.
            defaults = default_store_data()
            defaults.update(stored)  # type: ignore[typeddict-item]
            # update() merges one level deep, so the nested settings dict is re-merged separately.
            settings_defaults = default_store_data()["settings"]
            settings_defaults.update(stored.get("settings") or {})  # type: ignore[typeddict-item]
            self._migrate_legacy_learning_period(settings_defaults)
            defaults["settings"] = settings_defaults
            self.data = defaults
        return stored is not None

    @staticmethod
    def _migrate_legacy_learning_period(settings: dict[str, Any]) -> None:
        """Copy risk_learning_period_days into the per-rule learning_days.

        Rule ids are literal strings because store.py must not import
        detections.py (detections imports this module).
        """
        legacy = settings.pop("risk_learning_period_days", None)
        if legacy is None:
            return
        thresholds = settings.setdefault("detection_thresholds", {})
        for rule in ("new_ip_login", "off_hours_anomaly"):
            thresholds.setdefault(rule, {}).setdefault("learning_days", legacy)
        _LOGGER.info(
            "HA SOC: migrated risk_learning_period_days=%s into the per-rule "
            "learning_days detection thresholds",
            legacy,
        )

    def async_schedule_save(self) -> None:
        """Debounced save, safe to call after every small mutation."""
        self._store.async_delay_save(lambda: self.data, STORAGE_SAVE_DELAY)

    async def async_save_now(self) -> None:
        await self._store.async_save(self.data)

    @property
    def settings(self) -> SettingsData:
        return self.data["settings"]

    def async_update_settings(self, **changes: Any) -> None:
        self.data["settings"].update(changes)  # type: ignore[typeddict-item]
        self.async_schedule_save()

    def external_audit_head(self, source: str) -> dict[str, Any] | None:
        heads = self.data.setdefault("external_audit_heads", {})  # type: ignore[misc]
        head = heads.get(source)
        return dict(head) if isinstance(head, dict) else None

    def async_set_external_audit_head(self, source: str, head: dict[str, Any]) -> None:
        """The head only advances; a regressing call is a replay and is dropped."""
        heads = self.data.setdefault("external_audit_heads", {})  # type: ignore[misc]
        current = heads.get(source)
        if isinstance(current, dict) and int(current.get("seq", 0)) >= int(head["seq"]):
            return
        heads[source] = head
        self.async_schedule_save()

    def async_set_audit_head(self, head: dict[str, Any]) -> None:
        """Record the audit chain's flushed head ({seq, hash, at}).

        The mirror only ever advances; a regressing call is dropped.
        """
        current = self.data.get("audit_head")
        if isinstance(current, dict):
            try:
                if int(current.get("seq", 0)) >= int(head["seq"]):
                    return
            except (TypeError, ValueError, KeyError):
                pass
        self.data["audit_head"] = head
        self.async_schedule_save()

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
        self.data["panel_layout"].pop(user_id, None)
        self.async_schedule_save()

    def get_user_panel_layout(self, user_id: str, view_id: str) -> dict[str, Any]:
        """Return {"order", "hidden"} for one user's view, or {} when never customized."""
        return self.data["panel_layout"].get(user_id, {}).get(view_id, {})

    def async_set_user_panel_layout(
        self, user_id: str, view_id: str, order: list[str], hidden: list[str]
    ) -> None:
        self.data["panel_layout"].setdefault(user_id, {})[view_id] = {
            "order": order,
            "hidden": hidden,
        }
        self.async_schedule_save()

    def _findings_table(self, table: str) -> dict[str, dict[str, Any]]:
        return self.data[table]  # type: ignore[literal-required]

    def async_upsert_finding(self, table: str, finding_id: str, finding: dict[str, Any]) -> None:
        existing = self._findings_table(table).get(finding_id)
        if existing is not None:
            # Must overwrite, not setdefault: producers set "status": "new" unconditionally.
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

    def async_upsert_detection(self, detection_id: str, detection: dict[str, Any]) -> None:
        """Insert or replace a detection row, preserving analyst state.

        The branch is a no-op when the caller passes the existing dict
        object back (detections.py does).
        """
        existing = self.data["detections"].get(detection_id)
        if existing is not None and existing is not detection:
            detection["status"] = existing.get("status", detection.get("status"))
            for key in ("status_by", "status_at", "previous_status"):
                if key in existing:
                    detection[key] = existing[key]
        self.data["detections"][detection_id] = detection
        self.async_schedule_save()

    def async_set_detection_status(
        self,
        detection_id: str,
        status: str,
        *,
        by_user_id: str | None = None,
        at: str | None = None,
    ) -> dict[str, Any] | None:
        """Set a detection's status, recording who, when, and what it was.

        Returns the mutated detection, or None when no such detection
        exists (nothing changed, nothing should be audited).
        """
        detection = self.data["detections"].get(detection_id)
        if detection is None:
            return None
        detection["previous_status"] = detection.get("status")
        detection["status"] = status
        detection["status_by"] = by_user_id
        detection["status_at"] = at
        self.async_schedule_save()
        return detection

    def async_note_detection_pass_completed(self, at_iso: str) -> None:
        """Record that a detection pass finished (read by risk.py)."""
        self.data["detections_meta"]["last_pass_completed_at"] = at_iso
        self.async_schedule_save()

    def async_prune_evidence(self, now: datetime) -> dict[str, int]:
        """Prune closed-out evidence older than evidence_retention_days.

        Only resolved detections and resolved/dismissed findings are
        eligible. Returns per-table removal counts.
        """
        retention_days = self.settings.get(
            "evidence_retention_days", DEFAULT_EVIDENCE_RETENTION_DAYS
        )
        cutoff = dt_util.as_utc(now) - timedelta(days=retention_days)
        removed: dict[str, int] = {}

        def _is_expired(record: dict[str, Any], fallback_keys: tuple[str, ...]) -> bool:
            for key in ("status_at", *fallback_keys):
                raw = record.get(key)
                if raw:
                    moment = dt_util.parse_datetime(raw)
                    if moment is not None:
                        return moment < cutoff
            # No parseable timestamp: keep the record rather than guess its age.
            return False

        detections = self.data["detections"]
        expired_ids = [
            det_id
            for det_id, det in detections.items()
            if det.get("status") == DETECTION_RESOLVED
            and _is_expired(det, ("last_seen", "ts"))
        ]
        for det_id in expired_ids:
            del detections[det_id]
        removed["detections"] = len(expired_ids)

        for table in _EVIDENCE_FINDING_TABLES:
            findings = self._findings_table(table)
            expired_ids = [
                finding_id
                for finding_id, finding in findings.items()
                if finding.get("status") in (STATUS_RESOLVED, STATUS_DISMISSED)
                and _is_expired(finding, ("last_seen", "first_seen"))
            ]
            for finding_id in expired_ids:
                del findings[finding_id]
            removed[table] = len(expired_ids)

        if any(removed.values()):
            self.async_schedule_save()
            _LOGGER.debug("HA SOC evidence retention pruned: %s", removed)
        return removed

    def async_mark_posture_term_computed(self, term: str, at_iso: str) -> None:
        """Record the FIRST time a posture term computed from real data.

        Only the first stamp is ever kept.
        """
        terms = self.data["posture_terms"]
        if term not in terms:
            terms[term] = at_iso
            self.async_schedule_save()

    def async_append_posture_snapshot(self, snapshot: dict[str, Any], *, max_days: int = 90) -> None:
        history = self.data["posture_history"]
        history.append(snapshot)
        if len(history) > max_days:
            del history[: len(history) - max_days]
        self.async_schedule_save()

    def async_set_host_probe_result(self, result: dict[str, Any]) -> None:
        self.data["host_probe"] = result
        self.async_schedule_save()

    def async_set_snmp_status(self, status: dict[str, Any]) -> None:
        self.data["snmp_status"] = status
        self.async_schedule_save()

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
