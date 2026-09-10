"""SAE-80 rooted authority inputs for Evidence + Proof World.

Task 11 may construct candidate Proof Worlds, but it may not treat a caller's
self-consistent strings or hashes as positive authority. This module binds the
candidate world to already-PROVEN SAE-10/30/40/60/70 authority records and
binds an evidence proof class to an already-derived SAE-30 qualification.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .assurance_contract_registry import ACRRegistry, ClosureGrade
from .assurance_ledger import JudgeAssuranceLedger, LedgerRecordKind
from .capability_qualification import CapabilityPassport, SemanticCapabilityEvaluation
from .contract_closure_protocol import QualifiedContractClosure, validate_qualified_contract_closure
from .qualification_authority import (
    AuthenticatedIssuer,
    DerivedQualification,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityRegistry,
    QualificationIssuerAuthorization,
    QualificationAuthorityError,
    QualificationClosureProof,
    admit_qualification_attestation,
)
from .review_authority_bundle import ReviewAuthorityBundle, RABAuthorization
from .review_world import GitHubReviewWorld, ReviewWorldError, require_full_sha256, sha256_id
from .semantic_capability_protocol import QualifiedSemanticCapability, qualify_bounded_literal_dispatch


class ProofWorldAuthorityError(ReviewWorldError):
    """Raised when SAE-80 inputs are not rooted in qualified upstream authority."""


EVIDENCE_ARTIFACT_FAMILY = "sae80-evidence-proof"
EVIDENCE_DOMAIN = "sergeant.sae80-proof-world.v1"
EVIDENCE_QUALIFICATION_GENERATION = "sae80-evidence-qualification-v1"


def _sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise ProofWorldAuthorityError(str(exc)) from exc


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ProofWorldAuthorityError(f"{field} must be canonical and non-empty")
    return value


def _canonical_issuer(value: QualificationIssuerAuthorization) -> QualificationIssuerAuthorization:
    if not isinstance(value, QualificationIssuerAuthorization):
        raise ProofWorldAuthorityError("qualification registry contains invalid issuer authority")
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
        raise ProofWorldAuthorityError("qualification issuer authorization identity mismatch")
    return value


def _canonical_qualification_registry(value: QualificationAuthorityRegistry) -> QualificationAuthorityRegistry:
    if not isinstance(value, QualificationAuthorityRegistry):
        raise ProofWorldAuthorityError("qualified Proof World requires QualificationAuthorityRegistry")
    issuers = tuple(_canonical_issuer(item) for item in value.issuers)
    canonical = QualificationAuthorityRegistry.create(
        generation=value.generation,
        issuers=issuers,
        revoked_attestation_ids=value.revoked_attestation_ids,
        consumed_attestation_ids=value.consumed_attestation_ids,
    )
    if canonical != value:
        raise ProofWorldAuthorityError("qualification authority registry identity mismatch")
    return value


def _canonical_acr(value: ACRRegistry) -> ACRRegistry:
    if not isinstance(value, ACRRegistry):
        raise ProofWorldAuthorityError("qualified Proof World requires ACRRegistry")
    try:
        canonical = ACRRegistry.from_payload(value.to_payload())
    except (ReviewWorldError, TypeError, ValueError) as exc:
        raise ProofWorldAuthorityError(f"ACR registry identity mismatch: {exc}") from exc
    if canonical != value:
        raise ProofWorldAuthorityError("ACR registry is not canonical")
    return value


def _rab_component(rab: ReviewAuthorityBundle, name: str):
    for item in rab.components:
        if item.name == name:
            return item
    raise ProofWorldAuthorityError(f"RAB is missing required component {name}")


def _dependency_tuple(values: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, Mapping):
        raise ProofWorldAuthorityError("dependency generations must be a mapping")
    items = tuple(
        sorted(
            (_string(k, "dependency name"), _string(v, "dependency generation"))
            for k, v in values.items()
        )
    )
    if len({k for k, _ in items}) != len(items):
        raise ProofWorldAuthorityError("dependency generations contain duplicate names")
    return items


def _world_authority_body(value: "ProofWorldAuthority") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-proof-world-authority.v1",
        "review_world_id": value.review_world.review_world_id,
        "rab_id": value.rab.rab_id,
        "rab_authorization_generation": value.rab_authorization.authorization_generation,
        "ledger_id": value.ledger.ledger_id,
        "qualification_registry_id": value.qualification_registry.registry_id,
        "acr_registry_id": value.acr_registry.registry_id,
        "semantic_qualification_id": value.semantic_capability.qualification_id,
        "contract_closure_qualification_id": value.qualified_contract_closure.qualification_id,
        "candidate_generation": value.candidate_generation,
        "framework_generation": value.framework_generation,
        "provider_generation": value.provider_generation,
        "dependency_generations": dict(value.dependency_generations),
        "epoch": value.epoch,
    }


@dataclass(frozen=True)
class ProofWorldAuthority:
    review_world: GitHubReviewWorld
    rab: ReviewAuthorityBundle
    rab_authorization: RABAuthorization
    ledger: JudgeAssuranceLedger
    qualification_registry: QualificationAuthorityRegistry
    acr_registry: ACRRegistry
    capability_passport: CapabilityPassport
    capability_evaluation: SemanticCapabilityEvaluation
    semantic_capability: QualifiedSemanticCapability
    qualified_contract_closure: QualifiedContractClosure
    candidate_generation: str
    framework_generation: str
    provider_generation: str
    dependency_generations: tuple[tuple[str, str], ...]
    epoch: int
    authority_id: str


def bind_proof_world_authority(
    *,
    review_world: GitHubReviewWorld,
    rab: ReviewAuthorityBundle,
    rab_authorization: RABAuthorization,
    ledger: JudgeAssuranceLedger,
    qualification_registry: QualificationAuthorityRegistry,
    acr_registry: ACRRegistry,
    capability_passport: CapabilityPassport,
    capability_evaluation: SemanticCapabilityEvaluation,
    semantic_capability: QualifiedSemanticCapability,
    qualified_contract_closure: QualifiedContractClosure,
    epoch: int,
) -> ProofWorldAuthority:
    if not isinstance(review_world, GitHubReviewWorld):
        raise ProofWorldAuthorityError("qualified Review World authority is required")
    review_world.validate()
    if not isinstance(rab, ReviewAuthorityBundle):
        raise ProofWorldAuthorityError("qualified RAB authority is required")
    if rab.expected_id() != rab.rab_id or review_world.rab_id != rab.rab_id:
        raise ProofWorldAuthorityError("Review World is not bound to exact RAB authority")
    if not isinstance(rab_authorization, RABAuthorization):
        raise ProofWorldAuthorityError("RAB authorization record is required")
    rab_authorization.validate()
    if rab_authorization.rab_id != rab.rab_id or rab_authorization.state != "authorized":
        raise ProofWorldAuthorityError("RAB is not currently authorized")

    qreg = _canonical_qualification_registry(qualification_registry)
    acr = _canonical_acr(acr_registry)
    qcomp = _rab_component(rab, "qualification_authority_registry")
    acomp = _rab_component(rab, "acr_generation")
    if qcomp.lifecycle_state != "active" or qcomp.content_id != qreg.registry_id or qcomp.generation != qreg.generation:
        raise ProofWorldAuthorityError("RAB does not bind exact qualification authority registry")
    if acomp.lifecycle_state != "active" or acomp.content_id != acr.registry_id or acomp.generation != acr.generation:
        raise ProofWorldAuthorityError("RAB does not bind exact ACR registry generation")

    if not isinstance(ledger, JudgeAssuranceLedger):
        raise ProofWorldAuthorityError("qualified SAE-40 assurance ledger is required")
    ledger.validate()
    if ledger.review_world_id != review_world.review_world_id or ledger.rab_id != rab.rab_id:
        raise ProofWorldAuthorityError("assurance ledger belongs to a different Review World/RAB")
    review_records = [record for record in ledger.records if record.kind is LedgerRecordKind.REVIEW_WORLD]
    if not review_records or not any(
        record.payload().get("review_world_id") == review_world.review_world_id for record in review_records
    ):
        raise ProofWorldAuthorityError("assurance ledger lacks the exact Review World authority record")

    if not isinstance(capability_passport, CapabilityPassport) or not isinstance(capability_evaluation, SemanticCapabilityEvaluation):
        raise ProofWorldAuthorityError("qualified SAE-60 capability inputs are required")
    reproduced = qualify_bounded_literal_dispatch(passport=capability_passport, evaluation=capability_evaluation)
    if not isinstance(semantic_capability, QualifiedSemanticCapability) or reproduced != semantic_capability:
        raise ProofWorldAuthorityError("semantic capability is not the exact SAE-60 qualified generation")

    closure = validate_qualified_contract_closure(qualified_contract_closure)
    if closure.registry_id != acr.registry_id:
        raise ProofWorldAuthorityError("SAE-70 qualified closure and ACR registry generation disagree")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise ProofWorldAuthorityError("Proof World authority epoch must be a non-negative integer")

    candidate_generation = review_world.diff.head_commit
    framework_generation = capability_passport.framework_generation
    provider_generation = qreg.generation
    dependencies = _dependency_tuple(
        {
            "review-world": review_world.review_generation,
            "rab-authorization": rab_authorization.authorization_generation,
            "assurance-ledger": ledger.generation,
            "semantic-capability": semantic_capability.qualification_id,
            "contract-closure": closure.qualification_id,
            "acr-registry": acr.registry_id,
        }
    )
    provisional = ProofWorldAuthority(
        review_world, rab, rab_authorization, ledger, qreg, acr,
        capability_passport, capability_evaluation, semantic_capability, closure,
        candidate_generation, framework_generation, provider_generation, dependencies, epoch, "",
    )
    return ProofWorldAuthority(
        review_world, rab, rab_authorization, ledger, qreg, acr,
        capability_passport, capability_evaluation, semantic_capability, closure,
        candidate_generation, framework_generation, provider_generation, dependencies, epoch,
        sha256_id(_world_authority_body(provisional)),
    )


def validate_proof_world_authority(value: ProofWorldAuthority) -> ProofWorldAuthority:
    if not isinstance(value, ProofWorldAuthority):
        raise ProofWorldAuthorityError("qualified Proof World authority has invalid record type")
    canonical = bind_proof_world_authority(
        review_world=value.review_world,
        rab=value.rab,
        rab_authorization=value.rab_authorization,
        ledger=value.ledger,
        qualification_registry=value.qualification_registry,
        acr_registry=value.acr_registry,
        capability_passport=value.capability_passport,
        capability_evaluation=value.capability_evaluation,
        semantic_capability=value.semantic_capability,
        qualified_contract_closure=value.qualified_contract_closure,
        epoch=value.epoch,
    )
    if canonical != value:
        raise ProofWorldAuthorityError("qualified Proof World authority identity mismatch")
    return value


def _canonical_attestation(value: QualificationAttestation) -> QualificationAttestation:
    if not isinstance(value, QualificationAttestation):
        raise ProofWorldAuthorityError("evidence requires QualificationAttestation")
    canonical = QualificationAttestation.create(**value.constructor_fields())
    if canonical != value:
        raise ProofWorldAuthorityError("evidence qualification attestation identity mismatch")
    return value


def _qualification_body(value: DerivedQualification) -> dict[str, object]:
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


def _validate_derived(value: DerivedQualification) -> DerivedQualification:
    if not isinstance(value, DerivedQualification) or value.state != "QUALIFIED":
        raise ProofWorldAuthorityError("evidence requires already-derived QUALIFIED SAE-30 authority")
    for field in (
        "subject_id", "attestation_id", "issuer_authorization_id", "evidence_root_id",
        "qualification_lineage_id", "authenticated_provenance_id", "closure_proof_id", "qualification_id",
    ):
        _sha(getattr(value, field), f"derived qualification {field}")
    if value.qualification_id != sha256_id(_qualification_body(value)):
        raise ProofWorldAuthorityError("derived qualification identity mismatch")
    return value


def _evidence_authority_body(value: "QualifiedEvidenceProofAuthority") -> dict[str, object]:
    return {
        "schema_version": "sergeant.sae80-qualified-evidence-proof-authority.v1",
        "world_authority_id": value.world_authority_id,
        "obligation_id": value.obligation_id,
        "evidence_basis_id": value.evidence_basis_id,
        "attestation_id": value.attestation.attestation_id,
        "qualification_id": value.qualification.qualification_id,
        "issuer_authorization_id": value.issuer_authorization.authorization_id,
        "proof_class": value.proof_class,
        "closure_ceiling": value.closure_ceiling,
    }


@dataclass(frozen=True)
class _VerifierEvidenceAdmission:
    authority_id: str
    qualification_id: str
    attestation_id: str
    closure_proof_id: str


@dataclass(frozen=True)
class QualifiedEvidenceProofAuthority:
    world_authority_id: str
    obligation_id: str
    evidence_basis_id: str
    attestation: QualificationAttestation
    qualification: DerivedQualification
    issuer_authorization: QualificationIssuerAuthorization
    proof_class: str
    closure_ceiling: str
    authority_id: str
    _verifier_admission: _VerifierEvidenceAdmission | None = field(
        default=None, init=False, repr=False, compare=False
    )


def _seal_evidence_authority(value: QualifiedEvidenceProofAuthority) -> QualifiedEvidenceProofAuthority:
    object.__setattr__(
        value,
        "_verifier_admission",
        _VerifierEvidenceAdmission(
            authority_id=value.authority_id,
            qualification_id=value.qualification.qualification_id,
            attestation_id=value.attestation.attestation_id,
            closure_proof_id=value.qualification.closure_proof_id,
        ),
    )
    return value


def _validate_evidence_authority_content(
    value: QualifiedEvidenceProofAuthority,
    *,
    world_authority: ProofWorldAuthority,
) -> QualifiedEvidenceProofAuthority:
    world = validate_proof_world_authority(world_authority)
    obligation_id = _sha(value.obligation_id, "evidence authority obligation_id")
    evidence_basis_id = _sha(value.evidence_basis_id, "evidence authority basis_id")
    attestation = _canonical_attestation(value.attestation)
    qualification = _validate_derived(value.qualification)

    try:
        issuer = world.qualification_registry.find(attestation.issuer_identity, attestation.issuer_generation)
    except ReviewWorldError as exc:
        raise ProofWorldAuthorityError(str(exc)) from exc
    _canonical_issuer(issuer)
    if value.issuer_authorization != issuer:
        raise ProofWorldAuthorityError("evidence authority issuer does not match trusted registry")
    if issuer.state is not IssuerState.ACTIVE:
        raise ProofWorldAuthorityError("evidence qualification issuer is not active")
    if attestation.attestation_id in world.qualification_registry.revoked_attestation_ids:
        raise ProofWorldAuthorityError("evidence qualification attestation is revoked")

    if qualification.attestation_id != attestation.attestation_id:
        raise ProofWorldAuthorityError("derived qualification does not bind exact attestation")
    if qualification.issuer_authorization_id != issuer.authorization_id:
        raise ProofWorldAuthorityError("derived qualification does not bind exact issuer authorization")
    for name in (
        "subject_id", "artifact_family", "domain", "artifact_generation", "evidence_root_id",
        "independence_state", "qualification_lineage_id", "authenticated_provenance_id",
    ):
        if getattr(qualification, name) != getattr(attestation, name):
            raise ProofWorldAuthorityError(f"derived qualification {name} does not match attestation")

    if attestation.subject_id != obligation_id:
        raise ProofWorldAuthorityError("evidence qualification subject is not the SAE-70 obligation")
    if attestation.artifact_family != EVIDENCE_ARTIFACT_FAMILY or attestation.domain != EVIDENCE_DOMAIN:
        raise ProofWorldAuthorityError("evidence qualification artifact/domain is outside SAE-80")
    if attestation.artifact_generation != world.candidate_generation:
        raise ProofWorldAuthorityError("evidence qualification candidate generation is stale or fabricated")
    if attestation.acr_generation != world.acr_registry.generation:
        raise ProofWorldAuthorityError("evidence qualification ACR generation mismatch")
    if attestation.qualification_protocol_generation != EVIDENCE_QUALIFICATION_GENERATION:
        raise ProofWorldAuthorityError("evidence qualification protocol generation mismatch")
    if attestation.evidence_root_id != evidence_basis_id or qualification.evidence_root_id != evidence_basis_id:
        raise ProofWorldAuthorityError("evidence qualification does not bind exact evidence basis")
    if attestation.independence_state != "INDEPENDENT":
        raise ProofWorldAuthorityError("evidence qualification lacks independent provenance")
    if attestation.proof_class not in issuer.proof_classes:
        raise ProofWorldAuthorityError("evidence proof class is outside issuer qualification authority")
    if attestation.closure_grade not in issuer.closure_grades:
        raise ProofWorldAuthorityError("evidence closure ceiling is outside issuer qualification authority")
    if value.proof_class != attestation.proof_class or value.closure_ceiling != attestation.closure_grade:
        raise ProofWorldAuthorityError("evidence authority proof class/closure ceiling mismatch")
    try:
        ClosureGrade(attestation.closure_grade)
    except ValueError as exc:
        raise ProofWorldAuthorityError("evidence qualification closure grade is unknown") from exc
    if value.world_authority_id != world.authority_id:
        raise ProofWorldAuthorityError("evidence authority is bound to another Proof World authority")
    if value.authority_id != sha256_id(_evidence_authority_body(value)):
        raise ProofWorldAuthorityError("qualified evidence proof authority identity mismatch")
    return value


def bind_evidence_proof_authority(
    *,
    world_authority: ProofWorldAuthority,
    obligation_id: str,
    evidence_basis_id: str,
    attestation: QualificationAttestation,
    qualification: DerivedQualification | None = None,
    authenticated_issuer: AuthenticatedIssuer | None = None,
    closure_proof: QualificationClosureProof | None = None,
    issuer_verification_secret: bytes | None = None,
    expected_registry_generation: str | None = None,
    candidate_control_lineage_id: str | None = None,
    now=None,
) -> QualifiedEvidenceProofAuthority:
    world = validate_proof_world_authority(world_authority)
    obligation_id = _sha(obligation_id, "evidence authority obligation_id")
    evidence_basis_id = _sha(evidence_basis_id, "evidence authority basis_id")
    attestation = _canonical_attestation(attestation)

    if (
        authenticated_issuer is None
        or closure_proof is None
        or issuer_verification_secret is None
        or expected_registry_generation is None
        or candidate_control_lineage_id is None
        or now is None
    ):
        raise ProofWorldAuthorityError(
            "verifier-authentic SAE-30 admission is required for evidence authority"
        )

    try:
        derived, _ = admit_qualification_attestation(
            registry=world.qualification_registry,
            attestation=attestation,
            authenticated_issuer=authenticated_issuer,
            closure_proof=closure_proof,
            issuer_verification_secret=issuer_verification_secret,
            expected_registry_generation=expected_registry_generation,
            subject_id=obligation_id,
            artifact_family=EVIDENCE_ARTIFACT_FAMILY,
            domain=EVIDENCE_DOMAIN,
            artifact_generation=world.candidate_generation,
            acr_generation=world.acr_registry.generation,
            qualification_protocol_generation=EVIDENCE_QUALIFICATION_GENERATION,
            evidence_root_id=evidence_basis_id,
            independence_state="INDEPENDENT",
            qualification_lineage_id=attestation.qualification_lineage_id,
            authenticated_provenance_id=attestation.authenticated_provenance_id,
            candidate_control_lineage_id=candidate_control_lineage_id,
            now=now,
        )
    except QualificationAuthorityError as exc:
        raise ProofWorldAuthorityError(
            f"evidence qualification lacks verifier-authentic SAE-30 admission: {exc}"
        ) from exc

    if qualification is not None and qualification != derived:
        raise ProofWorldAuthorityError(
            "caller qualification does not match verifier-derived SAE-30 authority"
        )
    qualification = derived
    try:
        issuer = world.qualification_registry.find(attestation.issuer_identity, attestation.issuer_generation)
    except ReviewWorldError as exc:
        raise ProofWorldAuthorityError(str(exc)) from exc
    _canonical_issuer(issuer)

    provisional = QualifiedEvidenceProofAuthority(
        world.authority_id, obligation_id, evidence_basis_id, attestation, qualification,
        issuer, attestation.proof_class, attestation.closure_grade, "",
    )
    authority = QualifiedEvidenceProofAuthority(
        world.authority_id, obligation_id, evidence_basis_id, attestation, qualification,
        issuer, attestation.proof_class, attestation.closure_grade,
        sha256_id(_evidence_authority_body(provisional)),
    )
    _validate_evidence_authority_content(authority, world_authority=world)
    return _seal_evidence_authority(authority)


def validate_evidence_proof_authority(
    value: QualifiedEvidenceProofAuthority,
    *,
    world_authority: ProofWorldAuthority,
) -> QualifiedEvidenceProofAuthority:
    if not isinstance(value, QualifiedEvidenceProofAuthority):
        raise ProofWorldAuthorityError("qualified evidence proof authority has invalid record type")
    value = _validate_evidence_authority_content(value, world_authority=world_authority)
    expected = _VerifierEvidenceAdmission(
        authority_id=value.authority_id,
        qualification_id=value.qualification.qualification_id,
        attestation_id=value.attestation.attestation_id,
        closure_proof_id=value.qualification.closure_proof_id,
    )
    if value._verifier_admission != expected:
        raise ProofWorldAuthorityError(
            "qualified evidence proof authority lacks verifier-authentic admission capability"
        )
    return value
