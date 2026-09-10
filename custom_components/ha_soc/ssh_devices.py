"""Read-only SSH collection from UniFi devices, using controller-pushed keys.

UniFi's controller distributes an authorized public key to every adopted
device and re-pushes it on provisioning, so one keypair reaches the whole
estate and no per-device password is ever stored. HA SOC generates the pair,
keeps the private half in the private secret store, and shows the public half
for pasting into the controller once.

Nothing here writes to a device. Commands come from a fixed allowlist; there
is no path from a client-supplied string to a shell.

The key the controller distributes is nonetheless an ordinary shell login, and
the device enforces no restriction on it: the controller owns the
authorized_keys entry and the Integration API has no key-management route, so
no command= or restrict option can be attached from this side. Read-only, and
only the files in READABLE_PATHS, is this module's restraint and nothing
else's. Scope, the host-key rule, and why this lives in HA SOC rather than the
diagnostics sibling are in docs/design.md and docs/decisions.md.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
from typing import Any

import homeassistant.util.dt as dt_util

from homeassistant.core import HomeAssistant

from . import unifi_ap_log

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 10
COMMAND_TIMEOUT_SECONDS = 15
MAX_OUTPUT_BYTES = 256 * 1024

SECRET_SSH_PRIVATE_KEY = "ssh_private_key"

AUDIT_CATEGORY_RUN = "ssh_device_command"
AUDIT_CATEGORY_KEY = "ssh_key_change"
AUDIT_CATEGORY_HOST_KEY = "ssh_host_key_changed"

# Coded refusals; the panel branches on these.
ERR_DISABLED = "ssh_collection_disabled"
ERR_NO_KEY = "no_keypair"
ERR_NO_USERNAME = "no_username"
ERR_BAD_HOST = "invalid_host"
ERR_UNKNOWN_COMMAND = "unknown_command"
ERR_HOST_KEY_CHANGED = "host_key_changed"
ERR_AUTH = "auth_failed"
ERR_UNREACHABLE = "unreachable"

# Four-state result model: a check that could not run is "unknown", never
# "fail". A command that ran and returned non-zero is "fail"; one that could
# not be attempted, or whose tool is absent, is "unknown".
STATE_PASS = "pass"
STATE_FAIL = "fail"
STATE_UNKNOWN = "unknown"


class SshDeviceError(Exception):
    """A refusal carrying the code the panel branches on."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class Command:
    """One allowlisted read-only command.

    ``verified`` records whether the command's output has been seen on real
    hardware in this estate. An unverified command that fails returns
    ``unknown``, because "this device does not have that tool" and "this
    device is broken" are different answers and the collector cannot yet tell
    them apart.
    """

    def __init__(self, command_id: str, argv: str, description: str, *, verified: bool) -> None:
        self.id = command_id
        self.argv = argv
        self.description = description
        self.verified = verified


# Every file the allowlist is permitted to read, in full.
#
# This set exists because of what the credential actually is. The key the
# controller distributes is an ordinary shell login, so the device enforces
# nothing: "read-only, and only these files" is this module's restraint and
# nobody else's, and the allowlist already contains `cat` and `tail`, which
# will read whatever path they are given. Without an explicit set, a later
# entry reaching for /etc/shadow, a stored private key, or a wireless
# passphrase file would look exactly like the entries already here.
#
# Adding a path is a deliberate edit with a reason, the same as adding a
# command. _assert_reads_are_allowlisted refuses at import time otherwise, so
# a mistake fails in CI rather than on a live estate.
READABLE_PATHS = frozenset(
    {
        "/proc/uptime",
        "/etc/board.info",
        "/tmp/system.cfg",
        "/etc/persistent/cfg/mgmt",
        "/var/log/messages",
    }
)

