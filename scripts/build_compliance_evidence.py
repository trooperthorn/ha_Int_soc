"""Build a redacted, machine-verifiable repository compliance evidence pack.

The GitHub workflow supplies normalized API snapshots.  This module combines
them with immutable hashes of the repository's control documents and workflow
definitions.  It deliberately does not claim certification or collect Home
Assistant runtime data, credentials, private addresses, or raw security-alert
details.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SCHEMA_VERSION = "1.0"
CONTROL_DOCUMENTS = (
    "SECURITY.md",
    "docs/COMPLIANCE-EVIDENCE-PLAN.md",
    "docs/NIST-SOC2-CONTROL-MATRIX.md",
    "docs/THREAT-MODEL.md",
    "docs/TRANSPORT-SECURITY-MIGRATION.md",
    "docs/PKI-CERTIFICATE-TEMPLATE-SECURITY-RESEARCH.md",
)
SNAPSHOTS = (
    "repository.json",
    "branch.json",
    "immutable_releases.json",
    "latest_release.json",
    "recent_workflow_runs.json",
    "code_scanning_summary.json",
)
OPTIONAL_SNAPSHOTS = {"immutable_releases.json"}
REQUIRED_STATUS_CHECKS = {
    "pytest (Python 3.13)",
    "Frontend bundle matches source",
    "HACS validation",
    "hassfest (manifest sanity)",
    "Frontend dependency audit",
    "Python static security checks",
    "ShellCheck probe boundary",
    "CodeQL (python)",
    "CodeQL (javascript-typescript)",
}
_PINNED_ACTION_REF = re.compile(r"^[0-9a-f]{40}$")
_USES = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _hashed_files(root: Path, paths: Iterable[str]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relative in sorted(paths):
        path = root / relative
        if not path.is_file():
            continue
        records.append(
            {
                "path": relative.replace("\\", "/"),
                "sha256": _sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    return records


def action_pinning_findings(root: Path) -> list[dict[str, str]]:
    """Return every remote workflow action that is not pinned to a full SHA."""
    findings: list[dict[str, str]] = []
    for workflow in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        text = workflow.read_text(encoding="utf-8")
        for reference in _USES.findall(text):
            if reference.startswith("./") or reference.startswith("docker://"):
                continue
            action, separator, revision = reference.rpartition("@")
            if not separator or not action or not _PINNED_ACTION_REF.fullmatch(revision):
                findings.append(
                    {
                        "path": workflow.relative_to(root).as_posix(),
                        "reference": reference,
                    }
                )
    return findings


def _load_snapshot(path: Path) -> tuple[Any, str | None]:
    if not path.is_file():
        return {"available": False, "reason": "snapshot file missing"}, "missing"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return {
            "available": False,
            "reason": f"snapshot is not valid JSON: {type(err).__name__}",
        }, "invalid"
    if isinstance(value, dict) and value.get("available") is False:
        return value, str(value.get("reason", "API unavailable"))
    return value, None


def _manifest_version(root: Path) -> tuple[str, dict[str, Any]]:
    manifest_path = root / "custom_components" / "ha_soc" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return str(manifest["version"]), {
        "path": manifest_path.relative_to(root).as_posix(),
        "sha256": _sha256_file(manifest_path),
    }


def _test_inventory(root: Path) -> dict[str, int]:
    files = sorted((root / "tests").glob("test_*.py"))
    test_functions = 0
    for path in files:
        test_functions += len(
            re.findall(
                r"^\s*(?:async\s+)?def\s+test_",
                path.read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        )
    return {"files": len(files), "test_functions": test_functions}


def _branch_assessment(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("available") is False:
        return {"result": "not_observed", "observed_status_checks": []}
    required = snapshot.get("required_status_checks")
    if not isinstance(required, dict):
        required = {}
    observed = sorted(str(item) for item in required.get("contexts", []))
    missing = sorted(REQUIRED_STATUS_CHECKS.difference(observed))
    protected = snapshot.get("protected") is True
    enforcement = required.get("enforcement_level")
    passed = protected and enforcement == "everyone" and not missing
    return {
        "result": "pass" if passed else "deviation",
        "protected": protected,
        "status_check_enforcement": enforcement,
        "observed_status_checks": observed,
        "missing_expected_status_checks": missing,
    }


def _release_assessment(snapshot: Any) -> dict[str, Any]:
    if not isinstance(snapshot, dict) or snapshot.get("available") is False:
        return {"result": "not_observed"}
    assets = snapshot.get("assets")
    if not isinstance(assets, list) or not assets:
        return {"result": "deviation", "reason": "latest release has no assets"}
    without_digest = sorted(
        str(asset.get("name", "unknown"))
        for asset in assets
        if not isinstance(asset, dict)
        or not str(asset.get("digest", "")).startswith("sha256:")
    )
    return {
        "result": "pass" if not without_digest else "deviation",
        "tag": snapshot.get("tag_name"),
        "asset_count": len(assets),
        "assets_without_sha256_digest": without_digest,
    }


def build_evidence(
    root: Path,
    snapshot_dir: Path,
    *,
    repository: str,
    commit_sha: str,
    ref: str,
    run_id: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the evidence payload without writing it."""
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    version, manifest_record = _manifest_version(root)
    workflows = sorted(
        path.relative_to(root).as_posix()
        for path in (root / ".github" / "workflows").glob("*.y*ml")
    )
    snapshots: dict[str, Any] = {}
    warnings: list[str] = []
    for name in SNAPSHOTS:
        value, warning = _load_snapshot(snapshot_dir / name)
        snapshots[name.removesuffix(".json")] = value
        if warning and name not in OPTIONAL_SNAPSHOTS:
            warnings.append(f"{name}: {warning}")

    unpinned = action_pinning_findings(root)
    immutable = snapshots["immutable_releases"]
    immutable_enabled = isinstance(immutable, dict) and immutable.get("enabled") is True
    branch_assessment = _branch_assessment(snapshots["branch"])
    release_assessment = _release_assessment(snapshots["latest_release"])
    deviations = []
    if unpinned:
        deviations.append("one or more workflow actions are not pinned to a full commit SHA")
    if branch_assessment["result"] != "pass":
        deviations.append("expected protected main-branch status checks were not fully observed")
    if release_assessment["result"] != "pass":
        deviations.append("latest release assets were not fully covered by SHA-256 digests")

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "scope": {
            "repository": repository,
            "commit_sha": commit_sha,
            "ref": ref,
            "workflow_run_id": run_id,
            "evidence_type": "repository_and_ci_point_in_time",
        },
        "component": {"name": "HA SOC", "version": version, "manifest": manifest_record},
        "boundaries": {
            "certification_claim": False,
            "runtime_home_assistant_evidence_included": False,
            "secrets_or_private_network_data_included": False,
            "certificate_deployment_status": "deferred_for_security_template_research",
            "immutable_setting_observation": (
                "The settings endpoint requires Administration-read permission. It is collected "
                "when COMPLIANCE_ADMIN_TOKEN is configured; otherwise not_observed is an explicit "
                "scope boundary and release asset integrity is still assessed."
            ),
            "artifact_retention_note": (
                "GitHub Actions retains this transport artifact for 90 days; copy it to the "
                "approved evidence repository for the organization's longer retention period."
            ),
        },
        "repository_files": {
            "control_documents": _hashed_files(root, CONTROL_DOCUMENTS),
            "workflows": _hashed_files(root, workflows),
            "dependabot": _hashed_files(root, (".github/dependabot.yml",)),
            "tests": _test_inventory(root),
        },
        "github_observations": snapshots,
        "assessments": {
            "workflow_action_pinning": {
                "result": "pass" if not unpinned else "deviation",
                "unpinned_references": unpinned,
            },
            "main_branch_protection": branch_assessment,
            "immutable_releases": {
                "result": "pass" if immutable_enabled else "not_observed",
                "enabled": immutable_enabled,
            },
            "latest_release_integrity": release_assessment,
        },
        "control_support": [
            {
                "nist_800_53": ["CA-7", "CM-2", "CM-3", "SA-11", "SI-2", "SI-7", "SR-4"],
                "soc_2": ["CC4.1", "CC7.1", "CC8.1", "CC9.1"],
                "evidence": (
                    "repository file hashes, branch protection, CI runs, "
                    "scanning summary, and release integrity"
                ),
            }
        ],
        "collection_warnings": sorted(warnings),
        "deviations": sorted(deviations),
        "status": "complete" if not warnings and not deviations else "partial_or_deviating",
    }
    payload["integrity"] = {
        "canonical_payload_sha256": _sha256_bytes(_canonical_bytes(payload)),
        "verification": (
            "Remove the top-level integrity member, serialize as sorted compact UTF-8 JSON, "
            "and compare its SHA-256 digest."
        ),
    }
    return payload


