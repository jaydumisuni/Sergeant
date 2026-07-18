"""Static Riverpod provider lifetime checks across async gaps."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_BUILD_RE = re.compile(r"\bFuture[^\n{]*\bbuild\s*\([^)]*\)\s*async\s*\{", re.M)


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


def _findings(path: str, text: str) -> list[dict[str, Any]]:
    if "@riverpod" not in text:
        return []
    findings: list[dict[str, Any]] = []
    for build in _BUILD_RE.finditer(text):
        opening = build.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        await_match = re.search(r"\bawait\b", body)
        if await_match is None:
            continue
        after = body[await_match.end() :]
        ref_use = re.search(r"\bref\s*\.\s*(?:read|watch|invalidate|invalidateSelf|keepAlive)\s*\(", after)
        if ref_use is None:
            continue
        between = after[: ref_use.start()]
        if re.search(r"if\s*\(\s*!?\s*ref\.mounted\s*\)", between):
            continue
        await_line = _line(text, opening + 1 + await_match.start())
        ref_line = _line(text, opening + 1 + await_match.end() + ref_use.start())
        findings.append(
            {
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
                "supporting_evidence_refs": [f"{path}:{await_line}", f"{path}:{ref_line}"],
                "message": "An auto-dispose provider touches its lifecycle-bound ref after an async gap without proving it is still mounted.",
                "evidence": (
                    f"The Riverpod build method suspends at line {await_line} and accesses ref again at line {ref_line}. "
                    "The provider may be disposed while suspended."
                ),
                "falsifiers_checked": [
                    "Checked that the method belongs to an @riverpod provider build.",
                    "Checked that ref access occurs after the first await.",
                    "Checked for a ref.mounted guard before the resumed ref access.",
                ],
                "verification_test": "Capture required ref-backed dependencies before awaiting, or guard resumed lifecycle operations with ref.mounted.",
                "confidence": 0.98,
                "direct_evidence": True,
                "admission_hint": "actionable",
            }
        )
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
        "schema_version": "sergeant.static-dart-provider-lifetime-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
