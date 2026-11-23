"""Tests for phase 10 of the network inventory: the owner-only export, the
diagnostics summary, and the scenario replay corpus.

Each file under tests/fixtures/netscan_scenarios is a sequence of cycles and
owner actions with what the inventory must hold afterwards. The merge is a
pure function of (state, cycle, clock), so a scenario replays the same way
every time.
"""
import csv
import io
import json
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import inventory as inv
from custom_components.ha_soc import websocket_api
from custom_components.ha_soc.const import CONF_NETSCAN_EXTRA_NETWORKS, DOMAIN, REDACTED_PLACEHOLDER
from custom_components.ha_soc.diagnostics import async_get_config_entry_diagnostics

# Setting up the entry writes runtime files into the config directory; see conftest.py.
ISOLATED_CONFIG_DIR = True

T0 = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
SCENARIOS = sorted((Path(__file__).parent / "fixtures" / "netscan_scenarios").glob("*.json"))
MAC_A = "00:11:22:33:44:55"
MAC_B = "00:11:22:33:44:66"
# What an export or a diagnostics download must never contain by accident.
PRIVATE = (MAC_A, MAC_B, "192.0.2.10", "192.0.2.11", "hallway-nas", "My NAS", "CN=nas.example")


# --------------------------------------------------------------------------
# Scenario replay
# --------------------------------------------------------------------------


def _replay(scenario: dict) -> dict:
    state = inv.empty_state()
    ids = count(1)
    new_id = lambda: f"d_{next(ids):04d}"  # noqa: E731
    for fingerprint, cert in (scenario.get("certs") or {}).items():
        state["certs"][fingerprint] = {
            "sha256": fingerprint,
            "subject": cert["subject"],
            "issuer": cert["issuer"],
            "not_after": (T0 + timedelta(days=cert["expires_in_days"])).isoformat(),
            "unreadable": False,
        }

    def _by_mac(mac):
        return next(d for d in state["devices"].values() if d["macs"] == [mac])

    for step in scenario["steps"]:
        for index in range(step.get("repeat", 1)):
            now = T0 + timedelta(minutes=step["minute"] + 5 * index)
            if "hosts" in step:
                inv.merge_cycle(state, step["hosts"], now, new_id=new_id, presence=True)
            elif "unifi" in step:
                inv.merge_unifi_clients(state, step["unifi"], now, new_id=new_id)
            elif "acknowledge" in step:
                device = _by_mac(step["acknowledge"])
                device["verdict"] = inv.VERDICT_ACKNOWLEDGED
                inv._append_event(state, now.isoformat(), device["id"], "verdict")
            elif "watch" in step:
                device = _by_mac(step["watch"])
                device["watched"] = True
                inv._append_event(state, now.isoformat(), device["id"], "watch")
    return state


def _facts(device: dict) -> dict:
    name = inv.best_name(device)
    return {
        "baseline": device.get("baseline"),
        "verdict": device.get("verdict"),
        "mac_kind": device.get("mac_kind"),
        "vendor": device.get("vendor"),
        "best_name": name["value"] if name else None,
        "current_ip": device["addresses"][0]["ip"] if device.get("addresses") else None,
        "address_count": len(device.get("addresses") or []),
        "presence_segments": len(device.get("presence") or []),
        "missed_cycles": device.get("missed_cycles"),
        "down": bool(device.get("down_since")),
    }


def test_the_corpus_is_present():
    assert len(SCENARIOS) >= 7


@pytest.mark.parametrize("path", SCENARIOS, ids=lambda p: p.stem)
def test_scenario(path: Path):
    scenario = json.loads(path.read_text(encoding="utf-8"))
    state = _replay(scenario)
    expect = scenario["expect"]

    assert len(state["devices"]) == expect["devices"], scenario["description"]
    for mac, wanted in (expect.get("by_mac") or {}).items():
        device = next(d for d in state["devices"].values() if d["macs"] == [mac])
        facts = _facts(device)
        assert {key: facts[key] for key in wanted} == wanted, (mac, scenario["description"])
    if "events" in expect:
        assert [[e["kind"], e.get("alert")] for e in state["events"]] == expect["events"]
    if "created_after_learning" in expect:
        created = [e for e in state["events"] if e["kind"] == "created" and not e["baseline"]]
        assert len(created) == expect["created_after_learning"]


