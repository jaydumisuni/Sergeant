from __future__ import annotations

from pathlib import Path

import main_review.llm_review as llm_review_module
from main_review.cpl_runtime import run_cpl_review
from main_review.finding_adjudication import (
    adjudicate_cpl_findings,
    classify_council_gaps,
    cross_source_match,
)
from main_review.llm_provider import LLMRoute, LLMSettings


def deterministic_context(*findings: dict) -> dict:
    return {
        "capability_review": {
            "findings": list(findings),
        }
    }


def deterministic_security() -> dict:
    return {
        "capability": "security_taint",
        "severity": "major",
        "path": "src/jobs.py",
        "line_start": 5,
        "line_end": 5,
        "message": "Potential tainted input path needs validation review.",
        "evidence": "Input source and security-sensitive operation are both present.",
        "root_cause": "unsafe-data-flow",
    }


def cpl_security(*, supporting_models: list[str] | None = None) -> dict:
    return {
        "category": "security",
        "severity": "blocker",
        "path": "src/jobs.py",
        "line_start": 4,
        "line_end": 5,
        "message": "Unvalidated request input is executed with shell=True.",
        "evidence": "return subprocess.run(command, shell=True)",
        "evidence_verified": True,
        "why_it_matters": "An attacker can execute arbitrary commands.",
        "safer_alternative": "Use explicit arguments and validate input.",
        "supporting_models": supporting_models or ["model-a", "model-b"],
    }


def test_cross_source_security_confirmation_does_not_duplicate_deterministic_finding() -> None:
    deterministic = deterministic_security()
    cpl = cpl_security()

    assert cross_source_match(cpl, {**deterministic, "category": deterministic["capability"]}) is True

    result = adjudicate_cpl_findings(
        [cpl],
        deterministic_context(deterministic),
        minimum_supporting_models=2,
    )

    assert result["verdict"] == "PASS"
    assert result["actionable_findings"] == []
    assert len(result["confirmations"]) == 1
    assert result["confirmations"][0]["matched_finding"]["source"] == "capability"
    assert result["confirmations"][0]["matched_finding"]["severity"] == "major"


def test_cpl_cannot_raise_deterministic_minor_runtime_risk_to_major() -> None:
    deterministic = {
        "capability": "concurrency",
        "severity": "minor",
        "path": "src/jobs.py",
        "line_start": 6,
        "line_end": 6,
        "message": "Async or shared-state pattern may need race-condition review.",
        "evidence": "Concurrent execution signal and shared state naming were both detected.",
        "root_cause": "runtime-risk",
    }
    cpl = {
        "category": "correctness",
        "severity": "major",
        "path": "src/jobs.py",
        "line_start": 6,
        "line_end": 8,
        "message": "Global counter mutation can race across concurrent calls.",
        "evidence": "global global_counter\nawait job()\nglobal_counter += 1",
        "evidence_verified": True,
        "why_it_matters": "Concurrent calls can lose increments.",
        "safer_alternative": "Use a lock or remove shared mutable state.",
        "supporting_models": ["model-a", "model-b"],
    }

    result = adjudicate_cpl_findings(
        [cpl],
        deterministic_context(deterministic),
        minimum_supporting_models=2,
    )

    assert result["actionable_findings"] == []
    assert len(result["confirmations"]) == 1
    assert result["confirmations"][0]["matched_finding"]["severity"] == "minor"


def test_generic_test_request_stays_advisory_even_when_major() -> None:
    finding = {
        "category": "tests",
        "severity": "major",
        "path": "tests/test_jobs.py",
        "line_start": 1,
        "line_end": 4,
        "message": "Add more security tests.",
        "evidence": "def test_symbol_exists():\n    assert run_job",
        "evidence_verified": True,
        "why_it_matters": "The current test is narrow.",
        "safer_alternative": "Add focused behavior proof.",
        "supporting_models": ["model-a", "model-b"],
    }

    result = adjudicate_cpl_findings(
        [finding],
        {},
        minimum_supporting_models=2,
    )

    assert result["verdict"] == "PASS"
    assert result["actionable_findings"] == []
    assert result["advisory_findings"][0]["disposition"] == "advisory"


def test_novel_grounded_major_requires_independent_support_in_multi_model_council() -> None:
    one_model = cpl_security(supporting_models=["model-a"])
    one_model["path"] = "src/new.py"
    two_models = {**one_model, "supporting_models": ["model-a", "model-b"]}

    rejected = adjudicate_cpl_findings(
        [one_model],
        {},
        minimum_supporting_models=2,
    )
    admitted = adjudicate_cpl_findings(
        [two_models],
        {},
        minimum_supporting_models=2,
    )

    assert rejected["verdict"] == "PASS"
    assert rejected["actionable_findings"] == []
    assert "requires 2 supporting model" in rejected["rejected_findings"][0]["rejection_reason"]
    assert admitted["verdict"] == "BLOCK"
    assert admitted["actionable_findings"][0]["disposition"] == "admitted_novel"


def test_council_gap_classification_does_not_make_disagreement_or_provider_failure_a_gate() -> None:
    gaps = [
        {"type": "failed_member", "reason": "optional model route failed"},
        {"type": "disagreement", "reason": "wording differs"},
        {"type": "unanswered_question", "reason": "low-risk context missing"},
        {"type": "independent_confirmation", "reason": "major finding has one source"},
    ]

    result = classify_council_gaps(gaps)

    assert [item["type"] for item in result["confidence_gaps"]] == [
        "failed_member",
        "disagreement",
        "unanswered_question",
    ]
    assert [item["type"] for item in result["verdict_gaps"]] == ["independent_confirmation"]


def _settings() -> LLMSettings:
    return LLMSettings(
        enabled=True,
        policy="preferred",
        provider="configured",
        base_url="http://127.0.0.1:9999/v1",
        model="model-a",
        protocol="chat_completions",
        api_key="",
        timeout_seconds=1.0,
        max_output_tokens=1000,
    )


def _route() -> LLMRoute:
    return LLMRoute(
        provider="test",
        base_url="http://127.0.0.1:9999/v1",
        model="model-a",
        protocol="chat_completions",
        discovered_models=("model-a",),
    )


def test_confidence_only_gap_preserves_cpl_pass(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    monkeypatch.setenv("SERGEANT_CPL_DEPTH", "single")
    monkeypatch.setenv("SERGEANT_CPL_MAX_PASSES", "1")
    monkeypatch.setenv("SERGEANT_CPL_MAX_ROUNDS", "1")
    monkeypatch.setattr(
        llm_review_module,
        "invoke_json",
        lambda *args, **kwargs: {
            "verdict": "PASS",
            "confidence": 0.8,
            "summary": "No actionable defect found.",
            "findings": [],
            "unanswered_questions": ["A low-risk naming preference was not documented."],
            "coverage": {"files_reviewed": ["src/app.py"], "areas": ["correctness"]},
        },
    )

    result = run_cpl_review(
        tmp_path,
        ["src/app.py"],
        {"capability_review": {"findings": []}},
        settings=_settings(),
        route=_route(),
    )

    assert result["verdict"] == "PASS"
    assert result["council"]["complete"] is False
    assert result["council"]["verdict_complete"] is True
    assert result["council"]["verdict_gaps"] == []
    assert result["council"]["confidence_gaps"][0]["type"] == "unanswered_question"
