"""Custom WebSocket API: the single surface the frontend panel talks to.

Every command is gated by @require_soc_access, with owner-only tiers on top;
the access model and audit rules are in docs/security.md.
"""
from __future__ import annotations

import ipaddress
import logging
import re
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
    CONF_PIHOLE_API_KEY,
    CONF_PIHOLE_HOST,
    CONF_PIHOLE_IOT_CIDR,
    CONF_PIHOLE_VERIFY_SSL,
    CONF_SCANNER_ENABLED,
    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
    CONF_SECURITY_SOURCES_ENABLED,
    CONF_SNMP_AUTH_PASSPHRASE,
    CONF_SNMP_ENABLED,
    CONF_SNMP_LISTEN_ADDRESS,
    CONF_SNMP_PORT,
    CONF_SNMP_PRIV_PASSPHRASE,
    CONF_SNMP_USERNAME,
    CONF_SYSLOG_FACILITY,
    CONF_SYSLOG_FORMAT,
    CONF_SYSLOG_HOST,
    CONF_SYSLOG_PORT,
    CONF_SYSLOG_TLS_VERIFY,
    CONF_SYSLOG_TRANSPORT,
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
    SYSLOG_TRANSPORTS,
    SYSLOG_FORMATS,
    WATCHDOG_ACTIONS,
)
from .detections import THRESHOLD_SPECS, secure_default_thresholds, thresholds
from .resource_watchdog import ADDON_SLUG_PATTERN
from .snmp import (
    snmp_ip_address,
    validate_enabled_config,
    validate_snmp_passphrase,
    validate_snmp_username,
)

_LOGGER = logging.getLogger(__name__)
_SYSLOG_DNS_LABEL = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def _syslog_host(value: Any) -> str | None:
    """Accept only an IP literal or DNS hostname, never a URL/path."""
    if value is None:
        return None
    host = cv.string(value).strip()
    if not host:
        return None
    if len(host) > 253:
        raise vol.Invalid("Syslog host is too long")
    try:
        ipaddress.ip_address(host)
        return host
    except ValueError:
        pass
    labels = host.rstrip(".").split(".")
    if not labels or any(not _SYSLOG_DNS_LABEL.fullmatch(label) for label in labels):
        raise vol.Invalid("Syslog host must be an IP address or DNS hostname")
    return host


def _detection_thresholds_schema() -> vol.Schema:
    """The voluptuous schema for a detection_thresholds settings payload.

    Unknown rules or parameters are rejected; the schema is strict.
    """
    rules: dict[Any, Any] = {}
    for rule, params in THRESHOLD_SPECS.items():
        fields: dict[Any, Any] = {}
        for name, spec in params.items():
            default = spec["default"]
            if isinstance(default, bool):
                fields[vol.Optional(name)] = bool
            elif isinstance(default, float):
                fields[vol.Optional(name)] = vol.All(
                    vol.Coerce(float), vol.Range(min=spec["min"], max=spec["max"])
                )
            else:
                fields[vol.Optional(name)] = vol.All(
                    vol.Coerce(int), vol.Range(min=spec["min"], max=spec["max"])
                )
        rules[vol.Optional(rule)] = vol.Schema(fields)
    return vol.Schema(rules)


def _threshold_table_payload(store) -> dict[str, Any]:
    """THRESHOLD_SPECS plus effective values, shaped for the frontend."""
    out: dict[str, Any] = {}
    for rule, params in THRESHOLD_SPECS.items():
        effective = thresholds(store, rule)
        out[rule] = {
            name: {
                "value": effective[name],
                "default": spec["default"],
                "min": spec.get("min"),
                "max": spec.get("max"),
                "type": "bool"
                if isinstance(spec["default"], bool)
                else "float"
                if isinstance(spec["default"], float)
                else "int",
            }
            for name, spec in params.items()
        }
    return out


def _runtime(hass: HomeAssistant):
    # Local import: avoids a circular import with __init__.py.
    from . import get_runtime_data

    return get_runtime_data(hass)


