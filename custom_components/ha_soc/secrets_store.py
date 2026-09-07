"""Dedicated at-rest store for HA SOC's own credentials.

Holds only the keys in ALLOWED_SECRET_KEYS; trust boundary in docs/security.md.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SECRET_SETTING_KEYS

_LOGGER = logging.getLogger(__name__)

SECRET_STORAGE_KEY = f"{DOMAIN}.secrets"
SECRET_STORAGE_VERSION = 1

# On-disk key that re-pairs a running add-on; never rename without a migration.
PROBE_PAIRING_SECRET_KEY = "probe_pairing_secret"
# One JSON map of source slug to secret for ha_soc.ingest_audit callers, pinned per source.
EXTERNAL_AUDIT_SECRETS_KEY = "external_audit_secrets"

# Enforced on every get/set; add a new key to SECRET_SETTING_KEYS first.
ALLOWED_SECRET_KEYS: frozenset[str] = SECRET_SETTING_KEYS | {
    PROBE_PAIRING_SECRET_KEY,
    EXTERNAL_AUDIT_SECRETS_KEY,
}


class HaSocSecretStore:
    """One-key-at-a-time accessor over the private ha_soc.secrets Store.

    Setting None or "" clears a key entirely.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, str]] = Store(
            hass,
            SECRET_STORAGE_VERSION,
            SECRET_STORAGE_KEY,
            private=True,
            atomic_writes=True,
        )
        self._data: dict[str, str] = {}
        self._loaded = False

    def __repr__(self) -> str:
        # Key names only, never values.
        names = ", ".join(sorted(self._data)) or "none"
        return f"<HaSocSecretStore keys set: {names}>"

    @staticmethod
    def _check_key(key: str) -> None:
        if key not in ALLOWED_SECRET_KEYS:
            raise ValueError(
                f"{key!r} is not a known HA SOC secret key; add it to "
                "SECRET_SETTING_KEYS (and every masking path) first"
            )

    async def async_load(self) -> None:
        """Load the on-disk file once. Safe to call again (no-op)."""
        if self._loaded:
            return
        stored = await self._store.async_load()
        if stored:
            # Unknown keys are dropped, not errors; they vanish on the next save.
            self._data = {
                k: v for k, v in stored.items() if k in ALLOWED_SECRET_KEYS and v
            }
        self._loaded = True

    async def async_get(self, key: str) -> str | None:
        """The single value behind ``key``, or None when unset."""
        self._check_key(key)
        return self._data.get(key)

    async def async_set(self, key: str, value: str | None) -> None:
        """Set ``key`` to ``value``; None or "" clears it. Saved immediately, not debounced."""
        self._check_key(key)
        if value:
            self._data[key] = value
        else:
            self._data.pop(key, None)
        await self._store.async_save(dict(self._data))


async def async_migrate_legacy_secrets(secrets: HaSocSecretStore, store) -> list[str]:
    """One-time move of secret values out of the general store.

    Runs on every setup; a no-op once the legacy keys are gone. Returns the
    key names moved. ``store`` is untyped to avoid a circular import with store.py.
    """
    moved: list[str] = []

    settings = store.data["settings"]
    for key in sorted(SECRET_SETTING_KEYS):
        # pop(), so no None placeholder is left behind in settings.
        value = settings.pop(key, None)
        if value:
            await secrets.async_set(key, value)
            moved.append(key)

    firewall = store.data.get("firewall") or {}
    # Removed outright so nothing can read a stale copy from the general store.
    legacy_pin = firewall.pop("addon_secret", None)
    if legacy_pin:
        await secrets.async_set(PROBE_PAIRING_SECRET_KEY, legacy_pin)
        moved.append(PROBE_PAIRING_SECRET_KEY)

    if moved:
        # Save now, not on the debounce timer: plaintext copies stay on disk until this lands.
        await store.async_save_now()
        _LOGGER.info(
            "HA SOC: moved %d secret value(s) into the private secret store "
            "and removed the old copies from %s.",
            len(moved),
            f"{DOMAIN}.storage",
        )
    return moved
