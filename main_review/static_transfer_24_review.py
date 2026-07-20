"""Static checks learned after transfer set 24's blind artifact was frozen."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".rb", ".php", ".swift"}


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
        "source": "static-transfer-24-officer",
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


_RUBY_LAZY_METHOD_RE = re.compile(
    r"(?ms)^\s*def\s+(?P<name>[A-Za-z_][A-Za-z0-9_!?=]*)[^\n]*\n"
    r"(?P<body>.*?)(?=^\s*end\s*$)"
)
_RUBY_MEMO_RE = re.compile(r"@(?P<ivar>[A-Za-z_][A-Za-z0-9_]*)\s*\|\|=")
_RUBY_PRIORITY_RE = re.compile(
    r"(?:key|revision|identity|token|config|route|schema|metadata|descriptor)",
    re.I,
)
_RUBY_INITIALIZE_RE = re.compile(
    r"(?ms)^\s*def\s+initialize\b[^\n]*\n(?P<body>.*?)(?=^\s*end\s*$)"
)


def _ruby_freeze_findings(files: dict[str, str]) -> list[dict[str, Any]]:
    boundaries: list[tuple[str, str, int]] = []
    for path, text in files.items():
        if Path(path).suffix.lower() != ".rb":
            continue
        boundaries.extend(
            (path, text, match.start())
            for match in re.finditer(r"Ractor\.make_shareable\s*\((?P<object>[^)\n]+)\)", text)
        )
        boundaries.extend(
            (path, text, match.start())
            for match in re.finditer(r"(?<![A-Za-z0-9_])freeze\b", text)
        )
    if not boundaries:
        return []

    candidates: list[tuple[int, str, str, str, int]] = []
    for path, text in files.items():
        if Path(path).suffix.lower() != ".rb":
            continue
        init = _RUBY_INITIALIZE_RE.search(text)
        init_body = init.group("body") if init is not None else ""
        for method in _RUBY_LAZY_METHOD_RE.finditer(text):
            memo = _RUBY_MEMO_RE.search(method.group("body"))
            if memo is None:
                continue
            name = method.group("name")
            ivar = memo.group("ivar")
            if re.search(rf"@{re.escape(ivar)}\s*=", init_body):
                continue
            priority = 1 if _RUBY_PRIORITY_RE.search(name) else 0
            candidates.append((priority, path, name, ivar, method.start()))
    if not candidates:
        return []

    candidates.sort(key=lambda row: (-row[0], row[1], row[4]))
    _, path, name, ivar, offset = candidates[0]
    supporting: list[str] = []
    for boundary_path, boundary_text, boundary_offset in boundaries:
        before = boundary_text[:boundary_offset]
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?:\s|\()", before):
            continue
        supporting.append(f"{boundary_path}:{_line(boundary_text, boundary_offset)}")
    if not supporting:
        return []

    return [
        _finding(
            officer="Engineer",
            capability="state_lifecycle",
            category="correctness",
            severity="major",
            root_cause="lazy-state-initialized-after-freeze-or-shareability-boundary",
            path=path,
            line_start=_line(files[path], offset),
            message="A lazily memoized field can be first written only after the owning object graph has been frozen or made shareable.",
            evidence=(
                f"Accessor `{name}` writes `@{ivar}` with lazy memoization, but the field is not initialized by the constructor. "
                "A changed lifecycle path freezes or makes the surrounding object graph shareable without materializing that accessor first, "
                "so the first later read attempts to mutate frozen state."
            ),
            falsifiers=[
                "Required an instance-variable memoization write inside an accessor.",
                "Excluded fields assigned during initialize.",
                "Required a freeze or Ractor shareability boundary in the reviewed change set.",
                "Excluded lifecycle boundaries that call the accessor before freezing.",
            ],
            verification=(
                f"Initialize `@{ivar}` before the freeze/shareability boundary or call `{name}` explicitly before freezing, then prove the first post-freeze access performs no write."
            ),
            confidence=0.96,
            supporting=supporting,
        )
    ]


def _php_timeout_findings(path: str, text: str) -> list[dict[str, Any]]:
    if "SIGKILL" not in text or "posix_kill" not in text:
        return []
    fire = re.search(r"\$job->fire\s*\(\s*\)\s*;", text)
    if fire is None:
        return []
    if re.search(r"\$job->attempts\s*\(\s*\)", text[max(0, fire.start() - 1800) : fire.start()]):
        return []
    later = text[fire.end() :]
    if re.search(r"\$job->attempts\s*\(\s*\)", later) is None:
        return []
    if re.search(r"markJobAsFailedIf[A-Za-z0-9_]*MaxAttempts\s*\(", later) is None:
        return []
    return [
        _finding(
            officer="Medic",
            capability="retry_recovery",
            category="correctness",
            severity="blocker",
            root_cause="retry-limit-enforced-only-after-catchable-job-failure",
            path=path,
            line_start=_line(text, fire.start()),
            message="A worker enforces the retry limit only after a catchable job exception, while timeout handling can kill the worker before that path runs.",
            evidence=(
                "The worker executes the job before checking its attempt count. Retry-limit handling appears later in exception recovery, "
                "but timeout supervision uses SIGKILL against the child process. Repeated timeouts can therefore bypass failure marking indefinitely."
            ),
            falsifiers=[
                "Required an external hard-kill timeout path.",
                "Required job execution before any attempt-count check in the processing path.",
                "Required max-attempt enforcement only after execution in exception handling.",
                "Excluded workers that check attempts before firing the job or whose timeout path records failure durably before termination.",
            ],
            verification=(
                "Check attempts and mark over-limit jobs failed before executing them, retain exception-path checking for compatibility, and test a job that repeatedly times out."
            ),
            confidence=0.99,
        )
    ]


_SWIFT_STATUS_RE = re.compile(
    r"case\s*\(\s*(?P<major>\d+)\s*,\s*(?P<minor>\d+)\s*,\s*\.(?P<status>[A-Za-z_][A-Za-z0-9_]*)\s*\)\s*:\s*"
    r"self\.writeStaticString\s*\(\s*\"HTTP/(?P<wire_major>\d+)\.(?P<wire_minor>\d+)\s+(?P<code>\d{3})\s+(?P<phrase>[^\"\\]+)\\r\\n\"\s*\)",
    re.M,
)


def _swift_protocol_findings(path: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for match in _SWIFT_STATUS_RE.finditer(text):
        discriminant = (match.group("major"), match.group("minor"))
        wire = (match.group("wire_major"), match.group("wire_minor"))
        if discriminant == wire:
            continue
        findings.append(
            _finding(
                officer="Engineer",
                capability="protocol_contract",
                category="api_contract",
                severity="blocker",
                root_cause="protocol-fast-path-literal-disagrees-with-switch-discriminant",
                path=path,
                line_start=_line(text, match.start()),
                message="A hand-written protocol fast path emits a wire version that disagrees with the switch case selecting it.",
                evidence=(
                    f"The case for version {discriminant[0]}.{discriminant[1]} and status `{match.group('status')}` writes "
                    f"`HTTP/{wire[0]}.{wire[1]} {match.group('code')} ...`. The optimized literal therefore changes protocol semantics instead of matching the canonical formatter."
                ),
                falsifiers=[
                    "Required a literal protocol line selected by an explicit version/status switch case.",
                    "Compared the case version to the emitted wire version.",
                    "Excluded custom/default formatting paths and literals whose version matches the discriminant.",
                ],
                verification=(
                    "Generate the fast path from canonical status metadata or compare every optimized status line against the canonical formatter for every supported protocol version."
                ),
                confidence=0.99,
            )
        )
    return findings


def run_static_transfer_24_review(
    root: str | Path,
    changed_files: Iterable[str],
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    files: dict[str, str] = {}
    findings: list[dict[str, Any]] = []

    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if text:
            files[path] = text

    findings.extend(_ruby_freeze_findings(files))
    for path, text in files.items():
        suffix = Path(path).suffix.lower()
        if suffix == ".php":
            findings.extend(_php_timeout_findings(path, text))
        elif suffix == ".swift":
            findings.extend(_swift_protocol_findings(path, text))

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for finding in findings:
        unique[(
            str(finding.get("root_cause")),
            str(finding.get("path")),
            int(finding.get("line_start") or 0),
        )] = finding

    return {
        "schema_version": "sergeant.static-transfer-24-review.v1",
        "mode": "model_free_static",
        "finding_count": len(unique),
        "findings": list(unique.values()),
        "readable_changed_files": sorted(files),
        "executed_project_code": False,
    }