# The allowlist. Every entry is a read; none writes, restarts, or configures.
# Entries are marked unverified until their output has been captured from a
# device in this estate and a parser written against it, at which point the
# flag flips and the parser is added. Adding an entry is a code change on
# purpose: an operator-supplied command string would be a remote shell in a
# security integration, which is not what this is for.
COMMANDS: tuple[Command, ...] = (
    Command(
        "whoami",
        "whoami",
        "Proves the key authenticated and identifies the account the controller pushed.",
        verified=True,
    ),
    Command(
        "uname",
        "uname -a",
        "Kernel and architecture, enough to tell device generations apart.",
        verified=True,
    ),
    Command(
        "uptime",
        "cat /proc/uptime",
        "Seconds since boot, from procfs rather than a formatted tool.",
        verified=True,
    ),
    Command(
        "board_info",
        "cat /etc/board.info",
        "Board identity and model on UniFi hardware.",
        verified=False,
    ),
    Command(
        "system_cfg",
        "cat /tmp/system.cfg",
        "The running configuration. Expected to carry per-port VLAN and profile "
        "handling, which the Network API does not expose at any endpoint.",
        verified=False,
    ),
    Command(
        "mgmt_cfg",
        "cat /etc/persistent/cfg/mgmt",
        "Management configuration. Expected to carry the inform URL the device "
        "actually holds, which is the field adoption tracing needs.",
        verified=False,
    ),
    Command(
        "mca_info",
        "mca-cli-op info",
        "UniFi's own status summary, including adoption and inform state.",
        verified=False,
    ),
    # Association and authentication, which no controller API exposes at any
    # endpoint. A client that cannot join a wireless network is absent from
    # every UniFi client collection, so the access point's own view is the
    # only record that a join was ever attempted; see unifi_wifi.py.
    #
    # The tools differ by device generation, so the set is deliberately
    # overlapping rather than minimal: whichever entries a given device lacks
    # report unknown, which is what the four-state model is for. Observed
    # 2026-09-10 on this estate:
    #   U7 Pro (/bin)    wifi_list, stainfo, stamgr -> stainfo, ubus; no tail,
    #                    no wstalist, no mca-dump in /bin
    #   UDB Pro (/sbin)  wstalist -> ubntbox, mca-dump -> mca.sh, mca-sta,
    #                    amstainfo, tail -> busybox, wpa_cli, hostapd -> wpad
    Command(
        "wifi_list",
        "wifi_list",
        "Per-SSID radio summary and the stations on each: band, channel, PHY "
        "generation, BSSID, then each client's MAC, signal, key management "
        "(PSK or SAE) and negotiated capabilities. The clearest single answer "
        "to which clients an access point is actually carrying, and on which "
        "SSID.",
        verified=True,
    ),
    Command(
        "stainfo",
        "stainfo",
        "Station table on the newer access point generation, which has no "
        "wstalist. Present as stamgr by another name.",
        verified=False,
    ),
    Command(
        "wstalist",
        "wstalist",
        "Stations currently associated to this access point, as the radio sees "
        "them rather than as the controller reports them. Present on the "
        "ubntbox generation; not in the U7 Pro's /bin.",
        verified=False,
    ),
    Command(
        "mca_dump",
        "mca-dump",
        "Full device status, expected to carry the per-SSID station tables. The "
        "output is JSON and is redacted for wireless keys before it leaves the "
        "integration. Present on the ubntbox generation as a wrapper script; "
        "absent from the U7 Pro's /bin.",
        verified=False,
    ),
    Command(
        "syslog_tail",
        "tail -n 200 /var/log/messages",
        "The last 200 log lines. hostapd records authentication, association "
        "and deauthentication here, and alongside it UniFi's own station "
        "tracker (stahtd) emits one STA_ASSOC_TRACKER JSON object per attempt "
        "carrying event_type (association, success, soft failure, failure), "
        "auth_failures and wpa_auth_failures, auth_rssi and avg_rssi, the "
        "per-stage deltas, and the 802.11 disassoc_reason or deauth_reason. "
        "This is the record of a refused join that no controller API carries.",
        verified=True,
    ),
)

COMMANDS_BY_ID = {command.id: command for command in COMMANDS}


