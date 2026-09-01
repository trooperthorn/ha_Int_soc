#!/usr/bin/env python3
"""Build the deterministic HACS release archive for HA SOC.

The archive deliberately contains the contents of ``custom_components/ha_soc``
at its root.  That is the layout HACS expects when ``zip_release`` is enabled.
Stable ordering, timestamps, permissions, and compression make the same source
tree produce the same SHA-256 digest on every runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

_VERSION_RE = re.compile(r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_SKIP_PARTS = {"__pycache__", "node_modules"}


def _read_versions(repository: Path) -> dict[str, str]:
    manifest = json.loads(
        (repository / "custom_components/ha_soc/manifest.json").read_text(
            encoding="utf-8"
        )
    )["version"]
    probe_text = (repository / "ha_soc_probe/config.yaml").read_text(
        encoding="utf-8"
    )
    scanner_text = (
        repository / "ha_soc_probe/rootfs/etc/services.d/ha_soc_probe/run"
    ).read_text(encoding="utf-8")

    probe_match = re.search(r'^version:\s*"([^"]+)"', probe_text, re.MULTILINE)
    scanner_match = re.search(
        r'^SCANNER_VERSION="([^"]+)"', scanner_text, re.MULTILINE
    )
    return {
        "manifest": manifest,
        "probe": probe_match.group(1) if probe_match else "<missing>",
        "scanner": scanner_match.group(1) if scanner_match else "<missing>",
    }


def validate_versions(repository: Path) -> str:
    """Return the common component version or raise on drift."""
    versions = _read_versions(repository)
    distinct = set(versions.values())
    if len(distinct) != 1:
        rendered = ", ".join(f"{name}={value}" for name, value in versions.items())
        raise ValueError(f"Component versions do not match: {rendered}")
    version = versions["manifest"]
    if not _VERSION_RE.fullmatch(version):
        raise ValueError(f"Invalid release version: {version}")
    return version


def _release_files(source: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in source.rglob("*")
            if path.is_file()
            and not _SKIP_PARTS.intersection(path.relative_to(source).parts)
            and path.suffix not in {".pyc", ".pyo"}
        ),
        key=lambda path: path.relative_to(source).as_posix(),
    )


def build_archive(repository: Path, output: Path) -> tuple[str, str]:
    """Build ``output`` and return ``(version, sha256)``."""
    repository = repository.resolve()
    source = repository / "custom_components/ha_soc"
    version = validate_versions(repository)
    files = _release_files(source)
    if not files or source / "manifest.json" not in files:
        raise ValueError("Integration release source is empty or missing manifest.json")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        archive.comment = f"HA SOC {version}".encode("ascii")
        for path in files:
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=_FIXED_ZIP_TIME)
            info.create_system = 3
            executable = bool(path.stat().st_mode & stat.S_IXUSR)
            mode = 0o100755 if executable else 0o100644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.flag_bits |= 0x800  # UTF-8 file names
            archive.writestr(info, path.read_bytes(), compresslevel=9)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return version, digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to this script's repository)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/ha_soc.zip"),
        help="release archive path",
    )
    args = parser.parse_args()

    output = args.output
    if not output.is_absolute():
        output = args.repository / output
    version, digest = build_archive(args.repository, output)
    print(f"archive={output}")
    print(f"version={version}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
