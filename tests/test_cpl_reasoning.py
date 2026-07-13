from __future__ import annotations

from main_review.cpl_reasoning import cpl_depth, plan_cpl_assignments


def _names(assignments) -> list[str]:
    return [assignment.specialist for assignment in assignments]


def test_adaptive_planner_ignores_capability_metadata_without_findings(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_DEPTH", "adaptive")
    monkeypatch.setenv("SERGEANT_CPL_MAX_PASSES", "3")
    context = {
        "capability_review": {
            "capability_status": {
                "security_taint": "available",
                "api_contract": "available",
            },
            "findings": [],
        },
        "review_intelligence": {"ranked_findings": []},
    }

    assignments = plan_cpl_assignments(["src/app.py"], context, primary_verdict="PASS")

    assert _names(assignments) == ["correctness"]


def test_adaptive_planner_prioritizes_real_security_path(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_DEPTH", "adaptive")
    monkeypatch.setenv("SERGEANT_CPL_MAX_PASSES", "3")

    assignments = plan_cpl_assignments(
        ["src/auth/session.py", "tests/test_auth.py"],
        {"diff_findings": [{"message": "Authentication boundary changed."}]},
        primary_verdict="PASS",
    )

    assert _names(assignments)[:2] == ["security", "tests_contracts"]


def test_maximum_depth_deploys_all_current_specialists(monkeypatch) -> None:
    monkeypatch.setenv("SERGEANT_CPL_DEPTH", "maximum")
    monkeypatch.setenv("SERGEANT_CPL_MAX_PASSES", "8")

    assignments = plan_cpl_assignments([], {}, primary_verdict="PASS")

    assert set(_names(assignments)) == {
        "correctness",
        "security",
        "architecture",
        "tests_contracts",
        "performance_concurrency",
    }


def test_legacy_always_council_maps_to_maximum_depth(monkeypatch) -> None:
    monkeypatch.delenv("SERGEANT_CPL_DEPTH", raising=False)
    monkeypatch.delenv("SERGEANT_LLM_DEPTH", raising=False)
    monkeypatch.setenv("SERGEANT_LLM_COUNCIL", "always")

    assert cpl_depth() == "maximum"
