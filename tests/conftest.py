import pathlib
import shutil

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def hass_config_dir(request) -> str:
    """Give tests that write into the config directory a private one.

    The default is one directory inside site-packages shared by all pytest-xdist workers,
    so concurrent tests that write automations.yaml or set up the automation component
    (which copies example blueprints there) race and fail at random. A module opts in with
    ISOLATED_CONFIG_DIR = True. Other modules keep the shared directory because the
    scanner tests rely on the custom integrations it ships.
    """
    if getattr(request.module, "ISOLATED_CONFIG_DIR", False) or request.node.get_closest_marker(
        "isolated_config_dir"
    ):
        # Requested lazily: it populates tmp_path, which other tests count files in.
        return request.getfixturevalue("hass_tmp_config_dir")
    from pytest_homeassistant_custom_component.common import get_test_config_dir

    return get_test_config_dir()


@pytest.fixture
def hass_tmp_config_dir(tmp_path: pathlib.Path) -> str:
    """Copy the shared test config directory, leaving out what other tests write into it.

    Non-isolated modules run the integration against the shared directory, so HA SOC's own
    runtime files (``ha_soc`` with the crash forensics heartbeat and its temp file, and
    ``.storage``) appear and disappear there while another worker copies it. The copy only
    needs the static files the harness ships, so the runtime entries are skipped.
    """
    from pytest_homeassistant_custom_component.common import get_test_config_dir

    source = get_test_config_dir()

    def _skip_runtime(directory: str, names: list[str]) -> list[str]:
        if pathlib.Path(directory) != pathlib.Path(source):
            return []
        return [name for name in names if name in (".storage", "ha_soc") or name.endswith(".tmp")]

    shutil.copytree(
        source, tmp_path, symlinks=True, dirs_exist_ok=True, ignore=_skip_runtime
    )
    return str(tmp_path)
