"""Release archive integrity tests."""

from __future__ import annotations

import json
from pathlib import Path
import zipfile

from scripts.build_release_artifacts import build_archive, validate_versions


REPOSITORY = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = json.loads(
    (REPOSITORY / "custom_components/ha_soc/manifest.json").read_text(encoding="utf-8")
)["version"]


def test_component_versions_match() -> None:
    assert validate_versions(REPOSITORY) == EXPECTED_VERSION


def test_release_zip_is_reproducible_and_hacs_compatible(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_version, first_digest = build_archive(REPOSITORY, first)
    second_version, second_digest = build_archive(REPOSITORY, second)

    assert first_version == second_version == EXPECTED_VERSION
    assert first_digest == second_digest
    assert first.read_bytes() == second.read_bytes()

    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        assert "manifest.json" in names
        assert "__init__.py" in names
        assert not any(name.startswith("custom_components/") for name in names)
        assert not any("__pycache__" in name for name in names)
        assert archive.comment == f"HA SOC {EXPECTED_VERSION}".encode("ascii")
