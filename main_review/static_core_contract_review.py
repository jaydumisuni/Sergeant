"""Cross-language static contracts learned from blind external review.

These checks model source-level obligations that should be knowable before code is
executed.  They deliberately avoid repository names, exact bug-report strings and
provider/model assistance.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable


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
        if char in {"'", '"'}:
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


def _function_body(text: str, pattern: str) -> tuple[str, int] | None:
    match = re.search(pattern, text, re.M)
    if match is None:
        return None
    opening = text.find("{", match.start(), match.end())
    if opening < 0:
        return None
    closing = _matching_brace(text, opening)
    if closing is None:
        return None
    return text[opening + 1 : closing], opening + 1


def _finding(
    *,
    officer: str,
    capability: str,
    severity: str,
    root_cause: str,
    path: str,
    line_start: int,
    message: str,
    evidence: str,
    falsifiers: Iterable[str],
    verification: str,
    confidence: float,
    related_paths: Iterable[str] = (),
    supporting_refs: Iterable[str] = (),
) -> dict[str, Any]:
    return {
        "source": "static-core-contract-officer",
        "officer": officer,
        "capability": capability,
        "category": capability,
        "severity": severity,
        "root_cause": root_cause,
        "path": path,
        "line_start": line_start,
        "line_end": line_start,
        "evidence_ref": f"{path}:{line_start}",
        "related_paths": sorted({str(item) for item in related_paths if str(item)}),
        "supporting_evidence_refs": sorted({str(item) for item in supporting_refs if str(item)}),
        "message": message,
        "evidence": evidence,
        "falsifiers_checked": list(falsifiers),
        "verification_test": verification,
        "confidence": confidence,
        "direct_evidence": True,
        "admission_hint": "actionable",
    }


def _rust_sliced_shutdown_without_durable_intent(
    texts: dict[str, str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    sibling_controls: list[str] = []
    for path, text in texts.items():
        if Path(path).suffix.lower() != ".rs":
            continue
        if (
            "AtomicBool" in text
            and re.search(r"\b(?:stop|shutdown|cancel)[A-Za-z0-9_]*\.store\s*\(", text)
            and ".join()" in text
        ):
            match = re.search(r"\b(?:stop|shutdown|cancel)[A-Za-z0-9_]*\.store\s*\(", text)
            sibling_controls.append(f"{path}:{_line(text, match.start()) if match else 1}")

    for path, text in texts.items():
        if Path(path).suffix.lower() != ".rs":
            continue
        sliced = re.search(
            r"\bloop\s*\{[\s\S]{0,5000}?(?:run_in_mode|run_once|run_until|poll|recv_timeout)\s*\([\s\S]{0,600}?(?:Duration|from_millis|from_secs|timeout)",
            text,
            re.I,
        )
        if sliced is None:
            continue
        stop = _function_body(
            text,
            r"(?:pub(?:\([^)]*\))?\s+)?fn\s+(?:stop|shutdown|close|terminate)\s*\([^)]*\)\s*\{",
        )
        if stop is None:
            continue
        body, body_offset = stop
        if ".join()" not in body:
            continue
        if not re.search(r"\.(?:stop|wake|interrupt|unpark|notify_[A-Za-z0-9_]*)\s*\(", body):
            continue
        durable_request = bool(
            re.search(r"\.(?:store|send|cancel|close)\s*\(", body)
            or re.search(r"\b(?:AtomicBool|CancellationToken|Sender<|channel)\b", body)
        )
        loop_checks_request = bool(
            re.search(
                r"\b(?:stop|shutdown|cancel)[A-Za-z0-9_]*\s*\.\s*(?:load|is_cancelled|try_recv|recv|is_set)\s*\(",
                text[sliced.start() : sliced.end() + 5500],
                re.I,
            )
        )
        if durable_request or loop_checks_request:
            continue
        wake = re.search(r"\.(?:stop|wake|interrupt|unpark|notify_[A-Za-z0-9_]*)\s*\(", body)
        line_start = _line(text, body_offset + (wake.start() if wake else 0))
        findings.append(
            _finding(
                officer="Mechanic",
                capability="concurrency",
                severity="major",
                root_cause="sliced-loop-shutdown-without-durable-intent",
                path=path,
                line_start=line_start,
                message="A sliced worker loop relies on a transient wake/stop call and then joins without recording durable shutdown intent.",
                evidence=(
                    "The worker repeatedly re-enters a finite run/poll slice. Its shutdown function only wakes/stops the current slice and joins; "
                    "no atomic flag, cancellation token, channel state or loop condition records a stop request that lands between slices."
                ),
                falsifiers=(
                    "Checked for an atomic/cancellation flag stored before the wake call.",
                    "Checked for a channel send or other durable state transition consumed by the loop.",
                    "Checked whether the sliced loop tests shutdown intent before every re-entry.",
                ),
                verification=(
                    "Record shutdown intent before waking the worker, check it at every slice boundary, and prove a request arriving between slices cannot make join block indefinitely."
                ),
                confidence=0.97,
                supporting_refs=sibling_controls,
            )
        )
    return findings


def _proc_path_to_sysctl(path: str) -> str:
    prefix = "/proc/sys/"
    if not path.startswith(prefix):
        return ""
    return path[len(prefix) :].replace("/", ".")


def _privileged_runtime_state_without_authority(
    texts: dict[str, str],
) -> list[dict[str, Any]]:
    service_rows: list[tuple[str, str, int]] = []
    installers: list[tuple[str, str]] = []
    source_rows: list[tuple[str, str, str, int]] = []

    for path, text in texts.items():
        suffix = Path(path).suffix.lower()
        if suffix == ".service":
            user_match = re.search(r"(?m)^User\s*=\s*(?P<user>[^\s#]+)", text)
            if user_match and user_match.group("user").lower() not in {"root", "0"}:
                service_rows.append((path, text, _line(text, user_match.start())))
        if suffix in {".sh", ".bash"} or re.search(r"(?:^|/)(?:install|setup|bootstrap|deploy)[^/]*$", path, re.I):
            installers.append((path, text))
        for match in re.finditer(r"[\"'](?P<path>/proc/sys/[A-Za-z0-9_./-]+)[\"']", text):
            proc_path = match.group("path")
            nearby = text[max(0, match.start() - 700) : match.end() + 1800]
            if not re.search(r"(?:write|sysctl\b|set_|enable_)", nearby, re.I):
                continue
            source_rows.append((path, text, proc_path, _line(text, match.start())))

    findings: list[dict[str, Any]] = []
    for source_path, source_text, proc_path, source_line in source_rows:
        key = _proc_path_to_sysctl(proc_path)
        if not key:
            continue
        for service_path, service_text, service_line in service_rows:
            has_override = "CAP_DAC_OVERRIDE" in service_text
            writable = proc_path in service_text or "/proc/sys" in service_text
            if has_override or writable:
                continue
            source_explicitly_lacks_authority = bool(
                re.search(r"cannot\s+(?:open|write)|no\s+CAP_DAC_OVERRIDE|unprivileged", source_text, re.I)
                or ("tokio::fs::write" in source_text and "sysctl" in source_text)
            )
            if not source_explicitly_lacks_authority:
                continue
            established = False
            for _, installer_text in installers:
                if proc_path in installer_text or key in installer_text:
                    established = True
                    break
            if established:
                continue
            installer_paths = [path for path, _ in installers]
            primary_path = installer_paths[0] if installer_paths else source_path
            line_start = 1 if installer_paths else source_line
            findings.append(
                _finding(
                    officer="Engineer",
                    capability="deployment",
                    severity="major",
                    root_cause="required-privileged-state-not-established",
                    path=primary_path,
                    line_start=line_start,
                    message="Required privileged runtime state is delegated to a service that lacks authority, while installation does not establish it.",
                    evidence=(
                        f"{source_path}:{source_line} attempts to enable {key} through {proc_path}; {service_path}:{service_line} runs as a non-root user "
                        "without CAP_DAC_OVERRIDE or a writable proc-sys boundary, and no scoped installer establishes or persists that kernel state."
                    ),
                    falsifiers=(
                        "Checked whether the service runs as root or has the capability/write boundary needed for the state change.",
                        "Checked whether installation or startup writes the proc path, sysctl key, or a persistent sysctl.d entry.",
                        "Checked that the source attempts to change the state rather than only observing it.",
                    ),
                    verification=(
                        "Establish and persist the required state from a root-authorized install/startup boundary, then verify a fresh deployment satisfies it before dependent routing starts."
                    ),
                    confidence=0.98,
                    related_paths=(source_path, service_path, *installer_paths),
                    supporting_refs=(f"{source_path}:{source_line}", f"{service_path}:{service_line}"),
                )
            )
            break
    return findings


def _specialized_parser_behind_closed_gate(
    texts: dict[str, str],
) -> list[dict[str, Any]]:
    base_rows: list[tuple[str, str, int, set[str]]] = []
    subclasses: list[tuple[str, str]] = []

    for path, text in texts.items():
        suffix = Path(path).suffix.lower()
        if suffix not in {".kt", ".java"}:
            continue
        gate = re.search(
            r"(?:fun|boolean)\s+isTransactionMessage\s*\([^)]*\)[\s\S]{0,3000}?return\s+(?:transactionKeywords\.)?(?:any|stream|contains)",
            text,
            re.I,
        )
        parse_gate = re.search(
            r"(?:fun|[A-Za-z0-9_<>?]+)\s+parse\s*\([^)]*\)[\s\S]{0,900}?if\s*\(\s*!\s*isTransactionMessage\s*\([^)]*\)\s*\)[\s\S]{0,180}?return\s+null",
            text,
            re.I,
        )
        if gate and parse_gate:
            quoted = {
                item.lower()
                for item in re.findall(r"[\"']([A-Za-z][A-Za-z ]{2,30})[\"']", text[gate.start() : gate.end()])
            }
            base_rows.append((path, text, _line(text, parse_gate.start()), quoted))
        if re.search(r"class\s+[A-Za-z0-9_]+\s*:\s*[A-Za-z0-9_]*BankParser\s*\(", text):
            subclasses.append((path, text))

    findings: list[dict[str, Any]] = []
    for base_path, base_text, gate_line, _ in base_rows:
        balance_gate = bool(
            re.search(r"isBalanceUpdateNotification", base_text)
            and re.search(r"(?:available bal|avl bal|account balance)", base_text, re.I)
        )
        extensible_keywords = bool(
            re.search(r"(?:transactionKeywords|acceptedTransaction|isBankSpecificTransaction)\s*\(", base_text)
        )
        if extensible_keywords:
            continue
        for subclass_path, subclass_text in subclasses:
            if subclass_path == base_path:
                continue
            specialized = bool(
                re.search(r"override\s+fun\s+(?:extractAmount|extractTransactionType|extractMerchant)", subclass_text)
                and re.search(r"(?:transactions?|sender patterns?|-[A-Z]-?S\$|INDBNK-S)", subclass_text, re.I)
            )
            if not specialized:
                continue
            if re.search(r"override\s+fun\s+isTransactionMessage\s*\(", subclass_text):
                continue
            findings.append(
                _finding(
                    officer="Engineer",
                    capability="contracts",
                    severity="major",
                    root_cause="specialized-parser-blocked-by-closed-global-gate",
                    path=base_path,
                    line_start=gate_line,
                    message="A specialized parser cannot extend the global recognition gate that runs before its bank-specific extraction logic.",
                    evidence=(
                        f"{base_path}:{gate_line} returns null before extraction when a fixed global transaction-keyword gate rejects input. "
                        f"{subclass_path} defines bank-specific sender and extraction behavior but does not override or extend that gate"
                        + ("; a separate closed balance-only classifier can also claim bank-local variants." if balance_gate else ".")
                    ),
                    falsifiers=(
                        "Checked for a subclass override of isTransactionMessage.",
                        "Checked for an overridable keyword/capability hook used by the base gate.",
                        "Checked that the subclass actually supplies bank-specific extraction or classification behavior.",
                    ),
                    verification=(
                        "Make recognition extensible at the bank parser boundary and add positive and negative fixtures proving bank-local transaction variants reach extraction without turning balance-only or promotional messages into transactions."
                    ),
                    confidence=0.92,
                    related_paths=(subclass_path,),
                    supporting_refs=(f"{base_path}:{gate_line}", f"{subclass_path}:1"),
                )
            )
            break
    return findings


def run_static_core_contract_review(
    root: str | Path, changed_files: Iterable[str]
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    texts = {path: _safe_text(root_path, path) for path in changed}
    texts = {path: text for path, text in texts.items() if text}

    findings = [
        *_rust_sliced_shutdown_without_durable_intent(texts),
        *_privileged_runtime_state_without_authority(texts),
        *_specialized_parser_behind_closed_gate(texts),
    ]
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for finding in findings:
        unique[(str(finding["root_cause"]), str(finding["path"]))] = finding
    return {
        "schema_version": "sergeant.static-core-contract-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "reviewed_files": sorted(texts),
        "executed_project_code": False,
    }
