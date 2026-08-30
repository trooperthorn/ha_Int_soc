"""Sprint 4 scanner behaviors (work plan item 4.8): robustness against
pathological files, honest per-domain coverage, findings reconciliation,
the deterministic size-descending file cap, the install-scan toggle, and
the two rule extensions (os.system/os.popen, AnnAssign).
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import ConfigEntryChange
from homeassistant.core import HomeAssistant

from custom_components.ha_soc import scanner as scanner_mod
from custom_components.ha_soc.scanner import (
    MAX_FILES_PER_SCAN,
    IntegrationScanner,
    _rule_hardcoded_credential,
    _rule_insecure_deserialization,
    _rule_shell_injection_risk,
    scan_directory,
    scan_directory_report,
)
from custom_components.ha_soc.store import HaSocData

DOMAIN = "my_int"


@pytest.fixture
async def store(hass: HomeAssistant) -> HaSocData:
    data = HaSocData(hass)
    await data.async_load()
    return data


@pytest.fixture
async def scanner(hass: HomeAssistant, store: HaSocData) -> IntegrationScanner:
    return IntegrationScanner(hass, store)


def _run(rule, source: str) -> list[dict]:
    return rule(ast.parse(source), source.splitlines())


# -- Robustness ---------------------------------------------------------------


def test_scanner_survives_recursion_bomb(tmp_path: Path) -> None:
    """Two bombs, one scan: a parse-level bomb (deep parentheses drive the
    parser into RecursionError, counted as a parse failure) and a
    rule-level bomb (an attribute chain deeper than the recursion limit,
    which the iterative _dotted_name now walks flat). Neither may cost
    the other file its scan."""
    (tmp_path / "parse_bomb.py").write_text(
        "x = " + "(" * 100_000 + "1" + ")" * 100_000 + "\n", encoding="utf-8"
    )
    chain_bomb = "value = obj" + ".attr" * 3000 + ".load(data)\n"
    (tmp_path / "chain_bomb.py").write_text(chain_bomb, encoding="utf-8")
    (tmp_path / "normal.py").write_text(
        'import requests\nrequests.get("https://x", verify=False)\n', encoding="utf-8"
    )

    report = scan_directory_report(tmp_path, DOMAIN)
    assert report["coverage"]["parse_failures"] == 1
    assert report["coverage"]["scanned_files"] == 2
    patterns = {f["pattern"] for f in report["findings"]}
    assert "tls_verification_disabled" in patterns


def test_deep_attribute_chain_rule_is_iterative() -> None:
    # This chain is far past the default recursion limit; the recursive
    # _dotted_name blew up on it, aborting the file.
    source = "value = obj" + ".attr" * 3000 + ".load(data)\n"
    hits = _rule_insecure_deserialization(ast.parse(source), source.splitlines())
    assert hits == []  # the owner is not pickle/yaml-like; the point is no crash


# -- Coverage honesty ---------------------------------------------------------


async def test_unscanned_domain_is_not_zero(
    hass: HomeAssistant, scanner: IntegrationScanner, tmp_path: Path
) -> None:
    """A domain never scanned has NO coverage record in the listing
    payload — the backend's half of "not scanned is never rendered as
    zero findings" (the frontend render is a later wave)."""
    payload = scanner.listing_payload()
    assert payload["coverage"] == {}
    assert "never_scanned" not in payload["coverage"]

    (tmp_path / "mod.py").write_text("x = 1\n", encoding="utf-8")
    fake_integration = SimpleNamespace(file_path=tmp_path)
    with patch.object(
        scanner_mod, "async_get_integration", new=AsyncMock(return_value=fake_integration)
    ):
        await scanner.async_scan_integration(DOMAIN)

    payload = scanner.listing_payload()
    coverage = payload["coverage"][DOMAIN]
    assert coverage["scanned_files"] == 1
    assert coverage["skipped_oversize"] == 0
    assert coverage["skipped_over_cap"] == 0
    assert coverage["parse_failures"] == 0
    assert coverage["scanned_at"]


def test_file_cap_selects_largest_files(tmp_path: Path) -> None:
    """The cap keeps the LARGEST files (size descending, deterministic),
    so a padded directory cannot push big modules out of coverage."""
    filler = "# padding line\n"
    big_name = "zz_big.py"
    # One large file sorted last by path, plus enough small ones to
    # overflow the cap.
    (tmp_path / big_name).write_text(
        'import requests\nrequests.get("https://x", verify=False)\n' + filler * 200,
        encoding="utf-8",
    )
    for index in range(MAX_FILES_PER_SCAN):
        (tmp_path / f"a_{index:04}.py").write_text("x = 1\n", encoding="utf-8")

    report = scan_directory_report(tmp_path, DOMAIN)
    assert report["coverage"]["skipped_over_cap"] == 1
    assert big_name in report["scanned_paths"]
    assert any(f["file"] == big_name for f in report["findings"])


