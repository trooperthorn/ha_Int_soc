"""Diagnostics support for HA SOC.

Safe to attach to a GitHub issue as-is: secrets and private hosts appear as
presence flags, personal tables as row counts.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import REDACTED_PLACEHOLDER, SECRET_SETTING_KEYS
from .secrets_store import PROBE_PAIRING_SECRET_KEY, HaSocSecretStore

# Not credentials, but they identify the installation; redacted to a presence flag.
_PRIVATE_SETTING_KEYS = frozenset({"unifi_network_host", "unifi_protect_host"})


async def _safe_settings(
    settings: dict[str, Any], secrets: HaSocSecretStore
) -> dict[str, Any]:
    """The settings block of the diagnostics payload: non-secret settings
    verbatim, private hosts and secrets as placeholder-plus-presence-flag."""
    out: dict[str, Any] = {}
    for key, value in settings.items():
        if key in SECRET_SETTING_KEYS:
            # Defensive: a secret value that slipped back into settings must not reach the download.
            continue
        if key in _PRIVATE_SETTING_KEYS:
            out[key] = REDACTED_PLACEHOLDER if value else None
            out[f"{key}_set"] = bool(value)
        else:
            out[key] = value
    for key in sorted(SECRET_SETTING_KEYS):
        is_set = bool(await secrets.async_get(key))
        out[key] = REDACTED_PLACEHOLDER if is_set else None
        out[f"{key}_set"] = is_set
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
    secrets: HaSocSecretStore = runtime.secrets

    host_probe = store.data.get("host_probe") or {}
    firewall = store.data.get("firewall") or {}
    watchdog = store.data.get("resource_watchdog") or {}

    return {
        "entry": {
            "state": str(entry.state),
            "version": entry.version,
        },
        "settings": await _safe_settings(dict(store.settings), secrets),
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
            # Presence only, never the value.
            "addon_paired": bool(await secrets.async_get(PROBE_PAIRING_SECRET_KEY)),
        },
        "resource_watchdog": {
            # Thresholds are configuration, not installation data.
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
