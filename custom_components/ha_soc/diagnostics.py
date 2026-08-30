"""Diagnostics support for HA SOC.

Downloaded from Settings > Devices & Services > HA SOC > Download
diagnostics, and intended to be safe to attach to a GitHub issue as-is.
That drives two deliberate choices:

- Secrets (API keys, tokens, the probe pairing secret) are never included,
  only whether each one is configured. Since work item SEC-1 the secret
  values do not even pass through here: they live in the private secret
  store, and this module asks it per key for presence only, so the
  "<key>_set" flags stay accurate while the settings dict itself carries
  no credential. Host addresses for the UniFi connections are treated the
  same way as secrets: an internal IP identifies the installation and a
  bug report only needs to know whether one is set.
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
from .secrets_store import PROBE_PAIRING_SECRET_KEY, HaSocSecretStore

# Settings that are not credentials but still identify the installation
# (internal hostnames / IPs). Redacted to a presence flag like secrets.
_PRIVATE_SETTING_KEYS = frozenset({"unifi_network_host", "unifi_protect_host"})


async def _safe_settings(
    settings: dict[str, Any], secrets: HaSocSecretStore
) -> dict[str, Any]:
    """The settings block of the diagnostics payload: non-secret settings
    verbatim, private hosts and secrets as placeholder-plus-presence-flag.
    The output shape is unchanged from before SEC-1 (every secret key still
    appears, with its companion "<key>_set" boolean); only the source of
    the presence answer moved to the secret store."""
    out: dict[str, Any] = {}
    for key, value in settings.items():
        if key in SECRET_SETTING_KEYS:
            # Defensive: settings must not carry secret values anymore, but
            # if one ever slipped back in it must not reach the download.
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
            # The pairing secret moved to the secret store (SEC-1); only
            # its presence is asked for, never the value.
            "addon_paired": bool(await secrets.async_get(PROBE_PAIRING_SECRET_KEY)),
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
