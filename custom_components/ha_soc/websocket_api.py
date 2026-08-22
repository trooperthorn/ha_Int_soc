"""Custom WebSocket API — the single surface the frontend panel talks to.

Every command is gated by `@require_soc_access` (admin, plus HA SOC's own
owner-only/owner+admin access_level setting), regardless of whether the
panel itself is registered `require_admin=True` — panel visibility is
cosmetic (see `permissions.py`); the real gate has to be here. The one
exception is `ha_soc/access/info`, which stays on plain
`@websocket_api.require_admin` so an admin currently blocked by
access_level can still ask why.

Command namespace is `ha_soc/*`. Mutating/PII-bearing commands never return
raw refresh-token secrets or JWT material to the frontend — only metadata
(ids, timestamps, client names).
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    ACCESS_LEVEL_OWNER_AND_ADMINS,
    ACCESS_LEVEL_OWNER_ONLY,
    CONF_ACCESS_LEVEL,
    CONF_AUDIT_MAX_BYTES,
    CONF_AUDIT_RETENTION_DAYS,
    CONF_MFA_GRACE_PERIOD_DAYS,
    CONF_MFA_POLICY,
    CONF_NVD_API_KEY,
    CONF_RISK_LEARNING_PERIOD_DAYS,
    CONF_SCANNER_ENABLED,
    CONF_SCANNER_NETWORK_CHECKS_ENABLED,
    CONF_SECURITY_SOURCES_ENABLED,
    DEFAULT_ACCESS_LEVEL,
    DOMAIN,
    MFA_POLICY_AUDIT_ONLY,
    MFA_POLICY_AUTO_DEACTIVATE,
    SIGNAL_UPDATE,
)

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


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register every ha_soc/* command. Safe to call once per HA process."""
    for handler in (
        ws_access_info,
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
    ok = await runtime.users.async_delete_user(msg["user_id"])
    if not ok:
        connection.send_error(msg["id"], "delete_failed", "Could not delete user")
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
    count = await runtime.users.async_revoke_all_sessions(msg["user_id"])
    runtime.audit.async_log(
        "user_updated",
        user_id=connection.user.id,
        detail={"target_user_id": msg["user_id"], "action": "revoked_all_sessions", "count": count},
    )
    connection.send_result(msg["id"], {"revoked": count})


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
    connection.send_result(msg["id"], {"ok": True})


@require_soc_access
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
    runtime = _runtime(hass)
    runtime.store.async_set_detection_status(msg["detection_id"], msg["status"])
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
    api_key = runtime.store.settings.get("nvd_api_key") or None
    findings = await runtime.vulns.async_run_scan(api_key=api_key)
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
    connection.send_result(
        msg["id"],
        {
            "integrations": list(runtime.store.data["integration_health"].values()),
            "misconfig_findings": list(runtime.store.data["misconfig_findings"].values()),
        },
    )


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


@require_soc_access
@websocket_api.websocket_command(
    {
        vol.Required("type"): "ha_soc/entity_remap/apply",
        vol.Required("old_entity_id"): str,
        vol.Required("new_entity_id"): str,
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

    result = await async_apply_remap(hass, old_id, new_id)
    runtime.audit.async_log(
        "user_updated",
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
# Settings — the in-panel Settings tab. Mirrors the native "Configure"
# options flow (config_flow.py) over the exact same store: HaSocData.settings
# is the single source of truth, entry.options is kept as a synced copy for
# pre-load prefill only. See config_flow.py's module docstring.
# ----------------------------------------------------------------------------


@require_soc_access
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/settings/get"})
@websocket_api.async_response
async def ws_settings_get(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], dict(runtime.store.settings))


@require_soc_access
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
        vol.Optional(CONF_RISK_LEARNING_PERIOD_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
        vol.Optional(CONF_MFA_POLICY): vol.In([MFA_POLICY_AUDIT_ONLY, MFA_POLICY_AUTO_DEACTIVATE]),
        vol.Optional(CONF_MFA_GRACE_PERIOD_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=365)),
        vol.Optional(CONF_SECURITY_SOURCES_ENABLED): {str: bool},
    }
)
@websocket_api.async_response
async def ws_settings_set(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    changes = {k: v for k, v in msg.items() if k not in ("type", "id")}
    if changes:
        runtime.store.async_update_settings(**changes)

        # Keep entry.options in sync so the native Configure dialog (and a
        # pre-runtime prefill) never shows a value this tab already changed.
        entries = hass.config_entries.async_entries(DOMAIN)
        if entries:
            hass.config_entries.async_update_entry(
                entries[0], options=dict(runtime.store.settings)
            )

        runtime.audit.async_log(
            "user_updated",
            user_id=connection.user.id,
            detail={"action": "settings_changed", "changes": changes},
        )
    connection.send_result(msg["id"], dict(runtime.store.settings))


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
