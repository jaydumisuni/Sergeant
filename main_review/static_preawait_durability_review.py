"""Static review for state that must be durable before slow awaited work."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Iterable, Iterator

_PYTHON_SUFFIXES = {".py", ".pyi"}
_SLOW_CALL_TOKENS = (
    "reply",
    "process",
    "interpret",
    "analy",
    "extract",
    "generate",
    "request",
    "invoke",
    "call",
    "translate",
    "synth",
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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _is_state_transition(node: ast.AST) -> bool:
    targets: list[ast.AST] = []
    if isinstance(node, ast.Assign):
        targets.extend(node.targets)
    elif isinstance(node, ast.AnnAssign):
        targets.append(node.target)
    elif isinstance(node, ast.AugAssign):
        targets.append(node.target)
    else:
        return False

    for target in targets:
        if not isinstance(target, ast.Subscript):
            continue
        if not isinstance(target.value, ast.Name) or target.value.id != "state":
            continue
        if isinstance(target.slice, ast.Constant) and target.slice.value == "state":
            return True
    return False


def _contains_state_save(node: ast.AST) -> ast.Call | None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        if not _call_name(child.func).endswith("._save_state"):
            continue
        if any(isinstance(arg, ast.Name) and arg.id == "state" for arg in child.args):
            return child
    return None


def _slow_await(node: ast.AST) -> ast.Await | None:
    for child in ast.walk(node):
        if not isinstance(child, ast.Await) or not isinstance(child.value, ast.Call):
            continue
        name = _call_name(child.value.func).lower()
        if any(token in name for token in _SLOW_CALL_TOKENS):
            return child
    return None


def _nested_blocks(statement: ast.stmt) -> Iterator[list[ast.stmt]]:
    if isinstance(statement, (ast.If, ast.For, ast.AsyncFor, ast.While)):
        yield statement.body
        yield statement.orelse
    elif isinstance(statement, (ast.With, ast.AsyncWith)):
        yield statement.body
    elif isinstance(statement, ast.Try):
        yield statement.body
        yield statement.orelse
        yield statement.finalbody
        for handler in statement.handlers:
            yield handler.body
    elif hasattr(ast, "TryStar") and isinstance(statement, ast.TryStar):  # type: ignore[attr-defined]
        yield statement.body
        yield statement.orelse
        yield statement.finalbody
        for handler in statement.handlers:
            yield handler.body
    elif isinstance(statement, ast.Match):
        for case in statement.cases:
            yield case.body


def _block_findings(path: str, statements: list[ast.stmt]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, statement in enumerate(statements):
        transition: ast.AST | None = None
        for child in ast.walk(statement):
            if _is_state_transition(child):
                transition = child
                break

        if transition is not None:
            first_slow: ast.Await | None = None
            first_save: ast.Call | None = None
            for following in statements[index + 1 :]:
                save = _contains_state_save(following)
                slow = _slow_await(following)
                candidates = [item for item in (save, slow) if item is not None]
                if not candidates:
                    continue
                earliest = min(candidates, key=lambda item: (item.lineno, item.col_offset))
                if isinstance(earliest, ast.Call):
                    first_save = earliest
                else:
                    first_slow = earliest
                break

            if first_slow is not None:
                for following in statements[index + 1 :]:
                    save = _contains_state_save(following)
                    if save is not None and save.lineno > first_slow.lineno:
                        first_save = save
                        break

                if first_save is not None:
                    line = int(getattr(transition, "lineno", statement.lineno))
                    findings.append(
                        {
                            "source": "static-preawait-durability-officer",
                            "officer": "Mechanic",
                            "capability": "state_lifecycle",
                            "category": "state_lifecycle",
                            "severity": "major",
                            "root_cause": "routing-state-not-persisted-before-slow-await",
                            "path": path,
                            "line_start": line,
                            "line_end": line,
                            "evidence_ref": f"{path}:{line}",
                            "supporting_evidence_refs": [
                                f"{path}:{line}",
                                f"{path}:{first_slow.lineno}",
                                f"{path}:{first_save.lineno}",
                            ],
                            "message": "Required routing state is mutated in memory but first persisted only after slow awaited work.",
                            "evidence": (
                                f"The state transition at line {line} precedes a timeout-prone await at line {first_slow.lineno}; "
                                f"the first durable save of the same state occurs only at line {first_save.lineno}. "
                                "Timeout or cancellation can therefore erase the routing context needed by the next turn."
                            ),
                            "falsifiers_checked": [
                                "Checked for `_save_state(..., state)` before the first slow await in the same control-flow block.",
                                "Checked that a later save exists, proving the transition is intended to become durable.",
                                "Restricted slow-await evidence to interpretation, request, generation, extraction, translation, synthesis, processing, or reply calls.",
                            ],
                            "verification_test": (
                                "Persist the minimal routing state and compact follow-up context before entering timeout-prone work, then prove a timed-out first turn leaves the next turn on the intended recovery route."
                            ),
                            "confidence": 0.97,
                            "direct_evidence": True,
                            "admission_hint": "actionable",
                        }
                    )

        for nested in _nested_blocks(statement):
            findings.extend(_block_findings(path, nested))

    return findings


def run_static_preawait_durability_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []
    parse_errors: list[dict[str, str]] = []

    for path in changed:
        if Path(path).suffix.lower() not in _PYTHON_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        try:
            tree = ast.parse(text, filename=path)
        except SyntaxError as error:
            parse_errors.append({"path": path, "error": str(error)})
            continue

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.extend(_block_findings(path, node.body))
            elif isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        findings.extend(_block_findings(path, member.body))

    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding["root_cause"]), str(finding["path"]))] = finding

    return {
        "schema_version": "sergeant.static-preawait-durability-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "parse_errors": parse_errors,
        "executed_project_code": False,
    }
