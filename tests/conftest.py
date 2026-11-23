import pathlib
import shutil

import pytest


@pytest.fixture
def hass_config_dir(request) -> str:
    """Give tests that write into the config directory a private one.

    The default is one directory per pytest session (per pytest-xdist worker), shared by
    every test that does not opt out, so files one test writes there are still present
    for the next. A module opts in to a private directory with ISOLATED_CONFIG_DIR = True,
    a single test with the isolated_config_dir marker.
    """
    if getattr(request.module, "ISOLATED_CONFIG_DIR", False) or request.node.get_closest_marker(
        "isolated_config_dir"
    ):
        # Requested lazily: it populates tmp_path, which other tests count files in.
        return request.getfixturevalue("hass_tmp_config_dir")
    return request.getfixturevalue("shared_config_dir")


@pytest.fixture(scope="session")
def shared_config_dir(tmp_path_factory: pytest.TempPathFactory) -> str:
    """One config directory for the whole session, outside the repository.

    pytest-homeassistant defaults to tests/testing_config and creates nothing there. This
    suite writes into the config directory (audit files, the crash forensics heartbeat),
    so the default is a temporary directory instead of a path inside the working tree.
    """
    return str(tmp_path_factory.mktemp("shared_config"))


@pytest.fixture
def hass_tmp_config_dir(tmp_path: pathlib.Path, shared_config_dir: str) -> str:
    """Copy the shared test config directory, leaving out what other tests write into it.

    Non-isolated modules run the integration against the shared directory, so HA SOC's own
    runtime files (``ha_soc`` with the crash forensics heartbeat and its temp file, and
    ``.storage``) appear and disappear there while another worker copies it. The copy only
    needs whatever else is there, so the runtime entries are skipped.
    """
    source = shared_config_dir

    def _skip_runtime(directory: str, names: list[str]) -> list[str]:
        if pathlib.Path(directory) != pathlib.Path(source):
            return []
        return [name for name in names if name in (".storage", "ha_soc") or name.endswith(".tmp")]

    shutil.copytree(
        source, tmp_path, symlinks=True, dirs_exist_ok=True, ignore=_skip_runtime
    )
    return str(tmp_path)
