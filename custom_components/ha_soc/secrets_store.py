"""Dedicated at-rest store for HA SOC's own credentials (work item SEC-1).

This module exists so that every secret HA SOC holds lives in exactly one
place: a private (0o600), atomically-written Store file of its own
(".storage/ha_soc.secrets"), separate from the general settings/state store.
It holds exactly the values behind const.SECRET_SETTING_KEYS (external API
credentials, the GitHub token, and SNMP passphrases) plus the Probe add-on's
pairing secret under PROBE_PAIRING_SECRET_KEY, and nothing else; an attempt
to store any other key is a programming error and raises.

Honesty about the boundary: this is NOT protection against a hostile
integration. Home Assistant integrations are modules imported into one
Python process with no isolation, so any in-process code that goes looking
can still reach this object through the config entry's runtime data and
call async_get() itself. What the design buys, and why it is still worth
having:

- Fewer copies. A secret exists in one file and one in-memory dict, not in
  settings, not mirrored into entry.options, not inside every settings
  snapshot that gets logged, diagnosed, or sent over the wire.
- No shared-object exposure. The settings dict is handed around freely
  (WebSocket payloads, diagnostics, audit detail); this object never is.
  Its repr prints only which key NAMES are set, its values are reachable
  only one key at a time through an explicit await, and there is no
  property or method that returns all values at once.
- A stronger file mode than settings. The underlying Store is created with
  private=True (0o600) and atomic_writes=True, matching what core itself
  uses for the auth store and password hashes, so other uids on the host
  cannot read it even where the general storage file is world-readable.

The object is held on HaSocRuntimeData only. It is never placed in
hass.data under its own key, and no value it holds is ever logged.
"""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SECRET_SETTING_KEYS

_LOGGER = logging.getLogger(__name__)

SECRET_STORAGE_KEY = f"{DOMAIN}.secrets"
SECRET_STORAGE_VERSION = 1

# Stable storage key for the Probe add-on's pairing secret (the shared
# secret pinned on the add-on's first authenticated call, see firewall.py).
# Before SEC-1 it lived at store.data["firewall"]["addon_secret"]; the name
# below is the permanent home and must never be renamed without a migration,
# because the value on disk under this key is what re-pairs a running
# add-on across restarts.
PROBE_PAIRING_SECRET_KEY = "probe_pairing_secret"

# The complete set of keys this store will ever hold. Enforced on every
# get/set so a future credential cannot drift in here without being added
# to SECRET_SETTING_KEYS (and therefore to every masking/redaction path
# keyed off that set) first.
ALLOWED_SECRET_KEYS: frozenset[str] = SECRET_SETTING_KEYS | {PROBE_PAIRING_SECRET_KEY}


class HaSocSecretStore:
    """One-key-at-a-time accessor over the private ha_soc.secrets Store.

    Access is exclusively ``await async_get(key)`` / ``await async_set(key,
    value)``; there is deliberately no dict-style access and no
    all-values property, so a caller can only ever obtain the single value
    it names, at the moment it needs it (work item SEC-3 relies on that
    shape). Setting None or "" clears a key entirely rather than storing an
    empty string, so "is set" checks stay unambiguous.
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
        # Key NAMES only, never values: this object ends up in
        # HaSocRuntimeData, and a stray repr() of that dataclass must not
        # become a credential leak.
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
            # Drop unknown keys defensively instead of erroring: a file
            # edited by hand or written by a future version must not brick
            # setup, and a dropped unknown key is rewritten out on the next
            # save.
            self._data = {
                k: v for k, v in stored.items() if k in ALLOWED_SECRET_KEYS and v
            }
        self._loaded = True

    async def async_get(self, key: str) -> str | None:
        """The single value behind ``key``, or None when unset."""
        self._check_key(key)
        return self._data.get(key)

    async def async_set(self, key: str, value: str | None) -> None:
        """Set ``key`` to ``value``; None or "" clears it. Saved immediately
        (not debounced) because secrets change rarely and a crash inside a
        debounce window must not lose or resurrect a credential."""
        self._check_key(key)
        if value:
            self._data[key] = value
        else:
            self._data.pop(key, None)
        await self._store.async_save(dict(self._data))


async def async_migrate_legacy_secrets(secrets: HaSocSecretStore, store) -> list[str]:
    """One-time move of secret values out of the general store (SEC-1).

    Two legacy locations are drained: every SECRET_SETTING_KEYS value still
    sitting in store.data["settings"], and the Probe pairing secret at
    store.data["firewall"]["addon_secret"]. Values are written into the
    secret store first (saved immediately, so the private file exists
    before the old copies go away), then the old store is rewritten without
    them. Runs on every setup but is a no-op once the legacy keys are gone,
    so it costs nothing on a migrated install.

    Returns the list of key names that were moved so the caller can verify
    migration behavior internally. Logs expose only the count, never key
    names or values; even the presence of a particular credential is
    unnecessary operational metadata.

    The ``store`` parameter is typed loosely (HaSocData) to avoid a
    circular import between store.py and this module.
    """
    moved: list[str] = []

    settings = store.data["settings"]
    for key in sorted(SECRET_SETTING_KEYS):
        # pop() rather than get(): the settings dict must end up without
        # the key entirely, not with a None placeholder that a future
        # settings snapshot would still carry around.
        value = settings.pop(key, None)
        if value:
            await secrets.async_set(key, value)
            moved.append(key)

    firewall = store.data.get("firewall") or {}
    # The old key is removed outright (absent, per the SEC-1 design) so no
    # code path can ever read a stale copy from the general store again.
    legacy_pin = firewall.pop("addon_secret", None)
    if legacy_pin:
        await secrets.async_set(PROBE_PAIRING_SECRET_KEY, legacy_pin)
        moved.append(PROBE_PAIRING_SECRET_KEY)

    if moved:
        # Rewrite the old store now, not on the debounce timer: until this
        # save lands, the plaintext copies are still on disk in the
        # world-readable file.
        await store.async_save_now()
        _LOGGER.info(
            "HA SOC: moved %d secret value(s) into the private secret store "
            "and removed the old copies from %s.",
            len(moved),
            f"{DOMAIN}.storage",
        )
    return moved
