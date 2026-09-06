"""SAE-20 ACR Authoring Audit v2 authority boundary.

The v1 implementation is retained privately as a non-qualifying omission-audit
base.  This public boundary adds the authority-integrity checks found missing by
post-publication hostile review.  CLEAN still never means QUALIFIED.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from . import _acr_authoring_audit_base as _base
from .assurance_contract_registry import (
    ACRContract,
    ApplicabilityPredicate,
    BoundedDomain,
    ClosureGrade,
    ContractRequirement,
    NegativeApplicabilityBurden,
)
from .review_world import require_full_sha256, sha256_id

AuthoringAuditStatus = _base.AuthoringAuditStatus
ACREscapeDisposition = _base.ACREscapeDisposition
AuthoringAuditFinding = _base.AuthoringAuditFinding
AuthoringAuditResult = _base.AuthoringAuditResult
ACRQualificationEscapeRecord = _base.ACRQualificationEscapeRecord

_MUTABLE_GENERATION_ALIASES = {"latest", "current", "head", "tip", "main", "master"}


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field} must be canonical and non-empty")
    return value


def _generation(value: object, field: str) -> str:
    generation = _string(value, field)
    if generation.lower() in _MUTABLE_GENERATION_ALIASES:
        raise ValueError(f"{field} cannot use mutable authority alias {generation!r}")
    return generation


def _requirement_map(
    values: Sequence[str | ContractRequirement], field: str
) -> tuple[tuple[str, ClosureGrade], ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be a non-string sequence")
    normalized: list[tuple[str, ClosureGrade]] = []
    for item in values:
        if isinstance(item, str):
            requirement = ContractRequirement.create(item, ClosureGrade.EXACT)
        elif isinstance(item, ContractRequirement):
            requirement = ContractRequirement.from_payload(item.to_payload())
        else:
            raise ValueError(f"{field} contains invalid requirement")
        normalized.append((requirement.family, requirement.required_closure))
    normalized.sort(key=lambda item: item[0])
    if len({family for family, _ in normalized}) != len(normalized):
        raise ValueError(f"{field} contains duplicate families")
    return tuple(normalized)


def _requirements_payload(values: tuple[tuple[str, ClosureGrade], ...]) -> list[dict[str, str]]:
    return [{"family": family, "required_closure": grade.value} for family, grade in values]


def _requirements_from_payload(value: object, field: str) -> tuple[tuple[str, ClosureGrade], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    items: list[ContractRequirement] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ValueError(f"{field} entries must be objects")
        items.append(ContractRequirement.from_payload(raw))
    return _requirement_map(items, field)


def _closure_rank(grade: ClosureGrade) -> int:
    return {
        ClosureGrade.UNKNOWN: 0,
        ClosureGrade.PARTIAL: 1,
        ClosureGrade.CONSERVATIVE_SUPERSET: 2,
        ClosureGrade.EXACT: 3,
    }[grade]


@dataclass(frozen=True)
class AuthoringAuditProfile:
    schema_version: str
    base_profile: _base.AuthoringAuditProfile
    domain_generation: str
    domain_hash: str
    expected_applicability: ApplicabilityPredicate
    required_premise_closures: tuple[tuple[str, ClosureGrade], ...]
    required_obligation_closures: tuple[tuple[str, ClosureGrade], ...]
    required_material_input_closures: tuple[tuple[str, ClosureGrade], ...]
    profile_hash: str

    @classmethod
    def create(
        cls,
        *,
        profile_id: str,
        generation: str,
        contract_id: str,
        domain: BoundedDomain,
        expected_applicability: ApplicabilityPredicate,
        independent_basis_ids: Sequence[str],
        required_semantic_carriers: Sequence[str],
        required_consumer_interpretation_families: Sequence[str],
        required_affected_relations: Sequence[str],
        required_collections: Sequence,
        required_premises: Sequence[str | ContractRequirement],
        required_repeated_authority_premise_families: Sequence[str],
        required_obligations: Sequence[str | ContractRequirement],
        required_material_inputs: Sequence[str | ContractRequirement],
        required_coherence_rules: Sequence[str],
        required_temporal_rules: Sequence[str],
        required_falsifier_families: Sequence[str],
        required_independence: Sequence[str],
        required_external_review_lanes: Mapping[str, int],
        require_negative_applicability_burden: bool,
        require_unknown_fallback: bool,
    ) -> "AuthoringAuditProfile":
        generation = _generation(generation, "audit generation")
        if not isinstance(domain, BoundedDomain):
            raise ValueError("authoring profile domain must be a BoundedDomain")
        domain = BoundedDomain.from_payload(domain.to_payload())
        domain_generation = _generation(domain.generation, "bounded-domain generation")
        if not isinstance(expected_applicability, ApplicabilityPredicate):
            raise ValueError("expected_applicability must be declarative ApplicabilityPredicate")
        expected_applicability = ApplicabilityPredicate.from_payload(expected_applicability.to_payload())

        premise_closures = _requirement_map(required_premises, "required_premises")
        obligation_closures = _requirement_map(required_obligations, "required_obligations")
        material_input_closures = _requirement_map(required_material_inputs, "required_material_inputs")

        base = _base.AuthoringAuditProfile.create(
            profile_id=profile_id,
            generation=generation,
            contract_id=contract_id,
            domain_id=domain.domain_id,
            independent_basis_ids=independent_basis_ids,
            required_applicability_facts=expected_applicability.referenced_facts(),
            required_semantic_carriers=required_semantic_carriers,
            required_consumer_interpretation_families=required_consumer_interpretation_families,
            required_affected_relations=required_affected_relations,
            required_collections=required_collections,
            required_premises=tuple(family for family, _ in premise_closures),
            required_repeated_authority_premise_families=required_repeated_authority_premise_families,
            required_obligations=tuple(family for family, _ in obligation_closures),
            required_material_inputs=tuple(family for family, _ in material_input_closures),
            required_coherence_rules=required_coherence_rules,
            required_temporal_rules=required_temporal_rules,
            required_falsifier_families=required_falsifier_families,
            required_independence=required_independence,
            required_external_review_lanes=required_external_review_lanes,
            require_negative_applicability_burden=require_negative_applicability_burden,
            require_unknown_fallback=require_unknown_fallback,
        )
        body = {
            "schema_version": "sergeant.acr-authoring-audit-profile.v2",
            "base_profile": base.to_payload(),
            "domain_generation": domain_generation,
            "domain_hash": domain.domain_hash,
            "expected_applicability": expected_applicability.to_payload(),
            "required_premise_closures": _requirements_payload(premise_closures),
            "required_obligation_closures": _requirements_payload(obligation_closures),
            "required_material_input_closures": _requirements_payload(material_input_closures),
        }
        return cls(
            body["schema_version"], base, domain_generation, require_full_sha256(domain.domain_hash, "domain_hash"),
            expected_applicability, premise_closures, obligation_closures, material_input_closures, sha256_id(body),
        )

    def __getattr__(self, name: str):
        # Preserve read-only v1 profile access for callers while keeping v2
        # authority fields explicit on this wrapper.
        return getattr(self.base_profile, name)

    @property
    def independent_basis_ids(self) -> tuple[str, ...]:
        return self.base_profile.independent_basis_ids

    @property
    def required_premises(self) -> tuple[ContractRequirement, ...]:
        return tuple(ContractRequirement.create(family, grade) for family, grade in self.required_premise_closures)

    @property
    def required_obligations(self) -> tuple[ContractRequirement, ...]:
        return tuple(ContractRequirement.create(family, grade) for family, grade in self.required_obligation_closures)

    @property
    def required_material_inputs(self) -> tuple[ContractRequirement, ...]:
        return tuple(ContractRequirement.create(family, grade) for family, grade in self.required_material_input_closures)

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "base_profile": self.base_profile.to_payload(),
            "domain_generation": self.domain_generation,
            "domain_hash": self.domain_hash,
            "expected_applicability": self.expected_applicability.to_payload(),
            "required_premise_closures": _requirements_payload(self.required_premise_closures),
            "required_obligation_closures": _requirements_payload(self.required_obligation_closures),
            "required_material_input_closures": _requirements_payload(self.required_material_input_closures),
            "profile_hash": self.profile_hash,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "AuthoringAuditProfile":
        expected = {
            "schema_version", "base_profile", "domain_generation", "domain_hash", "expected_applicability",
            "required_premise_closures", "required_obligation_closures", "required_material_input_closures", "profile_hash",
        }
        if set(payload) != expected or payload["schema_version"] != "sergeant.acr-authoring-audit-profile.v2":
            raise ValueError("AuthoringAuditProfile persisted payload is not v2 canonical shape")
        if not isinstance(payload["base_profile"], Mapping) or not isinstance(payload["expected_applicability"], Mapping):
            raise ValueError("AuthoringAuditProfile nested authority must be objects")
        base = _base.AuthoringAuditProfile.from_payload(payload["base_profile"])
        expected_applicability = ApplicabilityPredicate.from_payload(payload["expected_applicability"])
        premise = _requirements_from_payload(payload["required_premise_closures"], "required_premise_closures")
        obligation = _requirements_from_payload(payload["required_obligation_closures"], "required_obligation_closures")
        material = _requirements_from_payload(payload["required_material_input_closures"], "required_material_input_closures")
        generation = _generation(payload["domain_generation"], "domain_generation")
        domain_hash = require_full_sha256(payload["domain_hash"], "domain_hash")
        body = {
            "schema_version": payload["schema_version"],
            "base_profile": base.to_payload(),
            "domain_generation": generation,
            "domain_hash": domain_hash,
            "expected_applicability": expected_applicability.to_payload(),
            "required_premise_closures": _requirements_payload(premise),
            "required_obligation_closures": _requirements_payload(obligation),
            "required_material_input_closures": _requirements_payload(material),
        }
        profile_hash = require_full_sha256(payload["profile_hash"], "profile_hash")
        if sha256_id(body) != profile_hash:
            raise ValueError("profile_hash mismatch")
        obj = cls(body["schema_version"], base, generation, domain_hash, expected_applicability, premise, obligation, material, profile_hash)
        if obj.to_payload() != payload:
            raise ValueError("AuthoringAuditProfile persisted payload is not canonical")
        return obj


def _closure_findings(actual: Sequence[ContractRequirement], required: tuple[tuple[str, ClosureGrade], ...], label: str) -> list[AuthoringAuditFinding]:
    actual_by_family = {item.family: item.required_closure for item in actual}
    findings: list[AuthoringAuditFinding] = []
    for family, expected in required:
        observed = actual_by_family.get(family)
        if observed is not None and _closure_rank(observed) < _closure_rank(expected):
            findings.append(AuthoringAuditFinding(
                "closure_grade_weakening",
                f"weakened {label} closure for {family}: {observed.value} < {expected.value}",
            ))
    return findings


def audit_contract_authoring(contract: ACRContract, profile: AuthoringAuditProfile) -> AuthoringAuditResult:
    if not isinstance(contract, ACRContract) or not isinstance(profile, AuthoringAuditProfile):
        raise ValueError("authoring audit requires ACRContract and AuthoringAuditProfile")
    try:
        contract = ACRContract.from_payload(contract.to_payload())
    except Exception as error:
        findings = [AuthoringAuditFinding("noncanonical_contract", f"contract failed canonical validation: {type(error).__name__}")]
        if not isinstance(getattr(contract, "negative_applicability", None), NegativeApplicabilityBurden):
            findings.append(AuthoringAuditFinding("negative_applicability_burden_missing", "PROVEN_NO_MATCH burden missing"))
        if getattr(contract, "unsupported_fallback", None) != "UNKNOWN":
            findings.append(AuthoringAuditFinding("unknown_fallback_weakening", "unsupported fallback must be UNKNOWN"))
        if getattr(contract, "self_qualification_allowed", False) is not False:
            findings.append(AuthoringAuditFinding("candidate_self_qualification", "candidate contract attempted to grant qualification"))
        return AuthoringAuditResult(AuthoringAuditStatus.DEFICIENT, tuple(sorted(findings, key=lambda item: (item.family, item.detail))), False)
    try:
        profile = AuthoringAuditProfile.from_payload(profile.to_payload())
    except Exception as error:
        return AuthoringAuditResult(
            AuthoringAuditStatus.DEFICIENT,
            (AuthoringAuditFinding("noncanonical_profile", f"profile failed canonical validation: {type(error).__name__}"),),
            False,
        )

    base_result = _base.audit_contract_authoring(contract, profile.base_profile)
    findings = list(base_result.findings)

    if contract.domain.generation != profile.domain_generation or contract.domain.domain_hash != profile.domain_hash:
        findings.append(AuthoringAuditFinding("audit_scope_mismatch", "exact bounded-domain generation/hash differs from authoring profile"))
    if contract.applicability.to_payload() != profile.expected_applicability.to_payload():
        findings.append(AuthoringAuditFinding("applicability_semantics_weakening", "candidate applicability predicate differs from independently expected predicate"))
    if contract.generation.lower() in _MUTABLE_GENERATION_ALIASES or contract.domain.generation.lower() in _MUTABLE_GENERATION_ALIASES:
        findings.append(AuthoringAuditFinding("mutable_generation_alias", "contract/domain generation uses mutable authority alias"))

    findings.extend(_closure_findings(contract.mandatory_premises, profile.required_premise_closures, "premise"))
    findings.extend(_closure_findings(contract.mandatory_obligations, profile.required_obligation_closures, "obligation"))
    findings.extend(_closure_findings(contract.material_inputs, profile.required_material_input_closures, "material input"))

    ordered = tuple(sorted(set(findings), key=lambda item: (item.family, item.detail)))
    return AuthoringAuditResult(AuthoringAuditStatus.DEFICIENT if ordered else AuthoringAuditStatus.CLEAN, ordered, False)


def record_qualification_escape(
    *, registry_id: str, contract_id: str, escaped_generation: str, defect_family: str, evidence_ids: Sequence[str]
) -> ACRQualificationEscapeRecord:
    escaped_generation = _generation(escaped_generation, "escaped_generation")
    return _base.record_qualification_escape(
        registry_id=registry_id,
        contract_id=contract_id,
        escaped_generation=escaped_generation,
        defect_family=defect_family,
        evidence_ids=evidence_ids,
    )
