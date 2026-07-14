from __future__ import annotations

from pathlib import Path

from main_review.pr_reviewer import render_pr_review_markdown, run_independent_pr_review
from main_review.review_intelligence import run_review_intelligence


def test_review_intelligence_ranks_and_groups_findings() -> None:
    packet = {"capability_review": {"findings": [
        {"capability": "security_taint", "severity": "major", "message": "Potential unsafe input path needs validation review.", "evidence": "Input source and sensitive operation are both present.", "confidence": 0.7, "path": "src/api.py", "related_paths": ["src/db.py"]},
        {"capability": "security_taint", "severity": "major", "message": "Potential unsafe input path needs validation review.", "evidence": "Input source and sensitive operation are both present.", "confidence": 0.7, "path": "src/api.py", "related_paths": ["src/db.py"]},
        {"capability": "test_impact", "severity": "major", "message": "Implementation changed without changed tests in the same PR.", "evidence": "0 changed test files.", "confidence": 0.78},
    ]}}

    result = run_review_intelligence(packet)

    assert result["verdict"] == "PASS"
    assert result["finding_count"] == 2
    assert result["promoted_count"] == 0
    assert result["duplicate_rate"] > 0
    assert "unsafe-data-flow" in result["root_causes"]
    assert result["ranked_findings"][0]["priority"] >= result["ranked_findings"][1]["priority"]
    assert result["ranked_findings"][0]["why_it_matters"]
    assert result["ranked_findings"][0]["safer_alternative"]
    assert result["trace"]


def test_generic_structurally_complete_evidence_is_not_promoted() -> None:
    result = run_review_intelligence({"capability_review": {"findings": [{
        "capability": "data_flow",
        "severity": "major",
        "message": "User-controlled input appears near a risky sink.",
        "evidence": "Input and sink patterns were both detected in the changed file.",
        "confidence": 0.92,
        "path": "src/api.py",
        "line_start": 7,
        "line_end": 7,
        "direct_evidence": True,
    }]}})

    assert result["verdict"] == "PASS"
    assert result["promoted_count"] == 0
    assert result["ranked_findings"][0]["challenge_result"] == "weakened: evidence is too generic"


def test_explicit_zero_confidence_is_not_defaulted_to_medium() -> None:
    result = run_review_intelligence({"capability_review": {"findings": [{
        "capability": "architecture",
        "severity": "major",
        "message": "Possible boundary issue.",
        "evidence": "web/dashboard.py:1 imports backend/database.py directly.",
        "confidence": 0.0,
        "path": "web/dashboard.py",
        "line_start": 1,
        "direct_evidence": True,
    }]}})

    finding = result["ranked_findings"][0]
    assert finding["confidence"] == 0.08
    assert finding["challenge_result"] == "weakened: low confidence"
    assert result["verdict"] == "PASS"


def test_completeness_does_not_count_guaranteed_template_text() -> None:
    result = run_review_intelligence({"capability_review": {"findings": [{
        "capability": "architecture",
        "severity": "minor",
        "message": "Possible boundary issue.",
        "evidence": "A dependency was observed.",
        "confidence": 0.7,
        "path": "web/dashboard.py",
    }]}})

    finding = result["ranked_findings"][0]
    assert finding["why_it_matters"]
    assert finding["verification_test"]
    assert finding["completeness_score"] < 0.8


def _write_project(root: Path) -> None:
    (root / "package.json").write_text('{"scripts":{"test":"node tests/test_api.js"}}\n', encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "api.js").write_text(
        "export function getUser(req) {\n"
        "  const sql = `SELECT * FROM users WHERE id=${req.query.id}`;\n"
        "  return query(sql);\n"
        "}\n"
        "app.get('/users/:id', getUser);\n",
        encoding="utf-8",
    )
    (root / "tests").mkdir()
    (root / "tests" / "test_api.js").write_text("assert.ok(true);\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")


def test_pr_review_includes_tier2_review_intelligence(tmp_path: Path) -> None:
    _write_project(tmp_path)

    packet = run_independent_pr_review(tmp_path, changed_files=["src/api.js"])
    rendered = render_pr_review_markdown(packet)

    assert "review_intelligence" in packet
    assert packet["review_intelligence"]["quality_score"] <= 100
    assert "Review intelligence verdict" in rendered
    assert "Tier 2 ranked findings" in rendered
