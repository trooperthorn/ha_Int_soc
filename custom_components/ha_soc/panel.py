"""Sidebar panel registration — the Alarmo/Browser Mod pattern.

Serves the committed frontend bundle (frontend/dist/ha-soc-panel.js) as a
static path, then registers it as a custom panel. require_admin=True hides
the panel from non-admin sidebars; it is not a substitute for the
admin-only gating already applied to every ha_soc/* websocket command
(panel visibility alone never protects data — see websocket_api.py).
"""
from __future__ import annotations

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


def _bundle_path() -> str:
    return os.path.join(os.path.dirname(__file__), "frontend", "dist", "ha-soc-panel.js")


def _bundle_mtime_sync(bundle_path: str) -> float | None:
    """The bundle's mtime, or None if it doesn't exist. Disk I/O — run in
    the executor only (same event-loop rule as integration_security.py's
    custom_components scan; stat-ing a file on the loop stalls everything
    on a slow disk)."""
    try:
        return os.path.getmtime(bundle_path)
    except OSError:
        return None


async def async_register_panel(hass: HomeAssistant) -> None:
    bundle_path = _bundle_path()
    mtime = await hass.async_add_executor_job(_bundle_mtime_sync, bundle_path)
    if mtime is None:
        _LOGGER.warning(
            "HA SOC frontend bundle not found at %s — build frontend/ before "
            "using the panel (see frontend/README.md). Skipping panel registration.",
            bundle_path,
        )
        return

    cache_bust = int(mtime)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL, bundle_path, cache_headers=False)]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_NAME,
        frontend_url_path=DOMAIN,
        module_url=f"{PANEL_URL}?v={cache_bust}",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=True,
        config={},
        config_panel_domain=DOMAIN,
    )


async def async_unregister_panel(hass: HomeAssistant) -> None:
    async_remove_panel(hass, DOMAIN, warn_if_unknown=False)
