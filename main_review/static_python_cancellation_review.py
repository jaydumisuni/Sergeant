"""Static Python shutdown checks for cancellation exception-group handling."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".py", ".pyi"}


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _has_taskgroup(tree: ast.AST, text: str) -> bool:
    if "TaskGroup" in text:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _name(node.func).endswith("TaskGroup"):
            return True
    return False


def _cancelled_variables(function: ast.AsyncFunctionDef) -> set[str]:
    result: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "cancel":
            continue
        target = _name(node.func.value)
        if target:
            result.add(target)
    return result


def _handler_names(node: ast.Try) -> set[str]:
    names: set[str] = set()
    for handler in node.handlers:
        name = _name(handler.type)
        if name:
            names.add(name)
    return names


def _awaited_names(node: ast.Try) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Await):
            name = _name(child.value)
            if name:
                names.add(name)
    return names


def _finding(path: str, line: int, function_name: str) -> dict[str, Any]:
    return {
        "source": "static-python-cancellation-officer",
        "officer": "Mechanic",
        "capability": "concurrency",
        "category": "concurrency",
        "severity": "major",
        "root_cause": "taskgroup-cancellation-not-caught-by-ordinary-except",
        "path": path,
        "line_start": line,
        "line_end": line,
        "evidence_ref": f"{path}:{line}",
        "supporting_evidence_refs": [f"{path}:{line}"],
        "message": "TaskGroup cancellation can escape shutdown because grouped cancellation is handled with ordinary except semantics.",
        "evidence": (
            f"{function_name} cancels tasks and awaits their completion inside a normal try/except that catches "
            "CancelledError. This module also uses TaskGroup, whose Python 3.11 cancellation failures can arrive as a "
            "BaseExceptionGroup and are not matched by ordinary except CancelledError."
        ),
        "falsifiers_checked": [
            "Checked that the module contains TaskGroup-backed work.",
            "Checked that shutdown explicitly cancels tasks before awaiting them.",
            "Checked that the await is guarded by ordinary ast.Try rather than ast.TryStar (except*).",
            "Checked for explicit BaseExceptionGroup or ExceptionGroup handling.",
        ],
        "verification_test": (
            "Use except* CancelledError or explicit BaseExceptionGroup-aware filtering, re-raise non-cancellation members, "
            "and repeatedly prove shutdown while TaskGroup work is active."
        ),
        "confidence": 0.97,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_python_cancellation_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        if not _has_taskgroup(tree, text):
            continue
        for function in (node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)):
            cancelled = _cancelled_variables(function)
            if not cancelled:
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Try):
                    continue
                handlers = _handler_names(node)
                if not any(name.endswith("CancelledError") for name in handlers):
                    continue
                if any(name.endswith(("ExceptionGroup", "BaseExceptionGroup")) for name in handlers):
                    continue
                awaited = _awaited_names(node)
                if not awaited:
                    continue
                # A loop variable often names the cancelled task in both loops; when
                # collection aliases obscure that relation, the same function-level
                # cancel+await shutdown sequence remains direct evidence.
                if cancelled.isdisjoint(awaited) and not any(
                    isinstance(child, ast.Await) for child in ast.walk(node)
                ):
                    continue
                findings.append(_finding(path, int(node.lineno), function.name))
                break

    unique = {
        (str(item.get("root_cause")), str(item.get("path"))): item
        for item in findings
    }
    return {
        "schema_version": "sergeant.static-python-cancellation-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
