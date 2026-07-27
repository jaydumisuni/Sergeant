from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


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
        assert "dependency" in text.lower() or "does not require" in text.lower()
        assert "final" in text.lower()

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
        assert "55-model-free-core-and-optional-model-reasoning.md" in text, path


def test_submission_documents_use_honest_model_wording() -> None:
    for path in ("docs/hackathon-submission.md", "SUBMISSION_READY.md"):
        text = _text(path)
        assert "model-free" in text.lower()
        assert "optional" in text.lower()
        assert "multi-model" in text.lower()
        assert "does not require" in text.lower() or "without requiring" in text.lower()


def test_python_entrypoints_default_to_model_free_review() -> None:
    clean_environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SERGEANT_CPL_") and not key.startswith("SERGEANT_LLM_")
    }
    code = (
        "import json; "
        "import main_review; "
        "from main_review.llm_provider import LLMSettings, discover_route; "
        "settings=LLMSettings.from_environment(); "
        "print(json.dumps({'enabled': settings.enabled, 'policy': settings.policy, "
        "'provider': settings.provider, 'route': discover_route(settings)}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=clean_environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    # The explicit enable switch is the authority. Preferred/auto remain dormant
    # compatibility metadata and cannot discover or call a route while disabled.
    assert payload == {
        "enabled": False,
        "policy": "preferred",
        "provider": "auto",
        "route": None,
    }


def test_explicit_enable_switch_preserves_optional_model_configuration() -> None:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("SERGEANT_CPL_") and not key.startswith("SERGEANT_LLM_")
    }
    environment.update(
        {
            "SERGEANT_CPL_ENABLED": "true",
            "SERGEANT_CPL_POLICY": "preferred",
            "SERGEANT_CPL_PROVIDER": "ollama",
            "SERGEANT_CPL_MODEL": "owner-selected-model",
        }
    )
    code = (
        "import json; "
        "from main_review.llm_provider import LLMSettings; "
        "settings=LLMSettings.from_environment(); "
        "print(json.dumps({'enabled': settings.enabled, 'policy': settings.policy, "
        "'provider': settings.provider, 'model': settings.model}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload == {
        "enabled": True,
        "policy": "preferred",
        "provider": "ollama",
        "model": "owner-selected-model",
    }


def test_vscode_defaults_to_model_free_review() -> None:
    package = json.loads(_text("package.json"))
    properties = package["contributes"]["configuration"]["properties"]
    extension = _text("src/vscode/extension.js")
    command_center = _text("resources/sergeant-command-center-v2.html")
    command_center_js = _text("resources/sergeant-command-center-v2.js")

    assert properties["sergeant.provider"]["default"] == "Disabled"
    assert properties["sergeant.llmPolicy"]["default"] == "disabled"
    assert properties["sergeant.llmProvider"]["default"] == "disabled"
    assert 'policy: configuration.get("llmPolicy") || "disabled"' in extension
    assert 'provider: configuration.get("llmProvider") || "disabled"' in extension
    assert "model-free permanent officers" in extension
    assert '<option value="disabled" selected>Disabled — normal model-free review</option>' in command_center
    assert '<option value="disabled" selected>Disabled — no model endpoint</option>' in command_center
    assert "policy: 'disabled'" in command_center_js
    assert "provider: 'disabled'" in command_center_js


def test_canonical_model_free_proof_remains_linked() -> None:
    readme = _text("README.md")
    deterministic = _text("docs/44-deterministic-permanent-officer-formation.md")
    multilanguage = _text("docs/45-model-free-multilanguage-assurance.md")

    assert "docs/44-deterministic-permanent-officer-formation.md" in readme
    assert "docs/45-model-free-multilanguage-assurance.md" in readme
    assert "docs/55-model-free-core-and-optional-model-reasoning.md" in readme
    assert "Models are optional support engines" in deterministic
    assert "zero model calls" in multilanguage
