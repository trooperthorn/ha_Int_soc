"""Constants shared across every HA SOC module.

Kept deliberately small: only the values that cross module boundaries live
here. Module-local constants (risk weights, regex patterns, WS command
strings) live next to the code that uses them.
"""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ha_soc"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# -- Storage ------------------------------------------------------------
# The main config/state Store (matrix, settings, finding lifecycle state).
# Kept separate from the audit log, which is high-volume and lives in its
# own rotating JSONL files rather than a single rewrite-on-every-save Store.
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 0
STORAGE_SAVE_DELAY = 15  # seconds, debounced

# Sub-directory under .storage/ where the audit log JSONL files and the
# hash-chain head live. Never written on the event loop.
AUDIT_STORAGE_SUBDIR = f"{DOMAIN}_audit"

# -- Dispatcher / bus -----------------------------------------------------
# Dispatcher signal used to push live updates to the frontend panel and to
# trigger sensor/binary_sensor coordinators. Topic is appended, e.g.
# f"{SIGNAL_UPDATE}_users".
SIGNAL_UPDATE = f"{DOMAIN}_update"

# Custom bus event fired for user-built automations (ha_soc_alert).
EVENT_ALERT = f"{DOMAIN}_alert"

# -- Access control ---------------------------------------------------------
# Who may reach the panel and its ha_soc/* WS commands at all. Defaults to
# the strictest option: a security-posture tool is itself a high-value
# target, so it starts locked to the account owner and must be deliberately
# opened up to every admin, never the other way around.
ACCESS_LEVEL_OWNER_ONLY = "owner_only"
ACCESS_LEVEL_OWNER_AND_ADMINS = "owner_and_admins"
DEFAULT_ACCESS_LEVEL = ACCESS_LEVEL_OWNER_ONLY
CONF_ACCESS_LEVEL = "access_level"

# -- MFA non-compliance policy ------------------------------------------
MFA_POLICY_AUDIT_ONLY = "audit_only"
MFA_POLICY_AUTO_DEACTIVATE = "auto_deactivate"
DEFAULT_MFA_POLICY = MFA_POLICY_AUDIT_ONLY
DEFAULT_MFA_GRACE_PERIOD_DAYS = 14
CONF_MFA_POLICY = "mfa_policy"
CONF_MFA_GRACE_PERIOD_DAYS = "mfa_grace_period_days"

# -- Defaults for the options flow / Store settings ----------------------
DEFAULT_AUDIT_RETENTION_DAYS = 90
DEFAULT_AUDIT_MAX_BYTES = 200 * 1024 * 1024  # 200 MB
DEFAULT_SCANNER_ENABLED = True
DEFAULT_SCANNER_NETWORK_CHECKS_ENABLED = False
DEFAULT_RISK_LEARNING_PERIOD_DAYS = 14

CONF_AUDIT_RETENTION_DAYS = "audit_retention_days"
CONF_AUDIT_MAX_BYTES = "audit_max_bytes"
CONF_SCANNER_ENABLED = "scanner_enabled"
CONF_SCANNER_NETWORK_CHECKS_ENABLED = "scanner_network_checks_enabled"
CONF_NVD_API_KEY = "nvd_api_key"
CONF_GITHUB_TOKEN = "github_token"
CONF_RISK_LEARNING_PERIOD_DAYS = "risk_learning_period_days"

# -- UniFi Network / Protect (local API keys, direct to the devices) ------
# The user provides a local controller host and an API key (UniFi OS →
# Control Plane → Integrations / API), and HA SOC calls the console
# directly over the LAN with an X-API-KEY header. See unifi.py.
CONF_UNIFI_NETWORK_HOST = "unifi_network_host"
CONF_UNIFI_NETWORK_API_KEY = "unifi_network_api_key"
CONF_UNIFI_NETWORK_VERIFY_SSL = "unifi_network_verify_ssl"
CONF_UNIFI_PROTECT_HOST = "unifi_protect_host"
CONF_UNIFI_PROTECT_API_KEY = "unifi_protect_api_key"
CONF_UNIFI_PROTECT_VERIFY_SSL = "unifi_protect_verify_ssl"

# UniFi consoles ship a self-signed certificate by default, so SSL
# verification defaults OFF for a direct-to-LAN connection — the same
# default Home Assistant's own official UniFi integration uses. A user
# fronting the console with a real cert can turn it back on per connection.
DEFAULT_UNIFI_VERIFY_SSL = False

# Local UniFi OS reverse-proxy prefixes. The console exposes each app's
# Integration API under /proxy/<app>/integration/v1 (a hardcoded literal —
# only the host comes from the user, never this path). See unifi.py.
UNIFI_NETWORK_API_PATH = "/proxy/network/integration/v1"
UNIFI_PROTECT_API_PATH = "/proxy/protect/integration/v1"

