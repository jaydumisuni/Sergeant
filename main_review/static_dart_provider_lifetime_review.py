"""Static Riverpod provider lifetime checks across async gaps."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_PROVIDER_CLASS_RE = re.compile(
    r"@(?:Riverpod(?:\([^)]*\))?|riverpod)\s+[\s\S]{0,320}?"
    r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+extends\s+_\$[A-Za-z_][A-Za-z0-9_]*\s*\{",
    re.I | re.M,
)
_ASYNC_METHOD_RE = re.compile(
    r"\bFuture[^\n{;=]*?\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*async\s*\{",
    re.M,
)
_AWAIT_STATEMENT_RE = re.compile(r"\bawait\b[\s\S]{0,1200}?;", re.M)
_DIRECT_LIFECYCLE_RE = re.compile(
    r"\bstate\s*=|\bref\s*\.\s*(?:read|watch|invalidate|invalidateSelf|keepAlive)\s*\(",
    re.M,
)
_MOUNTED_GUARD_RE = re.compile(
    r"if\s*\(\s*!\s*ref\.mounted[^)]*\)\s*(?:return\b|throw\b|\{)",
    re.I | re.M,
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
        if char in {"'", '"'}:
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


def _methods(class_body: str, class_offset: int) -> dict[str, tuple[str, int]]:
    rows: dict[str, tuple[str, int]] = {}
    for match in _ASYNC_METHOD_RE.finditer(class_body):
        opening = match.end() - 1
        closing = _matching_brace(class_body, opening)
        if closing is None:
            continue
        rows[match.group("name")] = (
            class_body[opening + 1 : closing],
            class_offset + opening + 1,
        )
    return rows


def _touches(body: str, lifecycle_helpers: set[str], method_name: str) -> list[tuple[int, str]]:
    touches: list[tuple[int, str]] = [
        (match.start(), match.group(0).strip())
        for match in _DIRECT_LIFECYCLE_RE.finditer(body)
    ]
    for helper in sorted(lifecycle_helpers):
        if helper == method_name:
            continue
        for match in re.finditer(rf"\b{re.escape(helper)}\s*\(", body):
            touches.append((match.start(), f"lifecycle helper {helper}"))
    return sorted(touches)


def _finding(
    *,
    path: str,
    class_name: str,
    method_name: str,
    await_line: int,
    touch_line: int,
    touch_label: str,
) -> dict[str, Any]:
    return {
        "source": "static-dart-provider-lifetime-officer",
        "officer": "Mechanic",
        "capability": "state_lifecycle",
        "category": "state_lifecycle",
        "severity": "major",
        "root_cause": "disposed-provider-ref-after-await",
        "path": path,
        "line_start": await_line,
        "line_end": await_line,
        "evidence_ref": f"{path}:{await_line}",
        "supporting_evidence_refs": [f"{path}:{await_line}", f"{path}:{touch_line}"],
        "message": "A Riverpod notifier touches lifecycle-bound state after an async gap without proving it is still mounted.",
        "evidence": (
            f"{class_name}.{method_name} resumes after awaited work at line {await_line} and reaches {touch_label} "
            f"at line {touch_line}. The notifier can be invalidated or disposed while suspended."
        ),
        "falsifiers_checked": [
            "Checked that the method belongs to a @riverpod or @Riverpod generated notifier class.",
            "Checked that the lifecycle touch occurs after a completed await statement rather than inside the awaited expression.",
            "Checked direct state/ref access and calls to same-class helpers that themselves touch state/ref.",
            "Checked for a ref.mounted fail-fast guard between the async gap and the lifecycle touch.",
        ],
        "verification_test": (
            "Guard every resumed state/ref operation with ref.mounted, or capture lifecycle-independent dependencies before awaiting, "
            "then prove notifier disposal during the operation cannot throw or publish state."
        ),
        "confidence": 0.98,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for provider_class in _PROVIDER_CLASS_RE.finditer(text):
        class_opening = provider_class.end() - 1
        class_closing = _matching_brace(text, class_opening)
        if class_closing is None:
            continue
        class_body = text[class_opening + 1 : class_closing]
        class_offset = class_opening + 1
        methods = _methods(class_body, class_offset)
        lifecycle_helpers = {
            name
            for name, (body, _) in methods.items()
            if re.search(r"\bref\s*\.|\bstate\s*(?:=|\.)", body)
        }

        for method_name, (body, body_offset) in methods.items():
            awaits = list(_AWAIT_STATEMENT_RE.finditer(body))
            if not awaits:
                continue
            for touch_offset, touch_label in _touches(body, lifecycle_helpers, method_name):
                previous = [item for item in awaits if item.end() <= touch_offset]
                if not previous:
                    continue
                awaited = previous[-1]
                between = body[awaited.end() : touch_offset]
                if _MOUNTED_GUARD_RE.search(between):
                    continue
                await_line = _line(text, body_offset + awaited.start())
                touch_line = _line(text, body_offset + touch_offset)
                findings.append(
                    _finding(
                        path=path,
                        class_name=provider_class.group("name"),
                        method_name=method_name,
                        await_line=await_line,
                        touch_line=touch_line,
                        touch_label=touch_label,
                    )
                )
                break
    return findings


def run_static_dart_provider_lifetime_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    readable: list[str] = []
    for path in changed:
        if Path(path).suffix.lower() != ".dart":
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        findings.extend(_findings(path, text))
    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding["root_cause"]), str(finding["path"]), int(finding["line_start"]))] = finding
    return {
        "schema_version": "sergeant.static-dart-provider-lifetime-review.v2",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
