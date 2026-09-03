"""Secure configuration contract for the Probe's optional Net-SNMP agent.

Only SNMPv3 USM AuthPriv is representable.  The Probe generates a read-only
VACM view and never receives a community string or a write credential.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from typing import Any

import voluptuous as vol

from .const import (
    CONF_SNMP_AUTH_PASSPHRASE,
    CONF_SNMP_ENABLED,
    CONF_SNMP_LISTEN_ADDRESS,
    CONF_SNMP_PORT,
    CONF_SNMP_PRIV_PASSPHRASE,
    CONF_SNMP_USERNAME,
)

# Safe-token charset keeps snmpd.conf values unambiguous; 20 chars exceeds Net-SNMP's 8-char minimum.
SNMP_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,32}$")
SNMP_PASSPHRASE_PATTERN = re.compile(
    r"^[A-Za-z0-9._~!@$%^&*+=:,-]{20,128}$"
)


def snmp_ip_address(value: Any) -> str | None:
    """Return a canonical explicit listener IP, rejecting wildcard binds."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        address = ipaddress.ip_address(text)
    except ValueError as err:
        raise vol.Invalid("SNMP listener must be an IP address, not a hostname or URL") from err
    if address.is_unspecified:
        raise vol.Invalid("SNMP listener may not be a wildcard address")
    if address.is_multicast:
        raise vol.Invalid("SNMP listener may not be a multicast address")
    return str(address)


def validate_snmp_username(value: Any) -> str:
    value = str(value).strip()
    if not SNMP_USERNAME_PATTERN.fullmatch(value):
        raise vol.Invalid("SNMP username must be 1-32 letters, numbers, dots, dashes, or underscores")
    return value


def validate_snmp_passphrase(value: Any) -> str:
    value = str(value)
    if value == "":
        return value
    if not SNMP_PASSPHRASE_PATTERN.fullmatch(value):
        raise vol.Invalid(
            "SNMP passphrases must be 20-128 characters from the documented safe character set"
        )
    return value


def validate_enabled_config(settings: dict[str, Any], secrets: dict[str, str | None]) -> None:
    """Reject an enabled configuration that cannot enforce AuthPriv."""
    if not settings.get(CONF_SNMP_ENABLED, False):
        return
    missing = [
        key
        for key in (CONF_SNMP_LISTEN_ADDRESS, CONF_SNMP_USERNAME)
        if not settings.get(key)
    ]
    missing.extend(
        key
        for key in (CONF_SNMP_AUTH_PASSPHRASE, CONF_SNMP_PRIV_PASSPHRASE)
        if not secrets.get(key)
    )
    if missing:
        raise vol.Invalid("SNMPv3 cannot be enabled until all listener and AuthPriv fields are configured")
    if secrets[CONF_SNMP_AUTH_PASSPHRASE] == secrets[CONF_SNMP_PRIV_PASSPHRASE]:
        raise vol.Invalid("SNMP authentication and privacy passphrases must be different")


async def async_config_for_probe(settings: dict[str, Any], secret_store) -> dict[str, Any]:
    """Build the authenticated Probe response, including a change token."""
    secrets = {
        CONF_SNMP_AUTH_PASSPHRASE: await secret_store.async_get(CONF_SNMP_AUTH_PASSPHRASE),
        CONF_SNMP_PRIV_PASSPHRASE: await secret_store.async_get(CONF_SNMP_PRIV_PASSPHRASE),
    }
    enabled = bool(settings.get(CONF_SNMP_ENABLED, False))
    if enabled:
        validate_enabled_config(settings, secrets)
    material = {
        "enabled": enabled,
        "listen_address": settings.get(CONF_SNMP_LISTEN_ADDRESS),
        "port": settings.get(CONF_SNMP_PORT, 161),
        "username": settings.get(CONF_SNMP_USERNAME),
        # Dormant credentials are never transmitted; delivered only with an enabled config.
        "auth_passphrase": secrets[CONF_SNMP_AUTH_PASSPHRASE] if enabled else None,
        "priv_passphrase": secrets[CONF_SNMP_PRIV_PASSPHRASE] if enabled else None,
        "auth_protocol": "SHA-256",
        "privacy_protocol": "AES-128",
    }
    generation = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {**material, "generation": generation}
