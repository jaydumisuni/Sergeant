"""Battle-test fixture validation and review-signal comparison for Sergeant.

Battle tests are local, static evidence records. This module intentionally does
not fetch networks or execute target repositories. It validates that committed
fixtures contain enough evidence for repeatable comparison, then checks that
maintainer/reviewer signals are explicitly mapped to Sergeant findings or final
verdict evidence.
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
    "review_comparison",
)

ALLOWED_VERDICTS = {
    "PASS",
    "PASS_WITH_WATCH",
    "NEEDS WORK",
    "BLOCK",
    "TRUSTED_WITH_WATCH",
}

FINAL_VERDICT_SENTINEL = "__final_verdict__"


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


def validate_battle_fixture(path: Path) -> BattleFixtureResult:
    payload, load_issues = _load_fixture(path)
    if payload is None:
        return BattleFixtureResult(
            path=str(path),
            fixture_id=path.stem,
            status="invalid",
            issues=load_issues,
        )

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

    if not isinstance(payload.get("review_comparison"), list) or not payload.get("review_comparison"):
        issues.append("review_comparison must be a non-empty list")

    for verdict_field in ("expected_initial_verdict", "expected_final_verdict"):
        verdict = payload.get(verdict_field)
        if verdict not in ALLOWED_VERDICTS:
            issues.append(f"{verdict_field} must be one of: {', '.join(sorted(ALLOWED_VERDICTS))}")

    return BattleFixtureResult(
        path=str(path),
        fixture_id=_fixture_id(payload, path),
        status="valid" if not issues else "invalid",
        issues=issues,
    )


def compare_battle_fixture(path: Path) -> BattleComparisonResult:
    fixture_result = validate_battle_fixture(path)
    payload, load_issues = _load_fixture(path)
    if payload is None:
        return BattleComparisonResult(
            path=str(path),
            fixture_id=path.stem,
            status="failed",
            signal_count=0,
            matched_signal_count=0,
            finding_count=0,
            referenced_finding_count=0,
            issues=load_issues,
        )

    review_signals = payload.get("review_signals") if isinstance(payload.get("review_signals"), list) else []
    expected_findings = payload.get("expected_sergeant_findings") if isinstance(payload.get("expected_sergeant_findings"), list) else []
    comparisons = payload.get("review_comparison") if isinstance(payload.get("review_comparison"), list) else []

    issues = list(fixture_result.issues)
    signal_set = {signal for signal in review_signals if isinstance(signal, str)}
    finding_set = {finding for finding in expected_findings if isinstance(finding, str)}
    matched_signals: set[str] = set()
    referenced_findings: set[str] = set()

    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            issues.append(f"review_comparison[{index}] must be an object")
            continue

        signal = comparison.get("review_signal")
        matched_finding = comparison.get("matched_finding")
        basis = comparison.get("basis")

        if signal not in signal_set:
            issues.append(f"review_comparison[{index}].review_signal must match a committed review_signals entry")
        else:
            matched_signals.add(signal)

        if matched_finding == FINAL_VERDICT_SENTINEL:
            referenced_findings.add(FINAL_VERDICT_SENTINEL)
        elif matched_finding not in finding_set:
            issues.append(
                f"review_comparison[{index}].matched_finding must match an expected_sergeant_findings entry or {FINAL_VERDICT_SENTINEL}"
            )
        else:
            referenced_findings.add(matched_finding)

        if not isinstance(basis, str) or not basis.strip():
            issues.append(f"review_comparison[{index}].basis must explain the match")

    missing_signals = signal_set - matched_signals
    for signal in sorted(missing_signals):
        issues.append(f"review signal has no comparison match: {signal}")

    non_verdict_references = referenced_findings - {FINAL_VERDICT_SENTINEL}
    if finding_set and len(non_verdict_references) < max(1, len(finding_set) // 2):
        issues.append("review comparison must reference at least half of expected_sergeant_findings")

    return BattleComparisonResult(
        path=str(path),
        fixture_id=_fixture_id(payload, path),
        status="passed" if not issues else "failed",
        signal_count=len(signal_set),
        matched_signal_count=len(matched_signals),
        finding_count=len(finding_set),
        referenced_finding_count=len(non_verdict_references),
        issues=issues,
    )


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
