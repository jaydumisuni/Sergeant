#!/usr/bin/env python3
"""Select opaque historical defect lineages without persisting ground truth text.

This selector is operational infrastructure, not reviewer intelligence. A workflow
copies it before checking out the already-frozen reviewer, then executes it only
after that reviewer commit is pinned. Titles, bodies, patches and tests may be
used transiently for qualification but are never written to the selection packet.
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

SCHEMA = "sergeant.opaque-candidate-selection.v7"

EXCLUDED_PARTS = {
    "test", "tests", "testing", "unittest", "unittests", "__tests__",
    "spec", "specs", "fixture", "fixtures", "snapshot", "snapshots",
    "playground", "playgrounds", "example", "examples", "sample", "samples",
    "bench", "benches", "benchmark", "benchmarks", "docs", "doc", ".github",
    "generated", "vendor", "third_party", "third-party", "node_modules",
    "migration", "migrations", "changelog", "changelogs",
}
EXCLUDED_NAMES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock",
    "poetry.lock", "go.sum", "gradle.lockfile", "gemfile.lock", "composer.lock",
}
EXCLUDED_FRAGMENTS = (
    ".test.", ".tests.", ".spec.", "_test.", "_tests.", "test_", "tests_",
    ".snap", ".golden", ".fixture.", ".generated.", "_generated.",
)
TEST_PARTS = {"test", "tests", "testing", "unittest", "unittests", "__tests__", "spec", "specs"}
TEST_FRAGMENTS = (".test.", ".spec.", "_test.", "test_", "tests_", "unittest")

DISALLOWED_TITLE = re.compile(
    r"^\s*(?:chore|docs?|documentation|typo|javadoc|format|formatting|lint|style|cleanup|clean-up|"
    r"refactor|build|ci|deps?|dependencies|rename|comment|comments|test|tests)(?:\b|\s*[:(])",
    re.I,
)
DISALLOWED_PHRASES = (
    "no functional change", "no behavior change", "no behavioural change",
    "no user-facing change", "no runtime change", "documentation only",
    "comment only", "comments only", "javadoc only", "typo only",
    "formatting only", "lint only", "style only", "refactor only",
    "cleanup only", "static analysis cleanup", "dependency update only",
    "dependencies only", "rename only", "test only", "tests only",
    "non-functional", "behavior-preserving", "behaviour-preserving",
)
POSITIVE_CLUES = re.compile(
    r"\b(?:fix|bug|incorrect|wrong|broken|regression|crash|panic|race|deadlock|hang|leak|loss|"
    r"corrupt|overflow|underflow|security|vulnerab|fail|error|missing|invalid|stale|duplicate|"
    r"idempot|timeout|cancel|exception|restore|misbehav|freeze|retry|attempt|protocol)\w*\b",
    re.I,
)
EXECUTABLE_LINE = re.compile(r"[A-Za-z_$@][A-Za-z0-9_$@:.<>?'-]*|[(){}\[\]=+\-*/&|!]", re.I)
COMMENT_ONLY = re.compile(
    r"^(?:\s*(?://|///|//!|#|;|--|/\*|\*|\*/|<!--|-->|'''|\"\"\"|@(?:param|return|throws|see)\b).*)?$"
)
REPOSITORY_PATTERN = re.compile(
    r"(?:repository\s*[:=]\s*|\"repository\"\s*:\s*\")([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
)


def parse_lane(raw: str) -> dict[str, Any]:
    try:
        name, suffix_text, repository_text = raw.split("=", 2)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("lane must be NAME=.ext,.ext=owner/repo,owner/repo") from exc
    suffixes = {item.strip().lower() for item in suffix_text.split(",") if item.strip()}
    repositories = [item.strip() for item in repository_text.split(",") if item.strip()]
    if not name.strip() or not suffixes or not repositories:
        raise argparse.ArgumentTypeError("lane name, suffixes and repositories are required")
    if any(not item.startswith(".") for item in suffixes):
        raise argparse.ArgumentTypeError("every suffix must begin with a dot")
    if any(item.count("/") != 1 for item in repositories):
        raise argparse.ArgumentTypeError("repositories must use owner/name")
    return {"lane": name.strip(), "suffixes": suffixes, "repos": repositories}


def api(path: str, headers: dict[str, str]) -> object:
    request = urllib.request.Request(f"https://api.github.com{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def search(query: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    payload = api(f"/search/issues?q={urllib.parse.quote(query)}&sort=updated&order=desc&per_page=50", headers)
    return list(payload.get("items", [])) if isinstance(payload, dict) else []


def pr_files(repository: str, number: int, headers: dict[str, str]) -> list[dict[str, Any]]:
    owner, name = repository.split("/", 1)
    payload = api(f"/repos/{owner}/{name}/pulls/{number}/files?per_page=100", headers)
    return list(payload) if isinstance(payload, list) else []


def is_test_file(filename: str) -> bool:
    path = Path(filename.replace("\\", "/"))
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return bool(parts & TEST_PARTS) or any(fragment in name for fragment in TEST_FRAGMENTS)


def is_production_source(filename: str, suffixes: set[str]) -> bool:
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
        "/priv/repo/migrations/", "/db/migrate/",
    )):
        return False
    return True


def changed_patch_lines(patch: str) -> list[str]:
    result: list[str] = []
    for line in patch.splitlines():
        if line.startswith(("+++", "---", "@@")):
            continue
        if line.startswith(("+", "-")):
            result.append(line[1:])
    return result


def executable_code_changes(rows: list[dict[str, Any]], source_files: set[str]) -> tuple[int, int, int]:
    total = additions = deletions = 0
    for row in rows:
        filename = str(row.get("filename") or "")
        if filename not in source_files:
            continue
        for raw in str(row.get("patch") or "").splitlines():
            if raw.startswith(("+++", "---", "@@")) or not raw.startswith(("+", "-")):
                continue
            line = raw[1:]
            stripped = line.strip()
            if not stripped or COMMENT_ONLY.match(line) or not EXECUTABLE_LINE.search(stripped):
                continue
            total += 1
            if raw.startswith("+"):
                additions += 1
            else:
                deletions += 1
    return total, additions, deletions


def eligible_sources(rows: list[dict[str, Any]], suffixes: set[str]) -> list[str]:
    selected: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("status") != "modified":
            continue
        filename = str(row.get("filename") or "")
        if is_production_source(filename, suffixes):
            selected.append(filename)
    return sorted(dict.fromkeys(selected))


def qualifies(pr: dict[str, Any], rows: list[dict[str, Any]], sources: list[str]) -> bool:
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")
    combined = f"{title}\n{body}".lower()
    if DISALLOWED_TITLE.search(title) or any(phrase in combined for phrase in DISALLOWED_PHRASES):
        return False
    if not POSITIVE_CLUES.search(f"{title}\n{body}"):
        return False
    if not any(is_test_file(str(row.get("filename") or "")) for row in rows):
        return False
    total, additions, deletions = executable_code_changes(rows, set(sources))
    if total < 5 or additions < 1 or deletions < 1:
        return False
    if int(pr.get("changed_files") or 0) > 80:
        return False
    return True


def prior_repositories(workflow_root: Path, current_set: str) -> set[str]:
    result: set[str] = set()
    for workflow in workflow_root.glob("model-free-core-*.yml"):
        if current_set in workflow.name:
            continue
        result.update(REPOSITORY_PATTERN.findall(workflow.read_text(encoding="utf-8", errors="ignore")))
    return result


def select(args: argparse.Namespace) -> dict[str, Any]:
    token = os.environ.get("GH_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"sergeant-{args.set_id}-selector",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    lanes = [parse_lane(item) for item in args.lane]
    used = prior_repositories(Path(args.workflow_root), args.set_id)
    chosen: list[dict[str, Any]] = []

    for lane in lanes:
        selected: dict[str, Any] | None = None
        for repository in lane["repos"]:
            if repository in used:
                continue
            candidates: list[dict[str, Any]] = []
            seen: set[int] = set()
            for query in (
                f"repo:{repository} is:pr is:merged label:bug",
                f"repo:{repository} is:pr is:merged in:title fix",
                f"repo:{repository} is:pr is:merged in:title regression",
                f"repo:{repository} is:pr is:merged in:title crash",
            ):
                for item in search(query, headers):
                    number = int(item.get("number") or 0)
                    if number and number not in seen:
                        candidates.append(item)
                        seen.add(number)
                if len(candidates) >= 30:
                    break

            owner, name = repository.split("/", 1)
            for item in candidates:
                number = int(item.get("number") or 0)
                if not number:
                    continue
                pr = api(f"/repos/{owner}/{name}/pulls/{number}", headers)
                if not isinstance(pr, dict) or not pr.get("merged_at"):
                    continue
                base = str((pr.get("base") or {}).get("sha") or "")
                head = str((pr.get("head") or {}).get("sha") or "")
                if not base or not head or base == head:
                    continue
                rows = pr_files(repository, number, headers)
                sources = eligible_sources(rows, set(lane["suffixes"]))
                if not (1 <= len(sources) <= 4) or not qualifies(pr, rows, sources):
                    continue
                compare = api(f"/repos/{owner}/{name}/compare/{base}...{head}", headers)
                if not isinstance(compare, dict):
                    continue
                if str((compare.get("merge_base_commit") or {}).get("sha") or "") != base:
                    continue
                if str(compare.get("status") or "") != "ahead" or int(compare.get("ahead_by") or 0) < 1:
                    continue
                selected = {
                    "lane": lane["lane"],
                    "repository": repository,
                    "source_pr": number,
                    "defective_ref": base,
                    "fixing_ref": head,
                    "changed_files": sources,
                }
                break
            if selected is not None:
                break
            time.sleep(0.2)

        if selected is None:
            raise SystemExit(f"No opaque behavioral-defect candidate found for lane {lane['lane']}")
        used.add(str(selected["repository"]))
        chosen.append(selected)

    if len(chosen) != len(lanes):
        raise SystemExit("Opaque selection did not fill every lane")

    return {
        "schema_version": SCHEMA,
        "reviewer_frozen_before_selection": args.reviewer,
        "titles_bodies_patches_tests_persisted": False,
        "production_source_only": True,
        "behavioral_defect_qualification": True,
        "nontrivial_executable_change_required": True,
        "bidirectional_code_change_required": True,
        "prior_repository_exclusion_count": len(prior_repositories(Path(args.workflow_root), args.set_id)),
        "cases": chosen,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--set-id", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workflow-root", default=".github/workflows")
    parser.add_argument("--lane", action="append", required=True)
    args = parser.parse_args()
    payload = select(args)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for row in payload["cases"]:
        print(
            f"selected lane={row['lane']} repository={row['repository']} "
            f"pr={row['source_pr']} production_files={len(row['changed_files'])}"
        )


if __name__ == "__main__":
    main()
