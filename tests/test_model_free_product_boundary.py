from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_public_product_identity_is_model_free() -> None:
    readme = _text("README.md")
    canonical = _text("docs/55-model-free-core-and-optional-model-reasoning.md")

    for text in (readme, canonical):
        assert "normal review system is **model-free**" in text or "normal review system is model-free" in text
        assert "optional" in text.lower()
        assert "multi-model" in text
        assert "not a product dependency" in text or "not a dependency" in text
        assert "Sergeant remains" in text and "final" in text

    assert "Adaptive multi-specialist and multi-model review" not in readme
    assert "Models power Cpl council members and officer-support bots" not in readme
    assert "multi-model council and verified experience" not in readme.lower()


def test_optional_model_documents_cannot_present_themselves_as_the_core() -> None:
    paths = (
        "docs/22-semantic-open-model-review.md",
        "docs/25-cloudflare-workers-ai.md",
        "docs/34-cpl-officer-amplification.md",
        "docs/35-cpl-council-command-and-experience.md",
        "docs/38-cpl-noise-governor-and-route-failover.md",
        "docs/39-review-intelligence-proof.md",
        "docs/CLOUDFLARE_COUNCIL.md",
    )
    for path in paths:
        text = _text(path)
        assert "optional" in text.lower(), path
        assert "model-free" in text.lower(), path
        assert "final authority" in text.lower() or "final review authority" in text.lower(), path


def test_submission_documents_use_honest_model_wording() -> None:
    for path in ("docs/hackathon-submission.md", "SUBMISSION_READY.md"):
        text = _text(path)
        assert "model-free" in text.lower()
        assert "optional" in text.lower()
        assert "multi-model" in text.lower()
        assert "does not require" in text.lower() or "without requiring" in text.lower()


def test_vscode_defaults_to_model_free_review() -> None:
    package = json.loads(_text("package.json"))
    properties = package["contributes"]["configuration"]["properties"]
    extension = _text("src/vscode/extension.js")

    assert properties["sergeant.provider"]["default"] == "Disabled"
    assert properties["sergeant.llmPolicy"]["default"] == "disabled"
    assert properties["sergeant.llmProvider"]["default"] == "disabled"
    assert 'policy: configuration.get("llmPolicy") || "disabled"' in extension
    assert 'provider: configuration.get("llmProvider") || "disabled"' in extension
    assert "model-free permanent officers" in extension


def test_canonical_model_free_proof_remains_linked() -> None:
    readme = _text("README.md")
    deterministic = _text("docs/44-deterministic-permanent-officer-formation.md")
    multilanguage = _text("docs/45-model-free-multilanguage-assurance.md")

    assert "docs/44-deterministic-permanent-officer-formation.md" in readme
    assert "docs/45-model-free-multilanguage-assurance.md" in readme
    assert "docs/55-model-free-core-and-optional-model-reasoning.md" in readme
    assert "Models are optional support engines" in deterministic
    assert "zero model calls" in multilanguage
