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
guessed at. The design, the owner-only tier, and the owner filter are in
docs/design.md.

Refreshing every downloaded repository one at a time multiplied HACS's own
five to seven GitHub calls per repository by however many repositories are
downloaded, which is where the multi-minute wall time came from. HACS
decorates ``update_repository`` with a concurrency limit of 10 itself, so a
bounded-concurrent refresh here (Semaphore(CONCURRENCY), gather with
exceptions handled per repository) stays inside what HACS already allows
while cutting wall time by roughly the concurrency factor. Per-repository
failure isolation is unchanged: one bad repository still cannot stop the
rest.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
import homeassistant.util.dt as dt_util

from .const import SIGNAL_UPDATE

if TYPE_CHECKING:
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

AUDIT_CATEGORY_REFRESH = "hacs_refresh_all"
AUDIT_CATEGORY_UPDATE = "hacs_update_all"
AUDIT_CATEGORY_SET_OWNERS = "hacs_set_owners"

# A refresh is one or more GitHub calls per repository; HACS itself allows up
# to 10 concurrent update_repository() calls (its own @concurrent decorator),
# so 6 stays under that ceiling while leaving headroom for HACS's own
# background refresh, which can run at the same time.
MAX_REPOSITORIES = 200
CONCURRENCY = 6
UPDATE_TIMEOUT_SECONDS = 600
MAX_OWNERS = 50
# A refresh flagged "in progress" longer than this is presumed to have died
# with the process rather than actually still running, so the panel does not
# stay latched busy forever.
STALE_REFRESH_AFTER = timedelta(minutes=30)


class HacsUnavailable(Exception):
    """HACS is not loaded, is disabled, or is not shaped as expected."""


class HacsBusy(Exception):
    """A refresh is already in progress."""


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


def _release_date(data: Any) -> str | None:
    """ISO 8601 release/update timestamp, defensively: last_updated (epoch-like
    int, per HACS's own doc treated as possibly 0/missing) falls back to
    last_fetched (a datetime), falls back to None. HACS's Python API is not a
    stable one, so every read here is a getattr with a default.
    """
    last_updated = getattr(data, "last_updated", None)
    if isinstance(last_updated, (int, float)) and last_updated > 0:
        try:
            return datetime.fromtimestamp(last_updated, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            pass
    last_fetched = getattr(data, "last_fetched", None)
    if isinstance(last_fetched, datetime):
        try:
            return last_fetched.isoformat()
        except ValueError:
            return None
    return None


def _owner(full_name: str) -> str:
    """The GitHub owner from "owner/repo". Always present in data.full_name,
    unlike data.authors (manifest codeowners), which is often empty and is
    why the panel filters on this instead.
    """
    return full_name.split("/", 1)[0] if "/" in full_name else ""


def _row(hass: HomeAssistant, repo: Any) -> dict[str, Any]:
    data = repo.data
    entity_id = _entity_id(hass, repo)
    state = hass.states.get(entity_id) if entity_id else None
    authors = getattr(data, "authors", None)
    full_name = str(data.full_name)
    return {
        "id": str(data.id),
        "full_name": full_name,
        "owner": _owner(full_name),
        "category": str(data.category),
        "installed_version": getattr(repo, "display_installed_version", None),
        "available_version": getattr(repo, "display_available_version", None),
        "pending_update": bool(getattr(repo, "pending_update", False)),
        "entity_id": entity_id,
        "entity_state": state.state if state else None,
        "in_progress": bool(state.attributes.get("in_progress")) if state else False,
        "authors": list(authors) if authors else [],
        "last_updated": _release_date(data),
    }


def _select(
    repos: list[Any],
    owners: list[str] | None,
    repository_ids: list[str] | None,
) -> list[Any]:
    """Narrow the downloaded repositories to act on.

    Explicit repository_ids win outright (a single-row action from the
    table). Otherwise owners narrows by case-insensitive GitHub owner; an
    empty or missing owners list means all repositories.
    """
    if repository_ids:
        wanted_ids = set(repository_ids)
        return [r for r in repos if str(r.data.id) in wanted_ids]
    if owners:
        wanted_owners = {o.lower() for o in owners}
        return [r for r in repos if _owner(str(r.data.full_name)).lower() in wanted_owners]
    return list(repos)


def _progress(last: dict[str, Any]) -> dict[str, Any]:
    """Progress fields from the store, with a stale in-progress flag aged out."""
    in_progress = bool(last.get("refresh_in_progress"))
    started_at = last.get("refresh_started_at")
    if in_progress and started_at:
        try:
            started = dt_util.parse_datetime(started_at)
        except (TypeError, ValueError):
            started = None
        if started is None or dt_util.utcnow() - started > STALE_REFRESH_AFTER:
            in_progress = False
    return {
        "refresh_in_progress": in_progress,
        "refresh_total": int(last.get("refresh_total") or 0),
        "refresh_done": int(last.get("refresh_done") or 0),
        "refresh_failed": int(last.get("refresh_failed") or 0),
        "refresh_started_at": started_at if in_progress else None,
    }


def _owners_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        owner = row["owner"]
        bucket = counts.setdefault(owner, {"count": 0, "pending": 0})
        bucket["count"] += 1
        if row["pending_update"]:
            bucket["pending"] += 1
    summary = [
        {"owner": owner, "count": data["count"], "pending": data["pending"]}
        for owner, data in counts.items()
    ]
    summary.sort(key=lambda s: (-s["count"], s["owner"].lower()))
    return summary


async def async_hacs_status(hass: HomeAssistant, store: Any) -> dict[str, Any]:
    """What HACS has downloaded, which of it has an update waiting, and the
    persisted owner filter and refresh progress.
    """
    last = (store.data.get("hacs_updates") or {}) if hasattr(store, "data") else {}
    owner_filter = list(last.get("owners") or [])
    progress = _progress(last)
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
            "owner_filter": owner_filter,
            "owners": [],
            **progress,
        }
    rows = [_row(hass, repo) for repo in repos]
    return {
        "available": True,
        "reason": None,
        "repositories": rows,
        "pending": sum(1 for r in rows if r["pending_update"]),
        "last_refresh": last.get("last_refresh"),
        "last_update": last.get("last_update"),
        "owner_filter": owner_filter,
        "owners": _owners_summary(rows),
        **progress,
    }


