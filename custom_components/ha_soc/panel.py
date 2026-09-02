"""Sidebar panel registration — the Alarmo/Browser Mod pattern.

Serves the committed frontend bundle (frontend/dist/ha-soc-panel.js) as a
static path, then registers it as a custom panel. require_admin=True hides
the panel from non-admin sidebars; it is not a substitute for the
admin-only gating already applied to every ha_soc/* websocket command
(panel visibility alone never protects data — see websocket_api.py).
"""
from __future__ import annotations

import hashlib
import logging
import os

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_NAME = "ha-soc-panel"
PANEL_URL = f"/api/panel_custom/{DOMAIN}"
PANEL_TITLE = "SOC"
PANEL_ICON = "mdi:shield-search"
_DATA_STATIC_PATH_REGISTERED = f"{DOMAIN}.panel_static_path_registered"


def _bundle_path() -> str:
    return os.path.join(os.path.dirname(__file__), "frontend", "dist", "ha-soc-panel.js")


def _bundle_cache_token_sync(bundle_path: str) -> str | None:
    """Return a content-derived cache token, or None when the bundle is absent.

    Release archives intentionally use a fixed timestamp for reproducibility,
    so an mtime cannot identify the deployed JavaScript. File I/O runs in the
    executor to avoid blocking Home Assistant's event loop.
    """
    try:
        with open(bundle_path, "rb") as bundle:
            return hashlib.file_digest(bundle, "sha256").hexdigest()[:16]
    except OSError:
        return None


async def async_register_panel(hass: HomeAssistant) -> None:
    bundle_path = _bundle_path()
    cache_token = await hass.async_add_executor_job(
        _bundle_cache_token_sync, bundle_path
    )
    if cache_token is None:
        _LOGGER.warning(
            "HA SOC frontend bundle not found at %s — build frontend/ before "
            "using the panel (see frontend/README.md). Skipping panel registration.",
            bundle_path,
        )
        return

    # aiohttp routes live for the lifetime of the Home Assistant process;
    # async_remove_panel() only removes the frontend/sidebar registration.
    # Consequently an integration reload must not add this GET route again.
    #
    # The RuntimeError recovery also covers the upgrade path from an older HA
    # SOC build: its route can already exist in the current process before this
    # process-local marker is introduced.
    if not hass.data.get(_DATA_STATIC_PATH_REGISTERED):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(PANEL_URL, bundle_path, cache_headers=False)]
            )
        except RuntimeError as err:
            message = str(err)
            if not (
                "Added route will never be executed" in message
                and "method GET is already registered" in message
            ):
                raise
            _LOGGER.debug(
                "HA SOC frontend route %s is already registered; reusing it",
                PANEL_URL,
            )
        hass.data[_DATA_STATIC_PATH_REGISTERED] = True

    # A failed setup can leave the frontend panel registered even though the
    # config entry never reached its normal unload path. Replace our own panel
    # registration deterministically before adding the current cache-busted
    # module URL.
    async_remove_panel(hass, DOMAIN, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_NAME,
        frontend_url_path=DOMAIN,
        module_url=f"{PANEL_URL}?v={cache_token}",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=True,
        config={},
        config_panel_domain=DOMAIN,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    async_remove_panel(hass, DOMAIN, warn_if_unknown=False)
