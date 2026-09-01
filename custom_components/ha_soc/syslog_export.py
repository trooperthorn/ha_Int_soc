"""Best-effort Syslog/SIEM export of finalized audit records.

Records enter this exporter only after the local JSONL append succeeds and
the audit hash/sequence fields are assigned. RFC 5424 JSON remains the default;
CEF 0 in RFC 5424 and bare canonical JSON are selectable compatibility modes.
TCP and TLS retain RFC 6587 octet counting, and UDP sends one message per
datagram. Delivery is bounded and non-blocking, while sequence numbers let the
SIEM detect any queue loss.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from copy import deepcopy
from datetime import datetime, timezone
import ipaddress
import json
import logging
import re
import ssl
from typing import Any, TypedDict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_SYSLOG_FACILITY,
    CONF_SYSLOG_FORMAT,
    CONF_SYSLOG_HOST,
    CONF_SYSLOG_PORT,
    CONF_SYSLOG_TLS_VERIFY,
    CONF_SYSLOG_TRANSPORT,
    DEFAULT_SYSLOG_FACILITY,
    DEFAULT_SYSLOG_FORMAT,
    DEFAULT_SYSLOG_PORT,
    DEFAULT_SYSLOG_TLS_VERIFY,
    DEFAULT_SYSLOG_TRANSPORT,
    SYSLOG_TRANSPORT_DISABLED,
    SYSLOG_TRANSPORT_TCP,
    SYSLOG_TRANSPORT_TLS,
    SYSLOG_TRANSPORT_UDP,
    SYSLOG_FORMAT_CEF,
    SYSLOG_FORMAT_RAW_JSON,
    SYSLOG_FORMATS,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_QUEUE_MAX = 2_000
_MESSAGE_MAX_BYTES = 32 * 1024
_CONNECT_TIMEOUT = 10
_SD_ID = "ha_soc@32473"
_HEADER_SAFE = re.compile(r"[^\x21-\x7e]")
_CEF_EVENT_ID_UNSAFE = re.compile(r"[^A-Za-z0-9_.:-]")

_CEF_EVENT_NAMES = {
    "area_registry_change": "Area Registry Change",
    "audit_chain_reset": "Audit Chain Reset",
    "category_registry_change": "Category Registry Change",
    "config_entry_change": "Configuration Entry Change",
    "core_config_change": "Core Configuration Change",
    "dashboard_panels_change": "Dashboard Panel Set Change",
    "detection_status_changed": "Detection Status Change",
    "device_registry_change": "Device Registry Change",
    "entity_registry_change": "Entity Registry Change",
    "firewall_pending_discarded": "Pending Firewall Change Discarded",
    "firewall_resolved": "Firewall Change Resolved",
    "floor_registry_change": "Floor Registry Change",
    "label_registry_change": "Label Registry Change",
    "login_fail": "Failed Login",
    "login_ok": "Successful Login",
    "lovelace_change": "Dashboard Change",
    "privileged_read": "Privileged Read",
    "probe_auth_rejected": "Probe Authentication Rejected",
    "service_call": "Service Call Attempted",
    "session_seen": "Session Observed",
    "soc_config_change": "HA SOC Configuration Change",
    "token_created": "Access Token Created",
    "user_added": "User Added",
    "user_removed": "User Removed",
    "user_updated": "User Updated",
    "watchdog_triggered": "Resource Watchdog Triggered",
}

_CEF_VERY_HIGH_10 = {"audit_chain_reset"}
_CEF_VERY_HIGH_9 = {"probe_auth_rejected"}
_CEF_HIGH_7 = {
    "firewall_pending_discarded",
    "login_fail",
    "user_deactivated",
    "user_removed",
}
_CEF_MEDIUM_5 = {
    "detection_status_changed",
    "firewall_resolved",
    "privileged_read",
    "token_created",
    "user_added",
    "user_updated",
    "watchdog_triggered",
}


class _QueuedMessage(TypedDict):
    """A record plus the payload format selected when it was enqueued."""

    record: dict[str, Any]
    payload_format: str


def _header_token(value: Any, fallback: str = "-") -> str:
    text = _HEADER_SAFE.sub("_", str(value or "")).replace(" ", "_")
    return text[:48] or fallback


def _sd_value(value: Any) -> str:
    return str(value if value is not None else "-").replace("\\", "\\\\").replace('"', '\\"').replace("]", "\\]")


def _severity(record: dict[str, Any]) -> int:
    category = str(record.get("category") or "")
    if category in {"audit_chain_reset", "probe_auth_rejected"}:
        return 3  # error
    if category in {"login_fail", "user_removed", "user_deactivated"}:
        return 4  # warning
    if category.endswith("_change") or category == "soc_config_change":
        return 5  # notice
    return 6  # informational


def _rfc5424_prefix(record: dict[str, Any], facility: int) -> str:
    """Return the common RFC 5424 envelope prefix through structured data."""
    pri = facility * 8 + _severity(record)
    timestamp = str(record.get("ts") or datetime.now(timezone.utc).isoformat())
    msg_id = _header_token(record.get("category"), "ha_soc")
    sd = (
        f'[{_SD_ID} seq="{_sd_value(record.get("seq"))}" '
        f'hash="{_sd_value(record.get("hash"))}" '
        f'category="{_sd_value(record.get("category"))}"]'
    )
    return f"<{pri}>1 {timestamp} homeassistant ha-soc - {msg_id} {sd} "


def _compact_record(record: dict[str, Any], original_bytes: int) -> dict[str, Any]:
    """Retain chain evidence and attribution when a JSON record is oversized."""
    compact = {
        key: record.get(key)
        for key in (
            "ts",
            "seq",
            "hash",
            "prev_hash",
            "category",
            "user_id",
            "domain",
            "service",
            "ip",
        )
    }
    compact["detail"] = {"truncated": True, "original_bytes": original_bytes}
    return compact


def _canonical_json(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"))


def format_rfc5424(record: dict[str, Any], facility: int) -> bytes:
    """Return one bounded RFC 5424 message containing canonical JSON."""
    payload_record = deepcopy(record)
    payload = _canonical_json(payload_record)
    prefix = _rfc5424_prefix(record, facility)
    encoded = (prefix + payload).encode("utf-8", errors="replace")
    if len(encoded) <= _MESSAGE_MAX_BYTES:
        return encoded

    # Preserve the chain identifiers and top-level attribution while
    # dropping an oversized detail object; never byte-slice invalid JSON.
    payload = _canonical_json(_compact_record(payload_record, len(encoded)))
    return (prefix + payload).encode("utf-8", errors="replace")


def format_raw_json(record: dict[str, Any]) -> bytes:
    """Return bounded canonical JSON without an RFC 5424 envelope."""
    payload_record = deepcopy(record)
    encoded = _canonical_json(payload_record).encode("utf-8", errors="replace")
    if len(encoded) <= _MESSAGE_MAX_BYTES:
        return encoded
    compact = _compact_record(payload_record, len(encoded))
    return _canonical_json(compact).encode("utf-8", errors="replace")


def _cef_escape(value: Any, *, header: bool, max_length: int) -> str:
    """Escape and bound one CEF value without splitting an escape sequence."""
    output: list[str] = []
    length = 0
    for character in str(value if value is not None else ""):
        if character == "\\":
            escaped = "\\\\"
        elif header and character == "|":
            escaped = "\\|"
        elif not header and character == "=":
            escaped = "\\="
        elif character == "\r":
            escaped = "\\r"
        elif character == "\n":
            escaped = "\\n"
        elif ord(character) < 0x20 or ord(character) == 0x7F:
            escaped = " "
        else:
            escaped = character
        if length + len(escaped) > max_length:
            break
        output.append(escaped)
        length += len(escaped)
    return "".join(output)


def _cef_header_value(value: Any, max_length: int) -> str:
    return _cef_escape(value, header=True, max_length=max_length) or "-"


def _cef_extension_value(value: Any, max_length: int) -> str:
    return _cef_escape(value, header=False, max_length=max_length)


def _cef_event_class_id(record: dict[str, Any]) -> str:
    category = str(record.get("category") or "unknown")
    safe_category = _CEF_EVENT_ID_UNSAFE.sub("_", category).strip("._:-")
    return f"ha_soc.{safe_category[:240] or 'unknown'}"


def _cef_event_name(record: dict[str, Any]) -> str:
    category = str(record.get("category") or "unknown")
    if category in _CEF_EVENT_NAMES:
        return _CEF_EVENT_NAMES[category]
    safe_category = _CEF_EVENT_ID_UNSAFE.sub("_", category)
    return safe_category.replace("_", " ").strip().title() or "Unknown HA SOC Event"


def _cef_severity(record: dict[str, Any]) -> int:
    """Return CEF's 0-10 severity, independent of the Syslog PRI severity."""
    category = str(record.get("category") or "")
    if category in _CEF_VERY_HIGH_10:
        return 10
    if category in _CEF_VERY_HIGH_9:
        return 9
    if category in _CEF_HIGH_7:
        return 7
    if category in _CEF_MEDIUM_5 or category.endswith("_change"):
        return 5
    if category in {"login_ok", "service_call", "session_seen"}:
        return 3
    return 4


