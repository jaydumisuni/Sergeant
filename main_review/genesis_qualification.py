"""Fail-closed SAE-150 integrated Genesis qualification package assembly.

Positive authority is never read from package fields. External evidence is
re-derived through the canonical SAE-30 EEPR constructor against provenance
verifiers supplied outside the package; qualification obligations close only
through attestations admitted into a trusted SAE-30 qualification registry;
external-review lane cardinality comes from ratified ACR lanes and never falls
below the SPIKE-EXT floor. Every trust anchor defaults to empty and fails closed.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .assurance_contract_registry import ExternalReviewLane
from .external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ExternalEvidenceProvenanceError,
    ExternalEvidenceProvenanceRecord,
    ExternalReviewLaneRequirement,
    IndependenceState,
    ProvenanceVerifierAuthorization,
    evaluate_external_review_census,
)
from .qualification_authority import (
    DerivedQualification,
    GenesisQualificationPackage,
    IssuerState,
    QualificationAttestation,
    QualificationAuthorityError,
    QualificationAuthorityRegistry,
)
from .review_world import ReviewWorldError, require_full_sha256, require_git_object_id, sha256_id

REQUIRED_PROVEN_NODE_BINDINGS = {
    "SAE-100": "73541e17e8ef7c208d2bfa91012695b6917e549b",
    "SAE-110": "1ba0fbbafc9423ed9b098137e0669fe941b052d0",
    "SAE-120": "e29ffbcd6aad7336e5827cbb1e6469be398cf730",
    "SAE-130A": "97c2d939df51a21828a6ea96f05458207ac0793c",
    "SAE-130B": "7af19145d13e173a9fe727cd3977c483aa4c8057",
    "SAE-130C": "4b3a59117c6ccfac5d6d6d47f795cb4333566b69",
    "SAE-130D": "948c450e15f71f3823be0df1fedf27650edec067",
    "SAE-130E": "a889f512662e0b1d62a81582025677276967806d",
    "SAE-140": "126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0",
    "SPIKE-EXT": "5a42072517efef7c1e621f12a99e9e2cbf610281",
}
PROVEN_NODE_BINDING_KINDS = {node: "blob" if node == "SPIKE-EXT" else "commit" for node in REQUIRED_PROVEN_NODE_BINDINGS}
SPIKE_EXT_CLOSEOUT_MANIFEST = "docs/69-spike-ext-proven-lifecycle-closeout-manifest.json"
REQUIRED_NODES = tuple(REQUIRED_PROVEN_NODE_BINDINGS)
REQUIRED_MUTATIONS = ("omission", "undercount", "cardinality", "acr", "material_input", "falsifier", "authority", "common_mode")
INDEPENDENT_OBLIGATIONS = ("independent_hidden_cases", "independent_hostile_implementation_review")
REQUIRED_QUALIFICATION_OBLIGATIONS = (
    "preservation_proof", "model_blackout_proof", "cpu_proof", "historical_replay", "clean_controls",
    "unrelated_transfer", *INDEPENDENT_OBLIGATIONS, *(f"mutation.{family}" for family in REQUIRED_MUTATIONS),
)
GENESIS_ARTIFACT_FAMILY_PREFIX = "sergeant.genesis."
# SPIKE-EXT (docs/65) accepted source classes and cardinality proposal; SC-5 vendor/account
# diversity is not a source class. SAE-20 never ratified a Genesis lane, so this is a floor only.
ACCEPTED_EXTERNAL_SOURCE_CLASSES = ("SC-1", "SC-2", "SC-3", "SC-4", "SC-6")
LANE_CARDINALITY_FLOOR = 2
LANE_SOURCE_CLASS_FLOOR = 2
DEFAULT_GENESIS_LANE_ID = "genesis-independent"
GENERATION_FIELDS = ("candidate_generation", "rab_generation", "acr_generation", "rust_generation", "qualification_protocol_generation")
_MUTABLE_ALIASES = {"latest", "current", "head", "tip", "main", "master"}
_EEPR_CREATE_FIELDS = (
    "evidence_id", "evidence_digest", "review_world_id", "source_principal_id", "authenticated_source_provenance",
    "source_organization", "source_class", "source_authority_generation", "creation_generation",
    "candidate_authoring_relationship", "qualification_corpus_relationship", "candidate_infrastructure_relationship",
    "reviewer_tool_lineage", "prompt_controller", "input_selector", "finding_selector", "provenance_verification_method",
)


class GenesisQualificationError(ValueError):
    """Raised when mandatory Genesis package structure is absent or malformed."""


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GenesisQualificationError(f"{field} must be a mapping")
    return dict(value)


def _require_sequence(value: object, field: str) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise GenesisQualificationError(f"{field} must be a non-string sequence")
    return list(value)


def _require_iterable(value: object, field: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Iterable):
        raise GenesisQualificationError(f"{field} must be a non-string iterable")
    return tuple(value)


def _canonical_strings(value: object, field: str) -> list[str]:
    values = _require_sequence(value, field)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise GenesisQualificationError(f"{field} must contain non-empty strings")
    return [item.strip() for item in values]


def _generation(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or value.lower() in _MUTABLE_ALIASES:
        raise GenesisQualificationError(f"{field} must be a canonical immutable generation identifier")
    return value


def _generations(row: Mapping[str, Any]) -> dict[str, str]:
    generations = {field: _generation(row.get(field), field) for field in GENERATION_FIELDS}
    try:
        require_git_object_id(generations["candidate_generation"], "candidate_generation")
        require_full_sha256(generations["rab_generation"], "rab_generation")
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise GenesisQualificationError(str(exc)) from exc
    return generations


def _review_world(value: object) -> str:
    if not isinstance(value, str):
        raise GenesisQualificationError("review_world_id must be a canonical sha256 identity")
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise GenesisQualificationError("review_world_id must be a canonical sha256 identity")
    return text


def _trusted_verifiers(values: object) -> dict[str, tuple[ProvenanceVerifierAuthorization, bytes]]:
    trusted: dict[str, tuple[ProvenanceVerifierAuthorization, bytes]] = {}
    for item in _require_iterable(values, "trusted_provenance_verifiers"):
        if not (
            isinstance(item, tuple) and len(item) == 2
            and isinstance(item[0], ProvenanceVerifierAuthorization) and isinstance(item[1], bytes)
        ):
            raise GenesisQualificationError("trusted provenance verifiers must be (ProvenanceVerifierAuthorization, secret) pairs")
        trusted[item[0].authorization_id] = item
    return trusted


def _rederive(
    record: ExternalEvidenceProvenanceRecord, *, proof: AuthenticatedProvenanceProof | None,
    verifier: tuple[ProvenanceVerifierAuthorization, bytes] | None,
) -> ExternalEvidenceProvenanceRecord:
    authorization, secret = verifier if verifier is not None else (None, None)
    try:
        return ExternalEvidenceProvenanceRecord.create(
            **{field: getattr(record, field) for field in _EEPR_CREATE_FIELDS},
            control_lineage_facts=record.control_lineage_facts,
            provenance_authorization=authorization,
            authenticated_provenance_proof=proof,
            provenance_verification_secret=secret,
        )
    except ExternalEvidenceProvenanceError as exc:
        raise GenesisQualificationError(f"external evidence provenance is non-canonical: {exc}") from exc


def _verified_evidence(
    row: Mapping[str, Any], *, verifiers: Mapping[str, tuple[ProvenanceVerifierAuthorization, bytes]], blockers: list[str],
) -> list[ExternalEvidenceProvenanceRecord]:
    records = _require_sequence(row.get("external_evidence"), "external_evidence")
    if any(not isinstance(record, ExternalEvidenceProvenanceRecord) for record in records):
        raise GenesisQualificationError("external_evidence must contain canonical ExternalEvidenceProvenanceRecord values")
    proofs_value = row.get("external_evidence_proofs")
    proofs = {} if proofs_value is None else _require_mapping(proofs_value, "external_evidence_proofs")
    if any(not isinstance(proof, AuthenticatedProvenanceProof) for proof in proofs.values()):
        raise GenesisQualificationError("external_evidence_proofs must contain AuthenticatedProvenanceProof values")
    verified = []
    for record in records:
        verifier = verifiers.get(record.provenance_verifier_authorization_id)
        rederived = _rederive(record, proof=proofs.get(record.evidence_id), verifier=verifier)
        if rederived != record:
            # Record fields claim more than canonical re-verification derives; conserve UNKNOWN_INDEPENDENCE.
            unrooted = record.provenance_authenticated and verifier is None
            blocker = "EXTERNAL_PROVENANCE_VERIFIER_UNROOTED" if unrooted else "EXTERNAL_PROVENANCE_UNVERIFIED"
            if blocker not in blockers:
                blockers.append(blocker)
            rederived = _rederive(record, proof=None, verifier=None)
        verified.append(rederived)
    if len({record.evidence_id for record in verified}) != len(verified):
        raise GenesisQualificationError("external review census contains duplicate evidence identity")
    return verified


def _lane_requirements(values: object) -> tuple[tuple[ExternalReviewLaneRequirement, ...], bool]:
    lanes = _require_iterable(values, "ratified_external_review_lanes")
    if any(not isinstance(lane, ExternalReviewLane) for lane in lanes):
        raise GenesisQualificationError("ratified external review lanes must be canonical ACR ExternalReviewLane values")
    sources = lanes or (ExternalReviewLane.create(DEFAULT_GENESIS_LANE_ID, LANE_CARDINALITY_FLOOR),)
    try:
        requirements = tuple(
            ExternalReviewLaneRequirement.create(
                lane_id=lane.lane_id,
                minimum_instances=max(lane.minimum_instances, LANE_CARDINALITY_FLOOR),
                minimum_source_classes=LANE_SOURCE_CLASS_FLOOR,
            )
            for lane in sources
        )
    except ExternalEvidenceProvenanceError as exc:
        raise GenesisQualificationError(f"external review lane requirement invalid: {exc}") from exc
    return requirements, bool(lanes)


def _admitted_qualification_map(values: object) -> dict[str, DerivedQualification]:
    admitted: dict[str, DerivedQualification] = {}
    for item in _require_iterable(values, "admitted_qualifications"):
        if not isinstance(item, DerivedQualification):
            raise GenesisQualificationError("admitted_qualifications must contain canonical DerivedQualification values")
        if item.state != "QUALIFIED":
            raise GenesisQualificationError("admitted qualification must have QUALIFIED state")
        if item.attestation_id in admitted:
            raise GenesisQualificationError("duplicate admitted qualification attestation identity")
        admitted[item.attestation_id] = item
    return admitted


def _attestation_admitted(
    attestation: QualificationAttestation, obligation: str, *, registry: QualificationAuthorityRegistry | None,
    admitted: Mapping[str, DerivedQualification], review_world_id: str, generations: Mapping[str, str],
) -> bool:
    if registry is None:
        return False
    qualification = admitted.get(attestation.attestation_id)
    if qualification is None or attestation.attestation_id not in registry.consumed_attestation_ids:
        return False
    if attestation.attestation_id in registry.revoked_attestation_ids:
        return False
    try:
        issuer = registry.find(attestation.issuer_identity, attestation.issuer_generation)
    except QualificationAuthorityError:
        return False
    return (
        qualification.state == "QUALIFIED"
        and qualification.subject_id == attestation.subject_id
        and qualification.artifact_family == attestation.artifact_family
        and qualification.domain == attestation.domain
        and qualification.artifact_generation == attestation.artifact_generation
        and qualification.attestation_id == attestation.attestation_id
        and qualification.evidence_root_id == attestation.evidence_root_id
        and qualification.independence_state == attestation.independence_state
        and qualification.qualification_lineage_id == attestation.qualification_lineage_id
        and qualification.authenticated_provenance_id == attestation.authenticated_provenance_id
        and issuer.state is IssuerState.ACTIVE
        and qualification.issuer_authorization_id == issuer.authorization_id
        and attestation.artifact_family in issuer.artifact_families
        and attestation.domain in issuer.domains
        and attestation.proof_class in issuer.proof_classes
        and attestation.closure_grade in issuer.closure_grades
        and attestation.independence_state in issuer.allowed_independence_states
        and attestation.subject_id == review_world_id
        and attestation.artifact_generation == generations["candidate_generation"]
        and attestation.acr_generation == generations["acr_generation"]
        and attestation.qualification_protocol_generation == generations["qualification_protocol_generation"]
        and (obligation not in INDEPENDENT_OBLIGATIONS or attestation.independence_state == IndependenceState.INDEPENDENT.value)
    )


def _closed_obligations(
    values: object, *, registry: object, admitted_qualifications: object, review_world_id: str, generations: Mapping[str, str],
) -> dict[str, str]:
    if registry is not None and not isinstance(registry, QualificationAuthorityRegistry):
        raise GenesisQualificationError("qualification_registry must be a trusted QualificationAuthorityRegistry")
    admitted = _admitted_qualification_map(admitted_qualifications)
    closed: dict[str, str] = {}
    seen: set[str] = set()
    for attestation in _require_sequence(values, "qualification_attestations"):
        if not isinstance(attestation, QualificationAttestation):
            raise GenesisQualificationError("qualification_attestations must contain QualificationAttestation values")
        try:
            canonical = QualificationAttestation.create(**attestation.constructor_fields())
        except QualificationAuthorityError as exc:
            raise GenesisQualificationError(f"qualification attestation is non-canonical: {exc}") from exc
        if canonical != attestation:
            raise GenesisQualificationError("qualification attestation identity is non-canonical")
        family = attestation.artifact_family
        obligation = family.removeprefix(GENESIS_ARTIFACT_FAMILY_PREFIX)
        if not family.startswith(GENESIS_ARTIFACT_FAMILY_PREFIX) or obligation not in REQUIRED_QUALIFICATION_OBLIGATIONS:
            raise GenesisQualificationError("qualification attestation is outside the required Genesis obligation census")
        if obligation in seen:
            raise GenesisQualificationError(f"duplicate qualification attestation for {obligation}")
        seen.add(obligation)
        if _attestation_admitted(
            attestation, obligation, registry=registry, admitted=admitted,
            review_world_id=review_world_id, generations=generations,
        ):
            closed[obligation] = attestation.attestation_id
    return closed


def qualify_genesis_package(
    package: Mapping[str, Any],
    *,
    trusted_provenance_verifiers: Iterable[tuple[ProvenanceVerifierAuthorization, bytes]] = (),
    ratified_external_review_lanes: Iterable[ExternalReviewLane] = (),
    qualification_registry: QualificationAuthorityRegistry | None = None,
    admitted_qualifications: Iterable[DerivedQualification] = (),
    trusted_generation_bindings: Mapping[str, str] | None = None,
    trusted_external_evidence_bindings: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    row = _require_mapping(package, "package")
    generations = _generations(row)
    review_world_id = _review_world(row.get("review_world_id"))

    nodes = _require_mapping(row.get("required_proven_nodes"), "required_proven_nodes")
    if nodes != REQUIRED_PROVEN_NODE_BINDINGS:
        raise GenesisQualificationError("canonical SAE-150 prerequisite generations must match the frozen manifest exactly")

    if row.get("limitations") is None:
        raise GenesisQualificationError("limitations must be declared explicitly")
    limitations = _canonical_strings(row.get("limitations"), "limitations")
    survivors = _canonical_strings(row.get("surviving_mutants"), "surviving_mutants")
    unknowns = _canonical_strings(row.get("residual_unknowns"), "residual_unknowns")
    closed = _closed_obligations(
        row.get("qualification_attestations"), registry=qualification_registry, admitted_qualifications=admitted_qualifications,
        review_world_id=review_world_id, generations=generations,
    )

    blockers: list[str] = []
    trusted = {} if trusted_generation_bindings is None else _require_mapping(trusted_generation_bindings, "trusted_generation_bindings")
    for field in GENERATION_FIELDS:
        if trusted.get(field) != generations[field]:
            blockers.append(f"UNTRUSTED_GENERATION_BINDING:{field}")
    verified = _verified_evidence(row, verifiers=_trusted_verifiers(trusted_provenance_verifiers), blockers=blockers)
    evidence_bindings = {} if trusted_external_evidence_bindings is None else _require_mapping(
        trusted_external_evidence_bindings, "trusted_external_evidence_bindings"
    )
    for record in verified:
        if evidence_bindings.get(record.evidence_id) != record.eepr_id:
            blockers.append(f"EXTERNAL_EVIDENCE_CLAIMS_UNTRUSTED:{record.evidence_id}")
    bound = [
        record for record in verified
        if record.review_world_id == review_world_id and evidence_bindings.get(record.evidence_id) == record.eepr_id
    ]
    if len(bound) != len(verified):
        blockers.append("EXTERNAL_EVIDENCE_REVIEW_WORLD_MISMATCH")
    requirements, ratified = _lane_requirements(ratified_external_review_lanes)
    try:
        census = evaluate_external_review_census(
            records=[record for record in bound if record.source_class in ACCEPTED_EXTERNAL_SOURCE_CLASSES],
            requirements=requirements,
        )
    except ExternalEvidenceProvenanceError as exc:
        raise GenesisQualificationError(f"external review census invalid: {exc}") from exc
    counted = set(census.eligible_independent_evidence_ids)
    if not counted:
        blockers.append("MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE")
    if not ratified:
        blockers.append("GENESIS_LANE_CARDINALITY_UNRATIFIED")
    if not census.satisfied:
        blockers.append("EXTERNAL_REVIEW_CENSUS_INCOMPLETE")
    blockers.extend(
        f"QUALIFICATION_OBLIGATION_OPEN:{obligation}"
        for obligation in REQUIRED_QUALIFICATION_OBLIGATIONS if obligation not in closed
    )
    if survivors:
        blockers.append("SURVIVING_REQUIRED_MUTANT")

    ordered = sorted(verified, key=lambda record: record.evidence_id)
    # No qualified ACR classifies any residual UNKNOWN as non-mandatory, so every UNKNOWN blocks.
    unknowns.extend(
        f"UNKNOWN_INDEPENDENCE:{record.evidence_id}"
        for record in ordered if record.independence_state is IndependenceState.UNKNOWN_INDEPENDENCE
    )
    if unknowns:
        blockers.append("MANDATORY_UNKNOWN")
    dispositions = [
        {
            "evidence_id": record.evidence_id, "eepr_id": record.eepr_id, "source_class": record.source_class,
            "independence_state": record.independence_state.value,
            "provenance_authenticated": record.provenance_authenticated,
            "review_world_bound": record.review_world_id == review_world_id,
            "counted": record.evidence_id in counted,
        }
        for record in ordered
    ]

    qualified = not blockers
    state = "GENESIS_QUALIFICATION_PACKAGE_CANDIDATE" if qualified else "GENESIS_PROVISIONAL"
    obligation_ids = {
        obligation: sha256_id({
            "schema_version": "sergeant.sae150.genesis-obligation.v1", "review_world_id": review_world_id,
            "candidate_generation": generations["candidate_generation"], "obligation": obligation,
        })
        for obligation in REQUIRED_QUALIFICATION_OBLIGATIONS
    }
    package_body = {
        "schema_version": "sergeant.sae150.genesis-qualification-package-candidate.v2",
        "generation_bindings": generations,
        "review_world_id": review_world_id,
        "required_proven_nodes": dict(REQUIRED_PROVEN_NODE_BINDINGS),
        "proven_node_binding_kinds": dict(PROVEN_NODE_BINDING_KINDS),
        "qualification_obligations": dict(sorted(closed.items())),
        "external_evidence_dispositions": dispositions,
        "external_review_lane_requirement_ids": [requirement.requirement_id for requirement in requirements],
        "external_review_lane_cardinality_ratified": ratified,
        "external_review_census_id": census.census_id,
        "surviving_mutants": survivors,
        "residual_unknowns": unknowns,
        "limitations": limitations,
        "blockers": blockers,
        "state": state,
    }
    package_digest = sha256_id(package_body)
    genesis_package = GenesisQualificationPackage.create(
        review_world_id=review_world_id,
        required_qualification_ids=obligation_ids.values(),
        present_qualification_ids=[obligation_ids[obligation] for obligation in closed],
        external_review_census_id=census.census_id,
        external_review_census_satisfied=census.satisfied,
        founding_final_proof_id=None,
        generation=package_digest,
    )
    return {
        "qualified": qualified,
        "state": state,
        "blockers": blockers,
        "generation_bindings": generations,
        "generation_bindings_digest": sha256_id({**generations, "review_world_id": review_world_id}),
        "review_world_id": review_world_id,
        "required_nodes": list(REQUIRED_NODES),
        "mutation_families": list(REQUIRED_MUTATIONS),
        "qualification_obligations": dict(sorted(closed.items())),
        "external_evidence_count": len(verified),
        "external_evidence_dispositions": dispositions,
        "external_review_lane_cardinality_ratified": ratified,
        "external_review_census_id": census.census_id,
        "external_review_census_satisfied": census.satisfied,
        "surviving_mutants": survivors,
        "residual_unknowns": unknowns,
        "limitations": limitations,
        "genesis_package": genesis_package,
        "package_id": genesis_package.package_id,
        "package_digest": package_digest,
        "authority_gain": [],
        "normal_verdict_authority": False,
        "activation_authorized": False,
    }
