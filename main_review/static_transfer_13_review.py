"""Static checks learned from transfer set 13 after its blind score was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_GO_SUFFIXES = {".go"}
_SELECTOR_FIELDS = ("Model", "Provider", "Backend", "Profile", "Engine", "Runtime")
_SAFE_BACKGROUND_CALLS = {
    "Add",
    "Done",
    "Lock",
    "Print",
    "Printf",
    "Println",
    "RLock",
    "RUnlock",
    "Stop",
    "Unlock",
    "Wait",
}
_BUILTIN_CALLS = {
    "append",
    "cap",
    "close",
    "copy",
    "delete",
    "len",
    "make",
    "new",
    "panic",
    "recover",
}


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
        if char in {'"', "'", "`"}:
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


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    category: str,
    message: str,
    evidence: str,
    falsifiers: Iterable[str],
    verification: str,
    confidence: float = 0.97,
) -> dict[str, Any]:
    return {
        "source": "static-transfer-13-officer",
        "officer": "Mechanic" if category == "concurrency" else "Engineer",
        "capability": category,
        "category": category,
        "severity": "major",
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": [f"{path}:{line_start}"],
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _go_functions(text: str) -> dict[str, str]:
    functions: dict[str, str] = {}
    pattern = re.compile(
        r"\bfunc\s*(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*\([^)]*\)(?:\s*\([^)]*\)|\s+[^\{\n]+)?\s*\{",
        re.M,
    )
    for match in pattern.finditer(text):
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is not None:
            functions[match.group("name")] = text[opening + 1 : closing]
    return functions


def _call_names(body: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(
        r"\b(?P<call>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\(",
        body,
    ):
        call = match.group("call")
        final = call.rsplit(".", 1)[-1]
        if final in _BUILTIN_CALLS or final in _SAFE_BACKGROUND_CALLS:
            continue
        if final in {"if", "for", "select", "switch", "return", "defer", "go"}:
            continue
        names.append(call)
    return names


def _body_has_panic_bearing_work(body: str) -> bool:
    """Exclude synchronization/log-only goroutines while retaining real work calls."""
    return bool(_call_names(body))


def _goroutine_finding(path: str, line_start: int, evidence: str) -> dict[str, Any]:
    return _finding(
        root_cause="detached-goroutine-without-panic-containment",
        path=path,
        line_start=line_start,
        category="concurrency",
        message="A fire-and-forget goroutine performs panic-bearing work without containing panics.",
        evidence=evidence,
        falsifiers=(
            "Checked that the launch uses the raw `go` statement rather than a structured task group.",
            "Checked the goroutine entry/target for a recover boundary.",
            "Excluded synchronization, wait-group, timer-stop, and logging-only bookkeeping.",
        ),
        verification=(
            "Install a deferred panic boundary at the goroutine entry point, preserve cleanup and result signalling, "
            "and inject a panicking dependency to prove the process survives and callers do not hang."
        ),
    )


def _detached_goroutine_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _GO_SUFFIXES:
        return []
    findings: list[dict[str, Any]] = []
    functions = _go_functions(text)

    for match in re.finditer(r"\bgo\s+func\s*\([^)]*\)\s*\{", text, re.M):
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        if re.search(r"\brecover\s*\(", body):
            continue
        calls = _call_names(body)
        if not calls:
            continue
        findings.append(
            _goroutine_finding(
                path,
                _line(text, match.start()),
                "The detached goroutine invokes "
                + ", ".join(f"`{name}`" for name in calls[:4])
                + " without a deferred recover boundary; a panic can terminate the Go process.",
            )
        )

    direct = re.compile(
        r"\bgo\s+(?P<call>(?:[A-Za-z_][A-Za-z0-9_]*\.)*(?P<name>[A-Za-z_][A-Za-z0-9_]*))\s*\(",
        re.M,
    )
    for match in direct.finditer(text):
        if text[match.start() : match.end()].startswith("go func"):
            continue
        target = functions.get(match.group("name"))
        # Cross-file or library targets are not sufficient direct evidence. The
        # same-file target must be visible and perform real work.
        if target is None or re.search(r"\brecover\s*\(", target):
            continue
        if not _body_has_panic_bearing_work(target):
            continue
        findings.append(
            _goroutine_finding(
                path,
                _line(text, match.start()),
                f"`go {match.group('call')}(...)` detaches a same-file worker that performs real calls but has no local recover boundary.",
            )
        )

    unique: dict[int, dict[str, Any]] = {}
    for finding in findings:
        unique[int(finding["line_start"])] = finding
    return list(unique.values())


def _documented_selector_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _GO_SUFFIXES:
        return []
    findings: list[dict[str, Any]] = []
    struct_re = re.compile(
        r"\btype\s+(?P<type>[A-Za-z_][A-Za-z0-9_]*Options)\s+struct\s*\{(?P<body>[\s\S]*?)\n\}",
        re.M,
    )
    for struct in struct_re.finditer(text):
        struct_type = struct.group("type")
        before = text[max(0, struct.start() - 700) : struct.start()]
        for field in _SELECTOR_FIELDS:
            if re.search(rf"(?m)^\s*{re.escape(field)}\s+string\b", struct.group("body")) is None:
                continue
            promised_default = re.search(
                rf"(?:empty\s+`?{re.escape(field)}`?|empty\s+{re.escape(field)}|zero\s+value)"
                rf"[\s\S]{{0,220}}?(?:resolve|default)",
                before,
                re.I,
            )
            if promised_default is None:
                continue
            function_re = re.compile(
                rf"\bfunc\s*(?:\([^)]*\)\s*)?[A-Za-z_][A-Za-z0-9_]*\s*\("
                rf"(?P<params>[^)]*\b(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s+{re.escape(struct_type)}[^)]*)\)"
                r"(?:\s*\([^)]*\)|\s+[^\{\n]+)?\s*\{",
                re.M,
            )
            for function in function_re.finditer(text):
                opening = function.end() - 1
                closing = _matching_brace(text, opening)
                if closing is None:
                    continue
                body = text[opening + 1 : closing]
                variable = function.group("var")
                selector = rf"{re.escape(variable)}\.{re.escape(field)}"
                forwarded = re.search(
                    rf"\b{re.escape(field)}\s*:\s*{selector}\b|\([^)]*{selector}[^)]*\)",
                    body,
                    re.S,
                )
                if forwarded is None:
                    continue
                empty_guard = re.search(
                    rf"\bif\s+{selector}\s*==\s*\"\"|\bif\s+len\s*\(\s*{selector}\s*\)\s*==\s*0",
                    body,
                )
                resolution = re.search(
                    rf"{selector}\s*=|\b(?:resolve|default)[A-Za-z0-9_]*{re.escape(field)}\s*\(",
                    body,
                    re.I,
                )
                if empty_guard is not None and resolution is not None:
                    continue
                findings.append(
                    _finding(
                        root_cause="documented-default-selector-forwarded-without-resolution",
                        path=path,
                        line_start=_line(text, function.start()),
                        category="api_contract",
                        message="An options contract promises default selector resolution, but the operation forwards the empty selector unchanged.",
                        evidence=(
                            f"`{struct_type}.{field}` is documented as resolving when empty; this operation forwards "
                            f"`{variable}.{field}` without an empty-value guard, fallback assignment, or resolver call."
                        ),
                        falsifiers=(
                            "Checked that the options declaration explicitly promises empty/zero-value default resolution.",
                            "Checked that the operation forwards the same selector into a downstream call or options object.",
                            "Checked the operation body for an empty-value guard and fallback/resolver assignment.",
                        ),
                        verification=(
                            "Resolve one authoritative selector before constructing the runtime request, reject unresolved empty values with an actionable error, "
                            "and prove every UI, daemon, and adapter path uses the same resolved value."
                        ),
                    )
                )
    return findings


def run_static_transfer_13_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    readable: list[str] = []
    findings: list[dict[str, Any]] = []
    for path in changed:
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        findings.extend(_detached_goroutine_findings(path, text))
        findings.extend(_documented_selector_findings(path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[
            (
                str(finding.get("root_cause")),
                str(finding.get("path")),
                int(finding.get("line_start") or 0),
            )
        ] = finding
    return {
        "schema_version": "sergeant.static-transfer-13-review.v2",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
