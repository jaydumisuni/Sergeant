"""Static JavaScript/TypeScript ownership checks around awaited persistence.

This officer targets one mechanism: an async action publishes newly-created
state remotely, then immediately enters a local continuation that consumes a
module-level state object which was never established before suspension.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
_EMPTY_STATE_RE = re.compile(
    r"^(?:export\s+)?(?:let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*(?:null|undefined|false)\s*;?",
    re.M,
)
_ASYNC_FUNCTION_RE = re.compile(
    r"(?:async\s+function\s+(?P<decl>[A-Za-z_$][\w$]*)\s*\([^)]*\)|"
    r"(?:const|let|var)\s+(?P<arrow>[A-Za-z_$][\w$]*)\s*=\s*async\s*\([^)]*\)\s*=>)\s*\{",
    re.M,
)
_PLAIN_FUNCTION_RE = re.compile(
    r"function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{",
    re.M,
)
_PERSIST_AWAIT_RE = re.compile(
    r"\bawait\s+(?P<callee>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(",
    re.M,
)
_PERSIST_NAME_RE = re.compile(
    r"(?:set|save|store|write|persist|commit|update|add|put|create|publish)",
    re.I,
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


def _matching(text: str, opening: int, open_char: str, close_char: str) -> int | None:
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
        if char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _functions(text: str, pattern: re.Pattern[str]) -> dict[str, tuple[str, int]]:
    functions: dict[str, tuple[str, int]] = {}
    for match in pattern.finditer(text):
        name = (
            match.groupdict().get("decl")
            or match.groupdict().get("arrow")
            or match.groupdict().get("name")
        )
        if not name:
            continue
        opening = match.end() - 1
        closing = _matching(text, opening, "{", "}")
        if closing is None:
            continue
        functions[name] = (text[opening + 1 : closing], opening + 1)
    return functions


def _shared_access(body: str, name: str) -> bool:
    return bool(
        re.search(
            rf"\b{re.escape(name)}\s*(?:\?\.|\.|\[)",
            body,
        )
    )


def _assigned_before_await(before: str, name: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name)}\s*=", before))


def _payload_is_created(before: str, awaited_call: str) -> bool:
    local_object = re.search(
        r"\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*\{",
        before,
    )
    inline_object = "{" in awaited_call and "}" in awaited_call
    return bool(local_object or inline_object)


def _finding(
    *,
    path: str,
    declaration_line: int,
    await_line: int,
    helper_line: int,
    function_name: str,
    helper_name: str,
    shared: str,
    callee: str,
) -> dict[str, Any]:
    return {
        "source": "static-js-await-ownership-officer",
        "officer": "Mechanic",
        "capability": "concurrency",
        "category": "concurrency",
        "severity": "major",
        "root_cause": "local-state-not-established-before-await",
        "path": path,
        "line_start": await_line,
        "line_end": await_line,
        "evidence_ref": f"{path}:{await_line}",
        "supporting_evidence_refs": [
            f"{path}:{declaration_line}",
            f"{path}:{await_line}",
            f"{path}:{helper_line}",
        ],
        "message": "An async action awaits remote persistence before establishing local state required by its immediate continuation.",
        "evidence": (
            f"{function_name} publishes newly-created state through awaited {callee} at line {await_line} while "
            f"module state {shared} remains empty, then immediately calls {helper_name} at line {helper_line}; "
            f"that helper dereferences {shared}."
        ),
        "falsifiers_checked": [
            "Checked that the consumed state is declared at module scope with an empty initial value.",
            "Checked for assignment of that same state before the awaited persistence call.",
            "Checked that the awaited operation carries newly-created object state, either inline or through a local object.",
            "Checked that the immediate continuation helper dereferences the same state, including optional chaining.",
        ],
        "verification_test": (
            "Commit the local state before the remote await, roll it back on persistence failure if required, "
            "and prove the immediate continuation always receives the new identity."
        ),
        "confidence": 0.96,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_js_await_ownership_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
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
        declarations = {
            match.group("name"): _line(text, match.start())
            for match in _EMPTY_STATE_RE.finditer(text)
        }
        if not declarations:
            continue
        async_functions = _functions(text, _ASYNC_FUNCTION_RE)
        helpers = _functions(text, _PLAIN_FUNCTION_RE)

        for function_name, (body, body_offset) in async_functions.items():
            for awaited in _PERSIST_AWAIT_RE.finditer(body):
                callee = awaited.group("callee")
                if not _PERSIST_NAME_RE.search(callee):
                    continue
                opening = awaited.end() - 1
                closing = _matching(body, opening, "(", ")")
                if closing is None:
                    continue
                before = body[: awaited.start()]
                awaited_call = body[awaited.start() : closing + 1]
                continuation = body[closing + 1 : closing + 501]
                if not _payload_is_created(before, awaited_call):
                    continue

                for helper_name, (helper_body, _) in helpers.items():
                    helper_call = re.search(
                        rf"^[\s;]*(?:void\s+)?{re.escape(helper_name)}\s*\(",
                        continuation,
                    )
                    if helper_call is None:
                        continue
                    for shared, declaration_line in sorted(declarations.items()):
                        if _assigned_before_await(before, shared):
                            continue
                        if not _shared_access(helper_body, shared):
                            continue
                        await_line = _line(text, body_offset + awaited.start())
                        helper_line = _line(
                            text,
                            body_offset + closing + 1 + helper_call.start(),
                        )
                        findings.append(
                            _finding(
                                path=path,
                                declaration_line=declaration_line,
                                await_line=await_line,
                                helper_line=helper_line,
                                function_name=function_name,
                                helper_name=helper_name,
                                shared=shared,
                                callee=callee,
                            )
                        )

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
        "schema_version": "sergeant.static-js-await-ownership-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
