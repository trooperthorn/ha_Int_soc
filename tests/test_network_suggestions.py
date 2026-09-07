"""Tests for the Network Security suggestion decisions and the gated UniFi
write-back: remediation attached to the right findings, decisions stored
and decorated, apply refused unless write-back is on, the write helpers
doing a full-object PUT and reading the change back, and the owner-only
WebSocket gate on apply.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ha_soc import network_security as ns
from custom_components.ha_soc import unifi
from custom_components.ha_soc.const import (
    CONF_UNIFI_NETWORK_HOST,
    CONF_UNIFI_NETWORK_WRITE_API_KEY,
    CONF_UNIFI_NETWORK_WRITE_ENABLED,
    DOMAIN,
    REMEDIATION_DISABLE_ACL_RULE,
    REMEDIATION_DISABLE_FIREWALL_POLICY,
)
from custom_components.ha_soc.unifi import UniFiError
from custom_components.ha_soc.websocket_api import (
    ws_network_security_suggestion_apply,
    ws_network_security_suggestion_set,
)

_BROAD_POLICY = {
    "order": 1,
    "id": "pol-1",
    "name": "Allow all",
    "enabled": True,
    "action": "ALLOW",
    "source": {"zone": "IoT", "filter_type": None},
    "destination": {"zone": "LAN", "filter_type": None},
}
_BROAD_ACL = {
    "order": 1,
    "id": "acl-1",
    "name": "Everything",
    "enabled": True,
    "action": "ALLOW",
    "source": {},
    "destination": {},
}


def _unifi(policies=None, acl=None):
    return {
        "acl": {"available": acl is not None, "rules": acl or []},
        "firewall_policies": {"available": policies is not None, "rules": policies or [], "zones": []},
        "server_ports": {"available": False, "ports": []},
    }


_PIHOLE = {"configured": True, "reachable": True, "blocking_enabled": True, "iot_cidr": "10.0.0.0/24", "iot_clients_scoped": True}


@pytest.fixture
async def entry(hass: HomeAssistant) -> MockConfigEntry:
    config_entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


def _connection(*, owner: bool = True) -> MagicMock:
    connection = MagicMock()
    connection.user = MagicMock(is_admin=True, is_owner=owner, id="u1" if owner else "admin2")
    return connection


def test_broad_policy_and_acl_findings_carry_a_remediation() -> None:
    findings = ns.build_findings(_unifi(policies=[_BROAD_POLICY], acl=[_BROAD_ACL]), _PIHOLE)
    by_id = {f["id"]: f for f in findings}
    policy = by_id["firewall_policy_broad_allow_pol-1"]["remediation"]
    assert policy["kind"] == REMEDIATION_DISABLE_FIREWALL_POLICY and policy["target_id"] == "pol-1"
    acl = by_id["acl_broad_allow_acl-1"]["remediation"]
    assert acl["kind"] == REMEDIATION_DISABLE_ACL_RULE and acl["target_id"] == "acl-1"
    assert "Re-enable" in policy["reversible"]


def test_findings_without_an_id_have_no_remediation() -> None:
    policy = {**_BROAD_POLICY, "id": None}
    findings = ns.build_findings(_unifi(policies=[policy]), _PIHOLE)
    assert findings[0]["remediation"] is None


def test_manual_findings_have_no_remediation() -> None:
    findings = ns.build_findings(_unifi(policies=[], acl=[]), {"configured": False, "reachable": False})
    assert findings and all(f["remediation"] is None for f in findings)


def test_decorate_attaches_decisions_by_id() -> None:
    findings = [{"id": "a"}, {"id": "b"}]
    decorated = ns.decorate_findings(findings, {"a": {"status": "ignored", "at": "t", "by": "u", "detail": None}})
    assert decorated[0]["decision"]["status"] == "ignored"
    assert decorated[1]["decision"] is None
    assert "decision" not in findings[0]


async def test_set_decision_stores_and_clears(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    store = entry.runtime_data.store
    ns.async_set_suggestion_decision(store, "f1", "planned", by_user_id="u1")
    assert store.data["network_suggestions"]["f1"]["status"] == "planned"
    ns.async_set_suggestion_decision(store, "f1", None, by_user_id="u1")
    assert "f1" not in store.data["network_suggestions"]
    with pytest.raises(ValueError):
        ns.async_set_suggestion_decision(store, "f1", "applied", by_user_id="u1")


async def test_apply_refused_while_write_back_is_off(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    runtime = entry.runtime_data
    ok, reason, _ = await ns.async_apply_suggestion(
        hass, runtime.store, runtime.secrets, "firewall_policy_broad_allow_pol-1", by_user_id="u1"
    )
    assert (ok, reason) == (False, "write_disabled")


async def test_apply_rederives_the_finding_and_records_applied(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    runtime.store.async_update_settings(unifi_network_write_enabled=True)
    result = {"policy_id": "pol-1", "name": "Allow all", "enabled_before": True, "enabled_after": False}
    with (
        patch.object(unifi, "async_network_overview", return_value=_unifi(policies=[_BROAD_POLICY])),
        patch("custom_components.ha_soc.pihole.async_pihole_overview", return_value=_PIHOLE),
        patch.object(unifi, "async_disable_firewall_policy", return_value=result) as disable,
    ):
        ok, reason, got = await ns.async_apply_suggestion(
            hass, runtime.store, runtime.secrets, "firewall_policy_broad_allow_pol-1", by_user_id="u1"
        )
        assert (ok, reason, got) == (True, None, result)
        disable.assert_awaited_once()
        assert disable.await_args.args[3] == "pol-1"

        # A finding that no longer fires cannot be acted on from a stale panel.
        ok, reason, _ = await ns.async_apply_suggestion(
            hass, runtime.store, runtime.secrets, "firewall_policy_broad_allow_gone", by_user_id="u1"
        )
        assert (ok, reason) == (False, "finding_not_current")

    decision = runtime.store.data["network_suggestions"]["firewall_policy_broad_allow_pol-1"]
    assert decision["status"] == "applied" and decision["detail"]["policy_id"] == "pol-1"


async def test_apply_surfaces_controller_errors_as_reasons(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    runtime.store.async_update_settings(unifi_network_write_enabled=True)
    with (
        patch.object(unifi, "async_network_overview", return_value=_unifi(policies=[_BROAD_POLICY])),
        patch("custom_components.ha_soc.pihole.async_pihole_overview", return_value=_PIHOLE),
        patch.object(unifi, "async_disable_firewall_policy", side_effect=UniFiError("nope")),
    ):
        ok, reason, _ = await ns.async_apply_suggestion(
            hass, runtime.store, runtime.secrets, "firewall_policy_broad_allow_pol-1", by_user_id="u1"
        )
    assert (ok, reason) == (False, "nope")
    assert "firewall_policy_broad_allow_pol-1" not in runtime.store.data["network_suggestions"]


async def test_overview_reports_write_enabled_and_decisions(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    ns.async_set_suggestion_decision(runtime.store, "firewall_policy_broad_allow_pol-1", "ignored", by_user_id="u1")
    with (
        patch.object(unifi, "async_network_overview", return_value={**_unifi(policies=[_BROAD_POLICY]), "clients": [], "reachable": True, "error": None, "generated_at": "t"}),
        patch("custom_components.ha_soc.pihole.async_pihole_overview", return_value=_PIHOLE),
    ):
        overview = await ns.async_network_security_overview(hass, runtime.store, runtime.secrets)
    assert overview["write_enabled"] is False
    assert overview["findings"][0]["decision"]["status"] == "ignored"


class _Resp:
    def __init__(self, status: int, payload):
        self.status = status
        self._payload = payload
        self.content_length = None
        self.content = self

    async def read(self, _n):
        import json

        return json.dumps(self._payload).encode()

    def raise_for_status(self):
        if self.status >= 400:
            raise AssertionError(self.status)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


class _WriteSession:
    """GET returns the policy, then after the PUT returns it disabled."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []
        self.enabled = True

    def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        if url.endswith("/sites"):
            return _Resp(200, {"data": [{"id": "site-1"}]})
        return _Resp(200, {"id": "pol-1", "index": 3, "metadata": {"origin": "USER_DEFINED"}, "name": "Allow all", "enabled": self.enabled, "action": {"type": "ALLOW"}})

    def put(self, url, **kwargs):
        self.calls.append(("PUT", url, kwargs))
        self.enabled = kwargs["json"]["enabled"]
        return _Resp(200, {})


