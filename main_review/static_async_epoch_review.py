"""Static epoch, lifetime, and ownership checks across suspension points.

The officer reasons about whether work that resumes after a suspension still owns
permission to publish shared state. Project code is never executed.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".kt", ".js", ".jsx", ".ts", ".tsx", ".html"}
_JS_ASYNC_RE = re.compile(
    r"(?:async\s+function\s+(?P<decl>[A-Za-z_$][\w$]*)\s*\([^)]*\)|"
    r"(?:const|let|var)\s+(?P<arrow>[A-Za-z_$][\w$]*)\s*=\s*async\s*\([^)]*\)\s*=>)\s*\{",
    re.M,
)
_EFFECT_RE = re.compile(r"\buseEffect\s*\(\s*\(\s*\)\s*=>\s*\{", re.M)


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


def _functions(text: str, pattern: re.Pattern[str]) -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    for match in pattern.finditer(text):
        groups = match.groupdict()
        name = groups.get("decl") or groups.get("arrow") or "anonymous"
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        rows.append((name, text[opening + 1 : closing], opening + 1))
    return rows


def _finding(
    *,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    supporting: Iterable[str],
    falsifiers: Iterable[str],
    verification: str,
    confidence: float,
) -> dict[str, Any]:
    return {
        "source": "static-async-epoch-officer",
        "officer": "Mechanic",
        "capability": "concurrency",
        "category": "concurrency",
        "severity": "major",
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(supporting),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _kotlin_suspend_names(root: Path) -> set[str]:
    names: set[str] = set()
    visited = 0
    for path in root.rglob("*.kt"):
        if visited >= 5000:
            break
        visited += 1
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        names.update(re.findall(r"\bsuspend\s+fun\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text))
    return names


def _kotlin_stale_response(
    root: Path,
    path: str,
    text: str,
    suspend_names: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    call_re = re.compile(
        r"(?P<whole>(?:when\s*\(\s*val\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*|"
        r"val\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*)"
        r"(?:[A-Za-z_][A-Za-z0-9_]*\.)*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^\n;]*\))"
    )
    for call in call_re.finditer(text):
        name = call.group("name")
        if name not in suspend_names:
            continue
        before = text[max(0, call.start() - 1200) : call.start()]
        pre_guard = re.search(
            r"if\s*\([^)]*(?:\b(?:gen|epoch|generation|requestId|version)\b[^)]*(?:!=|==)|!\s*isActive)[^)]*\)",
            before,
            re.I,
        )
        if pre_guard is None:
            continue
        after = text[call.end() : call.end() + 1800]
        write = re.search(
            r"(?P<target>(?:_[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*(?:State|Phase|Status)))\.value\s*=",
            after,
        )
        if write is None:
            continue
        between = after[: write.start()]
        post_guard = re.search(
            r"if\s*\([^)]*(?:\b(?:gen|epoch|generation|requestId|version)\b[^)]*(?:!=|==)|!\s*isActive)[^)]*\)\s*(?:return|continue|break)",
            between,
            re.I,
        )
        if post_guard is not None:
            continue
        call_line = _line(text, call.start())
        write_line = _line(text, call.end() + write.start())
        findings.append(
            _finding(
                root_cause="stale-coroutine-response-after-suspension",
                path=path,
                line_start=call_line,
                message="A coroutine checks its generation before a suspending call but publishes shared state after resumption without revalidating ownership.",
                evidence=(
                    f"Suspending call {name} occurs at line {call_line}; shared {write.group('target')}.value is written at line {write_line}. "
                    "The surrounding flow has a generation/activity guard before suspension but no equivalent guard after resumption and before publication."
                ),
                supporting=(f"{path}:{call_line}", f"{path}:{write_line}"),
                falsifiers=(
                    "Checked that the called function is declared suspend in the repository.",
                    "Checked for a generation, epoch, version, request identity, or activity guard before suspension.",
                    "Checked for an equivalent fail-fast guard after resumption and before the state write.",
                ),
                verification="Revalidate generation and coroutine activity immediately after the suspending call and before any phase/status write; prove a terminal transition cannot be overwritten by a stale response.",
                confidence=0.96,
            )
        )
    return findings


def _react_effect_lifetime(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for effect in _EFFECT_RE.finditer(text):
        opening = effect.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        tail = text[closing + 1 : closing + 300]
        dependencies = re.search(r",\s*\[(?P<deps>[^\]]*)\]\s*\)", tail)
        if dependencies is None or not dependencies.group("deps").strip():
            continue
        cleanup = re.search(r"return\s*\(\s*\)\s*=>\s*\{", body)
        if cleanup is None:
            continue
        for function_name, async_body, body_offset in _functions(body, _JS_ASYNC_RE):
            await_match = re.search(r"\bawait\b", async_body)
            if await_match is None:
                continue
            state_write = re.search(r"\bset[A-Z][A-Za-z0-9_]*\s*\(", async_body[await_match.end() :])
            if state_write is None:
                continue
            after_await = async_body[await_match.end() : await_match.end() + state_write.start()]
            lifetime_guard = re.search(
                r"if\s*\([^)]*(?:cancelled|canceled|disposed|stale|generation|epoch|requestId|isCurrent)[^)]*\)\s*return",
                after_await,
                re.I,
            )
            effect_has_lifetime = bool(
                re.search(r"\b(?:cancelled|canceled|disposed|stale)\s*=\s*false\b", body, re.I)
                and re.search(r"\b(?:cancelled|canceled|disposed|stale)\s*=\s*true\b", body[cleanup.start() :], re.I)
            )
            abort_signal = "AbortController" in body and re.search(r"\.abort\s*\(", body[cleanup.start() :])
            if lifetime_guard is not None or effect_has_lifetime or abort_signal:
                continue
            await_line = _line(text, opening + 1 + body_offset + await_match.start())
            write_line = _line(
                text,
                opening + 1 + body_offset + await_match.end() + state_write.start(),
            )
            findings.append(
                _finding(
                    root_cause="effect-response-published-after-lifetime-change",
                    path=path,
                    line_start=await_line,
                    message="An effect-owned async response can publish component state after the effect's dependency lifetime has ended.",
                    evidence=(
                        f"Nested async function {function_name} suspends at line {await_line} and calls a state setter at line {write_line}. "
                        "The effect has changing dependencies and cleanup, but no cancellation/epoch guard or abort signal prevents a stale response from publishing."
                    ),
                    supporting=(f"{path}:{await_line}", f"{path}:{write_line}"),
                    falsifiers=(
                        "Checked that the effect has a non-empty dependency list and cleanup path.",
                        "Checked for an effect-local cancelled/disposed flag set during cleanup and tested after await.",
                        "Checked for an AbortController cancelled during cleanup.",
                    ),
                    verification="Invalidate or abort the effect-owned request during cleanup and guard every post-await state publication; prove a prior dependency instance cannot overwrite the current one.",
                    confidence=0.95,
                )
            )
    return findings


def _js_controller_ownership(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    shared_collections = {
        match.group("name")
        for match in re.finditer(
            r"(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*=\s*new\s+(?:Map|Set)\s*\(",
            text,
        )
    }
    for function_name, body, body_offset in _functions(text, _JS_ASYNC_RE):
        token = re.search(
            r"(?:const|let|var)\s+(?P<token>[A-Za-z_$][\w$]*)\s*=\s*new\s+AbortController\s*\(\s*\)",
            body,
        )
        if token is None:
            continue
        token_name = token.group("token")
        owner = re.search(
            rf"(?P<owner>[A-Za-z_$][\w$]*)\s*=\s*{re.escape(token_name)}\s*;",
            body[token.end() : token.end() + 400],
        )
        if owner is None:
            continue
        owner_name = owner.group("owner")
        awaits = list(re.finditer(r"\bawait\b(?P<statement>[\s\S]{0,700}?)(?:;|\n)", body))
        if len(awaits) < 2:
            continue
        if not any(re.search(rf"\b{re.escape(token_name)}\.signal\b", item.group("statement")) for item in awaits[:-1]):
            continue
        for later in awaits[1:]:
            if re.search(rf"\b{re.escape(token_name)}\b|\bsignal\b", later.group("statement")):
                continue
            after = body[later.end() :]
            mutation = re.search(
                r"(?P<target>[A-Za-z_$][\w$]*)\s*\.\s*(?:set|add|push)\s*\(",
                after,
            )
            if mutation is None or mutation.group("target") not in shared_collections:
                continue
            between = after[: mutation.start()]
            guard = re.search(
                rf"if\s*\(\s*{re.escape(owner_name)}\s*!==\s*{re.escape(token_name)}\s*\)\s*return",
                between,
            )
            if guard is not None:
                continue
            await_line = _line(text, body_offset + later.start())
            mutation_line = _line(text, body_offset + later.end() + mutation.start())
            findings.append(
                _finding(
                    root_cause="ownership-token-not-revalidated-after-await",
                    path=path,
                    line_start=await_line,
                    message="An operation publishes shared state after a non-cancellable suspension without proving it still owns the operation epoch.",
                    evidence=(
                        f"{function_name} installs {token_name} as {owner_name}, then crosses a later await at line {await_line} that does not use the controller signal. "
                        f"It mutates shared {mutation.group('target')} at line {mutation_line} without comparing {owner_name} to {token_name}."
                    ),
                    supporting=(f"{path}:{await_line}", f"{path}:{mutation_line}"),
                    falsifiers=(
                        "Checked that an earlier awaited operation uses the controller signal.",
                        "Checked that a later awaited operation is not tied to that signal.",
                        "Checked for an owner-token comparison after the later await and before shared-state mutation.",
                        "Checked that the mutation targets a module/shared Map or Set.",
                    ),
                    verification="Revalidate the current controller/epoch after every non-cancellable await and before shared-state publication; prove superseded work cannot write into the new owner's state.",
                    confidence=0.97,
                )
            )
            break
    return findings


def run_static_async_epoch_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    suspend_names = _kotlin_suspend_names(root_path)
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        suffix = Path(path).suffix.lower()
        if suffix not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        readable.append(path)
        if suffix == ".kt":
            findings.extend(_kotlin_stale_response(root_path, path, text, suspend_names))
        else:
            findings.extend(_react_effect_lifetime(path, text))
            findings.extend(_js_controller_ownership(path, text))

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
        "schema_version": "sergeant.static-async-epoch-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "suspend_function_names": sorted(suspend_names),
        "executed_project_code": False,
    }
