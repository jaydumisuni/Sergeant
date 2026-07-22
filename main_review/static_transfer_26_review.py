"""Static checks learned after transfer set 26's blind artifact was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Iterator

_SOURCE_SUFFIXES = {".c", ".h", ".hs"}
_PROTOCOL_ID_FIELDS = r"(?:id|stream_id|handle|fd|channel_id)"
_PROTOCOL_ACTION_RE = re.compile(
    r"\b(?:submit|send|queue|write|dispatch|flush|frame|priority)[A-Za-z0-9_]*\s*\(",
    re.I,
)
_ACCUMULATOR_NAMES = r"(?:warns|warnings|diagnostics|messages|notices)"


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


def _matching_delimiter(text: str, opening: int, left: str, right: str) -> int | None:
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
        if char == left:
            depth += 1
        elif char == right:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _iter_braced_ifs(text: str) -> Iterator[tuple[int, str, str]]:
    for match in re.finditer(r"\bif\s*\(", text):
        opening_paren = text.find("(", match.start(), match.end())
        if opening_paren < 0:
            continue
        closing_paren = _matching_delimiter(text, opening_paren, "(", ")")
        if closing_paren is None:
            continue
        cursor = closing_paren + 1
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] != "{":
            continue
        closing_brace = _matching_delimiter(text, cursor, "{", "}")
        if closing_brace is None:
            continue
        yield (
            match.start(),
            text[opening_paren + 1 : closing_paren],
            text[cursor + 1 : closing_brace],
        )


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
        "source": "static-transfer-26-officer",
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


def _c_protocol_lifecycle_findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    assignment_re = re.compile(
        r"\bstruct\s+[A-Za-z_][A-Za-z0-9_]*\s*\*\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
        r"(?P<factory>[A-Za-z_][A-Za-z0-9_]*)\s*\([^;\n]*\)\s*;",
        re.M,
    )

    for assignment in assignment_re.finditer(text):
        variable = assignment.group("var")
        if not re.search(r"(?:stream|session|channel|connection|context|ctx)", variable, re.I):
            continue
        window = text[assignment.end() : assignment.end() + 3000]
        for branch_start, condition, body in _iter_braced_ifs(window):
            identity = re.search(rf"\b{re.escape(variable)}\s*->\s*{_PROTOCOL_ID_FIELDS}\b", body)
            if identity is None or _PROTOCOL_ACTION_RE.search(body) is None:
                continue

            prefix = window[:branch_start]
            preguard = re.search(
                rf"\bif\s*\(\s*(?:!\s*{re.escape(variable)}|{re.escape(variable)}\s*==\s*(?:NULL|0))\s*\)"
                rf"[\s\S]{{0,180}}?(?:return|goto|continue|break)\b",
                prefix[-700:],
                re.M,
            )
            pointer_guard = re.search(
                rf"(?:\b{re.escape(variable)}\s*&&|\b{re.escape(variable)}\s*!=\s*(?:NULL|0))",
                condition,
            )
            identity_guard = re.search(
                rf"\b{re.escape(variable)}\s*->\s*{_PROTOCOL_ID_FIELDS}\s*(?:>|>=|!=)\s*(?:0|-1)",
                condition,
            )
            if preguard or (pointer_guard and identity_guard):
                continue

            absolute_branch = assignment.end() + branch_start
            findings.append(
                _finding(
                    officer="Mechanic",
                    capability="protocol_lifecycle",
                    category="correctness",
                    severity="blocker",
                    root_cause="protocol-operation-uses-resource-before-open-identity",
                    path=path,
                    line_start=_line(text, absolute_branch),
                    message=(
                        "A protocol operation dereferences a stream/session resource before proving that the resource exists and has an opened protocol identity."
                    ),
                    evidence=(
                        f"`{variable}` is obtained from `{assignment.group('factory')}(...)`. A later branch does not establish both pointer existence and a usable protocol identifier, "
                        f"yet it dereferences `{identity.group(0)}` and submits or queues protocol work. The branch can run before the stream/session is opened."
                    ),
                    falsifiers=[
                        "Required a pointer-valued stream/session/channel/context resource obtained inside the function.",
                        "Required a later braced protocol-action branch that dereferences the resource identity.",
                        "Checked for an earlier fail-fast null guard.",
                        "Checked for both pointer existence and positive/non-sentinel protocol-identity guards in the branch condition.",
                        "Excluded guarded operations and non-protocol pointer use.",
                    ],
                    verification=(
                        "Gate the operation on both resource existence and an opened positive/non-sentinel protocol identity; test configuration changes before open, during open, and after close."
                    ),
                    confidence=0.99,
                    supporting=(f"{path}:{_line(text, assignment.start())}",),
                )
            )
            break
    return findings


def _haskell_accumulator_order_findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    prepend_re = re.compile(
        rf"(?:(?P<item>[A-Za-z_][A-Za-z0-9_'.]*)\s*:\s*(?P<acc>{_ACCUMULATOR_NAMES})\b|"
        rf"(?P<batch>[^\n]{{1,160}}?)\+\+\s*(?P<batch_acc>{_ACCUMULATOR_NAMES})\b)",
        re.M,
    )

    seen: set[str] = set()
    for prepend in prepend_re.finditer(text):
        accumulator = prepend.group("acc") or prepend.group("batch_acc")
        if accumulator in seen:
            continue
        direct_publish = re.search(
            rf"(?:\brun[A-Za-z0-9_']*\b|\bfailure\b|\bsuccess\b|\bfinali[sz]e[A-Za-z0-9_']*\b)"
            rf"[\s\S]{{0,1800}}?\(\s*{re.escape(accumulator)}\s*,",
            text,
            re.M,
        )
        if direct_publish is None:
            continue
        normalization = re.search(
            rf"\b(?:reverse|sort[A-Za-z0-9_']*)\s*(?:\([^)]*\)\s*)?{re.escape(accumulator)}\b",
            text,
            re.M,
        )
        if normalization is not None and normalization.start() <= direct_publish.end() + 500:
            continue
        append_in_order = re.search(
            rf"\b{re.escape(accumulator)}\s*\+\+\s*(?:\[[^\]]+\]|[A-Za-z_][A-Za-z0-9_']*)",
            text,
        )
        if append_in_order is not None and prepend.group("acc") is None:
            continue

        seen.add(accumulator)
        findings.append(
            _finding(
                officer="Analyst",
                capability="observable_ordering",
                category="correctness",
                severity="major",
                root_cause="prepended-diagnostics-published-in-reverse-order",
                path=path,
                line_start=_line(text, direct_publish.start()),
                message=(
                    "Diagnostics are prepended to an accumulator and later published directly, reversing their observable source order."
                ),
                evidence=(
                    f"`{accumulator}` is built by prepending individual or batched diagnostics to the existing accumulator. "
                    f"The result/failure boundary later returns `({accumulator}, ...)` without reversing or sorting it."
                ),
                falsifiers=[
                    "Required an accumulator whose semantic name denotes warnings, diagnostics, messages, or notices.",
                    "Required prepend-style accumulation (`item : accumulator` or `newBatch ++ accumulator`).",
                    "Required a run/failure/success/finalization boundary that directly publishes the same accumulator.",
                    "Checked for reverse/sort normalization before publication, including named helper functions.",
                    "Excluded append-in-order accumulation and normalized terminal output.",
                ],
                verification=(
                    "Publish diagnostics in source order by reversing the prepend accumulator or sorting by source position; verify multiple warnings across success and failure paths."
                ),
                confidence=0.98,
                supporting=(f"{path}:{_line(text, prepend.start())}",),
            )
        )
    return findings


def run_static_transfer_26_review(
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
        if suffix in {".c", ".h"}:
            findings.extend(_c_protocol_lifecycle_findings(path, text))
        elif suffix == ".hs":
            findings.extend(_haskell_accumulator_order_findings(path, text))

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
        "schema_version": "sergeant.static-transfer-26-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
