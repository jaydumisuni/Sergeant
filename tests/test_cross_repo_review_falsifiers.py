from __future__ import annotations

from pathlib import Path

from main_review.evidence import SECRET_PATTERNS, _placeholder_secret
from main_review.standard_engine import check_claims_match_implementation


def _generic_secret_match(line: str):
    pattern = dict(SECRET_PATTERNS)["generic api key assignment"]
    match = pattern.search(line)
    assert match is not None
    return match


def test_negative_control_must_not_secret_sentinels_are_not_reported_as_credentials() -> None:
    assert _placeholder_secret(_generic_secret_match('apiKey: "must-not-survive"'))
    assert _placeholder_secret(_generic_secret_match('token: "must-not-enter-pete-state"'))


def test_real_looking_generic_api_key_assignment_is_not_falsified() -> None:
    assert not _placeholder_secret(_generic_secret_match('api_key = "abcdefghijklmnop"'))


def test_generic_repository_reasoning_docs_do_not_require_sergeant_internal_modules(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("This repository implements deterministic reasoning behavior.\n")
    (tmp_path / "package.json").write_text('{"name":"external-review-target"}\n')
    report = check_claims_match_implementation(tmp_path)
    assert report["finding_count"] == 0


def test_sergeant_repository_reasoning_claim_still_requires_canonical_review_stack(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("Sergeant provides reasoning behavior.\n")
    (tmp_path / "main_review").mkdir()
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "sergeant-reviewer"\n')
    report = check_claims_match_implementation(tmp_path)
    assert report["finding_count"] == 1
