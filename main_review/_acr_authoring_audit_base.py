"""SAE-20 independent ACR Authoring Audit foundation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .assurance_contract_registry import (
    ACRContract,
    CardinalityKind,
    ClosureGrade,
    CollectionRequirement,
    CollectionSemantics,
    ExternalReviewLane,
    NegativeApplicabilityBurden,
    RegistryError,
)
from .review_world import require_full_sha256, sha256_id


class AuthoringAuditStatus(str, Enum):
    CLEAN = "CLEAN"
    DEFICIENT = "DEFICIENT"


class ACREscapeDisposition(str, Enum):
    SUSPEND_OR_REVOKE = "SUSPEND_OR_REVOKE"


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be canonical and non-empty")
    return value


def _strings(values: Sequence[str], field: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a non-string sequence")
    result = tuple(sorted(_string(value, field) for value in values))
    if len(set(result)) != len(result):
        raise ValueError(f"{field} contains duplicates")
    return result


@dataclass(frozen=True)
class AuthoringAuditFinding:
    family: str
    detail: str


@dataclass(frozen=True)
class AuthoringAuditResult:
    status: AuthoringAuditStatus
    findings: tuple[AuthoringAuditFinding, ...]
    qualifies_contract: bool = False


@dataclass(frozen=True)
class AuthoringAuditProfile:
    schema_version: str
    profile_id: str
    generation: str
    contract_id: str
    domain_id: str
    independent_basis_ids: tuple[str, ...]
    required_applicability_facts: tuple[str, ...]
    required_semantic_carriers: tuple[str, ...]
    required_consumer_interpretation_families: tuple[str, ...]
    required_affected_relations: tuple[str, ...]
    required_collections: tuple[CollectionRequirement, ...]
    required_premises: tuple[str, ...]
    required_repeated_authority_premise_families: tuple[str, ...]
    required_obligations: tuple[str, ...]
    required_material_inputs: tuple[str, ...]
    required_coherence_rules: tuple[str, ...]
    required_temporal_rules: tuple[str, ...]
    required_falsifier_families: tuple[str, ...]
    required_independence: tuple[str, ...]
    required_external_review_lanes: tuple[tuple[str, int], ...]
    require_negative_applicability_burden: bool
    require_unknown_fallback: bool
    profile_hash: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        generation: str,
        contract_id: str,
        domain_id: str,
        independent_basis_ids: Sequence[str],
        required_applicability_facts: Sequence[str],
        required_semantic_carriers: Sequence[str],
        required_consumer_interpretation_families: Sequence[str],
        required_affected_relations: Sequence[str],
        required_collections: Sequence[CollectionRequirement],
        required_premises: Sequence[str],
        required_repeated_authority_premise_families: Sequence[str],
        required_obligations: Sequence[str],
        required_material_inputs: Sequence[str],
        required_coherence_rules: Sequence[str],
        required_temporal_rules: Sequence[str],
        required_falsifier_families: Sequence[str],
        required_independence: Sequence[str],
        required_external_review_lanes: Mapping[str, int],
        require_negative_applicability_burden: bool,
        require_unknown_fallback: bool,
    ) -> "AuthoringAuditProfile":
        profile_id = _string(profile_id, "profile_id")
        generation = _string(generation, "audit generation")
        contract_id = _string(contract_id, "contract_id")
        domain_id = _string(domain_id, "domain_id")
        bases = tuple(sorted(require_full_sha256(item, "independent_basis_id") for item in independent_basis_ids))
        if not bases:
            raise ValueError("authoring audit requires at least one independent basis")
        if len(set(bases)) != len(bases):
            raise ValueError("independent basis IDs contain duplicates")
        collections = tuple(sorted(required_collections, key=lambda item: item.family))
        if len({item.family for item in collections}) != len(collections):
            raise ValueError("required collection families contain duplicates")
        for item in collections:
            if not isinstance(item, CollectionRequirement):
                raise ValueError("required_collections contains invalid item")
        if not isinstance(required_external_review_lanes, Mapping):
            raise ValueError("required_external_review_lanes must be a mapping")
        lanes: list[tuple[str, int]] = []
        for name, minimum in required_external_review_lanes.items():
            name = _string(name, "external review lane")
            if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum <= 0:
                raise ValueError("external review lane minimum must be positive")
            lanes.append((name, minimum))
        lanes.sort()
        if require_negative_applicability_burden is not True or require_unknown_fallback is not True:
            raise ValueError("SAE-20 authoring profile must require negative-applicability burden and UNKNOWN fallback")
        kwargs = {
            "required_applicability_facts": _strings(required_applicability_facts, "required_applicability_facts"),
            "required_semantic_carriers": _strings(required_semantic_carriers, "required_semantic_carriers"),
            "required_consumer_interpretation_families": _strings(required_consumer_interpretation_families, "required_consumer_interpretation_families"),
            "required_affected_relations": _strings(required_affected_relations, "required_affected_relations"),
            "required_premises": _strings(required_premises, "required_premises"),
            "required_repeated_authority_premise_families": _strings(required_repeated_authority_premise_families, "required_repeated_authority_premise_families"),
            "required_obligations": _strings(required_obligations, "required_obligations"),
            "required_material_inputs": _strings(required_material_inputs, "required_material_inputs"),
            "required_coherence_rules": _strings(required_coherence_rules, "required_coherence_rules"),
            "required_temporal_rules": _strings(required_temporal_rules, "required_temporal_rules"),
            "required_falsifier_families": _strings(required_falsifier_families, "required_falsifier_families"),
            "required_independence": _strings(required_independence, "required_independence"),
        }
        body = {
            "schema_version": "sergeant.acr-authoring-audit-profile.v1",
            "profile_id": profile_id,
            "generation": generation,
            "contract_id": contract_id,
            "domain_id": domain_id,
            "independent_basis_ids": list(bases),
            **{key: list(value) for key, value in kwargs.items()},
            "required_collections": [item.to_payload() for item in collections],
            "required_external_review_lanes": {name: minimum for name, minimum in lanes},
            "require_negative_applicability_burden": True,
            "require_unknown_fallback": True,
        }
        return cls(
            "sergeant.acr-authoring-audit-profile.v1", profile_id, generation, contract_id, domain_id, bases,
            kwargs["required_applicability_facts"], kwargs["required_semantic_carriers"], kwargs["required_consumer_interpretation_families"], kwargs["required_affected_relations"],
            collections, kwargs["required_premises"], kwargs["required_repeated_authority_premise_families"], kwargs["required_obligations"], kwargs["required_material_inputs"],
            kwargs["required_coherence_rules"], kwargs["required_temporal_rules"], kwargs["required_falsifier_families"],
            kwargs["required_independence"], tuple(lanes), True, True, sha256_id(body),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "profile_id": self.profile_id,
            "generation": self.generation,
            "contract_id": self.contract_id,
            "domain_id": self.domain_id,
            "independent_basis_ids": list(self.independent_basis_ids),
            "required_applicability_facts": list(self.required_applicability_facts),
            "required_semantic_carriers": list(self.required_semantic_carriers),
            "required_consumer_interpretation_families": list(self.required_consumer_interpretation_families),
            "required_affected_relations": list(self.required_affected_relations),
            "required_collections": [item.to_payload() for item in self.required_collections],
            "required_premises": list(self.required_premises),
            "required_repeated_authority_premise_families": list(self.required_repeated_authority_premise_families),
            "required_obligations": list(self.required_obligations),
            "required_material_inputs": list(self.required_material_inputs),
            "required_coherence_rules": list(self.required_coherence_rules),
            "required_temporal_rules": list(self.required_temporal_rules),
            "required_falsifier_families": list(self.required_falsifier_families),
            "required_independence": list(self.required_independence),
            "required_external_review_lanes": {name: minimum for name, minimum in self.required_external_review_lanes},
            "require_negative_applicability_burden": self.require_negative_applicability_burden,
            "require_unknown_fallback": self.require_unknown_fallback,
            "profile_hash": self.profile_hash,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AuthoringAuditProfile":
        expected = set(cls.__dataclass_fields__) - {"required_external_review_lanes"}
        # dataclass names match payload names except the tuple representation of external lanes.
        expected.add("required_external_review_lanes")
        if set(payload) != expected:
            raise ValueError("AuthoringAuditProfile persisted payload has wrong fields")
        if payload["schema_version"] != "sergeant.acr-authoring-audit-profile.v1":
            raise ValueError("unknown AuthoringAuditProfile schema")
        list_fields = [
            "independent_basis_ids", "required_applicability_facts", "required_semantic_carriers", "required_consumer_interpretation_families", "required_affected_relations",
            "required_collections", "required_premises", "required_repeated_authority_premise_families", "required_obligations", "required_material_inputs", "required_coherence_rules",
            "required_temporal_rules", "required_falsifier_families", "required_independence",
        ]
        if any(not isinstance(payload[field], list) for field in list_fields):
            raise ValueError("AuthoringAuditProfile sequence fields must be arrays")
        if not isinstance(payload["required_external_review_lanes"], Mapping):
            raise ValueError("required_external_review_lanes must be an object")
        obj = cls.create(
            profile_id=payload["profile_id"], generation=payload["generation"], contract_id=payload["contract_id"], domain_id=payload["domain_id"],
            independent_basis_ids=payload["independent_basis_ids"], required_applicability_facts=payload["required_applicability_facts"],
            required_semantic_carriers=payload["required_semantic_carriers"], required_consumer_interpretation_families=payload["required_consumer_interpretation_families"], required_affected_relations=payload["required_affected_relations"],
            required_collections=tuple(CollectionRequirement.from_payload(x) for x in payload["required_collections"]),
            required_premises=payload["required_premises"], required_repeated_authority_premise_families=payload["required_repeated_authority_premise_families"], required_obligations=payload["required_obligations"],
            required_material_inputs=payload["required_material_inputs"], required_coherence_rules=payload["required_coherence_rules"],
            required_temporal_rules=payload["required_temporal_rules"], required_falsifier_families=payload["required_falsifier_families"],
            required_independence=payload["required_independence"], required_external_review_lanes=payload["required_external_review_lanes"],
            require_negative_applicability_burden=payload["require_negative_applicability_burden"], require_unknown_fallback=payload["require_unknown_fallback"],
        )
        if require_full_sha256(payload["profile_hash"], "profile_hash") != obj.profile_hash:
            raise ValueError("profile_hash mismatch")
        if obj.to_payload() != payload:
            raise ValueError("AuthoringAuditProfile persisted payload is not canonical")
        return obj


def _families(requirements) -> set[str]:
    return {item.family for item in requirements}


def _finding(findings: list[AuthoringAuditFinding], family: str, detail: str) -> None:
    findings.append(AuthoringAuditFinding(family, detail))


def _closure_rank(grade: ClosureGrade) -> int:
    return {
        ClosureGrade.UNKNOWN: 0,
        ClosureGrade.PARTIAL: 1,
        ClosureGrade.CONSERVATIVE_SUPERSET: 2,
        ClosureGrade.EXACT: 3,
    }[grade]


def _cardinality_at_least(actual, required) -> bool:
    if actual.kind is not required.kind:
        return False
    if required.kind is CardinalityKind.BOUNDED_N:
        # A larger maximum covers at least the independently required bounded universe.
        return actual.maximum is not None and required.maximum is not None and actual.maximum >= required.maximum
    return actual.maximum == required.maximum


def audit_contract_authoring(contract: ACRContract, profile: AuthoringAuditProfile) -> AuthoringAuditResult:
    if not isinstance(contract, ACRContract) or not isinstance(profile, AuthoringAuditProfile):
        raise ValueError("authoring audit requires ACRContract and AuthoringAuditProfile")
    findings: list[AuthoringAuditFinding] = []
    if contract.contract_id != profile.contract_id or contract.domain.domain_id != profile.domain_id:
        _finding(findings, "audit_scope_mismatch", "contract/profile identity or bounded domain mismatch")

    refs = set(contract.applicability.referenced_facts())
    missing = set(profile.required_applicability_facts) - refs
    if missing:
        _finding(findings, "applicability_omission", f"missing applicability facts: {sorted(missing)!r}")

    for family, expected, actual in (
        ("semantic_carrier_omission", set(profile.required_semantic_carriers), set(contract.semantic_carrier_families)),
        ("consumer_interpretation_omission", set(profile.required_consumer_interpretation_families), set(contract.consumer_interpretation_families)),
        ("affected_relation_omission", set(profile.required_affected_relations), set(contract.affected_relation_families)),
        ("premise_omission", set(profile.required_premises), _families(contract.mandatory_premises)),
        ("repeated_authority_premise_omission", set(profile.required_repeated_authority_premise_families), set(contract.repeated_authority_premise_families)),
        ("obligation_omission", set(profile.required_obligations), _families(contract.mandatory_obligations)),
        ("material_input_omission", set(profile.required_material_inputs), _families(contract.material_inputs)),
        ("coherence_rule_omission", set(profile.required_coherence_rules), set(contract.coherence_rules)),
        ("temporal_rule_omission", set(profile.required_temporal_rules), set(contract.temporal_rules)),
        ("falsifier_family_omission", set(profile.required_falsifier_families), set(contract.mandatory_falsifier_families)),
        ("independence_rule_omission", set(profile.required_independence), set(contract.required_independence)),
    ):
        absent = expected - actual
        if absent:
            _finding(findings, family, f"missing required families/rules: {sorted(absent)!r}")

    actual_collections = {item.family: item for item in contract.collections}
    for required in profile.required_collections:
        actual = actual_collections.get(required.family)
        if actual is None:
            _finding(findings, "collection_omission", f"missing collection {required.family}")
            continue
        if actual.semantics is not required.semantics or not _cardinality_at_least(actual.cardinality, required.cardinality):
            _finding(findings, "collection_semantics_or_cardinality_weakening", f"weakened collection {required.family}")
        if _closure_rank(actual.required_closure) < _closure_rank(required.required_closure):
            _finding(findings, "closure_grade_weakening", f"weakened closure for {required.family}")

    actual_lanes = {lane.lane_id: lane.minimum_instances for lane in contract.external_review_lanes}
    for lane_id, required_minimum in profile.required_external_review_lanes:
        if actual_lanes.get(lane_id, 0) < required_minimum:
            _finding(findings, "external_review_lane_cardinality_weakening", f"{lane_id} requires at least {required_minimum}")

    if profile.require_negative_applicability_burden and not isinstance(contract.negative_applicability, NegativeApplicabilityBurden):
        _finding(findings, "negative_applicability_burden_missing", "PROVEN_NO_MATCH burden missing")
    if profile.require_unknown_fallback and contract.unsupported_fallback != "UNKNOWN":
        _finding(findings, "unknown_fallback_weakening", "unsupported fallback must be UNKNOWN")
    if contract.self_qualification_allowed is not False:
        _finding(findings, "candidate_self_qualification", "candidate contract attempted to grant qualification")

    ordered = tuple(sorted(findings, key=lambda item: (item.family, item.detail)))
    return AuthoringAuditResult(AuthoringAuditStatus.DEFICIENT if ordered else AuthoringAuditStatus.CLEAN, ordered, False)


@dataclass(frozen=True)
class ACRQualificationEscapeRecord:
    schema_version: str
    registry_id: str
    contract_id: str
    escaped_generation: str
    defect_family: str
    evidence_ids: tuple[str, ...]
    disposition: ACREscapeDisposition
    impact_analysis_required: bool
    automatic_corrected_contract_promotion_allowed: bool
    permanent_qualification_evidence: bool
    escape_id: str

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "contract_id": self.contract_id,
            "escaped_generation": self.escaped_generation,
            "defect_family": self.defect_family,
            "evidence_ids": list(self.evidence_ids),
            "disposition": self.disposition.value,
            "impact_analysis_required": self.impact_analysis_required,
            "automatic_corrected_contract_promotion_allowed": self.automatic_corrected_contract_promotion_allowed,
            "permanent_qualification_evidence": self.permanent_qualification_evidence,
            "escape_id": self.escape_id,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ACRQualificationEscapeRecord":
        expected = {
            "schema_version", "registry_id", "contract_id", "escaped_generation", "defect_family", "evidence_ids",
            "disposition", "impact_analysis_required", "automatic_corrected_contract_promotion_allowed",
            "permanent_qualification_evidence", "escape_id",
        }
        if set(payload) != expected:
            raise ValueError("ACR qualification escape payload has wrong fields")
        if payload["schema_version"] != "sergeant.acr-qualification-escape.v1":
            raise ValueError("unknown ACR qualification escape schema")
        if payload["disposition"] != ACREscapeDisposition.SUSPEND_OR_REVOKE.value:
            raise ValueError("qualification escape must suspend or revoke")
        if payload["impact_analysis_required"] is not True:
            raise ValueError("qualification escape requires impact analysis")
        if payload["automatic_corrected_contract_promotion_allowed"] is not False:
            raise ValueError("qualification escape cannot auto-promote corrected contract")
        if payload["permanent_qualification_evidence"] is not True:
            raise ValueError("qualification escape must become permanent qualification evidence")
        evidence = payload["evidence_ids"]
        if not isinstance(evidence, list):
            raise ValueError("qualification escape evidence_ids must be an array")
        obj = record_qualification_escape(
            registry_id=payload["registry_id"], contract_id=payload["contract_id"],
            escaped_generation=payload["escaped_generation"], defect_family=payload["defect_family"], evidence_ids=evidence,
        )
        if require_full_sha256(payload["escape_id"], "escape_id") != obj.escape_id:
            raise ValueError("escape_id mismatch")
        if obj.to_payload() != payload:
            raise ValueError("ACR qualification escape payload is non-canonical")
        return obj


def record_qualification_escape(
    *, registry_id: str, contract_id: str, escaped_generation: str, defect_family: str, evidence_ids: Sequence[str]
) -> ACRQualificationEscapeRecord:
    registry_id = require_full_sha256(registry_id, "registry_id")
    contract_id = _string(contract_id, "contract_id")
    escaped_generation = _string(escaped_generation, "escaped_generation")
    defect_family = _string(defect_family, "defect_family")
    evidence = tuple(sorted(require_full_sha256(item, "evidence_id") for item in evidence_ids))
    if not evidence:
        raise ValueError("qualification escape requires evidence")
    if len(set(evidence)) != len(evidence):
        raise ValueError("qualification escape evidence contains duplicates")
    body = {
        "schema_version": "sergeant.acr-qualification-escape.v1",
        "registry_id": registry_id,
        "contract_id": contract_id,
        "escaped_generation": escaped_generation,
        "defect_family": defect_family,
        "evidence_ids": list(evidence),
        "disposition": ACREscapeDisposition.SUSPEND_OR_REVOKE.value,
        "impact_analysis_required": True,
        "automatic_corrected_contract_promotion_allowed": False,
        "permanent_qualification_evidence": True,
    }
    return ACRQualificationEscapeRecord(
        body["schema_version"], registry_id, contract_id, escaped_generation, defect_family, evidence,
        ACREscapeDisposition.SUSPEND_OR_REVOKE, True, False, True, sha256_id(body),
    )
