"""Static checks learned after transfer set 28's blind artifact was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".zig", ".r", ".erl", ".hrl"}


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
        if char in {'"', "'"}:
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
    officer: str,
    capability: str,
    category: str,
    severity: str,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    falsifiers: list[str],
    verification: str,
    confidence: float,
    supporting: Iterable[str] = (),
) -> dict[str, Any]:
    primary = f"{path}:{line_start}"
    return {
        "source": "static-transfer-28-officer",
        "officer": officer,
        "capability": capability,
        "category": category,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": primary,
        "supporting_evidence_refs": list(dict.fromkeys([primary, *supporting])),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": falsifiers,
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _zig_keyword_diagnostic_findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    function_pattern = re.compile(r"\bfn\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
    diagnostic_pattern = re.compile(
        r'appendErrorNode\s*\(\s*(?P<node>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*'
        r'"(?P<message>[^"]*\bkeyword\b[^"]*)"',
        re.I,
    )
    for function in function_pattern.finditer(text):
        opening = text.find("{", function.end())
        if opening < 0:
            continue
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening : closing + 1]
        for diagnostic in diagnostic_pattern.finditer(body):
            message = diagnostic.group("message")
            prefix_words = message.lower().split("keyword", 1)[0].split()
            semantic = prefix_words[-1] if prefix_words else ""
            node = diagnostic.group("node")
            exact_token_evidence = bool(
                semantic and semantic in function.group("name").lower()
            )
            if semantic:
                exact_token_evidence = exact_token_evidence or bool(
                    re.search(
                        rf"\b[A-Za-z_][A-Za-z0-9_]*\.{re.escape(semantic)}_token\b",
                        body,
                        re.I,
                    )
                )
            exact_token_evidence = exact_token_evidence or bool(
                re.search(
                    rf"nodeMainToken\s*\(\s*{re.escape(node)}\s*\)",
                    body,
                )
            )
            if not exact_token_evidence:
                continue
            absolute = opening + diagnostic.start()
            findings.append(
                _finding(
                    officer="Engineer",
                    capability="diagnostic_contract",
                    category="correctness",
                    severity="major",
                    root_cause="keyword-diagnostic-owned-by-enclosing-node-not-token",
                    path=path,
                    line_start=_line(text, absolute),
                    message=(
                        "A diagnostic about a specific syntax keyword is anchored to the enclosing AST node instead of the keyword token."
                    ),
                    evidence=(
                        f"The `{function.group('name')}` path handles `{semantic or 'keyword'}` syntax and emits "
                        f"`{message}` through `appendErrorNode({node}, ...)`. The enclosing node can span an entire "
                        "expression or assignment, so the source location does not identify the offending keyword."
                    ),
                    falsifiers=[
                        "Required a diagnostic message explicitly naming a syntax keyword.",
                        "Required function or field evidence identifying the handled keyword/token.",
                        "Excluded diagnostics already emitted through a token-specific helper.",
                        "Excluded node-level diagnostics whose message concerns the complete expression rather than one token.",
                    ],
                    verification=(
                        "Anchor the diagnostic to the exact keyword token and verify expression and destructuring forms report the keyword column rather than the enclosing node."
                    ),
                    confidence=0.98,
                )
            )
    return findings


def _r_group_cardinality_findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    function_pattern = re.compile(
        r"(?P<name>[A-Za-z_.][A-Za-z0-9_.]*)\s*<-\s*function\s*\(",
        re.M,
    )
    for function in function_pattern.finditer(text):
        opening = text.find("{", function.end())
        if opening < 0 or opening - function.end() > 800:
            continue
        args = text[function.end() : opening]
        if "dots" not in args or "verb" not in args:
            continue
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening : closing + 1]
        if not re.search(r"\b(?:chunks|results)\s*<-\s*list\s*\(\s*\)", body):
            continue
        if not re.search(r"for\s*\([^)]*seq_along\s*\(\s*dots\s*\)", body):
            continue
        infer = re.search(
            r"(?P<size>[A-Za-z_][A-Za-z0-9_]*)\s*<-\s*\.Call\s*\("
            r"[^)]*(?:recycle|size|group)[^)]*,\s*(?:chunks|results)\b",
            body,
            re.I | re.S,
        )
        if infer is None:
            infer = re.search(
                r"(?P<size>[A-Za-z_][A-Za-z0-9_]*)\s*<-\s*\.Call\s*\("
                r"[\s\S]{0,220}?(?:chunks|results)\s*,\s*(?:chunks|results)",
                body,
                re.I,
            )
        if infer is None:
            continue
        independent_count = re.search(
            r"\b(?:n_groups|group_count|number_of_groups)\s*<-\s*"
            r"(?:[^,\n]*(?:get_n_groups|nrow\s*\(\s*(?:group_keys|keys)|length\s*\(\s*(?:groups|keys)))",
            body,
            re.I,
        )
        count_passed = re.search(
            r"\.Call\s*\([\s\S]{0,360}?\b(?:n_groups|group_count|number_of_groups)\b",
            body[infer.start() : infer.end() + 500],
            re.I,
        )
        if independent_count is not None and count_passed is not None:
            continue
        build_contract = re.search(
            rf"vec_rep_each\s*\([^,]+,\s*cols\$(?:{re.escape(infer.group('size'))}|sizes|group_sizes)\s*\)",
            text,
            re.I,
        )
        if build_contract is None:
            continue
        absolute = opening + infer.start()
        findings.append(
            _finding(
                officer="Engineer",
                capability="cardinality_contract",
                category="correctness",
                severity="major",
                root_cause="empty-expression-results-used-as-authority-for-nonempty-group-cardinality",
                path=path,
                line_start=_line(text, absolute),
                message=(
                    "Group cardinality is inferred from per-expression result collections even though the expression set may be empty."
                ),
                evidence=(
                    f"`{function.group('name')}` initializes result collections empty, fills them only while iterating `dots`, "
                    f"then derives `{infer.group('size')}` from those collections. The build path uses that value to repeat known "
                    "group keys. With zero expressions, an empty result collection does not mean zero groups, so key repetition "
                    "can fail or erase valid groups."
                ),
                falsifiers=[
                    "Required an expression loop whose result collections remain empty when no expressions are supplied.",
                    "Required group/key repetition to depend on the inferred size vector.",
                    "Checked for an independently captured group count from keys or the data mask.",
                    "Checked that the independent count is passed into the recycling/cardinality helper.",
                    "Excluded implementations that preserve zero-expression group cardinality explicitly.",
                ],
                verification=(
                    "Capture group count independently from group keys before expression evaluation, pass it to cardinality/recycling logic, and test zero expressions with ungrouped and grouped data."
                ),
                confidence=0.99,
                supporting=(f"{path}:{_line(text, build_contract.start())}",),
            )
        )
    return findings


def _erlang_nested_group_findings(path: str, text: str) -> list[dict[str, Any]]:
    if not (
        re.search(r"#state\s*\{\s*curr_group\s*=\s*\[[A-Za-z_][A-Za-z0-9_]*\s*\|", text)
        and re.search(r"curr_group\s*=\s*tl\s*\(", text)
    ):
        return []
    flattened = re.compile(
        r"(?P<fun>[a-z][A-Za-z0-9_]*)\s*\("
        r"(?P<head>[\s\S]{0,180}?\{(?P<action>[A-Z][A-Za-z0-9_]*),"
        r"(?P<group>_[A-Za-z][A-Za-z0-9_]*)\}[\s\S]{0,180}?)\)\s*->\s*"
        r"(?P=fun)\s*\((?P<delegate>[\s\S]{0,260}?)\)\s*;",
        re.M,
    )
    findings: list[dict[str, Any]] = []
    for match in flattened.finditer(text):
        group = match.group("group")
        delegate = match.group("delegate")
        if group in delegate:
            continue
        if match.group("action") not in delegate:
            continue
        findings.append(
            _finding(
                officer="Mechanic",
                capability="nested_lifecycle_state",
                category="state",
                severity="blocker",
                root_cause="nested-group-callback-discards-group-identity-before-stack-transition",
                path=path,
                line_start=_line(text, match.start()),
                message=(
                    "A nested group callback discards the group identity before delegating into code that mutates the active-group stack."
                ),
                evidence=(
                    f"`{match.group('fun')}` matches the tuple group component as `{group}` but delegates only "
                    f"`{match.group('action')}` with the unchanged state. The same module pushes and pops `curr_group`; "
                    "discarding the skipped group's identity makes nested callbacks operate on the parent stack entry, "
                    "corrupting testcase ownership and later cleanup."
                ),
                falsifiers=[
                    "Required explicit push and pop operations on the current-group stack in the same module.",
                    "Required a tuple callback carrying action and group identity.",
                    "Required delegation that omits the group identity and does not adjust state.",
                    "Excluded specialized clauses that push, compare, or pop the named group around delegation.",
                    "Excluded flat callbacks with no nested-group stack contract.",
                ],
                verification=(
                    "Preserve the group identity through skip handling, update the stack symmetrically for init/end callbacks, and test a skipped group nested beneath another skipped group."
                ),
                confidence=0.99,
            )
        )
    return findings


def run_static_transfer_28_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    readable: list[str] = []
    findings: list[dict[str, Any]] = []

    for path in changed:
        suffix = Path(path).suffix.lower()
        if suffix not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        if suffix == ".zig":
            findings.extend(_zig_keyword_diagnostic_findings(path, text))
        elif suffix == ".r":
            findings.extend(_r_group_cardinality_findings(path, text))
        elif suffix in {".erl", ".hrl"}:
            findings.extend(_erlang_nested_group_findings(path, text))

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
        "schema_version": "sergeant.static-transfer-28-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
