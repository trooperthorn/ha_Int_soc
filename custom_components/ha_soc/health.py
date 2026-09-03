"""Per-integration health counters and misconfiguration checks.

These are heuristic checks against a live install, not a penetration test.
A severity is a starting judgment for triage, never a verdict. Timing,
approximations, and the finding lifecycle are in docs/design.md.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import ipaddress
import json
import logging
import os
from typing import Any

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.config_entries import (
    SIGNAL_CONFIG_ENTRY_CHANGED,
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigEntryChange,
    ConfigEntryState,
)
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.loader import async_get_integration, async_get_integrations
import homeassistant.util.dt as dt

from .audit import BAN_LOGGER_NAME
from .config_hygiene import HYGIENE_COULD_NOT_EVALUATE, HygieneResult
from .const import (
    DOMAIN,
    PROBE_ADDON_NAME,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
    STATUS_CONFIRMED,
    STATUS_DISMISSED,
    STATUS_RESOLVED,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

HEALTH_TICK_INTERVAL = timedelta(minutes=5)
STARTUP_GRACE = timedelta(minutes=5)
ERROR_BUCKET_SPAN_HOURS = 24
RETRY_BUCKET_SPAN_HOURS = 24
UNAVAILABLE_SAMPLE_WINDOW = timedelta(hours=24)

GENERIC_ISSUE_TRANSLATION_KEY = "misconfig_finding"

# Item lists in a finding detail are capped; total_count always carries the true count.
DETAIL_ITEMS_CAP = 100

# A broader trusted_proxies network than these prefixes lets a spoofed X-Forwarded-For defeat IP banning.
MIN_TRUSTED_PROXY_V4_PREFIX = 24
MIN_TRUSTED_PROXY_V6_PREFIX = 64

# Each config entry gets at most one category; priority order is credential first, disabled last.
ISSUE_CATEGORY_CREDENTIAL = "credential"
ISSUE_CATEGORY_FAILING = "failing"
ISSUE_CATEGORY_COMMUNICATION = "communication"
ISSUE_CATEGORY_COLLECTION = "collection"
ISSUE_CATEGORY_ERRORS = "errors"
ISSUE_CATEGORY_DEBUG_LOGGING = "debug_logging"
ISSUE_CATEGORY_DISABLED = "disabled"
ISSUE_CATEGORY_NONE = "none"
ISSUE_CATEGORIES = (
    ISSUE_CATEGORY_CREDENTIAL,
    ISSUE_CATEGORY_FAILING,
    ISSUE_CATEGORY_COMMUNICATION,
    ISSUE_CATEGORY_COLLECTION,
    ISSUE_CATEGORY_ERRORS,
    ISSUE_CATEGORY_DEBUG_LOGGING,
    ISSUE_CATEGORY_DISABLED,
)

COLLECTION_UNAVAILABLE_RATIO_THRESHOLD = 0.2

ERROR_COUNT_ISSUE_THRESHOLD = 5

_FAILING_STATES = (
    ConfigEntryState.SETUP_ERROR,
    ConfigEntryState.MIGRATION_ERROR,
    ConfigEntryState.FAILED_UNLOAD,
)

# Only the official add-on's slug is known; other SSH add-ons match by name/slug substring.
_KNOWN_SSH_ADDON_SLUGS = {"core_ssh"}

# Matched by name: the cached Supervisor add-on info carries no volume-map field.
_CONFIG_MAPPING_ADDON_MARKERS = (
    "ssh",
    "samba",
    "file editor",
    "configurator",
    "studio code",
    "vscode",
)

# Generous: the add-on itself retries every 30s-5min, so this only fires for a stuck setup.
PROBE_NOT_REPORTING_GRACE = timedelta(minutes=30)


def _iso_now() -> str:
    return dt.utcnow().isoformat()


def _new_finding(
    finding_id: str, check: str, severity: str, *, title: str, summary: str, detail: dict
) -> dict:
    now = _iso_now()
    return {
        "id": finding_id,
        "check": check,
        "severity": severity,
        "title": title,
        "summary": summary,
        "detail": detail,
        "first_seen": now,
        "last_seen": now,
        # The store's upsert preserves an analyst-set status across re-scans.
        "status": "new",
    }


def _capped_detail(key: str, items: list) -> dict:
    """A finding detail carrying at most DETAIL_ITEMS_CAP items under ``key`` plus the honest ``total_count``."""
    return {key: list(items[:DETAIL_ITEMS_CAP]), "total_count": len(items)}


def _proxy_trust_problems(http_conf: dict) -> list[str]:
    """Why this http: block's proxy trust is too broad, empty when it is
    narrow enough. An entry that does not parse is reported as a problem,
    not skipped.
    """
    proxies = http_conf.get("trusted_proxies")
    if not proxies:
        return ["trusted_proxies is not set, so the header is trusted from anywhere"]
    if not isinstance(proxies, list):
        proxies = [proxies]

    problems: list[str] = []
    for raw in proxies:
        try:
            network = ipaddress.ip_network(str(raw), strict=False)
        except ValueError:
            problems.append(f"trusted_proxies entry {raw!r} is not a valid network")
            continue
        if network.prefixlen == 0:
            problems.append(f"{network} trusts the header from every address")
        elif network.version == 4 and network.prefixlen < MIN_TRUSTED_PROXY_V4_PREFIX:
            problems.append(
                f"{network} is broader than a /{MIN_TRUSTED_PROXY_V4_PREFIX}"
            )
        elif network.version == 6 and network.prefixlen < MIN_TRUSTED_PROXY_V6_PREFIX:
            problems.append(
                f"{network} is broader than a /{MIN_TRUSTED_PROXY_V6_PREFIX}"
            )
    return problems


def _hour_bucket(moment: datetime) -> int:
    return int(moment.timestamp() // 3600)


def _prune_and_sum(buckets: dict[int, int], now_hour: int, span_hours: int) -> int:
    oldest_kept = now_hour - span_hours + 1
    for hour in [h for h in buckets if h < oldest_kept]:
        del buckets[hour]
    return sum(buckets.values())


class _HealthLogHandler(logging.Handler):
    """Root-logger handler that hands WARNING+ records off to the loop.

    emit() can run on a non-loop thread, so it must hand off via
    call_soon_threadsafe rather than touch hass or the store directly.
    """

    def __init__(self, health: "IntegrationHealth") -> None:
        super().__init__(level=logging.WARNING)
        self._health = health

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._health.hass.loop.call_soon_threadsafe(
                self._health._handle_log_record, record.name
            )
        except RuntimeError:
            pass


class IntegrationHealth:
    """Rolling per-config-entry health counters plus misconfiguration checks."""

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self._store = store

        self._logger_prefixes: list[tuple[str, str]] = []
        self._entities_by_entry: dict[str, list[str]] = {}
        self._error_buckets: dict[str, dict[int, int]] = {}
        self._retry_buckets: dict[str, dict[int, int]] = {}
        self._unavail_samples: dict[str, list[tuple[float, float]]] = {}
        self._started_at: datetime | None = None
        # In-memory only; resets on every reload for a fresh grace window, like _started_at.
        self._probe_unreported_since: datetime | None = None

        self._dispatcher_unsub: Callable[[], None] | None = None
        self._timer_unsub: Callable[[], None] | None = None
        self._started_unsub: Callable[[], None] | None = None
        self._log_handler: _HealthLogHandler | None = None

        # "stale" means the next request loads; "loaded"/"failed" hold until the next sweep resets them.
        self._sweep_yaml: dict[str, Any] | None = None
        self._sweep_yaml_state: str = "stale"

    async def async_start(self) -> None:
        await self._async_refresh_attribution_maps()

        for entry in self.hass.config_entries.async_entries():
            self._store.data["integration_health"][entry.entry_id] = (
                self._build_health_record(entry)
            )
        self._store.async_schedule_save()

        self._dispatcher_unsub = async_dispatcher_connect(
            self.hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._on_entry_changed
        )

        self._log_handler = _HealthLogHandler(self)
        logging.getLogger().addHandler(self._log_handler)

        if self.hass.is_running:
            # (Re)started after HA already finished starting (e.g. a reload): no startup flurry to wait out.
            self._started_at = dt.utcnow() - STARTUP_GRACE
        else:
            self._started_unsub = self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, self._on_started
            )

        self._timer_unsub = async_track_time_interval(
            self.hass, self._async_tick, HEALTH_TICK_INTERVAL
        )

        await self.async_run_misconfig_checks()

    async def async_stop(self) -> None:
        if self._dispatcher_unsub is not None:
            self._dispatcher_unsub()
            self._dispatcher_unsub = None
        if self._log_handler is not None:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None
        if self._timer_unsub is not None:
            self._timer_unsub()
            self._timer_unsub = None
        if self._started_unsub is not None:
            try:
                self._started_unsub()
            except Exception:  # noqa: BLE001 - already-fired listen_once is fine
                pass
            self._started_unsub = None

    @callback
    def _on_started(self, _event) -> None:
        self._started_at = dt.utcnow()

    async def _on_entry_changed(
        self, change: ConfigEntryChange, entry: ConfigEntry
    ) -> None:
        if change == ConfigEntryChange.REMOVED:
            self._store.data["integration_health"].pop(entry.entry_id, None)
            self._retry_buckets.pop(entry.entry_id, None)
            self._unavail_samples.pop(entry.entry_id, None)
            self._store.async_schedule_save()
            return

        if entry.state == ConfigEntryState.SETUP_RETRY:
            bucket = self._retry_buckets.setdefault(entry.entry_id, {})
            hour = _hour_bucket(dt.utcnow())
            bucket[hour] = bucket.get(hour, 0) + 1

        if change == ConfigEntryChange.ADDED:
            await self._async_refresh_attribution_maps()

        self._store.data["integration_health"][entry.entry_id] = (
            self._build_health_record(entry)
        )
        self._store.async_schedule_save()

    def _build_health_record(self, entry: ConfigEntry) -> dict:
        now_hour = _hour_bucket(dt.utcnow())
        return {
            "entry_id": entry.entry_id,
            "domain": entry.domain,
            "title": entry.title,
            "state": entry.state.value,
            "reason": entry.reason,
            "disabled_by": entry.disabled_by.value if entry.disabled_by else None,
            "error_count_24h": _prune_and_sum(
                self._error_buckets.get(entry.domain, {}), now_hour, ERROR_BUCKET_SPAN_HOURS
            ),
            "unavailable_ratio": self._mean_unavailable_ratio(entry.entry_id),
            "retry_transitions_24h": _prune_and_sum(
                self._retry_buckets.get(entry.entry_id, {}), now_hour, RETRY_BUCKET_SPAN_HOURS
            ),
            "updated_at": _iso_now(),
        }

    async def async_integration_overview(self) -> dict:
        """Per-integration issue categorization for the SOC Dashboard.

        Computed fresh on every call. Category is priority-ordered, at most one
        per entry: credential, failing, communication, collection, errors,
        debug_logging, disabled; see docs/design.md for the definitions.
        """
        reauth_entry_ids = {
            flow["context"]["entry_id"]
            for flow in self.hass.config_entries.flow.async_progress()
            if flow.get("context", {}).get("source") == SOURCE_REAUTH
            and flow["context"].get("entry_id")
        }
        debug_domains = {
            domain
            for prefix, domain in self._logger_prefixes
            if logging.getLogger(prefix).getEffectiveLevel() <= logging.DEBUG
        }

        integrations: list[dict] = []
        category_counts = dict.fromkeys(ISSUE_CATEGORIES, 0)

        for record in self._store.data["integration_health"].values():
            category = self._issue_category(record, reauth_entry_ids, debug_domains)
            if category == ISSUE_CATEGORY_NONE:
                continue
            category_counts[category] += 1
            integrations.append({**record, "issue_category": category})

        integrations.sort(key=lambda r: r["error_count_24h"], reverse=True)
        return {"integrations": integrations, "category_counts": category_counts}

    @staticmethod
    def _issue_category(record: dict, reauth_entry_ids: set[str], debug_domains: set[str]) -> str:
        if record["entry_id"] in reauth_entry_ids:
            return ISSUE_CATEGORY_CREDENTIAL
        if record["state"] in (s.value for s in _FAILING_STATES):
            return ISSUE_CATEGORY_FAILING
        if record["state"] == ConfigEntryState.SETUP_RETRY.value:
            return ISSUE_CATEGORY_COMMUNICATION
        if record["state"] == ConfigEntryState.LOADED.value:
            if record["unavailable_ratio"] > COLLECTION_UNAVAILABLE_RATIO_THRESHOLD:
                return ISSUE_CATEGORY_COLLECTION
            if record["error_count_24h"] > ERROR_COUNT_ISSUE_THRESHOLD:
                return ISSUE_CATEGORY_ERRORS
        if record["domain"] in debug_domains:
            return ISSUE_CATEGORY_DEBUG_LOGGING
        if record.get("disabled_by") is not None:
            return ISSUE_CATEGORY_DISABLED
        return ISSUE_CATEGORY_NONE

    async def _async_refresh_attribution_maps(self) -> None:
        domains = {e.domain for e in self.hass.config_entries.async_entries()}

        prefixes: list[tuple[str, str]] = []
        for domain in domains:
            prefixes.append((f"homeassistant.components.{domain}", domain))
            prefixes.append((f"custom_components.{domain}", domain))
        for domain in domains:
            try:
                integration = await async_get_integration(self.hass, domain)
            except Exception:  # noqa: BLE001 - a domain with a broken manifest
                continue
            for logger_prefix in integration.manifest.get("loggers", []) or []:
                prefixes.append((logger_prefix, domain))
        # Longest prefix first so a specific manifest-declared logger name wins.
        prefixes.sort(key=lambda item: len(item[0]), reverse=True)
        self._logger_prefixes = prefixes

        registry = er.async_get(self.hass)
        self._entities_by_entry = {
            entry.entry_id: [
                entity.entity_id
                for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
            ]
            for entry in self.hass.config_entries.async_entries()
        }

    def _domain_for_logger(self, logger_name: str) -> str | None:
        for prefix, domain in self._logger_prefixes:
            if logger_name == prefix or logger_name.startswith(prefix + "."):
                return domain
        return None

    @callback
    def _handle_log_record(self, logger_name: str) -> None:
        domain = self._domain_for_logger(logger_name)
        if domain is None:
            return

        hour = _hour_bucket(dt.utcnow())
        bucket = self._error_buckets.setdefault(domain, {})
        bucket[hour] = bucket.get(hour, 0) + 1

        # Recompute here so the count is live rather than up to 5 minutes stale.
        count = _prune_and_sum(bucket, hour, ERROR_BUCKET_SPAN_HOURS)
        touched = False
        for entry in self.hass.config_entries.async_entries(domain):
            record = self._store.data["integration_health"].get(entry.entry_id)
            if record is None:
                continue
            record["error_count_24h"] = count
            record["updated_at"] = _iso_now()
            touched = True
        if touched:
            self._store.async_schedule_save()

    async def _async_tick(self, _now=None) -> None:
        try:
            self._async_sample_unavailable_ratios()
        except Exception:  # noqa: BLE001
            _LOGGER.warning("HA SOC health: unavailable-ratio sampling failed", exc_info=True)

        try:
            self._async_roll_all_records()
        except Exception:  # noqa: BLE001
            _LOGGER.warning("HA SOC health: rolling health counters failed", exc_info=True)

        self._store.async_schedule_save()

    def _async_sample_unavailable_ratios(self) -> None:
        if self._started_at is None:
            return
        if dt.utcnow() - self._started_at < STARTUP_GRACE:
            return

        now_epoch = dt.utcnow().timestamp()
        cutoff = now_epoch - UNAVAILABLE_SAMPLE_WINDOW.total_seconds()

        for entry_id, entity_ids in self._entities_by_entry.items():
            if not entity_ids:
                continue
            unavailable = 0
            total = 0
            for entity_id in entity_ids:
                state = self.hass.states.get(entity_id)
                if state is None:
                    continue
                total += 1
                if state.state in ("unavailable", "unknown"):
                    unavailable += 1
            if total == 0:
                continue

            samples = self._unavail_samples.setdefault(entry_id, [])
            samples.append((now_epoch, unavailable / total))
            self._unavail_samples[entry_id] = [s for s in samples if s[0] >= cutoff]

    def _mean_unavailable_ratio(self, entry_id: str) -> float:
        samples = self._unavail_samples.get(entry_id)
        if not samples:
            return 0.0
        return sum(ratio for _, ratio in samples) / len(samples)

    def _async_roll_all_records(self) -> None:
        now_hour = _hour_bucket(dt.utcnow())
        for entry in self.hass.config_entries.async_entries():
            record = self._store.data["integration_health"].get(entry.entry_id)
            if record is None:
                continue
            record["error_count_24h"] = _prune_and_sum(
                self._error_buckets.get(entry.domain, {}), now_hour, ERROR_BUCKET_SPAN_HOURS
            )
            record["retry_transitions_24h"] = _prune_and_sum(
                self._retry_buckets.get(entry.entry_id, {}), now_hour, RETRY_BUCKET_SPAN_HOURS
            )
            record["unavailable_ratio"] = self._mean_unavailable_ratio(entry.entry_id)
            record["updated_at"] = _iso_now()

    def _async_mirror_to_repairs(
        self, finding: dict, translation_key: str, placeholders: dict[str, str]
    ) -> None:
        # An unknown severity string maps DOWN to WARNING; bad data must not page anyone as CRITICAL.
        severity = finding["severity"]
        if severity == SEVERITY_CRITICAL:
            issue_severity = ir.IssueSeverity.CRITICAL
        elif severity == SEVERITY_HIGH:
            issue_severity = ir.IssueSeverity.ERROR
        else:
            issue_severity = ir.IssueSeverity.WARNING
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            finding["id"],
            is_fixable=False,
            severity=issue_severity,
            translation_key=translation_key,
            translation_placeholders=placeholders,
        )

    def _async_resolve_missing(self, check: str, active_ids: set[str]) -> None:
        now = _iso_now()
        for finding_id, finding in list(self._store.data["misconfig_findings"].items()):
            if finding.get("check") != check or finding_id in active_ids:
                continue
            # A dismissed or confirmed status survives a pass in which the condition was not seen.
            if finding.get("status") in (STATUS_DISMISSED, STATUS_CONFIRMED):
                continue
            ir.async_delete_issue(self.hass, DOMAIN, finding_id)
            self._store.async_set_finding_status(
                "misconfig_findings", finding_id, STATUS_RESOLVED,
                by_user_id=None, note=None, at=now,
            )

    def _async_finalize_check(
        self, check: str, items: list[tuple[dict, str, dict[str, str]]]
    ) -> list[dict]:
        active_ids: set[str] = set()
        findings: list[dict] = []
        for finding, translation_key, placeholders in items:
            active_ids.add(finding["id"])
            self._store.async_upsert_finding("misconfig_findings", finding["id"], finding)
            findings.append(finding)
            stored = self._store.data["misconfig_findings"].get(finding["id"], finding)
            if stored.get("status") == STATUS_DISMISSED:
                # A dismissed finding keeps its row in the table but loses its Repairs issue.
                ir.async_delete_issue(self.hass, DOMAIN, finding["id"])
            elif finding["severity"] == SEVERITY_INFO or finding.get("acknowledged_by_design"):
                # INFO and acknowledged-by-design rows never page through Repairs; the delete also clears a stale issue.
                ir.async_delete_issue(self.hass, DOMAIN, finding["id"])
            else:
                self._async_mirror_to_repairs(finding, translation_key, placeholders)
        self._async_resolve_missing(check, active_ids)
        return findings

    async def _async_sweep_yaml(self) -> dict[str, Any] | None:
        """The merged YAML configuration, loaded at most once per sweep. None after
        a failed load, which each consumer must treat as could_not_evaluate."""
        if self._sweep_yaml_state == "stale":
            from homeassistant.config import async_hass_config_yaml

            try:
                self._sweep_yaml = await async_hass_config_yaml(self.hass)
                self._sweep_yaml_state = "loaded"
            except Exception:  # noqa: BLE001 - includes HomeAssistantError on broken YAML
                self._sweep_yaml = None
                self._sweep_yaml_state = "failed"
                _LOGGER.warning(
                    "HA SOC: could not load the merged YAML configuration; the "
                    "YAML-backed misconfiguration checks report could_not_evaluate "
                    "this sweep",
                    exc_info=True,
                )
        return self._sweep_yaml

    async def async_run_misconfig_checks(self) -> list[dict]:
        # Nothing is evaluated and no finding is touched until HA has finished starting plus STARTUP_GRACE.
        if self._started_at is None or dt.utcnow() - self._started_at < STARTUP_GRACE:
            _LOGGER.debug(
                "HA SOC: skipping misconfiguration sweep, still inside the startup grace"
            )
            return []

        # Mark the cache stale so the first check that needs YAML triggers exactly one load.
        self._sweep_yaml = None
        self._sweep_yaml_state = "stale"

        checks = (
            self._check_http_insecure,
            self._check_http_hardening,
            self._check_trusted_networks,
            self._check_device_cleartext_url,
            self._check_cloud_egress_inventory,
            self._check_addon_protection_mode,
            self._check_ssh_addon_inventory,
            self._check_ssh_addon_exposed,
            self._check_probe_addon_not_reporting,
            self._check_audit_ban_logger,
            self._check_storage_file_modes,
            self._check_config_mapping_addons,
            self._check_backup_protection,
            self._check_samba_config_share,
            self._check_broken_entity_references,
            self._check_unknown_service_references,
            self._check_unknown_device_references,
            self._check_unknown_area_floor_label_references,
            self._check_alert_unknown_references,
            self._check_notify_group_unknown_members,
            self._check_person_unknown_trackers,
            self._check_group_unknown_members,
            self._check_proximity_unknown_references,
            self._check_lovelace_missing_resources,
            self._check_empty_areas_and_floors,
            self._check_unused_labels_and_blueprints,
            self._check_unknown_customize_entities,
            self._check_orphaned_statistics,
            self._check_energy_unknown_references,
            self._check_notify_coverage_gaps,
        )
        results: list[dict] = []
        for check in checks:
            try:
                results.extend(await check())
            except Exception:  # noqa: BLE001 - one bad check must not stop the rest
                _LOGGER.warning("HA SOC misconfig check %s failed", check.__name__, exc_info=True)
        return results

    async def async_run_config_check(self) -> list[dict]:
        """check="ha_config_invalid", on its own slower interval.

        Deliberately not part of the 5-minute sweep: a full YAML re-validation is
        real CPU/IO work. See __init__.py's CONFIG_CHECK_INTERVAL.
        """
        from homeassistant.config import async_check_ha_config_file

        try:
            error = await async_check_ha_config_file(self.hass)
        except Exception:  # noqa: BLE001 - never let this take the periodic loop down
            _LOGGER.warning("HA SOC config-check failed to run", exc_info=True)
            return []

        items: list[tuple[dict, str, dict[str, str]]] = []
        if error:
            finding = _new_finding(
                "misconfig:ha_config_invalid", "ha_config_invalid", SEVERITY_HIGH,
                title="Home Assistant's YAML configuration is currently invalid",
                summary=(
                    "The last configuration check failed. A restart while "
                    "this is broken would fail to fully start, or fall back "
                    "to safe mode. See Settings > System > General > Check "
                    "Configuration for the exact error."
                ),
                detail={"error": error},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        return self._async_finalize_check("ha_config_invalid", items)

    async def _check_http_insecure(self) -> list[dict]:
        """check="http_insecure" - matches translations/en.json's http_insecure key."""
        api = getattr(self.hass.config, "api", None)
        use_ssl = getattr(api, "use_ssl", False) if api is not None else False
        external_url = self.hass.config.external_url

        items: list[tuple[dict, str, dict[str, str]]] = []
        if external_url and external_url.startswith("http://"):
            finding = _new_finding(
                "misconfig:http_insecure:external_url", "http_insecure", SEVERITY_HIGH,
                title="External URL is not using HTTPS",
                summary=(
                    f"external_url is set to {external_url}, which is not "
                    "TLS-protected. Credentials and session tokens would "
                    "transit in cleartext for anyone using this URL."
                ),
                detail={"external_url": external_url},
            )
            items.append((finding, "http_insecure", {}))

        if use_ssl is False and external_url:
            conf = await self._async_sweep_yaml()
            http_conf = (conf.get("http") or {}) if conf is not None else None
            behind_narrow_proxy = (
                http_conf is not None
                and bool(http_conf.get("use_x_forwarded_for"))
                and bool(http_conf.get("trusted_proxies"))
                and not _proxy_trust_problems(http_conf)
            )
            severity = SEVERITY_INFO if behind_narrow_proxy else SEVERITY_LOW
            summary = (
                "use_ssl is disabled while an external_url is "
                "configured. Common and legitimate behind a reverse "
                "proxy that terminates TLS itself - confirm that is "
                "the case here."
            )
            if behind_narrow_proxy:
                summary += (
                    " Note: use_x_forwarded_for is enabled with a narrow "
                    "trusted_proxies list, so TLS termination at a "
                    "deliberately configured reverse proxy is the likely "
                    "explanation; downgraded to informational."
                )
            finding = _new_finding(
                "misconfig:http_insecure:no_ssl", "http_insecure", severity,
                title="Home Assistant is served without built-in TLS",
                summary=summary,
                detail={
                    "external_url": external_url,
                    "use_ssl": use_ssl,
                    "behind_narrow_proxy": behind_narrow_proxy,
                },
            )
            items.append((finding, "http_insecure", {}))

        return self._async_finalize_check("http_insecure", items)

    async def _check_http_hardening(self) -> list[dict]:
        """check="http_hardening" - cors/ip_ban/login_attempts_threshold, plus the proxy trust check."""
        conf = await self._async_sweep_yaml()
        if conf is None:
            return []

        http_conf = conf.get("http", {}) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []

        proxy_problems = _proxy_trust_problems(http_conf)
        if bool(http_conf.get("use_x_forwarded_for")) and proxy_problems:
            finding = _new_finding(
                "misconfig:http_hardening:proxy_trust", "http_hardening", SEVERITY_HIGH,
                title="X-Forwarded-For is trusted from too broad a source",
                summary=(
                    "use_x_forwarded_for is enabled but "
                    + "; ".join(proxy_problems)
                    + ". Any host in the trusted range can spoof a client "
                    "IP header, so IP bans and IP-based detections judge "
                    "an attacker-chosen address. List only the reverse "
                    "proxy's own address(es) in trusted_proxies."
                ),
                detail={
                    "use_x_forwarded_for": True,
                    "trusted_proxies": [
                        str(p) for p in (http_conf.get("trusted_proxies") or [])
                    ],
                    "problems": proxy_problems,
                },
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        cors = http_conf.get("cors_allowed_origins")
        if cors and "*" in cors:
            finding = _new_finding(
                "misconfig:http_hardening:cors", "http_hardening", SEVERITY_MEDIUM,
                title="CORS allows any origin",
                summary=(
                    "cors_allowed_origins includes \"*\", allowing any "
                    "website to make authenticated browser requests to "
                    "this Home Assistant instance."
                ),
                detail={"cors_allowed_origins": cors},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        if http_conf.get("ip_ban_enabled", True) is False:
            finding = _new_finding(
                "misconfig:http_hardening:ip_ban", "http_hardening", SEVERITY_MEDIUM,
                title="Automatic IP banning is disabled",
                summary=(
                    "ip_ban_enabled is set to false, so repeated failed "
                    "logins never result in an automatic ban."
                ),
                detail={"ip_ban_enabled": False},
            )
            items.append((finding, "ip_ban_disabled", {}))

        threshold = http_conf.get("login_attempts_threshold", -1)
        if threshold == -1:
            finding = _new_finding(
                "misconfig:http_hardening:login_attempts", "http_hardening", SEVERITY_MEDIUM,
                title="No login attempt threshold configured",
                summary=(
                    "login_attempts_threshold is unset — Home Assistant's "
                    "default is unlimited attempts, so failed logins never "
                    "trigger an automatic ban regardless of ip_ban_enabled."
                ),
                detail={"login_attempts_threshold": threshold},
            )
            items.append((finding, "ip_ban_disabled", {}))

        return self._async_finalize_check("http_hardening", items)

    async def _check_trusted_networks(self) -> list[dict]:
        """check="trusted_networks_permissive" - one finding per provider."""
        try:
            providers = [
                provider
                for provider in self.hass.auth.auth_providers
                if getattr(provider, "type", None) == "trusted_networks"
            ]
        except Exception:  # noqa: BLE001 - unexpected auth_providers shape
            _LOGGER.warning("Could not enumerate auth providers", exc_info=True)
            return []

        v4_any = ipaddress.ip_network("0.0.0.0/0")
        v6_any = ipaddress.ip_network("::/0")

        items: list[tuple[dict, str, dict[str, str]]] = []
        for index, provider in enumerate(providers):
            networks = list(getattr(provider, "trusted_networks", []) or [])
            allow_bypass = bool(
                getattr(provider, "config", {}).get("allow_bypass_login", False)
            )
            subject = getattr(provider, "id", None) or str(index)

            severity: str | None = None
            reasons: list[str] = []
            for network in networks:
                if network == v4_any or network == v6_any:
                    severity = SEVERITY_CRITICAL
                    reasons.append(f"{network} allows any address")
                elif not network.is_private and not network.is_loopback:
                    if severity != SEVERITY_CRITICAL:
                        severity = SEVERITY_HIGH
                    reasons.append(f"{network} is a public range")

            if allow_bypass and any(
                net.prefixlen < net.max_prefixlen for net in networks
            ):
                if severity != SEVERITY_CRITICAL:
                    severity = SEVERITY_HIGH
                reasons.append(
                    "allow_bypass_login is enabled for a network broader "
                    "than a single host"
                )

            privileged_mappings = await self._async_privileged_trusted_users(provider)
            if privileged_mappings:
                if severity != SEVERITY_CRITICAL:
                    severity = SEVERITY_HIGH
                reasons.extend(privileged_mappings)

            if severity is None:
                continue

            finding = _new_finding(
                f"misconfig:trusted_networks_permissive:{subject}",
                "trusted_networks_permissive", severity,
                title="Trusted Networks auth provider is permissively configured",
                summary="; ".join(reasons),
                detail={
                    "networks": [str(net) for net in networks],
                    "allow_bypass_login": allow_bypass,
                    "privileged_trusted_users": privileged_mappings,
                },
            )
            items.append((
                finding, "trusted_networks_permissive",
                {"network": ", ".join(str(net) for net in networks) or "(none)"},
            ))

        return self._async_finalize_check("trusted_networks_permissive", items)

    async def _async_privileged_trusted_users(self, provider) -> list[str]:
        """Reasons for every trusted_users mapping that grants a network
        passwordless login as an admin, the owner, or the admin group."""
        try:
            trusted_users = dict(getattr(provider, "trusted_users", None) or {})
        except Exception:  # noqa: BLE001 - a provider mock/shape without the property
            return []

        reasons: list[str] = []
        for network, user_or_group_list in trusted_users.items():
            if not isinstance(user_or_group_list, list):
                user_or_group_list = [user_or_group_list]
            for item in user_or_group_list:
                if isinstance(item, dict):
                    if item.get("group") == GROUP_ID_ADMIN:
                        reasons.append(
                            f"trusted_users maps {network} to the admin group"
                        )
                    continue
                user = await self.hass.auth.async_get_user(str(item))
                if user is None:
                    continue
                if user.is_owner:
                    reasons.append(
                        f"trusted_users maps {network} to the owner account "
                        f"({user.name or user.id})"
                    )
                elif user.is_admin:
                    reasons.append(
                        f"trusted_users maps {network} to the admin account "
                        f"({user.name or user.id})"
                    )
        return reasons

    async def _check_device_cleartext_url(self) -> list[dict]:
        """check="device_cleartext_url" - one aggregated finding."""
        registry = dr.async_get(self.hass)
        devices = [
            {
                "device_id": device.id,
                "name": device.name_by_user or device.name,
                "configuration_url": device.configuration_url,
            }
            for device in registry.devices.values()
            if device.configuration_url
            and device.configuration_url.startswith("http://")
        ]

        if not devices:
            return self._async_finalize_check("device_cleartext_url", [])

        finding = _new_finding(
            "misconfig:device_cleartext_url", "device_cleartext_url", SEVERITY_LOW,
            title="Devices expose a cleartext (http://) configuration URL",
            summary=(
                f"{len(devices)} device(s) have a configuration_url using "
                "http://. Very common for LAN IoT admin pages — confirm "
                "these are not reachable from outside the LAN."
            ),
            detail=_capped_detail("devices", devices),
        )
        return self._async_finalize_check(
            "device_cleartext_url",
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            })],
        )

    async def _check_cloud_egress_inventory(self) -> list[dict]:
        """check="cloud_egress_inventory" - informational, never mirrored."""
        domains = {e.domain for e in self.hass.config_entries.async_entries()}
        try:
            integrations = await async_get_integrations(self.hass, domains)
        except Exception:  # noqa: BLE001
            _LOGGER.warning("Could not resolve integrations for cloud egress inventory", exc_info=True)
            return []

        cloud_integrations = [
            {"domain": domain, "name": integration.name, "iot_class": integration.iot_class}
            for domain, integration in integrations.items()
            if not isinstance(integration, Exception)
            and integration.iot_class in ("cloud_polling", "cloud_push")
        ]

        finding = _new_finding(
            "misconfig:cloud_egress_inventory", "cloud_egress_inventory", SEVERITY_INFO,
            title="Cloud-connected integrations in use",
            summary=(
                f"{len(cloud_integrations)} integration(s) rely on a cloud "
                "service (cloud_polling/cloud_push). Informational only."
            ),
            detail=_capped_detail("cloud_integrations", cloud_integrations),
        )
        # Inventory, not a problem: no Repairs mirror, upsert only.
        self._store.async_upsert_finding("misconfig_findings", finding["id"], finding)
        return [finding]

    def _supervisor_missing_key_item(
        self, check: str, slug: str, name: str, missing: list[str]
    ) -> tuple[dict, str, dict[str, str]]:
        """The fail-closed outcome for cached add-on info lacking a key a check's
        judgment depends on: an INFO could_not_evaluate finding, never silence."""
        finding = _new_finding(
            f"misconfig:{check}:{slug}:could_not_evaluate", check, SEVERITY_INFO,
            title=f"{name}: {check} could not be evaluated",
            summary=(
                f"The Supervisor's cached info for add-on {name} is missing "
                f"the key(s) {', '.join(missing)}, so the {check} check "
                "could not evaluate this add-on this pass. Absence of a "
                "finding for it is not an all-clear."
            ),
            detail={"slug": slug, "missing_keys": missing, "could_not_evaluate": True},
        )
        return (finding, GENERIC_ISSUE_TRANSLATION_KEY, {
            "title": finding["title"], "summary": finding["summary"],
        })

    async def _check_addon_protection_mode(self) -> list[dict]:
        """check="addon_unprotected"; Supervisor-only, no-ops off Supervisor."""
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("addon_unprotected", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []
        hard_caps_configured = bool(
            (self._store.data.get("resource_watchdog") or {}).get("hard_limits")
        )

        for slug, info in addons.items():
            if not isinstance(info, dict):
                # The Supervisor failed to serve this add-on's info; skip it rather than treat unknown as clean.
                continue
            name = info.get("name") or slug
            if "protected" not in info:
                items.append(
                    self._supervisor_missing_key_item(
                        "addon_unprotected", slug, name, ["protected"]
                    )
                )
                continue
            if info["protected"]:
                continue
            # host_network only decides HIGH versus CRITICAL, so its absence matters only once protection is off.
            if "host_network" not in info:
                items.append(
                    self._supervisor_missing_key_item(
                        "addon_unprotected", slug, name, ["host_network"]
                    )
                )
                continue
            host_network = bool(info["host_network"])
            severity = SEVERITY_CRITICAL if host_network else SEVERITY_HIGH
            is_probe_hard_cap_case = (
                info.get("name") == PROBE_ADDON_NAME and hard_caps_configured
            )
            summary = (
                f"{name} has Supervisor's Protection mode turned off, "
                "granting it elevated access to the Supervisor API, "
                "Docker, and other add-ons rather than staying isolated "
                "to its own container."
            )
            if host_network:
                summary += (
                    " It also runs with host networking, so that elevated "
                    "container sits directly on the host's network."
                )
            if is_probe_hard_cap_case:
                summary += (
                    " Acknowledged by design (decision D-20): the HA SOC "
                    "Probe applies the configured container hard caps "
                    "through the Docker socket, which the Supervisor only "
                    "mounts with Protection Mode off. See the privilege "
                    "ledger in the Probe's documentation."
                )
            else:
                summary += (
                    " Only a small number of add-ons (ones that manage "
                    "other add-ons/backups) legitimately need this."
                )
            finding = _new_finding(
                f"misconfig:addon_unprotected:{slug}", "addon_unprotected", severity,
                title=f"{name} is running with Protection mode disabled",
                summary=summary,
                detail={"slug": slug, "host_network": host_network},
            )
            if is_probe_hard_cap_case:
                finding["acknowledged_by_design"] = True
                finding["acknowledged_reason"] = (
                    "hard caps are configured and the Docker socket "
                    "requires Protection Mode off (D-20)"
                )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        return self._async_finalize_check("addon_unprotected", items)

    async def _check_ssh_addon_inventory(self) -> list[dict]:
        """check="ssh_addon_inventory"; informational, never mirrored, best-effort by nature."""
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return []

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        ssh_addons = [
            {"slug": slug, "name": info.get("name") or slug, "state": info.get("state")}
            for slug, info in addons.items()
            if isinstance(info, dict)
            and (
                slug in _KNOWN_SSH_ADDON_SLUGS
                or "ssh" in slug.lower()
                or "ssh" in (info.get("name") or "").lower()
            )
        ]

        finding = _new_finding(
            "misconfig:ssh_addon_inventory", "ssh_addon_inventory", SEVERITY_INFO,
            title="SSH-capable add-ons installed",
            summary=(
                f"{len(ssh_addons)} installed add-on(s) look SSH-capable by "
                "name. Informational only — being installed and running is "
                "normal and often intentional."
            ),
            detail=_capped_detail("addons", ssh_addons),
        )
        self._store.async_upsert_finding("misconfig_findings", finding["id"], finding)
        return [finding]

    async def _check_ssh_addon_exposed(self) -> list[dict]:
        """check="ssh_addon_exposed"; Supervisor-only, no-ops off Supervisor."""
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("ssh_addon_exposed", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []

        for slug, info in addons.items():
            if not isinstance(info, dict):
                continue
            name = info.get("name") or slug
            is_ssh = (
                slug in _KNOWN_SSH_ADDON_SLUGS
                or "ssh" in slug.lower()
                or "ssh" in name.lower()
            )
            if not is_ssh:
                continue

            # Fail closed: a missing key must not read as "not exposed".
            missing = [key for key in ("host_network", "network") if key not in info]
            if missing:
                items.append(
                    self._supervisor_missing_key_item("ssh_addon_exposed", slug, name, missing)
                )
                continue

            host_network = bool(info["host_network"])
            published_ports = sorted(
                host_port for host_port in (info["network"] or {}).values()
                if host_port is not None
            )
            if not host_network and not published_ports:
                continue  # ingress-only (core_ssh's shipped default) or not running

            finding = _new_finding(
                f"misconfig:ssh_addon_exposed:{slug}", "ssh_addon_exposed", SEVERITY_HIGH,
                title=f"{name} is reachable directly on the host network",
                summary=(
                    f"{name} is exposed via "
                    f"{'host networking' if host_network else 'a published port'}, "
                    "reachable over SSH without going through Home Assistant's "
                    "own login at all. Confirm this is intentional and that "
                    "the add-on's own credentials are strong."
                ),
                detail={
                    "slug": slug,
                    "host_network": host_network,
                    "published_ports": published_ports,
                },
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        return self._async_finalize_check("ssh_addon_exposed", items)

    async def _check_probe_addon_not_reporting(self) -> list[dict]:
        """check="probe_addon_not_reporting"; Supervisor-only, no-ops off Supervisor.

        Scoped to installed, running, and never once reported successfully.
        """
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            self._probe_unreported_since = None
            return self._async_finalize_check("probe_addon_not_reporting", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        probe = next(
            (
                (slug, i)
                for slug, i in addons.items()
                if isinstance(i, dict) and i.get("name") == PROBE_ADDON_NAME
            ),
            None,
        )
        if probe is not None and "state" not in probe[1]:
            # Fail closed: a missing state key is reported, never read as "not running".
            self._probe_unreported_since = None
            return self._async_finalize_check(
                "probe_addon_not_reporting",
                [
                    self._supervisor_missing_key_item(
                        "probe_addon_not_reporting", probe[0], PROBE_ADDON_NAME, ["state"]
                    )
                ],
            )
        running = bool(probe is not None and probe[1].get("state") == "started")

        if not running or self._store.data.get("host_probe") is not None:
            self._probe_unreported_since = None
            return self._async_finalize_check("probe_addon_not_reporting", [])

        now = dt.utcnow()
        if self._probe_unreported_since is None:
            self._probe_unreported_since = now
        if now - self._probe_unreported_since < PROBE_NOT_REPORTING_GRACE:
            return self._async_finalize_check("probe_addon_not_reporting", [])

        finding = _new_finding(
            "misconfig:probe_addon_not_reporting", "probe_addon_not_reporting", SEVERITY_MEDIUM,
            title="HA SOC Probe add-on is running but has never reported in",
            summary=(
                "The HA SOC Probe add-on is installed and running, but "
                "hasn't successfully reported any data since HA SOC last "
                "started — it looks half set up. Check the add-on's own "
                "log (Settings > Add-ons > HA SOC Probe > Log) for why; a "
                "common cause is this config entry not having finished "
                "loading yet when the add-on made its first attempt."
            ),
            detail={},
        )
        return self._async_finalize_check(
            "probe_addon_not_reporting",
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            })],
        )

    async def _check_audit_ban_logger(self) -> list[dict]:
        """check="audit_ban_logger_silenced" - LOW. The value read is a logging level integer, nothing else."""
        level = logging.getLogger(BAN_LOGGER_NAME).getEffectiveLevel()
        items: list[tuple[dict, str, dict[str, str]]] = []
        if level > logging.WARNING:
            finding = _new_finding(
                "misconfig:audit_ban_logger_silenced",
                "audit_ban_logger_silenced", SEVERITY_LOW,
                title="Failed-login auditing is blinded by the logger configuration",
                summary=(
                    f"The {BAN_LOGGER_NAME} logger's effective level is "
                    f"{logging.getLevelName(level)}, above WARNING. Home "
                    "Assistant reports failed logins only as WARNING log "
                    "records from that logger, so HA SOC's login_fail "
                    "audit capture receives nothing while it stays this "
                    "quiet. Set the logger back to warning (or lower) in "
                    "your logger: configuration."
                ),
                detail={"logger": BAN_LOGGER_NAME, "effective_level": level},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))
        return self._async_finalize_check("audit_ban_logger_silenced", items)

    async def _check_storage_file_modes(self) -> list[dict]:
        """check="storage_file_modes" - LOW. Only file MODES are read, executor-side, never contents."""
        # ha-soc-allow: storage_file_access stats modes only, never reads content (SEC-7)
        secrets_path = self.hass.config.path("secrets.yaml")
        storage_path = self.hass.config.path(".storage")

        def _stat_modes() -> dict[str, int | None] | None:
            modes: dict[str, int | None] = {}
            for label, path in (
                ("secrets_yaml", secrets_path),
                ("storage_dir", storage_path),
            ):
                try:
                    modes[label] = os.stat(path).st_mode & 0o777
                except FileNotFoundError:
                    modes[label] = None
                except OSError:
                    return None
            return modes

        modes = await self.hass.async_add_executor_job(_stat_modes)
        if modes is None:
            _LOGGER.debug("Skipping storage_file_modes check: stat failed")
            return []

        items: list[tuple[dict, str, dict[str, str]]] = []
        # 0o077 masks exactly the group/other bits that let another uid reach the file.
        secrets_mode = modes["secrets_yaml"]
        if secrets_mode is not None and secrets_mode & 0o077:
            finding = _new_finding(
                "misconfig:storage_file_modes:secrets_yaml",
                "storage_file_modes", SEVERITY_LOW,
                title="secrets.yaml is readable beyond its owner",
                summary=(
                    f"secrets.yaml has mode {secrets_mode:04o}, so other "
                    "accounts on the host (and any container sharing the "
                    "directory without root remapping) can read every "
                    f"secret in it. Fix: chmod 600 {secrets_path}"
                ),
                detail={"path": secrets_path, "mode": f"{secrets_mode:04o}"},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))
        storage_mode = modes["storage_dir"]
        if storage_mode is not None and storage_mode & 0o077:
            finding = _new_finding(
                "misconfig:storage_file_modes:storage_dir",
                "storage_file_modes", SEVERITY_LOW,
                title="The .storage directory is accessible beyond its owner",
                summary=(
                    f"The .storage directory has mode {storage_mode:04o}. "
                    "It holds the auth store, HA SOC's private secret "
                    "store, and the audit chain; directory access is what "
                    "lets another uid list and open the private files "
                    f"inside. Fix: chmod 700 {storage_path}"
                ),
                detail={"path": storage_path, "mode": f"{storage_mode:04o}"},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))
        return self._async_finalize_check("storage_file_modes", items)

    async def _check_config_mapping_addons(self) -> list[dict]:
        """check="config_mapping_addon" - MEDIUM, HIGH when also exposed.

        Recognizes well-known config-mapping add-ons by name/slug substring only;
        absence of a finding is not proof nothing maps the config directory.
        """
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("config_mapping_addon", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass)
        if addons is None:
            _LOGGER.debug(
                "Skipping config_mapping_addon check: add-on info not cached yet"
            )
            return []

        items: list[tuple[dict, str, dict[str, str]]] = []
        for slug, info in addons.items():
            if not isinstance(info, dict):
                # The Supervisor failed to serve this add-on's info; skip it rather than treat unknown as clean.
                continue
            name = info.get("name") or slug
            haystack = f"{slug} {name}".lower()
            if not any(marker in haystack for marker in _CONFIG_MAPPING_ADDON_MARKERS):
                continue
            # Fail closed: the MEDIUM/HIGH split depends on these keys, so a missing one is reported.
            missing = [key for key in ("host_network", "network") if key not in info]
            if missing:
                items.append(
                    self._supervisor_missing_key_item("config_mapping_addon", slug, name, missing)
                )
                continue
            host_network = bool(info["host_network"])
            published_ports = sorted(
                host_port for host_port in (info["network"] or {}).values()
                if host_port is not None
            )
            exposed = host_network or bool(published_ports)
            severity = SEVERITY_HIGH if exposed else SEVERITY_MEDIUM
            exposure = (
                "and it is directly reachable on the host network, so a "
                "compromise of the add-on itself exposes those files "
                "without Home Assistant's login in the way"
                if exposed
                else "through Home Assistant's ingress only, as shipped"
            )
            finding = _new_finding(
                f"misconfig:config_mapping_addon:{slug}",
                "config_mapping_addon", severity,
                title=f"{name} can read Home Assistant's config directory",
                summary=(
                    f"{name} is one of the add-ons that map the config "
                    "directory, which includes .storage (the auth store, "
                    "HA SOC's private secret store, and the audit chain) "
                    f"and secrets.yaml, {exposure}. Keep it if you use it; "
                    "uninstall it if you do not."
                ),
                detail={
                    "slug": slug,
                    "name": name,
                    "state": info.get("state"),
                    "host_network": host_network,
                    "published_ports": published_ports,
                },
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))
        return self._async_finalize_check("config_mapping_addon", items)

    async def _check_backup_protection(self) -> list[dict]:
        """check="backup_unprotected" - MEDIUM. Reads .storage/backup executor-side:
        password null-ness only, and the per-agent protected booleans."""
        # ha-soc-allow: storage_file_access reads password null-ness and protected booleans only (SEC-7)
        path = self.hass.config.path(".storage", "backup")

        def _read() -> dict[str, Any] | None:
            try:
                with open(path, encoding="utf-8") as handle:
                    raw = json.load(handle)
            except FileNotFoundError:
                return {"absent": True}
            except (OSError, ValueError):
                return None
            config = ((raw.get("data") or {}).get("config")) or {}
            create = config.get("create_backup") or {}
            agents = config.get("agents") or {}
            return {
                "absent": False,
                "password_set": create.get("password") is not None,
                "agent_ids": sorted(agents),
                "unprotected_agents": sorted(
                    agent_id
                    for agent_id, agent in agents.items()
                    if isinstance(agent, dict) and agent.get("protected") is False
                ),
            }

        info = await self.hass.async_add_executor_job(_read)
        if info is None:
            _LOGGER.debug("Skipping backup_unprotected check: could not read %s", path)
            return []
        if info["absent"]:
            return self._async_finalize_check("backup_unprotected", [])

        problems: list[str] = []
        if info["agent_ids"] and not info["password_set"]:
            problems.append(
                "no backup password is configured, so backups are created "
                "unencrypted for every location"
            )
        if info["unprotected_agents"]:
            problems.append(
                "protection is turned off for: "
                + ", ".join(info["unprotected_agents"])
            )
        if not problems:
            return self._async_finalize_check("backup_unprotected", [])

        finding = _new_finding(
            "misconfig:backup_unprotected", "backup_unprotected", SEVERITY_MEDIUM,
            title="Backups are stored without protection for a configured location",
            summary=(
                "; ".join(problems).capitalize()
                + ". An unprotected backup carries the full .storage "
                "directory (auth store, HA SOC's secret store, the audit "
                "chain) readable by whoever holds the backup file. Enable "
                "backup encryption under Settings > System > Backups."
            ),
            detail={
                "password_set": info["password_set"],
                "unprotected_agents": info["unprotected_agents"],
                "configured_agents": info["agent_ids"],
            },
        )
        return self._async_finalize_check(
            "backup_unprotected",
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            })],
        )

    async def _check_samba_config_share(self) -> list[dict]:
        """check="samba_unauthenticated" - HIGH. Only option KEY presence and value
        truthiness are evaluated inside the closure; no option value is copied out."""
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("samba_unauthenticated", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass)
        if addons is None:
            _LOGGER.debug(
                "Skipping samba_unauthenticated check: add-on info not cached yet"
            )
            return []

        items: list[tuple[dict, str, dict[str, str]]] = []
        for slug, info in addons.items():
            if not isinstance(info, dict):
                continue
            name = info.get("name") or slug
            if "samba" not in f"{slug} {name}".lower():
                continue
            options = info.get("options")
            if not isinstance(options, dict):
                # Fail closed: no readable options means an INFO could_not_evaluate finding, never silence.
                items.append(
                    self._supervisor_missing_key_item(
                        "samba_unauthenticated", slug, name, ["options"]
                    )
                )
                continue
            password_keys = [
                key for key in options
                if isinstance(key, str) and key.lower() == "password"
            ]
            password_missing = bool(password_keys) and not any(
                options[key] for key in password_keys
            )
            guest_keys_on = sorted(
                key for key, value in options.items()
                if isinstance(key, str) and "guest" in key.lower() and value is True
            )
            if not password_missing and not guest_keys_on:
                continue

            reasons: list[str] = []
            if password_missing:
                reasons.append("its password option is empty")
            if guest_keys_on:
                reasons.append(
                    "guest access is enabled (" + ", ".join(guest_keys_on) + ")"
                )
            finding = _new_finding(
                f"misconfig:samba_unauthenticated:{slug}",
                "samba_unauthenticated", SEVERITY_HIGH,
                title=f"{name} shares the config directory without authentication",
                summary=(
                    f"{name} exposes the config directory over SMB and "
                    + " and ".join(reasons)
                    + ", so anyone on the network segment can read "
                    ".storage (the auth store, HA SOC's secret store, the "
                    "audit chain) and secrets.yaml. Set a password and "
                    "disable guest access in the add-on's configuration."
                ),
                detail={
                    "slug": slug,
                    "password_key_present": bool(password_keys),
                    "password_set": not password_missing if password_keys else None,
                    "guest_keys_enabled": guest_keys_on,
                },
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))
        return self._async_finalize_check("samba_unauthenticated", items)

    def _async_hygiene_finding(
        self, check: str, severity: str, title: str, summary: str, items: list[Any]
    ) -> list[dict]:
        """Shared plumbing for every config_hygiene.py-backed check: one aggregated
        finding when items is non-empty, none when empty, and NOTHING touched
        when the helper reported could_not_evaluate.
        """
        if getattr(items, "status", None) == HYGIENE_COULD_NOT_EVALUATE:
            _LOGGER.debug(
                "HA SOC hygiene check %s could not evaluate; findings left untouched",
                check,
            )
            return []
        if not items:
            return self._async_finalize_check(check, [])
        finding = _new_finding(
            f"misconfig:{check}", check, severity, title=title, summary=summary,
            detail=_capped_detail("items", list(items)),
        )
        return self._async_finalize_check(
            check,
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {"title": title, "summary": summary})],
        )

    async def _check_unknown_service_references(self) -> list[dict]:
        """check="unknown_service_references"; Spook-inspired."""
        from .config_hygiene import async_unknown_service_references

        items = await async_unknown_service_references(self.hass)
        return self._async_hygiene_finding(
            "unknown_service_references", SEVERITY_MEDIUM,
            "Automations/scripts call services that no longer exist",
            f"{len(items)} action(s) target a service that isn't registered — likely left behind "
            "after an integration was removed or renamed. That action silently does nothing when "
            "the automation/script runs.",
            items,
        )

    async def _check_unknown_device_references(self) -> list[dict]:
        """check="unknown_device_references" - Spook-inspired."""
        from .config_hygiene import async_unknown_device_references

        items = await async_unknown_device_references(self.hass)
        return self._async_hygiene_finding(
            "unknown_device_references", SEVERITY_MEDIUM,
            "Automations/scripts reference devices that no longer exist",
            f"{len(items)} device trigger/condition/action reference(s) point at a device_id no "
            "longer in the device registry — that trigger/condition/action can never fire.",
            items,
        )

    async def _check_unknown_area_floor_label_references(self) -> list[dict]:
        """check="unknown_area_floor_label_references"; Spook-inspired."""
        from .config_hygiene import async_unknown_area_floor_label_references

        items = await async_unknown_area_floor_label_references(self.hass)
        return self._async_hygiene_finding(
            "unknown_area_floor_label_references", SEVERITY_LOW,
            "Automations/scripts target areas, floors, or labels that no longer exist",
            f"{len(items)} area/floor/label reference(s) in automations or scripts point at "
            "something no longer in the registry.",
            items,
        )

    async def _check_alert_unknown_references(self) -> list[dict]:
        """check="alert_unknown_references"; Spook-inspired, HIGH severity."""
        from .config_hygiene import async_alert_unknown_references

        items = await async_alert_unknown_references(
            self.hass, config=await self._async_sweep_yaml()
        )
        return self._async_hygiene_finding(
            "alert_unknown_references", SEVERITY_HIGH,
            "An alert: entry references an entity or notifier that no longer exists",
            f"{len(items)} alert: reference(s) (watched entity or notify target) point at "
            "something that no longer exists — that alert has silently stopped working.",
            items,
        )

    async def _check_notify_group_unknown_members(self) -> list[dict]:
        """check="notify_group_unknown_members"; Spook-inspired."""
        from .config_hygiene import async_notify_group_unknown_members

        items = await async_notify_group_unknown_members(self.hass)
        return self._async_hygiene_finding(
            "notify_group_unknown_members", SEVERITY_MEDIUM,
            "A notify group references a member that no longer exists",
            f"{len(items)} notify group member reference(s) point at a service or entity that no "
            "longer exists — notifications sent to that group silently reach fewer recipients.",
            items,
        )

    async def _check_person_unknown_trackers(self) -> list[dict]:
        """check="person_unknown_trackers"; Spook-inspired."""
        from .config_hygiene import async_person_unknown_trackers

        items = await async_person_unknown_trackers(self.hass)
        return self._async_hygiene_finding(
            "person_unknown_trackers", SEVERITY_MEDIUM,
            "A person entity references a device tracker that no longer exists",
            f"{len(items)} person/device_tracker reference(s) point at a tracker that no longer "
            "exists — presence detection for that person is based on incomplete data.",
            items,
        )

    async def _check_group_unknown_members(self) -> list[dict]:
        """check="group_unknown_members" - Spook-inspired."""
        from .config_hygiene import async_group_unknown_members

        items = await async_group_unknown_members(self.hass)
        return self._async_hygiene_finding(
            "group_unknown_members", SEVERITY_LOW,
            "A group entity references a member that no longer exists",
            f"{len(items)} group member reference(s) point at an entity that no longer exists — "
            "an aggregation like \"all doors\"/\"all locks\" is silently monitoring fewer entities "
            "than configured.",
            items,
        )

    async def _check_proximity_unknown_references(self) -> list[dict]:
        """check="proximity_unknown_references" - Spook-inspired."""
        from .config_hygiene import async_proximity_unknown_references

        items = await async_proximity_unknown_references(self.hass)
        return self._async_hygiene_finding(
            "proximity_unknown_references", SEVERITY_LOW,
            "A proximity entry references a zone or tracked entity that no longer exists",
            f"{len(items)} proximity reference(s) (zone, tracked entity, or ignored zone) point at "
            "something that no longer exists.",
            items,
        )

    async def _check_lovelace_missing_resources(self) -> list[dict]:
        """check="lovelace_missing_resources"; informational. Only /local/ resource URLs are checkable."""
        from .config_hygiene import async_lovelace_missing_resources

        items = await async_lovelace_missing_resources(self.hass)
        return self._async_hygiene_finding(
            "lovelace_missing_resources", SEVERITY_INFO,
            "A Lovelace resource points at a local file that doesn't exist",
            f"{len(items)} dashboard resource(s) under /local/ don't correspond to a real file — "
            "the card(s) using them will fail to render.",
            items,
        )

    async def _check_empty_areas_and_floors(self) -> list[dict]:
        """check="empty_areas_and_floors" - informational, pure registry tidiness."""
        from .config_hygiene import async_empty_areas_and_floors

        result = await async_empty_areas_and_floors(self.hass)
        items = [{"kind": "area", "name": n} for n in result["areas"]] + [
            {"kind": "floor", "name": n} for n in result["floors"]
        ]
        return self._async_hygiene_finding(
            "empty_areas_and_floors", SEVERITY_INFO,
            "Areas or floors with nothing assigned to them",
            f"{len(items)} area(s)/floor(s) have no devices or entities assigned — organizational "
            "tidiness only, no functional impact.",
            items,
        )

    async def _check_unused_labels_and_blueprints(self) -> list[dict]:
        """check="unused_labels_and_blueprints" - informational, pure registry tidiness."""
        from .config_hygiene import async_unused_labels_and_blueprints

        result = await async_unused_labels_and_blueprints(self.hass)
        items = [{"kind": "label", "name": n} for n in result["labels"]] + [
            {"kind": "blueprint", "name": n} for n in result["blueprints"]
        ]
        return self._async_hygiene_finding(
            "unused_labels_and_blueprints", SEVERITY_INFO,
            "Labels or blueprints that aren't attached to or used by anything",
            f"{len(items)} label(s)/blueprint(s) aren't attached to or used by anything — "
            "organizational tidiness only, no functional impact.",
            items,
        )

    async def _check_unknown_customize_entities(self) -> list[dict]:
        """check="unknown_customize_entities"; informational."""
        from .config_hygiene import async_unknown_customize_entities

        entity_ids = await async_unknown_customize_entities(
            self.hass, config=await self._async_sweep_yaml()
        )
        items = HygieneResult(
            [{"entity_id": e} for e in entity_ids], status=entity_ids.status
        )
        return self._async_hygiene_finding(
            "unknown_customize_entities", SEVERITY_INFO,
            "customize: blocks for entities that no longer exist",
            f"{len(items)} customize: entry/entries reference an entity_id that no longer exists — "
            "dead configuration, safe to remove.",
            items,
        )

    async def _check_orphaned_statistics(self) -> list[dict]:
        """check="orphaned_statistics" - informational, database bloat only."""
        from .config_hygiene import async_orphaned_statistics

        statistic_ids = await async_orphaned_statistics(self.hass)
        items = HygieneResult(
            [{"statistic_id": s} for s in statistic_ids], status=statistic_ids.status
        )
        return self._async_hygiene_finding(
            "orphaned_statistics", SEVERITY_INFO,
            "Long-term statistics exist for entities that no longer exist",
            f"{len(items)} statistic series have no corresponding live entity — most often left "
            "behind after an entity was renamed or removed. Database bloat only.",
            items,
        )

    async def _check_energy_unknown_references(self) -> list[dict]:
        """check="energy_unknown_references" - informational."""
        from .config_hygiene import async_energy_unknown_references

        items = await async_energy_unknown_references(self.hass)
        return self._async_hygiene_finding(
            "energy_unknown_references", SEVERITY_INFO,
            "The Energy dashboard references a source that no longer exists",
            f"{len(items)} Energy dashboard reference(s) point at a statistic/entity that no "
            "longer exists — that source will show as missing data on the Energy dashboard.",
            items,
        )

    async def _check_notify_coverage_gaps(self) -> list[dict]:
        """check="notify_coverage_gaps": LOW for an untracked source, MEDIUM for
        one the operator deliberately toggled off."""
        from .config_hygiene import async_notify_coverage_gaps

        items = await async_notify_coverage_gaps(self.hass, self._store)
        if getattr(items, "status", None) == HYGIENE_COULD_NOT_EVALUATE:
            return []

        untracked = [i for i in items if i["gap"] == "untracked"]
        disabled = [i for i in items if i["gap"] == "disabled"]
        tail = (
            " - if that source goes silently unavailable, the dashboard won't reflect it and "
            "the only sign will be the notification never arriving."
        )

        finalize_items: list[tuple[dict, str, dict[str, str]]] = []
        if untracked:
            summary = (
                f"{len(untracked)} notify automation(s) trigger off a source Security Integrations "
                "Health doesn't track at all" + tail
            )
            finding = _new_finding(
                "misconfig:notify_coverage_gaps:untracked", "notify_coverage_gaps",
                SEVERITY_LOW,
                title="Notify automations depend on a source Security Integrations Health isn't watching",
                summary=summary,
                detail=_capped_detail("items", untracked),
            )
            finalize_items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": summary,
            }))
        if disabled:
            summary = (
                f"{len(disabled)} notify automation(s) trigger off a source that IS trackable but "
                "has its Security Integrations Health toggle turned off in Settings" + tail
            )
            finding = _new_finding(
                "misconfig:notify_coverage_gaps:disabled", "notify_coverage_gaps",
                SEVERITY_MEDIUM,
                title="Notify automations depend on a source whose Security Health toggle is off",
                summary=summary,
                detail=_capped_detail("items", disabled),
            )
            finalize_items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": summary,
            }))
        return self._async_finalize_check("notify_coverage_gaps", finalize_items)

    async def _check_broken_entity_references(self) -> list[dict]:
        """check="broken_entity_references"; one aggregated finding from entity_remap.py's single-pass scan."""
        from .entity_remap import async_scan_broken_references

        broken = await async_scan_broken_references(self.hass)
        if not broken:
            return self._async_finalize_check("broken_entity_references", [])

        finding = _new_finding(
            "misconfig:broken_entity_references", "broken_entity_references", SEVERITY_LOW,
            title="Automations, scripts, or scenes reference entities that no longer exist",
            summary=(
                f"{len(broken)} entity_id(s) are referenced by an automation, script, "
                "scene, or helper but don't correspond to any known entity — most often "
                "left behind after a device was replaced or an entity was renamed. Fix "
                "them from the HA SOC Entity ReMap tab."
            ),
            detail=_capped_detail("broken", broken),
        )
        return self._async_finalize_check(
            "broken_entity_references",
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            })],
        )
