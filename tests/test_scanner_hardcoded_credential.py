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

from custom_components.ha_soc.scanner import _rule_hardcoded_credential


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
