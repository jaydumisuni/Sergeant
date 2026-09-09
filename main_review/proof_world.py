"""SAE-80 Evidence + Proof World candidate substrate.

The candidate consumes qualified SAE-70 obligation authority, but positive
Evidence/Proof World semantics are also rooted in the already-PROVEN SAE-10,
SAE-30, SAE-40 and SAE-60 authority chain. Caller-selected labels and
self-consistent hashes are measurements only; they cannot create proof authority.

This remains Task 11 candidate machinery. It does not define or grant Task 12
``QUALIFIED_EVIDENCE_CONTRACT`` or ``QUALIFIED_PROOF_WORLD`` authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math

from .assurance_contract_registry import ACRContract, ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation, ObligationProvenance
from .contract_closure_protocol import QualifiedContractClosure, validate_qualified_contract_closure
from .proof_world_authority import (
    ProofWorldAuthority,
    QualifiedEvidenceProofAuthority,
    validate_evidence_proof_authority,
    validate_proof_world_authority,
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


def _sha(value: str, field: str) -> str:
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
    return type(value).__name__, sha256_id({"value": value})


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
        deps = tuple(
            sorted(
                (_string(name, "dependency name"), _string(generation, "dependency generation"))
                for name, generation in dependency_generations.items()
            )
        )
        if len({name for name, _ in deps}) != len(deps):
            raise ProofWorldError("dependency generations contain duplicate names")
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise ProofWorldError("world epoch must be a non-negative integer")
        body = _world_body(
            candidate_generation=candidate_generation,
            framework_generation=framework_generation,
            provider_generation=provider_generation,
            dependency_generations=deps,
            epoch=epoch,
        )
        return cls(candidate_generation, framework_generation, provider_generation, deps, epoch, sha256_id(body))

    @classmethod
    def from_authority(cls, authority: ProofWorldAuthority) -> "WorldCoordinates":
        try:
            authority = validate_proof_world_authority(authority)
        except ReviewWorldError as exc:
            raise ProofWorldError(f"qualified Proof World authority is invalid: {exc}") from exc
        return cls.create(
            candidate_generation=authority.candidate_generation,
            framework_generation=authority.framework_generation,
            provider_generation=authority.provider_generation,
            dependency_generations=dict(authority.dependency_generations),
            epoch=authority.epoch,
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
    def create(cls, *, family: str, closure: ClosureGrade, basis_id: str) -> "MaterialInputProof":
        family = _string(family, "material-input family")
        if not isinstance(closure, ClosureGrade):
            raise ProofWorldError("material-input closure is invalid")
        basis_id = _sha(basis_id, "material-input basis_id")
        body = _material_body(family=family, closure=closure, basis_id=basis_id)
        return cls(family, closure, basis_id, sha256_id(body))


def _validate_material(value: MaterialInputProof) -> MaterialInputProof:
    if not isinstance(value, MaterialInputProof):
        raise ProofWorldError("material-input proof has invalid record type")
    canonical = MaterialInputProof.create(family=value.family, closure=value.closure, basis_id=value.basis_id)
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
    def create(cls, *, assumption_id: str, kind: AssumptionKind, basis_id: str) -> "Assumption":
        assumption_id = _string(assumption_id, "assumption ID")
        if not isinstance(kind, AssumptionKind):
            raise ProofWorldError("assumption kind is invalid")
        basis_id = _sha(basis_id, "assumption basis_id")
        body = _assumption_body(assumption_id=assumption_id, kind=kind, basis_id=basis_id)
        return cls(assumption_id, kind, basis_id, sha256_id(body))


def _validate_assumption(value: Assumption) -> Assumption:
    if not isinstance(value, Assumption):
        raise ProofWorldError("assumption has invalid record type")
    canonical = Assumption.create(assumption_id=value.assumption_id, kind=value.kind, basis_id=value.basis_id)
    if canonical != value:
        raise ProofWorldError("assumption identity mismatch")
    return value


def _evidence_body(value: "EvidenceProof") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-evidence-proof.v2",
        "proof_authority_id": value.proof_authority.authority_id,
        "proof_class": value.proof_class.value,
        "claimed_closure": value.claimed_closure.value,
        "obligation_id": value.obligation_id,
        "contract_instance_ids": list(value.contract_instance_ids),
        "world_id": value.world_id,
        "material_input_ids": [item.material_input_id for item in value.material_inputs],
        "claims": dict(value.claims),
        "assumption_record_ids": [item.record_id for item in value.assumptions],
        "observed_epoch": value.observed_epoch,
        "evidence_basis_id": value.evidence_basis_id,
        "proof_ceiling": value.proof_ceiling.value,
    }


@dataclass(frozen=True)
class EvidenceProof:
    proof_authority: QualifiedEvidenceProofAuthority
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
        proof_authority: QualifiedEvidenceProofAuthority | None = None,
        world_authority: ProofWorldAuthority | None = None,
    ) -> "EvidenceProof":
        if not isinstance(proof_class, ProofClass):
            raise ProofWorldError("evidence proof class is invalid")
        if proof_authority is None or world_authority is None:
            raise ProofWorldError(f"{proof_class.value} evidence requires qualified proof authority")
        try:
            rooted_world = validate_proof_world_authority(world_authority)
            rooted_proof = validate_evidence_proof_authority(proof_authority, world_authority=rooted_world)
        except ReviewWorldError as exc:
            raise ProofWorldError(f"qualified evidence authority is invalid: {exc}") from exc
        canonical_world = WorldCoordinates.from_authority(rooted_world)
        if _validate_world(world) != canonical_world:
            raise ProofWorldError("evidence world is not the qualified Review World generation")
        if rooted_proof.proof_class != proof_class.value:
            raise ProofWorldError("caller proof class does not match qualified provenance")
        if not isinstance(claimed_closure, ClosureGrade):
            raise ProofWorldError("evidence claimed closure is invalid")
        try:
            authority_ceiling = ClosureGrade(rooted_proof.closure_ceiling)
        except ValueError as exc:
            raise ProofWorldError("qualified evidence closure ceiling is invalid") from exc
        ceiling = _weaker(_PROOF_CEILINGS[proof_class], authority_ceiling)
        if not _meets(ceiling, claimed_closure):
            raise ProofWorldError(
                f"{proof_class.value} proof ceiling {ceiling.value} cannot claim {claimed_closure.value}"
            )
        obligation_id = _sha(obligation_id, "evidence obligation_id")
        if rooted_proof.obligation_id != obligation_id:
            raise ProofWorldError("qualified evidence authority is bound to another obligation")
        if isinstance(contract_instance_ids, (str, bytes)):
            raise ProofWorldError("evidence contract instance IDs must be a non-string sequence")
        instances = tuple(sorted(_sha(item, "evidence contract instance id") for item in contract_instance_ids))
        if len(set(instances)) != len(instances):
            raise ProofWorldError("evidence contract instance IDs contain duplicates")
        if isinstance(material_inputs, (str, bytes)):
            raise ProofWorldError("evidence material inputs must be a non-string sequence")
        materials = tuple(
            sorted(
                (_validate_material(item) for item in material_inputs),
                key=lambda item: (item.family, item.material_input_id),
            )
        )
        if len({item.family for item in materials}) != len(materials):
            raise ProofWorldError("evidence material inputs contain duplicate families")
        if not isinstance(claims, Mapping):
            raise ProofWorldError("evidence claims must be a mapping")
        claim_items = tuple(
            sorted(
                (_string(name, "claim name"), _scalar(value, "claim value"))
                for name, value in claims.items()
            )
        )
        if len({name for name, _ in claim_items}) != len(claim_items):
            raise ProofWorldError("evidence claims contain duplicate names")
        if isinstance(assumptions, (str, bytes)):
            raise ProofWorldError("evidence assumptions must be a non-string sequence")
        assumption_items = tuple(
            sorted(
                (_validate_assumption(item) for item in assumptions),
                key=lambda item: (item.assumption_id, item.record_id),
            )
        )
        if len({item.assumption_id for item in assumption_items}) != len(assumption_items):
            raise ProofWorldError("evidence assumptions contain duplicate assumption IDs")
        if isinstance(observed_epoch, bool) or not isinstance(observed_epoch, int) or observed_epoch < 0:
            raise ProofWorldError("evidence observed epoch must be a non-negative integer")
        evidence_basis_id = _sha(evidence_basis_id, "evidence basis_id")
        if rooted_proof.evidence_basis_id != evidence_basis_id:
            raise ProofWorldError("evidence basis is not bound to qualified provenance")
        provisional = cls(
            rooted_proof,
            proof_class,
            claimed_closure,
            obligation_id,
            instances,
            canonical_world.world_id,
            materials,
            claim_items,
            assumption_items,
            observed_epoch,
            evidence_basis_id,
            ceiling,
            "",
        )
        return cls(
            rooted_proof,
            proof_class,
            claimed_closure,
            obligation_id,
            instances,
            canonical_world.world_id,
            materials,
            claim_items,
            assumption_items,
            observed_epoch,
            evidence_basis_id,
            ceiling,
            sha256_id(_evidence_body(provisional)),
        )


def _validate_evidence(value: EvidenceProof, *, world_authority: ProofWorldAuthority) -> EvidenceProof:
    if not isinstance(value, EvidenceProof):
        raise ProofWorldError("evidence has invalid record type")
    canonical_world = WorldCoordinates.from_authority(world_authority)
    canonical = EvidenceProof.create(
        proof_class=value.proof_class,
        claimed_closure=value.claimed_closure,
        obligation_id=value.obligation_id,
        contract_instance_ids=value.contract_instance_ids,
        world=canonical_world,
        material_inputs=value.material_inputs,
        claims=dict(value.claims),
        assumptions=value.assumptions,
        observed_epoch=value.observed_epoch,
        evidence_basis_id=value.evidence_basis_id,
        proof_authority=value.proof_authority,
        world_authority=world_authority,
    )
    if canonical != value:
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


def _canonical_registry(registry: ACRRegistry) -> ACRRegistry:
    if not isinstance(registry, ACRRegistry):
        raise ProofWorldError("Proof World registry must be an ACRRegistry")
    try:
        canonical = ACRRegistry.from_payload(registry.to_payload())
    except (ReviewWorldError, TypeError, ValueError) as exc:
        raise ProofWorldError(f"Proof World registry identity is malformed: {exc}") from exc
    return canonical


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
    if bindings != tuple(sorted(bindings)) or len({name for name, _ in bindings}) != len(bindings):
        raise ProofWorldError("expected obligation bindings are not canonical")
    for name, binding_value in bindings:
        _string(name, "expected obligation binding name")
        _string(binding_value, "expected obligation binding value")
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
    contracts = {contract.contract_id: contract for contract in registry.contracts}
    origins: list[ACRContract] = []
    strongest = ClosureGrade.UNKNOWN
    distinct: set[ClosureGrade] = set()
    for origin in value.provenance:
        if not isinstance(origin, ObligationProvenance):
            raise ProofWorldError("expected obligation provenance has invalid record type")
        contract_id = _string(origin.contract_id, "obligation provenance contract ID")
        generation = _string(origin.contract_generation, "obligation provenance contract generation")
        instance_id = _sha(origin.contract_instance_id, "obligation provenance contract instance ID")
        if not isinstance(origin.required_closure, ClosureGrade):
            raise ProofWorldError("obligation provenance required closure is invalid")
        if instance_id not in qualified.expected_instance_ids:
            raise ProofWorldError("expected obligation provenance is not bound to SAE-70 qualified instances")
        contract = contracts.get(contract_id)
        if contract is None or contract.generation != generation:
            raise ProofWorldError("expected obligation provenance contract is not bound to qualified registry")
        matching = [req for req in contract.mandatory_obligations if req.family == family]
        if len(matching) != 1 or matching[0].required_closure is not origin.required_closure:
            raise ProofWorldError("expected obligation provenance does not match registry obligation requirement")
        strongest = _stronger(strongest, origin.required_closure)
        distinct.add(origin.required_closure)
        origins.append(contract)
    if value.required_closure is not strongest:
        raise ProofWorldError("expected obligation strongest closure invariant mismatch")
    if value.conflict_resolved_conservatively is not (len(distinct) > 1):
        raise ProofWorldError("expected obligation conservative-conflict flag mismatch")
    if value.obligation_id != sha256_id(_obligation_body(value)):
        raise ProofWorldError("expected obligation identity mismatch")
    if value.obligation_id not in qualified.expected_obligation_ids:
        raise ProofWorldError("expected obligation is not bound to SAE-70 qualified authority")
    return value, tuple(origins)


def _basis_body(value: "ProofWorldBasis") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-proof-world-basis.v1",
        "qualified_closure_id": value.qualified_closure.qualification_id,
        "registry_id": value.registry.registry_id,
        "obligation_id": value.expected_obligation.obligation_id,
        "world_authority_id": value.world_authority.authority_id,
    }


@dataclass(frozen=True)
class ProofWorldBasis:
    qualified_closure: QualifiedContractClosure
    registry: ACRRegistry
    expected_obligation: ExpectedObligation
    world_authority: ProofWorldAuthority
    basis_id: str


def _make_basis(
    *,
    qualified_closure: QualifiedContractClosure,
    registry: ACRRegistry,
    expected_obligation: ExpectedObligation,
    world_authority: ProofWorldAuthority,
) -> ProofWorldBasis:
    try:
        qualified = validate_qualified_contract_closure(qualified_closure)
        authority = validate_proof_world_authority(world_authority)
    except ReviewWorldError as exc:
        raise ProofWorldError(f"invalid qualified Proof World basis: {exc}") from exc
    canonical_registry = _canonical_registry(registry)
    if canonical_registry.registry_id != qualified.registry_id:
        raise ProofWorldError("Proof World registry does not match SAE-70 qualified registry")
    if authority.qualified_contract_closure != qualified or authority.acr_registry != canonical_registry:
        raise ProofWorldError("Proof World authority does not bind exact SAE-70/ACR basis")
    obligation, _ = _validate_expected_obligation(expected_obligation, qualified=qualified, registry=canonical_registry)
    provisional = ProofWorldBasis(qualified, canonical_registry, obligation, authority, "")
    return ProofWorldBasis(qualified, canonical_registry, obligation, authority, sha256_id(_basis_body(provisional)))


def _validate_basis(value: ProofWorldBasis) -> ProofWorldBasis:
    if not isinstance(value, ProofWorldBasis):
        raise ProofWorldError("Proof World semantic basis has invalid record type")
    canonical = _make_basis(
        qualified_closure=value.qualified_closure,
        registry=value.registry,
        expected_obligation=value.expected_obligation,
        world_authority=value.world_authority,
    )
    if canonical != value:
        raise ProofWorldError("Proof World semantic basis identity mismatch")
    return value


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
    values = tuple(sorted((_scalar(item, "contradiction value") for item in value.values), key=_scalar_key))
    if len(values) < 2 or values != value.values or len({_scalar_key(item) for item in values}) != len(values):
        raise ProofWorldError("contradiction values are not canonical and distinct")
    evidence_ids = tuple(sorted(_sha(item, "contradiction evidence id") for item in value.evidence_ids))
    if evidence_ids != value.evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
        raise ProofWorldError("contradiction evidence IDs are not canonical")
    if value.contradiction_id != sha256_id(_contradiction_body(value)):
        raise ProofWorldError("contradiction identity mismatch")
    return value


def _required_materials(origin_contracts: Sequence[ACRContract]) -> dict[str, ClosureGrade]:
    required: dict[str, ClosureGrade] = {}
    for contract in origin_contracts:
        for requirement in contract.material_inputs:
            required[requirement.family] = _stronger(
                required.get(requirement.family, ClosureGrade.UNKNOWN),
                requirement.required_closure,
            )
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


def _derive_semantics(
    *,
    basis: ProofWorldBasis,
    evidence: tuple[EvidenceProof, ...],
) -> tuple[
    ClosureGrade,
    tuple[MaterialInputProof, ...],
    tuple[Assumption, ...],
    tuple[Contradiction, ...],
    tuple[str, ...],
]:
    basis = _validate_basis(basis)
    qualified = basis.qualified_closure
    obligation, origin_contracts = _validate_expected_obligation(
        basis.expected_obligation,
        qualified=qualified,
        registry=basis.registry,
    )
    world = WorldCoordinates.from_authority(basis.world_authority)
    evidence_items = tuple(
        sorted(
            (_validate_evidence(item, world_authority=basis.world_authority) for item in evidence),
            key=lambda item: item.evidence_id,
        )
    )
    if len({item.evidence_id for item in evidence_items}) != len(evidence_items):
        raise ProofWorldError("Proof World evidence contains duplicates")

    expected_instances = tuple(sorted(origin.contract_instance_id for origin in obligation.provenance))
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
        if item.contract_instance_ids != expected_instances:
            raise ProofWorldError("evidence contract instances do not exactly match SAE-70 obligation provenance")
        if item.world_id != world.world_id:
            raise ProofWorldError("evidence world generation/coherence does not match qualified Proof World")
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

    for rule in sorted(coherence_rules - _SUPPORTED_COHERENCE_RULES):
        grade = ClosureGrade.UNKNOWN
        blockers.append(f"unsupported coherence rule: {rule}")
    for rule in sorted(temporal_rules - _SUPPORTED_TEMPORAL_RULES):
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
    selected: list[MaterialInputProof] = []
    for family, required_closure in sorted(_required_materials(origin_contracts).items()):
        candidates = material_candidates.get(family, [])
        if not candidates:
            grade = ClosureGrade.UNKNOWN
            blockers.append(f"missing required material input: {family}")
            continue
        strongest = ClosureGrade.UNKNOWN
        for candidate in candidates:
            strongest = _stronger(strongest, candidate.closure)
        chosen = sorted(
            (candidate for candidate in candidates if candidate.closure is strongest),
            key=lambda item: item.material_input_id,
        )[0]
        selected.append(chosen)
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
    assumptions = tuple(
        sorted(assumptions_by_id.values(), key=lambda item: (item.assumption_id, item.record_id))
    )
    for assumption in assumptions:
        if assumption.kind is not AssumptionKind.VERIFIED:
            grade = ClosureGrade.UNKNOWN
            blockers.append(f"assumption {assumption.assumption_id} remains {assumption.kind.value}")

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
        evidence_ids = tuple(
            sorted({identifier for _, (_, identifiers) in ordered for identifier in identifiers})
        )
        provisional = Contradiction(claim, values, evidence_ids, "")
        contradictions.append(
            Contradiction(claim, values, evidence_ids, sha256_id(_contradiction_body(provisional)))
        )
        grade = ClosureGrade.UNKNOWN
        blockers.append(f"contradiction detected for claim: {claim}")

    return (
        grade,
        tuple(sorted(selected, key=lambda item: (item.family, item.material_input_id))),
        assumptions,
        tuple(sorted(contradictions, key=lambda item: (item.claim, item.contradiction_id))),
        tuple(sorted(set(blockers))),
    )


def _proof_world_body(value: "ProofWorld") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-proof-world.v2",
        "basis_id": value.basis.basis_id,
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
    basis: ProofWorldBasis
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
        basis = _validate_basis(self.basis)
        if self.qualified_closure_id != basis.qualified_closure.qualification_id:
            raise ProofWorldError("Proof World qualified closure authority mismatch")
        if self.obligation_id != basis.expected_obligation.obligation_id:
            raise ProofWorldError("Proof World obligation authority mismatch")
        world = WorldCoordinates.from_authority(basis.world_authority)
        if self.world_id != world.world_id:
            raise ProofWorldError("Proof World world authority mismatch")
        evidence = tuple(
            sorted(
                (_validate_evidence(item, world_authority=basis.world_authority) for item in self.evidence),
                key=lambda item: item.evidence_id,
            )
        )
        if evidence != self.evidence or len({item.evidence_id for item in evidence}) != len(evidence):
            raise ProofWorldError("Proof World evidence collection is not canonical")
        derived = _derive_semantics(basis=basis, evidence=evidence)
        actual = (
            self.grade,
            self.material_inputs,
            self.assumptions,
            self.contradictions,
            self.blockers,
        )
        if actual != derived:
            raise ProofWorldError("Proof World semantic recomputation mismatch")
        if self.proof_world_id != sha256_id(_proof_world_body(self)):
            raise ProofWorldError("Proof World identity mismatch")
        return self


def compile_proof_world(
    *,
    qualified_closure: QualifiedContractClosure,
    expected_obligation: ExpectedObligation,
    registry: ACRRegistry,
    world: WorldCoordinates,
    evidence: Sequence[EvidenceProof],
    world_authority: ProofWorldAuthority | None = None,
) -> ProofWorld:
    """Compile one candidate Proof World from rooted upstream authority."""
    if world_authority is None:
        raise ProofWorldError("qualified Review World/dependency authority is required")
    try:
        authority = validate_proof_world_authority(world_authority)
    except ReviewWorldError as exc:
        raise ProofWorldError(f"qualified Review World/dependency authority is invalid: {exc}") from exc
    canonical_world = WorldCoordinates.from_authority(authority)
    if _validate_world(world) != canonical_world:
        raise ProofWorldError("caller world generations do not match qualified authority")
    basis = _make_basis(
        qualified_closure=qualified_closure,
        registry=registry,
        expected_obligation=expected_obligation,
        world_authority=authority,
    )
    if isinstance(evidence, (str, bytes)):
        raise ProofWorldError("Proof World evidence must be a non-string sequence")
    evidence_items = tuple(
        sorted(
            (_validate_evidence(item, world_authority=authority) for item in evidence),
            key=lambda item: item.evidence_id,
        )
    )
    if len({item.evidence_id for item in evidence_items}) != len(evidence_items):
        raise ProofWorldError("Proof World evidence contains duplicates")
    grade, materials, assumptions, contradictions, blockers = _derive_semantics(
        basis=basis,
        evidence=evidence_items,
    )
    provisional = ProofWorld(
        basis,
        basis.qualified_closure.qualification_id,
        basis.expected_obligation.obligation_id,
        canonical_world.world_id,
        grade,
        materials,
        evidence_items,
        assumptions,
        contradictions,
        blockers,
        "",
    )
    proof = ProofWorld(
        provisional.basis,
        provisional.qualified_closure_id,
        provisional.obligation_id,
        provisional.world_id,
        provisional.grade,
        provisional.material_inputs,
        provisional.evidence,
        provisional.assumptions,
        provisional.contradictions,
        provisional.blockers,
        sha256_id(_proof_world_body(provisional)),
    )
    return proof.validate()
