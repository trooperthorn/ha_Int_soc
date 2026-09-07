"""ha_soc.ingest_audit: Supervisor gate, per-source secret, chain verification, detection."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.const import HASSIO_USER_NAME
from homeassistant.core import Context, HomeAssistant

from custom_components.ha_soc.const import DOMAIN
from custom_components.ha_soc.detections import RULE_EXTERNAL_AUDIT_CHAIN_BREAK
from custom_components.ha_soc.external_audit import (
    CATEGORY_CHAIN_BREAK,
    CATEGORY_RECORD,
    CATEGORY_REJECTED,
    record_digest,
)

SECRET = "unit-test-ingest-secret-0001"


def make_chain(n: int, start: int = 1, previous: str = "") -> list[dict[str, Any]]:
    """Records the way the Elk Programmer writes them."""
    out = []
    for i in range(start, start + n):
        record: dict[str, Any] = {
            "seq": i,
            "time": f"2026-09-06T23:00:{i:02d}Z",
            "event": "record_sent" if i % 2 else "login",
            "user_id": "user-1",
            "user_name": "Alice",
            "details": {"table": "zone", "number": i},
            "previous": previous,
        }
        content = {k: record[k] for k in ("time", "event", "user_id", "user_name", "details", "previous")}
        digest = hashlib.sha256(
            (json.dumps(content, sort_keys=True, separators=(",", ":")) + previous).encode()
        ).hexdigest()
        record["hash"] = digest
        previous = digest
        out.append(record)
    return out


@pytest.fixture
async def supervisor_user(hass: HomeAssistant):
    return await hass.auth.async_create_system_user(HASSIO_USER_NAME, group_ids=[GROUP_ID_ADMIN])


@pytest.fixture
async def supervisor_entry(hass: HomeAssistant, supervisor_user, tmp_path) -> MockConfigEntry:
    # The audit files live under the config directory; give each test its own.
    hass.config.config_dir = str(tmp_path)
    with (
        patch("custom_components.ha_soc.probe.is_hassio", return_value=True),
        patch("custom_components.ha_soc.external_audit.is_hassio", return_value=True),
    ):
        entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


@pytest.fixture
def ctx(supervisor_user) -> Context:
    return Context(user_id=supervisor_user.id)


async def _call(hass: HomeAssistant, ctx: Context, **data: Any) -> dict[str, Any]:
    payload = {"source": "elk_programmer", "secret": SECRET, **data}
    result = await hass.services.async_call(
        DOMAIN, "ingest_audit", payload, blocking=True, context=ctx, return_response=True
    )
    assert result is not None
    return result


async def _records(entry: MockConfigEntry, category: str) -> list[dict[str, Any]]:
    return await entry.runtime_data.audit.async_query(category=category, limit=100)


async def test_not_registered_off_supervisor(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={}, title="HA SOC")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "ingest_audit")


async def test_digest_matches_the_programmer_algorithm() -> None:
    chain = make_chain(2)
    assert record_digest(chain[0]) == chain[0]["hash"]
    assert chain[1]["previous"] == chain[0]["hash"]
    assert record_digest(chain[1]) == chain[1]["hash"]


async def test_non_supervisor_and_bad_secret_are_rejected_and_audited(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, ctx: Context
) -> None:
    chain = make_chain(1)
    other = await hass.auth.async_create_system_user("Other", group_ids=[GROUP_ID_ADMIN])
    result = await hass.services.async_call(
        DOMAIN,
        "ingest_audit",
        {"source": "elk_programmer", "secret": SECRET, "records": chain},
        blocking=True,
        context=Context(user_id=other.id),
        return_response=True,
    )
    assert result == {"accepted": 0, "last_seq": None, "rejected": "not_supervisor"}
    assert await _call(hass, ctx, records=chain) == {"accepted": 1, "last_seq": 1, "rejected": None}
    result = await _call(hass, ctx, secret="a-different-secret-value", records=make_chain(1, 2, chain[0]["hash"]))
    assert result["rejected"] == "bad_secret"
    rejected = await _records(supervisor_entry, CATEGORY_REJECTED)
    assert [r["detail"]["reason"] for r in rejected] == ["bad_secret", "not_supervisor"]
    assert (await _records(supervisor_entry, CATEGORY_RECORD))[0]["user_id"] == "user-1"


async def test_chain_accepted_across_calls_replays_ignored_gaps_flagged(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, ctx: Context
) -> None:
    chain = make_chain(5)
    assert (await _call(hass, ctx, records=chain[:3]))["accepted"] == 3
    # A replay of records 2 and 3 plus the new 4 accepts only 4.
    assert await _call(hass, ctx, records=chain[1:4]) == {"accepted": 1, "last_seq": 4, "rejected": None}
    # Record 5 never arrives; 6 links to it, which cannot be verified, so it is a break
    # and the response tells the source where to resume.
    later = make_chain(2, 6, chain[4]["hash"])
    result = await _call(hass, ctx, records=later)
    assert result == {"accepted": 0, "last_seq": 4, "rejected": "gap"}
    breaks = await _records(supervisor_entry, CATEGORY_CHAIN_BREAK)
    assert breaks[0]["detail"]["reason"] == "gap" and breaks[0]["detail"]["expected_seq"] == 5
    # Resending from 5 heals it.
    assert (await _call(hass, ctx, records=chain[4:] + later))["accepted"] == 3
    records = await _records(supervisor_entry, CATEGORY_RECORD)
    assert [r["detail"]["source_seq"] for r in records] == [7, 6, 5, 4, 3, 2, 1]
    head = supervisor_entry.runtime_data.store.external_audit_head("elk_programmer")
    assert head["seq"] == 7 and head["hash"] == later[-1]["hash"]


async def test_tampered_record_breaks_the_chain_and_raises_a_detection(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, ctx: Context
) -> None:
    chain = make_chain(3)
    chain[1]["details"]["number"] = 99  # edited after hashing
    result = await _call(hass, ctx, records=chain)
    assert result == {"accepted": 1, "last_seq": 1, "rejected": "hash_mismatch"}
    breaks = await _records(supervisor_entry, CATEGORY_CHAIN_BREAK)
    assert breaks[0]["detail"]["reason"] == "hash_mismatch"
    assert breaks[0]["detail"]["accepted_before_break"] == 1
    # Rewriting history under an already accepted sequence number is its own reason.
    forged = make_chain(1)
    forged[0]["details"]["number"] = 42
    forged[0]["hash"] = record_digest(forged[0])
    assert (await _call(hass, ctx, records=forged))["rejected"] == "rewritten_history"
    touched = await supervisor_entry.runtime_data.detections.async_run_pass()
    ours = [d for d in touched if d["rule_id"] == RULE_EXTERNAL_AUDIT_CHAIN_BREAK]
    assert ours and ours[0]["severity"] == "high"
    assert ours[0]["detail"]["source"] == "elk_programmer"


async def test_sources_have_independent_secrets_and_heads(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry, ctx: Context
) -> None:
    assert (await _call(hass, ctx, records=make_chain(1)))["accepted"] == 1
    other = await _call(hass, ctx, source="other_tool", secret="another-tool-secret-0001", records=make_chain(2))
    assert other == {"accepted": 2, "last_seq": 2, "rejected": None}
    wrong = await _call(hass, ctx, source="other_tool", secret=SECRET, records=make_chain(1, 3))
    assert wrong["rejected"] == "bad_secret"
    store = supervisor_entry.runtime_data.store
    assert store.external_audit_head("elk_programmer")["seq"] == 1
    assert store.external_audit_head("other_tool")["seq"] == 2


async def test_programming_session_events_are_audited(
    hass: HomeAssistant, supervisor_entry: MockConfigEntry
) -> None:
    hass.bus.async_fire(
        "elkm1.programming_started",
        {"source": "elk_programmer", "user": "user-1", "purpose": "programming", "attributed": True},
    )
    hass.bus.async_fire(
        "elkm1.programming_ended",
        {"source": "unattributed", "user": "", "attributed": False, "rp_seen": True},
    )
    await hass.async_block_till_done()
    records = await _records(supervisor_entry, "programming_session")
    assert [r["detail"]["phase"] for r in records] == ["ended", "started"]
    assert records[1]["user_id"] == "user-1"
    assert records[0]["detail"]["attributed"] is False