# Settings keys whose values are secrets — never logged verbatim, never
# returned raw to the frontend. audit.py redacts these inside async_log()
# itself, and ws_settings_get returns a boolean "is set" flag for each
# instead of the value. Add every future credential-shaped setting here.
SECRET_SETTING_KEYS: frozenset[str] = frozenset(
    {CONF_NVD_API_KEY, CONF_GITHUB_TOKEN, CONF_UNIFI_NETWORK_API_KEY, CONF_UNIFI_PROTECT_API_KEY}
)
REDACTED_PLACEHOLDER = "[redacted]"

# -- Severity vocabulary shared by vulns / misconfig / detections / scanner
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITY_INFO = "info"
SEVERITY_ORDER = [
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    SEVERITY_INFO,
]

# -- Finding lifecycle status vocabulary (vulns, misconfig, scanner) -----
STATUS_NEW = "new"
STATUS_CONFIRMED = "confirmed"
STATUS_DISMISSED = "dismissed"
STATUS_RESOLVED = "resolved"

# -- Detection lifecycle status vocabulary -------------------------------
DETECTION_OPEN = "open"
DETECTION_ACK = "ack"
DETECTION_RESOLVED = "resolved"

# -- Enforcement-level vocabulary (shown verbatim in the frontend) -------
LEVEL_ENFORCED = "enforced"
LEVEL_COSMETIC = "cosmetic"
LEVEL_BEST_EFFORT = "best_effort"

# -- Optional HA SOC Probe add-on ----------------------------------------
# The add-on's own `name:` in its config.yaml — matched exactly against
# homeassistant.components.hassio.get_addons_info()'s per-addon `name`
# field to detect it, since a Supervisor add-on's `slug` is derived from
# the installing repository (not something this integration controls or
# can predict ahead of publishing that repository), while `name` is a
# literal string this project owns and sets once.
PROBE_ADDON_NAME = "HA SOC Probe"

# Service this integration exposes for the add-on to call back into, via
# Supervisor's core-API proxy (SUPERVISOR_TOKEN + POST
# http://supervisor/core/api/services/<domain>/<service>).
SERVICE_INGEST_PROBE_RESULT = "ingest_probe_result"

# -- Security Integrations Health (Dashboard section) --------------------
# A curated allowlist of integration domains whose config-entry health is
# always worth surfacing on the dashboard for a security-focused install —
# alongside every entity in a security-relevant ENTITY domain (lock/siren/
# valve), regardless of which integration owns it. Each source is
# independently toggleable in Settings; this list is the default/known
# set, not a hard limit — an integration domain not in this list simply
# isn't offered as a toggle yet, it isn't blocked from anything else.
SECURITY_INTEGRATION_DOMAINS: list[str] = [
    "kidde_homesafe",  # Kidde HomeSafe smoke/CO detectors
    "elkm1",  # Elk-M1 security/alarm panel
    "emporia_vue",  # Emporia Vue energy monitor
    "unifiprotect",  # UniFi Protect cameras/NVR
    "keymaster",  # Lock code/keypad management
]
SECURITY_ENTITY_DOMAINS: list[str] = ["lock", "siren", "valve"]
DEFAULT_SECURITY_SOURCES_ENABLED: dict[str, bool] = dict.fromkeys(
    SECURITY_INTEGRATION_DOMAINS + SECURITY_ENTITY_DOMAINS, True
)
CONF_SECURITY_SOURCES_ENABLED = "security_sources_enabled"

# -- Firewall rules (Host Probe add-on, NET_ADMIN) ------------------------
# Read AND write host iptables state, the one thing in this project that
# actually mutates a host security control instead of just observing one.
# Requires the add-on to declare `privileged: [NET_ADMIN]` on top of the
# `host_network: true` it already has. The add-on's overall Supervisor
# security rating is 1, set unconditionally by its `docker_api` grant, a
# deliberate documented choice; the full privilege ledger lives in
# ha_soc_probe/DOCS.md and the README. Every rule this project ever
# applies lives in one dedicated iptables chain (HA_SOC_RULES_CHAIN
# below) that this project owns outright, plus exactly one jump rule at
# the top of INPUT into that chain; nothing Docker manages and no
# pre-existing host firewall rule is ever touched.
HA_SOC_RULES_CHAIN = "HA_SOC_RULES"

# Service the add-on calls on a fast (~5s) interval to pick up a pending
# apply/confirm/revert instruction — the reverse direction of
# SERVICE_INGEST_PROBE_RESULT, using return_response=True on an ordinary
# service call rather than a new listening port on the add-on (this
# project's own scanner.py already treats "a security tool with more open
# listening sockets than it needs" as the wrong default).
SERVICE_POLL_FIREWALL_COMMAND = "poll_firewall_command"

