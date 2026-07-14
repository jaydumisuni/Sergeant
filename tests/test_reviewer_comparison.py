from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from main_review.review_ingestion import ExternalReviewComment
from main_review.reviewer_comparison import (
    COMPARISON_SCHEMA,
    ReviewerComparisonError,
    compare_reviewer_reports,
    extract_external_findings,
    extract_sergeant_findings,
    load_live_external_comments,
    main,
    match_findings,
    render_comparison_markdown,
)


def _sergeant_packet() -> dict:
    return {
        "verdict": {"verdict": "REQUEST_CHANGES"},
        "review_intelligence": {
            "ranked_findings": [
                {
                    "finding_id": "sgt-auth",
                    "capability": "security_taint",
                    "severity": "major",
                    "message": "Privileged route lacks a visible authorization guard.",
                    "evidence": "src/admin.py:12 defines POST /admin/reset without a role or permission guard.",
                    "path": "src/admin.py",
                    "line_start": 12,
                    "line_end": 12,
                    "root_cause": "authorization-gap",
                    "challenge_result": "survived: evidence is specific enough for review output",
                },
                {
                    "finding_id": "sgt-generic",
                    "capability": "data_flow",
                    "severity": "major",
                    "message": "Input may reach a sink.",
                    "evidence": "Patterns were both detected.",
                    "path": "src/api.py",
                    "challenge_result": "weakened: evidence is too generic",
                },
                {
                    "finding_id": "sgt-test",
                    "capability": "test_impact",
                    "severity": "minor",
                    "message": "Changed behavior lacks focused regression proof.",
                    "evidence": "No changed test targets src/admin.py.",
                    "path": "src/admin.py",
                },
            ]
        },
    }


def _reference_comments() -> list[ExternalReviewComment]:
    return [
        ExternalReviewComment(
            source="live-github-review",
            body="Potential issue: The new admin reset route has no authorization or role guard, allowing an unprivileged caller to invoke it.",
            repository="owner/repo",
            pr_number=10,
            path="src/admin.py",
            line=12,
            author="coderabbitai[bot]",
            url="https://example.invalid/review/1",
        ),
        ExternalReviewComment(
            source="live-github-review",
            body="Nitpick: rename this local variable.",
            repository="owner/repo",
            pr_number=10,
            path="src/admin.py",
            line=4,
            author="coderabbitai[bot]",
        ),
        ExternalReviewComment(
            source="live-github-review",
            body="## Walkthrough\nThis PR adds a reviewer comparison command.",
            repository="owner/repo",
            pr_number=10,
            author="coderabbitai[bot]",
        ),
    ]


def test_sergeant_extraction_keeps_grounded_and_minor_findings() -> None:
    findings = extract_sergeant_findings(_sergeant_packet())

    assert [item.finding_id for item in findings] == ["sgt-auth", "sgt-test"]
    assert all(item.message != "Input may reach a sink." for item in findings)


def test_external_extraction_excludes_nitpicks_and_walkthroughs() -> None:
    findings = extract_external_findings(_reference_comments(), "CodeRabbit")

    assert len(findings) == 1
    assert findings[0].reviewer == "CodeRabbit"
    assert findings[0].path == "src/admin.py"
    assert findings[0].severity == "major"


def test_matching_pairs_equivalent_findings_and_preserves_unique_work() -> None:
    sergeant = extract_sergeant_findings(_sergeant_packet())
    reference = extract_external_findings(_reference_comments(), "CodeRabbit")

    shared, sergeant_only, reference_only = match_findings(sergeant, reference)

    assert len(shared) == 1
    assert shared[0].sergeant.finding_id == "sgt-auth"
    assert shared[0].reference.path == "src/admin.py"
    assert shared[0].path_match is True
    assert shared[0].line_match is True
    assert [item.finding_id for item in sergeant_only] == ["sgt-test"]
    assert reference_only == []


