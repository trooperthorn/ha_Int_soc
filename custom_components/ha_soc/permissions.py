"""Dashboard/view "permissions matrix" — cosmetic visibility, not access control.

Read this before wiring this module into anything that implies real
security:

Everything here is COSMETIC. Setting a view's `visible` list, flipping a
dashboard's `require_admin`/`show_in_sidebar`, or pushing `hiddenPanels`
into a user's sidebar only changes what that user's OWN frontend chooses to
render. None of it is enforced by Home Assistant's backend: any
authenticated user can call the `lovelace/config` websocket command for ANY
dashboard `url_path` and get back its full, unredacted configuration —
cards, entity ids, and all — regardless of anything this module has set.
There is no permission check on that command in Home Assistant core as of
the 2025.x/dev branch this was written against, and nothing below changes
that.

The only real enforcement lever for "should this user be able to see/reach
X" is the admin / non-admin group split on the user's account, handled in
users.py, not here. Treat every method below as "manage what the dashboard
UI shows", never as "manage what the account can fetch".

This module also talks to several internal, version-sensitive Home
Assistant surfaces (lovelace's runtime `hass.data` container, its
dashboards storage collection, the frontend's per-user storage helper).
None of those are formally public API — "internal but stable" at best — so
every access path here is wrapped defensively and degrades to a logged
WARNING plus a clear `error_reason` string instead of raising, both so a
version mismatch never crashes HA setup and so the websocket layer can
surface a real message instead of a stack trace.
"""
from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_LOVELACE_UPDATED_EVENT = "lovelace_updated"

# Plausible attribute names for the dashboards storage collection off the
# lovelace runtime data container — tried in order, first hit wins.
_DASHBOARDS_COLLECTION_ATTRS = ("dashboards_collection", "collection")

# permissions_matrix is keyed by real url_path strings; the default
# dashboard's url_path is None, which is not a safe/round-trippable JSON
# dict key (Store serializes it as the literal string "null" on save, but
# never converts it back to None on load), so it gets this sentinel key
# instead everywhere this module reads or writes the store.
_DEFAULT_DASHBOARD_KEY = "__default__"


def _to_storage_key(url_path: str | None) -> str:
    return url_path if url_path is not None else _DEFAULT_DASHBOARD_KEY


def _from_storage_key(key: str) -> str | None:
    return None if key == _DEFAULT_DASHBOARD_KEY else key


def _visible_user_ids(visible: Any) -> list[str] | None:
    """Return the explicit user-id allow-list from a view's `visible`.

    None means `visible` is not a per-user list at all (True/absent =
    visible to everyone, False = hidden from everyone) — the caller must
    tell that apart from an explicit-but-empty list, which means hidden
    from everyone too, just spelled differently.
    """
    if isinstance(visible, list):
        return [
            entry.get("user")
            for entry in visible
            if isinstance(entry, dict) and entry.get("user")
        ]
    return None


def _find_view(config: dict[str, Any], view_path: str) -> dict[str, Any] | None:
    views = config.get("views") or []
    for view in views:
        if isinstance(view, dict) and view.get("path") == view_path:
            return view
    # Real dashboards sometimes omit "path" on a view entirely — fall back
    # to treating view_path as a positional index into the views list.
    try:
        index = int(view_path)
    except (TypeError, ValueError):
        return None
    if 0 <= index < len(views) and isinstance(views[index], dict):
        return views[index]
    return None


