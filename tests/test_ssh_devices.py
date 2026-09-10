"""Tests for ssh_devices.py and the ha_soc/ssh/* commands.

The properties that matter are the ones a wrong implementation would still
appear to satisfy: a command string can only come from the allowlist, a
changed host key is refused rather than re-pinned, credential-shaped lines
never leave the module, and command output never reaches the audit log.

Nothing here opens a socket. The connection path is exercised through a fake
asyncssh connection, because what is being tested is this module's decisions,
not asyncssh's transport.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc import ssh_devices as sd
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import (
    ws_ssh_clear_key,
    ws_ssh_forget_host_key,
    ws_ssh_generate_key,
    ws_ssh_run,
    ws_ssh_status,
)


def _connection(is_owner: bool = True, is_admin: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner, id="owner1")
    return connection


async def _call(hass: HomeAssistant, handler, connection: MagicMock, msg: dict) -> MagicMock:
    connection.reset_mock()
    handler(hass, connection, msg)
    for _ in range(300):
        await hass.async_block_till_done()
        if connection.send_result.called or connection.send_error.called:
            await hass.async_block_till_done()
            return connection
        await asyncio.sleep(0.01)
    raise AssertionError(f"no reply to {msg['type']}")


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> str:
    """The harness config dir lives in site-packages and persists between runs."""
    hass.config.config_dir = str(tmp_path)
    return str(tmp_path)


@pytest.fixture
async def entry(hass: HomeAssistant, isolated_config_dir: str) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def enabled(hass: HomeAssistant, entry: MockConfigEntry) -> MockConfigEntry:
    entry.runtime_data.store.async_update_settings(
        ssh_collection_enabled=True, ssh_username="ubnt"
    )
    await hass.async_block_till_done()
    return entry


class _FakeHostKey:
    def __init__(self, material: bytes) -> None:
        self._material = material

    def export_public_key(self, _fmt: str) -> bytes:
        return self._material


class _FakeConn:
    """Stands in for an asyncssh connection; records what was run."""

    def __init__(self, host_key: bytes, outputs: dict[str, tuple[str, str, int]]) -> None:
        self._host_key = host_key
        self._outputs = outputs
        self.ran: list[str] = []

    def get_server_host_key(self):
        return _FakeHostKey(self._host_key)

    async def run(self, argv: str, check: bool = False):
        self.ran.append(argv)
        stdout, stderr, status = self._outputs.get(argv, ("", "not found", 127))
        return SimpleNamespace(stdout=stdout, stderr=stderr, exit_status=status)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def fake_ssh(monkeypatch):
    """Replace asyncssh.connect; everything else in the module runs for real."""
    import asyncssh

    state = {
        "host_key": b"host-key-material-A",
        "outputs": {"whoami": ("ubnt\n", "", 0), "uname -a": ("Linux udb\n", "", 0)},
        "raises": None,
        "conn": None,
    }

    async def _connect(host, **kwargs):
        if state["raises"] is not None:
            raise state["raises"]
        state["conn"] = _FakeConn(state["host_key"], state["outputs"])
        state["last_kwargs"] = kwargs
        return state["conn"]

    monkeypatch.setattr(asyncssh, "connect", _connect)
    return state


# --- host validation and the allowlist -------------------------------------


@pytest.mark.parametrize(
    "host",
    ["", "  ", "-oProxyCommand=x", "192.168.1.1 -p 22", "http://192.168.1.1", "a/b", "a b"],
)
def test_rejected_hosts(host: str) -> None:
    with pytest.raises(sd.SshDeviceError) as excinfo:
        sd.validate_host(host)
    assert excinfo.value.code == sd.ERR_BAD_HOST


@pytest.mark.parametrize("host", ["192.168.1.1", "fd00::1", "udb-main", "udb.lan"])
def test_accepted_hosts(host: str) -> None:
    assert sd.validate_host(host) == host


async def test_an_unlisted_command_is_refused(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    """There is no path from a client string to a shell."""
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    with pytest.raises(sd.SshDeviceError) as excinfo:
        await sd.async_run_commands(
            hass, runtime.store, runtime.secrets, "192.168.1.1", ["rm -rf /"], username="ubnt"
        )
    assert excinfo.value.code == sd.ERR_UNKNOWN_COMMAND


def test_every_allowlisted_command_is_a_read() -> None:
    """A guard against a future entry that mutates a device."""
    forbidden = ("rm ", "reboot", "shutdown", "set-", "mv ", ">", "|", ";", "&&")
    for command in sd.COMMANDS:
        assert not any(token in command.argv for token in forbidden), command.argv


# --- keypair ---------------------------------------------------------------


async def test_generate_then_read_public_key(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    assert await sd.async_public_key(hass, runtime.secrets) is None

    public = await sd.async_generate_keypair(hass, runtime.secrets)
    assert public.startswith("ssh-ed25519 ")
    assert await sd.async_public_key(hass, runtime.secrets) == public


async def test_the_private_key_is_never_in_a_settings_payload(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """It lives in the secret store and is masked like every other secret."""
    from custom_components.ha_soc.websocket_api import ws_settings_get

    runtime = entry.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)

    connection = await _call(hass, ws_settings_get, _connection(), {"id": 1})
    payload = connection.send_result.call_args[0][1]
    assert payload["ssh_private_key"] == "[redacted]"
    assert payload["ssh_private_key_set"] is True
    assert "BEGIN OPENSSH PRIVATE KEY" not in str(payload)


async def test_run_without_a_keypair_is_refused(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    with pytest.raises(sd.SshDeviceError) as excinfo:
        await sd.async_run_commands(
            hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
        )
    assert excinfo.value.code == sd.ERR_NO_KEY


# --- host key pinning ------------------------------------------------------


async def test_first_connection_pins_the_host_key(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)

    result = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
    )
    assert result["host_key_pinned_now"] is True
    assert sd.pinned_host_keys(runtime.store)["192.168.1.1"]["fingerprint"] == result[
        "host_key_fingerprint"
    ]


async def test_a_changed_host_key_is_refused_and_not_repinned(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    """The pin is the point. Silently accepting a new key would make it decor."""
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    first = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
    )

    fake_ssh["host_key"] = b"host-key-material-B"
    with pytest.raises(sd.SshDeviceError) as excinfo:
        await sd.async_run_commands(
            hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
        )
    assert excinfo.value.code == sd.ERR_HOST_KEY_CHANGED
    assert (
        sd.pinned_host_keys(runtime.store)["192.168.1.1"]["fingerprint"]
        == first["host_key_fingerprint"]
    )


async def test_forgetting_a_pin_allows_repinning(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
    )

    assert sd.forget_host_key(runtime.store, "192.168.1.1") is True
    assert sd.forget_host_key(runtime.store, "192.168.1.1") is False

    fake_ssh["host_key"] = b"host-key-material-B"
    again = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
    )
    assert again["host_key_pinned_now"] is True


# --- the four-state result model -------------------------------------------


async def test_an_unverified_command_that_fails_is_unknown_not_fail(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    """"This model has no such tool" is not "this device is broken"."""
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)

    result = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["mca_info"], username="ubnt"
    )
    row = result["results"][0]
    assert row["verified"] is False
    assert row["state"] == sd.STATE_UNKNOWN
    assert row["exit_status"] == 127


async def test_a_verified_command_that_fails_is_a_fail(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    fake_ssh["outputs"] = {"whoami": ("", "denied", 1)}

    result = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
    )
    assert result["results"][0]["state"] == sd.STATE_FAIL


async def test_an_unreachable_device_is_not_a_failed_check(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    fake_ssh["raises"] = OSError("no route to host")

    with pytest.raises(sd.SshDeviceError) as excinfo:
        await sd.async_run_commands(
            hass, runtime.store, runtime.secrets, "192.168.1.1", ["whoami"], username="ubnt"
        )
    assert excinfo.value.code == sd.ERR_UNREACHABLE


# --- redaction -------------------------------------------------------------


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("mgmt.authkey=ba9876543210", "mgmt.authkey=[redacted]"),
        ("users.1.password=$1$abc", "users.1.password=[redacted]"),
        ("aaa.1.wpa.psk=hunter2", "aaa.1.wpa.psk=[redacted]"),
        ("mgmt.servers.1.url=http://10.0.0.1:8080/inform", "mgmt.servers.1.url=http://10.0.0.1:8080/inform"),
        ("switch.port.1.vlan=10", "switch.port.1.vlan=10"),
    ],
)
def test_redaction_masks_secrets_and_keeps_the_data_we_need(line: str, expected: str) -> None:
    assert sd.redact_output(line) == expected


async def test_output_is_redacted_before_it_leaves_the_module(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    fake_ssh["outputs"] = {
        "cat /etc/persistent/cfg/mgmt": (
            "mgmt.authkey=deadbeef\nmgmt.servers.1.url=http://10.0.0.1:8080/inform\n",
            "",
            0,
        )
    }
    result = await sd.async_run_commands(
        hass, runtime.store, runtime.secrets, "192.168.1.1", ["mgmt_cfg"], username="ubnt"
    )
    stdout = result["results"][0]["stdout"]
    assert "deadbeef" not in stdout
    assert "http://10.0.0.1:8080/inform" in stdout


# --- the WebSocket surface -------------------------------------------------


async def test_every_ssh_command_is_owner_only(
    hass: HomeAssistant, enabled: MockConfigEntry
) -> None:
    admin = _connection(is_owner=False, is_admin=True)
    for handler, msg in (
        (ws_ssh_status, {"id": 1, "type": "ha_soc/ssh/status"}),
        (ws_ssh_generate_key, {"id": 2, "type": "ha_soc/ssh/generate_key"}),
        (ws_ssh_clear_key, {"id": 3, "type": "ha_soc/ssh/clear_key"}),
        (ws_ssh_forget_host_key, {"id": 4, "type": "ha_soc/ssh/forget_host_key", "host": "h"}),
        (ws_ssh_run, {"id": 5, "type": "ha_soc/ssh/run", "host": "h", "command_ids": ["whoami"]}),
    ):
        with pytest.raises(Unauthorized):
            handler(hass, admin, msg)


async def test_run_is_refused_while_collection_is_off(
    hass: HomeAssistant, entry: MockConfigEntry, fake_ssh
) -> None:
    connection = await _call(
        hass,
        ws_ssh_run,
        _connection(),
        {"id": 1, "type": "ha_soc/ssh/run", "host": "192.168.1.1", "command_ids": ["whoami"]},
    )
    assert connection.send_error.call_args[0][1] == sd.ERR_DISABLED


async def test_status_returns_the_catalog_and_the_public_key(
    hass: HomeAssistant, enabled: MockConfigEntry
) -> None:
    connection = await _call(
        hass, ws_ssh_generate_key, _connection(), {"id": 1, "type": "ha_soc/ssh/generate_key"}
    )
    public = connection.send_result.call_args[0][1]["public_key"]

    connection = await _call(
        hass, ws_ssh_status, _connection(), {"id": 2, "type": "ha_soc/ssh/status"}
    )
    status = connection.send_result.call_args[0][1]
    assert status["enabled"] is True
    assert status["has_keypair"] is True
    assert status["public_key"] == public
    assert status["username"] == "ubnt"
    assert {c["id"] for c in status["commands"]} == {c.id for c in sd.COMMANDS}


async def test_the_audit_record_carries_outcomes_not_output(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    """A configuration dump is exactly what an audit log should not accumulate."""
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    fake_ssh["outputs"] = {"whoami": ("ubnt-secret-hostname\n", "", 0)}

    await _call(
        hass,
        ws_ssh_run,
        _connection(),
        {"id": 1, "type": "ha_soc/ssh/run", "host": "192.168.1.1", "command_ids": ["whoami"]},
    )
    records = await runtime.audit.async_query(category=sd.AUDIT_CATEGORY_RUN, limit=10)
    assert records
    detail = records[0]["detail"]
    assert detail["outcomes"] == {"whoami": "pass"}
    assert "ubnt-secret-hostname" not in str(detail)


async def test_a_host_key_mismatch_is_audited_under_its_own_category(
    hass: HomeAssistant, enabled: MockConfigEntry, fake_ssh
) -> None:
    runtime = enabled.runtime_data
    await sd.async_generate_keypair(hass, runtime.secrets)
    await _call(
        hass,
        ws_ssh_run,
        _connection(),
        {"id": 1, "type": "ha_soc/ssh/run", "host": "192.168.1.1", "command_ids": ["whoami"]},
    )

    fake_ssh["host_key"] = b"host-key-material-B"
    connection = await _call(
        hass,
        ws_ssh_run,
        _connection(),
        {"id": 2, "type": "ha_soc/ssh/run", "host": "192.168.1.1", "command_ids": ["whoami"]},
    )
    assert connection.send_error.call_args[0][1] == sd.ERR_HOST_KEY_CHANGED

    records = await runtime.audit.async_query(category=sd.AUDIT_CATEGORY_HOST_KEY, limit=10)
    assert records
    assert records[0]["detail"]["refusal"] == sd.ERR_HOST_KEY_CHANGED


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"x_authkey": "ba9876543210"}', '{"x_authkey": "[redacted]"}'),
        ('"wpa_psk" : "hunter2"', '"wpa_psk" : "[redacted]"'),
        ('{"X_Password":"s3cret"}', '{"X_Password":"[redacted]"}'),
        # An escaped quote inside the value must not end the match early.
        ('{"psk": "a\\"b", "mac": "aa:bb"}', '{"psk": "[redacted]", "mac": "aa:bb"}'),
        # Fields a parser needs are untouched.
        ('{"essid": "wifiot", "signal": -71}', '{"essid": "wifiot", "signal": -71}'),
    ],
)
def test_json_output_is_redacted_too(text: str, expected: str) -> None:
    """mca-dump and wstalist answer with JSON, which the key=value rule misses."""
    assert sd.redact_output(text) == expected


def test_the_association_commands_are_present_and_unverified() -> None:
    """The only record of a refused wireless join lives on the access point.

    No UniFi API endpoint carries an association attempt or an authentication
    failure, so these three exist to reach the device's own view. They ship
    unverified until their output has been seen on this estate.
    """
    by_id = {c.id: c for c in sd.COMMANDS}
    assert by_id["wstalist"].argv == "wstalist"
    assert by_id["mca_dump"].argv == "mca-dump"
    assert by_id["syslog_tail"].argv == "tail -n 200 /var/log/messages"
    for command_id in ("wstalist", "mca_dump", "syslog_tail"):
        assert by_id[command_id].verified is False


# --- what the allowlist may read -------------------------------------------


def test_every_path_the_allowlist_reads_is_enumerated() -> None:
    """The shipped allowlist reads nothing outside READABLE_PATHS.

    `cat` and `tail` read whatever path they are given, and the device enforces
    nothing: the key the controller distributes is an ordinary shell login. So
    the set of readable files is this module's own restraint, and it has to be
    explicit to be auditable.
    """
    sd._assert_reads_are_allowlisted(sd.COMMANDS)
    for command in sd.COMMANDS:
        for token in command.argv.split():
            if token.startswith("/"):
                assert token in sd.READABLE_PATHS, command.argv


@pytest.mark.parametrize(
    "argv",
    [
        "cat /etc/shadow",
        "cat /etc/persistent/cfg/mgmt.bak",
        "tail -n 200 /data/ha_soc/secrets",
        # A reader nobody has added yet must be caught the same way.
        "head -c 1024 /etc/dropbear/dropbear_rsa_host_key",
        "grep -r psk /etc",
    ],
)
def test_an_unvetted_read_is_refused_at_import(argv: str) -> None:
    """A careless future entry fails in CI, not on a live estate."""
    bad = (sd.Command("new", argv, "should not ship", verified=False),)
    with pytest.raises(RuntimeError, match="READABLE_PATHS"):
        sd._assert_reads_are_allowlisted(bad)


def test_a_command_with_no_path_is_allowed() -> None:
    """Tools that take no file argument are unaffected by the path rule."""
    fine = (
        sd.Command("a", "whoami", "", verified=True),
        sd.Command("b", "mca-dump", "", verified=False),
        sd.Command("c", "tail -n 200 /var/log/messages", "", verified=False),
    )
    sd._assert_reads_are_allowlisted(fine)


def test_the_ap_tool_set_covers_both_device_generations() -> None:
    """The access-point tools differ by generation, so the set overlaps.

    Observed 2026-09-10: the U7 Pro has wifi_list and stainfo and no wstalist,
    mca-dump or tail; the UDB Pro has wstalist, mca-dump and tail and no
    wifi_list. Dropping either half would leave one generation with nothing,
    and an absent tool already reports unknown rather than fail.
    """
    by_id = {c.id: c for c in sd.COMMANDS}
    assert by_id["wifi_list"].argv == "wifi_list"
    assert by_id["stainfo"].argv == "stainfo"
    assert by_id["wstalist"].argv == "wstalist"
    # Output captured from this estate; the rest have not been seen.
    assert by_id["wifi_list"].verified is True
    # /var/log/messages and tail both exist on the U7 Pro and the UDB Pro.
    assert by_id["syslog_tail"].verified is True
    for command_id in ("stainfo", "wstalist", "mca_dump"):
        assert by_id[command_id].verified is False