def _summary(evidence: dict[str, Any]) -> str:
    assessments = evidence["assessments"]
    lines = [
        "# HA SOC Compliance Evidence Summary",
        "",
        f"- Generated: `{evidence['generated_at']}`",
        f"- Repository: `{evidence['scope']['repository']}`",
        f"- Commit: `{evidence['scope']['commit_sha']}`",
        f"- Component version: `{evidence['component']['version']}`",
        f"- Collection status: `{evidence['status']}`",
        f"- Workflow action pinning: `{assessments['workflow_action_pinning']['result']}`",
        f"- Main branch protection: `{assessments['main_branch_protection']['result']}`",
        f"- Immutable releases: `{assessments['immutable_releases']['result']}`",
        f"- Latest release integrity: `{assessments['latest_release_integrity']['result']}`",
        "",
        "This engineering evidence supports control assessment; it is not a SOC 2",
        "attestation, NIST certification, penetration test, or runtime Home Assistant",
        "evidence pack. Certificate deployment remains deferred.",
    ]
    if evidence["collection_warnings"]:
        lines.extend(("", "## Collection warnings", ""))
        lines.extend(f"- {item}" for item in evidence["collection_warnings"])
    if evidence["deviations"]:
        lines.extend(("", "## Deviations", ""))
        lines.extend(f"- {item}" for item in evidence["deviations"])
    return "\n".join(lines) + "\n"


def write_evidence(output_dir: Path, evidence: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / "evidence.json"
    summary_path = output_dir / "SUMMARY.md"
    evidence_path.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary_path.write_text(_summary(evidence), encoding="utf-8")
    checksum_lines = [
        f"{_sha256_file(path)}  {path.name}"
        for path in (evidence_path, summary_path)
    ]
    (output_dir / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    evidence = build_evidence(
        args.repository_root.resolve(),
        args.snapshot_dir.resolve(),
        repository=args.repository,
        commit_sha=args.sha,
        ref=args.ref,
        run_id=args.run_id,
        generated_at=args.generated_at,
    )
    write_evidence(args.output_dir.resolve(), evidence)
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"partial={'true' if evidence['status'] != 'complete' else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