async def _enable_write(entry: MockConfigEntry) -> None:
    runtime = entry.runtime_data
    runtime.store.async_update_settings(unifi_network_write_enabled=True, unifi_network_host="10.0.0.1")
    await runtime.secrets.async_set(CONF_UNIFI_NETWORK_WRITE_API_KEY, "write-key")


async def test_disable_policy_puts_full_object_without_server_fields_and_reads_back(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    await _enable_write(entry)
    session = _WriteSession()
    with patch.object(unifi, "async_get_clientsession", return_value=session):
        result = await unifi.async_disable_firewall_policy(hass, runtime.store, runtime.secrets, "pol-1")
    assert result == {"policy_id": "pol-1", "name": "Allow all", "enabled_before": True, "enabled_after": False}
    put = next(c for c in session.calls if c[0] == "PUT")
    assert put[1].endswith("/sites/site-1/firewall/policies/pol-1")
    body = put[2]["json"]
    assert body["enabled"] is False and body["name"] == "Allow all"
    assert not {"id", "index", "metadata"} & set(body)
    # The write key, never the read key, authenticates the write.
    assert put[2]["headers"]["X-API-KEY"] == "write-key"
    assert put[2]["allow_redirects"] is False
    # The change is proven by a read-back GET after the PUT.
    assert [c[0] for c in session.calls][-1] == "GET"


async def test_disable_policy_refuses_without_write_key_or_flag(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    runtime.store.async_update_settings(unifi_network_write_enabled=True, unifi_network_host="10.0.0.1")
    with pytest.raises(UniFiError, match="write"):
        await unifi.async_disable_firewall_policy(hass, runtime.store, runtime.secrets, "pol-1")
    await runtime.secrets.async_set(CONF_UNIFI_NETWORK_WRITE_API_KEY, "write-key")
    runtime.store.async_update_settings(unifi_network_write_enabled=False)
    with pytest.raises(UniFiError, match="write"):
        await unifi.async_disable_firewall_policy(hass, runtime.store, runtime.secrets, "pol-1")


async def test_disable_policy_refuses_a_non_token_id(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    runtime = entry.runtime_data
    await _enable_write(entry)
    with pytest.raises(UniFiError, match="plain token"):
        await unifi.async_disable_firewall_policy(hass, runtime.store, runtime.secrets, "../sites")


async def test_disable_policy_fails_when_read_back_still_enabled(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    runtime = entry.runtime_data
    await _enable_write(entry)
    session = _WriteSession()
    original_put = session.put

    def stubborn_put(url, **kwargs):
        resp = original_put(url, **kwargs)
        session.enabled = True
        return resp

    session.put = stubborn_put  # type: ignore[method-assign]
    with patch.object(unifi, "async_get_clientsession", return_value=session):
        with pytest.raises(UniFiError, match="still reports"):
            await unifi.async_disable_firewall_policy(hass, runtime.store, runtime.secrets, "pol-1")


def test_validate_write_config() -> None:
    unifi.validate_write_config({CONF_UNIFI_NETWORK_WRITE_ENABLED: False}, {})
    with pytest.raises(vol.Invalid, match="host"):
        unifi.validate_write_config({CONF_UNIFI_NETWORK_WRITE_ENABLED: True}, {})
    with pytest.raises(vol.Invalid, match="write-scoped"):
        unifi.validate_write_config(
            {CONF_UNIFI_NETWORK_WRITE_ENABLED: True, CONF_UNIFI_NETWORK_HOST: "10.0.0.1"}, {}
        )
    unifi.validate_write_config(
        {CONF_UNIFI_NETWORK_WRITE_ENABLED: True, CONF_UNIFI_NETWORK_HOST: "10.0.0.1"},
        {CONF_UNIFI_NETWORK_WRITE_API_KEY: "k"},
    )


async def test_ws_suggestion_set_records_and_audits(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_network_security_suggestion_set(hass, connection, {"id": 1, "finding_id": "f1", "status": "planned"})
    await hass.async_block_till_done()
    connection.send_result.assert_called_once_with(1, {"ok": True})
    assert entry.runtime_data.store.data["network_suggestions"]["f1"]["status"] == "planned"


async def test_ws_suggestion_apply_is_owner_only(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection(owner=False)
    with pytest.raises(Unauthorized):
        await ws_network_security_suggestion_apply(hass, connection, {"id": 1, "finding_id": "f1"})


async def test_ws_suggestion_apply_reports_refusal(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    connection = _connection()
    ws_network_security_suggestion_apply(hass, connection, {"id": 1, "finding_id": "f1"})
    await hass.async_block_till_done()
    connection.send_error.assert_called_once()
    assert connection.send_error.call_args[0][1:] == ("suggestion_apply_rejected", "write_disabled")
