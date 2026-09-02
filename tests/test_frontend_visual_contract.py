"""Structural gates for the approved HA SOC console composition.

These checks complement (rather than replace) browser screenshot review.  They
keep the reference hierarchy, truthful live-data labels, and container-driven
responsive contract from silently drifting while the frontend has no DOM test
runner of its own.
"""

from pathlib import Path


ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components" / "ha_soc" / "frontend"
PANEL = FRONTEND / "src" / "ha-soc-panel.ts"
DASHBOARD = FRONTEND / "src" / "views" / "dashboard-view.ts"
STYLES = FRONTEND / "src" / "styles.ts"
BUNDLE = FRONTEND / "dist" / "ha-soc-panel.js"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_console_shell_matches_protected_workspace_contract() -> None:
    panel = _text(PANEL)
    assert "HA SOC Security Console" in panel
    assert "Protected detail workspace" in panel
    assert "Owner access" in panel
    assert '@property({ type: Boolean, reflect: true }) narrow' in panel
    assert ":host([narrow]) .brand-context" in panel
    assert ":host([narrow]) .brand-context {\n      display: none" not in panel


def test_overview_reference_order_and_truthful_state() -> None:
    dashboard = _text(DASHBOARD)
    start = dashboard.index("private _renderReferenceOverview()")
    end = dashboard.index("private _statusDotColor(", start)
    overview = dashboard[start:end]

    labels = (
        "Security overview",
        "Posture score",
        "Open detections",
        "Critical / high findings",
        "Telemetry sources",
        "<h3>Asset availability</h3>",
        "<h3>Posture</h3>",
        "<h3>Finding severity</h3>",
        "<h3>Posture trend</h3>",
        "<h3>Priority queue</h3>",
    )
    positions = [overview.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "Live protected data" in overview
    assert "Planning preview" not in overview
    assert "sample data" not in overview


def test_dashboard_breakpoints_follow_component_width() -> None:
    dashboard = _text(DASHBOARD)
    styles = _text(STYLES)
    assert "container-type: inline-size" in styles
    assert "@container (max-width: 1100px)" in dashboard
    assert "@container (max-width: 900px)" in dashboard
    assert "@container (max-width: 560px)" in dashboard
    assert "@media (max-width:" not in dashboard


def test_committed_bundle_contains_visual_contract() -> None:
    bundle = _text(BUNDLE)
    for marker in (
        "HA SOC Security Console",
        "Protected detail workspace",
        "Telemetry sources",
        "Asset availability",
        "Priority queue",
        "@container (max-width: 560px)",
    ):
        assert marker in bundle
