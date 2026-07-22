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
_REQUIRED_ASSURANCE_WORDS = {
    "authorization",
    "credential",
    "evidence",
    "permission",
    "proof",
    "required",
    "runtime",
    "security",
    "test",
    "verification",
    "verify",
}

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
_RUNTIME_WORDS = {
    "async",
    "await",
    "concurrent",
    "counter",
    "global",
    "iteration",
    "lock",
    "loop",
    "performance",
    "race",
    "runtime",
    "scale",
    "thread",
}


def _safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalise_finding(item: object, source: str) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    severity = str(item.get("severity") or "note").strip().lower()
    category = str(item.get("capability") or item.get("category") or "other").strip().lower()
    path = str(item.get("path") or "").strip().replace("\\", "/")
    try:
        start = int(item.get("line_start") or item.get("line") or 1)
    except (TypeError, ValueError):
        start = 1
    try:
        end = int(item.get("line_end") or start)
    except (TypeError, ValueError):
        end = start
    start = max(1, start)
    end = max(start, end)
    return {
        **item,
        "source": source,
        "severity": severity,
        "category": category,
        "path": path,
        "line_start": start,
        "line_end": end,
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


def cross_source_match(left: dict[str, Any], right: dict[str, Any], *, max_line_distance: int = 10) -> bool:
    """Return whether a Cpl report confirms an existing deterministic finding.

    Cpl-internal matching remains stricter. Cross-source matching additionally
    recognises that deterministic capability engines and natural-language model
    reports may use different category names for the same evidenced defect.
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
    if left_family in {"security", "architecture", "api_contract", "proof"}:
        return True
    if left_family == "runtime":
        return bool((_text_tokens(left) | _text_tokens(right)) & _RUNTIME_WORDS)
    return str(left.get("category") or "") == str(right.get("category") or "")


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
    new blocker/major finding must be grounded and have the required independent
    model support. Generic tests/documentation requests and minor suggestions
    remain advisory rather than becoming merge gates.
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

        grounded = finding.get("evidence_verified") is True and bool(finding.get("path"))
        independently_supported = len(supporting_models) >= max(1, minimum_supporting_models)
        if grounded and independently_supported:
            actionable.append({**finding, "disposition": "admitted_novel"})
        else:
            reasons = []
            if not grounded:
                reasons.append("grounding contract not satisfied")
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


def classify_council_gaps(gaps: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Separate merge-affecting assurance gaps from uncertainty and context."""

    verdict_gaps: list[dict[str, Any]] = []
    confidence_gaps: list[dict[str, Any]] = []
    informational_gaps: list[dict[str, Any]] = []
    for gap in gaps:
        gap_type = str(gap.get("type") or "")
        reason = str(gap.get("reason") or "").lower()
        required_assurance = bool(set(re.findall(r"[a-z_][a-z0-9_]+", reason)) & _REQUIRED_ASSURANCE_WORDS)
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
