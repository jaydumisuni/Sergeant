from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_product_truth_is_model_free_with_optional_model_support() -> None:
    readme = text("README.md")
    agents = text("AGENTS.md")
    semantic = text("docs/22-semantic-open-model-review.md")
    canonical = text("docs/54-model-free-core-and-optional-reasoning.md")

    for document in [readme, agents, semantic, canonical]:
        assert "model-free" in document.lower()
        assert "optional" in document.lower()

    assert "Preferred is the product default" not in readme
    assert "Adaptive multi-specialist and multi-model review" not in readme
    assert "Default mode." not in semantic
    assert "- Deploy Cpl when a route is available." not in semantic


def test_runtime_and_ide_defaults_do_not_enable_models() -> None:
    provider = text("main_review/llm_provider.py")
    extension = text("src/vscode/extension.js")
    runner = text("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantRunner.kt")
    tool_window = text("adapters/jetbrains/src/main/kotlin/com/thetechguyds/sergeant/SergeantToolWindowFactory.kt")
    command_center = text("resources/sergeant-command-center-v2.js")
    package = json.loads(text("package.json"))
    props = package["contributes"]["configuration"]["properties"]

    assert 'policy_value = os.getenv("SERGEANT_CPL_POLICY")' in provider
    assert '"preferred" if explicit_enable or explicit_route else "disabled"' in provider
    assert 'enabled = policy != "disabled"' in provider
    assert 'policy: configuration.get("llmPolicy") || "disabled"' in extension
    assert 'provider: configuration.get("llmProvider") || "disabled"' in extension
    assert '?: "disabled"' in runner
    assert '"policy" to "disabled"' in tool_window
    assert '"provider" to "disabled"' in tool_window
    assert "policy: 'disabled'" in command_center
    assert "provider: 'disabled'" in command_center
    assert props["sergeant.provider"]["default"] == "Disabled"
    assert props["sergeant.llmPolicy"]["default"] == "disabled"
    assert props["sergeant.llmProvider"]["default"] == "disabled"


def test_command_center_presents_models_as_optional() -> None:
    html = text("resources/sergeant-command-center-v2.html")
    js = text("resources/sergeant-command-center-v2.js")

    assert "ENGINEERING REVIEWER" in html
    assert "Disabled — model-free Sergeant (default)" in html
    assert "Optional Model Reasoning" in html
    assert "AI CODE REVIEWER" not in html
    assert "Optional Cpl Model Reasoning" in js
