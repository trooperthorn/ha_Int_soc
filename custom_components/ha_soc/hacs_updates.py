"""Force-refresh and update everything HACS has downloaded.

HACS re-checks each repository on its own schedule and only then lets the
update entity show a newer version, so keeping twenty custom integrations
current is a manual round of "Update information" clicks. This module does
that round in one call through HACS's own objects, the way HACS's
``hacs/repository/refresh`` WebSocket command does it, and then installs
through Home Assistant's ``update.install`` service so every download is the
same code path a click on the update entity runs.

HACS internals are not a stable API: every read is defensive and a HACS that
is absent, disabled, or shaped differently is reported as such rather than
guessed at. The design and the owner-only tier are in docs/design.md.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import homeassistant.util.dt as dt_util

if TYPE_CHECKING:
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

AUDIT_CATEGORY_REFRESH = "hacs_refresh_all"
AUDIT_CATEGORY_UPDATE = "hacs_update_all"

# A refresh is one or more GitHub calls per repository; HACS itself disables
# when the remaining rate limit drops. Sequential, capped, and each failure
# is per repository so one bad repository does not stop the rest.
MAX_REPOSITORIES = 200
UPDATE_TIMEOUT_SECONDS = 600


class HacsUnavailable(Exception):
    """HACS is not loaded, is disabled, or is not shaped as expected."""


def _hacs(hass: HomeAssistant) -> Any:
    hacs = hass.data.get("hacs")
    if hacs is None:
        raise HacsUnavailable("HACS is not installed or not loaded")
    try:
        if hacs.system.disabled:
            reason = getattr(hacs.system, "disabled_reason", None)
            raise HacsUnavailable(f"HACS is disabled ({reason})" if reason else "HACS is disabled")
    except AttributeError as err:
        raise HacsUnavailable("HACS runtime data is not shaped as expected") from err
    return hacs


def _downloaded(hacs: Any) -> list[Any]:
    try:
        repos = list(hacs.repositories.list_downloaded)
    except AttributeError as err:
        raise HacsUnavailable("HACS repositories are not readable") from err
    repos.sort(key=lambda r: str(getattr(getattr(r, "data", None), "full_name", "")).lower())
    return repos[:MAX_REPOSITORIES]


def _entity_id(hass: HomeAssistant, repo: Any) -> str | None:
    """The HACS update entity for a repository: platform hacs, unique id = the repository id."""
    registry = er.async_get(hass)
    return registry.async_get_entity_id("update", "hacs", str(repo.data.id))


def _row(hass: HomeAssistant, repo: Any) -> dict[str, Any]:
    data = repo.data
    entity_id = _entity_id(hass, repo)
    state = hass.states.get(entity_id) if entity_id else None
    return {
        "id": str(data.id),
        "full_name": str(data.full_name),
        "category": str(data.category),
        "installed_version": getattr(repo, "display_installed_version", None),
        "available_version": getattr(repo, "display_available_version", None),
        "pending_update": bool(getattr(repo, "pending_update", False)),
        "entity_id": entity_id,
        "entity_state": state.state if state else None,
        "in_progress": bool(state.attributes.get("in_progress")) if state else False,
    }


async def async_hacs_status(hass: HomeAssistant, store: Any) -> dict[str, Any]:
    """What HACS has downloaded and which of it has an update waiting."""
    last = (store.data.get("hacs_updates") or {}) if hasattr(store, "data") else {}
    try:
        hacs = _hacs(hass)
        repos = _downloaded(hacs)
    except HacsUnavailable as err:
        return {
            "available": False,
            "reason": str(err),
            "repositories": [],
            "pending": 0,
            "last_refresh": last.get("last_refresh"),
            "last_update": last.get("last_update"),
        }
    rows = [_row(hass, repo) for repo in repos]
    return {
        "available": True,
        "reason": None,
        "repositories": rows,
        "pending": sum(1 for r in rows if r["pending_update"]),
        "last_refresh": last.get("last_refresh"),
        "last_update": last.get("last_update"),
    }


async def async_hacs_refresh_all(
    hass: HomeAssistant, store: Any, audit: "AuditLog", *, user_id: str | None
) -> dict[str, Any]:
    """Re-fetch every downloaded repository's metadata now, as HACS's own refresh does."""
    hacs = _hacs(hass)
    repos = _downloaded(hacs)
    refreshed: list[str] = []
    failed: list[dict[str, str]] = []
    for repo in repos:
        name = str(repo.data.full_name)
        try:
            await repo.update_repository(ignore_issues=True, force=True)
            refreshed.append(name)
        except Exception as err:  # noqa: BLE001 - one repository must not stop the rest
            _LOGGER.warning("HACS refresh of %s failed: %s", name, err)
            failed.append({"full_name": name, "error": str(err)})
    try:
        await hacs.data.async_write()
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("HACS data write after refresh failed: %s", err)
    for coordinator in list(getattr(hacs, "coordinators", {}).values()):
        try:
            coordinator.async_update_listeners()
        except Exception:  # noqa: BLE001
            continue
    now = dt_util.utcnow().isoformat()
    _remember(store, last_refresh=now)
    pending = [r["full_name"] for r in (_row(hass, repo) for repo in repos) if r["pending_update"]]
    audit.async_log(
        AUDIT_CATEGORY_REFRESH,
        user_id=user_id,
        detail={"refreshed": len(refreshed), "failed": failed, "pending_after": pending},
        flush=True,
    )
    return {"refreshed": refreshed, "failed": failed, "pending_after": pending, "at": now}


async def async_hacs_update_all(
    hass: HomeAssistant,
    store: Any,
    audit: "AuditLog",
    *,
    user_id: str | None,
    repository_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Install every pending HACS update (or the named ones) through update.install."""
    hacs = _hacs(hass)
    repos = _downloaded(hacs)
    wanted = set(repository_ids) if repository_ids else None
    installed: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for repo in repos:
        row = _row(hass, repo)
        if wanted is not None and row["id"] not in wanted:
            continue
        if not row["pending_update"]:
            if wanted is not None:
                skipped.append({"full_name": row["full_name"], "reason": "no update pending"})
            continue
        if not row["entity_id"]:
            skipped.append({"full_name": row["full_name"], "reason": "no update entity"})
            continue
        try:
            async with asyncio.timeout(UPDATE_TIMEOUT_SECONDS):
                await hass.services.async_call(
                    "update", "install", {"entity_id": row["entity_id"]}, blocking=True
                )
            installed.append(
                {
                    "full_name": row["full_name"],
                    "from": row["installed_version"],
                    "to": row["available_version"],
                    "entity_id": row["entity_id"],
                }
            )
        except Exception as err:  # noqa: BLE001 - reported per repository
            _LOGGER.warning("HACS update of %s failed: %s", row["full_name"], err)
            failed.append({"full_name": row["full_name"], "error": str(err)})
    now = dt_util.utcnow().isoformat()
    _remember(store, last_update=now)
    audit.async_log(
        AUDIT_CATEGORY_UPDATE,
        user_id=user_id,
        detail={"installed": installed, "skipped": skipped, "failed": failed},
        flush=True,
    )
    return {
        "installed": installed,
        "skipped": skipped,
        "failed": failed,
        "at": now,
        # HACS integrations take effect after a Core restart; the panel says so.
        "restart_needed": any(i for i in installed),
    }


def _remember(store: Any, **fields: str) -> None:
    current = dict(store.data.get("hacs_updates") or {})
    current.update(fields)
    store.data["hacs_updates"] = current
    store.async_schedule_save()
