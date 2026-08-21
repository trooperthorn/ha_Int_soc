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
CONF_RISK_LEARNING_PERIOD_DAYS = "risk_learning_period_days"

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
