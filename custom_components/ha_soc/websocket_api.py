"""Custom WebSocket API — the single surface the frontend panel talks to.

Every command is admin-gated (`@websocket_api.require_admin`), regardless of
whether the panel itself is registered `require_admin=True` — panel
visibility is cosmetic (see `permissions.py`); the real gate has to be here.

Command namespace is `ha_soc/*`. Mutating/PII-bearing commands never return
raw refresh-token secrets or JWT material to the frontend — only metadata
(ids, timestamps, client names).
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_UPDATE

_LOGGER = logging.getLogger(__name__)


def _runtime(hass: HomeAssistant):
    # Local import to avoid a circular import with __init__.py at module load time.
    from . import get_runtime_data

    return get_runtime_data(hass)


def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register every ha_soc/* command. Safe to call once per HA process."""
    for handler in (
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
        ws_dashboard_nodes,
        ws_subscribe,
    ):
        websocket_api.async_register_command(hass, handler)


# ----------------------------------------------------------------------------
# Users & Access
# ----------------------------------------------------------------------------


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/users/list"})
@websocket_api.async_response
async def ws_users_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"users": await runtime.users.async_list_users()})


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/sessions/list"})
@websocket_api.async_response
async def ws_sessions_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"sessions": runtime.live_sessions.list_sessions()})


# ----------------------------------------------------------------------------
# Audit log
# ----------------------------------------------------------------------------


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/audit/verify_chain"})
@websocket_api.async_response
async def ws_audit_verify_chain(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], await runtime.audit.async_verify_chain())


# ----------------------------------------------------------------------------
# Permissions matrix
# ----------------------------------------------------------------------------


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/permissions/dashboards/list"})
@websocket_api.async_response
async def ws_permissions_dashboards_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(
        msg["id"], {"dashboards": await runtime.permissions.async_list_dashboards()}
    )


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/permissions/drift/check"})
@websocket_api.async_response
async def ws_permissions_drift_check(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"drift": await runtime.permissions.async_check_drift()})


# ----------------------------------------------------------------------------
# Risk & posture
# ----------------------------------------------------------------------------


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/risk/list"})
@websocket_api.async_response
async def ws_risk_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    results = runtime.risk.last_risk_results or await runtime.risk.async_recompute_all()
    connection.send_result(msg["id"], {"risk": results})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/risk/posture"})
@websocket_api.async_response
async def ws_risk_posture(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    posture = runtime.risk.last_posture_result or await runtime.risk.async_compute_posture()
    connection.send_result(msg["id"], posture)


# ----------------------------------------------------------------------------
# Detections
# ----------------------------------------------------------------------------


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/vulns/list"})
@websocket_api.async_response
async def ws_vulns_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"findings": list(runtime.store.data["vuln_findings"].values())})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/vulns/scan_now"})
@websocket_api.async_response
async def ws_vulns_scan_now(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    api_key = runtime.store.settings.get("nvd_api_key") or None
    findings = await runtime.vulns.async_run_scan(api_key=api_key)
    connection.send_result(msg["id"], {"findings": findings})


@websocket_api.require_admin
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/scanner/list"})
@websocket_api.async_response
async def ws_scanner_list(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    connection.send_result(msg["id"], {"findings": list(runtime.store.data["scanner_findings"].values())})


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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


@websocket_api.require_admin
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

    connection.send_result(
        msg["id"],
        {
            "posture": posture,
            "posture_history": runtime.store.data["posture_history"][-30:],
            "open_detections_count": len(open_detections),
            "users_at_risk_count": len(users_at_risk),
            "total_users_count": len(risk_results),
            "critical_high_vuln_count": len(high_crit_vulns),
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


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): "ha_soc/dashboard/nodes"})
@websocket_api.async_response
async def ws_dashboard_nodes(hass: HomeAssistant, connection, msg: dict) -> None:
    runtime = _runtime(hass)
    overview = await runtime.vulns.async_node_overview()

    scored_nodes = [n for n in overview["nodes"] if n["total_findings"] > 0]
    combined_risk_score = (
        round(sum(n["risk_score"] for n in scored_nodes) / len(scored_nodes), 1)
        if scored_nodes
        else 0.0
    )

    connection.send_result(
        msg["id"],
        {
            "nodes": overview["nodes"],
            "status_counts": overview["status_counts"],
            "by_vendor": overview["by_vendor"],
            "combined_risk_score": combined_risk_score,
        },
    )


# ----------------------------------------------------------------------------
# Live-update subscription
# ----------------------------------------------------------------------------


@websocket_api.require_admin
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