def test_replaying_a_scenario_twice_gives_the_same_state():
    scenario = json.loads(SCENARIOS[0].read_text(encoding="utf-8"))
    assert _replay(scenario) == _replay(scenario)


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


def _devices():
    return [
        {
            "id": "d_0002",
            "label": "My NAS",
            "display_name": {"value": "My NAS", "source": "label"},
            "verdict": "acknowledged",
            "watched": True,
            "identity": "mac",
            "macs": [MAC_A],
            "mac_kind": "global",
            "vendor": {"value": "Synology", "source": "probe_oui"},
            "addresses": [{"ip": "192.0.2.10", "since": T0.isoformat(), "network": "192.0.2.0/24"}],
            "roles": ["dns"],
            "first_seen": T0.isoformat(),
            "last_seen": T0.isoformat(),
            "sources": ["probe_arp", "unifi"],
            "ports": {"443": {}, "22": {}, "80": {"closed_at": T0.isoformat()}},
        },
        {
            "id": "d_0001",
            "label": None,
            "display_name": {"value": '=HYPERLINK("http://evil.example","x")', "source": "dhcp"},
            "verdict": "unacknowledged",
            "identity": "address",
            "macs": [],
            "addresses": [],
            "vendor": {"value": "+cmd|' /C calc'!A0", "source": "probe_oui"},
        },
    ]


def test_csv_export_has_one_row_per_device_in_a_fixed_order():
    rows = list(csv.DictReader(io.StringIO(inv.export_csv(_devices()))))
    assert [row["id"] for row in rows] == ["d_0001", "d_0002"]
    assert list(rows[0]) == list(inv.EXPORT_COLUMNS)
    nas = rows[1]
    assert (nas["label"], nas["mac"], nas["ip"], nas["network"]) == ("My NAS", MAC_A, "192.0.2.10", "192.0.2.0/24")
    assert (nas["watched"], nas["roles"], nas["sources"], nas["open_ports"]) == ("yes", "dns", "probe_arp unifi", "22 443")
    assert (rows[0]["mac"], rows[0]["ip"], rows[0]["watched"]) == ("", "", "no")


def test_csv_export_defuses_cells_a_spreadsheet_would_run():
    rows = list(csv.DictReader(io.StringIO(inv.export_csv(_devices()))))
    assert rows[0]["name"] == "'=HYPERLINK(\"http://evil.example\",\"x\")"
    assert rows[0]["vendor"].startswith("'+cmd")
    for row in rows:
        assert not any(value.startswith(("=", "+", "-", "@")) for value in row.values())


def test_json_export_carries_the_same_rows():
    document = json.loads(inv.export_json(_devices(), exported_at=T0.isoformat()))
    assert document["exported_at"] == T0.isoformat()
    assert [row["id"] for row in document["devices"]] == ["d_0001", "d_0002"]
    assert set(document["devices"][0]) == set(inv.EXPORT_COLUMNS)
    # JSON is not opened as a spreadsheet, so the text is kept as it is.
    assert document["devices"][0]["name"].startswith("=HYPERLINK")


async def _runtime(hass: HomeAssistant):
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _fill(inventory) -> None:
    inventory.async_merge_cycle(
        [
            {"ip": "192.0.2.10", "mac": MAC_A, "open_ports": [{"port": 443}]},
            {"ip": "192.0.2.11", "mac": MAC_B},
        ]
    )
    device = next(d for d in inventory.state["devices"].values() if d["macs"] == [MAC_A])
    inventory.async_set_label(device["id"], "My NAS", at=T0.isoformat())
    inventory.state["certs"]["c1"] = {"sha256": "c1", "subject": "CN=nas.example", "unreadable": False}
    device["ports"]["443"]["cert_sha256"] = "c1"
    inv.apply_names(inventory.state, [{"mac": MAC_A, "name": "hallway-nas", "source": "dhcp"}], T0)


