"""SAE-80 Evidence + Proof World candidate substrate.

This module consumes already-qualified SAE-70 contract/instance/obligation
authority and constructs a content-addressed evidence world for one exact
expected obligation.  It is deliberately conservative: authority is bound to
the exact qualified ACR registry, evidence cannot mix world generations,
material inputs are unioned across every obligation origin, proof classes have
mechanical ceilings, unresolved assumptions and contradictions remain visible,
and unsupported coherence/temporal rules fail closed.

This is a Task 11 candidate mechanism only.  It does not define or grant the
Task 12 ``QUALIFIED_EVIDENCE_CONTRACT`` or ``QUALIFIED_PROOF_WORLD`` authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math

from .assurance_contract_registry import ACRContract, ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation, ObligationProvenance
from .contract_closure_protocol import (
    QualifiedContractClosure,
    validate_qualified_contract_closure,
)
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class ProofWorldError(ReviewWorldError):
    """Raised for malformed or inadmissible SAE-80 Proof World inputs."""


class ProofClass(str, Enum):
    MECHANICAL = "mechanical"
    EXHAUSTIVE_ORACLE = "exhaustive-oracle"
    HEURISTIC = "heuristic"


class AssumptionKind(str, Enum):
    VERIFIED = "VERIFIED"
    DECLARED = "DECLARED"
    UNRESOLVED = "UNRESOLVED"


_GRADE_RANK = {
    ClosureGrade.UNKNOWN: 0,
    ClosureGrade.PARTIAL: 1,
    ClosureGrade.CONSERVATIVE_SUPERSET: 2,
    ClosureGrade.EXACT: 3,
}

_PROOF_CEILINGS = {
    ProofClass.MECHANICAL: ClosureGrade.EXACT,
    ProofClass.EXHAUSTIVE_ORACLE: ClosureGrade.EXACT,
    ProofClass.HEURISTIC: ClosureGrade.CONSERVATIVE_SUPERSET,
}

_SUPPORTED_COHERENCE_RULES = {
    "same-candidate-generation",
    "same-framework-generation",
    "same-provider-generation",
    "same-dependency-generation",
}
_SUPPORTED_TEMPORAL_RULES = {"evidence-not-older-than-world"}


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProofWorldError(f"{field} must be a canonical non-empty string")
    return value


def _require_sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise ProofWorldError(str(exc)) from exc


def _weaker(left: ClosureGrade, right: ClosureGrade) -> ClosureGrade:
    return left if _GRADE_RANK[left] <= _GRADE_RANK[right] else right


def _stronger(left: ClosureGrade, right: ClosureGrade) -> ClosureGrade:
    return left if _GRADE_RANK[left] >= _GRADE_RANK[right] else right


def _meets(actual: ClosureGrade, required: ClosureGrade) -> bool:
    return _GRADE_RANK[actual] >= _GRADE_RANK[required]


def _scalar(value: object, field: str) -> object:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProofWorldError(f"{field} rejects non-finite numbers")
        return value
    raise ProofWorldError(f"{field} must be an immutable JSON scalar")


def _scalar_key(value: object) -> tuple[str, str]:
    value = _scalar(value, "claim value")
    return (type(value).__name__, sha256_id({"value": value}))


def _world_body(
    *,
    candidate_generation: str,
    framework_generation: str,
    provider_generation: str,
    dependency_generations: tuple[tuple[str, str], ...],
    epoch: int,
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-world-coordinates.v1",
        "candidate_generation": candidate_generation,
        "framework_generation": framework_generation,
        "provider_generation": provider_generation,
        "dependency_generations": dict(dependency_generations),
        "epoch": epoch,
    }


@dataclass(frozen=True)
class WorldCoordinates:
    candidate_generation: str
    framework_generation: str
    provider_generation: str
    dependency_generations: tuple[tuple[str, str], ...]
    epoch: int
    world_id: str

    @classmethod
    def create(
        cls,
        *,
        candidate_generation: str,
        framework_generation: str,
        provider_generation: str,
        dependency_generations: Mapping[str, str],
        epoch: int,
    ) -> "WorldCoordinates":
        candidate_generation = _string(candidate_generation, "candidate generation")
        framework_generation = _string(framework_generation, "framework generation")
        provider_generation = _string(provider_generation, "provider generation")
        if not isinstance(dependency_generations, Mapping):
            raise ProofWorldError("dependency generations must be a mapping")
        normalized: list[tuple[str, str]] = []
        for name, generation in dependency_generations.items():
            normalized.append(
                (
                    _string(name, "dependency name"),
                    _string(generation, "dependency generation"),
                )
            )
        normalized.sort()
        if len({name for name, _ in normalized}) != len(normalized):
            raise ProofWorldError("dependency generations contain duplicate names")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ProofWorldError("world epoch must be a non-negative integer")
        dependencies = tuple(normalized)
        body = _world_body(
            candidate_generation=candidate_generation,
            framework_generation=framework_generation,
            provider_generation=provider_generation,
            dependency_generations=dependencies,
            epoch=epoch,
        )
        return cls(
            candidate_generation,
            framework_generation,
            provider_generation,
            dependencies,
            epoch,
            sha256_id(body),
        )


def _validate_world(value: WorldCoordinates) -> WorldCoordinates:
    if not isinstance(value, WorldCoordinates):
        raise ProofWorldError("Proof World coordinates have invalid record type")
    canonical = WorldCoordinates.create(
        candidate_generation=value.candidate_generation,
        framework_generation=value.framework_generation,
        provider_generation=value.provider_generation,
        dependency_generations=dict(value.dependency_generations),
        epoch=value.epoch,
    )
    if canonical != value:
        raise ProofWorldError("Proof World coordinates identity mismatch")
    return value


def _material_body(*, family: str, closure: ClosureGrade, basis_id: str) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-material-input-proof.v1",
        "family": family,
        "closure": closure.value,
        "basis_id": basis_id,
    }


@dataclass(frozen=True)
class MaterialInputProof:
    family: str
    closure: ClosureGrade
    basis_id: str
    material_input_id: str

    @classmethod
    def create(
        cls,
        *,
        family: str,
        closure: ClosureGrade,
        basis_id: str,
    ) -> "MaterialInputProof":
        family = _string(family, "material-input family")
        if not isinstance(closure, ClosureGrade):
            raise ProofWorldError("material-input closure is invalid")
        basis_id = _require_sha(basis_id, "material-input basis_id")
        body = _material_body(family=family, closure=closure, basis_id=basis_id)
        return cls(family, closure, basis_id, sha256_id(body))


def _validate_material(value: MaterialInputProof) -> MaterialInputProof:
    if not isinstance(value, MaterialInputProof):
        raise ProofWorldError("material-input proof has invalid record type")
    canonical = MaterialInputProof.create(
        family=value.family,
        closure=value.closure,
        basis_id=value.basis_id,
    )
    if canonical != value:
        raise ProofWorldError("material-input proof identity mismatch")
    return value


def _assumption_body(*, assumption_id: str, kind: AssumptionKind, basis_id: str) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-assumption.v1",
        "assumption_id": assumption_id,
        "kind": kind.value,
        "basis_id": basis_id,
    }


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    kind: AssumptionKind
    basis_id: str
    record_id: str

    @classmethod
    def create(
        cls,
        *,
        assumption_id: str,
        kind: AssumptionKind,
        basis_id: str,
    ) -> "Assumption":
        assumption_id = _string(assumption_id, "assumption ID")
        if not isinstance(kind, AssumptionKind):
            raise ProofWorldError("assumption kind is invalid")
        basis_id = _require_sha(basis_id, "assumption basis_id")
        body = _assumption_body(assumption_id=assumption_id, kind=kind, basis_id=basis_id)
        return cls(assumption_id, kind, basis_id, sha256_id(body))


def _validate_assumption(value: Assumption) -> Assumption:
    if not isinstance(value, Assumption):
        raise ProofWorldError("assumption has invalid record type")
    canonical = Assumption.create(
        assumption_id=value.assumption_id,
        kind=value.kind,
        basis_id=value.basis_id,
    )
    if canonical != value:
        raise ProofWorldError("assumption identity mismatch")
    return value


def _evidence_body(
    *,
    proof_class: ProofClass,
    claimed_closure: ClosureGrade,
    obligation_id: str,
    contract_instance_ids: tuple[str, ...],
    world_id: str,
    material_inputs: tuple[MaterialInputProof, ...],
    claims: tuple[tuple[str, object], ...],
    assumptions: tuple[Assumption, ...],
    observed_epoch: int,
    evidence_basis_id: str,
    proof_ceiling: ClosureGrade,
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-evidence-proof.v1",
        "proof_class": proof_class.value,
        "claimed_closure": claimed_closure.value,
        "obligation_id": obligation_id,
        "contract_instance_ids": list(contract_instance_ids),
        "world_id": world_id,
        "material_input_ids": [item.material_input_id for item in material_inputs],
        "claims": dict(claims),
        "assumption_record_ids": [item.record_id for item in assumptions],
        "observed_epoch": observed_epoch,
        "evidence_basis_id": evidence_basis_id,
        "proof_ceiling": proof_ceiling.value,
    }


@dataclass(frozen=True)
class EvidenceProof:
    proof_class: ProofClass
    claimed_closure: ClosureGrade
    obligation_id: str
    contract_instance_ids: tuple[str, ...]
    world_id: str
    material_inputs: tuple[MaterialInputProof, ...]
    claims: tuple[tuple[str, object], ...]
    assumptions: tuple[Assumption, ...]
    observed_epoch: int
    evidence_basis_id: str
    proof_ceiling: ClosureGrade
    evidence_id: str

    @classmethod
    def create(
        cls,
        *,
        proof_class: ProofClass,
        claimed_closure: ClosureGrade,
        obligation_id: str,
        contract_instance_ids: Sequence[str],
        world: WorldCoordinates,
        material_inputs: Sequence[MaterialInputProof],
        claims: Mapping[str, object],
        assumptions: Sequence[Assumption],
        observed_epoch: int,
        evidence_basis_id: str,
    ) -> "EvidenceProof":
        if not isinstance(proof_class, ProofClass):
            raise ProofWorldError("evidence proof class is invalid")
        if not isinstance(claimed_closure, ClosureGrade):
            raise ProofWorldError("evidence claimed closure is invalid")
        ceiling = _PROOF_CEILINGS[proof_class]
        if not _meets(ceiling, claimed_closure):
            raise ProofWorldError(
                f"{proof_class.value} proof ceiling {ceiling.value} cannot claim {claimed_closure.value}"
            )
        obligation_id = _require_sha(obligation_id, "evidence obligation_id")
        if isinstance(contract_instance_ids, (str, bytes)):
            raise ProofWorldError("evidence contract instance IDs must be a non-string sequence")
        instance_ids = tuple(sorted(_require_sha(value, "evidence contract instance id") for value in contract_instance_ids))
        if len(set(instance_ids)) != len(instance_ids):
            raise ProofWorldError("evidence contract instance IDs contain duplicates")
        world = _validate_world(world)
        if isinstance(material_inputs, (str, bytes)):
            raise ProofWorldError("evidence material inputs must be a non-string sequence")
        materials = tuple(sorted((_validate_material(value) for value in material_inputs), key=lambda item: (item.family, item.material_input_id)))
        if len({item.family for item in materials}) != len(materials):
            raise ProofWorldError("evidence material inputs contain duplicate families")
        if not isinstance(claims, Mapping):
            raise ProofWorldError("evidence claims must be a mapping")
        claim_items: list[tuple[str, object]] = []
        for name, value in claims.items():
            claim_items.append((_string(name, "claim name"), _scalar(value, "claim value")))
        claim_items.sort(key=lambda item: item[0])
        if len({name for name, _ in claim_items}) != len(claim_items):
            raise ProofWorldError("evidence claims contain duplicate names")
        normalized_claims = tuple(claim_items)
        if isinstance(assumptions, (str, bytes)):
            raise ProofWorldError("evidence assumptions must be a non-string sequence")
        assumption_items = tuple(sorted((_validate_assumption(value) for value in assumptions), key=lambda item: (item.assumption_id, item.record_id)))
        if len({item.assumption_id for item in assumption_items}) != len(assumption_items):
            raise ProofWorldError("evidence assumptions contain duplicate assumption IDs")
        if isinstance(observed_epoch, bool) or not isinstance(observed_epoch, int) or observed_epoch < 0:
            raise ProofWorldError("evidence observed epoch must be a non-negative integer")
        evidence_basis_id = _require_sha(evidence_basis_id, "evidence basis_id")
        body = _evidence_body(
            proof_class=proof_class,
            claimed_closure=claimed_closure,
            obligation_id=obligation_id,
            contract_instance_ids=instance_ids,
            world_id=world.world_id,
            material_inputs=materials,
            claims=normalized_claims,
            assumptions=assumption_items,
            observed_epoch=observed_epoch,
            evidence_basis_id=evidence_basis_id,
            proof_ceiling=ceiling,
        )
        return cls(
            proof_class,
            claimed_closure,
            obligation_id,
            instance_ids,
            world.world_id,
            materials,
            normalized_claims,
            assumption_items,
            observed_epoch,
            evidence_basis_id,
            ceiling,
            sha256_id(body),
        )


def _validate_evidence(value: EvidenceProof) -> EvidenceProof:
    if not isinstance(value, EvidenceProof):
        raise ProofWorldError("evidence has invalid record type")
    if not isinstance(value.proof_class, ProofClass):
        raise ProofWorldError("evidence proof class is invalid")
    if not isinstance(value.claimed_closure, ClosureGrade):
        raise ProofWorldError("evidence claimed closure is invalid")
    expected_ceiling = _PROOF_CEILINGS[value.proof_class]
    if value.proof_ceiling is not expected_ceiling:
        raise ProofWorldError("evidence proof ceiling identity mismatch")
    if not _meets(expected_ceiling, value.claimed_closure):
        raise ProofWorldError("evidence claimed closure exceeds proof ceiling")
    _require_sha(value.obligation_id, "evidence obligation_id")
    instance_ids = tuple(sorted(_require_sha(item, "evidence contract instance id") for item in value.contract_instance_ids))
    if instance_ids != value.contract_instance_ids or len(set(instance_ids)) != len(instance_ids):
        raise ProofWorldError("evidence contract instance IDs are not canonical")
    materials = tuple(sorted((_validate_material(item) for item in value.material_inputs), key=lambda item: (item.family, item.material_input_id)))
    if materials != value.material_inputs or len({item.family for item in materials}) != len(materials):
        raise ProofWorldError("evidence material inputs are not canonical")
    claims: list[tuple[str, object]] = []
    for name, claim_value in value.claims:
        claims.append((_string(name, "claim name"), _scalar(claim_value, "claim value")))
    normalized_claims = tuple(sorted(claims, key=lambda item: item[0]))
    if normalized_claims != value.claims or len({name for name, _ in normalized_claims}) != len(normalized_claims):
        raise ProofWorldError("evidence claims are not canonical")
    assumptions = tuple(sorted((_validate_assumption(item) for item in value.assumptions), key=lambda item: (item.assumption_id, item.record_id)))
    if assumptions != value.assumptions or len({item.assumption_id for item in assumptions}) != len(assumptions):
        raise ProofWorldError("evidence assumptions are not canonical")
    if isinstance(value.observed_epoch, bool) or not isinstance(value.observed_epoch, int) or value.observed_epoch < 0:
        raise ProofWorldError("evidence observed epoch is invalid")
    _require_sha(value.world_id, "evidence world_id")
    _require_sha(value.evidence_basis_id, "evidence basis_id")
    body = _evidence_body(
        proof_class=value.proof_class,
        claimed_closure=value.claimed_closure,
        obligation_id=value.obligation_id,
        contract_instance_ids=value.contract_instance_ids,
        world_id=value.world_id,
        material_inputs=value.material_inputs,
        claims=value.claims,
        assumptions=value.assumptions,
        observed_epoch=value.observed_epoch,
        evidence_basis_id=value.evidence_basis_id,
        proof_ceiling=value.proof_ceiling,
    )
    if value.evidence_id != sha256_id(body):
        raise ProofWorldError("evidence proof identity mismatch")
    return value


def _obligation_body(value: ExpectedObligation) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae70-expected-obligation.v1",
        "family": value.family,
        "bindings": dict(value.bindings),
        "required_closure": value.required_closure.value,
        "provenance": [
            {
                "contract_id": origin.contract_id,
                "contract_generation": origin.contract_generation,
                "contract_instance_id": origin.contract_instance_id,
                "required_closure": origin.required_closure.value,
            }
            for origin in value.provenance
        ],
    }


def _validate_expected_obligation(
    value: ExpectedObligation,
    *,
    qualified: QualifiedContractClosure,
    registry: ACRRegistry,
) -> tuple[ExpectedObligation, tuple[ACRContract, ...]]:
    if not isinstance(value, ExpectedObligation):
        raise ProofWorldError("expected obligation has invalid record type")
    family = _string(value.family, "expected obligation family")
    if not isinstance(value.required_closure, ClosureGrade):
        raise ProofWorldError("expected obligation required closure is invalid")
    bindings = tuple(value.bindings)
    if bindings != tuple(sorted(bindings)):
        raise ProofWorldError("expected obligation bindings are not canonical")
    for name, binding_value in bindings:
        _string(name, "expected obligation binding name")
        _string(binding_value, "expected obligation binding value")
    if len({name for name, _ in bindings}) != len(bindings):
        raise ProofWorldError("expected obligation bindings contain duplicates")
    if not value.provenance:
        raise ProofWorldError("expected obligation requires provenance")
    canonical_provenance = tuple(
        sorted(
            value.provenance,
            key=lambda origin: (
                origin.contract_id,
                origin.contract_generation,
                origin.contract_instance_id,
                origin.required_closure.value if isinstance(origin.required_closure, ClosureGrade) else "",
            ),
        )
    )
    if canonical_provenance != value.provenance:
        raise ProofWorldError("expected obligation provenance is not canonical")
    if len({(origin.contract_id, origin.contract_instance_id) for origin in value.provenance}) != len(value.provenance):
        raise ProofWorldError("expected obligation provenance contains duplicates")

    contract_by_id = {contract.contract_id: contract for contract in registry.contracts}
    origin_contracts: list[ACRContract] = []
    strongest = ClosureGrade.UNKNOWN
    distinct_requirements: set[ClosureGrade] = set()
    for origin in value.provenance:
        if not isinstance(origin, ObligationProvenance):
            raise ProofWorldError("expected obligation provenance has invalid record type")
        contract_id = _string(origin.contract_id, "obligation provenance contract ID")
        generation = _string(origin.contract_generation, "obligation provenance contract generation")
        instance_id = _require_sha(origin.contract_instance_id, "obligation provenance contract instance ID")
        if not isinstance(origin.required_closure, ClosureGrade):
            raise ProofWorldError("obligation provenance required closure is invalid")
        if instance_id not in qualified.expected_instance_ids:
            raise ProofWorldError("expected obligation provenance is not bound to SAE-70 qualified instances")
        contract = contract_by_id.get(contract_id)
        if contract is None or contract.generation != generation:
            raise ProofWorldError("expected obligation provenance contract is not bound to qualified registry")
        matching = [
            requirement
            for requirement in contract.mandatory_obligations
            if requirement.family == family
        ]
        if len(matching) != 1 or matching[0].required_closure is not origin.required_closure:
            raise ProofWorldError("expected obligation provenance does not match registry obligation requirement")
        strongest = _stronger(strongest, origin.required_closure)
        distinct_requirements.add(origin.required_closure)
        origin_contracts.append(contract)

    if value.required_closure is not strongest:
        raise ProofWorldError("expected obligation strongest closure invariant mismatch")
    derived_conflict = len(distinct_requirements) > 1
    if value.conflict_resolved_conservatively is not derived_conflict:
        raise ProofWorldError("expected obligation conservative-conflict flag mismatch")
    if value.obligation_id != sha256_id(_obligation_body(value)):
        raise ProofWorldError("expected obligation identity mismatch")
    if value.obligation_id not in qualified.expected_obligation_ids:
        raise ProofWorldError("expected obligation is not bound to SAE-70 qualified authority")
    return value, tuple(origin_contracts)


@dataclass(frozen=True)
class Contradiction:
    claim: str
    values: tuple[object, ...]
    evidence_ids: tuple[str, ...]
    contradiction_id: str


def _contradiction_body(value: Contradiction) -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-contradiction.v1",
        "claim": value.claim,
        "values": list(value.values),
        "evidence_ids": list(value.evidence_ids),
    }


def _validate_contradiction(value: Contradiction) -> Contradiction:
    if not isinstance(value, Contradiction):
        raise ProofWorldError("contradiction has invalid record type")
    _string(value.claim, "contradiction claim")
    if len(value.values) < 2:
        raise ProofWorldError("contradiction requires at least two distinct values")
    values = tuple(sorted((_scalar(item, "contradiction value") for item in value.values), key=_scalar_key))
    if values != value.values or len({_scalar_key(item) for item in values}) != len(values):
        raise ProofWorldError("contradiction values are not canonical and distinct")
    evidence_ids = tuple(sorted(_require_sha(item, "contradiction evidence id") for item in value.evidence_ids))
    if evidence_ids != value.evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
        raise ProofWorldError("contradiction evidence IDs are not canonical")
    if value.contradiction_id != sha256_id(_contradiction_body(value)):
        raise ProofWorldError("contradiction identity mismatch")
    return value


def _proof_world_body(value: "ProofWorld") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-proof-world.v1",
        "qualified_closure_id": value.qualified_closure_id,
        "obligation_id": value.obligation_id,
        "world_id": value.world_id,
        "grade": value.grade.value,
        "material_input_ids": [item.material_input_id for item in value.material_inputs],
        "evidence_ids": [item.evidence_id for item in value.evidence],
        "assumption_record_ids": [item.record_id for item in value.assumptions],
        "contradiction_ids": [item.contradiction_id for item in value.contradictions],
        "blockers": list(value.blockers),
    }


@dataclass(frozen=True)
class ProofWorld:
    qualified_closure_id: str
    obligation_id: str
    world_id: str
    grade: ClosureGrade
    material_inputs: tuple[MaterialInputProof, ...]
    evidence: tuple[EvidenceProof, ...]
    assumptions: tuple[Assumption, ...]
    contradictions: tuple[Contradiction, ...]
    blockers: tuple[str, ...]
    proof_world_id: str

    def validate(self) -> "ProofWorld":
        _require_sha(self.qualified_closure_id, "Proof World qualified closure ID")
        _require_sha(self.obligation_id, "Proof World obligation ID")
        _require_sha(self.world_id, "Proof World world ID")
        if not isinstance(self.grade, ClosureGrade):
            raise ProofWorldError("Proof World closure grade is invalid")
        materials = tuple(sorted((_validate_material(item) for item in self.material_inputs), key=lambda item: (item.family, item.material_input_id)))
        if materials != self.material_inputs or len({item.family for item in materials}) != len(materials):
            raise ProofWorldError("Proof World material inputs are not canonical")
        evidence = tuple(sorted((_validate_evidence(item) for item in self.evidence), key=lambda item: item.evidence_id))
        if evidence != self.evidence or len({item.evidence_id for item in evidence}) != len(evidence):
            raise ProofWorldError("Proof World evidence collection is not canonical")
        assumptions = tuple(sorted((_validate_assumption(item) for item in self.assumptions), key=lambda item: (item.assumption_id, item.record_id)))
        if assumptions != self.assumptions or len({item.assumption_id for item in assumptions}) != len(assumptions):
            raise ProofWorldError("Proof World assumptions are not canonical")
        contradictions = tuple(sorted((_validate_contradiction(item) for item in self.contradictions), key=lambda item: (item.claim, item.contradiction_id)))
        if contradictions != self.contradictions:
            raise ProofWorldError("Proof World contradictions are not canonical")
        blockers = tuple(sorted(set(_string(item, "Proof World blocker") for item in self.blockers)))
        if blockers != self.blockers:
            raise ProofWorldError("Proof World blockers are not canonical")
        if self.proof_world_id != sha256_id(_proof_world_body(self)):
            raise ProofWorldError("Proof World identity mismatch")
        return self


def _canonical_registry(registry: ACRRegistry) -> ACRRegistry:
    if not isinstance(registry, ACRRegistry):
        raise ProofWorldError("Proof World registry must be an ACRRegistry")
    try:
        canonical = ACRRegistry.from_payload(registry.to_payload())
    except (ReviewWorldError, TypeError, ValueError) as exc:
        raise ProofWorldError(f"Proof World registry identity is malformed: {exc}") from exc
    return canonical


def _required_materials(origin_contracts: Sequence[ACRContract]) -> dict[str, ClosureGrade]:
    required: dict[str, ClosureGrade] = {}
    for contract in origin_contracts:
        for requirement in contract.material_inputs:
            current = required.get(requirement.family, ClosureGrade.UNKNOWN)
            required[requirement.family] = _stronger(current, requirement.required_closure)
    return required


def _admitted_proof_classes(origin_contracts: Sequence[ACRContract]) -> set[str]:
    if not origin_contracts:
        return set()
    admitted = set(origin_contracts[0].admissible_proof_classes)
    for contract in origin_contracts[1:]:
        admitted.intersection_update(contract.admissible_proof_classes)
    return admitted


def _rules(origin_contracts: Sequence[ACRContract], field: str) -> set[str]:
    values: set[str] = set()
    for contract in origin_contracts:
        values.update(getattr(contract, field))
    return values


def compile_proof_world(
    *,
    qualified_closure: QualifiedContractClosure,
    expected_obligation: ExpectedObligation,
    registry: ACRRegistry,
    world: WorldCoordinates,
    evidence: Sequence[EvidenceProof],
) -> ProofWorld:
    """Compile one SAE-80 candidate Proof World from qualified SAE-70 authority."""
    try:
        qualified = validate_qualified_contract_closure(qualified_closure)
    except ReviewWorldError as exc:
        raise ProofWorldError(f"invalid SAE-70 qualified closure: {exc}") from exc
    canonical_registry = _canonical_registry(registry)
    if canonical_registry.registry_id != qualified.registry_id:
        raise ProofWorldError("Proof World registry does not match SAE-70 qualified registry")
    world = _validate_world(world)
    obligation, origin_contracts = _validate_expected_obligation(
        expected_obligation,
        qualified=qualified,
        registry=canonical_registry,
    )
    if isinstance(evidence, (str, bytes)):
        raise ProofWorldError("Proof World evidence must be a non-string sequence")
    evidence_items = tuple(sorted((_validate_evidence(item) for item in evidence), key=lambda item: item.evidence_id))
    if len({item.evidence_id for item in evidence_items}) != len(evidence_items):
        raise ProofWorldError("Proof World evidence contains duplicates")

    expected_instance_ids = tuple(sorted(origin.contract_instance_id for origin in obligation.provenance))
    admitted_classes = _admitted_proof_classes(origin_contracts)
    coherence_rules = _rules(origin_contracts, "coherence_rules")
    temporal_rules = _rules(origin_contracts, "temporal_rules")

    grade = ClosureGrade.EXACT
    blockers: list[str] = []
    if not evidence_items:
        grade = ClosureGrade.UNKNOWN
        blockers.append("expected obligation has no evidence")

    strongest_evidence = ClosureGrade.UNKNOWN
    for item in evidence_items:
        if item.obligation_id != obligation.obligation_id:
            raise ProofWorldError("evidence obligation is not bound to the SAE-70 expected obligation")
        if item.contract_instance_ids != expected_instance_ids:
            raise ProofWorldError("evidence contract instances do not exactly match SAE-70 obligation provenance")
        if item.world_id != world.world_id:
            raise ProofWorldError("evidence world generation/coherence does not match Proof World")
        if item.proof_class.value not in admitted_classes:
            raise ProofWorldError(
                f"evidence proof class {item.proof_class.value!r} is not admissible for every origin contract"
            )
        strongest_evidence = _stronger(strongest_evidence, item.claimed_closure)

    if evidence_items:
        grade = _weaker(grade, strongest_evidence)
        if not _meets(strongest_evidence, obligation.required_closure):
            blockers.append(
                f"evidence closure {strongest_evidence.value} does not meet obligation requirement {obligation.required_closure.value}"
            )

    unknown_coherence = sorted(coherence_rules - _SUPPORTED_COHERENCE_RULES)
    for rule in unknown_coherence:
        grade = ClosureGrade.UNKNOWN
        blockers.append(f"unsupported coherence rule: {rule}")
    unknown_temporal = sorted(temporal_rules - _SUPPORTED_TEMPORAL_RULES)
    for rule in unknown_temporal:
        grade = ClosureGrade.UNKNOWN
        blockers.append(f"unsupported temporal rule: {rule}")

    if "evidence-not-older-than-world" in temporal_rules:
        for item in evidence_items:
            if item.observed_epoch != world.epoch:
                grade = ClosureGrade.UNKNOWN
                blockers.append(
                    f"stale/temporal evidence {item.evidence_id} observed at epoch {item.observed_epoch}, world epoch is {world.epoch}"
                )

    material_candidates: dict[str, list[MaterialInputProof]] = {}
    for item in evidence_items:
        for material in item.material_inputs:
            material_candidates.setdefault(material.family, []).append(material)
    selected_materials: list[MaterialInputProof] = []
    required_materials = _required_materials(origin_contracts)
    for family, required_closure in sorted(required_materials.items()):
        candidates = material_candidates.get(family, [])
        if not candidates:
            grade = ClosureGrade.UNKNOWN
            blockers.append(f"missing required material input: {family}")
            continue
        strongest = ClosureGrade.UNKNOWN
        for candidate in candidates:
            strongest = _stronger(strongest, candidate.closure)
        strongest_candidates = sorted(
            (candidate for candidate in candidates if candidate.closure is strongest),
            key=lambda candidate: candidate.material_input_id,
        )
        selected = strongest_candidates[0]
        selected_materials.append(selected)
        if not _meets(strongest, required_closure):
            grade = _weaker(grade, strongest)
            blockers.append(
                f"material input {family} closure {strongest.value} does not meet required {required_closure.value}"
            )

    assumptions_by_id: dict[str, Assumption] = {}
    for item in evidence_items:
        for assumption in item.assumptions:
            previous = assumptions_by_id.get(assumption.assumption_id)
            if previous is not None and previous != assumption:
                raise ProofWorldError("same assumption ID has conflicting records")
            assumptions_by_id[assumption.assumption_id] = assumption
    assumptions = tuple(sorted(assumptions_by_id.values(), key=lambda item: (item.assumption_id, item.record_id)))
    for assumption in assumptions:
        if assumption.kind is not AssumptionKind.VERIFIED:
            grade = ClosureGrade.UNKNOWN
            blockers.append(
                f"assumption {assumption.assumption_id} remains {assumption.kind.value}"
            )

    claims: dict[str, dict[tuple[str, str], tuple[object, set[str]]]] = {}
    for item in evidence_items:
        for claim, claim_value in item.claims:
            key = _scalar_key(claim_value)
            by_value = claims.setdefault(claim, {})
            if key not in by_value:
                by_value[key] = (claim_value, set())
            by_value[key][1].add(item.evidence_id)

    contradictions: list[Contradiction] = []
    for claim, by_value in sorted(claims.items()):
        if len(by_value) <= 1:
            continue
        ordered = sorted(by_value.items(), key=lambda item: item[0])
        values = tuple(item[1][0] for item in ordered)
        evidence_ids = tuple(sorted({identifier for _, (_, identifiers) in ordered for identifier in identifiers}))
        body = {
            "schema_version": "sergeant.sae80-contradiction.v1",
            "claim": claim,
            "values": list(values),
            "evidence_ids": list(evidence_ids),
        }
        contradictions.append(
            Contradiction(claim, values, evidence_ids, sha256_id(body))
        )
        grade = ClosureGrade.UNKNOWN
        blockers.append(f"contradiction detected for claim: {claim}")

    proof = ProofWorld(
        qualified_closure_id=qualified.qualification_id,
        obligation_id=obligation.obligation_id,
        world_id=world.world_id,
        grade=grade,
        material_inputs=tuple(sorted(selected_materials, key=lambda item: (item.family, item.material_input_id))),
        evidence=evidence_items,
        assumptions=assumptions,
        contradictions=tuple(sorted(contradictions, key=lambda item: (item.claim, item.contradiction_id))),
        blockers=tuple(sorted(set(blockers))),
        proof_world_id="",
    )
    proof = ProofWorld(
        proof.qualified_closure_id,
        proof.obligation_id,
        proof.world_id,
        proof.grade,
        proof.material_inputs,
        proof.evidence,
        proof.assumptions,
        proof.contradictions,
        proof.blockers,
        sha256_id(_proof_world_body(proof)),
    )
    return proof.validate()
