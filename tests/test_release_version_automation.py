"""CalVer calculation, synchronized writes, and workflow safety contracts."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import stat

from scripts.build_release_artifacts import validate_versions
from scripts.set_version import next_calver, parse_calver, set_version


ROOT = Path(__file__).resolve().parents[1]


def _version_fixture(tmp_path: Path, version: str = "2026.09.02.2") -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / ".release.json").write_text(
        (ROOT / ".release.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    manifest = repository / "custom_components/ha_soc/manifest.json"
    probe = repository / "ha_soc_probe/config.yaml"
    scanner = repository / "ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run"
    manifest.parent.mkdir(parents=True)
    probe.parent.mkdir(parents=True)
    scanner.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"domain": "ha_soc", "version": version}, indent=2) + "\n",
        encoding="utf-8",
    )
    probe.write_text(f'name: HA SOC Probe\nversion: "{version}"\n', encoding="utf-8")
    scanner.write_text(
        f'#!/usr/bin/with-contenv bashio\nSCANNER_VERSION="{version}"\n',
        encoding="utf-8",
    )
    return repository


def test_next_calver_uses_highest_sequence_for_release_date() -> None:
    assert next_calver(
        [
            "v2026.09.01.9",
            "v2026.09.02.1",
            "2026.09.02.4",
            "not-a-release",
        ],
        date(2026, 9, 2),
    ) == "2026.09.02.5"


def test_next_calver_starts_new_day_at_one() -> None:
    assert next_calver(["v2026.09.02.8"], date(2026, 9, 3)) == "2026.09.03.1"


def test_parse_calver_rejects_invalid_versions() -> None:
    for value in (
        "2026.02.30.1",
        "2026.9.02.1",
        "2026.09.02.0",
        "v2026.09.02.1",
    ):
        try:
            parse_calver(value)
        except ValueError:
            continue
        raise AssertionError(f"Invalid version was accepted: {value}")


def test_set_version_updates_every_shipped_identifier(tmp_path: Path) -> None:
    repository = _version_fixture(tmp_path)
    scanner = repository / "ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run"
    scanner.chmod(0o755)
    original_mode = stat.S_IMODE(scanner.stat().st_mode)

    set_version(repository, "2026.09.02.3")

    assert validate_versions(repository) == "2026.09.02.3"
    assert stat.S_IMODE(scanner.stat().st_mode) == original_mode


def test_prepare_release_workflow_preserves_protected_main() -> None:
    workflow = (ROOT / ".github/workflows/prepare-release.yml").read_text(
        encoding="utf-8"
    )
    assert 'workflows: ["Release"]' in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert "actions/create-github-app-token@" in workflow
    assert "RELEASE_AUTOMATION_CLIENT_ID" in workflow
    assert "RELEASE_AUTOMATION_PRIVATE_KEY" in workflow
    assert "--force-with-lease" in workflow
    assert "permission-contents: write" in workflow
    assert "permission-pull-requests: write" in workflow
    assert 'gh pr merge "$PR_NUMBER" --auto --squash' in workflow
    assert "git push origin main" not in workflow