def require_soc_access(func):
    """Admin-gate every ha_soc/* command, then apply HA SOC's own access_level.

    Fails closed to owner-only when the runtime is not reachable yet.
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
    """Owner-only gate, stricter than require_soc_access; ignores access_level."""

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

    Checks group membership, not User.is_admin, which is False for a
    deactivated admin. An unknown id returns False.
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
        ws_audit_category_stats,
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
        ws_detections_bulk_set_status,
        ws_detections_thresholds_get,
        ws_detections_thresholds_reset,
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
        ws_network_security_overview,
        ws_layout_get,
        ws_layout_set,
        ws_settings_get,
        ws_settings_set,
        ws_subscribe,
    ):
        websocket_api.async_register_command(hass, handler)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/access/info"})
@websocket_api.async_response
async def ws_access_info(hass: HomeAssistant, connection, msg: dict) -> None:
    """Tell the frontend (and a blocked admin) exactly where it stands.

    Stays on plain require_admin so a blocked admin can learn why.
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
    """The version shown in the panel's footer, read from manifest.json.

    Plain require_admin so a blocked admin still sees it.
    """
    from homeassistant.loader import async_get_integration

    integration = await async_get_integration(hass, DOMAIN)
    connection.send_result(
        msg["id"], {"version": str(integration.version) if integration.version else None}
    )


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
    # Audited before the fetch, so a probe for a missing id still leaves a record.
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

    # Admin-group targets are owner-only, as for deactivate/delete/revoke.
    if not connection.user.is_owner and await _async_target_is_admin(
        hass, msg["user_id"]
    ):
        raise Unauthorized

    # Core's async_update_user accepts is_active directly; keep the owner invariant.
    target = await hass.auth.async_get_user(msg["user_id"])
    if target is not None and target.is_owner and changes.get("is_active") is False:
        connection.send_error(
            msg["id"], "cannot_deactivate_owner", "The owner account cannot be deactivated"
        )
        return

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
    # Admin-group targets are owner-only.
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
    # Admin-group targets are owner-only.
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
    # Admin-group targets are owner-only.
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
    # Admin-group targets are owner-only.
    if not connection.user.is_owner and await _async_target_is_admin(hass, msg["user_id"]):
        raise Unauthorized
    revoked = await runtime.users.async_revoke_all_sessions(msg["user_id"])
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "revoked_all_sessions", "revoked": revoked},
    )
    connection.send_result(msg["id"], {"revoked": revoked})


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/users/set_password",
        vol.Required("user_id"): str,
        vol.Required("password"): str,
        # Default True: a reset must sign out whoever held the old password.
        vol.Optional("revoke_sessions", default=True): bool,
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
    sessions_revoked = 0
    if msg["revoke_sessions"]:
        sessions_revoked = await runtime.users.async_revoke_interactive_sessions(
            msg["user_id"]
        )
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={
            "target_user_id": msg["user_id"],
            "action": "password_reset",
            "revoke_sessions": msg["revoke_sessions"],
            "sessions_revoked": sessions_revoked,
        },
    )
    connection.send_result(msg["id"], {"ok": True, "sessions_revoked": sessions_revoked})


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


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/audit/category_stats"})
@websocket_api.async_response
async def ws_audit_category_stats(hass: HomeAssistant, connection, msg: dict) -> None:
    """Per-category record counts and byte shares for the newest audit day."""
    runtime = _runtime(hass)
    connection.send_result(msg["id"], await runtime.audit.async_category_stats())


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
    # Only flags present in the message are recorded.
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


