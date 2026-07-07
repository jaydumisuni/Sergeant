"""Battle-test fixture validation and review-signal comparison for Sergeant.

Battle tests are local, static evidence records. This module intentionally does
not fetch networks or execute target repositories. It validates committed
battle fixtures and computes a repeatable comparison between reviewer/maintainer
signals and expected Sergeant findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIXTURE_FIELDS = (
    "repository",
    "pull_request",
    "url",
    "title",
    "outcome",
    "review_signals",
    "expected_sergeant_findings",
    "expected_initial_verdict",
    "expected_final_verdict",
)

ALLOWED_VERDICTS = {
    "PASS",
    "PASS_WITH_WATCH",
    "NEEDS WORK",
    "BLOCK",
    "TRUSTED_WITH_WATCH",
}

FINAL_VERDICT_SENTINEL = "FINAL_VERDICT"

SIGNAL_FINDING_RULES = (
    (("overlap", "duplicate"), ("duplicate", "parameterized")),
    (("narrow", "input", "clarity", "unrelated"), ("unrelated", "clarity")),
    (("simplification", "small", "targeted"), ("small", "targeted")),
    (("architecture", "lifecycle"), ("architecture",)),
    (("documentation", "migration", "deprecation"), ("migration", "deprecation")),
    (("external app", "downstream app", "proxy"), ("proxy", "availability")),
    (("copied", "context", "counter"), ("copied", "context", "regression")),
    (("urlparse", "query", "separator", "question mark"), ("query", "detection", "question")),
    (("looked good", "suggestion", "review"), ("follow-up", "feedback", "final")),
    (("follow-up", "review feedback", "closing"), ("follow-up", "feedback", "final")),
)

FINAL_VERDICT_TERMS = ("approved", "merged", "passed", "accepted")


@dataclass(frozen=True)
class BattleFixtureResult:
    path: str
    fixture_id: str
    status: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "fixture_id": self.fixture_id,
            "status": self.status,
            "issues": self.issues,
        }


@dataclass(frozen=True)
class BattleComparisonResult:
    path: str
    fixture_id: str
    status: str
    signal_count: int
    matched_signal_count: int
    finding_count: int
    referenced_finding_count: int
    matches: list[dict[str, str]]
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "fixture_id": self.fixture_id,
            "status": self.status,
            "signal_count": self.signal_count,
            "matched_signal_count": self.matched_signal_count,
            "finding_count": self.finding_count,
            "referenced_finding_count": self.referenced_finding_count,
            "matches": self.matches,
            "issues": self.issues,
        }


def _load_fixture(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return None, [f"invalid json: {error.msg}"]

    if not isinstance(payload, dict):
        return None, ["fixture root must be an object"]

    return payload, []


def _fixture_id(payload: dict[str, Any], path: Path) -> str:
    repo = payload.get("repository")
    pr = payload.get("pull_request")
    if isinstance(repo, str) and repo and isinstance(pr, int):
        return f"{repo}#{pr}"
    return path.stem


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _find_expected_match(signal: str, findings: list[str]) -> str | None:
    signal_lower = signal.lower()
    for signal_terms, finding_terms in SIGNAL_FINDING_RULES:
        if _contains_any(signal_lower, signal_terms):
            for finding in findings:
                if _contains_any(finding, finding_terms):
                    return finding

    if _contains_any(signal_lower, FINAL_VERDICT_TERMS):
        return FINAL_VERDICT_SENTINEL

    return None


def validate_battle_fixture(path: Path) -> BattleFixtureResult:
    payload, load_issues = _load_fixture(path)
    if payload is None:
        return BattleFixtureResult(path=str(path), fixture_id=path.stem, status="invalid", issues=load_issues)

    issues: list[str] = []

    for field in REQUIRED_FIXTURE_FIELDS:
        if field not in payload:
            issues.append(f"missing required field: {field}")

    if not isinstance(payload.get("repository"), str) or "/" not in payload.get("repository", ""):
        issues.append('repository must be an "owner/name" string')

    if not isinstance(payload.get("pull_request"), int):
        issues.append("pull_request must be an integer")

    if not isinstance(payload.get("review_signals"), list) or not payload.get("review_signals"):
        issues.append("review_signals must be a non-empty list")

    if not isinstance(payload.get("expected_sergeant_findings"), list) or not payload.get("expected_sergeant_findings"):
        issues.append("expected_sergeant_findings must be a non-empty list")

    for verdict_field in ("expected_initial_verdict", "expected_final_verdict"):
        verdict = payload.get(verdict_field)
        if verdict not in ALLOWED_VERDICTS:
            issues.append(f"{verdict_field} must be one of: {', '.join(sorted(ALLOWED_VERDICTS))}")

    return BattleFixtureResult(path=str(path), fixture_id=_fixture_id(payload, path), status="valid" if not issues else "invalid", issues=issues)


def compare_battle_fixture(path: Path) -> BattleComparisonResult:
    fixture_result = validate_battle_fixture(path)
    payload, load_issues = _load_fixture(path)
    if payload is None:
        return BattleComparisonResult(path=str(path), fixture_id=path.stem, status="failed", signal_count=0, matched_signal_count=0, finding_count=0, referenced_finding_count=0, matches=[], issues=load_issues)

    review_signals = [signal for signal in payload.get("review_signals", []) if isinstance(signal, str)]
    expected_findings = [finding for finding in payload.get("expected_sergeant_findings", []) if isinstance(finding, str)]

    issues = list(fixture_result.issues)
    matches: list[dict[str, str]] = []
    referenced_findings: set[str] = set()

    for signal in review_signals:
        matched_finding = _find_expected_match(signal, expected_findings)
        if matched_finding is None:
            issues.append(f"review signal has no computed Sergeant comparison match: {signal}")
            continue

        matches.append({"review_signal": signal, "matched_finding": matched_finding})
        if matched_finding != FINAL_VERDICT_SENTINEL:
            referenced_findings.add(matched_finding)

    if expected_findings and len(referenced_findings) < max(1, len(expected_findings) // 2):
        issues.append("review comparison must reference at least half of expected_sergeant_findings")

    return BattleComparisonResult(path=str(path), fixture_id=_fixture_id(payload, path), status="passed" if not issues else "failed", signal_count=len(review_signals), matched_signal_count=len(matches), finding_count=len(expected_findings), referenced_finding_count=len(referenced_findings), matches=matches, issues=issues)


def validate_battle_fixtures(root: Path) -> dict[str, Any]:
    fixture_dir = root / "battle-tests"
    if not fixture_dir.exists():
        return {
            "status": "missing",
            "fixture_count": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "review_comparison_status": "missing",
            "review_comparison_passed_count": 0,
            "review_comparison_failed_count": 0,
            "fixtures": [],
            "comparisons": [],
            "next_actions": ["Create battle-tests/ with at least one JSON fixture."],
        }

    fixture_paths = sorted(fixture_dir.glob("*.json"))
    results = [validate_battle_fixture(path) for path in fixture_paths]
    comparisons = [compare_battle_fixture(path) for path in fixture_paths]
    invalid = [result for result in results if result.status != "valid"]
    failed_comparisons = [comparison for comparison in comparisons if comparison.status != "passed"]
    passed = bool(results) and not invalid and not failed_comparisons

    next_actions: list[str] = []
    if not results:
        next_actions.append("Add at least one battle-test fixture.")
    if invalid:
        next_actions.append("Fix invalid battle-test fixtures.")
    if failed_comparisons:
        next_actions.append("Fix failed battle review comparisons.")

    return {
        "status": "verified" if passed else "needs_work",
        "fixture_count": len(results),
        "valid_count": len(results) - len(invalid),
        "invalid_count": len(invalid),
        "review_comparison_status": "passed" if comparisons and not failed_comparisons else "needs_work",
        "review_comparison_passed_count": len(comparisons) - len(failed_comparisons),
        "review_comparison_failed_count": len(failed_comparisons),
        "fixtures": [result.to_dict() for result in results],
        "comparisons": [comparison.to_dict() for comparison in comparisons],
        "next_actions": next_actions,
    }