def _assert_reads_are_allowlisted(commands: tuple[Command, ...]) -> None:
    """Refuse an allowlist entry that reads a file READABLE_PATHS does not name.

    Checked at import, so a command added with an unvetted path cannot reach a
    device: the integration fails to load and CI says why. Any absolute path
    in any entry counts, not only arguments to cat and tail, because the next
    reader could be head, grep, or a tool nobody has thought of yet.
    """
    for command in commands:
        for token in command.argv.split():
            if token.startswith("/") and token not in READABLE_PATHS:
                raise RuntimeError(
                    f"SSH command {command.id!r} reads {token!r}, which is not in "
                    "READABLE_PATHS. Add the path there with a reason, or drop it."
                )


_assert_reads_are_allowlisted(COMMANDS)

# Redacted before the output ever leaves this module. These are the fields a
# parser has no use for (the inform authkey, passwords, wireless keys) and
# that would otherwise be rendered in a panel and pasted into a bug report.
_SECRET_LINE = re.compile(
    r"^(?P<key>[^=\n]*(?:authkey|password|passwd|psk|secret|privkey|wpa\.\d+\.psk)[^=\n]*)=.*$",
    re.IGNORECASE | re.MULTILINE,
)

# The same fields in JSON. mca-dump and wstalist answer with JSON, not
# key=value, so the line rule above would not touch a passphrase in their
# output, and a wireless key rendered in the panel is the exact thing that
# rule exists to prevent.
_SECRET_JSON = re.compile(
    r'(?P<key>"[^"\n]*(?:authkey|password|passwd|psk|secret|privkey)[^"\n]*"\s*:\s*)'
    r'"(?:[^"\\]|\\.)*"',
    re.IGNORECASE,
)

_HOSTNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,251}[A-Za-z0-9])?$")


def redact_output(text: str) -> str:
    """Mask credential-shaped assignments, keeping the key name visible.

    Both shapes the devices produce: ``key=value`` configuration lines, and
    JSON ``"key": "value"`` pairs.
    """
    text = _SECRET_LINE.sub(lambda m: f"{m.group('key')}=[redacted]", text)
    return _SECRET_JSON.sub(lambda m: f'{m.group("key")}"[redacted]"', text)


def validate_host(host: Any) -> str:
    """Accept an IP literal or a DNS hostname; never a URL, path, or option.

    The host reaches a connection call, so anything that could be read as a
    flag or a second argument is refused rather than escaped.
    """
    import ipaddress

    if not isinstance(host, str) or not host.strip():
        raise SshDeviceError(ERR_BAD_HOST, "A device address is required")
    candidate = host.strip()
    try:
        ipaddress.ip_address(candidate)
        return candidate
    except ValueError:
        pass
    if not _HOSTNAME.fullmatch(candidate):
        raise SshDeviceError(ERR_BAD_HOST, "Address must be an IP address or DNS hostname")
    return candidate


def _generate_keypair_sync() -> tuple[str, str]:
    """Return (private key OpenSSH PEM, public key authorized_keys line).

    Ed25519: small, fast, and universally accepted by current OpenSSH, which
    is what a device's own sshd runs. Blocking work; executor only.
    """
    import asyncssh

    key = asyncssh.generate_private_key("ssh-ed25519", comment="ha-soc")
    private_pem = key.export_private_key("openssh").decode("utf-8")
    public_line = key.export_public_key("openssh").decode("utf-8").strip()
    return private_pem, public_line


def _public_from_private_sync(private_pem: str) -> str:
    import asyncssh

    key = asyncssh.import_private_key(private_pem)
    return key.export_public_key("openssh").decode("utf-8").strip()


def host_key_fingerprint(key_data: bytes) -> str:
    """The SHA256:… fingerprint form OpenSSH prints, for display and pinning."""
    digest = hashlib.sha256(key_data).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


async def async_public_key(hass: HomeAssistant, secrets) -> str | None:
    """The public half to paste into the controller, or None when no pair exists."""
    private_pem = await secrets.async_get(SECRET_SSH_PRIVATE_KEY)
    if not private_pem:
        return None
    try:
        return await hass.async_add_executor_job(_public_from_private_sync, private_pem)
    except Exception:  # noqa: BLE001 - a corrupt stored key must not break the panel
        _LOGGER.exception("Stored SSH private key could not be read")
        return None