# Owner-only: rewrites another user's stored sidebar policy.
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
    # An unknown id is an error, not a silent success.
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


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/detections/bulk_set_status",
        vol.Required("detection_ids"): [str],
        vol.Required("status"): vol.In(["open", "ack", "resolved"]),
    }
)
@websocket_api.async_response
async def ws_detections_bulk_set_status(hass: HomeAssistant, connection, msg: dict) -> None:
    """Set many detections to one status in one action.

    Audited once with the ids that changed; unknown ids are reported back.
    """
    from homeassistant.util import dt as dt_util

    runtime = _runtime(hass)
    at = dt_util.utcnow().isoformat()
    updated: list[str] = []
    missing: list[str] = []
    for detection_id in msg["detection_ids"]:
        detection = runtime.store.async_set_detection_status(
            detection_id, msg["status"], by_user_id=connection.user.id, at=at
        )
        if detection is None:
            missing.append(detection_id)
        else:
            updated.append(detection_id)
    if updated:
        runtime.audit.async_log(
            "detection_status_changed",
            user_id=connection.user.id,
            detail={
                "action": "bulk_set_status",
                "detection_ids": updated,
                "new_status": msg["status"],
            },
        )
    connection.send_result(msg["id"], {"updated": len(updated), "missing": missing})


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/detections/thresholds"})
@websocket_api.async_response
async def ws_detections_thresholds_get(hass: HomeAssistant, connection, msg: dict) -> None:
    """The full threshold table: per rule and parameter the effective value,
    secure default, inclusive range, and type. Read-only."""
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"rules": _threshold_table_payload(runtime.store)})


# Owner-only: rewrites the same stored setting ha_soc/settings/set guards.
@require_owner
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/detections/thresholds_reset"})
@websocket_api.async_response
async def ws_detections_thresholds_reset(hass: HomeAssistant, connection, msg: dict) -> None:
    """One-action "Reset to secure defaults"; audits a per-field diff."""
    runtime = _runtime(hass)
    diff: dict[str, dict[str, Any]] = {}
    stored = runtime.store.settings.get("detection_thresholds") or {}
    for rule, params in stored.items():
        if rule not in THRESHOLD_SPECS or not params:
            continue
        defaults = secure_default_thresholds(rule)
        for name, value in params.items():
            if name in defaults and value != defaults[name]:
                diff[f"{rule}.{name}"] = {"old": value, "new": defaults[name]}
    runtime.store.async_update_settings(detection_thresholds={})
    if diff:
        runtime.audit.async_log(
            "soc_config_change",
            user_id=connection.user.id,
            detail={"action": "detection_thresholds_reset", "changes": diff},
        )
    connection.send_result(msg["id"], {"rules": _threshold_table_payload(runtime.store)})


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
    from homeassistant.util import dt as dt_util

    runtime = _runtime(hass)
    findings = await runtime.vulns.async_run_scan()
    # A completed scan proves p_vuln computed even when nothing was found.
    runtime.store.async_mark_posture_term_computed(
        "p_vuln", dt_util.utcnow().isoformat()
    )
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


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/health/list"})
@websocket_api.async_response
async def ws_health_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    findings = list(runtime.store.data["misconfig_findings"].values())
    # Most severe first; an unknown severity sorts last rather than raising.
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


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/logs/fault"})
@websocket_api.async_response
async def ws_logs_fault(hass: HomeAssistant, connection, msg: dict) -> None:
    from .logs import async_fault_log_overview

    # Privileged read; audited before the fetch even if the file is absent.
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

    # Privileged read; audited before the fetch, add-on targets as the bare slug.
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


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/probe/status"})
@websocket_api.async_response
async def ws_probe_status(hass: HomeAssistant, connection, msg: dict) -> None:
    from .probe import async_probe_overview

    runtime = _runtime(hass)
    overview = await async_probe_overview(hass, runtime.store)
    connection.send_result(msg["id"], overview)


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


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/entity_remap/find_references", vol.Required("entity_id"): str}
)
@websocket_api.async_response
async def ws_entity_remap_find_references(hass: HomeAssistant, connection, msg: dict) -> None:
    from .entity_remap import async_find_references

    report = await async_find_references(hass, msg["entity_id"])
    connection.send_result(msg["id"], report)


