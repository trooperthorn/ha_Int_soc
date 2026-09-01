"""Versioned persistence for HA SOC's configuration and finding state.

This Store holds everything EXCEPT the audit log itself: settings, the
permissions matrix, and the lifecycle state (new/confirmed/dismissed/
resolved) of vulnerability, misconfiguration, scanner, and detection
findings. It deliberately excludes the audit log and raw event history,
which are high-volume and live in their own rotating JSONL files
(see audit.py) — rewriting one Store file on every audit event would mean
serializing the whole history on every write. It also deliberately
excludes every secret value: those live in the dedicated private secret
store (secrets_store.py), so that this file never carries a credential.

The one audit-related thing this Store DOES hold is ``audit_head``: a tiny
{seq, hash, at} mirror of the audit chain's on-disk head, written by
audit.py after every successful flush (work item 1.5). It exists because
the audit directory and this Store file are two different files an
attacker would have to falsify consistently: a wiped or rolled-back audit
directory whose head has fallen behind this mirror is detected at the next
startup and verification. The mirror only ever advances (see
async_set_audit_head).

The Store itself is created ``private=True, atomic_writes=True`` (work
item 1.1): findings, baselines, and firewall history are sensitive even
with the secrets moved out, so the file is written 0o600 through a temp
file and rename, the same way core writes its own auth store.
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
    DEFAULT_PIHOLE_VERIFY_SSL,
    DEFAULT_SECURITY_SOURCES_ENABLED,
    DEFAULT_SYSLOG_FACILITY,
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

# Evidence retention (work item 3.3, decision D-6 option (a)): how long
# RESOLVED detections and RESOLVED/DISMISSED findings are kept before the
# periodic sweep prunes them. Open and acknowledged items never expire.
# Module-local rather than in const.py: only this module reads it, per
# const.py's own convention.
DEFAULT_EVIDENCE_RETENTION_DAYS = 365

# NVD lookups (decision D-12 option (a)): the device-vulnerability scan
# sends device manufacturer and model strings to NIST's NVD. It stays ON
# by default (existing behavior, now disclosed in Settings and the docs)
# with this owner-facing off switch; vulns.py consumes the setting.
DEFAULT_NVD_LOOKUPS_ENABLED = True

# The three finding tables the evidence retention sweep prunes. The
# firewall history is a capped list owned by firewall.py and is not swept
# here.
_EVIDENCE_FINDING_TABLES = ("vuln_findings", "misconfig_findings", "scanner_findings")


class SettingsData(TypedDict):
    # Secret VALUES are deliberately absent from this shape. Every key in
    # const.SECRET_SETTING_KEYS (the NVD API key, the GitHub token, the two
    # UniFi API keys) lives in the dedicated private secret store instead
    # (secrets_store.py, work item SEC-1); async_migrate_legacy_secrets
    # drains any value an older install still has in here on first load.
    # The frontend's "<key>_set" booleans are derived on the wire by
    # websocket_api._masked_settings, never persisted here.
    audit_retention_days: int
    audit_max_bytes: int
    # RFC 5424 off-box audit export. Disabled by default; UDP/TCP remain
    # explicit compatibility modes and TLS is the recommended destination.
    syslog_transport: str
    syslog_host: str | None
    syslog_port: int
    syslog_tls_verify: bool
    syslog_facility: int
    # How long resolved detections and resolved/dismissed findings are
    # retained (work item 3.3, D-6). Distinct from audit_retention_days,
    # which governs the audit chain's day files.
    evidence_retention_days: int
    scanner_enabled: bool
    scanner_network_checks_enabled: bool
    # D-12: device manufacturer/model strings are sent to NIST's NVD only
    # while this is on. Consumed by vulns.py.
    nvd_lookups_enabled: bool
    # Owner overrides for the tunable detection thresholds (work item 3.0,
    # D-9): rule id -> {parameter: value}, sparse. Effective values are
    # always read through detections.thresholds(), which merges these over
    # the secure defaults, so a missing key never means "off". The old
    # risk_learning_period_days setting was replaced by the two per-rule
    # learning_days parameters in here; async_load migrates a stored value
    # into both once.
    detection_thresholds: dict[str, dict[str, Any]]
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
    # UniFi Network / Protect direct-to-console connections (Network tab).
    # Host + SSL-verify per app; the matching API keys are secrets and live
    # in the secret store. Empty host means "not configured".
    unifi_network_host: str | None
    unifi_network_verify_ssl: bool
    unifi_protect_host: str | None
    unifi_protect_verify_ssl: bool
    # Pi-hole v6 direct connection (Network Security tab). Host + SSL-verify
    # + the IoT-subnet CIDR used only for the client-group-scoping check;
    # the app password is a secret and lives in the secret store. Empty
    # host means "not configured".
    pihole_host: str | None
    pihole_verify_ssl: bool
    pihole_iot_cidr: str | None


class StoreData(TypedDict):
    """Shape of the JSON persisted under .storage/ha_soc.storage."""

    settings: SettingsData
    # {seq, hash, at} mirror of the audit chain's last flushed head, written
    # by audit.py after every successful flush and compared against the
    # on-disk chain head at startup so a wiped or rolled-back audit
    # directory is detected (work item 1.5). None until the first flush.
    audit_head: dict[str, Any] | None
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
    # posture term -> ISO timestamp of the FIRST time that term ever
    # computed from real data (work item 3.4, D-10 "computed once ever").
    # risk.py stamps terms as their sources become observable; until every
    # term is present the posture result carries provisional=True.
    posture_terms: dict[str, str]
    # Detection-engine runtime facts that must survive a restart. Today:
    # {"last_pass_completed_at": ISO} - written by detections.py at the end
    # of every pass, read by risk.py as the p_detection term's evidence.
    detections_meta: dict[str, Any]
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
    # Integration Security (provenance). "github" caches per-repo
    # GitHub-derived signals keyed by "owner/repo" (see github_provenance.py);
    # refreshed_at is the last time the cache was refreshed.
    integration_security: dict[str, Any]
    # Container Resource Watchdog (see resource_watchdog.py). Config only —
    # breach counters and usage history are runtime-in-memory, never
    # persisted (writing a time series into this Store every sample would
    # churn it for purely diagnostic data). hard_limits is the owner-set
    # Docker cap per add-on slug ({memory_mb, cpus}); hard_limit_state is
    # the Probe's last report of what's actually applied on the host.
    resource_watchdog: dict[str, Any]
    # Per-user "Customize" layout for the panel's card-based views:
    # user_id -> view_id -> {"order": [section_id, ...], "hidden": [section_id, ...]}.
    # A personal UI preference, not a security setting — any user with SOC
    # access may set their own (see websocket_api.ws_layout_set), unlike the
    # owner-only Settings tab. Missing view_id/user_id both mean "use each
    # view's own declared default order, nothing hidden" (see
    # HaSocData.get_user_panel_layout) rather than an error.
    panel_layout: dict[str, dict[str, dict[str, Any]]]


def default_store_data() -> StoreData:
    """Return a fresh, empty StoreData structure."""
    return StoreData(
        settings=SettingsData(
            audit_retention_days=DEFAULT_AUDIT_RETENTION_DAYS,
            audit_max_bytes=DEFAULT_AUDIT_MAX_BYTES,
            syslog_transport=DEFAULT_SYSLOG_TRANSPORT,
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
            # No "addon_secret" key here anymore, deliberately: the shared
            # pairing secret with the Probe add-on lives in the private
            # secret store (secrets_store.PROBE_PAIRING_SECRET_KEY) since
            # work item SEC-1, and a legacy value in an older install's
            # stored firewall dict is drained into it on first load by
            # async_migrate_legacy_secrets. See
            # firewall.async_verify_or_pin_secret.
        },
        integration_security={"github": {}, "refreshed_at": None},
        resource_watchdog={
            "enabled": False,
            "default_cpu_percent": 85,
            "default_memory_percent": 85,
            "default_action": "restart",
            "sustained_samples": 3,
            "interval_seconds": 60,
            # slug -> {cpu_percent, memory_percent, action, enabled} — every
            # key optional; a missing key inherits the defaults above.
            "overrides": {},
            # slug -> {"memory_mb": int|None, "cpus": float|None} — Docker
            # hard caps for the Probe to apply (requires its Protection
            # Mode disabled; see resource_watchdog.py's docstring).
            "hard_limits": {},
            # slug -> {"status": applied|failed|denied, "detail", "at"} —
            # the Probe's last report of the caps actually on the host.
            "hard_limit_state": {},
        },
        panel_layout={},
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
        # private=True + atomic_writes=True (work item 1.1, D-8 option (a)):
        # findings, per-user baselines, and the firewall history are
        # sensitive even without the secret values (which live in
        # secrets_store.py), so the file gets the same 0o600 temp-file-and-
        # rename treatment core gives its own auth store.
        self._store = HaSocStore(
            hass,
            STORAGE_VERSION_MAJOR,
            STORAGE_KEY,
            private=True,
            atomic_writes=True,
            minor_version=STORAGE_VERSION_MINOR,
        )
        self.data: StoreData = default_store_data()
        # Runtime-only cache of the Supervisor system user's id, resolved
        # lazily by probe.py on the first inbound Probe call and never
        # persisted: the id is core's to assign, and caching it here just
        # spares the ~5s poll cadence a registry lookup per call.
        self.supervisor_user_id: str | None = None

    async def async_load(self) -> bool:
        """Load persisted state. Returns True if a prior save existed.

        The return value distinguishes "this is the very first time HA SOC
        has ever run" (nothing on disk yet) from a normal restart. The old
        seed-from-entry.options path that consumed it was removed with the
        entry.options mirror (work item SEC-2); the flag is kept because it
        is cheap and honest information a future first-run step may need.
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
            self._migrate_legacy_learning_period(settings_defaults)
            defaults["settings"] = settings_defaults
            self.data = defaults
        return stored is not None

    @staticmethod
    def _migrate_legacy_learning_period(settings: dict[str, Any]) -> None:
        """Copy risk_learning_period_days into the per-rule learning_days.

        Work item 3.0 (D-9): the single risk_learning_period_days setting
        was replaced by the two per-rule learning_days thresholds. A value
        an existing install had stored is copied into BOTH rules' override
        slots exactly once (setdefault, so an already-set per-rule value
        wins), then the legacy key is dropped so it stops round-tripping
        forever. The rule ids are literal strings here because store.py
        must not import detections.py (detections imports this module).
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

    # -- Audit chain head mirror (work item 1.5) -----------------------------
    def async_set_audit_head(self, head: dict[str, Any]) -> None:
        """Record the audit chain's flushed head ({seq, hash, at}).

        The mirror only ever advances. A chain head that moves backwards is
        exactly the wipe/rollback signal audit.py compares this mirror
        against, so accepting a lower seq here would erase the evidence the
        mirror exists to preserve. In normal operation the head always
        advances anyway (a post-reset chain continues numbering from this
        mirror, see audit.py), so a regressing call is a programming error
        or a race and is dropped rather than honored.
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
        self.data["panel_layout"].pop(user_id, None)
        self.async_schedule_save()

    # -- Panel "Customize" layout (per user, per view) -----------------------
    def get_user_panel_layout(self, user_id: str, view_id: str) -> dict[str, Any]:
        """{"order": [...], "hidden": [...]} for one user's one view, or
        an empty dict when they've never customized it — the caller falls
        back to that view's own declared default order with nothing
        hidden, never an error."""
        return self.data["panel_layout"].get(user_id, {}).get(view_id, {})

    def async_set_user_panel_layout(
        self, user_id: str, view_id: str, order: list[str], hidden: list[str]
    ) -> None:
        self.data["panel_layout"].setdefault(user_id, {})[view_id] = {
            "order": order,
            "hidden": hidden,
        }
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
        """Insert or replace a detection row, preserving analyst state.

        Work item 3.10: when a WRITER other than the row's own prior state
        replaces an existing detection wholesale (the resource watchdog
        builds a fresh dict with status "open" on every re-trip), the
        analyst-set lifecycle fields must survive - an acknowledged or
        resolved detection never flips back to open just because the same
        condition tripped again. detections.py's engine passes the
        existing dict object back on update, so this branch is a no-op
        for it.
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

        status_by/status_at/previous_status are recorded on the detection
        itself (work item 1.4) so the analyst trail survives on the record,
        not only in the audit chain. Returns the mutated detection so the
        caller can audit rule_id and previous_status, or None when no such
        detection exists (in which case nothing changed and nothing should
        be audited).
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
        """Record that a detection pass finished (read by risk.py, item 3.4)."""
        self.data["detections_meta"]["last_pass_completed_at"] = at_iso
        self.async_schedule_save()

    # -- Evidence retention (work item 3.3, decision D-6) --------------------
    def async_prune_evidence(self, now: datetime) -> dict[str, int]:
        """Prune closed-out evidence older than evidence_retention_days.

        D-6 option (a): only RESOLVED detections and RESOLVED/DISMISSED
        findings are eligible - an open or acknowledged item never
        expires, no matter how old. Age is measured from when the analyst
        closed the record (status_at) where that exists, falling back to
        the record's own last activity timestamp for records closed by a
        build that predates status_at. Returns per-table removal counts
        for the caller's logging.
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
            # No parseable timestamp at all: keep the record. Deleting
            # evidence whose age cannot be established would be guessing.
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

    # -- Posture term bookkeeping (work item 3.4, decision D-10) -------------
    def async_mark_posture_term_computed(self, term: str, at_iso: str) -> None:
        """Record the FIRST time a posture term computed from real data.

        Only the first stamp is kept ("computed once ever", per D-10): a
        term that has produced a value once stays counted even if its
        source table later empties out, because provisional means "never
        yet computed", not "currently empty".
        """
        terms = self.data["posture_terms"]
        if term not in terms:
            terms[term] = at_iso
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