def _epoch_milliseconds(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return str(int(parsed.timestamp() * 1000))


def _cef_detail(record: dict[str, Any], *, truncated_bytes: int | None = None) -> str:
    if truncated_bytes is not None:
        detail: Any = {"original_bytes": truncated_bytes, "truncated": True}
    else:
        detail = record.get("detail") or {}
    serialized = _canonical_json(detail) if isinstance(detail, dict) else str(detail)
    escaped = _cef_extension_value(serialized, 1023)
    complete = _cef_extension_value(serialized, len(serialized) * 2 + 1)
    if len(escaped) == len(complete):
        return serialized
    summary = _canonical_json(
        {"original_characters": len(serialized), "truncated": True}
    )
    return summary


def _cef_extension(record: dict[str, Any], *, truncated_bytes: int | None = None) -> str:
    """Map a finalized HA SOC audit record to deterministic CEF 0 fields."""
    fields: list[tuple[str, Any, int]] = []
    timestamp = _epoch_milliseconds(record.get("ts"))
    if timestamp is not None:
        fields.extend((("rt", timestamp, 32), ("start", timestamp, 32)))

    category = str(record.get("category") or "unknown")
    fields.append(("cat", category, 1023))

    domain = record.get("domain")
    service = record.get("service")
    if domain or service:
        action = ".".join(str(value) for value in (domain, service) if value)
        fields.append(("act", action, 63))

    if category == "login_ok":
        fields.append(("outcome", "success", 63))
    elif category in {"login_fail", "probe_auth_rejected"}:
        fields.append(("outcome", "failure", 63))

    raw_ip = record.get("ip")
    if raw_ip:
        try:
            address = ipaddress.ip_address(str(raw_ip))
        except ValueError:
            address = None
        if isinstance(address, ipaddress.IPv4Address):
            fields.append(("src", str(address), 45))
        elif isinstance(address, ipaddress.IPv6Address):
            fields.extend(
                (("c6a1Label", "Source IPv6", 1023), ("c6a1", str(address), 45))
            )

    if record.get("user_id") is not None:
        fields.append(("suid", record["user_id"], 1023))
    detail = record.get("detail")
    if isinstance(detail, dict) and detail.get("target_user_id") is not None:
        fields.append(("duid", detail["target_user_id"], 1023))
    if record.get("attempted_user") is not None:
        fields.append(("duser", record["attempted_user"], 1023))
    elif isinstance(detail, dict) and detail.get("target_name") is not None:
        fields.append(("duser", detail["target_name"], 1023))

    if record.get("seq") is not None:
        fields.extend(
            (("cn1Label", "Audit Sequence", 1023), ("cn1", record["seq"], 32))
        )
    if record.get("hash") is not None:
        fields.extend(
            (("cs1Label", "Audit Hash", 1023), ("cs1", record["hash"], 4000))
        )
    if record.get("prev_hash") is not None:
        fields.extend(
            (
                ("cs2Label", "Previous Audit Hash", 1023),
                ("cs2", record["prev_hash"], 4000),
            )
        )
    if record.get("context_id") is not None:
        fields.extend(
            (
                ("cs3Label", "HA Context ID", 1023),
                ("cs3", record["context_id"], 4000),
            )
        )
    if record.get("context_parent_id") is not None:
        fields.extend(
            (
                ("cs4Label", "HA Parent Context ID", 1023),
                ("cs4", record["context_parent_id"], 4000),
            )
        )
    if record.get("entity_ids"):
        entity_ids = json.dumps(record["entity_ids"], separators=(",", ":"))
        fields.extend(
            (
                ("cs5Label", "Entity IDs", 1023),
                ("cs5", entity_ids, 4000),
            )
        )

    fields.append(("msg", _cef_detail(record, truncated_bytes=truncated_bytes), 1023))
    return " ".join(
        f"{key}={_cef_extension_value(value, limit)}"
        for key, value, limit in fields
    )


def format_cef_payload(
    record: dict[str, Any], integration_version: str, *, truncated_bytes: int | None = None
) -> str:
    """Return one genuine CEF 0 payload for a finalized HA SOC record."""
    return (
        "CEF:0|Home Assistant|HA SOC|"
        f"{_cef_header_value(integration_version, 31)}|"
        f"{_cef_header_value(_cef_event_class_id(record), 1023)}|"
        f"{_cef_header_value(_cef_event_name(record), 512)}|"
        f"{_cef_severity(record)}|"
        f"{_cef_extension(record, truncated_bytes=truncated_bytes)}"
    )


def format_rfc5424_cef(
    record: dict[str, Any], facility: int, integration_version: str
) -> bytes:
    """Return one bounded RFC 5424 message containing a CEF 0 payload."""
    prefix = _rfc5424_prefix(record, facility)
    payload = format_cef_payload(record, integration_version)
    encoded = (prefix + payload).encode("utf-8", errors="replace")
    if len(encoded) <= _MESSAGE_MAX_BYTES:
        return encoded
    payload = format_cef_payload(
        record, integration_version, truncated_bytes=len(encoded)
    )
    return (prefix + payload).encode("utf-8", errors="replace")


def format_syslog_message(
    record: dict[str, Any],
    facility: int,
    payload_format: str,
    integration_version: str,
) -> bytes:
    """Dispatch a record to the configured, validated payload formatter."""
    if payload_format == SYSLOG_FORMAT_CEF:
        return format_rfc5424_cef(record, facility, integration_version)
    if payload_format == SYSLOG_FORMAT_RAW_JSON:
        return format_raw_json(record)
    return format_rfc5424(record, facility)


def frame_rfc6587(message: bytes) -> bytes:
    """RFC 6587 octet-counting frame for TCP/TLS transports."""
    return str(len(message)).encode("ascii") + b" " + message


class SyslogExporter:
    """Lifecycle-managed, bounded Syslog delivery worker."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: HaSocData,
        integration_version: str = "-",
    ) -> None:
        self.hass = hass
        self._store = store
        self._integration_version = integration_version
        self._entry: ConfigEntry | None = None
        self._queue: asyncio.Queue[_QueuedMessage] = asyncio.Queue(_QUEUE_MAX)
        self._task: asyncio.Task[None] | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._udp_transport: asyncio.DatagramTransport | None = None
        self._sent = 0
        self._dropped = 0
        self._last_sent_at: str | None = None
        self._last_error: str | None = None

    @property
    def _settings(self) -> dict[str, Any]:
        return self._store.settings

    @property
    def enabled(self) -> bool:
        return self._settings.get(CONF_SYSLOG_TRANSPORT, DEFAULT_SYSLOG_TRANSPORT) != SYSLOG_TRANSPORT_DISABLED

    @property
    def ready(self) -> bool:
        return self.enabled and bool((self._settings.get(CONF_SYSLOG_HOST) or "").strip())

    @property
    def status(self) -> dict[str, Any]:
        transport = self._settings.get(CONF_SYSLOG_TRANSPORT, DEFAULT_SYSLOG_TRANSPORT)
        payload_format = self._settings.get(CONF_SYSLOG_FORMAT, DEFAULT_SYSLOG_FORMAT)
        if payload_format not in SYSLOG_FORMATS:
            payload_format = DEFAULT_SYSLOG_FORMAT
        host = (self._settings.get(CONF_SYSLOG_HOST) or "").strip()
        return {
            "enabled": transport != SYSLOG_TRANSPORT_DISABLED,
            "transport": transport,
            "format": payload_format,
            "host_configured": bool(host),
            "connected": bool(self._writer is not None or self._udp_transport is not None),
            "queued": self._queue.qsize(),
            "sent": self._sent,
            "dropped": self._dropped,
            "last_sent_at": self._last_sent_at,
            "last_error": self._last_error,
        }

    @callback
    def async_start(self, entry: ConfigEntry) -> None:
        self._entry = entry
        if not self.enabled or self._task is not None:
            return
        if not (self._settings.get(CONF_SYSLOG_HOST) or "").strip():
            self._last_error = "Syslog transport is enabled but no destination host is configured."
            return
        self._last_error = None
        self._task = entry.async_create_background_task(
            self.hass, self._async_worker(), "HA SOC Syslog exporter"
        )

    async def async_reconfigure(self) -> None:
        await self.async_stop()
        if self._entry is not None:
            self.async_start(self._entry)

    async def async_stop(self, *, drain: bool = False) -> None:
        if drain and self._task is not None and not self._queue.empty():
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._queue.join(), timeout=5)
        task, self._task = self._task, None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._async_close_connection()

    @callback
    def async_enqueue(self, records: list[dict[str, Any]]) -> None:
        if not self.ready:
            return
        payload_format = self._settings.get(CONF_SYSLOG_FORMAT, DEFAULT_SYSLOG_FORMAT)
        if payload_format not in SYSLOG_FORMATS:
            payload_format = DEFAULT_SYSLOG_FORMAT
        for record in records:
            item = _QueuedMessage(
                record=deepcopy(record), payload_format=str(payload_format)
            )
            try:
                self._queue.put_nowait(item)
            except asyncio.QueueFull:
                self._dropped += 1
                _LOGGER.error(
                    "HA SOC Syslog queue full; dropped audit seq %s",
                    record.get("seq"),
                )

    async def _async_worker(self) -> None:
        retry_delay = 1
        while True:
            item = await self._queue.get()
            record = item["record"]
            delivered = False
            try:
                while True:
                    try:
                        await self._async_send(item)
                    except (OSError, ssl.SSLError, asyncio.TimeoutError) as err:
                        self._last_error = f"{type(err).__name__}: {err}"
                        await self._async_close_connection()
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 60)
                        continue
                    self._sent += 1
                    self._last_sent_at = datetime.now(timezone.utc).isoformat()
                    self._last_error = None
                    retry_delay = 1
                    delivered = True
                    break
            finally:
                # Reconfiguration/unload can cancel a send after Queue.get.
                # Put that in-flight record back before marking the original
                # queue item done so no sequence disappears silently.
                if not delivered:
                    try:
                        self._queue.put_nowait(item)
                    except asyncio.QueueFull:
                        # Producers can fill the slot while a send is in
                        # flight. Preserve bounded memory and expose the loss
                        # through both the counter and the audit sequence gap.
                        self._dropped += 1
                        self._last_error = (
                            "Syslog queue filled while preserving an in-flight record."
                        )
                        _LOGGER.error(
                            "HA SOC Syslog queue full during shutdown; dropped audit seq %s",
                            record.get("seq"),
                        )
                self._queue.task_done()

    async def _async_send(self, item: _QueuedMessage) -> None:
        settings = self._settings
        record = item["record"]
        transport = settings.get(CONF_SYSLOG_TRANSPORT, DEFAULT_SYSLOG_TRANSPORT)
        host = (settings.get(CONF_SYSLOG_HOST) or "").strip()
        port = int(settings.get(CONF_SYSLOG_PORT, DEFAULT_SYSLOG_PORT))
        facility = int(settings.get(CONF_SYSLOG_FACILITY, DEFAULT_SYSLOG_FACILITY))
        message = format_syslog_message(
            record,
            facility,
            item["payload_format"],
            self._integration_version,
        )

        if transport == SYSLOG_TRANSPORT_UDP:
            if self._udp_transport is None:
                loop = asyncio.get_running_loop()
                endpoint = loop.create_datagram_endpoint(
                    asyncio.DatagramProtocol, remote_addr=(host, port)
                )
                self._udp_transport, _ = await asyncio.wait_for(
                    endpoint, timeout=_CONNECT_TIMEOUT
                )
            self._udp_transport.sendto(message)
            await asyncio.sleep(0)
            return

        if self._writer is None:
            ssl_context: ssl.SSLContext | None = None
            server_hostname: str | None = None
            if transport == SYSLOG_TRANSPORT_TLS:
                verify = bool(
                    settings.get(CONF_SYSLOG_TLS_VERIFY, DEFAULT_SYSLOG_TLS_VERIFY)
                )
                if verify:
                    ssl_context = ssl.create_default_context()
                    server_hostname = host
                else:
                    # Explicit compatibility mode for today's self-signed
                    # certificates. The UI labels this unverified and TLS
                    # verification remains the secure default.
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE  # nosec B323
            _reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host,
                    port,
                    ssl=ssl_context,
                    server_hostname=server_hostname,
                ),
                timeout=_CONNECT_TIMEOUT,
            )
        self._writer.write(frame_rfc6587(message))
        await asyncio.wait_for(self._writer.drain(), timeout=_CONNECT_TIMEOUT)

    async def _async_close_connection(self) -> None:
        if self._udp_transport is not None:
            self._udp_transport.close()
            self._udp_transport = None
        if self._writer is not None:
            self._writer.close()
            with suppress(OSError, ssl.SSLError):
                await self._writer.wait_closed()
            self._writer = None
