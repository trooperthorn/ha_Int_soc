"""Regression pins for the supported, versioned UniFi Local APIs."""
from __future__ import annotations

from pathlib import Path

from custom_components.ha_soc import unifi
from custom_components.ha_soc.const import (
    UNIFI_NETWORK_API_PATH,
    UNIFI_PROTECT_API_PATH,
)


def test_local_api_base_paths_match_official_server_templates() -> None:
    assert UNIFI_NETWORK_API_PATH == "/proxy/network/integration/v1"
    assert UNIFI_PROTECT_API_PATH == "/proxy/protect/integration/v1"


def test_network_acl_uses_only_documented_10_4_57_route() -> None:
    assert unifi._ACL_ENDPOINT_SUFFIXES == ("acl-rules",)


def test_protect_7_2_105_has_no_guessed_rest_event_calls() -> None:
    source = Path(unifi.__file__).read_text(encoding="utf-8")
    for undocumented in (
        'f"/events?',
        'f"/detections?',
        'f"/alarms?',
    ):
        assert undocumented not in source
    assert "/subscribe/events" in source


def test_network_device_statistics_uses_documented_route() -> None:
    source = Path(unifi.__file__).read_text(encoding="utf-8")
    assert "/statistics/latest" in source
