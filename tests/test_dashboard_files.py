"""Tests for dashboard_files.py and the ha_soc/dashboards/* commands.

The two things worth proving are that no path outside <config>/dashboards is
reachable by any spelling, and that a write presenting a digest that did not
come from the current file on disk is refused rather than applied. The rest
of the surface (listing, validation tiers, backups, audit) is checked around
those two.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized

from custom_components.ha_soc import dashboard_files as df
from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.websocket_api import (
    ws_dashboards_list,
    ws_dashboards_read,
    ws_dashboards_validate,
    ws_dashboards_write,
)

OVERVIEW = "title: Overview\nviews:\n  - title: Home\n    cards: []\n"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _connection(is_owner: bool = True, is_admin: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=is_admin, is_owner=is_owner, id="owner1")
    return connection


def _write(hass: HomeAssistant, relative: str, text: str) -> str:
    path = os.path.join(hass.config.config_dir, "dashboards", *relative.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(text)
    return path


@pytest.fixture(autouse=True)
def isolated_config_dir(hass: HomeAssistant, tmp_path) -> str:
    """Give each test its own config dir.

    The harness's config dir lives inside site-packages and survives between
    runs, so a test that creates files there leaks into the next test and
    into every later use of that venv.
    """
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
    entry.runtime_data.store.async_update_settings(dashboard_edit_enabled=True)
    await hass.async_block_till_done()
    return entry


@pytest.fixture
def dashboards(hass: HomeAssistant, isolated_config_dir: str) -> str:
    _write(hass, "overview.yaml", OVERVIEW)
    _write(hass, "shared/rooms/kitchen.yaml", "type: entities\nentities: []\n")
    _write(hass, "notes.txt", "not yaml")
    return os.path.join(hass.config.config_dir, "dashboards")



async def _call(hass: HomeAssistant, handler, connection: MagicMock, msg: dict) -> MagicMock:
    """Run one command wrapper and wait for its single reply.

    These handlers are @async_response, so calling the wrapper only schedules
    the coroutine, and one async_block_till_done is not enough for a command
    that makes several executor round trips: it can return between them on a
    slower runner. Waiting on the reply itself is what the caller means, and
    it keeps the test from passing or failing on machine speed.
    """
    connection.reset_mock()
    handler(hass, connection, msg)
    for _ in range(200):
        await hass.async_block_till_done()
        if connection.send_result.called or connection.send_error.called:
            # The reply is sent after the audit append but before the flush
            # task it scheduled has run, so settle once more before returning.
            await hass.async_block_till_done()
            return connection
        await asyncio.sleep(0.01)
    raise AssertionError(f"no reply to {msg['type']}")


# --- path containment ------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "../configuration.yaml",
        "shared/../../configuration.yaml",
        "/etc/passwd",
        "..\\configuration.yaml",
        "shared\\rooms\\kitchen.yaml",
        "C:/config/configuration.yaml",
        "./overview.yaml",
        "",
        "overview.yaml\x00.txt",
        "secrets.txt",
        "overview.json",
    ],
)
def test_rejected_paths(hass: HomeAssistant, relative: str) -> None:
    with pytest.raises(df.DashboardFileError) as excinfo:
        df._resolve(hass, relative)
    assert excinfo.value.code == df.ERR_NOT_ALLOWED


def test_accepts_nested_yaml_path(hass: HomeAssistant) -> None:
    resolved = df._resolve(hass, "shared/rooms/kitchen.yaml")
    assert resolved.startswith(os.path.join(hass.config.config_dir, "dashboards"))


@pytest.mark.skipif(os.name == "nt", reason="symlink creation needs privileges on Windows")
async def test_symlink_out_of_the_folder_is_refused(
    hass: HomeAssistant, dashboards: str
) -> None:
    """A link whose name and suffix pass every textual check still resolves
    outside the folder, which is the check that decides."""
    outside = os.path.join(hass.config.config_dir, "configuration.yaml")
    with open(outside, "w", encoding="utf-8") as file:
        file.write("homeassistant: {}\n")
    os.symlink(outside, os.path.join(dashboards, "escape.yaml"))

    with pytest.raises(df.DashboardFileError) as excinfo:
        df._resolve(hass, "escape.yaml")
    assert excinfo.value.code == df.ERR_NOT_ALLOWED

    listing = await df.async_list_files(hass)
    assert "escape.yaml" not in {item["path"] for item in listing["files"]}


# --- listing and reading ---------------------------------------------------


async def test_list_is_recursive_and_yaml_only(hass: HomeAssistant, dashboards: str) -> None:
    listing = await df.async_list_files(hass)
    paths = {item["path"] for item in listing["files"]}
    assert paths == {"overview.yaml", "shared/rooms/kitchen.yaml"}
    assert listing["root"] == "dashboards"
    assert listing["root_exists"] is True


async def test_list_reports_a_missing_folder(hass: HomeAssistant) -> None:
    listing = await df.async_list_files(hass)
    assert listing["root_exists"] is False
    assert listing["files"] == []


async def test_read_returns_the_digest_of_the_content(
    hass: HomeAssistant, dashboards: str
) -> None:
    result = await df.async_read_file(hass, "overview.yaml")
    assert result["content"] == OVERVIEW
    assert result["sha256"] == _sha(OVERVIEW)


async def test_read_of_a_missing_file(hass: HomeAssistant, dashboards: str) -> None:
    with pytest.raises(df.DashboardFileError) as excinfo:
        await df.async_read_file(hass, "nope.yaml")
    assert excinfo.value.code == df.ERR_NOT_FOUND


async def test_read_refuses_an_oversized_file(hass: HomeAssistant, dashboards: str) -> None:
    _write(hass, "big.yaml", "# " + "x" * (df.MAX_FILE_BYTES + 10))
    with pytest.raises(df.DashboardFileError) as excinfo:
        await df.async_read_file(hass, "big.yaml")
    assert excinfo.value.code == df.ERR_TOO_LARGE


# --- validation ------------------------------------------------------------


async def test_valid_yaml_has_no_errors(hass: HomeAssistant) -> None:
    verdict = await df.async_validate(hass, OVERVIEW)
    assert verdict["valid"] is True
    assert verdict["errors"] == []


async def test_syntax_error_is_reported_with_a_line(hass: HomeAssistant) -> None:
    verdict = await df.async_validate(hass, "views:\n  - title: Home\n   cards: []\n")
    assert verdict["valid"] is False
    assert verdict["errors"][0]["line"] is not None


async def test_ha_tags_parse_without_being_resolved(hass: HomeAssistant) -> None:
    """A dashboards folder is built from !include; refusing it would make the
    editor useless on exactly the files it exists for."""
    verdict = await df.async_validate(hass, "views: !include shared/views.yaml\n")
    assert verdict["valid"] is True


async def test_duplicate_key_is_a_warning_not_an_error(hass: HomeAssistant) -> None:
    """annotatedyaml warns and keeps the last value, so Home Assistant would
    load this file; calling it an error would refuse a loadable file."""
    verdict = await df.async_validate(hass, "title: A\ntitle: B\n")
    assert verdict["valid"] is True
    assert any("Duplicate key" in item["message"] for item in verdict["warnings"])


async def test_missing_include_target_is_a_warning(hass: HomeAssistant, dashboards: str) -> None:
    verdict = await df.async_validate(
        hass, "views: !include shared/missing.yaml\n", "overview.yaml"
    )
    assert verdict["valid"] is True
    assert any("does not exist" in item["message"] for item in verdict["warnings"])


async def test_include_outside_the_folder_is_a_warning(
    hass: HomeAssistant, dashboards: str
) -> None:
    verdict = await df.async_validate(
        hass, "views: !include ../configuration.yaml\n", "overview.yaml"
    )
    assert verdict["valid"] is True
    assert any("outside the dashboards folder" in item["message"] for item in verdict["warnings"])


# --- writing ---------------------------------------------------------------


async def test_write_replaces_content_and_leaves_a_backup(
    hass: HomeAssistant, dashboards: str
) -> None:
    new_text = "title: Overview\nviews: []\n"
    result = await df.async_write_file(hass, "overview.yaml", new_text, _sha(OVERVIEW))

    with open(os.path.join(dashboards, "overview.yaml"), encoding="utf-8") as file:
        assert file.read() == new_text
    assert result["sha256"] == _sha(new_text)

    backup = os.path.join(hass.config.config_dir, result["backup"])
    with open(backup, encoding="utf-8") as file:
        assert file.read() == OVERVIEW


async def test_write_with_a_stale_digest_conflicts_and_changes_nothing(
    hass: HomeAssistant, dashboards: str
) -> None:
    with pytest.raises(df.DashboardFileError) as excinfo:
        await df.async_write_file(hass, "overview.yaml", "title: X\n", _sha("something else"))

    assert excinfo.value.code == df.ERR_CONFLICT
    # The refusal carries what is actually on disk so the panel can reload.
    assert excinfo.value.extra["content"] == OVERVIEW
    with open(os.path.join(dashboards, "overview.yaml"), encoding="utf-8") as file:
        assert file.read() == OVERVIEW


async def test_write_refuses_invalid_yaml(hass: HomeAssistant, dashboards: str) -> None:
    with pytest.raises(df.DashboardFileError) as excinfo:
        await df.async_write_file(
            hass, "overview.yaml", "views: [1, 2\ncards: }\n", _sha(OVERVIEW)
        )
    assert excinfo.value.code == df.ERR_INVALID_YAML
    with open(os.path.join(dashboards, "overview.yaml"), encoding="utf-8") as file:
        assert file.read() == OVERVIEW


async def test_write_cannot_create_a_new_file(hass: HomeAssistant, dashboards: str) -> None:
    """Modify only: a path that does not exist is a not_found, not a create."""
    with pytest.raises(df.DashboardFileError) as excinfo:
        await df.async_write_file(hass, "brand_new.yaml", OVERVIEW, _sha(OVERVIEW))
    assert excinfo.value.code == df.ERR_NOT_FOUND
    assert not os.path.exists(os.path.join(dashboards, "brand_new.yaml"))


async def test_write_preserves_file_mode(hass: HomeAssistant, dashboards: str) -> None:
    path = os.path.join(dashboards, "overview.yaml")
    os.chmod(path, 0o600)
    before = os.stat(path).st_mode & 0o777
    await df.async_write_file(hass, "overview.yaml", "title: Overview\n", _sha(OVERVIEW))
    assert os.stat(path).st_mode & 0o777 == before


# --- the WebSocket surface -------------------------------------------------


async def test_commands_require_admin(hass: HomeAssistant, enabled: MockConfigEntry) -> None:
    connection = _connection(is_owner=False, is_admin=False)
    with pytest.raises(Unauthorized):
        ws_dashboards_list(hass, connection, {"id": 1, "type": "ha_soc/dashboards/list"})


async def test_list_reports_disabled_without_leaking_the_folder(
    hass: HomeAssistant, entry: MockConfigEntry, dashboards: str
) -> None:
    connection = await _call(
        hass, ws_dashboards_list, _connection(), {"id": 1, "type": "ha_soc/dashboards/list"}
    )
    result = connection.send_result.call_args[0][1]
    assert result["enabled"] is False
    assert result["files"] == []


async def test_read_is_refused_while_editing_is_off(
    hass: HomeAssistant, entry: MockConfigEntry, dashboards: str
) -> None:
    connection = await _call(
        hass,
        ws_dashboards_read,
        _connection(),
        {"id": 1, "type": "ha_soc/dashboards/read", "path": "overview.yaml"},
    )
    assert connection.send_error.call_args[0][1] == df.ERR_DISABLED
    connection.send_result.assert_not_called()


async def test_admin_round_trip_when_enabled(
    hass: HomeAssistant, enabled: MockConfigEntry, dashboards: str
) -> None:
    admin = _connection(is_owner=False, is_admin=True)
    enabled.runtime_data.store.async_update_settings(access_level="owner_and_admins")

    await _call(hass, ws_dashboards_list, admin, {"id": 1, "type": "ha_soc/dashboards/list"})
    listing = admin.send_result.call_args[0][1]
    assert listing["enabled"] is True
    assert "overview.yaml" in {item["path"] for item in listing["files"]}

    await _call(
        hass,
        ws_dashboards_read,
        admin,
        {"id": 2, "type": "ha_soc/dashboards/read", "path": "overview.yaml"},
    )
    loaded = admin.send_result.call_args[0][1]

    await _call(
        hass,
        ws_dashboards_write,
        admin,
        {
            "id": 3,
            "type": "ha_soc/dashboards/write",
            "path": "overview.yaml",
            "content": "title: Renamed\n",
            "expected_sha256": loaded["sha256"],
            "reason": "rename the dashboard",
        },
    )
    written = admin.send_result.call_args[0][1]
    assert written["sha256"] == _sha("title: Renamed\n")


async def test_write_is_audited_with_the_reason(
    hass: HomeAssistant, enabled: MockConfigEntry, dashboards: str
) -> None:
    await _call(
        hass,
        ws_dashboards_write,
        _connection(),
        {
            "id": 1,
            "type": "ha_soc/dashboards/write",
            "path": "overview.yaml",
            "content": "title: Audited\n",
            "expected_sha256": _sha(OVERVIEW),
            "reason": "tidy the header",
        },
    )

    records = await enabled.runtime_data.audit.async_query(
        category=df.AUDIT_CATEGORY_WRITE, limit=10
    )
    assert records
    detail = records[0]["detail"]
    assert detail["path"] == "overview.yaml"
    assert detail["reason"] == "tidy the header"
    assert detail["sha256_before"] == _sha(OVERVIEW)


async def test_a_refused_path_is_audited(
    hass: HomeAssistant, enabled: MockConfigEntry, dashboards: str
) -> None:
    connection = await _call(
        hass,
        ws_dashboards_read,
        _connection(),
        {"id": 1, "type": "ha_soc/dashboards/read", "path": "../configuration.yaml"},
    )
    assert connection.send_error.call_args[0][1] == df.ERR_NOT_ALLOWED
    # "refusal", not "code": the audit redactor masks a key named "code".
    records = await enabled.runtime_data.audit.async_query(
        category=df.AUDIT_CATEGORY_DENIED, limit=10
    )
    assert records
    assert records[0]["detail"]["refusal"] == df.ERR_NOT_ALLOWED


async def test_validate_command_returns_the_server_verdict(
    hass: HomeAssistant, enabled: MockConfigEntry
) -> None:
    connection = await _call(
        hass,
        ws_dashboards_validate,
        _connection(),
        {"id": 1, "type": "ha_soc/dashboards/validate", "content": "a:\n b: 1\n  c: 2\n"},
    )
    result = connection.send_result.call_args[0][1]
    assert result["valid"] is False
