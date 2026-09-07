"""SAE-30 structural separation between engineering truth and Owner business risk."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class OwnerRiskError(ReviewWorldError):
    """Raised when an Owner-risk record attempts to cross its authority boundary."""


class EngineeringVerdict(str, Enum):
    PASS = "PASS"
    NEEDS_WORK = "NEEDS WORK"
    BLOCK = "BLOCK"


class BusinessRiskDecision(str, Enum):
    SHIP_WITH_ACCEPTED_RISK = "SHIP_WITH_ACCEPTED_RISK"
    MERGE_WITH_ACCEPTED_RISK = "MERGE_WITH_ACCEPTED_RISK"
    DEPLOY_WITH_ACCEPTED_RISK = "DEPLOY_WITH_ACCEPTED_RISK"
    DEFER = "DEFER"
    CANCEL = "CANCEL"
    # Convenience alias; it remains a business action, never engineering PASS.
    ACCEPT = "SHIP_WITH_ACCEPTED_RISK"


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise OwnerRiskError(str(exc)) from exc


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise OwnerRiskError(f"{field} must be canonical and non-empty")
    return value


@dataclass(frozen=True)
class EngineeringVerdictRecord:
    schema_version: str
    review_world_id: str
    evidence_root_id: str
    sergeant_authority_id: str
    verdict: EngineeringVerdict
    record_id: str

    @classmethod
    def create(
        cls,
        *,
        review_world_id: str,
        evidence_root_id: str,
        sergeant_authority_id: str,
        verdict: EngineeringVerdict,
    ) -> "EngineeringVerdictRecord":
        if not isinstance(verdict, EngineeringVerdict):
            raise OwnerRiskError("engineering verdict must be PASS, NEEDS WORK, or BLOCK")
        values = {
            "review_world_id": _sha(review_world_id, "review_world_id"),
            "evidence_root_id": _sha(evidence_root_id, "evidence_root_id"),
            "sergeant_authority_id": _sha(sergeant_authority_id, "sergeant_authority_id"),
        }
        body = {
            "schema_version": "sergeant.engineering-verdict-record.v1",
            **values,
            "verdict": verdict.value,
        }
        return cls(
            "sergeant.engineering-verdict-record.v1",
            values["review_world_id"], values["evidence_root_id"], values["sergeant_authority_id"],
            verdict, sha256_id(body),
        )


@dataclass(frozen=True)
class BusinessRiskDecisionRecord:
    schema_version: str
    engineering_verdict_id: str
    owner_authority_id: str
    decision: BusinessRiskDecision
    rationale: str
    record_id: str

    @classmethod
    def create(
        cls,
        *,
        engineering_verdict_id: str,
        owner_authority_id: str,
        decision: BusinessRiskDecision,
        rationale: str,
    ) -> "BusinessRiskDecisionRecord":
        if not isinstance(decision, BusinessRiskDecision):
            raise OwnerRiskError("business-risk decision has invalid type")
        values = {
            "engineering_verdict_id": _sha(engineering_verdict_id, "engineering_verdict_id"),
            "owner_authority_id": _sha(owner_authority_id, "owner_authority_id"),
            "rationale": _string(rationale, "business-risk rationale"),
        }
        body = {
            "schema_version": "sergeant.business-risk-decision-record.v1",
            **values,
            "decision": decision.value,
        }
        return cls(
            "sergeant.business-risk-decision-record.v1",
            values["engineering_verdict_id"], values["owner_authority_id"], decision,
            values["rationale"], sha256_id(body),
        )
