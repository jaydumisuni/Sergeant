"""Adjudicate Cpl findings against deterministic Sergeant evidence.

Raw officer/model reports remain available for audit. This module decides which
Cpl findings are genuinely new and actionable, which merely confirm existing
Sergeant evidence, and which should remain advisory or rejected. Deterministic
Sergeant findings retain authority over severity and the final merge gate.
"""
from __future__ import annotations

import re
from typing import Any

from .cpl_council import finding_root_cause, findings_match

ACTIONABLE_SEVERITIES = {"blocker", "major"}
ADVISORY_CATEGORIES = {"tests", "documentation"}
VERDICT_GAP_TYPES = {"missing_report", "independent_confirmation", "recurrence"}
CONFIDENCE_GAP_TYPES = {"failed_member", "disagreement"}
FINDING_DEPENDENT_GAP_TYPES = {"independent_confirmation", "recurrence"}

_SECURITY_CATEGORIES = {"security", "security_taint", "data_flow"}
_RUNTIME_CATEGORIES = {"correctness", "concurrency", "performance"}
_PROOF_CATEGORIES = {"tests", "test_impact", "documentation"}
_SECURITY_ROOTS = {
    "unsafe-shell-execution",
    "sql-injection",
    "unsafe-file-access",
    "authorization-gap",
    "secret-exposure",
    "unsafe-data-flow",
}
_GENERIC_ROOTS = {
    "security": {"unsafe-data-flow"},
    "runtime": {"runtime-risk"},
    "architecture": {"architecture-boundary"},
    "api_contract": {"change-impact"},
    "proof": {"proof-gap"},
}
_TOKEN_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "both",
    "by",
    "can",
    "code",
    "could",
    "defect",
    "detected",
    "evidence",
    "finding",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "issue",
    "line",
    "may",
    "needs",
    "of",
    "on",
    "operation",
    "or",
    "path",
    "possible",
    "present",
    "review",
    "risk",
    "security",
    "should",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def _safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_line_range(item: dict[str, Any]) -> tuple[int, int, bool]:
    raw_start = item.get("line_start", item.get("line"))
    if raw_start is None or isinstance(raw_start, bool):
        return 1, 1, False
    try:
        start = int(raw_start)
    except (TypeError, ValueError):
        return 1, 1, False

    raw_end = item.get("line_end", raw_start)
    if isinstance(raw_end, bool):
        return max(1, start), max(1, start), False
    try:
        end = int(raw_end)
    except (TypeError, ValueError):
        return max(1, start), max(1, start), False

    valid = start >= 1 and end >= start
    start = max(1, start)
    end = max(start, end)
    return start, end, valid


def _normalise_finding(item: object, source: str) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    severity = str(item.get("severity") or "note").strip().lower()
    category = str(item.get("capability") or item.get("category") or "other").strip().lower()
    path = str(item.get("path") or "").strip().replace("\\", "/")
    start, end, line_range_valid = _parse_line_range(item)
    return {
        **item,
        "source": source,
        "severity": severity,
        "category": category,
        "path": path,
        "line_start": start,
        "line_end": end,
        "line_range_valid": line_range_valid,
    }


