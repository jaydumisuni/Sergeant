#!/usr/bin/env python3
"""Select untouched behavioral-defect lineages without persisting ground truth.

This script is evidence infrastructure. It persists only repository, PR number,
defective/fixing SHAs, scored production paths and selector metadata. Titles,
bodies, patches, tests and expected roots are used transiently for qualification
and are deliberately excluded from the output packet.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

EXCLUDED_PARTS = {
    "test", "tests", "testing", "unittest", "unittests", "__tests__",
    "spec", "specs", "fixture", "fixtures", "snapshot", "snapshots",
    "playground", "playgrounds", "example", "examples", "sample", "samples",
    "bench", "benches", "benchmark", "benchmarks", "docs", "doc", ".github",
    "generated", "vendor", "third_party", "third-party", "node_modules",
    "priv", "deps",
}
EXCLUDED_NAMES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock",
    "poetry.lock", "go.sum", "gradle.lockfile", "gemfile.lock", "composer.lock",
    "mix.lock",
}
EXCLUDED_FRAGMENTS = (
    ".test.", ".tests.", ".spec.", "_test.", "_tests.",
    "test_", "tests_", ".snap", ".golden", ".fixture.",
)
TEST_PARTS = {
    "test", "tests", "testing", "unittest", "unittests", "__tests__",
    "spec", "specs",
}
TEST_FRAGMENTS = (
    ".test.", ".spec.", "_test.", "test_", "tests_", "unittest",
)
DISALLOWED_TITLE = re.compile(
    r"^\s*(?:chore|docs?|documentation|typo|javadoc|format|formatting|lint|style|"
    r"cleanup|clean-up|refactor|build|ci|deps?|dependencies|rename)"
    r"(?:\b|\s*[:(])",
    re.I,
)
DISALLOWED_PHRASES = (
    "no functional change", "no behavior change", "no behavioural change",
    "no user-facing change", "no runtime change", "documentation only",
    "comment only", "comments only", "javadoc only", "typo only",
    "formatting only", "lint only", "style only", "refactor only",
    "cleanup only", "static analysis cleanup", "dependency update only",
    "dependencies only", "rename only",
)
POSITIVE_CLUES = re.compile(
    r"\b(?:fix|bug|incorrect|wrong|broken|regression|crash|panic|race|deadlock|"
    r"hang|leak|loss|corrupt|overflow|underflow|security|vulnerab|fail|error|"
    r"missing|invalid|stale|duplicate|idempot|timeout|cancel|exception|restore|"
    r"misbehav|dead|wrongly|unexpected)\w*\b",
    re.I,
)
EXECUTABLE_LINE = re.compile(
    r"[A-Za-z_$@][A-Za-z0-9_$@:.<>?]*|[(){}\[\]=+\-*/&|!]",
    re.I,
)
COMMENT_ONLY = re.compile(
    r"^(?:\s*(?://|///|//!|#|/\*|\*|\*/|<!--|-->|'''|\"\"\"|"
    r"@(?:param|return|throws|see)\b).*)?$"
)
REPOSITORY_PATTERN = re.compile(
    r'(?:repository\s*[:=]\s*|"repository"\s*:\s*")'
    r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)'
)


def _api(path: str, headers: dict[str, str]) -> Any:
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _search(query: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    payload = _api(
        f"/search/issues?q={urllib.parse.quote(query)}"
        "&sort=updated&order=desc&per_page=50",
        headers,
    )
    time.sleep(2.1)
    return list(payload.get("items", [])) if isinstance(payload, dict) else []


def _pr_files(repository: str, number: int, headers: dict[str, str]) -> list[dict[str, Any]]:
    owner, name = repository.split("/", 1)
    payload = _api(f"/repos/{owner}/{name}/pulls/{number}/files?per_page=100", headers)
    return list(payload) if isinstance(payload, list) else []


def _is_test_file(filename: str) -> bool:
    path = Path(filename.replace("\\", "/"))
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return bool(parts & TEST_PARTS) or any(fragment in name for fragment in TEST_FRAGMENTS)


def _is_production_source(filename: str, suffixes: set[str]) -> bool:
    normalized = filename.replace("\\", "/")
    lowered = normalized.lower()
    path = Path(normalized)
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if path.suffix.lower() not in suffixes:
        return False
    if name in EXCLUDED_NAMES or parts & EXCLUDED_PARTS:
        return False
    if any(fragment in name for fragment in EXCLUDED_FRAGMENTS):
        return False
    if any(segment in lowered for segment in (
        "/src/test/", "/src/tests/", "/test/", "/tests/", "/unittests/",
        "/spec/", "/specs/", "/playground/", "/examples/", "/samples/",
    )):
        return False
    return True


def _changed_patch_lines(patch: str) -> tuple[list[str], list[str]]:
    additions: list[str] = []
    deletions: list[str] = []
    for line in patch.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith("+"):
            additions.append(line[1:])
        elif line.startswith("-"):
            deletions.append(line[1:])
    return additions, deletions


def _executable_change_counts(
    rows: list[dict[str, Any]],
    source_files: set[str],
) -> tuple[int, int]:
    added = 0
    removed = 0
    for row in rows:
        filename = str(row.get("filename") or "")
        if filename not in source_files:
            continue
        additions, deletions = _changed_patch_lines(str(row.get("patch") or ""))
        for line in additions:
            stripped = line.strip()
            if stripped and not COMMENT_ONLY.match(line) and EXECUTABLE_LINE.search(stripped):
                added += 1
        for line in deletions:
            stripped = line.strip()
            if stripped and not COMMENT_ONLY.match(line) and EXECUTABLE_LINE.search(stripped):
                removed += 1
    return added, removed


def _qualifies(
    pr: dict[str, Any],
    rows: list[dict[str, Any]],
    source_files: list[str],
) -> bool:
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")
    combined = f"{title}\n{body}".lower()
    if DISALLOWED_TITLE.search(title):
        return False
    if any(phrase in combined for phrase in DISALLOWED_PHRASES):
        return False
    if not POSITIVE_CLUES.search(f"{title}\n{body}"):
        return False
    if not any(_is_test_file(str(row.get("filename") or "")) for row in rows):
        return False
    added, removed = _executable_change_counts(rows, set(source_files))
    return added >= 2 and removed >= 2 and added + removed >= 6


def _eligible_sources(rows: list[dict[str, Any]], suffixes: set[str]) -> list[str]:
    selected: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "modified":
            continue
        filename = str(row.get("filename") or "")
        if _is_production_source(filename, suffixes):
            selected.append(filename)
    return sorted(dict.fromkeys(selected))


def _prior_repositories(set_id: str) -> set[str]:
    prior: set[str] = set()
    for workflow in Path(".github/workflows").glob("model-free-core-*.yml"):
        if set_id in workflow.name:
            continue
        prior.update(REPOSITORY_PATTERN.findall(workflow.read_text(encoding="utf-8", errors="ignore")))
    return prior


def select(
    *,
    reviewer: str,
    set_id: str,
    lanes: list[dict[str, Any]],
    output: Path,
) -> None:
    token = os.environ.get("GH_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"sergeant-{set_id}-selector",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    prior = _prior_repositories(set_id)
    chosen: list[dict[str, Any]] = []
    used = set(prior)

    for lane in lanes:
        selected: dict[str, Any] | None = None
        suffixes = {str(value).lower() for value in lane["suffixes"]}
        for repository in lane["repos"]:
            if repository in used:
                continue
            candidates: list[dict[str, Any]] = []
            seen: set[int] = set()
            for query in (
                f"repo:{repository} is:pr is:merged label:bug",
                f"repo:{repository} is:pr is:merged in:title fix",
            ):
                for item in _search(query, headers):
                    number = int(item.get("number") or 0)
                    if number and number not in seen:
                        candidates.append(item)
                        seen.add(number)
                if len(candidates) >= 25:
                    break

            owner, name = repository.split("/", 1)
            for item in candidates:
                number = int(item.get("number") or 0)
                if not number:
                    continue
                pr = _api(f"/repos/{owner}/{name}/pulls/{number}", headers)
                if not isinstance(pr, dict) or not pr.get("merged_at"):
                    continue
                base = str((pr.get("base") or {}).get("sha") or "")
                head = str((pr.get("head") or {}).get("sha") or "")
                if not base or not head or base == head:
                    continue
                rows = _pr_files(repository, number, headers)
                sources = _eligible_sources(rows, suffixes)
                if not 1 <= len(sources) <= 4:
                    continue
                if not _qualifies(pr, rows, sources):
                    continue
                compare = _api(f"/repos/{owner}/{name}/compare/{base}...{head}", headers)
                if not isinstance(compare, dict):
                    continue
                merge_base = str((compare.get("merge_base_commit") or {}).get("sha") or "")
                if merge_base != base:
                    continue
                if str(compare.get("status") or "") != "ahead":
                    continue
                if int(compare.get("ahead_by") or 0) < 1:
                    continue
                selected = {
                    "lane": str(lane["lane"]),
                    "repository": repository,
                    "source_pr": number,
                    "defective_ref": base,
                    "fixing_ref": head,
                    "changed_files": sources,
                }
                break
            if selected is not None:
                break

        if selected is None:
            raise SystemExit(f"No opaque behavioral-defect candidate found for lane {lane['lane']}")
        used.add(str(selected["repository"]))
        chosen.append(selected)

    if len(chosen) != len(lanes):
        raise SystemExit("Opaque selector did not choose exactly one candidate per lane")

    packet = {
        "schema_version": "sergeant.opaque-candidate-selection.v7",
        "reviewer_frozen_before_selection": reviewer,
        "titles_bodies_patches_tests_persisted": False,
        "production_source_only": True,
        "behavioral_defect_qualification": True,
        "nontrivial_bidirectional_executable_change_required": True,
        "prior_repository_exclusion_count": len(prior),
        "cases": chosen,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    for row in chosen:
        print(
            f"selected lane={row['lane']} repository={row['repository']} "
            f"pr={row['source_pr']} production_files={len(row['changed_files'])}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--set-id", required=True)
    parser.add_argument("--lanes-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    lanes = json.loads(Path(args.lanes_json).read_text(encoding="utf-8"))
    if not isinstance(lanes, list) or len(lanes) != 3:
        raise SystemExit("lanes JSON must contain exactly three lanes")
    select(
        reviewer=args.reviewer,
        set_id=args.set_id,
        lanes=lanes,
        output=Path(args.output),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