async def async_hacs_refresh_all(
    hass: HomeAssistant,
    store: Any,
    audit: "AuditLog",
    *,
    user_id: str | None,
    owners: list[str] | None = None,
    repository_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Re-fetch the selected downloaded repositories' metadata now, bounded
    to CONCURRENCY at a time, as HACS's own refresh does.
    """
    hacs = _hacs(hass)
    all_repos = _downloaded(hacs)
    repos = _select(all_repos, owners, repository_ids)

    last = dict(store.data.get("hacs_updates") or {})
    if _progress(last)["refresh_in_progress"]:
        raise HacsBusy("A HACS refresh is already in progress")

    if not repos:
        audit.async_log(
            AUDIT_CATEGORY_REFRESH,
            user_id=user_id,
            detail={"owners": owners or [], "selected": 0, "refreshed": 0, "failed": []},
            flush=True,
        )
        return {"refreshed": [], "failed": [], "pending_after": [], "at": None, "selected": 0, "owners": owners or []}

    total = len(repos)
    started_at = dt_util.utcnow().isoformat()
    _remember(
        store,
        refresh_in_progress=True,
        refresh_total=total,
        refresh_done=0,
        refresh_failed=0,
        refresh_started_at=started_at,
    )

    refreshed: list[str] = []
    failed: list[dict[str, str]] = []
    semaphore = asyncio.Semaphore(CONCURRENCY)
    done = 0
    fail_count = 0
    lock = asyncio.Lock()

    async def _one(repo: Any) -> None:
        nonlocal done, fail_count
        name = str(repo.data.full_name)
        async with semaphore:
            try:
                await repo.update_repository(ignore_issues=True, force=True)
                async with lock:
                    refreshed.append(name)
                    done += 1
            except Exception as err:  # noqa: BLE001 - one repository must not stop the rest
                _LOGGER.warning("HACS refresh of %s failed: %s", name, err)
                async with lock:
                    failed.append({"full_name": name, "error": str(err)})
                    done += 1
                    fail_count += 1
        _remember(store, refresh_done=done, refresh_failed=fail_count)
        async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_hacs")

    try:
        await asyncio.gather(*(_one(repo) for repo in repos))
        try:
            await hacs.data.async_write()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("HACS data write after refresh failed: %s", err)
        for coordinator in list(getattr(hacs, "coordinators", {}).values()):
            try:
                coordinator.async_update_listeners()
            except Exception:  # noqa: BLE001
                continue
    finally:
        _remember(store, refresh_in_progress=False)
        async_dispatcher_send(hass, f"{SIGNAL_UPDATE}_hacs")

    now = dt_util.utcnow().isoformat()
    _remember(store, last_refresh=now)
    pending = [r["full_name"] for r in (_row(hass, repo) for repo in repos) if r["pending_update"]]
    audit.async_log(
        AUDIT_CATEGORY_REFRESH,
        user_id=user_id,
        detail={
            "owners": owners or [],
            "selected": total,
            "refreshed": len(refreshed),
            "failed": failed,
            "pending_after": pending,
        },
        flush=True,
    )
    return {
        "refreshed": refreshed,
        "failed": failed,
        "pending_after": pending,
        "at": now,
        "selected": total,
        "owners": owners or [],
    }


async def async_hacs_update_all(
    hass: HomeAssistant,
    store: Any,
    audit: "AuditLog",
    *,
    user_id: str | None,
    owners: list[str] | None = None,
    repository_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Install every pending HACS update within the selection through update.install."""
    hacs = _hacs(hass)
    all_repos = _downloaded(hacs)
    repos = _select(all_repos, owners, repository_ids)
    narrowed = bool(owners) or bool(repository_ids)
    installed: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    for repo in repos:
        row = _row(hass, repo)
        if not row["pending_update"]:
            if narrowed:
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
        detail={"owners": owners or [], "installed": installed, "skipped": skipped, "failed": failed},
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


async def async_hacs_set_owners(store: Any, owners: list[str]) -> list[str]:
    """Persist the owner filter: stripped, lowercased, deduplicated, capped."""
    seen: list[str] = []
    for raw in owners:
        cleaned = raw.strip().lower()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
        if len(seen) >= MAX_OWNERS:
            break
    _remember(store, owners=seen)
    return seen


def _remember(store: Any, **fields: Any) -> None:
    current = dict(store.data.get("hacs_updates") or {})
    current.update(fields)
    store.data["hacs_updates"] = current
    store.async_schedule_save()