def deterministic_findings(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return deterministic findings supplied to Cpl without collapsing them.

    Distinct deterministic capabilities may intentionally describe different
    assurance dimensions on the same line. They remain separate. This list is
    used only to decide whether a Cpl report is confirmation or genuinely new.
    """

    rows: list[tuple[str, object]] = []
    rows.extend(("repository", item) for item in _safe_list(context.get("repository_findings")))
    rows.extend(("diff", item) for item in _safe_list(context.get("diff_findings")))

    capability = _safe_dict(context.get("capability_review"))
    rows.extend(("capability", item) for item in _safe_list(capability.get("findings")))

    intelligence = _safe_dict(context.get("review_intelligence"))
    promoted = intelligence.get("promoted_findings", intelligence.get("ranked_findings", []))
    rows.extend(("review_intelligence", item) for item in _safe_list(promoted))

    output: list[dict[str, Any]] = []
    for source, item in rows:
        normalised = _normalise_finding(item, source)
        if normalised is not None:
            output.append(normalised)
    return output


def _line_distance(left: dict[str, Any], right: dict[str, Any]) -> int:
    left_start = int(left.get("line_start") or 1)
    left_end = int(left.get("line_end") or left_start)
    right_start = int(right.get("line_start") or 1)
    right_end = int(right.get("line_end") or right_start)
    if left_end >= right_start and right_end >= left_start:
        return 0
    return max(right_start - left_end, left_start - right_end)


def _text_tokens(finding: dict[str, Any]) -> set[str]:
    text = " ".join(
        str(finding.get(field) or "")
        for field in ("message", "evidence", "why_it_matters", "root_cause")
    ).lower()
    return set(re.findall(r"[a-z_][a-z0-9_]+", text))


def _meaningful_tokens(finding: dict[str, Any]) -> set[str]:
    return {
        token
        for token in _text_tokens(finding)
        if len(token) > 2 and token not in _TOKEN_STOPWORDS
    }


def _family(finding: dict[str, Any]) -> str:
    category = str(finding.get("category") or "other").lower()
    root = finding_root_cause(finding)
    if root in _SECURITY_ROOTS or category in _SECURITY_CATEGORIES:
        return "security"
    if root == "runtime-risk" or category in _RUNTIME_CATEGORIES:
        return "runtime"
    if root == "architecture-boundary" or category == "architecture":
        return "architecture"
    if root == "change-impact" or category == "api_contract":
        return "api_contract"
    if root == "proof-gap" or category in _PROOF_CATEGORIES:
        return "proof"
    return category


def _defect_overlap(left: dict[str, Any], right: dict[str, Any], family: str) -> bool:
    left_root = finding_root_cause(left)
    right_root = finding_root_cause(right)
    if left_root and right_root:
        if left_root == right_root:
            return True
        generic = _GENERIC_ROOTS.get(family, set())
        if left_root not in generic and right_root not in generic:
            return False

    left_tokens = _meaningful_tokens(left)
    right_tokens = _meaningful_tokens(right)
    shared = left_tokens & right_tokens
    if len(shared) >= 2:
        return True

    generic = _GENERIC_ROOTS.get(family, set())
    if len(shared) == 1 and ((left_root in generic) or (right_root in generic)):
        return True

    return False


def cross_source_match(left: dict[str, Any], right: dict[str, Any], *, max_line_distance: int = 10) -> bool:
    """Return whether a Cpl report confirms an existing deterministic finding.

    Cpl-internal matching remains stricter. Cross-source matching additionally
    recognises that deterministic capability engines and natural-language model
    reports may use different category names for the same evidenced defect.
    Family and line proximity alone are never enough: the reports must share a
    root cause or meaningful defect-level evidence.
    """

    if findings_match(left, right, max_line_distance=max_line_distance):
        return True
    left_path = str(left.get("path") or "").replace("\\", "/")
    right_path = str(right.get("path") or "").replace("\\", "/")
    if not left_path or left_path != right_path:
        return False
    if _line_distance(left, right) > max_line_distance:
        return False

    left_family = _family(left)
    right_family = _family(right)
    if left_family != right_family:
        return False
    return _defect_overlap(left, right, left_family)


def _supporting_models(finding: dict[str, Any]) -> list[str]:
    values = [
        *_safe_list(finding.get("supporting_models")),
        *_safe_list(finding.get("council_confirmed_by")),
    ]
    return sorted({str(value) for value in values if str(value).strip() and str(value) != "None"})


def _finding_reference(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": finding.get("source"),
        "category": finding.get("category"),
        "severity": finding.get("severity"),
        "path": finding.get("path"),
        "line_start": finding.get("line_start"),
        "line_end": finding.get("line_end"),
        "message": finding.get("message"),
        "root_cause": finding_root_cause(finding),
    }


def _verdict(findings: list[dict[str, Any]]) -> str:
    if any(item.get("severity") == "blocker" for item in findings):
        return "BLOCK"
    if any(item.get("severity") == "major" for item in findings):
        return "NEEDS WORK"
    return "PASS"


def adjudicate_cpl_findings(
    cpl_findings: list[dict[str, Any]],
    deterministic_context: dict[str, Any],
    *,
    minimum_supporting_models: int = 1,
) -> dict[str, Any]:
    """Classify raw Cpl findings without allowing duplicate model noise to gate.

    A Cpl report matching deterministic evidence becomes a confirmation. The
    deterministic finding keeps its message, root cause and severity. A genuinely
    new blocker/major finding must be grounded, identify a valid supplied location
    and have the required independent model support. Generic tests/documentation
    requests and minor suggestions remain advisory rather than becoming gates.
    """

    deterministic = deterministic_findings(deterministic_context)
    actionable: list[dict[str, Any]] = []
    confirmations: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in cpl_findings:
        finding = _normalise_finding(raw, "cpl")
        if finding is None:
            continue
        existing = next((item for item in deterministic if cross_source_match(finding, item)), None)
        if existing is not None:
            confirmations.append({
                **finding,
                "disposition": "confirmed_existing",
                "matched_finding": _finding_reference(existing),
                "supporting_models": _supporting_models(finding),
            })
            continue

        category = str(finding.get("category") or "other")
        severity = str(finding.get("severity") or "note")
        supporting_models = _supporting_models(finding)
        finding["supporting_models"] = supporting_models

        if category in ADVISORY_CATEGORIES or severity not in ACTIONABLE_SEVERITIES:
            advisory.append({**finding, "disposition": "advisory"})
            continue

        grounded = (
            finding.get("evidence_verified") is True
            and bool(finding.get("path"))
            and finding.get("line_range_valid") is True
        )
        independently_supported = len(supporting_models) >= max(1, minimum_supporting_models)
        if grounded and independently_supported:
            actionable.append({**finding, "disposition": "admitted_novel"})
        else:
            reasons = []
            if not grounded:
                reasons.append("grounding contract not satisfied: supplied path and valid line range required")
            if not independently_supported:
                reasons.append(
                    f"requires {max(1, minimum_supporting_models)} supporting model(s), got {len(supporting_models)}"
                )
            rejected.append({
                **finding,
                "disposition": "rejected_from_gate",
                "rejection_reason": "; ".join(reasons),
            })

    return {
        "schema_version": "sergeant.cpl-finding-adjudication.v1",
        "verdict": _verdict(actionable),
        "minimum_supporting_models": max(1, minimum_supporting_models),
        "deterministic_finding_count": len(deterministic),
        "raw_cpl_finding_count": len(cpl_findings),
        "actionable_findings": actionable,
        "confirmations": confirmations,
        "advisory_findings": advisory,
        "rejected_findings": rejected,
        "rule": (
            "Deterministic Sergeant evidence retains severity and gate authority. "
            "Cpl confirmations add provenance; only grounded, sufficiently independent novel findings may add a gate."
        ),
    }


def adjudicate_finding_dependent_gaps(
    gaps: list[dict[str, Any]],
    actionable_findings: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Keep finding-dependent gaps gating only for admitted actionable findings.

    Raw recurrence and independent-confirmation gaps remain auditable. A gap tied
    only to a confirmation, advisory or rejected model claim cannot bypass the
    finding-admission boundary and change the final verdict.
    """

    effective: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for gap in gaps:
        gap_type = str(gap.get("type") or "")
        if gap_type not in FINDING_DEPENDENT_GAP_TYPES:
            effective.append(gap)
            continue
        target = gap.get("target_finding")
        admitted = isinstance(target, dict) and any(
            findings_match(target, finding) or cross_source_match(target, finding)
            for finding in actionable_findings
        )
        if admitted:
            effective.append(gap)
        else:
            suppressed.append({
                **gap,
                "adjudication_disposition": "non_gating_unadmitted_finding",
            })
    return {
        "effective_gaps": effective,
        "suppressed_gaps": suppressed,
    }


def classify_council_gaps(gaps: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Separate merge-affecting assurance gaps from uncertainty and context."""

    verdict_gaps: list[dict[str, Any]] = []
    confidence_gaps: list[dict[str, Any]] = []
    informational_gaps: list[dict[str, Any]] = []
    for gap in gaps:
        gap_type = str(gap.get("type") or "")
        required_assurance = gap.get("required_assurance") is True
        if gap_type in VERDICT_GAP_TYPES or (gap_type == "unanswered_question" and required_assurance):
            verdict_gaps.append(gap)
        elif gap_type in CONFIDENCE_GAP_TYPES or gap_type == "unanswered_question":
            confidence_gaps.append(gap)
        else:
            informational_gaps.append(gap)
    return {
        "verdict_gaps": verdict_gaps,
        "confidence_gaps": confidence_gaps,
        "informational_gaps": informational_gaps,
    }