async def async_generate_keypair(hass: HomeAssistant, secrets) -> str:
    """Create a keypair, store the private half, return the public half.

    Replacing a pair invalidates every pinned host key's usefulness for
    authentication but not the pinning itself, so host keys are deliberately
    left alone here: the device's identity has not changed just because ours
    did.
    """
    private_pem, public_line = await hass.async_add_executor_job(_generate_keypair_sync)
    await secrets.async_set(SECRET_SSH_PRIVATE_KEY, private_pem)
    return public_line


async def async_clear_keypair(secrets) -> None:
    await secrets.async_set(SECRET_SSH_PRIVATE_KEY, "")


def pinned_host_keys(store) -> dict[str, Any]:
    return dict((store.data.get("unifi_ssh") or {}).get("host_keys") or {})


def _save_host_keys(store, host_keys: dict[str, Any]) -> None:
    stored = dict(store.data.get("unifi_ssh") or {})
    stored["host_keys"] = host_keys
    store.async_set_unifi_ssh(stored)


def forget_host_key(store, host: str) -> bool:
    """Drop one pinned host key so the next connection pins afresh."""
    host_keys = pinned_host_keys(store)
    if host not in host_keys:
        return False
    del host_keys[host]
    _save_host_keys(store, host_keys)
    return True


class _Pinner:
    """Trust on first use, then refuse a changed key.

    A pinned key that later differs is reported and the connection is
    abandoned. It is never updated automatically: on a flat management
    network the only two explanations are a reprovisioned device and someone
    answering for it, and this integration is not the one that should decide
    which by itself.
    """

    def __init__(self, store, host: str) -> None:
        self._store = store
        self._host = host
        self.pinned_now = False
        self.changed_from: str | None = None

    def known(self) -> str | None:
        entry = pinned_host_keys(self._store).get(self._host)
        return entry.get("fingerprint") if isinstance(entry, dict) else None

    def check(self, fingerprint: str) -> None:
        known = self.known()
        if known is None:
            host_keys = pinned_host_keys(self._store)
            host_keys[self._host] = {
                "fingerprint": fingerprint,
                "pinned_at": dt_util.utcnow().isoformat(),
            }
            _save_host_keys(self._store, host_keys)
            self.pinned_now = True
            return
        if known != fingerprint:
            self.changed_from = known
            raise SshDeviceError(
                ERR_HOST_KEY_CHANGED,
                f"The device's SSH host key changed (pinned {known}, now {fingerprint}). "
                "Confirm the device was reprovisioned, then forget the pinned key before "
                "connecting again.",
            )


