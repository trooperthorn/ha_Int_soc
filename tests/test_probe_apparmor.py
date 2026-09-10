"""Regression tests for the HA SOC Probe AppArmor policy."""

import re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
APPARMOR_PROFILE = REPO / "ha_soc_probe" / "apparmor.txt"

# Every one of these holds shell or execline that an interpreter must open to
# run. The s6-overlay boot chain is /init -> preinit -> stage0..2, all under
# /package; /command carries execline scripts such as with-contenv; bashio is
# sourced by the service run scripts.
SCRIPT_BEARING_PATHS = (
    "/init",
    "/bin/**",
    "/usr/bin/**",
    "/package/**",
    "/command/**",
    "/usr/lib/bashio/**",
)


def _profile() -> str:
    return APPARMOR_PROFILE.read_text(encoding="utf-8")


def test_script_paths_grant_read_as_well_as_execute() -> None:
    """A script path with `ix` but no `r` stops the container in preinit.

    This profile deliberately omits the documented example's blanket `file,`
    rule, so read is not granted implicitly anywhere. An `ix` rule alone lets
    the kernel exec an ELF binary but leaves the shell unable to open a
    script, which fails as "can't open ...: Permission denied" and exit code
    2 before any service starts. That reached production twice: for /init,
    fixed in #35, and for /package, which #35 did not carry the reasoning to.
    """
    profile = _profile()
    for path in SCRIPT_BEARING_PATHS:
        pattern = rf"^\s*{re.escape(path)}\s+(?P<mode>[a-zA-Z]+),"
        match = re.search(pattern, profile, re.MULTILINE)
        assert match is not None, f"{path} has no rule in the profile"
        mode = match.group("mode")
        assert "x" in mode, f"{path} must be executable, got {mode!r}"
        assert "r" in mode, (
            f"{path} carries {mode!r}: execute without read. The interpreter "
            "cannot open a script it is allowed to execute."
        )


def test_the_blanket_file_rule_stays_out() -> None:
    """The enumerated paths are the point; `file,` would undo all of them."""
    assert not re.search(r"^\s*file,\s*$", _profile(), re.MULTILINE)
