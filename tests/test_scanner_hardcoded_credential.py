"""Regression test for scanner.py's hardcoded_credential (CWE-798) rule.

Prompted by the scanner flagging its own integration:
    ha_soc  hardcoded_credential  const.py:65  medium  CWE-798
Line 65 is `CONF_NVD_API_KEY = "nvd_api_key"` — a voluptuous/config-schema
KEY NAME, not a credential value (the real, user-supplied NVD API key
lives in store.py's SettingsData, entered at runtime; nothing about its
value is in source). CONF_* is Home Assistant's own universal convention
for this (homeassistant.const.CONF_PASSWORD, CONF_API_KEY, ...), so the
same false positive would fire on virtually any integration using it.
"""
import ast
import json
from pathlib import Path

from custom_components.ha_soc.scanner import (
    IntegrationScanner,
    _rule_hardcoded_credential,
    scan_directory,
)


def _hits(source: str) -> list[dict]:
    tree = ast.parse(source)
    lines = source.splitlines()
    return _rule_hardcoded_credential(tree, lines)


def test_conf_constant_is_not_flagged() -> None:
    assert _hits('CONF_NVD_API_KEY = "nvd_api_key"\n') == []
    assert _hits('CONF_API_KEY = "api_key"\n') == []
    assert _hits('CONF_PASSWORD = "password"\n') == []


def test_real_looking_hardcoded_secret_is_still_flagged() -> None:
    hits = _hits('nvd_api_key = "AIzaSyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY"\n')
    assert len(hits) == 1
    assert hits[0]["cwe"] == "CWE-798"


def test_short_or_placeholder_values_still_excluded_regardless_of_name() -> None:
    assert _hits('api_key = "short"\n') == []
    assert _hits('api_key = "changeme"\n') == []


# A syntactically valid key-shaped literal for the masking tests below. If
# the match is real in the wild, this literal is a live credential, so the
# scanner must never store it (work plan item 1.3).
_FAKE_SECRET = "AIzaSyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY"


def test_scanner_snippet_masks_credential_value(tmp_path: Path) -> None:
    """The stored snippet is the assignment target plus a masked value; the
    matched literal appears nowhere in the finding or the GHSA export."""
    source = f'nvd_api_key = "{_FAKE_SECRET}"\n'

    # Rule level: the hit's snippet is already the masked form.
    hits = _hits(source)
    assert len(hits) == 1
    assert hits[0]["snippet"] == f'nvd_api_key = "[redacted, {len(_FAKE_SECRET)} chars]"'
    assert _FAKE_SECRET not in json.dumps(hits[0])

    # End to end: the finding built by a directory scan (the exact dict the
    # store persists and every WebSocket listing returns) carries only the
    # masked snippet, and so does the GHSA export text shaped from it.
    (tmp_path / "leaky.py").write_text(source, encoding="utf-8")
    findings = scan_directory(tmp_path, "leaky_domain")
    assert len(findings) == 1
    finding = findings[0]
    assert finding["pattern"] == "hardcoded_credential"
    assert _FAKE_SECRET not in json.dumps(finding)
    assert finding["snippet"] == f'nvd_api_key = "[redacted, {len(_FAKE_SECRET)} chars]"'

    # export_ghsa reads nothing but the finding dict, so constructing the
    # scanner without __init__ keeps this test free of a running hass.
    scanner = IntegrationScanner.__new__(IntegrationScanner)
    export = scanner.export_ghsa(finding)
    assert _FAKE_SECRET not in json.dumps(export)
    assert "[redacted," in export["description"]


def test_key_name_constant_is_not_a_credential() -> None:
    """A *_KEY constant naming a storage or dict key is the convention the
    secret store itself uses; the finding must not fire on the key NAME,
    while a digit-bearing value under the same naming still fires."""
    from custom_components.ha_soc.scanner import _rule_hardcoded_credential
    import ast

    src = (
        'PROBE_PAIRING_SECRET_KEY = "probe_pairing_secret"\n'
        'API_KEY = "hunter2secret9"\n'
        'api_key = "looks_like_a_key_name"\n'
    )
    hits = _rule_hardcoded_credential(ast.parse(src), src.splitlines())
    lines = sorted(h["lineno"] for h in hits)
    # Line 2 fires on its digits despite the ALL_CAPS *_KEY name; line 3
    # fires because a lowercase variable is outside the constant-name
    # guard entirely, whatever shape its value has.
    assert lines == [2, 3], hits
