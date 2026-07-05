from __future__ import annotations

from pathlib import Path

from main_review.evidence import collect_evidence
from main_review.github_collector import collect_github_comments


def test_collect_github_comments_accepts_live_pr_payload_shape() -> None:
    payload = {
        "pull_request": {"number": 16, "title": "Sergeant smoke test"},
        "comments": [
            {
                "body": "Sergeant/Main Review workflow ran and produced the review payload.",
                "user": {"login": "github-actions[bot]"},
                "url": "https://github.com/jaydumisuni/Sergeant/pull/16#issuecomment-4884267376",
            }
        ],
    }

    result = collect_github_comments(payload, repository="jaydumisuni/Sergeant", pr_number=16)

    assert len(result) == 1
    assert result[0].repository == "jaydumisuni/Sergeant"
    assert result[0].pr_number == 16
    assert result[0].source == "github-actions"


def test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Scratch repo\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    fake_value = "x" * 16
    secret_name = "API" + "_KEY"
    (tmp_path / "src" / "config.py").write_text(f'{secret_name}="{fake_value}"\n', encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_config.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    payload = collect_evidence(tmp_path)
    findings = payload["findings"]

    assert any(
        finding["provider"] == "secret-scanner"
        and finding["severity"] == "blocker"
        and finding["category"] == "security"
        for finding in findings
    )