def test_comparison_never_declares_winner_from_comment_volume() -> None:
    result = compare_reviewer_reports(
        _sergeant_packet(),
        _reference_comments(),
        reference_name="CodeRabbit",
    )

    assert result["schema_version"] == COMPARISON_SCHEMA
    assert result["counts"] == {
        "sergeant": 2,
        "reference": 1,
        "shared": 1,
        "sergeant_only": 1,
        "reference_only": 0,
    }
    assert result["winner"] is None
    assert "No winner" in result["winner_rule"]
    assert result["adjudication"]["complete"] is False


def test_adjudication_reports_verified_precision_without_inventing_recall(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.json"
    decisions.write_text(json.dumps({
        "decisions": [
            {"reviewer": "Sergeant", "finding_id": "sgt-auth", "status": "confirmed"},
            {"reviewer": "Sergeant", "finding_id": "sgt-test", "status": "suggestion"},
            {"reviewer": "CodeRabbit", "finding_id": "reference-1", "status": "confirmed"},
        ]
    }), encoding="utf-8")

    result = compare_reviewer_reports(
        _sergeant_packet(),
        _reference_comments(),
        reference_name="CodeRabbit",
        adjudication_file=decisions,
    )

    assert result["adjudication"]["complete"] is True
    assert result["adjudication"]["sergeant"]["verified_precision"] == 1.0
    assert result["adjudication"]["reference"]["verified_precision"] == 1.0
    assert result["winner"] is None


def test_markdown_renders_reviewers_side_by_side() -> None:
    result = compare_reviewer_reports(_sergeant_packet(), _reference_comments(), reference_name="CodeRabbit")
    markdown = render_comparison_markdown(result)

    assert "| Metric | Sergeant | CodeRabbit |" in markdown
    assert "src/admin.py:12" in markdown
    assert "## Unique findings" in markdown
    assert "No winner is declared" in markdown


@dataclass(frozen=True)
class FakeLiveResult:
    pull_request: dict
    all_comments: list[dict]

    def proof_dict(self) -> dict:
        return {"proof_version": "test-proof"}


def test_live_fetch_filters_author_and_freezes_head(monkeypatch: pytest.MonkeyPatch) -> None:
    result = FakeLiveResult(
        pull_request={"head": {"sha": "frozen-head"}},
        all_comments=[
            {
                "body": "Potential issue: missing authorization guard.",
                "path": "src/admin.py",
                "line": 12,
                "html_url": "https://example.invalid/1",
                "user": {"login": "coderabbitai[bot]"},
            },
            {
                "body": "Unrelated human comment.",
                "path": "src/admin.py",
                "line": 8,
                "user": {"login": "human"},
            },
        ],
    )
    monkeypatch.setattr("main_review.reviewer_comparison.fetch_pr_comments_live", lambda *args, **kwargs: result)

    comments, metadata = load_live_external_comments(
        "owner/repo",
        10,
        author="coderabbitai",
        expected_head_sha="frozen-head",
    )

    assert len(comments) == 1
    assert comments[0].author == "coderabbitai[bot]"
    assert metadata["head_sha"] == "frozen-head"
    assert metadata["matched_author_comment_count"] == 1

    with pytest.raises(ReviewerComparisonError, match="PR head changed"):
        load_live_external_comments(
            "owner/repo",
            10,
            author="coderabbitai",
            expected_head_sha="different-head",
        )


def test_cli_writes_json_and_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    packet_path = tmp_path / "sergeant.json"
    packet_path.write_text(json.dumps(_sergeant_packet()), encoding="utf-8")
    review_path = tmp_path / "reference.json"
    review_path.write_text(json.dumps({
        "comments": [comment.to_dict() for comment in _reference_comments()]
    }), encoding="utf-8")
    json_output = tmp_path / "comparison.json"
    markdown_output = tmp_path / "comparison.md"

    code = main([
        "--sergeant-packet", str(packet_path),
        "--reference-review", str(review_path),
        "--reference-name", "CodeRabbit",
        "--output", str(json_output),
        "--markdown-output", str(markdown_output),
        "--pretty",
    ])

    assert code == 0
    assert json.loads(capsys.readouterr().out)["reference_name"] == "CodeRabbit"
    assert json.loads(json_output.read_text(encoding="utf-8"))["winner"] is None
    assert "Sergeant Reviewer Comparison" in markdown_output.read_text(encoding="utf-8")
