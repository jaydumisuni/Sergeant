from __future__ import annotations

from pathlib import Path

from main_review.final_proof import assert_final_proof, run_final_proof


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


def test_final_proof_passes_for_verified_repository(tmp_path: Path) -> None:
    _make_verified_repo(tmp_path)

    result = run_final_proof(tmp_path)

    assert result["passed"] is True
    assert result["blockers"] == []
    assert result["review_verdict"]["verdict"] == "PASS"
    assert result["verification"]["status"] == "verified"


def test_final_proof_fails_when_verification_missing(tmp_path: Path) -> None:
    result = run_final_proof(tmp_path)

    assert result["passed"] is False
    assert result["blockers"]


def test_assert_final_proof_exits_on_failure(tmp_path: Path) -> None:
    try:
        assert_final_proof(tmp_path)
    except SystemExit as exc:
        assert "Final proof failed" in str(exc)
    else:
        raise AssertionError("final proof should fail for an empty repository")