async def async_run_commands(
    hass: HomeAssistant,
    store,
    secrets,
    host: str,
    command_ids: list[str],
    *,
    username: str,
) -> dict[str, Any]:
    """Run allowlisted read-only commands on one device over SSH.

    Returns a per-command result in the four-state model. Output is redacted,
    capped, and returned for the operator to read; it is never persisted and
    never audited.
    """
    import asyncssh

    checked_host = validate_host(host)
    if not username:
        raise SshDeviceError(ERR_NO_USERNAME, "The device SSH username is not configured")
    commands = []
    for command_id in command_ids:
        command = COMMANDS_BY_ID.get(command_id)
        if command is None:
            raise SshDeviceError(ERR_UNKNOWN_COMMAND, f"Unknown command {command_id!r}")
        commands.append(command)

    private_pem = await secrets.async_get(SECRET_SSH_PRIVATE_KEY)
    if not private_pem:
        raise SshDeviceError(ERR_NO_KEY, "No SSH keypair has been generated yet")

    pinner = _Pinner(store, checked_host)
    results: list[dict[str, Any]] = []
    host_key_fp: str | None = None

    try:
        client_key = await hass.async_add_executor_job(asyncssh.import_private_key, private_pem)
        async with asyncio.timeout(
            CONNECT_TIMEOUT_SECONDS + COMMAND_TIMEOUT_SECONDS * len(commands)
        ):
            conn = await asyncssh.connect(
                checked_host,
                username=username,
                client_keys=[client_key],
                # Pinning is done here, against our own store; OpenSSH's
                # known_hosts file does not exist in this container.
                known_hosts=None,
                config=None,
            )
            async with conn:
                server_key = conn.get_server_host_key()
                host_key_fp = host_key_fingerprint(server_key.export_public_key("rfc4716"))
                pinner.check(host_key_fp)
                for command in commands:
                    results.append(await _run_one(conn, command))
    except SshDeviceError:
        raise
    except asyncssh.PermissionDenied as err:
        raise SshDeviceError(
            ERR_AUTH,
            "The device refused the key. Confirm the public key is pasted into the "
            f"controller's SSH Keys panel and the device has re-provisioned since: {err}",
        ) from err
    except (OSError, asyncio.TimeoutError, asyncssh.Error) as err:
        raise SshDeviceError(ERR_UNREACHABLE, f"Could not reach the device: {err}") from err

    return {
        "host": checked_host,
        "username": username,
        "host_key_fingerprint": host_key_fp,
        "host_key_pinned_now": pinner.pinned_now,
        "results": results,
        "ran_at": dt_util.utcnow().isoformat(),
    }


async def _run_one(conn: Any, command: Command) -> dict[str, Any]:
    """One command, reduced to a four-state result plus redacted output."""
    try:
        completed = await asyncio.wait_for(
            conn.run(command.argv, check=False), timeout=COMMAND_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return _result(command, STATE_UNKNOWN, None, "The command did not finish in time", None)
    except Exception as err:  # noqa: BLE001 - one command failing is not the run failing
        return _result(command, STATE_UNKNOWN, None, f"The command could not be run: {err}", None)

    stdout = _clip(str(completed.stdout or ""))
    stderr = _clip(str(completed.stderr or ""))
    status = completed.exit_status

    if status == 0:
        state = STATE_PASS
    elif command.verified:
        # A command known to work here failing is a real answer about the device.
        state = STATE_FAIL
    else:
        # An unverified command may simply not exist on this model. Saying
        # "fail" would assert something about the device that has not been
        # established.
        state = STATE_UNKNOWN

    return _result(command, state, status, stderr, stdout)


def _result(
    command: Command,
    state: str,
    exit_status: int | None,
    stderr: str | None,
    stdout: str | None,
) -> dict[str, Any]:
    return {
        "command_id": command.id,
        "argv": command.argv,
        "description": command.description,
        "verified": command.verified,
        "state": state,
        "exit_status": exit_status,
        "stdout": redact_output(stdout) if stdout else "",
        "stderr": redact_output(stderr) if stderr else "",
        "bytes": len(stdout or ""),
        # Structured reading of the output, for the commands that have one.
        # None means this command has no parser, which is not the same as a
        # parser that found nothing.
        "analysis": _analyze(command, stdout),
    }


def _analyze(command: Command, stdout: str | None) -> dict[str, Any] | None:
    """Parse a command's output when a parser exists for it.

    Only syslog_tail has one today: its output carries the per-client join
    attempts that no controller API reports. Parsing here rather than in the
    panel keeps the reading next to the four-state model, and a parser that
    raises must never turn a successful collection into a failure.
    """
    if command.id != "syslog_tail" or not stdout:
        return None
    try:
        return unifi_ap_log.analyze(stdout)
    except Exception:  # noqa: BLE001 - output we have never seen must not break a run
        _LOGGER.debug("Access point log analysis failed", exc_info=True)
        return None


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_BYTES:
        return text
    return text[:MAX_OUTPUT_BYTES] + "\n[output truncated by HA SOC]"


def command_catalog() -> list[dict[str, Any]]:
    """The allowlist, for the panel to render as the set of available reads."""
    return [
        {
            "id": command.id,
            "argv": command.argv,
            "description": command.description,
            "verified": command.verified,
        }
        for command in COMMANDS
    ]
