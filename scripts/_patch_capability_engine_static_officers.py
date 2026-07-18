from __future__ import annotations

from pathlib import Path


path = Path("main_review/capability_engine.py")
text = path.read_text(encoding="utf-8")

import_marker = "from .scanner import scan_repository\n"
import_replacement = (
    "from .scanner import scan_repository\n"
    "from .static_invariant_review import run_static_invariant_review\n"
)
if text.count(import_marker) != 1:
    raise SystemExit("capability_engine import marker changed")
text = text.replace(import_marker, import_replacement, 1)

function_marker = "def run_capability_engine(root: str | Path = \".\", changed_files: list[str] | None = None) -> dict[str, Any]:\n"
start = text.find(function_marker)
if start < 0:
    raise SystemExit("run_capability_engine marker changed")

replacement = '''def _finding_identity(finding: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(finding.get("root_cause") or finding.get("message") or "unknown"),
        str(finding.get("path") or ""),
        int(finding.get("line_start") or 0),
        str(finding.get("message") or ""),
    )


def run_capability_engine(root: str | Path = ".", changed_files: list[str] | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = _changed_set(changed_files)
    evaluation_files = sorted(path for path in changed if _is_evaluation_path(path))
    reviewable_changed = changed - set(evaluation_files)
    indexes = _build_indexes(root_path)
    base_findings: list[CapabilityFinding] = []
    for provider in (
        _cross_file_findings,
        _architecture_findings,
        _data_flow_findings,
        _call_graph_findings,
        _security_taint_findings,
        _performance_findings,
        _concurrency_findings,
        _api_contract_findings,
        _test_impact_findings,
        _regression_findings,
    ):
        base_findings.extend(provider(indexes, reviewable_changed))

    invariant_review = run_static_invariant_review(root_path, sorted(reviewable_changed))
    finding_rows: list[dict[str, Any]] = [finding.to_dict() for finding in base_findings]
    finding_rows.extend(
        dict(item)
        for item in invariant_review.get("findings", [])
        if isinstance(item, dict)
    )

    severity_rank = {"blocker": 4, "major": 3, "minor": 2, "note": 1, "advisory": 1}
    unique: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for finding in finding_rows:
        key = _finding_identity(finding)
        existing = unique.get(key)
        if existing is None:
            unique[key] = finding
            continue
        existing_score = (
            severity_rank.get(str(existing.get("severity") or "").lower(), 0),
            float(existing.get("confidence") or 0.0),
        )
        candidate_score = (
            severity_rank.get(str(finding.get("severity") or "").lower(), 0),
            float(finding.get("confidence") or 0.0),
        )
        if candidate_score > existing_score:
            unique[key] = finding

    findings = list(unique.values())
    covered = sorted(
        {
            str(finding.get("capability") or finding.get("category"))
            for finding in findings
            if str(finding.get("capability") or finding.get("category") or "")
        }
    )
    capability_status = {
        name: "active"
        for name in (
            "cross_file",
            "architecture",
            "data_flow",
            "call_graph",
            "security_taint",
            "performance",
            "concurrency",
            "api_contract",
            "test_impact",
            "regression",
        )
    }
    capability_status["language"] = "scanner-backed"
    for capability in covered:
        capability_status.setdefault(capability, "static-officer")

    strongest = max(
        (severity_rank.get(str(finding.get("severity") or "").lower(), 0) for finding in findings),
        default=0,
    )
    return {
        "verdict": "BLOCK" if strongest == 4 else "NEEDS WORK" if strongest >= 3 else "PASS",
        "changed_files": sorted(changed),
        "reviewable_changed_files": sorted(reviewable_changed),
        "evaluation_files_excluded": evaluation_files,
        "capability_status": capability_status,
        "covered_by_findings": covered,
        "finding_count": len(findings),
        "findings": findings,
        "static_invariant_review": invariant_review,
    }
'''

path.write_text(text[:start] + replacement, encoding="utf-8")
