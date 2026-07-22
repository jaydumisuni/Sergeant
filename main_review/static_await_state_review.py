"""Static await/state invariants across Python, JavaScript, and TypeScript.

These checks model state that crosses a suspension point. They do not execute
project code and deliberately require source-grounded ordering evidence.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx"}
_LOAD_NAME_RE = re.compile(r"(?:load|read|get|fetch|snapshot|config|state|data)", re.I)
_PERSIST_NAME_RE = re.compile(r"(?:save|write|dump|persist|store|commit|update)", re.I)
_REMOTE_AWAIT_RE = re.compile(r"\bawait\s+[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\(")
_JS_FUNCTION_RE = re.compile(
    r"(?:async\s+function\s+(?P<decl>[A-Za-z_$][\w$]*)\s*\([^)]*\)|"
    r"(?:const|let|var)\s+(?P<arrow>[A-Za-z_$][\w$]*)\s*=\s*async\s*\([^)]*\)\s*=>)\s*\{",
    re.M,
)
_PLAIN_FUNCTION_RE = re.compile(r"function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{", re.M)
_MODULE_NULL_RE = re.compile(
    r"^(?:export\s+)?(?:let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:null|undefined|false)\s*;?",
    re.M,
)


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(text: str, offset: int) -> int:
    return text[: max(0, offset)].count("\n") + 1


def _finding(
    *,
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
        "source": "static-await-state-officer",
        "officer": "Mechanic",
        "capability": "concurrency",
        "category": "concurrency",
        "severity": "major",
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


def _call_name(node: ast.AST | None) -> str:
    if not isinstance(node, ast.Call):
        return ""
    target = node.func
    parts: list[str] = []
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
    return ".".join(reversed(parts))


def _assigned_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    return None


def _root_name(node: ast.AST) -> str | None:
    current = node
    while isinstance(current, (ast.Attribute, ast.Subscript)):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def _contains_name(node: ast.AST, name: str) -> bool:
    return any(isinstance(item, ast.Name) and item.id == name for item in ast.walk(node))


def _python_stale_snapshot_after_await(path: str, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    findings: list[dict[str, Any]] = []
    for function in ast.walk(tree):
        if not isinstance(function, ast.AsyncFunctionDef):
            continue
        awaits = sorted(node.lineno for node in ast.walk(function) if isinstance(node, ast.Await))
        if not awaits:
            continue
        first_await = awaits[0]

        snapshots: list[tuple[str, int]] = []
        assignments: list[tuple[str, int, ast.AST | None]] = []
        mutations: dict[str, list[int]] = {}
        sinks: dict[str, list[int]] = {}

        for node in ast.walk(function):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    plain = _assigned_name(target)
                    if plain:
                        assignments.append((plain, node.lineno, value))
                        call = _call_name(value)
                        if node.lineno < first_await and call and _LOAD_NAME_RE.search(call):
                            snapshots.append((plain, node.lineno))
                    root = _root_name(target)
                    if root and not isinstance(target, ast.Name) and node.lineno > first_await:
                        mutations.setdefault(root, []).append(node.lineno)
            elif isinstance(node, ast.Call):
                name = _call_name(node)
                if not name or not _PERSIST_NAME_RE.search(name):
                    continue
                for snapshot_name, _ in snapshots:
                    if _contains_name(node, snapshot_name):
                        sinks.setdefault(snapshot_name, []).append(node.lineno)

        for snapshot_name, load_line in snapshots:
            mutation_lines = sorted(mutations.get(snapshot_name, []))
            sink_lines = sorted(sinks.get(snapshot_name, []))
            if not mutation_lines or not sink_lines:
                continue
            mutation_line = mutation_lines[0]
            later_sinks = [line for line in sink_lines if line >= mutation_line]
            if not later_sinks:
                continue
            sink_line = later_sinks[0]
            refreshed = False
            for assigned, line, value in assignments:
                if assigned != snapshot_name or not (first_await < line <= sink_line):
                    continue
                call = _call_name(value)
                if call and _LOAD_NAME_RE.search(call):
                    refreshed = True
                    break
            if refreshed:
                continue
            findings.append(
                _finding(
                    root_cause="stale-snapshot-persisted-after-await",
                    path=path,
                    line_start=load_line,
                    message="A mutable snapshot is loaded before an await and persisted afterward without being refreshed.",
                    evidence=(
                        f"{function.name} loads {snapshot_name} at line {load_line}, suspends at line {first_await}, "
                        f"mutates the same snapshot at line {mutation_line}, and persists it at line {sink_line}. "
                        "Concurrent writers can be overwritten by the stale whole-state copy."
                    ),
                    supporting=(
                        f"{path}:{load_line}",
                        f"{path}:{first_await}",
                        f"{path}:{mutation_line}",
                        f"{path}:{sink_line}",
                    ),
                    falsifiers=(
                        "Checked for a fresh reload of the same snapshot after the await and before persistence.",
                        "Checked that the post-await write mutates and persists the pre-await object rather than an unrelated local value.",
                        "Checked that an actual persistence-style call receives the stale object.",
                    ),
                    verification="Reload or compare-and-merge authoritative state after the await, then prove a concurrent update survives the write-back.",
                    confidence=0.97,
                )
            )
    return findings


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _functions(text: str, pattern: re.Pattern[str]) -> dict[str, tuple[str, int]]:
    functions: dict[str, tuple[str, int]] = {}
    for match in pattern.finditer(text):
        name = match.groupdict().get("decl") or match.groupdict().get("arrow") or match.groupdict().get("name")
        if not name:
            continue
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        functions[name] = (text[opening + 1 : closing], opening + 1)
    return functions


def _js_shared_reset_across_await(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for function_name, (body, body_offset) in _functions(text, _JS_FUNCTION_RE).items():
        await_match = _REMOTE_AWAIT_RE.search(body)
        if await_match is None:
            continue
        before = body[: await_match.start()]
        after = body[await_match.end() :]
        for reset in re.finditer(
            r"(?P<target>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)+)\s*=\s*(?:\[\s*\]|\{\s*\})\s*;?",
            before,
        ):
            target = reset.group("target")
            root = target.split(".", 1)[0]
            if re.search(rf"\b(?:const|let|var)\s+{re.escape(root)}\b", before):
                continue
            mutation = re.search(
                rf"(?:{re.escape(target)}\s*=\s*\[[\s\S]{{0,260}}{re.escape(target)}|"
                rf"{re.escape(target)}\s*\.\s*(?:push|add|set)\s*\()",
                after,
            )
            if mutation is None:
                continue
            reset_line = _line(text, body_offset + reset.start())
            await_line = _line(text, body_offset + await_match.start())
            mutation_line = _line(text, body_offset + await_match.end() + mutation.start())
            findings.append(
                _finding(
                    root_cause="shared-state-reset-before-await-mutation",
                    path=path,
                    line_start=reset_line,
                    message="A re-entrant async operation resets shared state before awaiting and mutates it after resumption.",
                    evidence=(
                        f"{function_name} clears {target} at line {reset_line}, suspends at line {await_line}, and mutates "
                        f"the same shared target at line {mutation_line}. Overlapping calls can erase or duplicate each other's results."
                    ),
                    supporting=(f"{path}:{reset_line}", f"{path}:{await_line}", f"{path}:{mutation_line}"),
                    falsifiers=(
                        "Checked that the target root is not declared locally inside the async function.",
                        "Checked that the same shared target is mutated after the await.",
                        "Checked that the reset is not deferred until after the suspension point.",
                    ),
                    verification="Use call-local accumulation plus atomic replacement/deduplication, or serialize overlapping loads, and prove concurrent invocations cannot erase or duplicate state.",
                    confidence=0.96,
                )
            )
    return findings


def _js_uncommitted_local_state_before_await(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    async_functions = _functions(text, _JS_FUNCTION_RE)
    helpers = _functions(text, _PLAIN_FUNCTION_RE)
    shared_names = {match.group("name") for match in _MODULE_NULL_RE.finditer(text)}
    if not shared_names:
        return findings

    for function_name, (body, body_offset) in async_functions.items():
        await_match = _REMOTE_AWAIT_RE.search(body)
        if await_match is None:
            continue
        before = body[: await_match.start()]
        after = body[await_match.end() :]
        for helper_name, (helper_body, _) in helpers.items():
            helper_call = re.search(rf"\b{re.escape(helper_name)}\s*\(", after)
            if helper_call is None:
                continue
            for shared in sorted(shared_names):
                if not re.search(rf"\b{re.escape(shared)}\s*(?:\.|\[)", helper_body):
                    continue
                if re.search(rf"\b{re.escape(shared)}\s*=", before):
                    continue
                if not re.search(r"\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*\{", before):
                    continue
                await_line = _line(text, body_offset + await_match.start())
                helper_line = _line(text, body_offset + await_match.end() + helper_call.start())
                declaration = next(
                    (match for match in _MODULE_NULL_RE.finditer(text) if match.group("name") == shared),
                    None,
                )
                declaration_line = _line(text, declaration.start()) if declaration is not None else 1
                findings.append(
                    _finding(
                        root_cause="local-state-not-established-before-await",
                        path=path,
                        line_start=await_line,
                        message="An async action awaits remote persistence before establishing local state required by its immediate continuation.",
                        evidence=(
                            f"{function_name} suspends at line {await_line} while shared {shared} is still in its empty initial state; "
                            f"it then calls {helper_name} at line {helper_line}, and that helper dereferences {shared}."
                        ),
                        supporting=(
                            f"{path}:{declaration_line}",
                            f"{path}:{await_line}",
                            f"{path}:{helper_line}",
                        ),
                        falsifiers=(
                            "Checked for assignment of the consumed shared state before the await.",
                            "Checked that the immediate continuation actually dereferences the shared state.",
                            "Checked that the shared state begins empty and is not a call-local variable.",
                        ),
                        verification="Commit the local ownership/state before the remote await, roll it back on failure if required, and prove the immediate continuation always sees the new identity.",
                        confidence=0.94,
                    )
                )
    return findings


def run_static_await_state_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        suffix = Path(path).suffix.lower()
        if suffix not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        if suffix == ".py":
            findings.extend(_python_stale_snapshot_after_await(path, text))
        else:
            findings.extend(_js_shared_reset_across_await(path, text))
            findings.extend(_js_uncommitted_local_state_before_await(path, text))

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
        "schema_version": "sergeant.static-await-state-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
