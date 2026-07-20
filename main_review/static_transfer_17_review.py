"""Static checks learned only after transfer set 17's blind 0/3 was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_PYTHON_SUFFIXES = {".py"}
_GO_SUFFIXES = {".go"}
_KOTLIN_SUFFIXES = {".kt", ".kts"}


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
        "source": "static-transfer-17-officer",
        "officer": "Mechanic" if category in {"concurrency", "lifecycle", "durability"} else "Engineer",
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


def _payload_quality_findings(texts: dict[str, str]) -> list[dict[str, Any]]:
    corpus = "\n".join(texts.values())
    if re.search(r"m\.room\.encrypted|opaque|ciphertext|decrypt", corpus, re.I) is None:
        return []

    findings: list[dict[str, Any]] = []
    upsert_re = re.compile(
        r"INSERT\s+INTO\s+(?P<table>[A-Za-z_][A-Za-z0-9_]*)[\s\S]{0,1400}?"
        r"ON\s+CONFLICT[\s\S]{0,900}?DO\s+UPDATE\s+SET[\s\S]{0,700}?"
        r"(?P<column>event_json|payload|content|body)\s*=\s*excluded\.(?P=column)",
        re.I,
    )
    for path, text in texts.items():
        if Path(path).suffix.lower() not in _PYTHON_SUFFIXES:
            continue
        for match in upsert_re.finditer(text):
            local = text[match.start() : min(len(text), match.end() + 900)]
            guarded = bool(
                re.search(r"\bWHERE\b[\s\S]{0,700}(?:encrypted|opaque|ciphertext|quality|accepted)", local, re.I)
                or re.search(r"RETURNING\s+(?:event_id|id)", local, re.I)
            )
            if guarded:
                continue
            derived = re.search(
                r"DELETE\s+FROM\s+(?:event_[A-Za-z0-9_]+|[A-Za-z0-9_]*(?:index|reference|thread|edit)[A-Za-z0-9_]*)"
                r"[\s\S]{0,1800}?(?:serialized_events|event_ids)",
                text[match.end() : match.end() + 7000],
                re.I,
            )
            supporting = ()
            if derived is not None:
                supporting = (f"{path}:{_line(text, match.end() + derived.start())}",)
            findings.append(
                _finding(
                    root_cause="lower-quality-payload-can-overwrite-higher-quality-cache-entry",
                    path=path,
                    line_start=_line(text, match.start()),
                    category="durability",
                    severity="blocker",
                    message="A quality-sensitive cached payload is replaced unconditionally by the latest arrival.",
                    evidence=(
                        f"The `{match.group('table')}` conflict clause replaces `{match.group('column')}` with the incoming "
                        "payload without an atomic quality predicate. The reviewed cache handles opaque/encrypted and clear "
                        "representations of the same identity, so a later lower-quality envelope can destroy previously clear "
                        "content; derived indexes may then be reconciled from the rejected-quality arrival."
                    ),
                    falsifiers=(
                        "Required reviewed source evidence of clear/decrypted versus opaque/encrypted payload quality.",
                        "Checked the conflict update for an atomic predicate that refuses quality downgrade.",
                        "Checked for RETURNING/accepted-row filtering before derived index reconciliation.",
                    ),
                    verification=(
                        "Make payload quality monotonic inside the database conflict clause, update derived indexes only for "
                        "accepted payloads, and prove both arrival orders converge on the higher-quality representation."
                    ),
                    supporting=supporting,
                )
            )
    return findings


def _go_connection_and_revision_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _GO_SUFFIXES:
        return []
    findings: list[dict[str, Any]] = []

    function_re = re.compile(
        r"func\s*(?:\([^)]*\)\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)[^{]*\{",
        re.M,
    )
    for function in function_re.finditer(text):
        opening = text.find("{", function.start())
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        reserved = re.search(
            r"(?P<conn>[A-Za-z_][A-Za-z0-9_]*)\s*,\s*(?:err|error)\s*:=\s*"
            r"[A-Za-z_][A-Za-z0-9_.]*\.Conn\s*\(",
            body,
        )
        if reserved is not None:
            conn = reserved.group("conn")
            if re.search(rf"\b{re.escape(conn)}\.PrepareContext\s*\(", body) and not re.search(
                rf"(?:defer\s+)?{re.escape(conn)}\.Close\s*\(", body
            ):
                findings.append(
                    _finding(
                        root_cause="reserved-db-connection-escapes-through-prepared-statement",
                        path=path,
                        line_start=_line(text, opening + 1 + reserved.start()),
                        category="lifecycle",
                        severity="major",
                        message="A database connection reserved for statement preparation is never returned to the pool.",
                        evidence=(
                            f"`{function.group('name')}` acquires `{conn}` with `DB.Conn`, prepares through that connection, "
                            "and returns the statement without closing the reserved connection. Repeated preparation can "
                            "consume the pool even when callers later close the statement."
                        ),
                        falsifiers=(
                            "Checked the function for defer conn.Close or explicit conn.Close on all successful paths.",
                            "Distinguished DB.Conn().PrepareContext from DB.PrepareContext, which leaves pooling to database/sql.",
                            "Required the prepared statement or wrapper to escape the function."
                        ),
                        verification=(
                            "Prepare through DB.PrepareContext or bind connection ownership to a closeable wrapper, then prove "
                            "repeated prepare/close cycles leave zero connections reserved."
                        ),
                    )
                )

        if function.group("name") == "Append" and re.search(r"\.Insert\s*\(", body):
            revision = bool(re.search(r"currentRev\s*:=\s*[^\n]*currentRev\.Load\s*\(", body))
            one_shot = bool(re.search(r"currentRev\.CompareAndSwap\s*\(", body))
            serialized = bool(
                re.search(r"(?:appendMu|writeMu|commitMu|serialMu)\.Lock\s*\(", body)
                or re.search(r"\bs\.Lock\s*\(", body)
            )
            retry_cas = bool(re.search(r"for\s+[^\n{]*CompareAndSwap|for\s*\{[\s\S]{0,500}CompareAndSwap", body))
            if revision and one_shot and not serialized and not retry_cas:
                insert = re.search(r"\.Insert\s*\(", body)
                findings.append(
                    _finding(
                        root_cause="revision-allocating-append-is-not-serialized-through-commit-publication",
                        path=path,
                        line_start=_line(text, opening + 1 + (insert.start() if insert else 0)),
                        category="concurrency",
                        severity="blocker",
                        message="Concurrent appends can publish committed revisions out of order and leave the visible revision stale.",
                        evidence=(
                            "`Append` reads the current revision, enters the dialect insert without a dedicated serialization "
                            "boundary, and performs only one CompareAndSwap afterward. A database may allocate revision IDs when "
                            "inserts begin but commit transactions in a different order, creating gaps and allowing the one-shot "
                            "CAS to leave the in-memory revision behind a committed write."
                        ),
                        falsifiers=(
                            "Checked for a dedicated append/write/commit mutex covering the dialect insert and publication.",
                            "Checked for a retrying monotonic CAS loop rather than a one-shot swap.",
                            "Required a revision-bearing append path with Insert, currentRev load and notification semantics."
                        ),
                        verification=(
                            "Serialize the shared append boundary through commit, update current revision monotonically with a "
                            "retry loop, always notify the poller after commit, and reproduce two inserts whose commits finish out of order."
                        ),
                    )
                )
    return findings


def _kotlin_unpublished_collection_findings(path: str, text: str) -> list[dict[str, Any]]:
    if Path(path).suffix.lower() not in _KOTLIN_SUFFIXES:
        return []
    function_re = re.compile(
        r"(?:private\s+|internal\s+|public\s+)?fun\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^)]*)\)[^{=]*\{",
        re.M,
    )
    findings: list[dict[str, Any]] = []
    for function in function_re.finditer(text):
        params = function.group("params")
        model_match = re.search(r"(?P<model>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*[A-Za-z_][A-Za-z0-9_.<>?]*", params)
        if model_match is None:
            continue
        model = model_match.group("model")
        opening = text.find("{", function.start())
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        body = text[opening + 1 : closing]
        local = re.search(
            r"val\s+(?P<list>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*mutableListOf\s*<(?P<type>[A-Za-z_][A-Za-z0-9_.]*)>\s*\(\s*\)",
            body,
        )
        if local is None:
            continue
        collection = local.group("list")
        if re.search(rf"\b{re.escape(collection)}\.(?:add|addAll)\s*\(", body) is None:
            continue
        published = bool(
            re.search(rf"\b{re.escape(model)}\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^\n;]*\b{re.escape(collection)}\b", body)
            or re.search(rf"\b{re.escape(model)}\.[A-Za-z_][A-Za-z0-9_]*\.(?:add|addAll)\s*\([^)]*\b{re.escape(collection)}\b", body)
            or re.search(rf"\b{re.escape(model)}\.[A-Za-z_][A-Za-z0-9_]*\s*=\s*\b{re.escape(model)}\.[A-Za-z_][A-Za-z0-9_]*\.plus\s*\(\s*{re.escape(collection)}\s*\)", body)
            or re.search(rf"\breturn\s+{re.escape(collection)}\b", body)
        )
        if published:
            continue
        findings.append(
            _finding(
                root_cause="derived-collection-built-but-never-published-to-target",
                path=path,
                line_start=_line(text, opening + 1 + local.start()),
                category="api_contract",
                severity="major",
                message="A derived collection is populated but never committed to the target model or returned.",
                evidence=(
                    f"`{function.group('name')}` builds and populates local `{collection}` from source media/data, but the "
                    f"function neither assigns or appends it to `{model}`, nor returns it. Separate extraction helpers can "
                    "therefore discard one another's output or silently lose the derived items."
                ),
                falsifiers=(
                    "Checked for assignment or add/addAll from the local collection into the target model.",
                    "Checked for accumulation with target.property.plus(localCollection).",
                    "Checked whether the local collection is returned to the caller."
                ),
                verification=(
                    "Publish the derived items exactly once through an accumulation contract, preserve items already attached "
                    "by other extraction paths, and test combined photo plus embedded image/video inputs."
                ),
            )
        )
    return findings


def run_static_transfer_17_review(root: str | Path, changed_files: Iterable[str]) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    texts = {path: _safe_text(root_path, path) for path in changed}
    texts = {path: text for path, text in texts.items() if text}

    findings: list[dict[str, Any]] = []
    findings.extend(_payload_quality_findings(texts))
    for path, text in texts.items():
        findings.extend(_go_connection_and_revision_findings(path, text))
        findings.extend(_kotlin_unpublished_collection_findings(path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding.get("root_cause")), str(finding.get("path")), int(finding.get("line_start") or 0))] = finding

    return {
        "schema_version": "sergeant.static-transfer-17-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "executed_project_code": False,
    }