class PermissionsMatrix:
    """Manages cosmetic dashboard/view visibility and per-user sidebar hiding.

    See the module docstring: nothing here is enforced server-side. This
    class only edits lovelace dashboard configs and per-user frontend
    storage, and mirrors the intended state into HaSocData so the matrix UI
    and async_check_drift() have a source of truth to compare the live
    config against.
    """

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self.store = store
        self._unsub_bus: Callable[[], None] | None = None
        self._unsub_collection: Callable[[], None] | None = None
        # Cached once found; never cached negative, so a lovelace integration
        # that finishes loading after async_start() still gets picked up on
        # the first call that needs it.
        self._dashboards_collection: Any | None = None

    async def async_start(self) -> None:
        self._unsub_bus = self.hass.bus.async_listen(
            _LOVELACE_UPDATED_EVENT, self._on_lovelace_updated
        )

        collection = self._get_dashboards_collection()
        if collection is not None:
            try:
                self._unsub_collection = collection.async_add_listener(
                    self._on_dashboards_changed
                )
            except (AttributeError, TypeError):
                _LOGGER.debug(
                    "Dashboards collection has no usable async_add_listener; "
                    "drift detection will rely on the lovelace_updated event only",
                    exc_info=True,
                )

    async def async_stop(self) -> None:
        if self._unsub_bus is not None:
            self._unsub_bus()
            self._unsub_bus = None
        if self._unsub_collection is not None:
            try:
                self._unsub_collection()
            except Exception:  # noqa: BLE001 - unsub callables should never raise, but never let teardown die
                _LOGGER.debug(
                    "Error unsubscribing dashboards collection listener", exc_info=True
                )
            self._unsub_collection = None

    @callback
    def _on_lovelace_updated(self, event: Event) -> None:
        _LOGGER.debug("lovelace_updated event received: %s", event.data)

    @callback
    def _on_dashboards_changed(self, change_type: str, item_id: str, config: Any) -> None:
        _LOGGER.debug("Dashboards collection changed: %s %s", change_type, item_id)

    # -- Internal: reaching lovelace's runtime state -------------------------

    def _get_lovelace_data(self) -> Any | None:
        try:
            from homeassistant.components.lovelace.const import LOVELACE_DATA
        except ImportError:
            _LOGGER.warning(
                "Could not import LOVELACE_DATA from "
                "homeassistant.components.lovelace.const on this HA version"
            )
            return None

        try:
            return self.hass.data.get(LOVELACE_DATA)
        except (AttributeError, TypeError):
            _LOGGER.warning(
                "Unexpected shape of hass.data while looking up lovelace runtime data",
                exc_info=True,
            )
            return None

    def _get_dashboards(self) -> dict[str | None, Any] | None:
        lovelace_data = self._get_lovelace_data()
        if lovelace_data is None:
            return None

        dashboards = getattr(lovelace_data, "dashboards", None)
        if dashboards is not None:
            return dashboards

        try:
            dashboards = lovelace_data["dashboards"]
        except (KeyError, TypeError):
            dashboards = None

        if dashboards is None:
            _LOGGER.warning(
                "Could not find 'dashboards' on lovelace runtime data (type %s); "
                "this HA version's lovelace internals may have changed",
                type(lovelace_data),
            )
        return dashboards

    def _get_dashboards_collection(self) -> Any | None:
        if self._dashboards_collection is not None:
            return self._dashboards_collection

        lovelace_data = self._get_lovelace_data()
        if lovelace_data is None:
            return None

        for attr in _DASHBOARDS_COLLECTION_ATTRS:
            collection = getattr(lovelace_data, attr, None)
            if collection is not None:
                self._dashboards_collection = collection
                return collection

        if isinstance(lovelace_data, dict):
            for attr in _DASHBOARDS_COLLECTION_ATTRS:
                collection = lovelace_data.get(attr)
                if collection is not None:
                    self._dashboards_collection = collection
                    return collection

        return None

    async def _async_collection_items(self, collection: Any) -> list[Any]:
        data = getattr(collection, "data", None)
        if isinstance(data, dict):
            return list(data.values())

        getter = getattr(collection, "async_items", None)
        if callable(getter):
            try:
                result = getter()
                if inspect.isawaitable(result):
                    result = await result
                if isinstance(result, list):
                    return result
            except (AttributeError, TypeError):
                _LOGGER.debug("collection.async_items() call failed", exc_info=True)

        return []

    @staticmethod
    def _collection_field(item: Any, name: str) -> Any:
        if isinstance(item, dict):
            return item.get(name)
        return getattr(item, name, None)

    # -- Dashboard inventory --------------------------------------------------

    async def async_list_dashboards(self) -> list[dict[str, Any]]:
        dashboards = self._get_dashboards()
        if dashboards is None:
            return []

        items_by_url_path: dict[str | None, Any] = {}
        collection = self._get_dashboards_collection()
        if collection is not None:
            for item in await self._async_collection_items(collection):
                items_by_url_path[self._collection_field(item, "url_path")] = item

        result: list[dict[str, Any]] = []
        for url_path, lovelace_config in dashboards.items():
            item = items_by_url_path.get(url_path)
            result.append(
                {
                    "id": self._collection_field(item, "id"),
                    "url_path": url_path,
                    "title": self._collection_field(item, "title"),
                    "icon": self._collection_field(item, "icon"),
                    "mode": getattr(lovelace_config, "mode", None),
                    "require_admin": self._collection_field(item, "require_admin"),
                    "show_in_sidebar": self._collection_field(item, "show_in_sidebar"),
                }
            )
        return result

    async def async_get_dashboard_config(self, url_path: str | None) -> dict[str, Any] | None:
        dashboards = self._get_dashboards()
        if dashboards is None:
            return None

        lovelace_config = dashboards.get(url_path)
        if lovelace_config is None:
            _LOGGER.warning("No lovelace dashboard found for url_path=%s", url_path)
            return None

        try:
            return await lovelace_config.async_load(False)
        except HomeAssistantError:
            _LOGGER.warning(
                "Failed to load dashboard config for url_path=%s", url_path, exc_info=True
            )
            return None
        except (AttributeError, TypeError):
            _LOGGER.warning(
                "Unexpected lovelace config object shape for url_path=%s",
                url_path,
                exc_info=True,
            )
            return None

    # -- View visibility --------------------------------------------------

    async def async_set_view_visibility(
        self, url_path: str | None, view_path: str, user_ids: list[str]
    ) -> tuple[bool, str | None]:
        dashboards = self._get_dashboards()
        if dashboards is None:
            return (False, "lovelace_internals_unavailable")

        lovelace_config = dashboards.get(url_path)
        if lovelace_config is None:
            return (False, "dashboard_not_found")

        try:
            config = await lovelace_config.async_load(False)
        except HomeAssistantError:
            _LOGGER.warning(
                "Failed to load dashboard %s before setting view visibility",
                url_path,
                exc_info=True,
            )
            return (False, "dashboard_load_failed")
        except (AttributeError, TypeError):
            _LOGGER.warning(
                "Unexpected lovelace config shape for dashboard %s", url_path, exc_info=True
            )
            return (False, "lovelace_internals_unavailable")

        try:
            view = _find_view(config, view_path)
        except (AttributeError, TypeError, KeyError):
            _LOGGER.warning(
                "Unexpected dashboard config shape while locating view %s on %s",
                view_path,
                url_path,
                exc_info=True,
            )
            return (False, "lovelace_internals_unavailable")

        if view is None:
            return (False, "view_not_found")

        previous_user_ids = _visible_user_ids(view.get("visible")) or []

        # Empty user_ids means "reset to visible for everyone" — writing an
        # empty list instead would mean "visible to no one", which is a
        # different and surprising state, so it is never written here.
        view["visible"] = [{"user": uid} for uid in user_ids] if user_ids else True

        try:
            await lovelace_config.async_save(config)
        except HomeAssistantError as err:
            if str(err) == "Not supported":
                return (False, "yaml_dashboard_read_only")
            _LOGGER.warning(
                "Failed to save dashboard %s after setting view visibility",
                url_path,
                exc_info=True,
            )
            return (False, "dashboard_save_failed")
        except (AttributeError, TypeError):
            _LOGGER.warning(
                "Unexpected lovelace config object shape saving dashboard %s",
                url_path,
                exc_info=True,
            )
            return (False, "lovelace_internals_unavailable")

        # expected_policy[uid] = True means "this user should see the view".
        # Users newly listed get True; users dropped from an explicit list
        # get False; but if user_ids is empty (visible-to-all reset), any
        # previously-restricted user now also gets True, not False.
        expected_policy: dict[str, bool] = {uid: True for uid in user_ids}
        for uid in previous_user_ids:
            expected_policy.setdefault(uid, not user_ids)

        storage_key = _to_storage_key(url_path)
        for uid, expected_visible in expected_policy.items():
            policy = self.store.get_user_dashboard_policy(uid, storage_key)
            views_policy = dict(policy.get("views") or {})
            views_policy[view_path] = expected_visible
            self.store.async_set_user_dashboard_policy(
                uid, storage_key, {**policy, "views": views_policy}
            )

        return (True, None)

    # -- Dashboard-level flags ------------------------------------------------

    async def async_set_dashboard_flags(
        self,
        dashboard_id: str,
        *,
        require_admin: bool | None = None,
        show_in_sidebar: bool | None = None,
    ) -> tuple[bool, str | None]:
        collection = self._get_dashboards_collection()
        if collection is None:
            _LOGGER.warning(
                "No dashboards storage collection reachable on this HA version; "
                "change require_admin/show_in_sidebar manually in "
                "Settings > Dashboards instead"
            )
            return (False, "dashboards_collection_unavailable")

        changes: dict[str, Any] = {}
        if require_admin is not None:
            changes["require_admin"] = require_admin
        if show_in_sidebar is not None:
            changes["show_in_sidebar"] = show_in_sidebar

        if not changes:
            return (True, None)

        try:
            await collection.async_update_item(dashboard_id, changes)
        except (AttributeError, TypeError):
            _LOGGER.warning(
                "Dashboards collection does not support async_update_item as expected",
                exc_info=True,
            )
            return (False, "dashboards_collection_unavailable")
        except (HomeAssistantError, KeyError, ValueError):
            _LOGGER.warning(
                "Failed to update dashboard %s flags", dashboard_id, exc_info=True
            )
            return (False, "dashboard_update_failed")

        return (True, None)

    # -- Sidebar push ---------------------------------------------------------

    async def async_push_sidebar_policy(
        self, user_id: str, hidden_dashboard_paths: list[str]
    ) -> tuple[bool, str | None]:
        try:
            from homeassistant.components.frontend import storage as frontend_storage
        except ImportError:
            _LOGGER.warning(
                "Could not import homeassistant.components.frontend.storage on this HA version"
            )
            return (False, "sidebar_store_unavailable")

        try:
            user_store = frontend_storage.async_user_store(self.hass, user_id)
            if inspect.isawaitable(user_store):
                user_store = await user_store
        except (AttributeError, TypeError, HomeAssistantError):
            _LOGGER.warning(
                "Could not reach the frontend user store for user %s", user_id, exc_info=True
            )
            return (False, "sidebar_store_unavailable")

        existing_sidebar: dict[str, Any] = {}
        data = getattr(user_store, "data", None)
        if isinstance(data, dict):
            existing_sidebar = data.get("sidebar") or {}

        if not existing_sidebar:
            getter = getattr(user_store, "async_get_item", None)
            if callable(getter):
                try:
                    fetched = await getter("sidebar")
                    if isinstance(fetched, dict):
                        existing_sidebar = fetched
                except (AttributeError, TypeError, KeyError, HomeAssistantError):
                    _LOGGER.warning(
                        "Could not read existing sidebar customization for user %s; "
                        "proceeding without merging — this user's own panelOrder "
                        "may be overwritten",
                        user_id,
                        exc_info=True,
                    )

        if not isinstance(existing_sidebar, dict):
            existing_sidebar = {}

        panel_order = existing_sidebar.get("panelOrder") or []
        previously_hidden = existing_sidebar.get("hiddenPanels") or []
        merged_hidden = sorted(set(previously_hidden) | set(hidden_dashboard_paths))

        setter = getattr(user_store, "async_set_item", None)
        if not callable(setter):
            _LOGGER.warning("Frontend user store for user %s has no async_set_item", user_id)
            return (False, "sidebar_store_unavailable")

        try:
            await setter(
                "sidebar", {"panelOrder": panel_order, "hiddenPanels": merged_hidden}
            )
        except (AttributeError, TypeError, HomeAssistantError):
            _LOGGER.warning("Failed to push sidebar policy for user %s", user_id, exc_info=True)
            return (False, "sidebar_store_unavailable")

        return (True, None)

    # -- Drift detection ------------------------------------------------------

    async def async_check_drift(self) -> list[dict[str, Any]]:
        """Compare stored intent against live dashboard configs.

        Read-only by design: the matrix UI re-applies a mismatch with an
        explicit call to async_set_view_visibility, this never writes.
        """
        mismatches: list[dict[str, Any]] = []

        dashboards = self._get_dashboards()
        if dashboards is None:
            return mismatches

        config_cache: dict[str | None, dict[str, Any] | None] = {}
        matrix = self.store.data.get("permissions_matrix", {})

        for user_id, per_dashboard in matrix.items():
            for storage_key, policy in per_dashboard.items():
                views_policy = policy.get("views") or {}
                if not views_policy:
                    continue

                url_path = _from_storage_key(storage_key)
                if url_path not in config_cache:
                    lovelace_config = dashboards.get(url_path)
                    if lovelace_config is None:
                        config_cache[url_path] = None
                    else:
                        try:
                            config_cache[url_path] = await lovelace_config.async_load(False)
                        except (HomeAssistantError, AttributeError, TypeError):
                            _LOGGER.warning(
                                "Could not load dashboard %s for drift check",
                                url_path,
                                exc_info=True,
                            )
                            config_cache[url_path] = None

                config = config_cache[url_path]
                if config is None:
                    continue

                for view_path, expected_visible in views_policy.items():
                    try:
                        view = _find_view(config, view_path)
                    except (AttributeError, TypeError, KeyError):
                        continue
                    if view is None:
                        continue

                    visible = view.get("visible")
                    actual_user_ids = _visible_user_ids(visible)
                    if actual_user_ids is None:
                        actual_visible = True if visible is None else bool(visible)
                    else:
                        actual_visible = user_id in actual_user_ids

                    if actual_visible != bool(expected_visible):
                        mismatches.append(
                            {
                                "url_path": url_path,
                                "view_path": view_path,
                                "user_id": user_id,
                                "expected_visible": bool(expected_visible),
                                "actual_visible": actual_visible,
                            }
                        )

        return mismatches
