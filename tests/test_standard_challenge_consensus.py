from __future__ import annotations

from pathlib import Path

from main_review.challenge import run_challenge_mode
from main_review.consensus import build_consensus
from main_review.standard_engine import run_standard_engine
from main_review.verdict import review_repository


def _make_verified_repo(root: Path) -> None:
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (root / "main_review").mkdir()
    (root / "tests").mkdir()
    (root / "tests" / "test_app.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
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


def test_standard_engine_and_challenge_mode_pass_verified_repo(tmp_path: Path) -> None:
    _make_verified_repo(tmp_path)

    review = review_repository(tmp_path)
    standard = run_standard_engine(tmp_path, ["src/app.py", "tests/test_app.py"])
    challenge = run_challenge_mode(review)

    assert review["verdict"]["verdict"] == "PASS"
    assert standard["passed"] is True
    assert challenge["challenged"] is True
    assert challenge["trusted"] is True


def test_consensus_uses_strongest_negative_signal() -> None:
    consensus = build_consensus(
        [
            {"source": "main-review", "verdict": "PASS", "evidence": []},
            {"source": "external", "verdict": "BLOCK", "evidence": ["proof"]},
        ]
    )

    assert consensus["consensus"] == "BLOCK"
    assert consensus["summary"]["blocking"] == 1
