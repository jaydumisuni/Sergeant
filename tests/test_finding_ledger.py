from __future__ import annotations

from main_review.cpl_runtime import _gap_impact
from main_review.finding_ledger import build_finding_ledger
from main_review.pr_reviewer import _decide
from main_review.review_benchmark import extract_predictions


def _deterministic(
    category: str,
    *,
    severity: str = "major",
    root_cause: str,
    message: str,
    path: str = "src/app.py",
    line: int = 5,
    promoted: bool = True,
) -> dict:
    return {
        "capability": category,
        "severity": severity,
        "root_cause": root_cause,
        "message": message,
        "evidence": "return subprocess.run(command, shell=True)",
        "path": path,
        "line_start": line,
        "line_end": line,
        "promoted": promoted,
        "challenge_result": "survived: evidence is specific enough for review output",
    }


def _cpl(
    category: str,
    *,
    severity: str = "major",
    message: str,
    path: str = "src/app.py",
    line: int = 5,
    models: list[str] | None = None,
    verified: bool = True,
) -> dict:
    return {
        "category": category,
        "severity": severity,
        "message": message,
        "evidence": "return subprocess.run(command, shell=True)",
        "evidence_verified": verified,
        "why_it_matters": "The supplied input can execute an unintended operation.",
        "safer_alternative": "Use a safe API and validate the input.",
        "path": path,
        "line_start": line,
        "line_end": line,
        "supporting_models": models or ["model-a", "model-b"],
    }


def _ledger(*, deterministic: list[dict] | None = None, cpl: list[dict] | None = None) -> dict:
    return build_finding_ledger(
        {},
        {},
        {"ranked_findings": deterministic or []},
        {"findings": cpl or []},
    )


def test_cpl_confirmation_attaches_without_collapsing_distinct_deterministic_facets() -> None:
    ledger = _ledger(
        deterministic=[
            _deterministic(
                "data_flow",
                root_cause="unsafe-data-flow",
                message="User-controlled input appears near a risky sink.",
            ),
            _deterministic(
                "security_taint",
                root_cause="unsafe-data-flow",
                message="Potential tainted input path needs validation review.",
            ),
        ],
        cpl=[
            _cpl(
                "security",
                message="Potential command injection through shell=True.",
            )
        ],
    )

    assert len(ledger["actionable_findings"]) == 2
    assert {item["category"] for item in ledger["actionable_findings"]} == {"data_flow", "security_taint"}
    assert len(ledger["duplicate_confirmations"]) == 1
    assert ledger["duplicate_confirmations"][0]["disposition"] == "duplicate_confirmation"
    assert any("cpl_review" in item.get("supporting_sources", []) for item in ledger["actionable_findings"])


def test_generic_cpl_test_request_stays_advisory_without_deterministic_proof_gap() -> None:
    ledger = _ledger(
        cpl=[
            _cpl(
                "tests",
                message="Add more tests for the changed behavior.",
                path="tests/test_app.py",
                line=3,
            )
        ]
    )

    assert ledger["verdict"] == "PASS"
    assert ledger["actionable_findings"] == []
    assert ledger["advisory_findings"][0]["disposition"] == "advisory_without_deterministic_proof_gap"


def test_independently_supported_novel_cpl_major_is_admitted() -> None:
    ledger = _ledger(
        cpl=[
            _cpl(
                "correctness",
                message="The returned state contradicts the supplied implementation contract.",
                path="src/state.py",
                line=8,
            )
        ]
    )

    assert ledger["verdict"] == "NEEDS WORK"
    assert len(ledger["actionable_findings"]) == 1
    assert ledger["actionable_findings"][0]["admission"] == "independently_grounded_novel_finding"


def test_single_model_novel_cpl_major_remains_auditable_but_non_gating() -> None:
    ledger = _ledger(
        cpl=[
            _cpl(
                "correctness",
                message="The returned state may contradict the implementation contract.",
                models=["model-a"],
            )
        ]
    )

    assert ledger["verdict"] == "PASS"
    assert ledger["gating_findings"] == []
    assert ledger["suppressed_findings"][0]["disposition"] == "advisory_unconfirmed"


def test_deterministic_minor_remains_visible_without_changing_merge_verdict() -> None:
    ledger = _ledger(
        deterministic=[
            _deterministic(
                "performance",
                severity="minor",
                root_cause="runtime-risk",
                message="Nested iteration may create scaling risk.",
                promoted=False,
            )
        ]
    )

    assert len(ledger["actionable_findings"]) == 1
    assert ledger["actionable_findings"][0]["severity"] == "minor"
    assert ledger["gating_findings"] == []
    assert ledger["verdict"] == "PASS"


def test_benchmark_scores_the_adjudicated_ledger_surface() -> None:
    ledger = _ledger(
        deterministic=[
            _deterministic(
                "architecture",
                root_cause="architecture-boundary",
                message="UI layer imports backend implementation directly.",
                path="web/dashboard.py",
                line=1,
            )
        ],
        cpl=[
            _cpl(
                "architecture",
                message="UI imports the backend layer directly.",
                path="web/dashboard.py",
                line=1,
            )
        ],
    )

    predictions, raw_count = extract_predictions({"finding_ledger": ledger})

    assert len(predictions) == 1
    assert predictions[0]["source"] == "finding_ledger"
    assert raw_count == ledger["raw_candidate_count"]


def test_gap_impact_separates_assurance_from_confidence_only_uncertainty() -> None:
    assert _gap_impact({"type": "missing_report"}) == "assurance"
    assert _gap_impact({"type": "independent_confirmation"}) == "assurance"
    assert _gap_impact({"type": "disagreement"}) == "confidence"
    assert _gap_impact({"type": "unanswered_question"}) == "confidence"


def test_final_decision_uses_ledger_instead_of_raw_cpl_uncertainty() -> None:
    verdict = _decide(
        {"verdict": {"verdict": "PASS"}},
        {"passed": True, "blockers": []},
        {"verdict": {"verdict": "PASS"}},
        {"verdict": "PASS", "promoted_findings": []},
        {"trusted": True, "confidence_after_challenge": 0.9},
        {"status": "completed", "policy": "required", "verdict": "NEEDS WORK", "confidence": 0.8},
        {"consensus": "PASS"},
        {"verdict": "PASS", "gating_findings": [], "required_actions": []},
    )

    assert verdict.verdict == "APPROVE"
