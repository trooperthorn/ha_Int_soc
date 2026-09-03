"""Constants shared across every HA SOC module.

Only values that cross module boundaries live here; module-local constants
stay next to the code that uses them.
"""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "ha_soc"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 0
STORAGE_SAVE_DELAY = 15  # seconds, debounced

# Audit JSONL files and the chain head live here; never written on the event loop.
AUDIT_STORAGE_SUBDIR = f"{DOMAIN}_audit"

# A topic is appended to the signal, e.g. f"{SIGNAL_UPDATE}_users".
SIGNAL_UPDATE = f"{DOMAIN}_update"

# Custom bus event fired for user-built automations (ha_soc_alert).
EVENT_ALERT = f"{DOMAIN}_alert"

ACCESS_LEVEL_OWNER_ONLY = "owner_only"
ACCESS_LEVEL_OWNER_AND_ADMINS = "owner_and_admins"
DEFAULT_ACCESS_LEVEL = ACCESS_LEVEL_OWNER_ONLY
CONF_ACCESS_LEVEL = "access_level"

MFA_POLICY_AUDIT_ONLY = "audit_only"
MFA_POLICY_AUTO_DEACTIVATE = "auto_deactivate"
DEFAULT_MFA_POLICY = MFA_POLICY_AUDIT_ONLY
DEFAULT_MFA_GRACE_PERIOD_DAYS = 14
CONF_MFA_POLICY = "mfa_policy"
CONF_MFA_GRACE_PERIOD_DAYS = "mfa_grace_period_days"

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

SYSLOG_TRANSPORT_DISABLED = "disabled"
SYSLOG_TRANSPORT_UDP = "udp"
SYSLOG_TRANSPORT_TCP = "tcp"
SYSLOG_TRANSPORT_TLS = "tls"
SYSLOG_TRANSPORTS = (
    SYSLOG_TRANSPORT_DISABLED,
    SYSLOG_TRANSPORT_UDP,
    SYSLOG_TRANSPORT_TCP,
    SYSLOG_TRANSPORT_TLS,
)
DEFAULT_SYSLOG_TRANSPORT = SYSLOG_TRANSPORT_DISABLED
DEFAULT_SYSLOG_PORT = 514
DEFAULT_SYSLOG_TLS_VERIFY = True
DEFAULT_SYSLOG_FACILITY = 16  # local0
SYSLOG_FORMAT_RFC5424_JSON = "rfc5424_json"
SYSLOG_FORMAT_CEF = "cef"
SYSLOG_FORMAT_RAW_JSON = "raw_json"
SYSLOG_FORMATS = (
    SYSLOG_FORMAT_RFC5424_JSON,
    SYSLOG_FORMAT_CEF,
    SYSLOG_FORMAT_RAW_JSON,
)
DEFAULT_SYSLOG_FORMAT = SYSLOG_FORMAT_RFC5424_JSON
CONF_SYSLOG_TRANSPORT = "syslog_transport"
CONF_SYSLOG_FORMAT = "syslog_format"
CONF_SYSLOG_HOST = "syslog_host"
CONF_SYSLOG_PORT = "syslog_port"
CONF_SYSLOG_TLS_VERIFY = "syslog_tls_verify"
CONF_SYSLOG_FACILITY = "syslog_facility"

CONF_SNMP_ENABLED = "snmp_enabled"
CONF_SNMP_LISTEN_ADDRESS = "snmp_listen_address"
CONF_SNMP_PORT = "snmp_port"
CONF_SNMP_USERNAME = "snmp_username"
CONF_SNMP_AUTH_PASSPHRASE = "snmp_auth_passphrase"
CONF_SNMP_PRIV_PASSPHRASE = "snmp_priv_passphrase"
DEFAULT_SNMP_ENABLED = False
DEFAULT_SNMP_PORT = 161

CONF_UNIFI_NETWORK_HOST = "unifi_network_host"
CONF_UNIFI_NETWORK_API_KEY = "unifi_network_api_key"
CONF_UNIFI_NETWORK_VERIFY_SSL = "unifi_network_verify_ssl"
CONF_UNIFI_PROTECT_HOST = "unifi_protect_host"
CONF_UNIFI_PROTECT_API_KEY = "unifi_protect_api_key"
CONF_UNIFI_PROTECT_VERIFY_SSL = "unifi_protect_verify_ssl"

# Off by default: UniFi consoles ship self-signed certificates; see docs/operations.md.
DEFAULT_UNIFI_VERIFY_SSL = False

# Hardcoded literals; only the host ever comes from the user.
UNIFI_NETWORK_API_PATH = "/proxy/network/integration/v1"
UNIFI_PROTECT_API_PATH = "/proxy/protect/integration/v1"

CONF_PIHOLE_HOST = "pihole_host"
CONF_PIHOLE_API_KEY = "pihole_api_key"
CONF_PIHOLE_VERIFY_SSL = "pihole_verify_ssl"
CONF_PIHOLE_IOT_CIDR = "pihole_iot_cidr"
DEFAULT_PIHOLE_VERIFY_SSL = False
PIHOLE_API_PATH = "/api"

