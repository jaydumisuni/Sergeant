"""Static async/lifecycle invariants that require ordering and state-contract reasoning."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

_TERMINAL_STATES = {
    "completed",
    "failed",
    "stopped",
    "cancelled",
    "canceled",
    "aborted",
    "terminated",
    "done",
    "closed",
    "finished",
}
_END_MARKERS = ("ended_at", "finished_at", "completed_at", "closed_at", "terminated_at")
_SOURCE_SUFFIXES = {".py", ".pyi", ".js", ".jsx", ".ts", ".tsx"}


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _path(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _path(node.value)
        return f"{base}.{node.attr}" if base else None
    if isinstance(node, ast.Subscript):
        base = _path(node.value)
        if not base:
            return None
        if isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            return f"{base}[{node.slice.value!r}]"
    return None


def _root_name(path: str) -> str:
    return path.split(".", 1)[0].split("[", 1)[0]


def _loop_names(target: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(target) if isinstance(node, ast.Name)}


def _falsey_guard_paths(node: ast.AST) -> set[str]:
    paths: set[str] = set()
    if isinstance(node, ast.BoolOp):
        for value in node.values:
            paths.update(_falsey_guard_paths(value))
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        candidate = _path(node.operand)
        if candidate:
            paths.add(candidate)
    elif isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        left = _path(node.left)
        right = node.comparators[0]
        op = node.ops[0]
        if left and isinstance(right, ast.Constant) and right.value in {None, False, ""}:
            if isinstance(op, (ast.Is, ast.Eq)):
                paths.add(left)
        right_path = _path(right)
        if right_path and isinstance(node.left, ast.Constant) and node.left.value in {None, False, ""}:
            if isinstance(op, (ast.Is, ast.Eq)):
                paths.add(right_path)
    return paths


def _is_release_value(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value in {None, False, ""}


def _claim_assignments(statements: list[ast.stmt]) -> list[tuple[str, int]]:
    claims: list[tuple[str, int]] = []
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, ast.Assign):
                if _is_release_value(node.value):
                    continue
                for target in node.targets:
                    candidate = _path(target)
                    if candidate:
                        claims.append((candidate, node.lineno))
            elif isinstance(node, ast.AnnAssign):
                if _is_release_value(node.value):
                    continue
                candidate = _path(node.target)
                if candidate:
                    claims.append((candidate, node.lineno))
    return claims


def _await_lines(statements: list[ast.stmt]) -> list[int]:
    return [node.lineno for statement in statements for node in ast.walk(statement) if isinstance(node, ast.Await)]


def _lock_regions(function: ast.AsyncFunctionDef) -> list[tuple[int, int]]:
    regions: list[tuple[int, int]] = []
    for node in ast.walk(function):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        contexts = " ".join(ast.unparse(item.context_expr) for item in node.items).lower()
        if any(token in contexts for token in ("lock", "mutex", "semaphore")):
            regions.append((node.lineno, getattr(node, "end_lineno", node.lineno)))
    return regions


def _inside(line: int, regions: Iterable[tuple[int, int]]) -> bool:
    return any(start <= line <= end for start, end in regions)


def _finding(
    *,
    officer: str,
    capability: str,
    severity: str,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    supporting: Iterable[str],
    falsifiers: Iterable[str],
    verification: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "source": "static-async-lifecycle-officer",
        "officer": officer,
        "capability": capability,
        "category": capability,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(supporting),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _await_before_resource_claim(path: str, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for function in ast.walk(tree):
        if not isinstance(function, ast.AsyncFunctionDef):
            continue
        lock_regions = _lock_regions(function)
        for loop in ast.walk(function):
            if not isinstance(loop, (ast.For, ast.AsyncFor)):
                continue
            loop_names = _loop_names(loop.target)
            if not loop_names:
                continue
            for branch in ast.walk(loop):
                if not isinstance(branch, ast.If):
                    continue
                guard_paths = {
                    candidate
                    for candidate in _falsey_guard_paths(branch.test)
                    if _root_name(candidate) in loop_names
                }
                if not guard_paths:
                    continue
                await_lines = sorted(_await_lines(branch.body))
                claims = sorted(_claim_assignments(branch.body), key=lambda item: item[1])
                if not await_lines or not claims:
                    continue
                for guarded_path in sorted(guard_paths):
                    matching_claims = [line for candidate, line in claims if candidate == guarded_path]
                    if not matching_claims:
                        continue
                    first_await = await_lines[0]
                    claims_before_await = [line for line in matching_claims if line < first_await]
                    claims_after_await = [line for line in matching_claims if line > first_await]
                    if claims_before_await or not claims_after_await:
                        continue
                    claim_line = claims_after_await[0]
                    if _inside(first_await, lock_regions) and _inside(claim_line, lock_regions):
                        continue
                    key = (guarded_path, branch.lineno)
                    if key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        _finding(
                            officer="Mechanic",
                            capability="concurrency",
                            severity="major",
                            root_cause="resource-claim-after-await",
                            path=path,
                            line_start=branch.lineno,
                            message="A resource is checked as available, then awaited work runs before the resource is claimed.",
                            evidence=(
                                f"{function.name} checks {guarded_path} as unclaimed at line {branch.lineno}, "
                                f"crosses an await at line {first_await}, and assigns the claim only at line {claim_line}. "
                                "A concurrent handler can pass the same availability check while the first task is suspended."
                            ),
                            supporting=(
                                f"{path}:{branch.lineno}",
                                f"{path}:{first_await}",
                                f"{path}:{claim_line}",
                            ),
                            falsifiers=(
                                "Checked for a claim assignment to the same resource before the first await.",
                                "Checked whether the availability check and claim are enclosed by the same lock/mutex/semaphore region.",
                                "Checked that the guarded object is the resource selected by the enclosing loop rather than unrelated local state.",
                                "Ignored rollback assignments that release the claim with None/False/empty values.",
                            ),
                            verification=(
                                "Claim the selected resource before the first suspension point, release it on send/dispatch failure, "
                                "and prove two concurrent starts cannot both select the same resource."
                            ),
                            confidence=0.98,
                        )
                    )
    return findings


def _status_literal_refs(scope: Path) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    scanned = 0
    if not scope.exists():
        return refs
    for file_path in scope.rglob("*"):
        if scanned >= 2500:
            break
        if not file_path.is_file() or file_path.suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        if any(part in {".git", ".venv", "venv", "node_modules", "dist", "build"} for part in file_path.parts):
            continue
        scanned += 1
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative = file_path.relative_to(scope)
        for match in re.finditer(
            r"(?:\bstatus\s*=\s*|[\"']status[\"']\s*:\s*)[\"']"
            r"(completed|failed|stopped|cancelled|canceled|aborted|terminated|done|closed|finished)[\"']",
            text,
            re.I,
        ):
            status = match.group(1).lower()
            line = text[: match.start()].count("\n") + 1
            refs.setdefault(status, []).append(f"{relative.as_posix()}:{line}")
    return refs


def _terminal_state_timestamp_omission(root: Path, path: str, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    source_path = root / path
    scope = source_path.parent.parent if source_path.parent.parent.is_dir() else source_path.parent
    observed = _status_literal_refs(scope)
    findings: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or not isinstance(node.test, ast.Compare):
            continue
        test = node.test
        if len(test.ops) != 1 or not isinstance(test.ops[0], ast.In) or len(test.comparators) != 1:
            continue
        left_path = _path(test.left)
        if not left_path or not left_path.lower().endswith("status"):
            continue
        container = test.comparators[0]
        if not isinstance(container, (ast.Tuple, ast.List, ast.Set)):
            continue
        closed = {
            element.value.lower()
            for element in container.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
        body_text = "\n".join(ast.unparse(statement) for statement in node.body)
        if not any(marker in body_text for marker in _END_MARKERS):
            continue
        missing = sorted((set(observed) & _TERMINAL_STATES) - closed)
        if not missing:
            continue
        supporting = [ref for state in missing for ref in observed.get(state, [])[:3]]
        findings.append(
            _finding(
                officer="Mechanic",
                capability="state_lifecycle",
                severity="major",
                root_cause="terminal-state-without-end-timestamp",
                path=path,
                line_start=node.lineno,
                message="A terminal status used by the package is omitted from the end-timestamp transition.",
                evidence=(
                    f"The closure branch timestamps {sorted(closed)}, while the same package emits terminal status "
                    f"{missing}; those sessions can become terminal without ended/finished/closed time."
                ),
                supporting=(f"{path}:{node.lineno}", *supporting),
                falsifiers=(
                    "Checked that the branch actually updates an end/finished/completed/closed timestamp.",
                    "Checked that the missing status is emitted as a status value elsewhere in the same package tree.",
                    "Checked that the status is terminal rather than a transient running/pending state.",
                ),
                verification=(
                    "Centralize the terminal-state set or include every package-emitted terminal state, then prove each terminal "
                    "transition stamps the authoritative end time exactly once."
                ),
                confidence=0.94,
            )
        )
    return findings


def run_static_async_lifecycle_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        if Path(path).suffix.lower() != ".py":
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        findings.extend(_await_before_resource_claim(path, text))
        findings.extend(_terminal_state_timestamp_omission(root_path, path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[
            (
                str(finding.get("root_cause")),
                str(finding.get("path")),
                int(finding.get("line_start", 0)),
            )
        ] = finding

    return {
        "schema_version": "sergeant.static-async-lifecycle-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
