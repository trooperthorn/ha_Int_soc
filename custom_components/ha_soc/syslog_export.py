"""Best-effort RFC 5424 export of finalized audit records to a SIEM.

Records enter this exporter only after the local JSONL append succeeds and
the audit hash/sequence fields are assigned.  TCP and TLS use RFC 6587 octet
counting; UDP sends one RFC 5424 message per datagram.  Delivery is bounded
and non-blocking, while sequence numbers let the SIEM detect any queue loss.
"""
from __future__ import annotations

import asyncio
from contextlib import suppress
from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
import re
import ssl
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_SYSLOG_FACILITY,
    CONF_SYSLOG_HOST,
    CONF_SYSLOG_PORT,
    CONF_SYSLOG_TLS_VERIFY,
    CONF_SYSLOG_TRANSPORT,
    DEFAULT_SYSLOG_FACILITY,
    DEFAULT_SYSLOG_PORT,
    DEFAULT_SYSLOG_TLS_VERIFY,
    DEFAULT_SYSLOG_TRANSPORT,
    SYSLOG_TRANSPORT_DISABLED,
    SYSLOG_TRANSPORT_TCP,
    SYSLOG_TRANSPORT_TLS,
    SYSLOG_TRANSPORT_UDP,
)
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

_QUEUE_MAX = 2_000
_MESSAGE_MAX_BYTES = 32 * 1024
_CONNECT_TIMEOUT = 10
_SD_ID = "ha_soc@32473"
_HEADER_SAFE = re.compile(r"[^\x21-\x7e]")


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


def format_rfc5424(record: dict[str, Any], facility: int) -> bytes:
    """Return one bounded RFC 5424 message containing canonical JSON."""
    payload_record = deepcopy(record)
    payload = json.dumps(payload_record, sort_keys=True, separators=(",", ":"))
    pri = facility * 8 + _severity(record)
    timestamp = str(record.get("ts") or datetime.now(timezone.utc).isoformat())
    msg_id = _header_token(record.get("category"), "ha_soc")
    sd = (
        f'[{_SD_ID} seq="{_sd_value(record.get("seq"))}" '
        f'hash="{_sd_value(record.get("hash"))}" '
        f'category="{_sd_value(record.get("category"))}"]'
    )
    prefix = f"<{pri}>1 {timestamp} homeassistant ha-soc - {msg_id} {sd} "
    encoded = (prefix + payload).encode("utf-8", errors="replace")
    if len(encoded) <= _MESSAGE_MAX_BYTES:
        return encoded

    # Preserve the chain identifiers and top-level attribution while
    # dropping an oversized detail object; never byte-slice invalid JSON.
    compact = {
        key: payload_record.get(key)
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
    compact["detail"] = {"truncated": True, "original_bytes": len(encoded)}
    payload = json.dumps(compact, sort_keys=True, separators=(",", ":"))
    return (prefix + payload).encode("utf-8", errors="replace")


def frame_rfc6587(message: bytes) -> bytes:
    """RFC 6587 octet-counting frame for TCP/TLS transports."""
    return str(len(message)).encode("ascii") + b" " + message


class SyslogExporter:
    """Lifecycle-managed, bounded Syslog delivery worker."""

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self._store = store
        self._entry: ConfigEntry | None = None
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(_QUEUE_MAX)
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
        host = (self._settings.get(CONF_SYSLOG_HOST) or "").strip()
        return {
            "enabled": transport != SYSLOG_TRANSPORT_DISABLED,
            "transport": transport,
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
        for record in records:
            try:
                self._queue.put_nowait(deepcopy(record))
            except asyncio.QueueFull:
                self._dropped += 1
                _LOGGER.error(
                    "HA SOC Syslog queue full; dropped audit seq %s",
                    record.get("seq"),
                )

    async def _async_worker(self) -> None:
        retry_delay = 1
        while True:
            record = await self._queue.get()
            delivered = False
            try:
                while True:
                    try:
                        await self._async_send(record)
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
                        self._queue.put_nowait(record)
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

    async def _async_send(self, record: dict[str, Any]) -> None:
        settings = self._settings
        transport = settings.get(CONF_SYSLOG_TRANSPORT, DEFAULT_SYSLOG_TRANSPORT)
        host = (settings.get(CONF_SYSLOG_HOST) or "").strip()
        port = int(settings.get(CONF_SYSLOG_PORT, DEFAULT_SYSLOG_PORT))
        facility = int(settings.get(CONF_SYSLOG_FACILITY, DEFAULT_SYSLOG_FACILITY))
        message = format_rfc5424(record, facility)

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
