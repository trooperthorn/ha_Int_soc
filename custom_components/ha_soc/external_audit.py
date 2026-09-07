"""Ingest of hash-chained audit records from other tools on the host.

The Elk Programmer app keeps its own hash-chained audit log; this service
lets it, and any tool following the same contract, hand those records to
HA SOC so one place holds the history. Each source's chain is verified on
receipt against the head HA SOC last accepted, so a break in the source's
log, or records it never delivered, is visible here even if the source's own
file is edited. The
caller must be the Supervisor (an app on this host reaching Core through
the Supervisor's proxy) and must present the per-source secret pinned on
the source's first call, the same two gates the Probe passes. See
docs/protocol.md, "External audit ingest".
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.hassio import is_hassio
import homeassistant.util.dt as dt_util

from .const import DOMAIN
from .probe import async_supervisor_call_rejection
from .secrets_store import EXTERNAL_AUDIT_SECRETS_KEY, HaSocSecretStore
from .store import HaSocData

if TYPE_CHECKING:
    from .audit import AuditLog

_LOGGER = logging.getLogger(__name__)

SERVICE_INGEST_AUDIT = "ingest_audit"
CATEGORY_RECORD = "external_audit"
CATEGORY_CHAIN_BREAK = "external_audit_chain_break"
CATEGORY_REJECTED = "external_audit_rejected"
RECORDS_PER_CALL_MAX = 200
DETAILS_MAX_BYTES = 8192

_SOURCE_RE = r"^[a-z][a-z0-9_]{0,31}$"
_HASH_RE = r"^[0-9a-f]{64}$"

RECORD_SCHEMA = vol.Schema(
    {
        vol.Required("seq"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Required("time"): vol.All(str, vol.Length(max=64)),
        vol.Required("event"): vol.All(str, vol.Length(min=1, max=64)),
        vol.Optional("user_id"): vol.Any(None, vol.All(str, vol.Length(max=128))),
        vol.Optional("user_name"): vol.Any(None, vol.All(str, vol.Length(max=128))),
        vol.Optional("details", default=dict): dict,
        vol.Required("previous"): vol.Any("", vol.Match(_HASH_RE)),
        vol.Required("hash"): vol.Match(_HASH_RE),
    }
)

INGEST_AUDIT_SCHEMA = vol.Schema(
    {
        vol.Required("source"): vol.Match(_SOURCE_RE),
        vol.Required("secret"): vol.All(str, vol.Length(min=16, max=256)),
        vol.Required("records"): vol.All(
            [RECORD_SCHEMA], vol.Length(min=1, max=RECORDS_PER_CALL_MAX)
        ),
    }
)


def record_digest(record: dict[str, Any]) -> str:
    """The hash a well-formed source computes for a record.

    Content is the record without ``hash`` and with ``previous`` inside it;
    the digest is SHA-256 over the canonical compact JSON of that content
    followed by ``previous`` again. This is exactly what the Elk Programmer
    writes, so its files verify unchanged.
    """
    content = {
        "time": record["time"],
        "event": record["event"],
        "user_id": record.get("user_id"),
        "user_name": record.get("user_name"),
        "details": record.get("details") or {},
        "previous": record["previous"],
    }
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256((canonical + record["previous"]).encode("utf-8")).hexdigest()


async def _async_source_secret_ok(
    secrets: HaSocSecretStore, source: str, presented: str
) -> bool:
    """Per-source trust-on-first-use secret, kept as one JSON map in the secret store."""
    raw = await secrets.async_get(EXTERNAL_AUDIT_SECRETS_KEY)
    try:
        table: dict[str, str] = json.loads(raw) if raw else {}
    except ValueError:
        table = {}
    pinned = table.get(source)
    if pinned is None:
        table[source] = presented
        await secrets.async_set(EXTERNAL_AUDIT_SECRETS_KEY, json.dumps(table, sort_keys=True))
        _LOGGER.info("HA SOC: pinned the audit ingest secret for source %s (first call).", source)
        return True
    return hmac.compare_digest(presented, pinned)


def async_register_external_audit_service(
    hass: HomeAssistant, store: HaSocData, audit: AuditLog, secrets: HaSocSecretStore
) -> None:
    """Register ``ha_soc.ingest_audit``; nothing on a non-Supervisor install."""
    if not is_hassio(hass):
        _LOGGER.debug("HA SOC: not a Supervisor install; ingest_audit is not registered.")
        return

    async def _handle(call: ServiceCall) -> dict[str, Any]:
        source = call.data["source"]
        reason = await async_supervisor_call_rejection(hass, store, call)
        if reason is None and not await _async_source_secret_ok(
            secrets, source, call.data["secret"]
        ):
            reason = "bad_secret"
        if reason is not None:
            audit.async_log(
                CATEGORY_REJECTED,
                user_id=call.context.user_id,
                detail={"source": source, "caller_user_id": call.context.user_id, "reason": reason},
            )
            return {"accepted": 0, "last_seq": None, "rejected": reason}

        head = store.external_audit_head(source)
        last_seq = int(head["seq"]) if head else 0
        last_hash = str(head["hash"]) if head else ""
        accepted = 0
        rejected: str | None = None
        for record in call.data["records"]:
            seq = int(record["seq"])
            if seq <= last_seq:
                # A replay of something already accepted is harmless; a different
                # record under an accepted sequence number is a rewritten history.
                if seq == last_seq and record["hash"] != last_hash:
                    rejected = "rewritten_history"
                    break
                continue
            if seq > last_seq + 1:
                # The link to the missing records cannot be verified; the source
                # resends from last_seq + 1 (the response says where to start).
                rejected = "gap"
                break
            if last_seq and record["previous"] != last_hash:
                rejected = "previous_hash_mismatch"
                break
            if record_digest(record) != record["hash"]:
                rejected = "hash_mismatch"
                break
            if len(json.dumps(record.get("details") or {})) > DETAILS_MAX_BYTES:
                rejected = "details_too_large"
                break
            audit.async_log(
                CATEGORY_RECORD,
                user_id=record.get("user_id"),
                detail={
                    "source": source,
                    "source_seq": seq,
                    "source_hash": record["hash"],
                    "source_time": record["time"],
                    "event": record["event"],
                    "user_name": record.get("user_name"),
                    "details": record.get("details") or {},
                },
            )
            last_seq, last_hash = seq, record["hash"]
            accepted += 1

        if accepted:
            store.async_set_external_audit_head(
                source, {"seq": last_seq, "hash": last_hash, "at": dt_util.utcnow().isoformat()}
            )
        if rejected is not None:
            audit.async_log(
                CATEGORY_CHAIN_BREAK,
                user_id=call.context.user_id,
                detail={
                    "source": source,
                    "reason": rejected,
                    "accepted_before_break": accepted,
                    "head_seq": last_seq,
                    "expected_seq": last_seq + 1,
                },
            )
        return {"accepted": accepted, "last_seq": last_seq or None, "rejected": rejected}

    hass.services.async_register(
        DOMAIN,
        SERVICE_INGEST_AUDIT,
        _handle,
        schema=INGEST_AUDIT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unregister_external_audit_service(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_INGEST_AUDIT):
        hass.services.async_remove(DOMAIN, SERVICE_INGEST_AUDIT)
