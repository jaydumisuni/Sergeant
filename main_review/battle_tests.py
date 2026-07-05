"""Battle-test fixture validation for Sergeant.

Battle tests are local, static evidence records. This module intentionally does
not fetch networks or execute target repositories. It only validates that the
fixtures committed under battle-tests/ have the fields needed for repeatable
comparison.
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


def _fixture_id(payload: dict[str, Any], path: Path) -> str:
    repo = payload.get("repository")
    pr = payload.get("pull_request")
    if isinstance(repo, str) and repo and isinstance(pr, int):
        return f"{repo}#{pr}"
    return path.stem


def validate_battle_fixture(path: Path) -> BattleFixtureResult:
    issues: list[str] = []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return BattleFixtureResult(
            path=str(path),
            fixture_id=path.stem,
            status="invalid",
            issues=[f"invalid json: {error.msg}"],
        )

    if not isinstance(payload, dict):
        return BattleFixtureResult(
            path=str(path),
            fixture_id=path.stem,
            status="invalid",
            issues=["fixture root must be an object"],
        )

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

    return BattleFixtureResult(
        path=str(path),
        fixture_id=_fixture_id(payload, path),
        status="valid" if not issues else "invalid",
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
            "fixtures": [],
            "next_actions": ["Create battle-tests/ with at least one JSON fixture."],
        }

    fixture_paths = sorted(fixture_dir.glob("*.json"))
    results = [validate_battle_fixture(path) for path in fixture_paths]
    invalid = [result for result in results if result.status != "valid"]

    return {
        "status": "verified" if results and not invalid else "needs_work",
        "fixture_count": len(results),
        "valid_count": len(results) - len(invalid),
        "invalid_count": len(invalid),
        "fixtures": [result.to_dict() for result in results],
        "next_actions": [] if results and not invalid else ["Fix invalid battle-test fixtures."],
    }
