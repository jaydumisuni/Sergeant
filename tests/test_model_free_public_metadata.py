from __future__ import annotations

from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_pypi_metadata_describes_model_free_core_and_optional_reasoning() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert "model-free" in project["description"].lower()
    assert "optional" in project["description"].lower()
    assert "model-free-review" in project["keywords"]
    assert "optional-model-reasoning" in project["keywords"]


def test_jetbrains_marketplace_metadata_matches_product_boundary() -> None:
    plugin = (
        ROOT
        / "adapters"
        / "jetbrains"
        / "src"
        / "main"
        / "resources"
        / "META-INF"
        / "plugin.xml"
    ).read_text(encoding="utf-8")

    assert "model-free evidence-based engineering reviewer" in plugin
    assert "explicit owner-enabled extra reasoning" in plugin
    assert "multi-model council" in plugin
    assert "Sergeant remains final authority" in plugin
    assert "model-free review against the current project" in plugin


def test_command_center_recurring_timer_has_owned_teardown() -> None:
    script = (ROOT / "resources" / "sergeant-command-center-v2.js").read_text(encoding="utf-8")
    visual = (ROOT / "tests" / "command-center-visual.spec.js").read_text(encoding="utf-8")

    assert "const clockTimer = setInterval(updateClock, 1000)" in script
    assert "clearInterval(clockTimer)" in script
    assert "window.addEventListener('pagehide', stopClock" in script
    assert "window.addEventListener('beforeunload', stopClock" in script
    assert "window.sergeantClock = { stop: stopClock" in script
    assert "owns and tears down its recurring clock timer" in visual
    assert "window.sergeantClock.stop()" in visual