# Owner-only: applying a remap rewrites configuration files.
@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/entity_remap/apply",
        # cv.entity_id enforces domain.object_id, so a typo cannot break automations on reload.
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


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/security_health/list"})
@websocket_api.async_response
async def ws_security_health_list(hass: HomeAssistant, connection, msg: dict) -> None:
    from .security_health import async_security_overview

    runtime = _runtime(hass)
    overview = await async_security_overview(hass, runtime.store)
    connection.send_result(msg["id"], overview)


# Every firewall command is owner-only, status included; see docs/THREAT-MODEL.md.
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
    non-empty one re-pins (trust-on-first-use)."""
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
    """Owner-only escape hatch: archive a pending test whose report will
    never arrive because the add-on went silent mid-test."""
    from .firewall import async_discard_pending

    runtime = _runtime(hass)
    ok, reason = await async_discard_pending(
        hass, runtime.store, user_id=connection.user.id
    )
    if not ok:
        connection.send_error(msg["id"], "firewall_discard_rejected", reason)
        return
    connection.send_result(msg["id"], {"ok": True})


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


# Owner-only: thresholds and hard caps restart add-ons and change host containers.
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
        # clear=True removes the override; slugs are also checked against installed add-ons below.
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
        # memory_mb and cpus both None clears the cap; applied by the Probe, not Core.
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

    # Clears skip the installed check so a stale entry for a removed add-on stays removable.
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
            # Stale applied-state would read as "still capped"; drop it too.
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
        # Re-arm the timer so enabled/interval changes apply immediately.
        runtime.watchdog.async_start()
        runtime.audit.async_log(
            "soc_config_change",
            user_id=connection.user.id,
            detail={"action": "watchdog_config_changed", "changes": changes},
        )
    connection.send_result(msg["id"], runtime.watchdog.status())


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/network/overview"})
@websocket_api.async_response
async def ws_network_overview(hass: HomeAssistant, connection, msg: dict) -> None:
    from .unifi import async_network_overview

    runtime = _runtime(hass)
    overview = await async_network_overview(hass, runtime.store, runtime.secrets)
    connection.send_result(msg["id"], overview)


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/network_security/overview"})
@websocket_api.async_response
async def ws_network_security_overview(hass: HomeAssistant, connection, msg: dict) -> None:
    from .network_security import async_network_security_overview

    runtime = _runtime(hass)
    overview = await async_network_security_overview(hass, runtime.store, runtime.secrets)
    connection.send_result(msg["id"], overview)


# Layout commands touch only the calling user's own layout and are not audited.
@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/layout/get", vol.Required("view_id"): str}
)
@websocket_api.async_response
async def ws_layout_get(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    layout = runtime.store.get_user_panel_layout(connection.user.id, msg["view_id"])
    connection.send_result(
        msg["id"], {"order": layout.get("order", []), "hidden": layout.get("hidden", [])}
    )


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/layout/set",
        vol.Required("view_id"): str,
        vol.Required("order"): [str],
        vol.Required("hidden"): [str],
    }
)
@websocket_api.async_response
async def ws_layout_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    runtime.store.async_set_user_panel_layout(
        connection.user.id, msg["view_id"], msg["order"], msg["hidden"]
    )
    connection.send_result(msg["id"], {"order": msg["order"], "hidden": msg["hidden"]})


async def _masked_settings(settings: dict, secrets) -> dict:
    """A copy of settings safe to send to the frontend: every secret key is
    present as a redaction placeholder (when set) or "" (when unset), plus a
    companion "<key>_set" boolean."""
    out = dict(settings)
    for key in SECRET_SETTING_KEYS:
        # Defensive pop: a stray secret value must not reach the wire.
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
    payload = await _masked_settings(runtime.store.settings, runtime.secrets)
    payload["syslog_status"] = runtime.syslog.status
    payload["snmp_status"] = runtime.store.data.get("snmp_status")
    connection.send_result(msg["id"], payload)


@require_owner
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/settings/set",
        vol.Optional(CONF_ACCESS_LEVEL): vol.In(
            [ACCESS_LEVEL_OWNER_ONLY, ACCESS_LEVEL_OWNER_AND_ADMINS]
        ),
        vol.Optional(CONF_AUDIT_RETENTION_DAYS): vol.All(vol.Coerce(int), vol.Range(min=7, max=3650)),
        vol.Optional(CONF_AUDIT_MAX_BYTES): vol.All(vol.Coerce(int), vol.Range(min=1_000_000)),
        vol.Optional(CONF_SYSLOG_TRANSPORT): vol.In(SYSLOG_TRANSPORTS),
        vol.Optional(CONF_SYSLOG_FORMAT): vol.In(SYSLOG_FORMATS),
        vol.Optional(CONF_SYSLOG_HOST): _syslog_host,
        vol.Optional(CONF_SYSLOG_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(CONF_SYSLOG_TLS_VERIFY): bool,
        # local0 through local7 only.
        vol.Optional(CONF_SYSLOG_FACILITY): vol.All(vol.Coerce(int), vol.Range(min=16, max=23)),
        # The floor of 30 stops an accidental "1" from erasing an evidence trail.
        vol.Optional("evidence_retention_days"): vol.All(vol.Coerce(int), vol.Range(min=30, max=3650)),
        vol.Optional(CONF_SCANNER_ENABLED): bool,
        vol.Optional(CONF_SCANNER_NETWORK_CHECKS_ENABLED): bool,
        # Off switch for NVD lookups (consumed by vulns.py).
        vol.Optional("nvd_lookups_enabled"): bool,
        vol.Optional(CONF_NVD_API_KEY): str,
        vol.Optional(CONF_GITHUB_TOKEN): str,
        # Partial per-rule overrides; ranges come from detections.THRESHOLD_SPECS.
        vol.Optional("detection_thresholds"): _detection_thresholds_schema(),
        vol.Optional(CONF_MFA_POLICY): vol.In([MFA_POLICY_AUDIT_ONLY, MFA_POLICY_AUTO_DEACTIVATE]),
        vol.Optional(CONF_MFA_GRACE_PERIOD_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Optional(CONF_SECURITY_SOURCES_ENABLED): {str: bool},
        # None or "" clears a host; API keys use the placeholder-means-unchanged logic below.
        vol.Optional(CONF_UNIFI_NETWORK_HOST): vol.Any(str, None),
        vol.Optional(CONF_UNIFI_NETWORK_API_KEY): str,
        vol.Optional(CONF_UNIFI_NETWORK_VERIFY_SSL): bool,
        vol.Optional(CONF_UNIFI_PROTECT_HOST): vol.Any(str, None),
        vol.Optional(CONF_UNIFI_PROTECT_API_KEY): str,
        vol.Optional(CONF_UNIFI_PROTECT_VERIFY_SSL): bool,
        # Same host and secret handling as UniFi; iot_cidr is not a secret.
        vol.Optional(CONF_PIHOLE_HOST): vol.Any(str, None),
        vol.Optional(CONF_PIHOLE_API_KEY): str,
        vol.Optional(CONF_PIHOLE_VERIFY_SSL): bool,
        vol.Optional(CONF_PIHOLE_IOT_CIDR): vol.Any(str, None),
        # Only an explicit unicast listener and SNMPv3 AuthPriv are representable.
        vol.Optional(CONF_SNMP_ENABLED): bool,
        vol.Optional(CONF_SNMP_LISTEN_ADDRESS): snmp_ip_address,
        vol.Optional(CONF_SNMP_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Optional(CONF_SNMP_USERNAME): vol.Any(None, validate_snmp_username),
        vol.Optional(CONF_SNMP_AUTH_PASSPHRASE): vol.Any(None, validate_snmp_passphrase),
        vol.Optional(CONF_SNMP_PRIV_PASSPHRASE): vol.Any(None, validate_snmp_passphrase),
    }
)
@websocket_api.async_response
async def ws_settings_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    changes = {k: v for k, v in msg.items() if k not in ("type", "id")}
    # The placeholder means "unchanged"; the frontend never round-trips the real value.
    for key in SECRET_SETTING_KEYS:
        if changes.get(key) == REDACTED_PLACEHOLDER:
            del changes[key]

    # Secrets go to the secret store, never the settings dict; "" clears one.
    secret_changes = {
        key: changes.pop(key) for key in list(changes) if key in SECRET_SETTING_KEYS
    }

    snmp_keys = {
        CONF_SNMP_ENABLED,
        CONF_SNMP_LISTEN_ADDRESS,
        CONF_SNMP_PORT,
        CONF_SNMP_USERNAME,
        CONF_SNMP_AUTH_PASSPHRASE,
        CONF_SNMP_PRIV_PASSPHRASE,
    }
    if snmp_keys.intersection(changes) or snmp_keys.intersection(secret_changes):
        prospective_settings = dict(runtime.store.settings)
        prospective_settings.update(changes)
        prospective_secrets = {
            key: (
                secret_changes[key]
                if key in secret_changes
                else await runtime.secrets.async_get(key)
            )
            for key in (CONF_SNMP_AUTH_PASSPHRASE, CONF_SNMP_PRIV_PASSPHRASE)
        }
        # Validate the full prospective config before writing either store.
        validate_enabled_config(prospective_settings, prospective_secrets)

    for key, value in secret_changes.items():
        await runtime.secrets.async_set(key, value)

    # Partial override merged per field; the audit diff is against the effective value.
    threshold_diff: dict[str, Any] = {}
    threshold_payload = changes.pop("detection_thresholds", None)
    if threshold_payload:
        stored_thresholds = {
            rule: dict(params)
            for rule, params in (
                runtime.store.settings.get("detection_thresholds") or {}
            ).items()
        }
        for rule, params in threshold_payload.items():
            effective = thresholds(runtime.store, rule)
            for name, value in params.items():
                if effective.get(name) != value:
                    threshold_diff[f"{rule}.{name}"] = {
                        "old": effective.get(name),
                        "new": value,
                    }
                stored_thresholds.setdefault(rule, {})[name] = value
        runtime.store.async_update_settings(detection_thresholds=stored_thresholds)

    if changes:
        runtime.store.async_update_settings(**changes)

    if any(
        key in changes
        for key in (
            CONF_SYSLOG_TRANSPORT,
            CONF_SYSLOG_FORMAT,
            CONF_SYSLOG_HOST,
            CONF_SYSLOG_PORT,
            CONF_SYSLOG_TLS_VERIFY,
            CONF_SYSLOG_FACILITY,
        )
    ):
        await runtime.syslog.async_reconfigure()

    if changes or secret_changes or threshold_diff:
        # Secrets are masked here, before entering the audit path.
        audited_changes: dict[str, Any] = {
            **changes,
            **{key: REDACTED_PLACEHOLDER for key in secret_changes},
        }
        if threshold_diff:
            audited_changes["detection_thresholds"] = threshold_diff
        runtime.audit.async_log(
            "soc_config_change",
            user_id=connection.user.id,
            detail={"action": "settings_changed", "changes": audited_changes},
        )
    payload = await _masked_settings(runtime.store.settings, runtime.secrets)
    payload["syslog_status"] = runtime.syslog.status
    payload["snmp_status"] = runtime.store.data.get("snmp_status")
    connection.send_result(msg["id"], payload)


@require_soc_access
@websocket_api.websocket_command(
    {vol.Required("type"): "ha_soc/subscribe", vol.Optional("topic", default="dashboard"): str}
)
@callback
def ws_subscribe(hass: HomeAssistant, connection, msg: dict) -> None:
    """Push a lightweight 'refresh' ping whenever the named topic updates.

    Signals only that something changed, not what.
    """

    @callback
    def _forward(*_args: Any) -> None:
        connection.send_message(websocket_api.messages.event_message(msg["id"], {"topic": msg["topic"]}))

    unsub = async_dispatcher_connect(hass, f"{SIGNAL_UPDATE}_{msg['topic']}", _forward)
    connection.subscriptions[msg["id"]] = unsub
    connection.send_result(msg["id"])