# Every credential-shaped setting belongs here; async_log and ws_settings_get redact by it.
SECRET_SETTING_KEYS: frozenset[str] = frozenset(
    {
        CONF_NVD_API_KEY,
        CONF_GITHUB_TOKEN,
        CONF_UNIFI_NETWORK_API_KEY,
        CONF_UNIFI_PROTECT_API_KEY,
        CONF_PIHOLE_API_KEY,
        CONF_SNMP_AUTH_PASSPHRASE,
        CONF_SNMP_PRIV_PASSPHRASE,
    }
)
REDACTED_PLACEHOLDER = "[redacted]"

# The only keys ever read out of another integration's config entry; see docs/security.md.
INTEGRATION_LOCATOR_KEYS: tuple[str, ...] = (
    "host",
    "hosts",
    "ip",
    "ip_address",
    "address",
    "url",
    "base_url",
    "device",
    "port",
    "serial_port",
    "path",
    "usb_path",
    "entity_id",
    "source",
    "source_entity_id",
)

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

STATUS_NEW = "new"
STATUS_CONFIRMED = "confirmed"
STATUS_DISMISSED = "dismissed"
STATUS_RESOLVED = "resolved"

DETECTION_OPEN = "open"
DETECTION_ACK = "ack"
DETECTION_RESOLVED = "resolved"

LEVEL_ENFORCED = "enforced"
LEVEL_COSMETIC = "cosmetic"
LEVEL_BEST_EFFORT = "best_effort"

# Matched exactly against get_addons_info()'s per-addon "name"; slugs are repository-derived.
PROBE_ADDON_NAME = "HA SOC Probe"

SERVICE_INGEST_PROBE_RESULT = "ingest_probe_result"

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

# The one chain this project owns; nothing outside it is ever touched. See docs/security.md.
HA_SOC_RULES_CHAIN = "HA_SOC_RULES"

SERVICE_POLL_FIREWALL_COMMAND = "poll_firewall_command"

# Separate from poll_firewall_command on purpose; see docs/design.md.
SERVICE_POLL_SNMP_CONFIG = "poll_snmp_config"

FIREWALL_RULE_ACTIONS = ["allow", "deny"]
FIREWALL_RULE_PROTOS = ["tcp", "udp"]

# A sourced rule is pinned to its address family; a rule with no source defaults to "both".
FIREWALL_RULE_FAMILY_V4 = "4"
FIREWALL_RULE_FAMILY_V6 = "6"
FIREWALL_RULE_FAMILY_BOTH = "both"
FIREWALL_RULE_FAMILIES = [
    FIREWALL_RULE_FAMILY_V4,
    FIREWALL_RULE_FAMILY_V6,
    FIREWALL_RULE_FAMILY_BOTH,
]

# Bound on add-on-supplied text; the add-on truncates to the same length before sending.
FIREWALL_REPORT_REASON_MAX = 200

# Pending-test state machine (HaSocData.data["firewall"]["pending"]).
FIREWALL_TEST_TESTING = "testing"
FIREWALL_TEST_CONFIRMED = "confirmed"
FIREWALL_TEST_REVERTED = "reverted"
# Window passed with no add-on report yet; the slot stays occupied until one arrives.
FIREWALL_TEST_EXPIRED_UNREPORTED = "expired_unreported"
# Owner cleared the slot by hand; only this and the add-on's own report ever clear it.
FIREWALL_TEST_DISCARDED_UNREPORTED = "discarded_unreported"

DEFAULT_FIREWALL_TEST_WINDOW_SECONDS = 45

# Full design in docs/RESOURCE-WATCHDOG.md.
WATCHDOG_ACTION_ALERT = "alert"
WATCHDOG_ACTION_RESTART = "restart"
WATCHDOG_ACTION_STOP = "stop"
WATCHDOG_ACTIONS = [WATCHDOG_ACTION_ALERT, WATCHDOG_ACTION_RESTART, WATCHDOG_ACTION_STOP]

DEFAULT_WATCHDOG_ENABLED = False  # opt-in: never auto-acts out of the box
DEFAULT_WATCHDOG_CPU_PERCENT = 85
DEFAULT_WATCHDOG_MEMORY_PERCENT = 85
DEFAULT_WATCHDOG_ACTION = WATCHDOG_ACTION_RESTART
DEFAULT_WATCHDOG_SUSTAINED_SAMPLES = 3
DEFAULT_WATCHDOG_INTERVAL_SECONDS = 60
# Past this the container is downgraded to alert-only; see docs/operations.md.
WATCHDOG_MAX_ACTIONS_PER_HOUR = 3

# Provenance score, never a safety score; no surface may say Safe, Verified, or Trusted.
INTEGRATION_TIER_CORE = "core"  # ships inside HA Core; hassfest-validated
INTEGRATION_TIER_HACS = "hacs"  # tracked by HACS from a GitHub repo
INTEGRATION_TIER_CUSTOM = "custom"  # hand-copied / unmanaged custom_components

INTEGRATION_FLAG_CUSTOM_REPO = "custom_repo"
INTEGRATION_FLAG_CUSTOM_SOURCE_LIST = "custom_source_list"

# Hardcoded literal, never built from user input.
GITHUB_API_BASE = "https://api.github.com"

INTEGRATION_SECURITY_CACHE_TTL_HOURS = 24
