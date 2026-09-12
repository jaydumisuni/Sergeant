"""SAE-120 facility-gradient contract preserving one assurance law across unequal facilities."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Sequence

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class FacilityError(ReviewWorldError):
    pass


class FacilityKind(str, Enum):
    GITHUB = "github"
    LOCAL = "local"
    IDE = "ide"


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNKNOWN = "UNKNOWN"


def _sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise FacilityError(str(exc)) from exc


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise FacilityError(f"{field} must be canonical and non-empty")
    return value


def _capabilities(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(_text(value, "capability") for value in values)
    if normalized != tuple(sorted(set(normalized))):
        raise FacilityError("capabilities must be unique and sorted")
    return normalized


@dataclass(frozen=True)
class FacilityContract:
    schema_version: str
    kind: FacilityKind
    facility_generation: str
    acr_authority_id: str
    judge_authority_id: str
    rust_authority_id: str
    pass_law_id: str
    capabilities: tuple[str, ...]
    writes_enabled: bool
    owner_write_approved: bool
    law_identity: str
    contract_id: str
    verdict_semantics_authority_gain: bool = False

    @classmethod
    def create(
        cls, *, kind: FacilityKind, facility_generation: str, acr_authority_id: str,
        judge_authority_id: str, rust_authority_id: str, pass_law_id: str,
        capabilities: Sequence[str], writes_enabled: bool, owner_write_approved: bool,
    ) -> "FacilityContract":
        if not isinstance(kind, FacilityKind):
            raise FacilityError("facility kind must be canonical")
        facility_generation = _text(facility_generation, "facility_generation")
        acr_authority_id = _sha(acr_authority_id, "acr_authority_id")
        judge_authority_id = _sha(judge_authority_id, "judge_authority_id")
        rust_authority_id = _sha(rust_authority_id, "rust_authority_id")
        pass_law_id = _sha(pass_law_id, "pass_law_id")
        caps = _capabilities(capabilities)
        if kind is FacilityKind.GITHUB and (writes_enabled or owner_write_approved):
            raise FacilityError("GitHub facility is constrained and read-only")
        if writes_enabled and not owner_write_approved:
            raise FacilityError("local/IDE writes require explicit owner approval")
        if owner_write_approved and not writes_enabled:
            raise FacilityError("owner write approval cannot float without an enabled write facility")
        law_body = {
            "acr_authority_id": acr_authority_id,
            "judge_authority_id": judge_authority_id,
            "rust_authority_id": rust_authority_id,
            "pass_law_id": pass_law_id,
        }
        law_identity = sha256_id(law_body)
        body = {
            "schema_version": "sergeant.sae120-facility-contract.v1",
            "kind": kind.value,
            "facility_generation": facility_generation,
            **law_body,
            "capabilities": list(caps),
            "writes_enabled": bool(writes_enabled),
            "owner_write_approved": bool(owner_write_approved),
            "law_identity": law_identity,
            "verdict_semantics_authority_gain": False,
        }
        return cls(
            body["schema_version"], kind, facility_generation, acr_authority_id, judge_authority_id,
            rust_authority_id, pass_law_id, caps, bool(writes_enabled), bool(owner_write_approved),
            law_identity, sha256_id(body), False,
        )

    def with_pass_law(self, pass_law_id: str) -> "FacilityContract":
        return self.create(
            kind=self.kind, facility_generation=self.facility_generation,
            acr_authority_id=self.acr_authority_id, judge_authority_id=self.judge_authority_id,
            rust_authority_id=self.rust_authority_id, pass_law_id=pass_law_id,
            capabilities=self.capabilities, writes_enabled=self.writes_enabled,
            owner_write_approved=self.owner_write_approved,
        )

    @staticmethod
    def require_same_law(contracts: Sequence["FacilityContract"]) -> str:
        if not contracts:
            raise FacilityError("facility roster cannot be empty")
        identities = {item.law_identity for item in contracts if isinstance(item, FacilityContract)}
        if len(identities) != 1 or len(contracts) != sum(isinstance(item, FacilityContract) for item in contracts):
            raise FacilityError("all facilities must bind the same assurance law")
        return next(iter(identities))


@dataclass(frozen=True)
class FacilityRequirement:
    kind: FacilityKind
    capability: str

    @classmethod
    def create(cls, *, kind: FacilityKind, capability: str) -> "FacilityRequirement":
        if not isinstance(kind, FacilityKind):
            raise FacilityError("requirement facility kind must be canonical")
        return cls(kind=kind, capability=_text(capability, "required capability"))


@dataclass(frozen=True)
class FacilityAssessment:
    availability: Availability
    can_support_pass: bool
    facility_contract_id: str | None
    reason: str


def evaluate_facility_requirement(
    requirement: FacilityRequirement, contracts: Sequence[FacilityContract]
) -> FacilityAssessment:
    if not isinstance(requirement, FacilityRequirement):
        raise FacilityError("facility requirement must be canonical")
    if contracts:
        FacilityContract.require_same_law(contracts)
    matches = [item for item in contracts if item.kind is requirement.kind]
    if not matches:
        return FacilityAssessment(Availability.UNKNOWN, False, None, "required facility is unavailable")
    if len(matches) != 1:
        raise FacilityError("facility roster contains duplicate facility kind")
    contract = matches[0]
    if requirement.capability not in contract.capabilities:
        return FacilityAssessment(Availability.UNKNOWN, False, contract.contract_id, "required capability is unavailable")
    return FacilityAssessment(Availability.AVAILABLE, True, contract.contract_id, "required facility capability is available")
