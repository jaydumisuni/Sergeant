"""Static review for caller-controlled identifiers inserted into URL paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_GO_SUFFIXES = {".go"}
_PATH_CALL_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\.(?:get|post|put|patch|delete|request)\s*\("
    r"(?:[^,\n]+,\s*)?(?P<path>[`\"][^\n;]{0,500})",
    re.I,
)
_CONCAT_RE = re.compile(r"[+]\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b")
_ID_NAME_RE = re.compile(r"(?:^|_)(?:id|slug|key|ref|token)$|(?:ID|Id|Slug|Key|Ref|Token)$")


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


def _function_window(text: str, offset: int) -> str:
    start = text.rfind("func ", 0, offset)
    if start < 0:
        start = max(0, offset - 4000)
    return text[start : min(len(text), offset + 1000)]


def _caller_controlled(window: str, name: str) -> bool:
    escaped = re.escape(name)
    return bool(
        re.search(rf"\b{escaped}\s*,\s*err\s*:=\s*[A-Za-z_][A-Za-z0-9_]*(?:ID|Id|Slug|Key|Ref|Token)\s*\(", window)
        or re.search(rf"\b{escaped}\s*:=\s*(?:args|rest)\s*\[", window)
        or re.search(rf"func\s+(?:\([^)]*\)\s*)?[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\b{escaped}\s+string\b", window, re.S)
    )


def _encoded(window: str, name: str) -> bool:
    escaped = re.escape(name)
    return bool(
        re.search(rf"(?:url\.)?PathEscape\s*\(\s*{escaped}\s*\)", window)
        or re.search(rf"\b(?:escaped|encoded|safe)[A-Za-z0-9_]*\s*:=\s*(?:url\.)?PathEscape\s*\(\s*{escaped}\s*\)", window)
    )


def _finding(path: str, line_start: int, name: str) -> dict[str, Any]:
    return {
        "source": "static-url-path-contract-officer",
        "officer": "Engineer",
        "capability": "api_contract",
        "category": "api_contract",
        "severity": "major",
        "root_cause": "caller-controlled-path-segment-not-percent-escaped",
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": [f"{path}:{line_start}"],
        "message": "A caller-controlled identifier is concatenated into an HTTP path without percent-escaping.",
        "evidence": (
            f"`{name}` is derived from command input or a string parameter and appended directly to a slash-delimited request path. "
            "Values containing `/`, `?`, `#`, or `%` can change the addressed resource instead of remaining one path segment."
        ),
        "falsifiers_checked": [
            "Checked that the value is derived from arguments, a string parameter, or an ID/slug parser.",
            "Checked for url.PathEscape or an equivalent encoded intermediate value in the same function.",
            "Checked that the value is inserted into a path rather than through a query-value builder.",
        ],
        "verification_test": "Percent-escape the identifier as one path segment and test slash, question-mark, hash, percent, Unicode, and ordinary IDs.",
        "confidence": 0.98,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def run_static_url_path_contract_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    readable: list[str] = []
    findings: list[dict[str, Any]] = []

    for path in changed:
        if Path(path).suffix.lower() not in _GO_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        for call in _PATH_CALL_RE.finditer(text):
            for concatenated in _CONCAT_RE.finditer(call.group("path")):
                name = concatenated.group("name")
                if _ID_NAME_RE.search(name) is None:
                    continue
                window = _function_window(text, call.start())
                if not _caller_controlled(window, name) or _encoded(window, name):
                    continue
                findings.append(_finding(path, _line(text, call.start()), name))
                break

    unique = {(str(item["root_cause"]), str(item["path"])): item for item in findings}
    return {
        "schema_version": "sergeant.static-url-path-contract-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
