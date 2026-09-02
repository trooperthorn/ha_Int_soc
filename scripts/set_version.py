#!/usr/bin/env python3
"""Calculate and apply synchronized HA SOC CalVer release versions.

The release identifier is stored in three shipped components.  This module is
the only writer for those fields; ``build_release_artifacts.validate_versions``
remains the independent reader used by the release gate.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if __package__ in {None, ""}:  # Support direct ``python scripts/set_version.py`` use.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_release_artifacts import validate_versions


_CALVER_RE = re.compile(
    r"^(?P<year>[0-9]{4})\.(?P<month>[0-9]{2})\.(?P<day>[0-9]{2})\."
    r"(?P<sequence>[1-9][0-9]*)$"
)
_PROBE_VERSION_RE = re.compile(r'^version:\s*"[^"]+"', re.MULTILINE)
_SCANNER_VERSION_RE = re.compile(r'^SCANNER_VERSION="[^"]+"', re.MULTILINE)


def parse_calver(value: str) -> tuple[date, int]:
    """Parse ``YYYY.MM.DD.N`` and reject invalid dates or zero sequences."""
    match = _CALVER_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"Invalid CalVer release version: {value}")
    release_date = date(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )
    return release_date, int(match.group("sequence"))


def next_calver(existing_versions: list[str], release_date: date) -> str:
    """Return the next sequence for ``release_date`` from existing versions."""
    sequences: list[int] = []
    for value in existing_versions:
        try:
            version_date, sequence = parse_calver(value.removeprefix("v"))
        except ValueError:
            continue
        if version_date == release_date:
            sequences.append(sequence)
    return f"{release_date:%Y.%m.%d}.{max(sequences, default=0) + 1}"


def versions_from_git_tags(repository: Path) -> list[str]:
    """Read immutable version candidates from the repository's local tags."""
    result = subprocess.run(
        ["git", "tag", "--list", "v[0-9]*"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _replace_one(text: str, pattern: re.Pattern[str], replacement: str, label: str) -> str:
    updated, count = pattern.subn(replacement, text)
    if count != 1:
        raise ValueError(f"Expected exactly one {label}; found {count}")
    return updated


def set_version(repository: Path, version: str) -> None:
    """Set every shipped version field, preserving the Probe script mode."""
    parse_calver(version)
    repository = repository.resolve()
    manifest_path = repository / "custom_components/ha_soc/manifest.json"
    probe_path = repository / "ha_soc_probe/config.yaml"
    scanner_path = (
        repository / "ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run"
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest.get("version"), str):
        raise ValueError("Integration manifest has no string version")
    manifest["version"] = version
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"

    probe_text = _replace_one(
        probe_path.read_text(encoding="utf-8"),
        _PROBE_VERSION_RE,
        f'version: "{version}"',
        "Probe version",
    )
    scanner_text = _replace_one(
        scanner_path.read_text(encoding="utf-8"),
        _SCANNER_VERSION_RE,
        f'SCANNER_VERSION="{version}"',
        "SCANNER_VERSION",
    )

    manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")
    probe_path.write_text(probe_text, encoding="utf-8", newline="\n")
    scanner_path.write_text(scanner_text, encoding="utf-8", newline="\n")
    if validate_versions(repository) != version:
        raise ValueError("Version synchronization failed after writing files")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to this script's repository)",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--version", help="explicit YYYY.MM.DD.N version")
    selection.add_argument(
        "--next-from-tags",
        action="store_true",
        help="calculate today's next sequence from local Git tags",
    )
    parser.add_argument(
        "--timezone",
        default="America/Chicago",
        help="IANA timezone used with --next-from-tags",
    )
    args = parser.parse_args()

    version = args.version
    if args.next_from_tags:
        try:
            release_date = datetime.now(ZoneInfo(args.timezone)).date()
        except ZoneInfoNotFoundError as err:
            raise ValueError(f"Unknown release timezone: {args.timezone}") from err
        version = next_calver(versions_from_git_tags(args.repository), release_date)

    assert version is not None
    set_version(args.repository, version)
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
