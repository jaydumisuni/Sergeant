"""Adjudicated finding ledger for deterministic Sergeant and Cpl evidence.

The ledger preserves every source report, but exposes one actionable review surface.
Deterministic findings remain authoritative. Cpl confirmations are attached to the
matching deterministic finding instead of becoming duplicate user-facing defects.
A genuinely new Cpl blocker or major finding gates only when it is grounded and
independently supported.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable

from .cpl_council import finding_root_cause, findings_match

_ACTIONABLE_SEVERITIES = {"blocker", "major", "minor"}
_GATING_SEVERITIES = {"blocker", "major"}
_SEVERITY_RANK = {"minor": 1, "major": 2, "blocker": 3}
_CPL_ADVISORY_CATEGORIES = {"tests", "testing", "documentation"}
_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.I)


def _text(value: object) -> str:
    return str(value or "").strip()


def _stable_id(prefix: str, *values: object) -> str:
    material = "\x1f".join(_text(value) for value in values)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _bucket_rows(packet: dict[str, Any], section: str) -> list[dict[str, Any]]:
    value = packet.get(section, {}) if isinstance(packet, dict) else {}
    if not isinstance(value, dict):
        return []
    rows: list[dict[str, Any]] = []
    for bucket in ("blocking_findings", "major_findings", "minor_findings"):
        items = value.get(bucket, [])
        if isinstance(items, list):
            rows.extend(item for item in items if isinstance(item, dict))
    return rows


def _repository_rows(repository_review: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = repository_review.get("evidence", {}) if isinstance(repository_review, dict) else {}
    findings = evidence.get("findings", []) if isinstance(evidence, dict) else []
    return [item for item in findings if isinstance(item, dict)]


def _diff_rows(diff_review: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = diff_review.get("evidence", {}) if isinstance(diff_review, dict) else {}
    findings = evidence.get("findings", []) if isinstance(evidence, dict) else []
    if isinstance(findings, list) and findings:
        return [item for item in findings if isinstance(item, dict)]
    return _bucket_rows(diff_review, "verdict")


def _intelligence_rows(intelligence: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ranked = intelligence.get("ranked_findings", []) if isinstance(intelligence, dict) else []
    actionable: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for item in ranked if isinstance(ranked, list) else []:
        if not isinstance(item, dict):
            continue
        severity = _text(item.get("severity")).lower()
        if severity == "minor" or bool(item.get("promoted")):
            actionable.append(item)
        elif severity in _GATING_SEVERITIES:
            suppressed.append(item)
    return actionable, suppressed


def _normalize(
    row: dict[str, Any],
    *,
    source_layer: str,
    authority: str,
) -> dict[str, Any] | None:
    severity = _text(row.get("severity")).lower()
    if severity not in _ACTIONABLE_SEVERITIES:
        return None
    category = _text(row.get("capability") or row.get("category") or "other").lower() or "other"
    message = _text(row.get("message")) or "Review finding"
    path = _text(row.get("path")) or None
    line_start = row.get("line_start") or row.get("line")
    line_end = row.get("line_end") or line_start
    root_cause = _text(row.get("root_cause")) or None
    finding_id = _text(row.get("finding_id")) or _stable_id(
        authority,
        source_layer,
        category,
        path,
        line_start,
        message,
    )
    supporting_models = sorted(
        {
            _text(model)
            for model in row.get("supporting_models", [])
            if _text(model)
        }
    ) if isinstance(row.get("supporting_models", []), list) else []
    confirmations = sorted(
        {
            _text(model)
            for model in row.get("council_confirmed_by", [])
            if _text(model)
        }
    ) if isinstance(row.get("council_confirmed_by", []), list) else []
    return {
        **row,
        "finding_id": finding_id,
        "severity": severity,
        "category": category,
        "message": message,
        "path": path,
        "line_start": line_start if isinstance(line_start, int) else None,
        "line_end": line_end if isinstance(line_end, int) else None,
        "root_cause": root_cause,
        "source_layer": source_layer,
        "authority": authority,
        "supporting_models": supporting_models,
        "council_confirmed_by": confirmations,
        "gating": severity in _GATING_SEVERITIES,
        "disposition": "actionable",
    }


def _exact_key(finding: dict[str, Any]) -> tuple[object, ...]:
    return (
        finding.get("source_layer"),
        finding.get("category"),
        _text(finding.get("message")).lower(),
        finding.get("path"),
        finding.get("line_start"),
    )


def _tokens(*values: object) -> set[str]:
    stop = {"the", "and", "for", "with", "from", "this", "that", "into", "when", "should", "could"}
    return {
        token.lower()
        for value in values
        for token in _TOKEN_RE.findall(_text(value))
        if len(token) > 2 and token.lower() not in stop
    }


def _token_overlap(left: dict[str, Any], right: dict[str, Any]) -> float:
    left_tokens = _tokens(left.get("message"), left.get("evidence"), left.get("root_cause"))
    right_tokens = _tokens(right.get("message"), right.get("evidence"), right.get("root_cause"))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _line_distance(left: dict[str, Any], right: dict[str, Any]) -> int | None:
    left_start = left.get("line_start")
    right_start = right.get("line_start")
    if not isinstance(left_start, int) or not isinstance(right_start, int):
        return None
    left_end = left.get("line_end") if isinstance(left.get("line_end"), int) else left_start
    right_end = right.get("line_end") if isinstance(right.get("line_end"), int) else right_start
    if left_end >= right_start and right_end >= left_start:
        return 0
    return max(right_start - left_end, left_start - right_end)


def _broad_root(finding: dict[str, Any]) -> str:
    root = finding_root_cause(finding)
    aliases = {
        "unsafe-shell-execution": "unsafe-data-flow",
        "sql-injection": "unsafe-data-flow",
        "security": "unsafe-data-flow",
    }
    if root:
        return aliases.get(root, root)
    category = _text(finding.get("category") or finding.get("capability")).lower()
    return {
        "security": "unsafe-data-flow",
        "security_taint": "unsafe-data-flow",
        "data_flow": "unsafe-data-flow",
        "api_contract": "change-impact",
        "cross_file": "change-impact",
        "call_graph": "change-impact",
        "regression": "change-impact",
        "tests": "proof-gap",
        "testing": "proof-gap",
        "test_impact": "proof-gap",
        "performance": "runtime-risk",
        "concurrency": "runtime-risk",
        "architecture": "architecture-boundary",
    }.get(category, category)


def _same_cross_source_issue(deterministic: dict[str, Any], cpl: dict[str, Any]) -> bool:
    if findings_match(deterministic, cpl):
        return True
    left_path = _text(deterministic.get("path")).replace("\\", "/")
    right_path = _text(cpl.get("path")).replace("\\", "/")
    if not left_path or left_path != right_path:
        return False
    distance = _line_distance(deterministic, cpl)
    if distance is not None and distance > 10:
        return False
    left_root = _broad_root(deterministic)
    right_root = _broad_root(cpl)
    if left_root and left_root == right_root:
        return True
    return (
        _text(deterministic.get("category")) == _text(cpl.get("category"))
        and _token_overlap(deterministic, cpl) >= 0.25
    )


def _best_match(cpl: dict[str, Any], deterministic: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [item for item in deterministic if _same_cross_source_issue(item, cpl)]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            _SEVERITY_RANK.get(_text(item.get("severity")), 0),
            _token_overlap(item, cpl),
            -(_line_distance(item, cpl) or 0),
        ),
    )


def _attach_confirmation(target: dict[str, Any], cpl: dict[str, Any]) -> None:
    sources = target.setdefault("supporting_sources", [])
    if "cpl_review" not in sources:
        sources.append("cpl_review")
    models = target.setdefault("supporting_models", [])
    for model in [*cpl.get("supporting_models", []), *cpl.get("council_confirmed_by", [])]:
        if model and model not in models:
            models.append(model)
    confirmations = target.setdefault("cpl_confirmations", [])
    confirmations.append({
        "finding_id": cpl.get("finding_id"),
        "severity": cpl.get("severity"),
        "category": cpl.get("category"),
        "message": cpl.get("message"),
        "evidence": cpl.get("evidence"),
        "supporting_models": cpl.get("supporting_models", []),
    })


def _independently_supported(cpl: dict[str, Any]) -> bool:
    models = {
        _text(model)
        for model in [*cpl.get("supporting_models", []), *cpl.get("council_confirmed_by", [])]
        if _text(model)
    }
    return len(models) >= 2


def _required_action(finding: dict[str, Any]) -> str:
    location = _text(finding.get("path"))
    if finding.get("line_start"):
        location = f"{location}:{finding['line_start']}" if location else f"line {finding['line_start']}"
    prefix = f" at {location}" if location else ""
    return f"Answer {finding.get('severity')} {finding.get('category')} finding{prefix}: {finding.get('message')}"


def _normalized_rows(
    rows: Iterable[dict[str, Any]],
    *,
    source_layer: str,
    authority: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        finding = _normalize(row, source_layer=source_layer, authority=authority)
        if finding is not None:
            output.append(finding)
    return output


def build_finding_ledger(
    repository_review: dict[str, Any],
    diff_review: dict[str, Any],
    intelligence: dict[str, Any],
    cpl_review: dict[str, Any],
) -> dict[str, Any]:
    """Build one actionable finding surface while preserving every source report."""

    intelligence_rows, suppressed_intelligence_rows = _intelligence_rows(intelligence)
    deterministic_candidates = [
        *_normalized_rows(_repository_rows(repository_review), source_layer="repository_review", authority="deterministic"),
        *_normalized_rows(_diff_rows(diff_review), source_layer="diff_review", authority="deterministic"),
        *_normalized_rows(intelligence_rows, source_layer="review_intelligence", authority="deterministic"),
    ]
    deterministic: list[dict[str, Any]] = []
    seen: set[tuple[object, ...]] = set()
    for finding in deterministic_candidates:
        key = _exact_key(finding)
        if key in seen:
            continue
        seen.add(key)
        finding["supporting_sources"] = [finding["source_layer"]]
        deterministic.append(finding)

    suppressed: list[dict[str, Any]] = []
    for finding in _normalized_rows(
        suppressed_intelligence_rows,
        source_layer="review_intelligence",
        authority="deterministic",
    ):
        finding.update({"gating": False, "disposition": "suppressed_by_evidence_challenge"})
        suppressed.append(finding)

    cpl_rows = cpl_review.get("findings", []) if isinstance(cpl_review, dict) else []
    cpl_candidates = _normalized_rows(
        [item for item in cpl_rows if isinstance(item, dict)] if isinstance(cpl_rows, list) else [],
        source_layer="cpl_review",
        authority="cpl",
    )
    admitted_cpl: list[dict[str, Any]] = []
    duplicate_confirmations: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []

    for finding in cpl_candidates:
        match = _best_match(finding, deterministic)
        if match is not None:
            _attach_confirmation(match, finding)
            duplicate = {
                **finding,
                "gating": False,
                "disposition": "duplicate_confirmation",
                "duplicate_of": match.get("finding_id"),
            }
            duplicate_confirmations.append(duplicate)
            suppressed.append(duplicate)
            continue

        grounded = finding.get("evidence_verified") is True
        independent = _independently_supported(finding)
        category = _text(finding.get("category")).lower()
        severity = _text(finding.get("severity")).lower()
        if (
            severity in _GATING_SEVERITIES
            and grounded
            and independent
            and category not in _CPL_ADVISORY_CATEGORIES
        ):
            finding["supporting_sources"] = ["cpl_review"]
            finding["admission"] = "independently_grounded_novel_finding"
            admitted_cpl.append(finding)
            continue

        disposition = "advisory_unconfirmed"
        if category in _CPL_ADVISORY_CATEGORIES:
            disposition = "advisory_without_deterministic_proof_gap"
        elif not grounded:
            disposition = "rejected_unverified_evidence"
        finding.update({
            "gating": False,
            "disposition": disposition,
            "admission": "not_admitted_to_gate",
        })
        advisory.append(finding)
        suppressed.append(finding)

    actionable = [*deterministic, *admitted_cpl]
    blockers = [item for item in actionable if item.get("severity") == "blocker"]
    majors = [item for item in actionable if item.get("severity") == "major"]
    gating = [item for item in actionable if item.get("gating")]
    verdict = "BLOCK" if blockers else "NEEDS WORK" if majors else "PASS"
    required_actions = sorted({_required_action(item) for item in gating})
    return {
        "schema_version": "sergeant.finding-ledger.v1",
        "verdict": verdict,
        "actionable_findings": actionable,
        "gating_findings": gating,
        "advisory_findings": advisory,
        "duplicate_confirmations": duplicate_confirmations,
        "suppressed_findings": suppressed,
        "required_actions": required_actions,
        "raw_candidate_count": len(deterministic_candidates) + len(cpl_candidates),
        "counts": {
            "actionable": len(actionable),
            "gating": len(gating),
            "advisory": len(advisory),
            "duplicate_confirmations": len(duplicate_confirmations),
            "suppressed": len(suppressed),
        },
        "rule": (
            "Deterministic Sergeant evidence is authoritative. Cpl confirmations attach to matching findings. "
            "A novel Cpl blocker or major gates only with verified evidence and support from at least two models."
        ),
    }
