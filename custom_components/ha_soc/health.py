"""Per-integration health counters and misconfiguration checks.

These are heuristic checks against a live install, not a penetration test.
Every finding this module writes is meant to be reviewed by an admin — the
confirm/dismiss lifecycle lives in store.py's generic finding-table helpers,
not here. A severity is a starting judgment for triage, never a verdict.

Two load-bearing approximations, called out where they matter below:

- Entity "unavailable ratio" is a point-in-time sample taken every 5
  minutes, not a true time-weighted duty cycle. Tracking exact
  unavailable-seconds per entity would need a persistent per-entity
  state-change listener; sampling is honest about being an approximation
  and is good enough for a posture score. Because of this there is no
  ``async_track_state_change_event`` subscription for ``async_stop`` to
  reverse — the internal 5-minute timer is the only thing to cancel.
- Root-logger attribution of a log record to a domain is best-effort: a
  logger name that doesn't start with ``homeassistant.components.<domain>``
  or ``custom_components.<domain>`` is checked against each integration's
  manifest ``loggers`` list, but plenty of third-party libraries log under
  names no manifest declares (e.g. a shared HTTP client). Those records are
  dropped rather than guessed at. Likewise, when a domain has more than one
  config entry, error counts are attributed per-domain and copied onto
  every entry of that domain, since a log record carries no entry_id.

A finding, once set to "dismissed" by an analyst, is never flipped back by
a later pass of these checks — only the resolve path (condition no longer
present) touches status, and it explicitly skips dismissed findings.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import ipaddress
import logging

from homeassistant.config import async_hass_config_yaml
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

from .const import (
    DOMAIN,
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INFO,
    SEVERITY_LOW,
    SEVERITY_MEDIUM,
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

# Generic Repairs translation key used when a check has no dedicated entry
# under translations/en.json's "issues" block (that file is out of scope
# for this module — see the check docstrings for which keys already exist).
GENERIC_ISSUE_TRANSLATION_KEY = "misconfig_finding"

# Per-integration issue categories for the "Issues by Integration" dashboard
# widget. Each config entry gets AT MOST one category — priority order below
# (credential first: a broken credential is usually the root cause behind
# what would otherwise look like a communication or collection problem;
# debug_logging/disabled last since neither is necessarily a problem, just
# something worth a human's attention).
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

# A loaded, non-retrying integration with more than this fraction of its
# entities unavailable is flagged "collection" — it can talk to its
# hub/cloud service (state != setup_retry) but specific devices aren't
# reporting, which is a different problem than the integration itself
# being down.
COLLECTION_UNAVAILABLE_RATIO_THRESHOLD = 0.2

# A loaded integration that isn't failing outright or losing devices
# (collection, above) but is still logging more than this many
# WARNING+ records in 24h — "errors" — has non-fatal issues fetching or
# handling devices/entities worth a human's attention.
ERROR_COUNT_ISSUE_THRESHOLD = 5

_FAILING_STATES = (
    ConfigEntryState.SETUP_ERROR,
    ConfigEntryState.MIGRATION_ERROR,
    ConfigEntryState.FAILED_UNLOAD,
)

# The official Terminal & SSH add-on's slug — everything else SSH-shaped
# is matched by a name/slug substring instead, since this project has no
# way to enumerate every third-party SSH add-on's slug ahead of time.
_KNOWN_SSH_ADDON_SLUGS = {"core_ssh"}


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
    }


def _hour_bucket(moment: datetime) -> int:
    return int(moment.timestamp() // 3600)


def _prune_and_sum(buckets: dict[int, int], now_hour: int, span_hours: int) -> int:
    oldest_kept = now_hour - span_hours + 1
    for hour in [h for h in buckets if h < oldest_kept]:
        del buckets[hour]
    return sum(buckets.values())


class _HealthLogHandler(logging.Handler):
    """Root-logger handler that hands WARNING+ records off to the loop.

    Mirrors the technique HA's own system_log component uses. emit() can run
    on a non-loop thread (any logging call anywhere can), so it must do the
    minimum possible work and hand off via call_soon_threadsafe rather than
    touching hass or the store directly.
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

        self._dispatcher_unsub: Callable[[], None] | None = None
        self._timer_unsub: Callable[[], None] | None = None
        self._started_unsub: Callable[[], None] | None = None
        self._log_handler: _HealthLogHandler | None = None

    # -- Lifecycle ----------------------------------------------------------

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
            # We were (re)started after HA already finished starting (e.g. a
            # config entry reload) — there's no startup flurry to wait out.
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

    # -- Config-entry state tracking -----------------------------------------

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

        Computed fresh on every call rather than cached in the store: the
        one signal that decides "credential" (a pending reauth flow) is
        inherently transient config_entries.flow state, not something this
        module tracks continuously.

        Category is a priority-ordered classification, not a combination —
        each entry gets at most one, in this order:
          1. credential      - a reauth flow is currently pending for it.
          2. failing         - state is setup_error/migration_error/
                                failed_unload.
          3. communication   - state is setup_retry (can't reach its
                                hub/cloud service at all right now).
          4. collection      - state is loaded, but more than
                                COLLECTION_UNAVAILABLE_RATIO_THRESHOLD of its
                                entities are unavailable/unknown (it's
                                connected, but specific devices aren't
                                reporting).
          5. errors          - state is loaded and not already flagged
                                collection, but it's logged more than
                                ERROR_COUNT_ISSUE_THRESHOLD WARNING+ records
                                in 24h — non-fatal trouble fetching/handling
                                devices or entities.
          6. debug_logging   - any of this domain's loggers (core, custom,
                                or manifest-declared) is currently at DEBUG
                                level or more verbose. Not necessarily a
                                problem, but worth knowing about: verbose
                                logs can carry sensitive data and cost
                                performance, and are easy to forget enabled.
          7. disabled        - the entry is registered but disabled_by is
                                set. Also not necessarily a problem — just
                                worth surfacing rather than looking like it
                                silently vanished.
        Anything else (loaded and healthy, or not yet tracked) has no
        category and is excluded from the counts/records below.
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

    # -- Log-volume attribution ----------------------------------------------

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
        # Longest prefix first so a specific manifest-declared logger name
        # wins over an accidental broader match.
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

        # Simplest choice per spec: recompute error_count_24h for this
        # domain's entries right here rather than deferring to the 5-minute
        # ticker, so the count is live instead of up to 5 minutes stale.
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

    # -- Unavailable-ratio sampling + bucket rollup (5-minute ticker) -------

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

    # -- Misconfiguration checks ---------------------------------------------

    def _async_mirror_to_repairs(
        self, finding: dict, translation_key: str, placeholders: dict[str, str]
    ) -> None:
        severity = finding["severity"]
        if severity == "high":
            issue_severity = ir.IssueSeverity.ERROR
        elif severity in ("medium", "low"):
            issue_severity = ir.IssueSeverity.WARNING
        else:
            issue_severity = ir.IssueSeverity.CRITICAL
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
            if finding.get("status") == STATUS_DISMISSED:
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
            if finding["severity"] != SEVERITY_INFO:
                self._async_mirror_to_repairs(finding, translation_key, placeholders)
        self._async_resolve_missing(check, active_ids)
        return findings

    async def async_run_misconfig_checks(self) -> list[dict]:
        checks = (
            self._check_http_insecure,
            self._check_http_hardening,
            self._check_trusted_networks,
            self._check_device_cleartext_url,
            self._check_cloud_egress_inventory,
            self._check_addon_protection_mode,
            self._check_ssh_addon_inventory,
            self._check_ssh_addon_exposed,
        )
        results: list[dict] = []
        for check in checks:
            try:
                results.extend(await check())
            except Exception:  # noqa: BLE001 - one bad check must not stop the rest
                _LOGGER.warning("HA SOC misconfig check %s failed", check.__name__, exc_info=True)
        return results

    async def async_run_config_check(self) -> list[dict]:
        """check="ha_config_invalid" — on its own slower interval.

        Unlike every other check in this module, core creates no persistent
        Repairs issue when the YAML configuration is invalid —
        homeassistant.config.async_check_ha_config_file() is purely
        on-demand (it's exactly what the "Check Configuration" button
        calls), so this project has to run it itself and hold the result.
        Deliberately NOT part of async_run_misconfig_checks()'s 5-minute
        sweep: a full YAML re-validation is real CPU/IO work, unlike this
        module's other checks, which only read already-in-memory registries
        and counters. See __init__.py's CONFIG_CHECK_INTERVAL.
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
        """check="http_insecure" — matches translations/en.json's http_insecure key."""
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
            finding = _new_finding(
                "misconfig:http_insecure:no_ssl", "http_insecure", SEVERITY_LOW,
                title="Home Assistant is served without built-in TLS",
                summary=(
                    "use_ssl is disabled while an external_url is "
                    "configured. Common and legitimate behind a reverse "
                    "proxy that terminates TLS itself — confirm that is "
                    "the case here."
                ),
                detail={"external_url": external_url, "use_ssl": use_ssl},
            )
            items.append((finding, "http_insecure", {}))

        return self._async_finalize_check("http_insecure", items)

    async def _check_http_hardening(self) -> list[dict]:
        """check="http_hardening" — cors/ip_ban/login_attempts_threshold."""
        try:
            conf = await async_hass_config_yaml(self.hass)
        except Exception:  # noqa: BLE001 - includes HomeAssistantError on broken YAML
            _LOGGER.debug("Skipping http_hardening check: could not load YAML config", exc_info=True)
            return []

        http_conf = conf.get("http", {}) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []

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
        """check="trusted_networks_permissive" — one finding per provider."""
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
                },
            )
            items.append((
                finding, "trusted_networks_permissive",
                {"network": ", ".join(str(net) for net in networks) or "(none)"},
            ))

        return self._async_finalize_check("trusted_networks_permissive", items)

    async def _check_device_cleartext_url(self) -> list[dict]:
        """check="device_cleartext_url" — one aggregated finding."""
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
            detail={"devices": devices},
        )
        return self._async_finalize_check(
            "device_cleartext_url",
            [(finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            })],
        )

    async def _check_cloud_egress_inventory(self) -> list[dict]:
        """check="cloud_egress_inventory" — informational, never mirrored."""
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
            detail={"cloud_integrations": cloud_integrations},
        )
        # Inventory, not a problem: no Repairs mirror, upsert only.
        self._store.async_upsert_finding("misconfig_findings", finding["id"], finding)
        return [finding]

    async def _check_addon_protection_mode(self) -> list[dict]:
        """check="addon_unprotected" — Supervisor-only; no-ops off Supervisor.

        "Protected mode" is a real, generic Supervisor add-on setting (any
        add-on can have it, not just SSH-related ones) — disabling it grants
        that add-on's container elevated access to the Supervisor API and
        other add-ons, a real, deliberate weakening of Docker-level
        isolation a user has to consciously flip.
        """
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("addon_unprotected", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []

        for slug, info in addons.items():
            if info.get("protected", True):
                continue
            name = info.get("name") or slug
            finding = _new_finding(
                f"misconfig:addon_unprotected:{slug}", "addon_unprotected", SEVERITY_MEDIUM,
                title=f"{name} is running with Protection mode disabled",
                summary=(
                    f"{name} has Supervisor's Protection mode turned off, "
                    "granting it elevated access to the Supervisor API, "
                    "Docker, and other add-ons rather than staying isolated "
                    "to its own container. Only a small number of add-ons "
                    "(ones that manage other add-ons/backups) legitimately "
                    "need this."
                ),
                detail={"slug": slug},
            )
            items.append((finding, GENERIC_ISSUE_TRANSLATION_KEY, {
                "title": finding["title"], "summary": finding["summary"],
            }))

        return self._async_finalize_check("addon_unprotected", items)

    async def _check_ssh_addon_inventory(self) -> list[dict]:
        """check="ssh_addon_inventory" — informational, never mirrored.

        Best-effort by nature: matched against the official Terminal & SSH
        add-on's known slug plus a name/slug substring fallback for the
        many community SSH add-ons this project can't enumerate ahead of
        time — absence from this list is not proof no SSH access exists.
        """
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return []

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        ssh_addons = [
            {"slug": slug, "name": info.get("name") or slug, "state": info.get("state")}
            for slug, info in addons.items()
            if slug in _KNOWN_SSH_ADDON_SLUGS
            or "ssh" in slug.lower()
            or "ssh" in (info.get("name") or "").lower()
        ]

        finding = _new_finding(
            "misconfig:ssh_addon_inventory", "ssh_addon_inventory", SEVERITY_INFO,
            title="SSH-capable add-ons installed",
            summary=(
                f"{len(ssh_addons)} installed add-on(s) look SSH-capable by "
                "name. Informational only — being installed and running is "
                "normal and often intentional."
            ),
            detail={"addons": ssh_addons},
        )
        self._store.async_upsert_finding("misconfig_findings", finding["id"], finding)
        return [finding]

    async def _check_ssh_addon_exposed(self) -> list[dict]:
        """check="ssh_addon_exposed" — Supervisor-only; no-ops off Supervisor.

        Unlike the inventory above, this one IS a real, mirrored finding:
        the official Terminal & SSH add-on (core_ssh) ships with its port
        *unbound* by default (ingress-only — reachable only through Home
        Assistant's own authenticated web terminal, not a direct SSH
        client). A host-bound port, or host_network enabled outright, means
        someone deliberately opened direct SSH access that bypasses Home
        Assistant's login entirely — worth a human reviewing it, not just
        noting it exists.
        """
        from homeassistant.helpers.hassio import is_hassio

        if not is_hassio(self.hass):
            return self._async_finalize_check("ssh_addon_exposed", [])

        from homeassistant.components.hassio import get_addons_info

        addons = get_addons_info(self.hass) or {}
        items: list[tuple[dict, str, dict[str, str]]] = []

        for slug, info in addons.items():
            name = info.get("name") or slug
            is_ssh = (
                slug in _KNOWN_SSH_ADDON_SLUGS
                or "ssh" in slug.lower()
                or "ssh" in name.lower()
            )
            if not is_ssh:
                continue

            host_network = bool(info.get("host_network"))
            published_ports = sorted(
                host_port for host_port in (info.get("network") or {}).values()
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
