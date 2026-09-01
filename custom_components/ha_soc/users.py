"""User security data access — the only HA SOC module that touches hass.auth.

Everything here reads and writes the real Home Assistant auth store
(hass.auth); it holds no state of its own beyond the in-memory
LiveSessionRegistry below. Two limitations are load-bearing, not bugs:

- "Last login" is inferred from refresh-token activity
  (created_at / last_used_at). A token refresh looks identical to a fresh
  login to this API, so last_login_at is best described as "last time this
  user's session was active", not a true authentication timestamp.
- MFA state can be read and audited (async_get_enabled_mfa) but never
  enforced from here — Home Assistant core has no hook to require MFA for a
  user, so HA SOC can only report on it.

This module knows nothing about websocket_api, audit.py, or any other HA SOC
module. It talks to hass.auth and nothing else.
"""
from __future__ import annotations

import inspect
import logging
import uuid
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.util.dt as dt

try:
    from homeassistant.auth.const import (
        TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
        TOKEN_TYPE_SYSTEM,
    )
except ImportError:  # pragma: no cover - older/newer core layout fallback
    try:
        from homeassistant.auth.models import (
            TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN,
            TOKEN_TYPE_SYSTEM,
        )
    except ImportError:
        TOKEN_TYPE_SYSTEM = "system"
        TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN = "long_lived_access_token"

from homeassistant.auth.models import User
from homeassistant.auth.providers import homeassistant as auth_ha

_LOGGER = logging.getLogger(__name__)


def _iso(value) -> str | None:
    return value.isoformat() if value is not None else None


async def _async_get_ha_auth_provider(hass: HomeAssistant):
    # Core's signature is synchronous despite the async_ prefix, but that
    # prefix convention has flipped before elsewhere in core — tolerate
    # either shape rather than guessing.
    result = auth_ha.async_get_provider(hass)
    if inspect.isawaitable(result):
        result = await result
    return result


