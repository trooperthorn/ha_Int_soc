"""Custom WebSocket API — the single surface the frontend panel talks to.

Every command is gated by `@require_soc_access` (admin, plus HA SOC's own
owner-only/owner+admin access_level setting), regardless of whether the
panel itself is registered `require_admin=True` — panel visibility is
cosmetic (see `permissions.py`); the real gate has to be here. The one
exception is `ha_soc/access/info`, which stays on plain
`@websocket_api.require_admin` so an admin currently blocked by
access_level can still ask why.

Above that baseline sit two owner-only tiers. `@require_owner` gates the
commands that can take the platform over or rewrite configuration
outright: Settings, the watchdog/hard-cap configuration, every firewall
command including status (D-4, D-5), `entity_remap/apply`, and
`permissions/sidebar/push` (D-23). Additionally, the four user-management
commands that can cut a user off (`users/deactivate`, `users/delete`,
`users/revoke_token`, `users/revoke_all_sessions`) become owner-only
whenever the TARGET is an admin-group user, resolved server-side from
hass.auth (D-23 option (a)); a non-owner admin keeps them for non-admin
targets, so the admins tier still means routine user management.

Command namespace is `ha_soc/*`. Mutating/PII-bearing commands never return
raw refresh-token secrets or JWT material to the frontend — only metadata
(ids, timestamps, client names).

HA SOC's own actions are in its own audit chain (work item 1.4, decision
D-14 option (a)): every mutating command here writes an audit record, and
the three privileged READS (host/Supervisor/add-on container logs, the
crash log, and a user's detail including their token list) write a
`privileged_read` record naming the target. Ordinary list/summary reads
are deliberately not audited (D-14 rejected option (b)); logging every
panel refresh would bury the records that matter.
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    CONF_ACCESS_LEVEL,
    CONF_AUDIT_MAX_BYTES,
    CONF_AUDIT_RETENTION_DAYS,
    CONF_MFA_GRACE_PERIOD_DAYS,
    CONF_MFA_POLICY,
    CONF_GITHUB_TOKEN,
    CONF_NVD_API_KEY,
    CONF_RISK_LEARNING_PERIOD_DAYS,
    CONF_SCANNER_ENABLED,
    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
    CONF_SECURITY_SOURCES_ENABLED,
    CONF_UNIFI_NETWORK_API_KEY,
    CONF_UNIFI_NETWORK_HOST,
    CONF_UNIFI_NETWORK_VERIFY_SSL,
    CONF_UNIFI_PROTECT_API_KEY,
    CONF_UNIFI_PROTECT_HOST,
    CONF_UNIFI_PROTECT_VERIFY_SSL,
    DEFAULT_ACCESS_LEVEL,
    DOMAIN,
    MFA_POLICY_AUDIT_ONLY,
    MFA_POLICY_AUTO_DEACTIVATE,
    REDACTED_PLACEHOLDER,
    SECRET_SETTING_KEYS,
    SEVERITY_ORDER,
    SIGNAL_UPDATE,
    WATCHDOG_ACTIONS,
)
from .resource_watchdog import ADDON_SLUG_PATTERN

_LOGGER = logging.getLogger(__name__)


def _runtime(hass: HomeAssistant):
    # Local import to avoid a circular import with __init__.py at module load time.
    from . import get_runtime_data

    return get_runtime_data(hass)


def require_soc_access(func):
    """Admin-gate every ha_soc/* command, then apply HA SOC's own access_level.

    Modeled directly on websocket_api.require_admin (same signature, same
    "raise Unauthorized, don't call func" shape) so it composes with
    @websocket_command/@async_response exactly the way require_admin does.
    On top of the baseline admin check, a non-owner admin is only let
    through when the setting is explicitly opened up to
    ACCESS_LEVEL_OWNER_AND_ADMINS — a security-posture tool is itself a
    high-value target, so it defaults to owner-only and fails closed if the
    runtime (and therefore the setting) isn't reachable yet.
    """

    @wraps(func)
    def with_soc_access(hass: HomeAssistant, connection, msg: dict) -> None:
        user = connection.user
        if user is None or not user.is_admin:
            raise Unauthorized
        if not user.is_owner:
            try:
                access_level = _runtime(hass).store.settings.get(
                    "access_level", DEFAULT_ACCESS_LEVEL
                )
            except RuntimeError:
                access_level = DEFAULT_ACCESS_LEVEL
            if access_level != ACCESS_LEVEL_OWNER_AND_ADMINS:
                raise Unauthorized
        func(hass, connection, msg)

    return with_soc_access


def require_owner(func):
    """Owner-only gate — stricter than require_soc_access, ignoring access_level.

    A non-owner admin is refused here even under owner_and_admins. What
    carries this gate, and why (decisions D-4, D-5, D-23):

    - Settings: they hold the security-sensitive controls, including the
      access level itself and the API credentials.
    - Every firewall command, status included (D-4): a firewall change can
      end with the platform unreachable, and reading the ruleset maps the
      attack surface, so no account but the owner may even look.
    - The watchdog/hard-cap configuration: enforcement controls that
      restart add-ons and change host containers.
    - entity_remap/apply and permissions/sidebar/push (D-23): both rewrite
      configuration or per-user policy, the same takeover surface D-4
      closes for the firewall.

    Commands that act on a TARGET user apply a second, conditional owner
    gate inside their handlers instead (see _async_target_is_admin), so
    admins keep routine management of non-admin users.
    """

    @wraps(func)
    def with_owner(hass: HomeAssistant, connection, msg: dict) -> None:
        user = connection.user
        if user is None or not user.is_owner:
            raise Unauthorized
        func(hass, connection, msg)

    return with_owner


async def _async_target_is_admin(hass: HomeAssistant, user_id: str) -> bool:
    """True when the TARGET of a user-management command is the owner or a
    member of the admin group, resolved server-side from hass.auth.

    Decision D-23 option (a): deactivating, deleting, or revoking the
    sessions or tokens of an admin-group user is owner-only, because an
    admin who can cut off other admins (or the owner) through HA SOC can
    take the platform over; admins keep those commands for non-admin
    targets. The check never trusts anything the client sent beyond the
    user id, and it looks at group membership directly rather than
    User.is_admin because is_admin is False for a DEACTIVATED admin-group
    user, and a deactivated admin is still exactly the kind of account
    this gate protects (deleting one, or clearing its tokens, stays an
    owner call). An unknown user id returns False so the command's own
    not-found handling answers, which discloses nothing beyond the id's
    absence.
    """
    from homeassistant.auth.const import GROUP_ID_ADMIN

    target = await hass.auth.async_get_user(user_id)
    if target is None:
        return False
    return bool(
        target.is_owner or any(group.id == GROUP_ID_ADMIN for group in target.groups)
    )


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register every ha_soc/* command. Safe to call once per HA process."""
    for handler in (
        ws_access_info,
        ws_version_get,
        ws_users_list,
        ws_users_detail,
        ws_users_create,
        ws_users_update,
        ws_users_deactivate,
        ws_users_delete,
        ws_users_revoke_token,
        ws_users_revoke_all_sessions,
        ws_users_set_password,
        ws_sessions_connect,
        ws_sessions_list,
        ws_audit_query,
        ws_audit_verify_chain,
        ws_permissions_dashboards_list,
        ws_permissions_dashboard_config,
        ws_permissions_view_visibility_set,
        ws_permissions_dashboard_flags_set,
        ws_permissions_sidebar_push,
        ws_permissions_drift_check,
        ws_risk_list,
        ws_risk_posture,
        ws_detections_list,
        ws_detections_set_status,
        ws_vulns_list,
        ws_vulns_scan_now,
        ws_vulns_set_status,
        ws_scanner_list,
        ws_scanner_scan_now,
        ws_scanner_export,
        ws_health_list,
        ws_logs_fault,
        ws_logs_targets,
        ws_logs_container,
        ws_misconfig_set_status,
        ws_dashboard_summary,
        ws_dashboard_devices,
        ws_dashboard_integrations,
        ws_probe_status,
        ws_peripherals_list,
        ws_peripherals_set_ignored,
        ws_entity_remap_find_references,
        ws_entity_remap_apply,
        ws_entity_remap_broken_references,
        ws_security_health_list,
        ws_firewall_status,
        ws_firewall_test,
        ws_firewall_confirm,
        ws_firewall_cancel,
        ws_firewall_discard_pending,
        ws_firewall_reset_pairing,
        ws_integration_security_list,
        ws_integration_security_refresh,
        ws_containers_resources,
        ws_watchdog_status,
        ws_watchdog_set,
        ws_network_overview,
        ws_settings_get,
        ws_settings_set,
        ws_subscribe,
    ):
        websocket_api.async_register_command(hass, handler)


# ----------------------------------------------------------------------------
# Access control
# ----------------------------------------------------------------------------


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/access/info"})
@websocket_api.async_response
async def ws_access_info(hass: HomeAssistant, connection, msg: dict) -> None:
    """Tell the frontend (and a blocked admin) exactly where it stands.

    Deliberately stays on plain @websocket_api.require_admin rather than
    @require_soc_access — an admin who's been locked out by access_level
    still needs a way to find out why, instead of every command in the
    panel just silently 401ing with no explanation.
    """
    runtime = _runtime(hass)
    user = connection.user
    access_level = runtime.store.settings.get("access_level", DEFAULT_ACCESS_LEVEL)
    allowed = bool(user.is_owner or access_level == ACCESS_LEVEL_OWNER_AND_ADMINS)
    connection.send_result(
        msg["id"],
        {
            "is_owner": bool(user.is_owner),
            "access_level": access_level,
            "allowed": allowed,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/version/get"})
@websocket_api.async_response
async def ws_version_get(hass: HomeAssistant, connection, msg: dict) -> None:
    """The version shown in the panel's footer, on every tab.

    Reads manifest.json (the single source of truth HA itself already
    uses for update-checking) via the loader, rather than duplicating the
    version as a second hardcoded string somewhere in this file — exactly
    the kind of two-places-to-update drift the probe add-on's run.sh
    SCANNER_VERSION constant already has to be manually kept in lockstep
    for. Plain @websocket_api.require_admin, same as ha_soc/access/info:
    a version number isn't sensitive, and an admin locked out by
    access_level should still see it on the denied screen, not just once
    they're let in.
    """
    from homeassistant.loader import async_get_integration

    integration = await async_get_integration(hass, DOMAIN)
    connection.send_result(
        msg["id"], {"version": str(integration.version) if integration.version else None}
    )


# ----------------------------------------------------------------------------
# Users & Access
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/users/list"})
@websocket_api.async_response
async def ws_users_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"users": await runtime.users.async_list_users()})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/users/detail", vol.Required("user_id"): str}
)
@websocket_api.async_response
async def ws_users_detail(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # Privileged read (work item 1.4, D-14): the detail includes the target
    # user's refresh-token list. The ATTEMPT is what gets audited, before
    # the fetch, so a probe for a nonexistent user id still leaves a
    # record; a not_found answer discloses nothing beyond the id's absence.
    runtime.audit.async_log(
        "privileged_read",
        user_id=connection.user.id,
        detail={"target": msg["user_id"], "read": "user_detail"},
    )
    detail = await runtime.users.async_get_user_detail(msg["user_id"])
    if detail is None:
        connection.send_error(msg["id"], "not_found", "User not found")
        return
    connection.send_result(msg["id"], detail)


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/users/create",
        vol.Required("name"): str,
        vol.Optional("group_ids"): [str],
        vol.Optional("local_only"): bool,
    }
)
@websocket_api.async_response
async def ws_users_create(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    record = await runtime.users.async_create_user(
        msg["name"], group_ids=msg.get("group_ids"), local_only=msg.get("local_only")
    )
    runtime.audit.async_log(
        "user_added", user_id=connection.user.id, detail={"created_name": msg["name"]}
    )
    connection.send_result(msg["id"], record)


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/users/update",
        vol.Required("user_id"): str,
        vol.Optional("name"): str,
        vol.Optional("is_active"): bool,
        vol.Optional("group_ids"): [str],
        vol.Optional("local_only"): bool,
    }
)
@websocket_api.async_response
async def ws_users_update(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    changes = {
        k: v
        for k, v in msg.items()
        if k in ("name", "is_active", "group_ids", "local_only")
    }
    ok = await runtime.users.async_update_user(msg["user_id"], **changes)
    if not ok:
        connection.send_error(msg["id"], "update_failed", "Could not update this user")
        return
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "changes": changes},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/users/deactivate", vol.Required("user_id"): str}
)
@websocket_api.async_response
async def ws_users_deactivate(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # D-23: deactivating an admin-group user is owner-only; a non-owner
    # admin keeps this command for non-admin targets.
    if not connection.user.is_owner and await _async_target_is_admin(hass, msg["user_id"]):
        raise Unauthorized
    ok, reason = await runtime.users.async_deactivate_user(msg["user_id"])
    if not ok:
        connection.send_error(msg["id"], reason or "deactivate_failed", "Could not deactivate user")
        return
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "deactivated"},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/users/delete", vol.Required("user_id"): str}
)
@websocket_api.async_response
async def ws_users_delete(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # D-23: deleting an admin-group user is owner-only.
    if not connection.user.is_owner and await _async_target_is_admin(hass, msg["user_id"]):
        raise Unauthorized
    ok, reason = await runtime.users.async_delete_user(
        msg["user_id"], requesting_user_id=connection.user.id
    )
    if not ok:
        connection.send_error(msg["id"], reason or "delete_failed", "Could not delete user")
        return
    runtime.store.async_purge_user(msg["user_id"])
    runtime.audit.async_log(
        "user_removed",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/users/revoke_token",
        vol.Required("user_id"): str,
        vol.Required("token_id"): str,
    }
)
@websocket_api.async_response
async def ws_users_revoke_token(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # D-23: revoking an admin-group user's token is owner-only; cutting an
    # admin's session or automation token off is a takeover primitive.
    if not connection.user.is_owner and await _async_target_is_admin(hass, msg["user_id"]):
        raise Unauthorized
    ok = await runtime.users.async_revoke_token(msg["user_id"], msg["token_id"])
    if not ok:
        connection.send_error(msg["id"], "not_found", "Token not found for this user")
        return
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "revoked_token", "token_id": msg["token_id"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/users/revoke_all_sessions", vol.Required("user_id"): str}
)
@websocket_api.async_response
async def ws_users_revoke_all_sessions(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # D-23: revoking an admin-group user's sessions wholesale is owner-only.
    if not connection.user.is_owner and await _async_target_is_admin(hass, msg["user_id"]):
        raise Unauthorized
    revoked = await runtime.users.async_revoke_all_sessions(msg["user_id"])
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "revoked_all_sessions", "revoked": revoked},
    )
    # revoked = {"sessions": N, "long_lived_tokens": M} so the UI can state
    # exactly what was cleared, including the long-lived tokens.
    connection.send_result(msg["id"], {"revoked": revoked})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/users/set_password",
        vol.Required("user_id"): str,
        vol.Required("password"): str,
    }
)
@websocket_api.async_response
async def ws_users_set_password(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    ok, reason = await runtime.users.async_set_password(
        msg["user_id"], msg["password"], requesting_user_is_owner=bool(connection.user.is_owner)
    )
    if not ok:
        connection.send_error(
            msg["id"],
            reason or "set_password_failed",
            "Only the account owner can reset another user's password"
            if reason == "owner_required"
            else "Could not set password",
        )
        return
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "password_reset"},
    )
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Live sessions (Browser-Mod style handshake)
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/sessions/connect"})
@websocket_api.async_response
async def ws_sessions_connect(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    key = runtime.live_sessions.add(connection)

    @callback
    def _on_close() -> None:
        runtime.live_sessions.remove(key)

    connection.subscriptions[msg["id"]] = _on_close
    connection.send_result(msg["id"], {"session_key": key})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/sessions/list"})
@websocket_api.async_response
async def ws_sessions_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"sessions": runtime.live_sessions.list_sessions()})


# ----------------------------------------------------------------------------
# Audit log
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/audit/query",
        vol.Optional("since"): str,
        vol.Optional("until"): str,
        vol.Optional("user_id"): str,
        vol.Optional("category"): str,
        vol.Optional("ip"): str,
        vol.Optional("limit", default=200): int,
    }
)
@websocket_api.async_response
async def ws_audit_query(hass: HomeAssistant, connection, msg: dict) -> None:
    from homeassistant.util import dt as dt_util

    runtime = _runtime(hass)
    since = dt_util.parse_datetime(msg["since"]) if msg.get("since") else None
    until = dt_util.parse_datetime(msg["until"]) if msg.get("until") else None
    records = await runtime.audit.async_query(
        since=since,
        until=until,
        user_id=msg.get("user_id"),
        category=msg.get("category"),
        ip=msg.get("ip"),
        limit=msg.get("limit", 200),
    )
    connection.send_result(msg["id"], {"events": records})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/audit/verify_chain"})
@websocket_api.async_response
async def ws_audit_verify_chain(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], await runtime.audit.async_verify_chain())


# ----------------------------------------------------------------------------
# Permissions matrix
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/permissions/dashboards/list"})
@websocket_api.async_response
async def ws_permissions_dashboards_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(
        msg["id"], {"dashboards": await runtime.permissions.async_list_dashboards()}
    )


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/permissions/dashboard_config", vol.Optional("url_path"): vol.Any(None, str)}
)
@websocket_api.async_response
async def ws_permissions_dashboard_config(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    config = await runtime.permissions.async_get_dashboard_config(msg.get("url_path"))
    if config is None:
        connection.send_error(msg["id"], "not_found", "Dashboard not found")
        return
    connection.send_result(msg["id"], {"config": config})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/permissions/view_visibility/set",
        vol.Optional("url_path"): vol.Any(None, str),
        vol.Required("view_path"): str,
        vol.Required("user_ids"): [str],
    }
)
@websocket_api.async_response
async def ws_permissions_view_visibility_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    ok, reason = await runtime.permissions.async_set_view_visibility(
        msg.get("url_path"), msg["view_path"], msg["user_ids"]
    )
    if not ok:
        connection.send_error(msg["id"], reason or "set_failed", "Could not update view visibility")
        return
    runtime.audit.async_log(
        "lovelace_change",
        user_id=connection.user.id,
        detail={"url_path": msg.get("url_path"), "view_path": msg["view_path"], "user_ids": msg["user_ids"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/permissions/dashboard_flags/set",
        vol.Required("dashboard_id"): str,
        vol.Optional("require_admin"): bool,
        vol.Optional("show_in_sidebar"): bool,
    }
)
@websocket_api.async_response
async def ws_permissions_dashboard_flags_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    ok, reason = await runtime.permissions.async_set_dashboard_flags(
        msg["dashboard_id"],
        require_admin=msg.get("require_admin"),
        show_in_sidebar=msg.get("show_in_sidebar"),
    )
    if not ok:
        connection.send_error(msg["id"], reason or "set_failed", "Could not update dashboard flags")
        return
    # Work item 1.4: only the flags actually present in the message are
    # recorded, so the record says what changed, not what happened to be
    # omitted.
    runtime.audit.async_log(
        "lovelace_change",
        user_id=connection.user.id,
        detail={
            "action": "dashboard_flags_set",
            "dashboard_id": msg["dashboard_id"],
            "flags": {
                key: msg[key]
                for key in ("require_admin", "show_in_sidebar")
                if key in msg
            },
        },
    )
    connection.send_result(msg["id"], {"ok": True})


# Owner-only (D-23): this rewrites another user's stored sidebar policy,
# and configuration/policy rewrites carry the same takeover reasoning D-4
# applied to the firewall. Non-owner admins get the standard unauthorized
# error; the command's existing lovelace_change audit record is unchanged.
@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/permissions/sidebar/push",
        vol.Required("user_id"): str,
        vol.Required("hidden_dashboard_paths"): [str],
    }
)
@websocket_api.async_response
async def ws_permissions_sidebar_push(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    ok, reason = await runtime.permissions.async_push_sidebar_policy(
        msg["user_id"], msg["hidden_dashboard_paths"]
    )
    if not ok:
        connection.send_error(msg["id"], reason or "push_failed", "Could not update sidebar for that user")
        return
    # Work item 1.4: this is a per-user visibility change (cosmetic, per
    # permissions.py's labeling, but still an admin acting on another
    # user), so the record carries the target user and the full hidden set.
    runtime.audit.async_log(
        "lovelace_change",
        user_id=connection.user.id,
        detail={
            "action": "sidebar_push",
            "target_user_id": msg["user_id"],
            "hidden_dashboard_paths": msg["hidden_dashboard_paths"],
        },
    )
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/permissions/drift/check"})
@websocket_api.async_response
async def ws_permissions_drift_check(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"drift": await runtime.permissions.async_check_drift()})


# ----------------------------------------------------------------------------
# Risk & posture
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/risk/list"})
@websocket_api.async_response
async def ws_risk_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    results = runtime.risk.last_risk_results or await runtime.risk.async_recompute_all()
    connection.send_result(msg["id"], {"risk": results})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/risk/posture"})
@websocket_api.async_response
async def ws_risk_posture(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    posture = runtime.risk.last_posture_result or await runtime.risk.async_compute_posture()
    connection.send_result(msg["id"], posture)


# ----------------------------------------------------------------------------
# Detections
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/detections/list", vol.Optional("status"): str, vol.Optional("limit", default=200): int}
)
@websocket_api.async_response
async def ws_detections_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    detections = list(runtime.store.data["detections"].values())
    if msg.get("status"):
        detections = [d for d in detections if d.get("status") == msg["status"]]
    detections.sort(key=lambda d: d.get("last_seen", d.get("ts", "")), reverse=True)
    connection.send_result(msg["id"], {"detections": detections[: msg.get("limit", 200)]})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/detections/set_status",
        vol.Required("detection_id"): str,
        vol.Required("status"): vol.In(["open", "ack", "resolved"]),
    }
)
@websocket_api.async_response
async def ws_detections_set_status(hass: HomeAssistant, connection, msg: dict) -> None:
    from homeassistant.util import dt as dt_util

    runtime = _runtime(hass)
    # The store records status_by/status_at/previous_status on the
    # detection itself and hands the record back so the audit entry can
    # carry the rule id and the transition (work item 1.4). An unknown id
    # is an error now, not a silent {"ok": True}: nothing changed, so
    # claiming success would be false and auditing it would be fiction.
    detection = runtime.store.async_set_detection_status(
        msg["detection_id"],
        msg["status"],
        by_user_id=connection.user.id,
        at=dt_util.utcnow().isoformat(),
    )
    if detection is None:
        connection.send_error(msg["id"], "not_found", "Detection not found")
        return
    runtime.audit.async_log(
        "detection_status_changed",
        user_id=connection.user.id,
        detail={
            "detection_id": msg["detection_id"],
            "rule_id": detection.get("rule_id"),
            "old_status": detection.get("previous_status"),
            "new_status": msg["status"],
        },
    )
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Device vulnerabilities
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/vulns/list"})
@websocket_api.async_response
async def ws_vulns_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"findings": list(runtime.store.data["vuln_findings"].values())})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/vulns/scan_now"})
@websocket_api.async_response
async def ws_vulns_scan_now(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    # The tracker fetches the NVD API key from the secret store right
    # before each request (SEC-3); no key is handled here.
    findings = await runtime.vulns.async_run_scan()
    connection.send_result(msg["id"], {"findings": findings})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/vulns/set_status",
        vol.Required("finding_id"): str,
        vol.Required("status"): vol.In(["new", "confirmed", "dismissed", "resolved"]),
        vol.Optional("note"): str,
    }
)
@websocket_api.async_response
async def ws_vulns_set_status(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    await runtime.vulns.async_set_status(
        msg["finding_id"], msg["status"], user_id=connection.user.id, note=msg.get("note")
    )
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Integration security scanner
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/scanner/list"})
@websocket_api.async_response
async def ws_scanner_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"findings": list(runtime.store.data["scanner_findings"].values())})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/scanner/scan_now", vol.Optional("domain"): str}
)
@websocket_api.async_response
async def ws_scanner_scan_now(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    if msg.get("domain"):
        findings = await runtime.scanner.async_scan_integration(msg["domain"])
        connection.send_result(msg["id"], {"findings": findings})
    else:
        results = await runtime.scanner.async_scan_all()
        connection.send_result(msg["id"], {"results": results})


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/scanner/export", vol.Required("finding_id"): str}
)
@websocket_api.async_response
async def ws_scanner_export(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    finding = runtime.store.data["scanner_findings"].get(msg["finding_id"])
    if finding is None:
        connection.send_error(msg["id"], "not_found", "Finding not found")
        return
    connection.send_result(msg["id"], runtime.scanner.export_ghsa(finding))


# ----------------------------------------------------------------------------
# Integration health & misconfiguration
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/health/list"})
@websocket_api.async_response
async def ws_health_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    findings = list(runtime.store.data["misconfig_findings"].values())
    # Most severe first — SEVERITY_ORDER is critical/high/medium/low/info, so a
    # finding whose severity isn't in that list (shouldn't happen, but never
    # trust stored data blindly) sorts last rather than raising.
    findings.sort(
        key=lambda f: SEVERITY_ORDER.index(f["severity"]) if f["severity"] in SEVERITY_ORDER else len(SEVERITY_ORDER)
    )
    connection.send_result(
        msg["id"],
        {
            "integrations": list(runtime.store.data["integration_health"].values()),
            "misconfig_findings": findings,
        },
    )


# ----------------------------------------------------------------------------
# Logs
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/logs/fault"})
@websocket_api.async_response
async def ws_logs_fault(hass: HomeAssistant, connection, msg: dict) -> None:
    from .logs import async_fault_log_overview

    # Privileged read (work item 1.4, D-14): the crash/fault log is Core's
    # own post-mortem dump and can carry anything that was in scope when a
    # thread died. The attempt is audited even when the file turns out not
    # to exist.
    runtime = _runtime(hass)
    runtime.audit.async_log(
        "privileged_read",
        user_id=connection.user.id,
        detail={"target": "core", "read": "fault_log"},
    )
    connection.send_result(msg["id"], await async_fault_log_overview(hass))


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/logs/targets"})
@websocket_api.async_response
async def ws_logs_targets(hass: HomeAssistant, connection, msg: dict) -> None:
    """Log sources the Logs tab can offer besides the integration log:
    Core, Supervisor, host journal, and every installed add-on."""
    from .logs import async_container_log_targets

    connection.send_result(msg["id"], await async_container_log_targets(hass))


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/logs/container",
        vol.Required("target"): str,
    }
)
@websocket_api.async_response
async def ws_logs_container(hass: HomeAssistant, connection, msg: dict) -> None:
    """Current log text of one container. The target string is validated in
    logs.py against the Supervisor's own add-on list, never interpolated raw."""
    from .logs import async_fetch_container_log

    # Privileged read (work item 1.4, D-14): host, Supervisor, Core, and
    # add-on logs routinely carry material their own UIs gate behind admin.
    # The audited target is the plain slug for an add-on ("addon:" prefix
    # stripped) or core/supervisor/host, and the attempt is audited before
    # the fetch so a failed or rejected fetch still leaves a record.
    runtime = _runtime(hass)
    runtime.audit.async_log(
        "privileged_read",
        user_id=connection.user.id,
        detail={
            "target": msg["target"].removeprefix("addon:"),
            "read": "container_log",
        },
    )
    connection.send_result(msg["id"], await async_fetch_container_log(hass, msg["target"]))


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/misconfig/set_status",
        vol.Required("finding_id"): str,
        vol.Required("status"): vol.In(["new", "confirmed", "dismissed", "resolved"]),
        vol.Optional("note"): str,
    }
)
@websocket_api.async_response
async def ws_misconfig_set_status(hass: HomeAssistant, connection, msg: dict) -> None:
    from homeassistant.util import dt as dt_util

    runtime = _runtime(hass)
    runtime.store.async_set_finding_status(
        "misconfig_findings",
        msg["finding_id"],
        msg["status"],
        by_user_id=connection.user.id,
        note=msg.get("note"),
        at=dt_util.utcnow().isoformat(),
    )
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Dashboard summary (one round trip for the SOC Dashboard view's KPI row)
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/dashboard/summary"})
@websocket_api.async_response
async def ws_dashboard_summary(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    posture = runtime.risk.last_posture_result or await runtime.risk.async_compute_posture()
    risk_results = runtime.risk.last_risk_results or await runtime.risk.async_recompute_all()
    users = await runtime.users.async_list_users()
    detections = list(runtime.store.data["detections"].values())
    open_detections = [d for d in detections if d.get("status") == "open"]
    users_at_risk = [r for r in risk_results.values() if r.get("score", 0) >= 60]
    vulns = [
        f for f in runtime.store.data["vuln_findings"].values() if f.get("status") != "dismissed"
    ]
    high_crit_vulns = [f for f in vulns if (f.get("cvss") or 0) >= 7.0]
    active_users = [u for u in users if u.get("is_active")]

    from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

    all_states = hass.states.async_all()
    unavailable_count = sum(1 for s in all_states if s.state == STATE_UNAVAILABLE)
    unknown_count = sum(1 for s in all_states if s.state == STATE_UNKNOWN)

    connection.send_result(
        msg["id"],
        {
            "posture": posture,
            "posture_history": runtime.store.data["posture_history"][-30:],
            "open_detections_count": len(open_detections),
            "users_at_risk_count": len(users_at_risk),
            "total_users_count": len(risk_results),
            "critical_high_vuln_count": len(high_crit_vulns),
            "entity_state_counts": {
                "unavailable": unavailable_count,
                "unknown": unknown_count,
                "total": len(all_states),
            },
            "risk_band_counts": {
                band: len([r for r in risk_results.values() if r.get("band") == band])
                for band in ("low", "moderate", "high", "critical")
            },
            "mfa_counts": {
                "enabled": len([u for u in active_users if u.get("mfa_enabled")]),
                "disabled": len([u for u in active_users if not u.get("mfa_enabled")]),
            },
            "detection_severity_counts": {
                severity: len([d for d in detections if d.get("severity") == severity])
                for severity in ("critical", "high", "medium", "low", "info")
            },
        },
    )


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/dashboard/devices"})
@websocket_api.async_response
async def ws_dashboard_devices(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    overview = await runtime.vulns.async_device_overview()

    scored_devices = [d for d in overview["devices"] if d["total_findings"] > 0]
    combined_risk_score = (
        round(sum(d["risk_score"] for d in scored_devices) / len(scored_devices), 1)
        if scored_devices
        else 0.0
    )

    connection.send_result(
        msg["id"],
        {
            "devices": overview["devices"],
            "status_counts": overview["status_counts"],
            "by_vendor": overview["by_vendor"],
            "combined_risk_score": combined_risk_score,
        },
    )


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/dashboard/integrations"})
@websocket_api.async_response
async def ws_dashboard_integrations(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    overview = await runtime.health.async_integration_overview()
    connection.send_result(msg["id"], overview)


# ----------------------------------------------------------------------------
# Host Probe (optional add-on)
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/probe/status"})
@websocket_api.async_response
async def ws_probe_status(hass: HomeAssistant, connection, msg: dict) -> None:
    from .probe import async_probe_overview

    runtime = _runtime(hass)
    overview = await async_probe_overview(hass, runtime.store)
    connection.send_result(msg["id"], overview)


# ----------------------------------------------------------------------------
# Local Peripherals (USB/serial devices)
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/peripherals/list"})
@websocket_api.async_response
async def ws_peripherals_list(hass: HomeAssistant, connection, msg: dict) -> None:
    from .peripherals import async_peripheral_overview

    runtime = _runtime(hass)
    overview = await async_peripheral_overview(hass, runtime.store)
    connection.send_result(msg["id"], overview)


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/peripherals/set_ignored",
        vol.Required("key"): str,
        vol.Required("ignored"): bool,
        vol.Optional("raw_name", default=""): str,
    }
)
@websocket_api.async_response
async def ws_peripherals_set_ignored(hass: HomeAssistant, connection, msg: dict) -> None:
    from .peripherals import async_set_peripheral_ignored

    runtime = _runtime(hass)
    async_set_peripheral_ignored(
        runtime.store, msg["key"], msg["ignored"], by_user_id=connection.user.id, raw_name=msg["raw_name"]
    )
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Entity ReMap — find and fix broken/stale entity_id references across
# automations, scripts, scenes, dashboards, and helpers. See entity_remap.py
# for exactly what's editable vs. detect-only and why.
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/entity_remap/find_references", vol.Required("entity_id"): str}
)
@websocket_api.async_response
async def ws_entity_remap_find_references(hass: HomeAssistant, connection, msg: dict) -> None:
    from .entity_remap import async_find_references

    report = await async_find_references(hass, msg["entity_id"])
    connection.send_result(msg["id"], report)


# Owner-only (D-23): applying a remap rewrites YAML configuration files,
# stored dashboards, and helper entries, and a configuration rewrite is the
# same takeover surface D-4 closed for the firewall. Finding references
# stays open to admins; only the write is gated.
@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/entity_remap/apply",
        # cv.entity_id enforces the domain.object_id shape, so a typo'd or
        # empty string can't be substituted into an entity_id field and
        # silently break the automation/script on next reload.
        vol.Required("old_entity_id"): cv.entity_id,
        vol.Required("new_entity_id"): cv.entity_id,
        vol.Required("backup_acknowledged"): bool,
    }
)
@websocket_api.async_response
async def ws_entity_remap_apply(hass: HomeAssistant, connection, msg: dict) -> None:
    from .entity_remap import async_apply_remap

    runtime = _runtime(hass)
    old_id, new_id = msg["old_entity_id"], msg["new_entity_id"]
    if old_id == new_id:
        connection.send_error(msg["id"], "same_entity", "Old and replacement entity are the same.")
        return

    result = await async_apply_remap(
        hass, old_id, new_id, backup_acknowledged=msg["backup_acknowledged"]
    )
    if result.get("error") == "backup_not_acknowledged":
        connection.send_error(
            msg["id"],
            "backup_not_acknowledged",
            "Acknowledge the backup before applying an entity remap.",
        )
        return
    runtime.audit.async_log(
        "soc_config_change",
        user_id=connection.user.id,
        detail={"action": "entity_remap_applied", **result},
    )
    connection.send_result(msg["id"], result)


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/entity_remap/broken_references"})
@websocket_api.async_response
async def ws_entity_remap_broken_references(hass: HomeAssistant, connection, msg: dict) -> None:
    from .entity_remap import async_scan_broken_references

    broken = await async_scan_broken_references(hass)
    connection.send_result(msg["id"], {"broken": broken})


# ----------------------------------------------------------------------------
# Security Integrations Health — always-present Dashboard card. See
# security_health.py for exactly what "problem"/"low battery" mean and why.
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/security_health/list"})
@websocket_api.async_response
async def ws_security_health_list(hass: HomeAssistant, connection, msg: dict) -> None:
    from .security_health import async_security_overview

    runtime = _runtime(hass)
    overview = await async_security_overview(hass, runtime.store)
    connection.send_result(msg["id"], overview)


# ----------------------------------------------------------------------------
# Firewall rules — read AND write host iptables state via the optional
# HA SOC Probe add-on's NET_ADMIN capability. See firewall.py's module
# docstring for the full test/confirm/revert safety design; every mutating
# command here is audit-logged since this is the one control in the project
# that actually changes a host security setting rather than just reporting
# on one.
#
# The ENTIRE feature is owner-only, status included (decision D-4),
# regardless of access_level: a firewall change can end with the platform
# unreachable and is therefore a takeover primitive, and even the read-only
# status maps the attack surface. The panel hides the card from non-owner
# admins for the same reason; this gate is the one that actually enforces
# it.
# ----------------------------------------------------------------------------


@require_owner
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/firewall/status"})
@websocket_api.async_response
async def ws_firewall_status(hass: HomeAssistant, connection, msg: dict) -> None:
    from .firewall import async_get_status

    runtime = _runtime(hass)
    connection.send_result(msg["id"], await async_get_status(hass, runtime.store))


@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/firewall/test",
        vol.Required("rules"): [dict],
        vol.Required("backup_acknowledged"): bool,
    }
)
@websocket_api.async_response
async def ws_firewall_test(hass: HomeAssistant, connection, msg: dict) -> None:
    from .firewall import async_propose_test

    runtime = _runtime(hass)
    ok, reason, pending = await async_propose_test(
        hass,
        runtime.store,
        rules=msg["rules"],
        backup_acknowledged=msg["backup_acknowledged"],
        user_id=connection.user.id,
    )
    if not ok:
        connection.send_error(msg["id"], "firewall_test_rejected", reason)
        return

    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={
            "action": "firewall_test_proposed",
            "test_id": pending["test_id"],
            "rules": pending["proposed_rules"],
        },
    )
    connection.send_result(msg["id"], pending)


@require_owner
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/firewall/confirm", vol.Required("test_id"): str}
)
@websocket_api.async_response
async def ws_firewall_confirm(hass: HomeAssistant, connection, msg: dict) -> None:
    from .firewall import async_confirm_test

    runtime = _runtime(hass)
    ok, reason = await async_confirm_test(
        hass, runtime.store, test_id=msg["test_id"], user_id=connection.user.id
    )
    if not ok:
        connection.send_error(msg["id"], "firewall_confirm_rejected", reason)
        return

    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"action": "firewall_test_confirmed", "test_id": msg["test_id"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_owner
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/firewall/reset_pairing"})
@websocket_api.async_response
async def ws_firewall_reset_pairing(hass: HomeAssistant, connection, msg: dict) -> None:
    """Owner-only recovery: clear the pinned add-on secret so the next
    non-empty one re-pins (trust-on-first-use). Use if the add-on was
    reinstalled/rotated its secret, or a bad first-boot pin locked out the
    real add-on.
    """
    from .firewall import async_reset_addon_secret

    runtime = _runtime(hass)
    await async_reset_addon_secret(runtime.secrets)
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"action": "firewall_pairing_reset"},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_owner
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/firewall/cancel", vol.Required("test_id"): str}
)
@websocket_api.async_response
async def ws_firewall_cancel(hass: HomeAssistant, connection, msg: dict) -> None:
    from .firewall import async_cancel_test

    runtime = _runtime(hass)
    ok, reason = await async_cancel_test(
        hass, runtime.store, test_id=msg["test_id"], user_id=connection.user.id
    )
    if not ok:
        connection.send_error(msg["id"], "firewall_cancel_rejected", reason)
        return

    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"action": "firewall_test_cancelled", "test_id": msg["test_id"]},
    )
    connection.send_result(msg["id"], {"ok": True})


@require_owner
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/firewall/discard_pending"})
@websocket_api.async_response
async def ws_firewall_discard_pending(hass: HomeAssistant, connection, msg: dict) -> None:
    """Owner-only escape hatch (decision D-5): archive a pending test whose
    report will never arrive because the add-on went silent mid-test. The
    server refuses the discard while the countdown is still running
    (window_not_lapsed) so it can never race a report that is merely late;
    the panel offers the button under the same condition. The archive and
    the firewall_pending_discarded audit record (flushed immediately) are
    written by firewall.async_discard_pending so the state machine stays
    the single owner of the pending slot.
    """
    from .firewall import async_discard_pending

    runtime = _runtime(hass)
    ok, reason = await async_discard_pending(
        hass, runtime.store, user_id=connection.user.id
    )
    if not ok:
        connection.send_error(msg["id"], "firewall_discard_rejected", reason)
        return
    connection.send_result(msg["id"], {"ok": True})


# ----------------------------------------------------------------------------
# Integration Security — provenance (NOT safety) view of every installed
# integration. See integration_security.py's docstring for the rule that
# governs it: nothing here proves code is safe to run.
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/integration_security/list"})
@websocket_api.async_response
async def ws_integration_security_list(hass: HomeAssistant, connection, msg: dict) -> None:
    from .integration_security import async_integration_security_overview

    runtime = _runtime(hass)
    overview = await async_integration_security_overview(hass, runtime.store, runtime.secrets)
    overview["refreshed_at"] = runtime.store.data.get("integration_security", {}).get("refreshed_at")
    connection.send_result(msg["id"], overview)


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/integration_security/refresh"})
@websocket_api.async_response
async def ws_integration_security_refresh(hass: HomeAssistant, connection, msg: dict) -> None:
    """Refresh the GitHub-derived signals. Needs the owner-set github_token;
    returns a clear no-op reason when it's absent rather than erroring."""
    from .github_provenance import async_refresh_github_signals
    from .integration_security import async_integration_security_overview

    runtime = _runtime(hass)
    # Discover the repo URLs to look up from the current local overview.
    overview = await async_integration_security_overview(hass, runtime.store, runtime.secrets)
    repo_urls = [r["repo_url"] for r in overview["integrations"] if r.get("repo_url")]
    result = await async_refresh_github_signals(hass, runtime.store, repo_urls, runtime.secrets)
    connection.send_result(msg["id"], result)


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/containers/resources"})
@websocket_api.async_response
async def ws_containers_resources(hass: HomeAssistant, connection, msg: dict) -> None:
    """Live per-container CPU/memory (add-ons + Core + Supervisor). Returns
    available=False on a non-Supervisor install rather than erroring."""
    from .containers import async_container_resources

    connection.send_result(msg["id"], await async_container_resources(hass))


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/watchdog/status"})
@websocket_api.async_response
async def ws_watchdog_status(hass: HomeAssistant, connection, msg: dict) -> None:
    """Watchdog config + per-container runtime state (breach counters, last
    outcome, in-memory usage history) + hard-cap applied state."""
    runtime = _runtime(hass)
    connection.send_result(msg["id"], runtime.watchdog.status())


# The watchdog and hard-cap configuration are enforcement controls — a bad
# threshold auto-restarts add-ons, a hard cap changes host containers — so
# mutation is OWNER-ONLY like Settings, regardless of access_level.
@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/watchdog/set",
        vol.Optional("enabled"): bool,
        vol.Optional("default_cpu_percent"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        vol.Optional("default_memory_percent"): vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
        vol.Optional("default_action"): vol.In(WATCHDOG_ACTIONS),
        vol.Optional("sustained_samples"): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("interval_seconds"): vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
        # Per-container override — slug + any subset of the fields; passing
        # clear=True removes the override entirely (back to defaults).
        # Both slugs are shape-validated here (work item 2.2) and checked
        # against the Supervisor's installed add-on list in the handler.
        vol.Optional("override"): vol.Schema(
            {
                vol.Required("slug"): vol.All(str, vol.Match(ADDON_SLUG_PATTERN)),
                vol.Optional("cpu_percent"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=10, max=100))),
                vol.Optional("memory_percent"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=10, max=100))),
                vol.Optional("action"): vol.In(WATCHDOG_ACTIONS),
                vol.Optional("enabled"): bool,
                vol.Optional("clear"): bool,
            }
        ),
        # Docker hard cap for one add-on — memory_mb/cpus of None (or both
        # missing) clears the cap. Applied by the Probe, not by Core.
        vol.Optional("hard_limit"): vol.Schema(
            {
                vol.Required("slug"): vol.All(str, vol.Match(ADDON_SLUG_PATTERN)),
                vol.Optional("memory_mb"): vol.Any(None, vol.All(vol.Coerce(int), vol.Range(min=64, max=1_048_576))),
                vol.Optional("cpus"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0.1, max=64.0))),
            }
        ),
    }
)
@websocket_api.async_response
async def ws_watchdog_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)

    # Work item 2.2: a slug that is about to be STORED must name an add-on
    # the Supervisor itself reports as installed, and on a non-Supervisor
    # install (where no add-on exists at all) the request is refused as
    # not_supervisor. Clears are deliberately exempt from the installed
    # check: an override or cap left behind by a since-uninstalled add-on
    # must stay removable, and a clear never sends the slug anywhere (the
    # Probe resets removed caps from its own previously-applied list). The
    # slug's shape is schema-enforced above for clears too.
    from .resource_watchdog import async_installed_addon_slugs

    stored_slugs: list[str] = []
    if "override" in msg and not msg["override"].get("clear"):
        stored_slugs.append(msg["override"]["slug"])
    if "hard_limit" in msg and (
        msg["hard_limit"].get("memory_mb") or msg["hard_limit"].get("cpus")
    ):
        stored_slugs.append(msg["hard_limit"]["slug"])
    if stored_slugs:
        installed = async_installed_addon_slugs(hass)
        if installed is None:
            connection.send_error(
                msg["id"],
                "not_supervisor",
                "Per-add-on overrides and hard caps need a Supervisor-based install.",
            )
            return
        for slug in stored_slugs:
            if slug not in installed:
                connection.send_error(
                    msg["id"],
                    "addon_not_installed",
                    f"No installed add-on has the slug '{slug}'.",
                )
                return

    cfg = runtime.store.data["resource_watchdog"]
    changes: dict[str, Any] = {}

    for key in (
        "enabled",
        "default_cpu_percent",
        "default_memory_percent",
        "default_action",
        "sustained_samples",
        "interval_seconds",
    ):
        if key in msg:
            cfg[key] = msg[key]
            changes[key] = msg[key]

    if "override" in msg:
        ov = dict(msg["override"])
        slug = ov.pop("slug")
        if ov.pop("clear", False):
            cfg.setdefault("overrides", {}).pop(slug, None)
            changes["override_cleared"] = slug
        else:
            entry = cfg.setdefault("overrides", {}).setdefault(slug, {})
            entry.update(ov)
            changes["override"] = {"slug": slug, **ov}

    if "hard_limit" in msg:
        hl = dict(msg["hard_limit"])
        slug = hl.pop("slug")
        if not hl.get("memory_mb") and not hl.get("cpus"):
            cfg.setdefault("hard_limits", {}).pop(slug, None)
            # Stale applied-state would read as "still capped" — drop it too.
            cfg.setdefault("hard_limit_state", {}).pop(slug, None)
            changes["hard_limit_cleared"] = slug
        else:
            cfg.setdefault("hard_limits", {})[slug] = {
                "memory_mb": hl.get("memory_mb"),
                "cpus": hl.get("cpus"),
            }
            changes["hard_limit"] = {"slug": slug, **hl}

    if changes:
        runtime.store.async_schedule_save()
        # Re-arm the sampling timer so enabled/interval changes take effect
        # immediately rather than on the next restart.
        runtime.watchdog.async_start()
        runtime.audit.async_log(
            "soc_config_change",
            user_id=connection.user.id,
            detail={"action": "watchdog_config_changed", "changes": changes},
        )
    connection.send_result(msg["id"], runtime.watchdog.status())


# ----------------------------------------------------------------------------
# Network — UniFi Network / Protect direct-to-console read-only overview.
# One snapshot command backs the whole Network tab (status, WAN, clients,
# devices, Protect summary). Never mutates controller state; a connection
# problem comes back as reachable=False with a human-readable reason rather
# than a WS error, so the tab renders a "not reachable" card, not a failure.
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/network/overview"})
@websocket_api.async_response
async def ws_network_overview(hass: HomeAssistant, connection, msg: dict) -> None:
    from .unifi import async_network_overview

    runtime = _runtime(hass)
    overview = await async_network_overview(hass, runtime.store, runtime.secrets)
    connection.send_result(msg["id"], overview)


# ----------------------------------------------------------------------------
# Settings — the in-panel Settings tab. OWNER-ONLY (@require_owner): settings
# carry the security-sensitive controls (access level, API credentials), so
# they are reachable by the account owner alone, regardless of access_level.
# HaSocData.settings is the single source of truth for every non-secret
# setting; secret values live only in the private secret store (SEC-1), and
# the old entry.options mirror is gone entirely (SEC-2): a legacy mirror is
# scrubbed to {} once at setup. See config_flow.py's docstring.
# ----------------------------------------------------------------------------


async def _masked_settings(settings: dict, secrets) -> dict:
    """A copy of settings safe to send to the frontend: every secret key is
    present as a redaction placeholder (when set) or "" (when unset), and a
    companion "<key>_set" boolean says whether one is configured, so the
    form can show "configured" without ever receiving the raw secret.

    Secret VALUES no longer live in the settings dict at all (they moved to
    the private secret store, SEC-1), so presence is asked of that store
    per key; the wire shape is byte-for-byte what it was before the move,
    which is why the frontend needed no change.
    """
    out = dict(settings)
    for key in SECRET_SETTING_KEYS:
        # Defensive pop: settings must never carry a secret value anymore,
        # but if a stray one ever appeared it must not reach the wire.
        out.pop(key, None)
        is_set = bool(await secrets.async_get(key))
        out[key] = REDACTED_PLACEHOLDER if is_set else ""
        out[f"{key}_set"] = is_set
    return out


@require_owner
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/settings/get"})
@websocket_api.async_response
async def ws_settings_get(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(
        msg["id"], await _masked_settings(runtime.store.settings, runtime.secrets)
    )


@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/settings/set",
        vol.Optional(CONF_ACCESS_LEVEL): vol.In(
            [ACCESS_LEVEL_OWNER_ONLY, ACCESS_LEVEL_OWNER_AND_ADMINS]
        ),
        vol.Optional(CONF_AUDIT_RETENTION_DAYS): vol.All(vol.Coerce(int), vol.Range(min=7, max=3650)),
        vol.Optional(CONF_AUDIT_MAX_BYTES): vol.All(vol.Coerce(int), vol.Range(min=1_000_000)),
        vol.Optional(CONF_SCANNER_ENABLED): bool,
        vol.Optional(CONF_SCANNER_NETWORK_CHECKS_ENABLED): bool,
        vol.Optional(CONF_NVD_API_KEY): str,
        vol.Optional(CONF_GITHUB_TOKEN): str,
        vol.Optional(CONF_RISK_LEARNING_PERIOD_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
        vol.Optional(CONF_MFA_POLICY): vol.In([MFA_POLICY_AUDIT_ONLY, MFA_POLICY_AUTO_DEACTIVATE]),
        vol.Optional(CONF_MFA_GRACE_PERIOD_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Optional(CONF_SECURITY_SOURCES_ENABLED): {str: bool},
        # UniFi Network / Protect connections. Hosts accept a string or None
        # (None/"" clears the connection); the API keys are secrets handled
        # by the placeholder-means-unchanged logic below.
        vol.Optional(CONF_UNIFI_NETWORK_HOST): vol.Any(str, None),
        vol.Optional(CONF_UNIFI_NETWORK_API_KEY): str,
        vol.Optional(CONF_UNIFI_NETWORK_VERIFY_SSL): bool,
        vol.Optional(CONF_UNIFI_PROTECT_HOST): vol.Any(str, None),
        vol.Optional(CONF_UNIFI_PROTECT_API_KEY): str,
        vol.Optional(CONF_UNIFI_PROTECT_VERIFY_SSL): bool,
    }
)
@websocket_api.async_response
async def ws_settings_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    changes = {k: v for k, v in msg.items() if k not in ("type", "id")}
    # A secret field left as the redaction placeholder means "leave it as
    # it is" — the frontend never round-trips the real value back, so treat
    # the placeholder as no-change rather than overwriting the stored secret
    # with the mask string.
    for key in SECRET_SETTING_KEYS:
        if changes.get(key) == REDACTED_PLACEHOLDER:
            del changes[key]

    # Secret values are routed to the private secret store and never enter
    # the settings dict (SEC-1). An empty string clears the stored secret,
    # matching the pre-SEC-1 behavior where "" made the "<key>_set" flag
    # read false.
    secret_changes = {
        key: changes.pop(key) for key in list(changes) if key in SECRET_SETTING_KEYS
    }
    for key, value in secret_changes.items():
        await runtime.secrets.async_set(key, value)

    if changes:
        runtime.store.async_update_settings(**changes)

    if changes or secret_changes:
        # The audit record names every changed key. Secret values are
        # replaced with the placeholder HERE so no raw secret even enters
        # the audit path; audit.async_log's own _redact_secrets_deep stays
        # behind this as defense in depth.
        runtime.audit.async_log(
            "soc_config_change",
            user_id=connection.user.id,
            detail={
                "action": "settings_changed",
                "changes": {
                    **changes,
                    **{key: REDACTED_PLACEHOLDER for key in secret_changes},
                },
            },
        )
    connection.send_result(
        msg["id"], await _masked_settings(runtime.store.settings, runtime.secrets)
    )


# ----------------------------------------------------------------------------
# Live-update subscription
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/subscribe", vol.Optional("topic", default="dashboard"): str}
)
@callback
def ws_subscribe(hass: HomeAssistant, connection, msg: dict) -> None:
    """Push a lightweight 'refresh' ping whenever the named topic updates.

    The frontend re-fetches the relevant list/summary command on receipt —
    this only tells it *that* something changed, not what, keeping payloads
    small and this module decoupled from every consumer's exact shape.
    """

    @callback
    def _forward(*_args: Any) -> None:
        connection.send_message(websocket_api.messages.event_message(msg["id"], {"topic": msg["topic"]}))

    unsub = async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{msg['topic']}", _forward)
    connection.subscriptions[msg["id"]] = unsub
    connection.send_result(msg["id"])
