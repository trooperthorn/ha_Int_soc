"""Repository compliance-evidence automation tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.build_compliance_evidence import (
    _canonical_bytes,
    action_pinning_findings,
    build_evidence,
    write_evidence,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _write_snapshots(path: Path, *, branch_available: bool = True) -> None:
    path.mkdir()
    snapshots = {
        "repository.json": {"full_name": "trooperthorn/ha_Int_soc"},
        "branch.json": (
            {
                "protected": True,
                "required_status_checks": {
                    "enforcement_level": "everyone",
                    "contexts": [
                        "pytest (Python 3.13)",
                        "Frontend bundle matches source",
                        "HACS validation",
                        "hassfest (manifest sanity)",
                        "Frontend dependency audit",
                        "Python static security checks",
                        "ShellCheck probe boundary",
                        "CodeQL (python)",
                        "CodeQL (javascript-typescript)",
                    ],
                },
            }
            if branch_available
            else {"available": False, "reason": "not authorized"}
        ),
        "immutable_releases.json": {"enabled": True, "enforced_by_owner": False},
        "latest_release.json": {
            "tag_name": "v2026.09.01.2",
            "assets": [
                {"name": "ha_soc.zip", "digest": "sha256:" + "a" * 64},
                {"name": "SHA256SUMS", "digest": "sha256:" + "b" * 64},
            ],
        },
        "recent_workflow_runs.json": {"workflow_runs": []},
        "code_scanning_summary.json": {"open_total": 0, "by_severity": {}},
    }
    for name, value in snapshots.items():
        (path / name).write_text(json.dumps(value), encoding="utf-8")


def test_all_remote_workflow_actions_are_commit_pinned() -> None:
    assert action_pinning_findings(REPOSITORY) == []


def test_evidence_pack_is_complete_and_self_verifying(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    output = tmp_path / "output"
    _write_snapshots(snapshots)

    evidence = build_evidence(
        REPOSITORY,
        snapshots,
        repository="trooperthorn/ha_Int_soc",
        commit_sha="1" * 40,
        ref="refs/heads/main",
        run_id="123",
        generated_at="2026-09-01T00:00:00+00:00",
    )
    integrity = evidence.pop("integrity")
    assert hashlib.sha256(_canonical_bytes(evidence)).hexdigest() == integrity[
        "canonical_payload_sha256"
    ]
    evidence["integrity"] = integrity

    assert evidence["status"] == "complete"
    assert evidence["boundaries"]["runtime_home_assistant_evidence_included"] is False
    assert evidence["boundaries"]["certificate_deployment_status"].startswith("deferred")
    assert evidence["assessments"]["workflow_action_pinning"]["result"] == "pass"
    assert evidence["assessments"]["latest_release_integrity"]["result"] == "pass"

    write_evidence(output, evidence)
    assert {path.name for path in output.iterdir()} == {
        "evidence.json",
        "SUMMARY.md",
        "SHA256SUMS",
    }
    for line in (output / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        digest, name = line.split("  ", 1)
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


def test_unavailable_control_observation_is_not_a_pass(tmp_path: Path) -> None:
    snapshots = tmp_path / "snapshots"
    _write_snapshots(snapshots, branch_available=False)

    evidence = build_evidence(
        REPOSITORY,
        snapshots,
        repository="trooperthorn/ha_Int_soc",
        commit_sha="2" * 40,
        ref="refs/heads/main",
        run_id="456",
        generated_at="2026-09-01T00:00:00+00:00",
    )

    assert evidence["status"] == "partial_or_deviating"
    assert evidence["assessments"]["main_branch_protection"]["result"] == "not_observed"
    assert any("branch.json" in warning for warning in evidence["collection_warnings"])
    assert any("branch" in deviation for deviation in evidence["deviations"])


def test_workflow_automates_attested_monthly_collection() -> None:
    workflow = (REPOSITORY / ".github/workflows/compliance-evidence.yml").read_text(
        encoding="utf-8"
    )
    assert "schedule:" in workflow
    assert "actions/attest@" in workflow
    assert "actions/upload-artifact@" in workflow
    assert "Reject incomplete collection" in workflow
    assert "retention-days: 90" in workflow