FIREWALL_RULE_ACTIONS = ["allow", "deny"]
FIREWALL_RULE_PROTOS = ["tcp", "udp"]

# Pending-test state machine (HaSocData.data["firewall"]["pending"]).
FIREWALL_TEST_TESTING = "testing"
FIREWALL_TEST_CONFIRMED = "confirmed"
FIREWALL_TEST_REVERTED = "reverted"
# Display-only status for a pending test whose window has passed with no
# report from the add-on yet. "Unreported" is the load-bearing half: the
# add-on's own timer has (or should have) reverted the rules, but until its
# report arrives Core does not know that for a fact, so the slot stays
# occupied and no new test may be proposed. Replaces the old bare
# "expired" string so the panel can say exactly that.
FIREWALL_TEST_EXPIRED_UNREPORTED = "expired_unreported"

# Window a proposed ruleset stays live before the add-on reverts it
# automatically if nobody confirms — the whole safety mechanism this
# feature exists for. The user asked for "30-60 seconds"; 45s is the
# midpoint, not independently user-configurable yet (see firewall.py).
DEFAULT_FIREWALL_TEST_WINDOW_SECONDS = 45

# -- Container Resource Watchdog ------------------------------------------
# Supervisor exposes NO API to cap an add-on's CPU/memory (verified against
# aiohasupervisor's full AddonsClient surface), so "make sure no container
# runs away" is built from what IS supported plus an explicit opt-in
# escape hatch:
#   * the watchdog samples per-container stats, and on a SUSTAINED breach
#     of its threshold takes a per-container action — alert, restart, or
#     stop — via the real Supervisor API (restart/stop only ever for
#     add-ons, never Core or the Supervisor themselves);
#   * hard caps (real Docker --memory/--cpus) are delivered to the Probe
#     add-on over the existing poll channel and applied against the Docker
#     socket — which requires the Probe's Protection Mode to be DISABLED,
#     a root-equivalent grant the UI spells out before anything is applied,
#     and which must be re-applied whenever Supervisor recreates a
#     container (the add-on re-applies on a timer for exactly that reason).
WATCHDOG_ACTION_ALERT = "alert"
WATCHDOG_ACTION_RESTART = "restart"
WATCHDOG_ACTION_STOP = "stop"
WATCHDOG_ACTIONS = [WATCHDOG_ACTION_ALERT, WATCHDOG_ACTION_RESTART, WATCHDOG_ACTION_STOP]

DEFAULT_WATCHDOG_ENABLED = False  # opt-in: never auto-acts out of the box
DEFAULT_WATCHDOG_CPU_PERCENT = 85
DEFAULT_WATCHDOG_MEMORY_PERCENT = 85
# Per the feature request: once enabled, the default response to a
# sustained breach is an automatic add-on restart (per-container override
# to alert/stop in the panel).
DEFAULT_WATCHDOG_ACTION = WATCHDOG_ACTION_RESTART
DEFAULT_WATCHDOG_SUSTAINED_SAMPLES = 3
DEFAULT_WATCHDOG_INTERVAL_SECONDS = 60
# After this many enforcement actions on one container within an hour the
# watchdog downgrades that container to alert-only — an add-on that
# re-breaches immediately after every restart is a restart LOOP, and
# looping it forever is worse than telling the operator it's broken.
WATCHDOG_MAX_ACTIONS_PER_HOUR = 3

# -- Integration Security (provenance) -----------------------------------
# A PROVENANCE score, not a SAFETY score. HA integrations are arbitrary
# Python running in-process with no sandbox — nothing measured here proves
# code is safe to run. It measures how much is known about where the code
# came from and how it's maintained. Every surface that shows this MUST
# say so; never "Safe"/"Verified"/"Trusted"/a bare shield. See
# integration_security.py's docstring for the full rationale.

# Tier — how vetted the SOURCE of an installed integration is. This is the
# generalization of HACS's own default-store-vs-custom concept to cover
# every install path, not only HACS content.
INTEGRATION_TIER_CORE = "core"  # ships inside HA Core; hassfest-validated
INTEGRATION_TIER_HACS = "hacs"  # tracked by HACS from a GitHub repo
INTEGRATION_TIER_CUSTOM = "custom"  # hand-copied / unmanaged custom_components

# Per variance from the feature request: only the two lowest-provenance
# HACS source origins are flagged, not default-store HACS content.
INTEGRATION_FLAG_CUSTOM_REPO = "custom_repo"
INTEGRATION_FLAG_CUSTOM_SOURCE_LIST = "custom_source_list"

# GitHub REST base — a hardcoded literal, never built from user input.
GITHUB_API_BASE = "https://api.github.com"

# Cache TTL for a repo's GitHub-derived provenance signals, so a refresh
# doesn't re-hit the API for repos already looked up recently.
INTEGRATION_SECURITY_CACHE_TTL_HOURS = 24
