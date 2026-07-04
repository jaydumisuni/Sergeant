from __future__ import annotations

import json
from pathlib import Path

from main_review.memory import ReviewMemoryStore, default_memory_path
from main_review.review_batch import batch_summary, run_review_learning_batch


def test_review_learning_batch_collects_and_ingests(tmp_path: Path) -> None:
    comments_file = tmp_path / "github-comments.json"
    comments_file.write_text(
        json.dumps(
            [
                {
                    "body": "CodeRabbit noticed a missing regression test.",
                    "user": {"login": "coderabbitai"},
                    "path": "src/api.py",
                    "line": 12,
                }
            ]
        ),
        encoding="utf-8",
    )

    result = run_review_learning_batch(comments_file, repository="jaydumisuni/demo", pr_number=5)
    summary = batch_summary(result)

    assert summary["collected_comments"] == 1
    assert summary["sources"] == ["coderabbit"]
    assert summary["inline_comments"] == 1
    assert summary["classification_summary"]["unclassified"] == 1
    assert summary["learning_candidates"] == 0
    assert result["normalized"]["comments"][0]["repository"] == "jaydumisuni/demo"


def test_review_learning_batch_can_write_memory_after_preclassified_comments(tmp_path: Path) -> None:
    comments_file = tmp_path / "github-comments.json"
    comments_file.write_text(
        json.dumps(
            [
                {
                    "body": "Missing receiver validation test.",
                    "user": {"login": "coderabbitai"},
                    "path": "src/api.py",
                    "classification": "🟢",
                }
            ]
        ),
        encoding="utf-8",
    )

    # GitHub raw comments do not normally contain classification, but the batch
    # path must preserve pre-classified exports for offline learning runs.
    result = run_review_learning_batch(comments_file, root=tmp_path, write_memory=True)
    records = ReviewMemoryStore(default_memory_path(tmp_path)).load()

    assert batch_summary(result)["memory_written"] == 1
    assert len(records) == 1
    assert records[0].status == "proposed"
