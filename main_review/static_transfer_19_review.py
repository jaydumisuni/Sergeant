"""Static checks learned only after transfer set 19's blind 0/3 was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_C_SUFFIXES = {".c", ".cc", ".cpp", ".h", ".hpp"}


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
        "source": "static-transfer-19-officer",
        "officer": "Engineer" if category in {"api_contract", "correctness", "security"} else "Mechanic",
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


def _go_repeat_registration_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() != ".go":
        return []

    findings: list[dict[str, Any]] = []
    function_re = re.compile(
        r"func\s+(?P<name>(?:Must)?Register[A-Za-z0-9_]*)\s*\(\s*(?P<param>[A-Za-z_][A-Za-z0-9_]*)\s+\*(?P<type>[A-Za-z_][A-Za-z0-9_.]*)\s*\)\s*\{",
        re.M,
    )
    for function in function_re.finditer(text):
        opening = text.find("{", function.start())
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        param = function.group("param")

        guard = re.search(
            r"if\s+(?P<slot>[A-Za-z_][A-Za-z0-9_]*)\s*!=\s*nil\s*\{(?P<branch>[\s\S]{0,500}?)\}",
            body,
        )
        if guard is None or re.search(r"\bpanic\s*\(", guard.group("branch")) is None:
            continue
        slot = guard.group("slot")
        assignment = re.search(rf"\b{re.escape(slot)}\s*=\s*{re.escape(param)}\b", body)
        if assignment is None:
            continue
        global_slot = re.search(
            rf"(?:var\s*\([^)]*\b{re.escape(slot)}\s+\*{re.escape(function.group('type'))}\b|\bvar\s+{re.escape(slot)}\s+\*{re.escape(function.group('type'))}\b)",
            text[: function.start()],
            re.S,
        )
        if global_slot is None:
            continue

        equivalence = re.search(
            rf"(?:Equal|Equivalent|Same|Matches|DeepEqual|Compare)[A-Za-z0-9_]*\s*\([^)]*\b{re.escape(slot)}\b[^)]*\b{re.escape(param)}\b|"
            rf"(?:Equal|Equivalent|Same|Matches|DeepEqual|Compare)[A-Za-z0-9_]*\s*\([^)]*\b{re.escape(param)}\b[^)]*\b{re.escape(slot)}\b",
            body,
            re.I,
        )
        explicit_once = re.search(r"\bsync\.Once\b|\.Do\s*\(", body)
        if equivalence is not None or explicit_once is not None:
            continue

        line_start = _line(text, opening + 1 + guard.start())
        findings.append(
            _finding(
                root_cause="repeat-registration-panics-before-equivalence-check",
                path=path,
                line_start=line_start,
                category="api_contract",
                severity="major",
                message="A process-global registration API treats every repeat call as fatal without allowing an identical registration to be a no-op.",
                evidence=(
                    f"`{function.group('name')}` stores `{param}` in process-global `{slot}`, but its non-nil guard panics before "
                    "checking whether the already registered value is equivalent. Re-initializing the same component in one process "
                    "therefore crashes even when the effective policy is unchanged."
                ),
                falsifiers=(
                    "Required an exported registration-style function that assigns its pointer argument to process-global state.",
                    "Required a non-nil repeat guard that panics.",
                    "Checked for an equality/equivalence comparison or sync.Once boundary before the panic.",
                ),
                verification=(
                    "Validate the candidate, make identical re-registration a no-op, continue rejecting a different value, and test "
                    "first registration, identical repeat, conflicting repeat and invalid input."
                ),
                supporting=(f"{path}:{_line(text, opening + 1 + assignment.start())}",),
                confidence=0.95,
            )
        )
    return findings


def _java_distribution_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() != ".java":
        return []
    normalized = path.replace("\\", "/").lower()
    if "/client/" in normalized or normalized.startswith("client/"):
        return []
    if not any(marker in normalized for marker in ("/common/", "/server/", "common/", "server/")):
        return []

    client_import = re.search(r"^\s*import\s+(?P<type>(?:net\.minecraft\.)?client\.[A-Za-z0-9_$.]+)\s*;", text, re.M)
    if client_import is None:
        client_import = re.search(r"^\s*import\s+(?P<type>net\.minecraft\.client\.[A-Za-z0-9_$.]+)\s*;", text, re.M)
    if client_import is None:
        return []
    simple_name = client_import.group("type").split(".")[-1]
    runtime_use = re.search(rf"\b(?:instanceof|new)\s+{re.escape(simple_name)}\b|\b{re.escape(simple_name)}\.", text[client_import.end() :])
    if runtime_use is None:
        return []
    client_guard = re.search(r"@OnlyIn\s*\(\s*Dist\.CLIENT\s*\)|DistExecutor\.|FMLEnvironment\.dist\s*==\s*Dist\.CLIENT", text)
    if client_guard is not None:
        return []

    line_start = _line(text, client_import.start())
    return [
        _finding(
            root_cause="common-or-server-code-references-client-only-runtime-type",
            path=path,
            line_start=line_start,
            category="security",
            severity="blocker",
            message="Common/server code directly references a client-only runtime class and can fail class loading on a dedicated server.",
            evidence=(
                f"The file lives in a common/server source boundary, imports `{client_import.group('type')}`, and uses the type in "
                "runtime logic without a client-distribution gate. Dedicated-server class loading can therefore throw before the "
                "guarded operation completes, and repeated remote actions can repeatedly block the server loop."
            ),
            falsifiers=(
                "Excluded files located in an explicit client source boundary.",
                "Required both a client-only import and runtime use of that type.",
                "Checked for OnlyIn/DistExecutor/runtime distribution gating.",
            ),
            verification=(
                "Remove the client-only type from common/server code or isolate it behind a client-only adapter; prove dedicated-server "
                "startup and repeated remote menu actions without class-loading errors."
            ),
            supporting=(f"{path}:{_line(text, client_import.end() + runtime_use.start())}",),
            confidence=0.99,
        )
    ]


def _c_publication_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _C_SUFFIXES:
        return []

    findings: list[dict[str, Any]] = []
    guard_re = re.compile(
        r"if\s*\(\s*(?P<object>[A-Za-z_][A-Za-z0-9_]*)->(?P<flag>[A-Za-z_][A-Za-z0-9_]*(?:inited|initialized|ready|valid))\s*\)\s*(?:\{\s*)?return\s*;",
        re.I,
    )
    for guard in guard_re.finditer(text):
        obj = guard.group("object")
        flag = guard.group("flag")
        tail = text[guard.end() :]
        publish = re.search(
            rf"(?P<data>{re.escape(obj)}->(?!{re.escape(flag)}\b)[A-Za-z_][A-Za-z0-9_]*\s*=)[\s\S]{{0,5000}}?"
            rf"(?P<fence>(?:[A-Za-z_][A-Za-z0-9_]*memory_barrier|atomic_thread_fence|__sync_synchronize)\s*\([^;]*\)\s*;)[\s\S]{{0,800}}?"
            rf"(?P<flagwrite>{re.escape(obj)}->{re.escape(flag)}\s*=\s*(?:1|TRUE|true)\s*;)",
            tail,
            re.I,
        )
        if publish is None:
            continue
        context_start = max(0, guard.start() - 500)
        guard_context = text[context_start : guard.end()]
        acquire = re.search(
            r"atomic_load(?:_explicit)?\s*\([^;]*memory_order_acquire|load[_A-Za-z0-9]*acquire|__ldar\w*\s*\(|READ_ONCE\s*\(",
            guard_context,
            re.I,
        )
        if acquire is not None:
            continue

        line_start = _line(text, guard.start())
        findings.append(
            _finding(
                root_cause="publication-flag-read-without-acquire-semantics",
                path=path,
                line_start=line_start,
                category="concurrency",
                severity="blocker",
                message="A plain initialization-flag read can observe publication before the separately guarded data is visible on weak-memory architectures.",
                evidence=(
                    f"The fast path reads `{obj}->{flag}` directly and returns, while the publishing path writes other `{obj}` fields, "
                    "executes a memory barrier, and only then sets the flag. A release-side barrier without an acquire read does not "
                    "establish the required visibility ordering on weak-memory systems such as ARM64."
                ),
                falsifiers=(
                    "Required a fast-path read of an initialization/ready flag.",
                    "Required separate data writes followed by a release-side barrier and flag publication.",
                    "Checked the read path for atomic acquire/load-acquire semantics.",
                ),
                verification=(
                    "Read the publication flag with architecture-correct acquire semantics, preserve the release-side publication order, "
                    "and run the concurrent initialization reproducer on a weak-memory target."
                ),
                supporting=(
                    f"{path}:{_line(text, guard.end() + publish.start('data'))}",
                    f"{path}:{_line(text, guard.end() + publish.start('fence'))}",
                    f"{path}:{_line(text, guard.end() + publish.start('flagwrite'))}",
                ),
                confidence=0.99,
            )
        )
    return findings


def run_static_transfer_19_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    findings: list[dict[str, Any]] = []
    for path in changed:
        text = _safe_text(root_path, path)
        if not text:
            continue
        findings.extend(_go_repeat_registration_findings(path, text))
        findings.extend(_java_distribution_findings(path, text))
        findings.extend(_c_publication_findings(path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding.get("root_cause")), str(finding.get("path")), int(finding.get("line_start") or 0))] = finding

    return {
        "schema_version": "sergeant.static-transfer-19-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "executed_project_code": False,
    }
