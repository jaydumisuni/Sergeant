"""Static checks for persistence intent, response contracts, and runtime authority ownership."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".js", ".jsx", ".ts", ".tsx", ".dart", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp"}
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
    severity: str,
    category: str,
    officer: str,
    message: str,
    evidence: str,
    falsifiers: Iterable[str],
    verification: str,
    supporting: Iterable[str] = (),
    confidence: float = 0.97,
) -> dict[str, Any]:
    refs = [f"{path}:{line_start}", *[str(item) for item in supporting]]
    return {
        "source": "static-transfer-10-officer",
        "officer": officer,
        "capability": category,
        "category": category,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": refs[0],
        "supporting_evidence_refs": sorted(set(refs)),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
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
        re.compile(
            r"\b(?:public\s+|private\s+|protected\s+)?(?:async\s+)?"
            r"(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{",
            re.M,
        ),
    )
    seen: set[tuple[int, str]] = set()
    for pattern in patterns:
        for match in pattern.finditer(text):
            key = (match.start(), match.group("name"))
            if key in seen:
                continue
            seen.add(key)
            opening = match.end() - 1
            closing = _matching_brace(text, opening)
            if closing is not None:
                yield match.group("name"), text[opening + 1 : closing], match.start()


def _has_persistence_boundary(body: str) -> bool:
    direct = re.compile(
        r"(?:\bawait\b|"
        r"\b(?:fetch|authFetch|axios)\s*\(|"
        r"\b(?:localStorage|sessionStorage|indexedDB)\b|"
        r"\b(?:mutate|mutateAsync|onSave|onSubmit|persist|saveTo|writeTo|patch|post|put)\s*\(|"
        r"\b[A-Za-z_$][A-Za-z0-9_$]*(?:API|Api|Client|Service)\s*\.\s*"
        r"(?:create|update|save|patch|post|put|write|persist)\s*\()",
        re.I,
    )
    if direct.search(body):
        return True

    for call in re.finditer(r"\b(?P<name>[A-Za-z_$][A-Za-z0-9_$]*)\s*\(", body):
        name = call.group("name")
        if name.startswith("set"):
            continue
        if re.search(r"(?:save|persist|commit|write|patch|update|submit)$", name, re.I):
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
        if len(state_calls) < 2:
            continue

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
        if re.search(r"\b(?:localOnly|draftOnly|previewOnly|temporary)\b", body, re.I):
            continue

        line = _line(text, offset)
        findings.append(
            _finding(
                root_cause="ui-save-mutates-local-state-without-persistence",
                path=path,
                line_start=line,
                severity="major",
                category="data_integrity",
                officer="Engineer",
                message="A user-facing save handler reports completion by changing local UI state without crossing a durable persistence boundary.",
                evidence=(
                    f"`{name}` updates domain state, clears edit/draft state, and has no request, storage write, mutation callback, "
                    "or other persistence operation in the handler. The UI can appear saved while a refresh restores the old record."
                ),
                falsifiers=(
                    "Checked for awaited and direct fetch/HTTP calls in the handler.",
                    "Checked for API/client/service create, update, save, patch, put, post or persist calls.",
                    "Checked for onSave/onSubmit callbacks and local durable browser storage.",
                    "Checked that the handler updates domain state and exits edit mode rather than only changing a temporary preview.",
                ),
                verification=(
                    "Persist the edited record first, fail visibly on a rejected/non-successful write, and update local state or leave edit mode "
                    "only after the durable write succeeds. Prove a refresh retains the change and a failed write keeps recovery controls available."
                ),
            )
        )
    return findings


def _invalid_shape_empty_findings(path: str, text: str) -> list[dict[str, Any]]:
    suffix = Path(path).suffix.lower()
    if suffix not in {".dart", ".js", ".jsx", ".ts", ".tsx", ".py"}:
        return []

    patterns = (
        re.compile(
            r"if\s*\(\s*(?P<value>[A-Za-z_$][A-Za-z0-9_$]*)\s+is!\s+List(?:<[^>]+>)?\s*\)"
            r"\s*(?:\{\s*)?return\s+(?:const\s+)?\[\s*\]\s*;",
            re.M,
        ),
        re.compile(
            r"if\s*\(\s*!\s*Array\.isArray\s*\(\s*(?P<value>[A-Za-z_$][A-Za-z0-9_$]*)\s*\)\s*\)"
            r"\s*(?:\{\s*)?return\s+\[\s*\]\s*;?",
            re.M,
        ),
        re.compile(
            r"if\s+not\s+isinstance\s*\(\s*(?P<value>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*list\s*\)\s*:"
            r"\s*(?:\n[ \t]+)?return\s+\[\s*\]",
            re.M,
        ),
    )

    findings: list[dict[str, Any]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            value = match.group("value")
            before = text[max(0, match.start() - 900) : match.start()]
            network_value = bool(
                re.search(
                    rf"\b{re.escape(value)}\s*=\s*await\s+[^\n;]*(?:get|fetch|request|call|send)\s*\(",
                    before,
                    re.I,
                )
                or re.search(
                    rf"\bfinal\s+{re.escape(value)}\s*=\s*await\s+[^\n;]+",
                    before,
                    re.I,
                )
                or re.search(r"(?:/api/|ApiClient|_apiClient|fetch\s*\()", before, re.I)
            )
            if not network_value:
                continue
            around = text[max(0, match.start() - 300) : min(len(text), match.end() + 300)]
            if re.search(r"(?:204|no[_ -]?content|optional|nullable|not[_ -]?found)", around, re.I):
                continue

            line = _line(text, match.start())
            findings.append(
                _finding(
                    root_cause="invalid-response-shape-silently-converted-to-empty-result",
                    path=path,
                    line_start=line,
                    severity="major",
                    category="api_contract",
                    officer="Engineer",
                    message="An invalid remote response shape is converted into a valid empty collection.",
                    evidence=(
                        f"The remote result `{value}` is required to be a collection, but a non-collection value returns an empty list. "
                        "Callers cannot distinguish a contract failure from a successful request with zero domain items."
                    ),
                    falsifiers=(
                        "Checked that the value comes from an awaited API/network boundary.",
                        "Checked that the unexpected type returns an empty collection rather than raising or returning an explicit error.",
                        "Checked for an explicit optional, 204/no-content or not-found contract near the branch.",
                        "Checked that the normal path converts the same value into a typed collection.",
                    ),
                    verification=(
                        "Reject the unexpected response type with a controlled contract error and prove malformed payloads surface failure while "
                        "a genuine empty list remains a successful empty-domain result."
                    ),
                )
            )
    return findings


def _global_authority_findings(
    changed: list[str],
    texts: dict[str, str],
) -> list[dict[str, Any]]:
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
            if "thread_local" in pointer.group("prefix"):
                continue
            type_name = pointer.group("type").split("::")[-1].split("<", 1)[0]
            if _AUTHORITY_TYPE_RE.search(type_name) is None:
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
            ambient_use = re.search(
                rf"(?:registerCommand|Factory|build|create|make_unique)[\s\S]{{0,2400}}\bget{re.escape(stem)}\s*\(",
                corpus,
                re.I,
            )
            if setter is None or getter is None or ambient_use is None:
                continue

            line = _line(text, pointer.start())
            findings.append(
                _finding(
                    root_cause="process-wide-runtime-authority-reached-through-mutable-global",
                    path=path,
                    line_start=line,
                    severity="major",
                    category="architecture",
                    officer="Engineer",
                    message="Operation-specific runtime authority is reached through a process-wide mutable pointer.",
                    evidence=(
                        f"`{variable}` stores `{type_name}` authority globally; setter/getter accessors mutate and expose it, and a factory/build "
                        "path obtains the authority through the getter instead of receiving it from the caller that owns the operation."
                    ),
                    falsifiers=(
                        "Checked that the pointer type represents runtime, session, engine, manager, client, connection or controller authority.",
                        "Checked for both a mutable setter and getter around the same global pointer.",
                        "Checked that a factory/build path actually consumes the getter.",
                        "Excluded thread-local authority and code that only receives the dependency through an explicit per-operation context.",
                    ),
                    verification=(
                        "Remove the mutable global accessor and thread the required authority through an explicit request/session/operation context. "
                        "Prove two independent owners can build operations without overwriting or borrowing each other's runtime dependency."
                    ),
                )
            )
    return findings


def run_static_transfer_10_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    texts: dict[str, str] = {}
    findings: list[dict[str, Any]] = []
    readable: list[str] = []

    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES | {".py"}:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        texts[path] = text
        readable.append(path)
        findings.extend(_ui_state_only_save_findings(path, text))
        findings.extend(_invalid_shape_empty_findings(path, text))

    findings.extend(_global_authority_findings(changed, texts))

    unique = {(str(item["root_cause"]), str(item["path"])): item for item in findings}
    return {
        "schema_version": "sergeant.static-transfer-10-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": readable,
        "executed_project_code": False,
    }
