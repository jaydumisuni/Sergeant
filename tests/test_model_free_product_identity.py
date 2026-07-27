from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_canonical_model_boundary_is_explicit() -> None:
    canonical = text("docs/55-model-free-core-and-optional-model-reasoning.md")
    for phrase in (
        "Sergeant is a model-free engineering review system",
        "does not require",
        "optional owner-enabled model support",
        "A multi-model council is only one optional configuration",
        "Sergeant still issues the verdict",
    ):
        assert phrase in canonical


def test_primary_public_docs_do_not_present_multi_model_as_the_product() -> None:
    readme = text("README.md")
    assert "Sergeant's reviewer core is model-free" in readme
    assert "optional one-model or bounded multi-model reasoning support" in readme
    assert "Adaptive multi-specialist and multi-model review." not in readme
    assert "Cpl multi-model council and verified experience" not in text("docs/hackathon-submission.md")


def test_agent_memory_preserves_model_free_identity() -> None:
    agents = text("AGENTS.md")
    assert "## Model-free product boundary" in agents
    assert "Cpl, permanent officers and privates are native Sergeant roles" in agents
    assert "optional owner-enabled extra reasoning" in agents
    assert "must not present Sergeant itself as a multi-model reviewer" in agents
    assert "model-free engineering reviewer" in text("CLAUDE.md")
    assert "model-free engineering reviewer" in text(".github/copilot-instructions.md")


def test_optional_model_docs_keep_authority_below_sergeant() -> None:
    for path in (
        "docs/22-semantic-open-model-review.md",
        "docs/34-cpl-officer-amplification.md",
        "docs/35-cpl-council-command-and-experience.md",
    ):
        value = text(path)
        assert "model-free" in value.lower()
        assert "optional" in value.lower()
        assert "Sergeant" in value
    assert "Models never replace Cpl or the permanent officers" in text(
        "docs/22-semantic-open-model-review.md"
    )


def test_command_center_visibly_separates_core_from_optional_models() -> None:
    html = text("resources/sergeant-command-center-v2.html")
    script = text("resources/sergeant-command-center-v2.js")
    assert "ENGINEERING REVIEW SYSTEM" in html
    assert "Model-Free Core / Optional Model Support" in html
    assert "Model-free only — no model calls" in html
    assert "Cpl / Officer Reasoning" in html
    assert "Optional Model Route" in html
    assert "Model-free Sergeant core" in script
    assert "Optional Model Rounds" in script
    assert "Optional Model Assistance" in script
    assert "Cross-check Independence" in script


def test_runtime_configuration_contract_remains_honest() -> None:
    provider = text("main_review/llm_provider.py")
    assert 'LLMPolicy = Literal["preferred", "required", "disabled"]' in provider
    assert '"SERGEANT_LLM_POLICY", "disabled"' in provider
    assert "Automatic discovery probes loopback endpoints only" in provider
    package = __import__("json").loads(text("package.json"))
    properties = package["contributes"]["configuration"]["properties"]
    assert properties["sergeant.llmPolicy"]["default"] == "disabled"
    assert properties["sergeant.provider"]["default"] == "Model-Free Sergeant Core"
    canonical = text("docs/55-model-free-core-and-optional-model-reasoning.md")
    assert "SERGEANT_CPL_POLICY=disabled" in canonical
    assert "SERGEANT_CPL_POLICY=preferred" in canonical
    assert "SERGEANT_CPL_POLICY=required" in canonical
