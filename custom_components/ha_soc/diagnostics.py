"""Diagnostics support for HA SOC.

Downloaded from Settings > Devices & Services > HA SOC > Download
diagnostics, and intended to be safe to attach to a GitHub issue as-is.
That drives two deliberate choices:

- Secrets (API keys, tokens, the probe pairing secret) are never included,
  only whether each one is configured. Host addresses for the UniFi
  connections are treated the same way: an internal IP identifies the
  installation and a bug report only needs to know whether one is set.
- Tables that hold personal or per-installation detail (users, audit
  records, findings, permissions) are reported as row counts, not contents.
  A count answers "is the module collecting data" without shipping the
  data itself. Anyone debugging deeper is already an owner and can read
  the full tables in the panel.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import REDACTED_PLACEHOLDER, SECRET_SETTING_KEYS

# Settings that are not credentials but still identify the installation
# (internal hostnames / IPs). Redacted to a presence flag like secrets.
_PRIVATE_SETTING_KEYS = frozenset({"unifi_network_host", "unifi_protect_host"})


def _safe_settings(settings: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in settings.items():
        if key in SECRET_SETTING_KEYS or key in _PRIVATE_SETTING_KEYS:
            out[key] = REDACTED_PLACEHOLDER if value else None
            out[f"{key}_set"] = bool(value)
        else:
            out[key] = value
    return out


def _table_counts(data: dict[str, Any]) -> dict[str, Any]:
    counts: dict[str, Any] = {}
    for table, value in data.items():
        if table == "settings":
            continue
        if isinstance(value, dict):
            counts[table] = len(value)
        elif isinstance(value, list):
            counts[table] = len(value)
        else:
            counts[table] = "set" if value is not None else "empty"
    return counts


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for the (single) HA SOC config entry."""
    runtime = entry.runtime_data
    store = runtime.store

    host_probe = store.data.get("host_probe") or {}
    firewall = store.data.get("firewall") or {}
    watchdog = store.data.get("resource_watchdog") or {}

    return {
        "entry": {
            "state": str(entry.state),
            "version": entry.version,
        },
        "settings": _safe_settings(dict(store.settings)),
        "store_table_counts": _table_counts(dict(store.data)),
        "host_probe": {
            "reported": bool(host_probe),
            "reported_at": host_probe.get("reported_at"),
            "scanner_version": host_probe.get("scanner_version"),
            "port_count": len(host_probe.get("ports") or []),
        },
        "firewall": {
            "rules_reported": firewall.get("known_rules") is not None,
            "rules_reported_at": firewall.get("known_rules_reported_at"),
            "pending_change": firewall.get("pending") is not None,
            "history_length": len(firewall.get("history") or []),
            "addon_paired": bool(firewall.get("addon_secret")),
        },
        "resource_watchdog": {
            # Threshold numbers are configuration, not installation data;
            # they help reproduce watchdog-behavior reports verbatim.
            key: watchdog.get(key)
            for key in (
                "enabled",
                "default_cpu_percent",
                "default_memory_percent",
                "default_action",
                "sustained_samples",
                "interval_seconds",
            )
        },
    }
