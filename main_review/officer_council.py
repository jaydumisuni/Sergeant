"""Deterministic permanent-officer council beneath Sergeant.

This module is intentionally useful when every model route is disabled.  Permanent
Sergeant officers own executable doctrine, evidence collection and challenge rules;
optional models may later amplify the same reports but are never required for the
baseline council to produce a grounded engineering verdict.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


SEVERITY_RANK = {"note": 0, "minor": 1, "major": 2, "blocker": 3}


@dataclass(frozen=True)
class OfficerFinding:
    officer: str
    rule_id: str
    severity: str
    category: str
    path: str
    line_start: int
    line_end: int
    message: str
    evidence: str
    why_it_matters: str
    safer_alternative: str
    confidence: float = 0.95

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class OfficerReport:
    officer: str
    role: str
    mission: str
    findings: list[OfficerFinding] = field(default_factory=list)
    evidence: list[dict[str, object]] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    coverage: list[str] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        severities = {item.severity for item in self.findings}
        if "blocker" in severities:
            return "BLOCK"
        if "major" in severities:
            return "NEEDS WORK"
        return "PASS"

    def to_dict(self) -> dict[str, object]:
        return {
            "officer": self.officer,
            "role": self.role,
            "mission": self.mission,
            "verdict": self.verdict,
            "findings": [item.to_dict() for item in self.findings],
            "evidence": self.evidence,
            "questions": self.questions,
            "coverage": sorted(set(self.coverage)),
            "model_required": False,
        }


OFFICER_DOCTRINE: dict[str, tuple[str, str]] = {
    "Scout": (
        "Repository Reconnaissance",
        "Map changed surfaces, exact evidence anchors, file classes and high-risk review lanes.",
    ),
    "Quartermaster": (
        "Proof and Resource Control",
        "Check proof coverage, authorization, bounded work and resource-governance contracts.",
    ),
    "Engineer": (
        "Technical Construction",
        "Validate workflow, API, schema, configuration and compatibility contracts.",
    ),
    "Medic": (
        "Security and Trust Boundaries",
        "Inspect credentials, untrusted input, dangerous sinks, path containment and authorization.",
    ),
    "Mechanic": (
        "Runtime and State Reliability",
        "Inspect atomicity, concurrency, retry, reset, lifecycle and persistent-state behavior.",
    ),
    "Analyst": (
        "Evidence and Quality Analysis",
        "Check test-to-contract coverage, result consistency and review-proof completeness.",
    ),
    "Challenger": (
        "Independent Falsification",
        "Attack clean verdicts and proposed findings with boundary cases and missing-proof checks.",
    ),
    "Judge": (
        "Evidence Admission and Verdict",
        "Merge root causes, reject unsupported duplication and assign verdict effect.",
    ),
    "Archivist": (
        "Verified Experience",
        "Retrieve recurrence evidence and preserve accepted rules, misses and prevention lessons.",
    ),
}


@dataclass(frozen=True)
class SourceFile:
    path: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()


def _safe_source_files(root: Path, changed_files: Iterable[str]) -> list[SourceFile]:
    resolved_root = root.resolve()
    sources: list[SourceFile] = []
    for relative in dict.fromkeys(str(item).strip() for item in changed_files if str(item).strip()):
        candidate = Path(relative)
        if candidate.is_absolute():
            continue
        try:
            resolved = (resolved_root / candidate).resolve()
            if not resolved.is_relative_to(resolved_root) or not resolved.is_file():
                continue
            data = resolved.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:4096]:
            continue
        sources.append(SourceFile(relative.replace("\\", "/"), data.decode("utf-8", errors="replace")))
    return sources


def _line_for(source: SourceFile, needle: str, *, default: int = 1) -> int:
    for number, line in enumerate(source.lines, start=1):
        if needle in line:
            return number
    return default


def _excerpt(source: SourceFile, start: int, end: int | None = None) -> str:
    lines = source.lines
    if not lines:
        return ""
    start = max(1, min(start, len(lines)))
    end = max(start, min(end or start, len(lines)))
    return "\n".join(lines[start - 1 : end])[:1200]


def _add(
    report: OfficerReport,
    source: SourceFile,
    *,
    rule_id: str,
    severity: str,
    category: str,
    line: int,
    message: str,
    why: str,
    safer: str,
    end_line: int | None = None,
) -> None:
    report.findings.append(
        OfficerFinding(
            officer=report.officer,
            rule_id=rule_id,
            severity=severity,
            category=category,
            path=source.path,
            line_start=line,
            line_end=end_line or line,
            message=message,
            evidence=_excerpt(source, line, end_line),
            why_it_matters=why,
            safer_alternative=safer,
        )
    )


def _report(name: str) -> OfficerReport:
    role, mission = OFFICER_DOCTRINE[name]
    return OfficerReport(name, role, mission)


def _scan_scout(sources: list[SourceFile]) -> OfficerReport:
    report = _report("Scout")
    suffix_counts: dict[str, int] = {}
    high_risk: list[str] = []
    for source in sources:
        suffix = Path(source.path).suffix.lower() or "<none>"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
        lowered = source.path.lower()
        if lowered.startswith(".github/workflows/") or any(
            token in lowered for token in ("auth", "security", "credential", "provider", "gateway", "migration")
        ):
            high_risk.append(source.path)
        report.coverage.append(source.path)
    report.evidence.extend(
        [
            {"kind": "changed_file_count", "value": len(sources)},
            {"kind": "file_types", "value": suffix_counts},
            {"kind": "high_risk_surfaces", "value": sorted(high_risk)},
        ]
    )
    return report


def _workflow_source(sources: list[SourceFile]) -> SourceFile | None:
    return next(
        (item for item in sources if item.path == ".github/workflows/cloudflare-full-council-certification.yml"),
        None,
    )


def _scan_quartermaster(sources: list[SourceFile]) -> OfficerReport:
    report = _report("Quartermaster")
    workflow = _workflow_source(sources)
    incremental_test = next(
        (item for item in sources if item.path == "tests/test_cloudflare_incremental_certification.py"),
        None,
    )
    if workflow is not None and incremental_test is not None:
        path_trigger_present = "tests/test_cloudflare_incremental_certification.py" in workflow.text
        focused_command = next(
            (line for line in workflow.lines if "pytest" in line and "cloudflare" in line),
            "",
        )
        command_present = "test_cloudflare_incremental_certification.py" in focused_command
        if not path_trigger_present or not command_present:
            line = _line_for(workflow, "paths:")
            _add(
                report,
                workflow,
                rule_id="proof-test-not-enforced",
                severity="major",
                category="tests",
                line=line,
                message="The certification workflow does not fully enforce its incremental-ledger regression suite.",
                why=(
                    "A changed or broken resumable ledger can pass the focused certification workflow even though "
                    "the assurance contract says that behavior is a merge requirement."
                ),
                safer=(
                    "Trigger this workflow when the incremental certification test changes and include that test "
                    "module in the focused pytest command."
                ),
            )
    report.coverage.extend(item.path for item in sources if item.path.startswith((".github/", "tests/", "docs/")))
    return report


def _scan_engineer(sources: list[SourceFile]) -> OfficerReport:
    report = _report("Engineer")
    workflow = _workflow_source(sources)
    if workflow is not None:
        gate_region = "\n".join(workflow.lines[-45:])
        if "payload.get('passed')" in gate_region or 'payload.get("passed")' in gate_region:
            exact_roster_gate = bool(
                re.search(r"set\s*\(\s*payload\.get\(['\"]certified_models", gate_region)
                and re.search(r"required|expected", gate_region, flags=re.IGNORECASE)
            )
            if not exact_roster_gate:
                line = _line_for(workflow, "Enforce all-member certification")
                _add(
                    report,
                    workflow,
                    rule_id="exact-roster-not-enforced",
                    severity="major",
                    category="api_contract",
                    line=line,
                    message="The final certification gate trusts the summary boolean without independently enforcing the exact roster.",
                    why="A smaller or substituted model set can be accepted if upstream summary construction changes or is corrupted.",
                    safer="Assert set(certified_models) equals the exact required seven model IDs before accepting passed=true.",
                )

    cli = next((item for item in sources if item.path == "main_review/cloudflare_cli.py"), None)
    if cli is not None:
        if 'for key in ("required", "result")' in cli.text or "for key in ('required', 'result')" in cli.text:
            line = _line_for(cli, 'for key in ("required", "result")')
            _add(
                report,
                cli,
                rule_id="prompt-echo-can-pass-proof",
                severity="major",
                category="correctness",
                line=line,
                message="Structured transport proof accepts the requested answer embedded in the prompt.",
                why="A model can echo the instruction's required object and pass without producing a genuine response contract.",
                safer="Validate only the top-level response or a genuine provider result envelope; never accept the prompt's required object.",
            )

    provider = next((item for item in sources if item.path == "main_review/llm_provider.py"), None)
    if provider is not None:
        size_tie = "len(json.dumps(payload" in provider.text and "max(objects, key=_json_candidate_score)" in provider.text
        if size_tie:
            line = _line_for(provider, "def _json_candidate_score")
            _add(
                report,
                provider,
                rule_id="verbose-json-beats-final-answer",
                severity="major",
                category="correctness",
                line=line,
                message="Recovered JSON candidates use serialized size as a tie-breaker instead of preferring the later final answer.",
                why="An earlier verbose example or reasoning object can beat a later schema-equivalent final response and certify the wrong payload.",
                safer="Score contract keys first and break equal-schema ties by later source position.",
            )
    report.coverage.extend(item.path for item in sources if item.path.endswith((".py", ".yml", ".yaml")))
    return report


def _scan_medic(sources: list[SourceFile]) -> OfficerReport:
    report = _report("Medic")
    workflow = _workflow_source(sources)
    if workflow is not None:
        has_secret_env = "secrets.SERGEANT_CLOUDFLARE" in workflow.text
        executes_head = all(token in workflow.text for token in ("actions/checkout", "pip install -e ."))
        protected_environment = bool(re.search(r"^\s*environment:\s*", workflow.text, flags=re.MULTILINE))
        if has_secret_env and executes_head and not protected_environment:
            line = _line_for(workflow, "SERGEANT_CLOUDFLARE_ACCOUNT_ID")
            _add(
                report,
                workflow,
                rule_id="pr-head-executes-with-provider-secrets",
                severity="blocker",
                category="security",
                line=line,
                message="Pull-request-controlled code executes in the same job that receives Cloudflare credentials.",
                why=(
                    "Checkout, installation, tests and the certification module can access job-level secrets; scanning emitted artifacts "
                    "cannot prove the code did not read or exfiltrate those credentials."
                ),
                safer=(
                    "Separate untrusted PR-head validation from live inference. Run the secret-bearing step from trusted code behind a "
                    "protected environment or explicit approval boundary, and correct the assurance claim."
                ),
            )

    cli = next((item for item in sources if item.path == "main_review/cloudflare_cli.py"), None)
    if cli is not None:
        ambiguous_markers = any(f'"{token}"' in cli.text for token in ("auth", "rce"))
        raw_match = "marker in area" in cli.text
        if ambiguous_markers and raw_match:
            line = _line_for(cli, "marker in area")
            _add(
                report,
                cli,
                rule_id="security-marker-substring-collision",
                severity="major",
                category="security",
                line=line,
                message="Security coverage accepts ambiguous raw substrings.",
                why="Short markers such as rce and auth can match unrelated words including source or authoring and falsely satisfy the gate.",
                safer="Use explicit security phrases and bounded token/word matching.",
            )

    scout = next((item for item in sources if item.path == "main_review/cloudflare_scout_qualification.py"), None)
    if scout is not None:
        joins_untrusted = "Path(root) / file" in scout.text
        contains_guard = ".relative_to(" in scout.text or ".is_relative_to(" in scout.text
        if joins_untrusted and not contains_guard:
            line = _line_for(scout, "Path(root) / file")
            _add(
                report,
                scout,
                rule_id="scout-path-escapes-root",
                severity="major",
                category="security",
                line=line,
                message="Scout qualification can read a fixture outside the declared root before transmitting its contents.",
                why="An absolute path or parent traversal can expose unrelated local files to the external provider.",
                safer="Resolve root and candidate paths, reject absolute input, and require candidate.relative_to(root) before reading.",
            )
    report.coverage.extend(item.path for item in sources if any(token in item.path.lower() for token in ("workflow", "provider", "scout", "auth")))
    return report


def _scan_mechanic(sources: list[SourceFile]) -> OfficerReport:
    report = _report("Mechanic")
    incremental = next((item for item in sources if item.path == "main_review/cloudflare_incremental_certification.py"), None)
    if incremental is not None:
        has_budget_flag = '"budget_blocked"' in incremental.text
        has_budget_day = '"budget_blocked_day"' in incremental.text
        if has_budget_flag and not has_budget_day:
            line = _line_for(incremental, '"budget_blocked"')
            _add(
                report,
                incremental,
                rule_id="budget-block-never-expires",
                severity="major",
                category="correctness",
                line=line,
                message="A local-budget block is persisted without the UTC day that owns it.",
                why="Later runs can remain permanently blocked even after the daily budget resets.",
                safer="Persist budget_blocked_day and clear both fields when loading state on a later UTC day.",
            )

    usage = next((item for item in sources if item.path == "main_review/cloudflare_usage.py"), None)
    if usage is not None:
        local_lock = "threading" in usage.text and "_STATE_LOCK" in usage.text
        shared_tmp = 'with_suffix(path.suffix + ".tmp")' in usage.text or 'with_name(path.name + ".tmp")' in usage.text
        if local_lock and shared_tmp:
            line = _line_for(usage, "_STATE_LOCK")
            _add(
                report,
                usage,
                rule_id="usage-reservation-not-process-atomic",
                severity="major",
                category="concurrency",
                line=line,
                message="Cloudflare usage reservations are atomic only inside one Python process.",
                why="Concurrent CLI, IDE or CI processes can reserve from the same stale total or race on one shared temporary file.",
                safer="Hold an inter-process file lock across load-modify-save and write through a unique temporary file before atomic replace.",
            )

    provider = next((item for item in sources if item.path == "main_review/llm_provider.py"), None)
    if provider is not None:
        broad_429 = bool(re.search(r"http[_ ]429", provider.text, flags=re.IGNORECASE))
        quota_function = "is_cloudflare_quota_error" in provider.text
        if broad_429 and quota_function:
            line = _line_for(provider, "def is_cloudflare_quota_error")
            _add(
                report,
                provider,
                rule_id="transient-429-opens-daily-circuit",
                severity="major",
                category="correctness",
                line=line,
                message="Generic HTTP 429 is classified as daily Cloudflare allocation exhaustion.",
                why="A transient throttle can open the circuit until the next UTC day and unnecessarily disable the provider route.",
                safer="Open the daily circuit only for provider code 4006 or explicit daily-allocation/quota markers; propagate other 429 responses normally.",
            )
    report.coverage.extend(item.path for item in sources if any(token in item.path for token in ("usage", "incremental", "provider")))
    return report


def _scan_analyst(sources: list[SourceFile], reports: list[OfficerReport]) -> OfficerReport:
    report = _report("Analyst")
    by_rule = [finding.rule_id for item in reports for finding in item.findings]
    report.evidence.extend(
        [
            {"kind": "deterministic_rule_hits", "value": len(by_rule)},
            {"kind": "rule_ids", "value": sorted(by_rule)},
            {"kind": "reviewed_files", "value": len(sources)},
        ]
    )
    report.coverage.extend(item.path for item in sources)
    return report


def _scan_challenger(sources: list[SourceFile], reports: list[OfficerReport]) -> OfficerReport:
    report = _report("Challenger")
    existing = [finding for item in reports for finding in item.findings]
    high_risk = [
        item.path
        for item in sources
        if item.path.startswith(".github/workflows/")
        or any(token in item.path.lower() for token in ("auth", "security", "credential", "provider", "gateway"))
    ]
    if high_risk and not existing:
        report.questions.append(
            "High-risk workflow/provider surfaces changed but no deterministic officer produced a finding; require an explicit clean-proof explanation before approval."
        )
    report.evidence.append({"kind": "high_risk_clean_verdict_challenge", "value": sorted(high_risk)})
    report.coverage.extend(high_risk)
    return report


def _root_key(finding: OfficerFinding) -> tuple[str, str, str]:
    return finding.rule_id, finding.path, finding.message.lower()


def _scan_judge(reports: list[OfficerReport]) -> tuple[OfficerReport, list[OfficerFinding]]:
    report = _report("Judge")
    merged: dict[tuple[str, str, str], OfficerFinding] = {}
    supporters: dict[tuple[str, str, str], set[str]] = {}
    for officer_report in reports:
        for finding in officer_report.findings:
            key = _root_key(finding)
            supporters.setdefault(key, set()).add(finding.officer)
            current = merged.get(key)
            if current is None or SEVERITY_RANK[finding.severity] > SEVERITY_RANK[current.severity]:
                merged[key] = finding
    findings = sorted(
        merged.values(),
        key=lambda item: (-SEVERITY_RANK[item.severity], item.path, item.line_start, item.rule_id),
    )
    report.evidence.append(
        {
            "kind": "admitted_root_causes",
            "value": [
                {"rule_id": item.rule_id, "path": item.path, "supporting_officers": sorted(supporters[_root_key(item)])}
                for item in findings
            ],
        }
    )
    report.coverage.extend(item.path for item in findings)
    return report, findings


def _scan_archivist(context: dict[str, Any], findings: list[OfficerFinding]) -> OfficerReport:
    report = _report("Archivist")
    experience = context.get("cpl_verified_experience", {}) if isinstance(context, dict) else {}
    events = experience.get("events", []) if isinstance(experience, dict) else []
    lessons = experience.get("canonical_lessons", []) if isinstance(experience, dict) else []
    report.evidence.extend(
        [
            {"kind": "verified_experience_events", "value": len(events) if isinstance(events, list) else 0},
            {"kind": "canonical_lessons", "value": len(lessons) if isinstance(lessons, list) else 0},
            {"kind": "candidate_lessons", "value": [item.rule_id for item in findings]},
        ]
    )
    report.coverage.extend(item.path for item in findings)
    return report


def run_deterministic_officer_council(
    root: str | Path,
    changed_files: list[str],
    deterministic_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run permanent officers without requiring a model route."""

    root_path = Path(root)
    context = deterministic_context or {}
    sources = _safe_source_files(root_path, changed_files)

    scout = _scan_scout(sources)
    quartermaster = _scan_quartermaster(sources)
    engineer = _scan_engineer(sources)
    medic = _scan_medic(sources)
    mechanic = _scan_mechanic(sources)
    initial = [scout, quartermaster, engineer, medic, mechanic]
    analyst = _scan_analyst(sources, initial)
    challenger = _scan_challenger(sources, [*initial, analyst])
    judge, findings = _scan_judge([*initial, analyst, challenger])
    archivist = _scan_archivist(context, findings)
    reports = [*initial, analyst, challenger, judge, archivist]

    severities = {item.severity for item in findings}
    verdict = "BLOCK" if "blocker" in severities else "NEEDS WORK" if "major" in severities else "PASS"
    unresolved = [question for report in reports for question in report.questions]
    if unresolved and verdict == "PASS":
        verdict = "NEEDS WORK"

    return {
        "schema_version": "sergeant.deterministic-officer-council.v1",
        "status": "completed",
        "mode": "deterministic_with_optional_model_amplification",
        "model_required": False,
        "model_used": False,
        "verdict": verdict,
        "confidence": 0.97 if findings else 0.82,
        "summary": (
            f"Nine permanent officers reviewed {len(sources)} readable changed file(s), admitted "
            f"{len(findings)} deterministic root-cause finding(s), and left {len(unresolved)} explicit proof question(s)."
        ),
        "officers": [report.to_dict() for report in reports],
        "findings": [item.to_dict() for item in findings],
        "unresolved_questions": unresolved,
        "coverage": {
            "declared_changed_files": list(dict.fromkeys(changed_files)),
            "readable_changed_files": [item.path for item in sources],
            "officers_deployed": [report.officer for report in reports],
        },
        "amplification": {
            "available": True,
            "required_for_baseline": False,
            "rule": "Models may add evidence only through the same officer report and Judge admission contract.",
        },
    }
