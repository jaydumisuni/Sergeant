"""Static checks learned only after transfer set 15's blind 0/3 was frozen."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Iterable

_PYTHON_SUFFIXES = {".py"}
_KOTLIN_SUFFIXES = {".kt", ".kts"}
_SWIFT_SUFFIXES = {".swift"}


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
    severity: str,
    message: str,
    evidence: str,
    falsifiers: Iterable[str],
    verification: str,
    supporting: Iterable[str] = (),
    confidence: float = 0.97,
) -> dict[str, Any]:
    refs = [f"{path}:{line_start}", *[str(item) for item in supporting]]
    return {
        "source": "static-transfer-15-officer",
        "officer": "Mechanic" if category in {"concurrency", "lifecycle"} else "Engineer",
        "capability": category,
        "category": category,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "supporting_evidence_refs": list(dict.fromkeys(refs)),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _python_transport_envelope_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _PYTHON_SUFFIXES:
        return []
    if re.search(
        r"(?:websocket|web_socket|socket|transport|send_(?:command|message)|recv|round.?trip)",
        text,
        re.I,
    ) is None:
        return []

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []

    parent: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    findings: list[dict[str, Any]] = []
    no_answer_names = re.compile(
        r"(?:Connection|Timeout|WebSocket|Socket|Transport|OSError|BrokenPipe|Reset|Closed)",
        re.I,
    )

    def dotted(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            base = dotted(node.value)
            return f"{base}.{node.attr}" if base else node.attr
        if isinstance(node, ast.Call):
            return dotted(node.func)
        return ""

    def contains_soft_failure_return(nodes: list[ast.stmt]) -> bool:
        for item in ast.walk(ast.Module(body=nodes, type_ignores=[])):
            if not isinstance(item, ast.Return) or not isinstance(item.value, ast.Dict):
                continue
            values: dict[str, ast.AST] = {}
            for key, value in zip(item.value.keys, item.value.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    values[key.value] = value
            success = values.get("success")
            has_false_success = isinstance(success, ast.Constant) and success.value is False
            if has_false_success and ("error" in values or "message" in values):
                return True
        return False

    def handler_rethrows_no_answer(handler: ast.ExceptHandler) -> bool:
        segment = ast.get_source_segment(text, handler) or ""
        if re.search(
            r"(?:Connection|Timeout|WebSocket|Socket|Transport|OSError).{0,100}\braise\b",
            segment,
            re.S,
        ):
            return True
        for item in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
            if isinstance(item, ast.Raise):
                probe = ast.get_source_segment(text, parent.get(item, item)) or segment
                if no_answer_names.search(probe):
                    return True
        return False

    for function in [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]:
        function_segment = ast.get_source_segment(text, function) or ""
        if re.search(
            r"(?:websocket|socket|transport|send_(?:command|message))",
            function_segment,
            re.I,
        ) is None:
            continue
        for attempt in [node for node in ast.walk(function) if isinstance(node, ast.Try)]:
            awaited_calls = [
                node
                for node in ast.walk(ast.Module(body=attempt.body, type_ignores=[]))
                if isinstance(node, ast.Await) and isinstance(node.value, ast.Call)
            ]
            call_names = [dotted(node.value.func) for node in awaited_calls]
            if not any(
                re.search(r"(?:get_.*(?:socket|client)|connect|send|recv|request|command)", name, re.I)
                for name in call_names
            ):
                continue

            protected_types: list[str] = []
            broad: ast.ExceptHandler | None = None
            for handler in attempt.handlers:
                if handler.type is None:
                    broad = handler
                    continue
                type_text = ast.get_source_segment(text, handler.type) or ""
                if type_text in {"Exception", "BaseException"}:
                    broad = handler
                else:
                    protected_types.append(type_text)
            if broad is None or not contains_soft_failure_return(broad.body):
                continue
            if any(no_answer_names.search(item) for item in protected_types):
                continue
            if handler_rethrows_no_answer(broad):
                continue

            line = getattr(broad, "lineno", getattr(attempt, "lineno", 1))
            findings.append(
                _finding(
                    root_cause="transport-no-answer-collapsed-into-authoritative-failure-envelope",
                    path=path,
                    line_start=line,
                    category="api_contract",
                    severity="blocker",
                    message=(
                        "A remote transport that never answered is collapsed into the same soft failure "
                        "envelope as an authoritative remote rejection."
                    ),
                    evidence=(
                        f"`{function.name}` awaits connection/send work under a broad exception handler and returns a "
                        "`success: false` envelope without preserving a typed no-answer path. Callers cannot distinguish "
                        "blind transport failure from a remote system that received and rejected the command."
                    ),
                    falsifiers=(
                        "Checked for a typed connection, timeout, socket, transport, or reset handler that rethrows before the broad handler.",
                        "Checked the broad handler for an explicit no-answer classification followed by raise.",
                        "Required awaited transport/send semantics and a structured soft-failure return, not an ordinary local Result wrapper.",
                    ),
                    verification=(
                        "Separate no-answer transport failures from answered rejections, raise or explicitly mark the former, "
                        "and prove blind read paths cannot report authoritative empty or negative results."
                    ),
                )
            )
    return findings


def _kotlin_cancellation_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _KOTLIN_SUFFIXES:
        return []

    findings: list[dict[str, Any]] = []
    function_re = re.compile(
        r"\bsuspend\s+fun\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)"
        r"(?:\s*:\s*[^{=\n]+)?\s*\{",
        re.M,
    )
    for match in function_re.finditer(text):
        opening = text.find("{", match.start())
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        if "runCatching" not in body and re.search(
            r"catch\s*\(\s*\w+\s*:\s*(?:Exception|Throwable)", body
        ) is None:
            continue
        if re.search(r"CancellationException", body):
            continue
        if re.search(
            r"\bensureActive\s*\(|\bcurrentCoroutineContext\s*\(\s*\)\.ensureActive",
            body,
        ):
            continue

        isolated_call = re.search(
            r"runCatching\s*\{(?P<inside>[\s\S]{0,1000}?)\}"
            r"\s*\.(?:onFailure|recover|recoverCatching|getOrElse|fold)\b",
            body,
        )
        broad_catch = re.search(r"catch\s*\(\s*\w+\s*:\s*(?:Exception|Throwable)\s*\)", body)
        if isolated_call is None and broad_catch is None:
            continue

        call_body = isolated_call.group("inside") if isolated_call is not None else body
        if re.search(
            r"\b[A-Za-z0-9_]*(?:update|refresh|fetch|load|save|send|receive|await|collect|emit|sync|upload|download|execute|invoke)"
            r"[A-Za-z0-9_]*\s*\(",
            call_body,
            re.I,
        ) is None:
            continue

        local_offset = isolated_call.start() if isolated_call is not None else broad_catch.start()
        line = _line(text, opening + 1 + local_offset)
        findings.append(
            _finding(
                root_cause="coroutine-cancellation-swallowed-by-per-item-isolation",
                path=path,
                line_start=line,
                category="lifecycle",
                severity="major",
                message="A suspend operation isolates ordinary item failures but also swallows coroutine cancellation.",
                evidence=(
                    f"`{match.group('name')}` runs suspend-like refresh/update work through broad failure isolation and "
                    "continues or logs every failure without rethrowing `CancellationException`. Cooperative cancellation "
                    "can therefore be converted into an ordinary per-item error."
                ),
                falsifiers=(
                    "Checked for an explicit CancellationException rethrow before ordinary failure handling.",
                    "Checked for ensureActive/currentCoroutineContext cancellation enforcement.",
                    "Required a suspend function and refresh/update/fetch/load/save/send-style work, excluding non-suspending local runCatching uses.",
                ),
                verification=(
                    "Rethrow CancellationException (or call ensureActive) before isolating ordinary failures, and prove cancellation "
                    "stops remaining work while non-cancellation item errors remain contained."
                ),
            )
        )
    return findings


def _swift_optional_presence_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _SWIFT_SUFFIXES:
        return []

    struct_re = re.compile(
        r"(?:private\s+|internal\s+|public\s+)?struct\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        r"[^{]*\{",
        re.M,
    )
    structs: dict[str, str] = {}
    for match in struct_re.finditer(text):
        opening = text.find("{", match.start())
        closing = _matching_brace(text, opening)
        if closing is not None:
            structs[match.group("name")] = text[opening + 1 : closing]

    findings: list[dict[str, Any]] = []
    optional_field_re = re.compile(
        r"\blet\s+(?P<field>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*:\s*(?P<type>[A-Za-z_][A-Za-z0-9_]*)\?",
        re.I,
    )
    for owner_name, owner_body in structs.items():
        for field_match in optional_field_re.finditer(owner_body):
            field = field_match.group("field")
            if re.search(r"(?:limit|cap|budget|quota)", field, re.I) is None:
                continue
            value_type = field_match.group("type")
            value_body = structs.get(value_type, "")
            if not value_body:
                continue

            parsed_properties: list[str] = []
            property_re = re.compile(
                r"\bvar\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
                r"\s*:\s*(?:Decimal|Double|Float|Int|UInt)[^=\n{]*\?\s*\{",
                re.I,
            )
            for prop in property_re.finditer(value_body):
                parsed = prop.group("name")
                if re.search(r"(?:amount|value|decimal|parsed|scaled)", parsed, re.I) is None:
                    continue
                prop_opening = value_body.find("{", prop.start())
                prop_closing = _matching_brace(value_body, prop_opening)
                if prop_closing is None:
                    continue
                prop_body = value_body[prop_opening + 1 : prop_closing]
                if re.search(r"\b(?:guard|if)\b[\s\S]{0,700}?\breturn\s+nil\b", prop_body) is None:
                    continue
                parsed_properties.append(parsed)

            for parsed in parsed_properties:
                use_re = re.compile(
                    rf"\b(?:[A-Za-z_][A-Za-z0-9_]*\??\.)*{re.escape(field)}\?\."
                    rf"{re.escape(parsed)}\b"
                )
                for use in use_re.finditer(text):
                    context = text[max(0, use.start() - 220) : min(len(text), use.end() + 220)]
                    if re.search(r"(?:budget|cap|limit|quota|uncapped|unlimited)", context, re.I) is None:
                        continue
                    function_window = text[max(0, use.start() - 1800) : min(len(text), use.end() + 1800)]
                    if re.search(
                        rf"guard\s+let\s+{re.escape(field)}\b|if\s+let\s+{re.escape(field)}\b",
                        function_window,
                    ):
                        continue
                    line = _line(text, use.start())
                    findings.append(
                        _finding(
                            root_cause="present-invalid-optional-field-collapsed-into-absent-semantics",
                            path=path,
                            line_start=line,
                            category="data_integrity",
                            severity="major",
                            message=(
                                "A present-but-invalid optional control value is collapsed into the same nil state as an absent value."
                            ),
                            evidence=(
                                f"`{owner_name}.{field}` is optional, while `{value_type}.{parsed}` is also optional because validation "
                                f"can reject malformed values. The consumer uses `{field}?.{parsed}` directly in limit/budget semantics, "
                                "so absent/null and present-but-invalid inputs become indistinguishable."
                            ),
                            falsifiers=(
                                "Checked that the outer field is optional and named as a limit, cap, budget, or quota.",
                                "Checked that the inner parsed numeric property can return nil on validation failure.",
                                "Checked for an explicit field-presence branch that treats absent/null separately from invalid-present content.",
                            ),
                            verification=(
                                "Branch on field presence first, then validate the present value; preserve absent/null as the intentional "
                                "uncapped state and reject or invalidate a present malformed value."
                            ),
                        )
                    )
    return findings


def run_static_transfer_15_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    for path in changed:
        text = _safe_text(root_path, path)
        if not text:
            continue
        findings.extend(_python_transport_envelope_findings(path, text))
        findings.extend(_kotlin_cancellation_findings(path, text))
        findings.extend(_swift_optional_presence_findings(path, text))

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
        "schema_version": "sergeant.static-transfer-15-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "executed_project_code": False,
    }
