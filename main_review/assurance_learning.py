"""Fail-closed SAE-140 assurance-learning qualification.

Learning may propose assurance improvements, but proposal qualification grants no
ACR activation, capability qualification, verdict authority, risk-acceptance
truth, self-promotion, or merge authority.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

ALLOWED_TYPES={"detector","acr","cardinality","closure","falsifier","mutation","capability","evidence","relation"}
FORBIDDEN_EFFECTS={"activate_acr","qualify_capability","rewrite_verdict","consume_owner_risk_acceptance_as_truth","self_promote","auto_merge"}
REQUIRED_SOURCE="teacher_prosecutor_defender"

class LearningContractError(ValueError):
    """Raised when an assurance-learning proposal violates the governed contract."""

def _text(value: object) -> str:
    return "" if value is None else str(value).strip()

def qualify_learning_proposals(
    proposals: Iterable[Mapping[str, Any]],
    *,
    terminally_rejected: set[tuple[str,str]] | None = None,
) -> dict[str, Any]:
    rejected=set(terminally_rejected or set())
    accepted=[]
    seen=set()
    for raw in proposals:
        item=dict(raw)
        lesson_id=_text(item.get("lesson_id"))
        evidence_id=_text(item.get("evidence_id"))
        proposal_type=_text(item.get("proposal_type")).lower()
        pair=(lesson_id,evidence_id)
        if not lesson_id or not evidence_id:
            raise LearningContractError("lesson_id and evidence_id are required")
        if pair in seen:
            raise LearningContractError("duplicate lesson/evidence pair")
        seen.add(pair)
        if pair in rejected:
            raise LearningContractError("terminally rejected lesson cannot revive from the same evidence")
        if proposal_type not in ALLOWED_TYPES:
            raise LearningContractError("unsupported assurance-learning proposal type")
        if _text(item.get("source")) != REQUIRED_SOURCE:
            raise LearningContractError("Teacher/Prosecutor/Defender lineage is required")
        for field in ("negative_controls_passed","transfer_passed","hidden_holdout_passed"):
            if item.get(field) is not True:
                raise LearningContractError(f"{field} is required")
        if item.get("owner_promotion_required") is not True:
            raise LearningContractError("Owner-controlled promotion must remain mandatory")
        effects={_text(value) for value in item.get("requested_effects",[]) if _text(value)}
        forbidden=effects & FORBIDDEN_EFFECTS
        if forbidden:
            raise LearningContractError(f"forbidden authority effect: {sorted(forbidden)[0]}")
        accepted.append({
            "lesson_id":lesson_id,
            "evidence_id":evidence_id,
            "proposal_type":proposal_type,
            "source":REQUIRED_SOURCE,
            "feedback":list(item.get("feedback") or []),
            "requested_effects":sorted(effects),
            "owner_promotion_required":True,
            "state":"proposal_only",
        })
    if not accepted:
        raise LearningContractError("at least one proposal is required")
    return {
        "qualified":True,
        "proposals":accepted,
        "authority_gain":[],
        "auto_merge":False,
        "auto_promote":False,
        "owner_risk_acceptance_consumed_as_truth":False,
    }
