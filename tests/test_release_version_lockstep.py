"""Release identifiers must stay synchronized across all shipped components."""

from __future__ import annotations

import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_release_versions_are_in_lockstep() -> None:
    manifest = json.loads(
        (ROOT / "custom_components/ha_soc/manifest.json").read_text(encoding="utf-8")
    )["version"]
    probe_text = (ROOT / "ha_soc_probe/config.yaml").read_text(encoding="utf-8")
    scanner_text = (
        ROOT / "ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run"
    ).read_text(encoding="utf-8")

    probe_match = re.search(r'^version:\s*"([^"]+)"', probe_text, re.MULTILINE)
    scanner_match = re.search(
        r'^SCANNER_VERSION="([^"]+)"', scanner_text, re.MULTILINE
    )

    assert probe_match is not None, "Probe version is missing from config.yaml"
    assert scanner_match is not None, "SCANNER_VERSION is missing from the Probe"
    versions = {
        "manifest": manifest,
        "probe": probe_match.group(1),
        "scanner": scanner_match.group(1),
    }
    assert len(set(versions.values())) == 1, f"Release version drift: {versions}"
