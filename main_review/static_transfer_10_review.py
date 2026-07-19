"""Implementation helpers for transfer-10 persistence and runtime-authority checks.

This module is not invoked directly by the canonical status bundle. The
``static_contract_surface_review`` wrapper owns admission and reuses the proven
helpers below, while remote collection-shape contracts remain owned by
``static_remote_contract_review``.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
_UI_SUFFIXES = {".js", ".jsx", ".ts", ".tsx"}
_CPP_SUFFIXES = {".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
_AUTHORITY_TYPE_RE = re.compile(
    r"(?:AudioEngine|Engine|Session|Runtime|Context|Manager|Client|Connection|Controller)$",
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
) -> dict[str, Any]:
    return {
        "source": "static-contract-surface-officer",
        "officer": "Engineer",
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
        "confidence": 0.97,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _javascript_function_blocks(text: str) -> Iterable[tuple[str, str, int]]:
    patterns = (
        re.compile(
            r"\b(?:const|let|var)\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*"
            r"(?:async\s*)?\([^)]*\)\s*=>\s*\{",
            re.M,
        ),
        re.compile(
            r"\b(?:async\s+)?function\s+(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{",
            re.M,
        ),
    )
    for pattern in patterns:
        for match in pattern.finditer(text):
            opening = match.end() - 1
            closing = _matching_brace(text, opening)
            if closing is not None:
                yield match.group("name"), text[opening + 1 : closing], match.start()


def _has_persistence_boundary(body: str) -> bool:
    if re.search(
        r"(?:\bawait\b|\b(?:fetch|authFetch|axios)\s*\(|"
        r"\b(?:localStorage|sessionStorage|indexedDB)\b|"
        r"\b(?:mutate|mutateAsync|onSave|onSubmit|persist|saveTo|writeTo|patch|post|put)\s*\(|"
        r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:API|Api|Client|Service)\s*\.\s*"
        r"(?:create|update|save|patch|post|put|write|persist)\s*\()",
        body,
        re.I,
    ):
        return True
    for call in re.finditer(r"\b(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\(", body):
        name = call.group("name")
        if not name.startswith("set") and re.search(r"(?:save|persist|commit|write|patch|update|submit)$", name, re.I):
            return True
    return False


def _ui_state_only_save_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _UI_SUFFIXES:
        return []
    remote_context = bool(
        re.search(
            r"(?:\bfetch\s*\(|\bauthFetch\s*\(|\baxios\b|"
            r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:API|Api|Client|Service)\s*\.|"
            r"/api/|projectId|recordId|unitId|entityId)",
            text,
            re.I,
        )
    )
    if not remote_context:
        return []

    findings: list[dict[str, Any]] = []
    for name, body, offset in _javascript_function_blocks(text):
        if re.search(r"(?:save|submit|commit|apply)$", name, re.I) is None:
            continue
        state_calls = list(re.finditer(r"\bset(?P<state>[A-Z][A-Za-z0-9_$]*)\s*\(", body))
        domain_updates = [
            item
            for item in state_calls
            if re.search(r"(?:edit|editing|draft|loading|error|open|modal|selected)", item.group("state"), re.I)
            is None
        ]
        closes_edit = bool(
            re.search(
                r"\bset(?:Editing[A-Za-z0-9_$]*|[A-Za-z0-9_$]*Draft)\s*\(\s*null\s*\)",
                body,
                re.I,
            )
        )
        if not domain_updates or not closes_edit or _has_persistence_boundary(body):
            continue
        findings.append(
            _finding(
                root_cause="ui-save-mutates-local-state-without-persistence",
                path=path,
                line_start=_line(text, offset),
                category="data_integrity",
                message="A user-facing save handler reports completion by changing local UI state without crossing a durable persistence boundary.",
                evidence=(
                    f"`{name}` updates domain state, clears edit/draft state, and has no request, storage write, mutation callback, "
                    "or other persistence operation. The apparent save can disappear on reload."
                ),
                falsifiers=(
                    "Checked for fetch/HTTP, API/client/service writes, mutation callbacks and durable browser storage.",
                    "Checked that the handler updates domain state and exits edit mode rather than only changing a temporary preview.",
                ),
                verification=(
                    "Persist the edited record first, fail visibly on non-success, and update local state or leave edit mode only after the durable write succeeds."
                ),
            )
        )
    return findings


def _global_authority_findings(changed: list[str], texts: dict[str, str]) -> list[dict[str, Any]]:
    corpus = "\n".join(texts[path] for path in changed if Path(path).suffix.lower() in _CPP_SUFFIXES)
    if not corpus:
        return []
    pointer_re = re.compile(
        r"(?m)^(?P<prefix>\s*(?:static\s+)?)"
        r"(?P<type>[A-Za-z_][A-Za-z0-9_:<>]*)\s*\*\s*"
        r"(?P<var>(?:s_|g_)[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?:nullptr|NULL|0)\s*;"
    )
    findings: list[dict[str, Any]] = []
    for path in changed:
        if Path(path).suffix.lower() not in _CPP_SUFFIXES:
            continue
        text = texts.get(path, "")
        for pointer in pointer_re.finditer(text):
            type_name = pointer.group("type").split("::")[-1].split("<", 1)[0]
            if "thread_local" in pointer.group("prefix") or _AUTHORITY_TYPE_RE.search(type_name) is None:
                continue
            variable = pointer.group("var")
            stem = re.sub(r"^(?:s_|g_)", "", variable)
            stem = stem[:1].upper() + stem[1:]
            setter = re.search(
                rf"\bset{re.escape(stem)}\s*\([^)]*\)\s*\{{[^}}]*\b{re.escape(variable)}\s*=",
                corpus,
                re.S,
            )
            getter = re.search(
                rf"\bget{re.escape(stem)}\s*\([^)]*\)\s*\{{[^}}]*return\s+{re.escape(variable)}\s*;",
                corpus,
                re.S,
            )
            ambient = re.search(
                rf"(?:registerCommand|Factory|build|create|make_unique)[\s\S]{{0,2400}}\bget{re.escape(stem)}\s*\(",
                corpus,
                re.I,
            )
            if setter is None or getter is None or ambient is None:
                continue
            findings.append(
                _finding(
                    root_cause="process-wide-runtime-authority-reached-through-mutable-global",
                    path=path,
                    line_start=_line(text, pointer.start()),
                    category="architecture",
                    message="Operation-specific runtime authority is reached through a process-wide mutable pointer.",
                    evidence=(
                        f"`{variable}` stores `{type_name}` globally; setter/getter accessors expose it and factory/build code obtains it ambiently."
                    ),
                    falsifiers=(
                        "Checked for both a mutable setter and getter around the same runtime pointer.",
                        "Checked that command/factory/build logic consumes the getter.",
                        "Excluded thread-local state and explicit per-operation context parameters.",
                    ),
                    verification=(
                        "Remove the mutable global accessor and pass the authority through an explicit request/session/operation context."
                    ),
                )
            )
    return findings
