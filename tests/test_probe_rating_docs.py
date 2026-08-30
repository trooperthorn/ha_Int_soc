"""The documented Supervisor rating must match what config.yaml earns.

The add-on's README and DOCS.md state, as a deliberate choice, that the
Probe's Supervisor security rating is 1. That claim must not drift: if a
future change adds or removes a grant in ha_soc_probe/config.yaml, this
test recomputes the rating the Supervisor would assign and fails when the
docs no longer tell the truth.

The algorithm is transcribed from the Supervisor's rating_security
(verified against Supervisor commit c5a5477; see
docs/HA-SOC-Security-Work-Plan.md section 6.1): start at 5; AppArmor
disabled -1 or custom profile +1; ingress +2, else no host network and no
ports +2, else auth_api +1; signed +1; any dangerous capability
(NET_ADMIN among them) or kernel modules -1; hassio_role manager -1 or
admin -2; host_network -1; host_pid -2; host_uts with SYS_ADMIN -1; then
docker_api or full_access forces the rating to 1; clamp to 1..8.
"""
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "ha_soc_probe" / "config.yaml"

DANGEROUS_CAPS = {
    "BPF",
    "CHECKPOINT_RESTORE",
    "DAC_READ_SEARCH",
    "NET_ADMIN",
    "NET_RAW",
    "PERFMON",
    "SYS_ADMIN",
    "SYS_MODULE",
    "SYS_PTRACE",
    "SYS_RAWIO",
}


def _supervisor_rating(cfg: dict) -> int:
    rating = 5

    apparmor = cfg.get("apparmor", True)
    if apparmor is False:
        rating -= 1
    elif apparmor == "profile":
        rating += 1

    ports = cfg.get("ports") or {}
    if cfg.get("ingress"):
        rating += 2
    elif not cfg.get("host_network") and not ports:
        rating += 2
    elif cfg.get("auth_api"):
        rating += 1

    if cfg.get("signed"):
        rating += 1

    privileged = set(cfg.get("privileged") or [])
    if privileged & DANGEROUS_CAPS or cfg.get("kernel_modules"):
        rating -= 1

    role = cfg.get("hassio_role", "default")
    if role == "manager":
        rating -= 1
    elif role == "admin":
        rating -= 2

    if cfg.get("host_network"):
        rating -= 1
    if cfg.get("host_pid"):
        rating -= 2
    if cfg.get("host_uts") and "SYS_ADMIN" in privileged:
        rating -= 1

    if cfg.get("docker_api") or cfg.get("full_access"):
        rating = 1

    return max(1, min(8, rating))


def test_config_yaml_earns_the_documented_rating() -> None:
    cfg = yaml.safe_load(CONFIG.read_text())
    assert _supervisor_rating(cfg) == 1, (
        "ha_soc_probe/config.yaml no longer earns a Supervisor rating of 1. "
        "Update the privilege ledger and the rating statements in README.md "
        "and ha_soc_probe/DOCS.md to the new number in the same change."
    )


def test_docs_state_the_rating_plainly() -> None:
    readme = (REPO / "README.md").read_text()
    docs = (REPO / "ha_soc_probe" / "DOCS.md").read_text()
    assert "security rating is 1" in readme
    assert "security rating is 1" in docs
    # The stale framing this replaced: the rating is not a per-grant
    # deduction story, docker_api pins it to 1 outright.
    assert "rating by one point" not in readme
    assert "rating by one point" not in docs
