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


def test_persistent_worker_and_distribution_surfaces_match_product_truth() -> None:
    claude = text("CLAUDE.md")
    copilot = text(".github/copilot-instructions.md")
    pyproject = text("pyproject.toml")
    plugin = text("adapters/jetbrains/src/main/resources/META-INF/plugin.xml")

    for document in [claude, copilot, pyproject, plugin]:
        assert "model-free" in document.lower()
        assert "optional" in document.lower()

    assert 'description = "Sergeant model-free engineering reviewer with optional owner-enabled model reasoning."' in pyproject
    assert '"model-free-review"' in pyproject
    assert '"optional-model-reasoning"' in pyproject
    assert "Run Sergeant's model-free review against the current project" in plugin


def test_submission_and_optional_provider_docs_do_not_recast_models_as_core() -> None:
    submission = text("SUBMISSION_READY.md")
    hackathon = text("docs/hackathon-submission.md")
    noise = text("docs/38-cpl-noise-governor-and-route-failover.md")
    benchmark = text("docs/39-review-intelligence-proof.md")
    cloudflare = text("docs/CLOUDFLARE_COUNCIL.md")

    for document in [submission, hackathon, noise, benchmark, cloudflare]:
        assert "model-free" in document.lower()
        assert "optional" in document.lower()

    assert "Cpl council reasoning" not in submission
    assert "Cpl multi-model council and verified experience" not in hackathon
    assert "Sergeant's normal model-free permanent-officer formation does not depend on this layer" in noise
    assert "`deterministic` — canonical Sergeant benchmark" in benchmark
    assert "Cloudflare credentials present               → still model-free until enabled" in cloudflare


def test_retired_draft_harvest_preserves_only_verified_product_truth() -> None:
    harvest = text("docs/55-model-free-tail-harvest.md")
    lesson = json.loads(
        text(".github/self-learning/lessons/product-identity-runtime-consistency-20260727.json")
    )

    assert "PR #151" in harvest
    assert "PR #154" in harvest
    assert "Import-time environment mutation" in harvest
    assert "Duplicate visual workflow" in harvest
    assert lesson["status"] == "accepted"
    assert lesson["source"]["fixing_pr"] == 152
    assert lesson["authority"]["may_auto_promote"] is False
    assert lesson["authority"]["may_auto_merge"] is False
    assert lesson["authority"]["final_verdict"] == "Sergeant"