class UsersManager:
    """Read/write access to hass.auth, shaped for the HA SOC users panel."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def _async_build_user_record(self, user: User) -> dict[str, Any]:
        session_tokens = [
            token
            for token in user.refresh_tokens.values()
            if token.token_type != TOKEN_TYPE_SYSTEM
        ]

        last_login_at: str | None = None
        last_login_ip: str | None = None
        if session_tokens:
            latest = max(session_tokens, key=lambda t: t.last_used_at or t.created_at)
            last_login_at = _iso(latest.last_used_at or latest.created_at)
            last_login_ip = latest.last_used_ip

        llat_tokens = [
            token
            for token in user.refresh_tokens.values()
            if token.token_type == TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN
        ]
        llat_count = len(llat_tokens)
        llat_oldest_days: int | None = None
        if llat_tokens:
            oldest = min(token.created_at for token in llat_tokens)
            llat_oldest_days = (dt.utcnow() - oldest).days

        # Best-effort proxy only — Home Assistant does not record a true
        # "account created" timestamp on User, so this is the age of the
        # user's oldest surviving refresh token instead.
        account_age_days: int | None = None
        if user.refresh_tokens:
            oldest_token = min(t.created_at for t in user.refresh_tokens.values())
            account_age_days = (dt.utcnow() - oldest_token).days

        # Credential creation age, for the never_logged_in risk factor
        # (work item 3.5): a user with credentials but no refresh tokens
        # has no account_age_days at all. The installed core's Credentials
        # model carries NO created_at field (verified against
        # homeassistant/auth/models.py), so this getattr probe yields None
        # today and only starts reporting an age if a future core adds
        # the field - risk.py's factor says "unknown age" until then.
        credential_age_days: int | None = None
        credential_created = [
            created
            for cred in user.credentials
            if (created := getattr(cred, "created_at", None)) is not None
        ]
        if credential_created:
            credential_age_days = (dt.utcnow() - min(credential_created)).days

        auth_provider_types = sorted(
            {cred.auth_provider_type for cred in user.credentials}
        )
        # Decision D-18 option (a): MFA compliance is only assessable for
        # users Home Assistant's own auth provider authenticates. A user
        # whose ONLY credentials come from a non-homeassistant provider
        # (an SSO/header-auth proxy, trusted_networks, a command-line
        # provider) may well satisfy MFA upstream where HA cannot see it,
        # so mfa_policy.py exempts them from auto_deactivate and the UI
        # reports "MFA not assessable". A user with no credentials at all
        # stays assessable - there is no external provider to defer to.
        mfa_assessable = not auth_provider_types or "homeassistant" in auth_provider_types

        mfa_modules = await self.hass.auth.async_get_enabled_mfa(user)

        return {
            "id": user.id,
            "name": user.name,
            "is_owner": user.is_owner,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "local_only": user.local_only,
            "groups": [group.id for group in user.groups],
            "mfa_enabled": bool(mfa_modules),
            "last_login_at": last_login_at,
            "last_login_ip": last_login_ip,
            "llat_count": llat_count,
            "llat_oldest_days": llat_oldest_days,
            "account_age_days": account_age_days,
            "credential_age_days": credential_age_days,
            "credentials_count": len(user.credentials),
            "refresh_token_count": len(session_tokens),
            "auth_provider_types": auth_provider_types,
            "mfa_assessable": mfa_assessable,
        }

    async def async_list_users(self) -> list[dict[str, Any]]:
        users = await self.hass.auth.async_get_users()
        return [
            await self._async_build_user_record(user)
            for user in users
            if not user.system_generated
        ]

    async def async_get_user_detail(self, user_id: str) -> dict[str, Any] | None:
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return None

        record = await self._async_build_user_record(user)
        record["refresh_tokens"] = [
            {
                "id": token.id,
                "client_id": token.client_id,
                "client_name": token.client_name,
                "token_type": token.token_type,
                "created_at": _iso(token.created_at),
                "last_used_at": _iso(token.last_used_at),
                "last_used_ip": token.last_used_ip,
            }
            for token in user.refresh_tokens.values()
        ]
        record["credentials"] = [
            {
                "id": cred.id,
                "auth_provider_type": cred.auth_provider_type,
                "auth_provider_id": cred.auth_provider_id,
                "username": cred.data.get("username")
                if cred.auth_provider_type == "homeassistant"
                else None,
            }
            for cred in user.credentials
        ]
        return record

    async def async_revoke_token(self, user_id: str, token_id: str) -> bool:
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return False

        token = user.refresh_tokens.get(token_id)
        if token is None:
            return False

        self.hass.auth.async_remove_refresh_token(token)
        return True

    async def async_revoke_all_sessions(self, user_id: str) -> dict[str, int]:
        """Revoke this user's sessions AND long-lived access tokens.

        Used as an incident-response "lock this account out now" action, so
        it must not quietly leave a compromised account's persistent API
        tokens standing — long-lived access tokens are included here, unlike
        an earlier version that skipped them. Returns a per-type breakdown so
        the UI can state exactly what was revoked rather than implying a
        clean sweep it didn't perform.
        """
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return {"sessions": 0, "long_lived_tokens": 0}

        sessions = 0
        long_lived = 0
        for token in list(user.refresh_tokens.values()):
            if token.token_type == TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN:
                long_lived += 1
            else:
                sessions += 1
            self.hass.auth.async_remove_refresh_token(token)
        return {"sessions": sessions, "long_lived_tokens": long_lived}

    async def async_revoke_interactive_sessions(self, user_id: str) -> int:
        """Revoke this user's interactive sessions, keeping long-lived tokens.

        The post-password-reset revocation (work item 4.12): a password
        reset says "whoever held the old password must be signed out", so
        every normal/webhook refresh token goes. Long-lived access tokens
        are deliberately spared here - they are not password-derived, and
        silently killing a user's automations on a routine reset would
        punish the wrong thing; revoke_all_sessions remains the
        incident-response hammer that takes those too. Returns the number
        of sessions revoked.
        """
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return 0

        revoked = 0
        for token in list(user.refresh_tokens.values()):
            if token.token_type in (TOKEN_TYPE_SYSTEM, TOKEN_TYPE_LONG_LIVED_ACCESS_TOKEN):
                continue
            self.hass.auth.async_remove_refresh_token(token)
            revoked += 1
        return revoked

    async def async_create_user(
        self,
        name: str,
        group_ids: list[str] | None = None,
        local_only: bool | None = None,
    ) -> dict[str, Any]:
        user = await self.hass.auth.async_create_user(
            name, group_ids=group_ids, local_only=local_only
        )
        return await self._async_build_user_record(user)

    async def async_update_user(self, user_id: str, **changes: Any) -> bool:
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return False

        # Defense in depth for callers outside websocket_api: the generic
        # update primitive must never be usable to deactivate the owner.
        # The dedicated deactivate method already gets this protection from
        # Home Assistant core, but async_update_user does not.
        if user.is_owner and changes.get("is_active") is False:
            return False

        try:
            await self.hass.auth.async_update_user(user, **changes)
        except (ValueError, HomeAssistantError):
            # Raised for system-generated users, among other invalid updates.
            _LOGGER.warning("Could not update user %s", user_id, exc_info=True)
            return False
        return True

    async def async_deactivate_user(self, user_id: str) -> tuple[bool, str | None]:
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return (False, "user_not_found")

        try:
            # Also revokes all of this user's refresh tokens as a side
            # effect of core's async_deactivate_user — intentional, not
            # something this method needs to duplicate.
            await self.hass.auth.async_deactivate_user(user)
        except ValueError:
            return (False, "cannot_deactivate_owner")
        return (True, None)

    async def async_delete_user(
        self, user_id: str, *, requesting_user_id: str | None = None
    ) -> tuple[bool, str | None]:
        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return (False, "user_not_found")

        # Guard the owner and self-deletion, matching the protection already
        # applied to deactivate/set_password. Core's async_remove_user does
        # NOT block removing the owner (verified), which would leave the
        # instance with no owner at all — the account this whole tool exists
        # to protect, erased through the tool itself.
        if user.is_owner:
            return (False, "cannot_delete_owner")
        if requesting_user_id is not None and user.id == requesting_user_id:
            return (False, "cannot_delete_self")

        await self.hass.auth.async_remove_user(user)
        return (True, None)

    async def async_set_password(
        self, user_id: str, new_password: str, *, requesting_user_is_owner: bool
    ) -> tuple[bool, str | None]:
        # Mirrors core's admin_change_password websocket command exactly:
        # owner-only, not merely admin-only. Do not weaken this check.
        if not requesting_user_is_owner:
            return (False, "owner_required")

        user = await self.hass.auth.async_get_user(user_id)
        if user is None:
            return (False, "user_not_found")

        credential = next(
            (c for c in user.credentials if c.auth_provider_type == "homeassistant"),
            None,
        )
        if credential is None:
            return (False, "no_homeassistant_credential")

        provider = await _async_get_ha_auth_provider(self.hass)
        username = credential.data["username"]
        await provider.async_change_password(username, new_password)
        return (True, None)


class LiveSessionRegistry:
    """In-memory tracker of currently-open websocket connections.

    No persistence: this reflects live sessions right now, not history. A
    different module (websocket_api.py) drives add()/remove()/touch() from
    the connection lifecycle of an actual websocket command.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def add(self, connection) -> str:
        key = uuid.uuid4().hex
        now = _iso(dt.utcnow())
        self._sessions[key] = {
            "user_id": connection.user.id,
            "user_name": connection.user.name,
            "refresh_token_id": connection.refresh_token_id,
            "connected_at": now,
            "last_seen": now,
        }
        return key

    def remove(self, key: str) -> None:
        self._sessions.pop(key, None)

    def touch(self, key: str) -> None:
        session = self._sessions.get(key)
        if session is None:
            return
        session["last_seen"] = _iso(dt.utcnow())

    def list_sessions(self) -> list[dict[str, Any]]:
        return [
            {"session_key": key, **session} for key, session in self._sessions.items()
        ]