# -- Findings reconciliation --------------------------------------------------


async def test_scanner_reconciles_findings(
    hass: HomeAssistant, scanner: IntegrationScanner, store: HaSocData, tmp_path: Path
) -> None:
    mod = tmp_path / "mod.py"
    mod.write_text('import requests\nrequests.get("https://x", verify=False)\n', encoding="utf-8")
    fake_integration = SimpleNamespace(file_path=tmp_path)

    with patch.object(
        scanner_mod, "async_get_integration", new=AsyncMock(return_value=fake_integration)
    ):
        findings = await scanner.async_scan_integration(DOMAIN)
        assert len(findings) == 1
        finding_id = findings[0]["id"]

        # The pattern is fixed: the rescan resolves the finding with the
        # honest reason.
        mod.write_text('import requests\nrequests.get("https://x")\n', encoding="utf-8")
        await scanner.async_scan_integration(DOMAIN)

    stored = store.data["scanner_findings"][finding_id]
    assert stored["status"] == "resolved"
    assert stored["resolved_reason"] == "not_found_on_rescan"


async def test_reconciliation_skips_unevaluated_files(
    hass: HomeAssistant, scanner: IntegrationScanner, store: HaSocData, tmp_path: Path
) -> None:
    """Fail-open guard: a finding whose file could not be parsed this
    pass is NOT resolved — absence from an unevaluated file is not
    evidence the pattern is gone."""
    mod = tmp_path / "mod.py"
    mod.write_text('import requests\nrequests.get("https://x", verify=False)\n', encoding="utf-8")
    fake_integration = SimpleNamespace(file_path=tmp_path)

    with patch.object(
        scanner_mod, "async_get_integration", new=AsyncMock(return_value=fake_integration)
    ):
        findings = await scanner.async_scan_integration(DOMAIN)
        finding_id = findings[0]["id"]

        # The file becomes unparseable (a bad edit): the finding must
        # survive because nothing evaluated it this pass.
        mod.write_text("def broken(:\n", encoding="utf-8")
        await scanner.async_scan_integration(DOMAIN)

    stored = store.data["scanner_findings"][finding_id]
    assert stored["status"] == "new"
    assert "resolved_reason" not in stored


# -- Install-scan toggle ------------------------------------------------------


async def test_install_scan_honors_toggle(
    hass: HomeAssistant, scanner: IntegrationScanner, store: HaSocData
) -> None:
    entry = SimpleNamespace(domain="some_domain")
    with patch.object(scanner, "_async_scan_on_install", new=AsyncMock()) as spy:
        store.data["settings"]["scanner_enabled"] = False
        scanner._on_config_entry_changed(ConfigEntryChange.ADDED, entry)
        await hass.async_block_till_done()
        spy.assert_not_called()

        store.data["settings"]["scanner_enabled"] = True
        scanner._on_config_entry_changed(ConfigEntryChange.ADDED, entry)
        await hass.async_block_till_done()
        spy.assert_awaited_once_with("some_domain")


# -- Rule extensions ----------------------------------------------------------


def test_os_system_and_popen_join_shell_rule() -> None:
    hits = _run(
        _rule_shell_injection_risk,
        'import os\nos.system(f"ping {host}")\nos.popen("ls " + user_dir)\n',
    )
    assert len(hits) == 2
    assert all(h["pattern"] == "shell_injection_risk" for h in hits)

    # A literal command through os.system is not attacker-controlled and
    # stays quiet, same as the shell=True co-condition.
    assert _run(_rule_shell_injection_risk, 'import os\nos.system("ls /tmp")\n') == []


def test_annassign_joins_credential_rule() -> None:
    hits = _run(_rule_hardcoded_credential, 'api_key: str = "hunter2secret9"\n')
    assert len(hits) == 1
    assert hits[0]["pattern"] == "hardcoded_credential"
    # The snippet is masked exactly like the plain-Assign form.
    assert "hunter2secret9" not in hits[0]["snippet"]
    assert "[redacted" in hits[0]["snippet"]

    # The CONF_* guard applies to annotated assignments too.
    assert _run(_rule_hardcoded_credential, 'CONF_PASSWORD: str = "password_key"\n') == []


def test_scan_directory_wrapper_still_returns_findings(tmp_path: Path) -> None:
    (tmp_path / "mod.py").write_text(
        'import requests\nrequests.get("https://x", verify=False)\n', encoding="utf-8"
    )
    findings = scan_directory(tmp_path, DOMAIN)
    assert len(findings) == 1
    assert findings[0]["pattern"] == "tls_verification_disabled"
