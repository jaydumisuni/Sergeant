"""Static React component lifetime checks for async state publication."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
_STATE_DECL_RE = re.compile(
    r"const\s*\[[^,\]]+,\s*(?P<setter>set[A-Z][A-Za-z0-9_$]*)\s*\]\s*=\s*useState(?:<[^;=()]*>)?\s*\(",
    re.M,
)
_ASYNC_CALLBACK_RE = re.compile(
    r"(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:(?:useCallback|useMemo)\s*\(\s*)?async\s*\([^)]*\)\s*(?::\s*[^=]+)?=>\s*\{",
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


def _guarded(before_write: str) -> bool:
    mounted_return = re.search(
        r"if\s*\(\s*!\s*[A-Za-z_$][\w$]*(?:Mounted|Active|Alive)[A-Za-z0-9_$]*\.current\s*\)\s*(?:\{\s*)?return\b",
        before_write,
        re.I,
    )
    cancellation_return = re.search(
        r"if\s*\(\s*(?:[A-Za-z_$][\w$]*\.signal\.)?(?:aborted|cancelled|canceled)\s*\)\s*(?:\{\s*)?return\b",
        before_write,
        re.I,
    )
    positive_guard = re.search(
        r"if\s*\(\s*[A-Za-z_$][\w$]*(?:Mounted|Active|Alive)[A-Za-z0-9_$]*\.current\s*\)\s*\{[^{}]*$",
        before_write,
        re.I | re.S,
    )
    return mounted_return is not None or cancellation_return is not None or positive_guard is not None


def _finding(path: str, function_name: str, await_line: int, write_line: int, setter: str) -> dict[str, Any]:
    return {
        "source": "static-component-async-officer",
        "officer": "Mechanic",
        "capability": "state_lifecycle",
        "category": "state_lifecycle",
        "severity": "major",
        "root_cause": "component-async-publication-after-unmount",
        "path": path,
        "line_start": await_line,
        "line_end": await_line,
        "evidence_ref": f"{path}:{await_line}",
        "supporting_evidence_refs": [f"{path}:{await_line}", f"{path}:{write_line}"],
        "message": "An async component action can publish React state after the component lifetime has ended.",
        "evidence": (
            f"{function_name} suspends at line {await_line} and later calls the component state setter {setter} "
            f"at line {write_line}. No mounted/active or cancellation guard proves the component still owns that publication."
        ),
        "falsifiers_checked": [
            "Checked that the setter is declared by useState in the same file.",
            "Checked that the state publication occurs after an async suspension.",
            "Checked for an isMounted/isActive/isAlive ref guard before the post-await write.",
            "Checked for an aborted/cancelled guard before the post-await write.",
        ],
        "verification_test": (
            "Abort in-flight work during cleanup and guard every success, error and finally state publication with a live component "
            "ownership check; prove unmount during the request cannot update state."
        ),
        "confidence": 0.96,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_component_async_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
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
        setters = {match.group("setter") for match in _STATE_DECL_RE.finditer(text)}
        if not setters:
            continue
        setter_pattern = "|".join(re.escape(item) for item in sorted(setters, key=len, reverse=True))
        for match in _ASYNC_CALLBACK_RE.finditer(text):
            opening = match.end() - 1
            closing = _matching_brace(text, opening)
            if closing is None:
                continue
            body = text[opening + 1 : closing]
            await_match = re.search(r"\bawait\b", body)
            if await_match is None:
                continue
            after = body[await_match.end() :]
            write = re.search(rf"\b(?P<setter>{setter_pattern})\s*\(", after)
            if write is None:
                continue
            before_write = after[: write.start()]
            if _guarded(before_write):
                continue
            await_line = _line(text, opening + 1 + await_match.start())
            write_line = _line(text, opening + 1 + await_match.end() + write.start())
            findings.append(
                _finding(path, match.group("name"), await_line, write_line, write.group("setter"))
            )
            break

    unique = {
        (str(item.get("root_cause")), str(item.get("path"))): item
        for item in findings
    }
    return {
        "schema_version": "sergeant.static-component-async-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