async def test_export_requires_owner(hass: HomeAssistant) -> None:
    await _runtime(hass)
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=False)
    with pytest.raises(Unauthorized):
        websocket_api.ws_inventory_export(hass, connection, {"id": 1, "format": "csv"})


@pytest.mark.parametrize("fmt", ["csv", "json"])
async def test_export_is_audited_as_a_privileged_read_without_its_content(hass: HomeAssistant, fmt) -> None:
    runtime = (await _runtime(hass)).runtime_data
    _fill(runtime.inventory)
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=True, id="owner-id")
    with patch.object(runtime.audit, "async_log") as audit_log:
        websocket_api.ws_inventory_export(hass, connection, {"id": 1, "format": fmt})
        await hass.async_block_till_done()

    result = connection.send_result.call_args.args[1]
    assert (result["format"], result["devices"]) == (fmt, 2)
    assert MAC_A in result["content"] and "My NAS" in result["content"]
    audit_log.assert_called_once_with(
        "privileged_read",
        user_id="owner-id",
        detail={"target": "network_inventory", "read": "export", "format": fmt, "devices": 2},
    )


# --------------------------------------------------------------------------
# Diagnostics
# --------------------------------------------------------------------------


async def test_diagnostics_summarize_the_inventory_without_any_of_it(hass: HomeAssistant) -> None:
    entry = await _runtime(hass)
    runtime = entry.runtime_data
    _fill(runtime.inventory)
    runtime.inventory.state["meta"]["gateway_ip"] = "192.0.2.1"
    runtime.inventory.state["meta"]["dns_servers"] = ["192.0.2.53"]
    runtime.store.async_update_settings(**{CONF_NETSCAN_EXTRA_NETWORKS: ["192.168.20.0/24"]})

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    summary = diagnostics["network_inventory"]
    assert summary["devices"] == 2
    assert summary["by_verdict"] == {"unacknowledged": 2}
    assert summary["by_source"] == {"probe_arp": 2, "probe_tcp": 1}
    assert summary["by_name_source"] == {"cert": 1, "dhcp": 1}
    assert (summary["labeled"], summary["certificates"], summary["open_ports"]) == (1, 1, 1)
    assert (summary["gateway_known"], summary["dns_servers"]) == (True, 1)

    dumped = json.dumps(diagnostics)
    device_ids = tuple(runtime.inventory.state["devices"])
    for secret in (*PRIVATE, *device_ids, "192.0.2.1", "192.0.2.53", "192.168.20.0/24"):
        assert secret not in dumped, secret
    assert diagnostics["settings"][CONF_NETSCAN_EXTRA_NETWORKS] == REDACTED_PLACEHOLDER
    assert diagnostics["settings"][f"{CONF_NETSCAN_EXTRA_NETWORKS}_set"] is True


def test_diagnostics_summary_contains_only_numbers_flags_and_fixed_words():
    state = inv.empty_state()
    inv.merge_cycle(state, [{"ip": "192.0.2.10", "mac": MAC_A}], T0, new_id=lambda: "d_0001")

    def _leaves(value):
        if isinstance(value, dict):
            for key, inner in value.items():
                yield key
                yield from _leaves(inner)
        else:
            yield value

    allowed_words = {
        "unacknowledged", "acknowledged", "ignored", "mac", "address", "global", "local", "None",
        "probe_arp", "probe_tcp", "unifi", "ha_registry", "created", "probe", "supervisor",
    }
    summary = inv.diagnostics_summary(state)
    for leaf in _leaves(summary):
        if isinstance(leaf, str) and leaf not in summary and leaf != T0.isoformat():
            assert leaf in allowed_words, leaf
