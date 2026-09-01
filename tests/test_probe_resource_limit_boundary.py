"""Executable regression tests for the Probe's privileged Docker boundary."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


HELPER = (
    Path(__file__).parents[1]
    / "ha_soc_probe"
    / "rootfs"
    / "usr"
    / "lib"
    / "ha_soc"
    / "resource_limits.sh"
)


def _run(function: str, payload: object) -> subprocess.CompletedProcess[str]:
    bash = shutil.which("bash")
    jq = shutil.which("jq")
    if bash is None or jq is None:
        pytest.skip("Probe boundary execution needs bash and jq")
    return subprocess.run(
        [bash, "-c", f'source "$1"; {function}', "ha-soc-test", str(HELPER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"../escape": {"memory_mb": 512}},
        {"safe": "not-an-object"},
        {"safe": {"memory_mb": "64+$(id)", "cpus": 1}},
        {"safe": {"memory_mb": 63}},
        {"safe": {"memory_mb": 1048577}},
        {"safe": {"cpus": 0.09}},
        {"safe": {"cpus": 65}},
        {"safe": {"memory_mb": None, "cpus": None}},
        {"safe": {"memory_mb": 512, "unknown": 1}},
        {f"addon_{i}": {"memory_mb": 64} for i in range(129)},
    ],
)
def test_invalid_limit_document_is_rejected(payload: object) -> None:
    result = _run("validate_resource_limits", payload)
    assert result.returncode != 0


def test_valid_limit_document_and_docker_body_are_canonical() -> None:
    payload = {"a0d7b954_zwavejs": {"memory_mb": 512, "cpus": 1.5}}
    validated = _run("validate_resource_limits", payload)
    assert validated.returncode == 0
    assert json.loads(validated.stdout) == payload

    body = _run(
        "docker_body_for_resource_limit",
        {"memory_mb": 512, "cpus": 1.5},
    )
    assert body.returncode == 0
    assert json.loads(body.stdout) == {
        "Memory": 536870912,
        "MemorySwap": 536870912,
        "NanoCpus": 1500000000,
    }


def test_applied_slug_state_rejects_injection_tokens() -> None:
    result = _run(
        "validate_applied_resource_slugs",
        ["safe", "../var/run/docker.sock", "$(id)"],
    )
    assert result.returncode != 0
