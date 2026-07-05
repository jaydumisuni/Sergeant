from __future__ import annotations

from pathlib import Path

from main_review.app_bridge import handle_app_review_request
from main_review.learning_loop import build_learning_candidates, run_learning_loop


def test_learning_loop_builds_verified_candidates() -> None:
    review_result = {
        "classified_findings": [
            {
                "message": "Client route has no matching server route.",
                "evidence": "fetch('/missing') was found.",
                "classification": "correct",
                "category": "api_contract",
                "verdict": "NEEDS WORK",
                "confidence": 0.8,
                "path": "src/client.js",
            }
        ]
    }
    decisions = [
        {
            "finding_index": 0,
            "decision": "accepted",
            "reason": "Human confirmed this route drift is real.",
            "confidence": 0.95,
        }
    ]

    result = build_learning_candidates(review_result, decisions)

    assert result["candidate_count"] == 1
    candidate = result["candidates"][0]
    assert candidate["status"] == "verified"
    assert "accepted" in candidate["tags"]
    assert candidate["applies_to"] == ["src/client.js"]


def test_learning_loop_writes_memory(tmp_path: Path) -> None:
    review_result = {"classified_findings": [{"message": "Use project boundary.", "evidence": "ADR says so.", "classification": "correct", "category": "architecture", "confidence": 0.7}]}
    decisions = [{"finding_index": 0, "decision": "learn", "reason": "Accepted project rule."}]

    result = run_learning_loop(tmp_path, review_result, decisions, write=True)

    assert result["written"]["written_count"] == 1
    assert (tmp_path / ".main-review" / "memory.json").exists()


def _make_repo(root: Path) -> None:
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "main_review").mkdir()
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("def ok():\n    return True\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_app.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (root / "docs").mkdir()
    for name in [
        "12-external-review-learning-loop.md",
        "19-thetechguy-engineering-standard.md",
        "20-clean-clone-proof.md",
        "21-open-source-reviewer-patterns.md",
    ]:
        (root / "docs" / name).write_text("# Doc\n", encoding="utf-8")


def test_app_bridge_exposes_learning_candidates(tmp_path: Path) -> None:
    _make_repo(tmp_path)

    payload = handle_app_review_request(
        {
            "root": str(tmp_path),
            "mode": "pull_request",
            "changed_files": ["src/app.py"],
            "external_providers": [{"source": "CodeRabbit", "verdict": "NEEDS WORK", "message": "Review route impact."}],
            "human_decisions": [{"finding_index": 0, "decision": "accepted", "reason": "Confirmed."}],
        }
    )

    assert payload["ok"] is True
    assert "learning" in payload
    assert payload["learning"]["learning"]["candidate_count"] >= 1
