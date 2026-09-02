"""Regression tests for the HA SOC Probe AppArmor policy."""

from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
APPARMOR_PROFILE = REPO / "ha_soc_probe" / "apparmor.txt"


def test_s6_init_script_is_readable_and_inherits_profile() -> None:
    """The shell must read /init before s6-overlay can start."""
    profile = APPARMOR_PROFILE.read_text(encoding="utf-8")

    assert "/init rix," in profile
    assert "/init ix," not in profile
