"""SAE-80 Evidence + Proof World candidate substrate.

Positive authority is separated into two roots:

* Review World truth is bound from current SAE-10 Review World/RAB authority
  plus the exact SAE-70 qualified contract/obligation generation.
* Evidence proof class/ceiling is derived from SAE-30 qualification admission;
  a caller cannot promote a heuristic or unqualified producer by changing a
  label or recomputing a public content hash.

``ProofWorld.validate`` re-derives semantic outputs from those bound sources,
so changing UNKNOWN to EXACT and rehashing cannot manufacture authority.

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
from .qualification_authority import (
    AuthenticatedIssuer,
    DerivedQualification,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityRegistry,
    QualificationClosureProof,
    QualificationIssuerAuthorization,
    admit_qualification_attestation,
)
from .review_authority_bundle import (
    RABAuthorizationSet,
    ReviewAuthorityBundle,
    authorize_rab,
)
from .review_world import GitHubReviewWorld, ReviewWorldError, require_full_sha256, sha256_id
from .review_world_currentness import check_github_currentness


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
_PUBLIC_EVIDENCE_ARTIFACT_FAMILY = "sae80-evidence-proof"
_PUBLIC_EVIDENCE_QUALIFICATION_GENERATION = "sae80-evidence-qualification-v1"


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


def _canonical_registry(registry: ACRRegistry) -> ACRRegistry:
    if not isinstance(registry, ACRRegistry):
        raise ProofWorldError("Proof World registry must be an ACRRegistry")
    try:
        canonical = ACRRegistry.from_payload(registry.to_payload())
    except (ReviewWorldError, TypeError, ValueError) as exc:
        raise ProofWorldError(f"Proof World registry identity is malformed: {exc}") from exc
    if canonical != registry:
        raise ProofWorldError("Proof World registry is not canonical")
    return registry


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


def _qualified_world_body(value: "QualifiedWorld") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-qualified-world.v1",
        "review_world_id": value.review_world.review_world_id,
        "current_world_id": value.current_world.review_world_id,
        "rab_id": value.rab_bundle.rab_id,
        "rab_authorization_set_id": value.rab_authorizations.authorization_set_id,
        "qualified_closure_id": value.qualified_closure.qualification_id,
        "registry_id": value.registry.registry_id,
        "world_id": value.coordinates.world_id,
    }


@dataclass(frozen=True)
class QualifiedWorld:
    review_world: GitHubReviewWorld
    current_world: GitHubReviewWorld
    rab_bundle: ReviewAuthorityBundle
    rab_authorizations: RABAuthorizationSet
    qualified_closure: QualifiedContractClosure
    registry: ACRRegistry
    coordinates: WorldCoordinates
    authority_id: str

    @property
    def candidate_generation(self) -> str:
        return self.coordinates.candidate_generation

    @property
    def framework_generation(self) -> str:
        return self.coordinates.framework_generation

    @property
    def provider_generation(self) -> str:
        return self.coordinates.provider_generation

    @property
    def dependency_generations(self) -> tuple[tuple[str, str], ...]:
        return self.coordinates.dependency_generations

    @property
    def epoch(self) -> int:
        return self.coordinates.epoch

    @property
    def world_id(self) -> str:
        return self.coordinates.world_id


def bind_qualified_world(
    *,
    review_world: GitHubReviewWorld,
    current_world: GitHubReviewWorld,
    rab_bundle: ReviewAuthorityBundle,
    rab_authorizations: RABAuthorizationSet,
    qualified_closure: QualifiedContractClosure,
    registry: ACRRegistry,
    epoch: int,
) -> QualifiedWorld:
    """Bind caller-visible world coordinates to current SAE-10 + SAE-70 authority."""
    if not isinstance(review_world, GitHubReviewWorld) or not isinstance(current_world, GitHubReviewWorld):
        raise ProofWorldError("qualified Review World authority is required")
    review_world.validate()
    current_world.validate()
    if not isinstance(rab_bundle, ReviewAuthorityBundle):
        raise ProofWorldError("qualified RAB bundle is required")
    if rab_bundle.expected_id() != rab_bundle.rab_id:
        raise ProofWorldError("RAB bundle identity mismatch")
    if review_world.rab_id != rab_bundle.rab_id or current_world.rab_id != rab_bundle.rab_id:
        raise ProofWorldError("Review World is not bound to exact RAB bundle")
    if not isinstance(rab_authorizations, RABAuthorizationSet):
        raise ProofWorldError("RAB authorization set is required")
    if rab_authorizations.expected_id() != rab_authorizations.authorization_set_id:
        raise ProofWorldError("RAB authorization set identity mismatch")
    authorization = authorize_rab(rab_bundle, rab_authorizations)
    if not authorization.authorized or authorization.authorization_generation is None:
        raise ProofWorldError(f"RAB is not authorized: {authorization.reason}")
    currentness = check_github_currentness(
        review_world,
        current_world,
        rab_authorized=True,
    )
    if currentness.state != "CURRENT":
        raise ProofWorldError(
            f"qualified Review World is not current: {currentness.state} {currentness.reasons}"
        )
    try:
        qualified = validate_qualified_contract_closure(qualified_closure)
    except ReviewWorldError as exc:
        raise ProofWorldError(f"invalid SAE-70 qualified closure: {exc}") from exc
    canonical_registry = _canonical_registry(registry)
    if qualified.registry_id != canonical_registry.registry_id:
        raise ProofWorldError("SAE-70 qualified closure and ACR registry disagree")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise ProofWorldError("qualified world epoch must be a non-negative integer")
    coordinates = WorldCoordinates.create(
        candidate_generation=review_world.diff.head_commit,
        framework_generation=review_world.review_generation,
        provider_generation=authorization.authorization_generation,
        dependency_generations={
            "review-world": review_world.review_world_id,
            "rab": rab_bundle.rab_id,
            "rab-authorization-set": rab_authorizations.authorization_set_id,
            "sae70-contract-closure": qualified.qualification_id,
            "acr-registry": canonical_registry.registry_id,
        },
        epoch=epoch,
    )
    provisional = QualifiedWorld(
        review_world,
        current_world,
        rab_bundle,
        rab_authorizations,
        qualified,
        canonical_registry,
        coordinates,
        "",
    )
    return QualifiedWorld(
        review_world,
        current_world,
        rab_bundle,
        rab_authorizations,
        qualified,
        canonical_registry,
        coordinates,
        sha256_id(_qualified_world_body(provisional)),
    )


def _validate_qualified_world(value: QualifiedWorld) -> QualifiedWorld:
    if not isinstance(value, QualifiedWorld):
        raise ProofWorldError("qualified Review World authority has invalid record type")
    canonical = bind_qualified_world(
        review_world=value.review_world,
        current_world=value.current_world,
        rab_bundle=value.rab_bundle,
        rab_authorizations=value.rab_authorizations,
        qualified_closure=value.qualified_closure,
        registry=value.registry,
        epoch=value.epoch,
    )
    if canonical != value:
        raise ProofWorldError("qualified Review World authority identity mismatch")
    return value


WorldAuthority = ProofWorldAuthority | QualifiedWorld


def _coordinates_from_authority(authority: WorldAuthority) -> WorldCoordinates:
    if isinstance(authority, QualifiedWorld):
        return _validate_qualified_world(authority).coordinates
    return WorldCoordinates.from_authority(authority)


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


def _issuer_canonical(value: QualificationIssuerAuthorization) -> QualificationIssuerAuthorization:
    if not isinstance(value, QualificationIssuerAuthorization):
        raise ProofWorldError("qualified evidence issuer authority has invalid record type")
    canonical = QualificationIssuerAuthorization.create(
        issuer_identity=value.issuer_identity,
        key_id=value.key_id,
        namespace=value.namespace,
        issuer_generation=value.issuer_generation,
        artifact_families=value.artifact_families,
        domains=value.domains,
        proof_classes=value.proof_classes,
        closure_grades=value.closure_grades,
        allowed_independence_states=value.allowed_independence_states,
        control_lineage_id=value.control_lineage_id,
        authentication_secret_digest=value.authentication_secret_digest,
        state=value.state,
    )
    if canonical != value:
        raise ProofWorldError("qualified evidence issuer authority identity mismatch")
    return value


def _derived_qualification_body(value: DerivedQualification) -> dict[str, object]:
    return {
        "schema_version": "sergeant.derived-qualification.v3",
        "subject_id": value.subject_id,
        "artifact_family": value.artifact_family,
        "domain": value.domain,
        "artifact_generation": value.artifact_generation,
        "attestation_id": value.attestation_id,
        "issuer_authorization_id": value.issuer_authorization_id,
        "evidence_root_id": value.evidence_root_id,
        "independence_state": value.independence_state,
        "qualification_lineage_id": value.qualification_lineage_id,
        "authenticated_provenance_id": value.authenticated_provenance_id,
        "closure_proof_id": value.closure_proof_id,
        "state": value.state,
    }


def _public_evidence_authority_body(value: "AdmittedEvidenceAuthority") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-admitted-evidence-authority.v1",
        "world_authority_id": value.world_authority_id,
        "attestation_id": value.attestation.attestation_id,
        "qualification_id": value.qualification.qualification_id,
        "issuer_authorization_id": value.issuer_authorization.authorization_id,
        "proof_class": value.proof_class,
        "closure_ceiling": value.closure_ceiling,
        "evidence_basis_id": value.evidence_basis_id,
    }


@dataclass(frozen=True)
class AdmittedEvidenceAuthority:
    world_authority_id: str
    attestation: QualificationAttestation
    qualification: DerivedQualification
    issuer_authorization: QualificationIssuerAuthorization
    proof_class: str
    closure_ceiling: str
    evidence_basis_id: str
    authority_id: str


def _validate_admitted_evidence_authority(
    value: AdmittedEvidenceAuthority,
    *,
    world: QualifiedWorld,
) -> AdmittedEvidenceAuthority:
    world = _validate_qualified_world(world)
    if not isinstance(value, AdmittedEvidenceAuthority):
        raise ProofWorldError("admitted evidence authority has invalid record type")
    if value.world_authority_id != world.authority_id:
        raise ProofWorldError("evidence qualification is bound to another Review World authority")
    if not isinstance(value.attestation, QualificationAttestation):
        raise ProofWorldError("qualified evidence attestation has invalid record type")
    if QualificationAttestation.create(**value.attestation.constructor_fields()) != value.attestation:
        raise ProofWorldError("qualified evidence attestation identity mismatch")
    issuer = _issuer_canonical(value.issuer_authorization)
    qualification = value.qualification
    if not isinstance(qualification, DerivedQualification) or qualification.state != "QUALIFIED":
        raise ProofWorldError("evidence lacks derived QUALIFIED SAE-30 authority")
    if qualification.qualification_id != sha256_id(_derived_qualification_body(qualification)):
        raise ProofWorldError("derived evidence qualification identity mismatch")
    for field in (
        "subject_id",
        "artifact_family",
        "domain",
        "artifact_generation",
        "evidence_root_id",
        "independence_state",
        "qualification_lineage_id",
        "authenticated_provenance_id",
    ):
        if getattr(qualification, field) != getattr(value.attestation, field):
            raise ProofWorldError(f"derived evidence qualification {field} mismatch")
    if qualification.attestation_id != value.attestation.attestation_id:
        raise ProofWorldError("derived evidence qualification attestation mismatch")
    if qualification.issuer_authorization_id != issuer.authorization_id:
        raise ProofWorldError("derived evidence qualification issuer mismatch")
    if issuer.state is not IssuerState.ACTIVE:
        raise ProofWorldError("qualified evidence issuer is not active")
    if value.attestation.artifact_family != _PUBLIC_EVIDENCE_ARTIFACT_FAMILY:
        raise ProofWorldError("qualified evidence artifact family is outside SAE-80")
    if value.attestation.artifact_generation != world.authority_id:
        raise ProofWorldError("qualified evidence candidate/Review World generation mismatch")
    if value.attestation.acr_generation != world.registry.generation:
        raise ProofWorldError("qualified evidence ACR generation mismatch")
    if value.attestation.qualification_protocol_generation != _PUBLIC_EVIDENCE_QUALIFICATION_GENERATION:
        raise ProofWorldError("qualified evidence protocol generation mismatch")
    if value.attestation.subject_id != value.evidence_basis_id:
        raise ProofWorldError("qualified evidence subject is not exact evidence basis")
    if value.attestation.evidence_root_id != value.evidence_basis_id:
        raise ProofWorldError("qualified evidence root is not exact evidence basis")
    if value.attestation.independence_state != "INDEPENDENT":
        raise ProofWorldError("qualified evidence lacks independent provenance")
    if value.proof_class != value.attestation.proof_class or value.proof_class not in issuer.proof_classes:
        raise ProofWorldError("qualified evidence proof class is outside issuer authority")
    if value.closure_ceiling != value.attestation.closure_grade or value.closure_ceiling not in issuer.closure_grades:
        raise ProofWorldError("qualified evidence closure ceiling is outside issuer authority")
    try:
        ProofClass(value.proof_class)
        ClosureGrade(value.closure_ceiling)
    except ValueError as exc:
        raise ProofWorldError("qualified evidence proof class/closure ceiling is unknown") from exc
    if value.evidence_basis_id != _sha(value.evidence_basis_id, "qualified evidence basis_id"):
        raise ProofWorldError("qualified evidence basis identity mismatch")
    if value.authority_id != sha256_id(_public_evidence_authority_body(value)):
        raise ProofWorldError("admitted evidence authority identity mismatch")
    return value


ProofAuthority = QualifiedEvidenceProofAuthority | AdmittedEvidenceAuthority


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


def _normalize_evidence_fields(
    *,
    proof_authority: ProofAuthority,
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
    proof_ceiling: ClosureGrade,
) -> tuple[object, ...]:
    if not isinstance(proof_class, ProofClass):
        raise ProofWorldError("evidence proof class is invalid")
    if not isinstance(claimed_closure, ClosureGrade) or not isinstance(proof_ceiling, ClosureGrade):
        raise ProofWorldError("evidence closure grade is invalid")
    if not _meets(proof_ceiling, claimed_closure):
        raise ProofWorldError(
            f"{proof_class.value} proof ceiling {proof_ceiling.value} cannot claim {claimed_closure.value}"
        )
    obligation_id = _sha(obligation_id, "evidence obligation_id")
    if isinstance(contract_instance_ids, (str, bytes)):
        raise ProofWorldError("evidence contract instance IDs must be a non-string sequence")
    instances = tuple(sorted(_sha(item, "evidence contract instance id") for item in contract_instance_ids))
    if len(set(instances)) != len(instances):
        raise ProofWorldError("evidence contract instance IDs contain duplicates")
    world = _validate_world(world)
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
    return (
        proof_authority,
        proof_class,
        claimed_closure,
        obligation_id,
        instances,
        world.world_id,
        materials,
        claim_items,
        assumption_items,
        observed_epoch,
        evidence_basis_id,
        proof_ceiling,
    )


@dataclass(frozen=True)
class EvidenceProof:
    proof_authority: ProofAuthority
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
        try:
            authority_ceiling = ClosureGrade(rooted_proof.closure_ceiling)
        except ValueError as exc:
            raise ProofWorldError("qualified evidence closure ceiling is invalid") from exc
        ceiling = _weaker(_PROOF_CEILINGS[proof_class], authority_ceiling)
        if rooted_proof.obligation_id != obligation_id:
            raise ProofWorldError("qualified evidence authority is bound to another obligation")
        if rooted_proof.evidence_basis_id != evidence_basis_id:
            raise ProofWorldError("evidence basis is not bound to qualified provenance")
        fields = _normalize_evidence_fields(
            proof_authority=rooted_proof,
            proof_class=proof_class,
            claimed_closure=claimed_closure,
            obligation_id=obligation_id,
            contract_instance_ids=contract_instance_ids,
            world=canonical_world,
            material_inputs=material_inputs,
            claims=claims,
            assumptions=assumptions,
            observed_epoch=observed_epoch,
            evidence_basis_id=evidence_basis_id,
            proof_ceiling=ceiling,
        )
        provisional = cls(*fields, "")
        return cls(*fields, sha256_id(_evidence_body(provisional)))


def create_qualified_evidence(
    *,
    claimed_closure: ClosureGrade,
    obligation_id: str,
    contract_instance_ids: Sequence[str],
    world: QualifiedWorld,
    material_inputs: Sequence[MaterialInputProof],
    claims: Mapping[str, object],
    assumptions: Sequence[Assumption],
    observed_epoch: int,
    evidence_basis_id: str,
    qualification_registry: QualificationAuthorityRegistry,
    attestation: QualificationAttestation,
    authenticated_issuer: AuthenticatedIssuer,
    closure_proof: QualificationClosureProof,
    issuer_verification_secret: bytes,
    expected_registry_generation: str,
    qualification_lineage_id: str,
    authenticated_provenance_id: str,
    candidate_control_lineage_id: str,
    now,
) -> tuple[EvidenceProof, QualificationAuthorityRegistry]:
    """Admit SAE-30 provenance, derive proof class/ceiling, and build evidence."""
    world = _validate_qualified_world(world)
    obligation_id = _sha(obligation_id, "qualified evidence obligation_id")
    evidence_basis_id = _sha(evidence_basis_id, "qualified evidence basis_id")
    if not isinstance(attestation, QualificationAttestation):
        raise ProofWorldError("qualified evidence requires QualificationAttestation")
    if attestation.subject_id != evidence_basis_id or attestation.evidence_root_id != evidence_basis_id:
        raise ProofWorldError("qualified evidence attestation must bind exact evidence basis")
    if attestation.artifact_family != _PUBLIC_EVIDENCE_ARTIFACT_FAMILY:
        raise ProofWorldError("qualified evidence artifact family is outside SAE-80")
    if attestation.artifact_generation != world.authority_id:
        raise ProofWorldError("qualified evidence artifact generation is not exact Review World authority")
    if attestation.acr_generation != world.registry.generation:
        raise ProofWorldError("qualified evidence ACR generation mismatch")
    if attestation.qualification_protocol_generation != _PUBLIC_EVIDENCE_QUALIFICATION_GENERATION:
        raise ProofWorldError("qualified evidence qualification protocol generation mismatch")
    if attestation.qualification_lineage_id != qualification_lineage_id:
        raise ProofWorldError("qualified evidence qualification lineage mismatch")
    if attestation.authenticated_provenance_id != authenticated_provenance_id:
        raise ProofWorldError("qualified evidence authenticated provenance mismatch")
    try:
        proof_class = ProofClass(attestation.proof_class)
        authority_ceiling = ClosureGrade(attestation.closure_grade)
    except ValueError as exc:
        raise ProofWorldError("qualified evidence proof class/closure ceiling is unknown") from exc
    qualification, consumed = admit_qualification_attestation(
        registry=qualification_registry,
        attestation=attestation,
        authenticated_issuer=authenticated_issuer,
        closure_proof=closure_proof,
        issuer_verification_secret=issuer_verification_secret,
        subject_id=attestation.subject_id,
        artifact_family=attestation.artifact_family,
        domain=attestation.domain,
        artifact_generation=world.authority_id,
        acr_generation=world.registry.generation,
        qualification_protocol_generation=attestation.qualification_protocol_generation,
        evidence_root_id=evidence_basis_id,
        independence_state=attestation.independence_state,
        qualification_lineage_id=qualification_lineage_id,
        authenticated_provenance_id=authenticated_provenance_id,
        candidate_control_lineage_id=candidate_control_lineage_id,
        expected_registry_generation=expected_registry_generation,
        now=now,
    )
    issuer = qualification_registry.find(attestation.issuer_identity, attestation.issuer_generation)
    if issuer is None:
        raise ProofWorldError("qualified evidence issuer authorization is missing")
    issuer = _issuer_canonical(issuer)
    provisional_authority = AdmittedEvidenceAuthority(
        world.authority_id,
        attestation,
        qualification,
        issuer,
        proof_class.value,
        authority_ceiling.value,
        evidence_basis_id,
        "",
    )
    proof_authority = AdmittedEvidenceAuthority(
        world.authority_id,
        attestation,
        qualification,
        issuer,
        proof_class.value,
        authority_ceiling.value,
        evidence_basis_id,
        sha256_id(_public_evidence_authority_body(provisional_authority)),
    )
    _validate_admitted_evidence_authority(proof_authority, world=world)
    ceiling = _weaker(_PROOF_CEILINGS[proof_class], authority_ceiling)
    fields = _normalize_evidence_fields(
        proof_authority=proof_authority,
        proof_class=proof_class,
        claimed_closure=claimed_closure,
        obligation_id=obligation_id,
        contract_instance_ids=contract_instance_ids,
        world=world.coordinates,
        material_inputs=material_inputs,
        claims=claims,
        assumptions=assumptions,
        observed_epoch=observed_epoch,
        evidence_basis_id=evidence_basis_id,
        proof_ceiling=ceiling,
    )
    provisional = EvidenceProof(*fields, "")
    evidence = EvidenceProof(*fields, sha256_id(_evidence_body(provisional)))
    return evidence, consumed


def _validate_evidence(value: EvidenceProof, *, world_authority: WorldAuthority) -> EvidenceProof:
    if not isinstance(value, EvidenceProof):
        raise ProofWorldError("evidence has invalid record type")
    canonical_world = _coordinates_from_authority(world_authority)
    if isinstance(value.proof_authority, AdmittedEvidenceAuthority):
        if not isinstance(world_authority, QualifiedWorld):
            raise ProofWorldError("SAE-30 admitted evidence requires qualified public Review World authority")
        rooted = _validate_admitted_evidence_authority(value.proof_authority, world=world_authority)
        proof_class = ProofClass(rooted.proof_class)
        authority_ceiling = ClosureGrade(rooted.closure_ceiling)
        ceiling = _weaker(_PROOF_CEILINGS[proof_class], authority_ceiling)
        fields = _normalize_evidence_fields(
            proof_authority=rooted,
            proof_class=proof_class,
            claimed_closure=value.claimed_closure,
            obligation_id=value.obligation_id,
            contract_instance_ids=value.contract_instance_ids,
            world=canonical_world,
            material_inputs=value.material_inputs,
            claims=dict(value.claims),
            assumptions=value.assumptions,
            observed_epoch=value.observed_epoch,
            evidence_basis_id=value.evidence_basis_id,
            proof_ceiling=ceiling,
        )
        canonical = EvidenceProof(*fields, sha256_id(_evidence_body(EvidenceProof(*fields, ""))))
    else:
        if not isinstance(world_authority, ProofWorldAuthority):
            raise ProofWorldError("legacy qualified evidence requires its exact rooted world authority")
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
        "schema_version": "sergeant.sae80-proof-world-basis.v2",
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
    world_authority: WorldAuthority
    basis_id: str


def _make_basis(
    *,
    qualified_closure: QualifiedContractClosure,
    registry: ACRRegistry,
    expected_obligation: ExpectedObligation,
    world_authority: WorldAuthority,
) -> ProofWorldBasis:
    try:
        qualified = validate_qualified_contract_closure(qualified_closure)
    except ReviewWorldError as exc:
        raise ProofWorldError(f"invalid SAE-70 qualified closure: {exc}") from exc
    canonical_registry = _canonical_registry(registry)
    if canonical_registry.registry_id != qualified.registry_id:
        raise ProofWorldError("Proof World registry does not match SAE-70 qualified registry")
    if isinstance(world_authority, QualifiedWorld):
        authority = _validate_qualified_world(world_authority)
        if authority.qualified_closure != qualified or authority.registry != canonical_registry:
            raise ProofWorldError("qualified world does not bind exact SAE-70/ACR basis")
    else:
        try:
            authority = validate_proof_world_authority(world_authority)
        except ReviewWorldError as exc:
            raise ProofWorldError(f"invalid qualified Proof World authority: {exc}") from exc
        if authority.qualified_contract_closure != qualified or authority.acr_registry != canonical_registry:
            raise ProofWorldError("Proof World authority does not bind exact SAE-70/ACR basis")
    obligation, _ = _validate_expected_obligation(expected_obligation, qualified=qualified, registry=canonical_registry)
    provisional = ProofWorldBasis(qualified, canonical_registry, obligation, authority, "")
    return ProofWorldBasis(
        qualified,
        canonical_registry,
        obligation,
        authority,
        sha256_id(_basis_body(provisional)),
    )


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
    world = _coordinates_from_authority(basis.world_authority)
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
        if isinstance(item.proof_authority, AdmittedEvidenceAuthority):
            if item.proof_authority.attestation.domain != obligation.family:
                raise ProofWorldError("qualified evidence domain is not the exact SAE-70 obligation family")
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
        world = _coordinates_from_authority(basis.world_authority)
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
    world: WorldCoordinates | QualifiedWorld,
    evidence: Sequence[EvidenceProof],
    world_authority: WorldAuthority | None = None,
) -> ProofWorld:
    """Compile one candidate Proof World from rooted upstream authority."""
    if isinstance(world, QualifiedWorld):
        public_world = _validate_qualified_world(world)
        if world_authority is not None and world_authority != public_world:
            raise ProofWorldError("conflicting qualified world authority supplied")
        authority: WorldAuthority = public_world
        canonical_world = public_world.coordinates
    else:
        if world_authority is None:
            raise ProofWorldError("qualified Review World/dependency authority is required")
        authority = world_authority
        canonical_world = _coordinates_from_authority(authority)
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
