"""SAE-30 External Evidence Provenance Record and independent-review census.

Control-lineage claims become positive independence authority only after a
trusted provenance verifier authenticates the exact evidence/source/lineage
record. Unauthenticated or unverifiable provenance conserves
UNKNOWN_INDEPENDENCE.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import hmac
from typing import Iterable

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class ExternalEvidenceProvenanceError(ReviewWorldError):
    """Raised when external-evidence provenance is incomplete or non-canonical."""


class IndependenceState(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    NOT_INDEPENDENT = "NOT_INDEPENDENT"
    UNKNOWN_INDEPENDENCE = "UNKNOWN_INDEPENDENCE"


class ProvenanceVerifierState(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExternalEvidenceProvenanceError(f"{field} must be canonical and non-empty")
    return value


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise ExternalEvidenceProvenanceError(str(exc)) from exc


def _optional_bool(value: object, field: str) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ExternalEvidenceProvenanceError(f"{field} must be true, false, or unknown")


def _secret_digest(secret: bytes) -> str:
    if not isinstance(secret, bytes) or len(secret) < 16:
        raise ExternalEvidenceProvenanceError("provenance verifier secret must contain at least 16 bytes")
    return hashlib.sha256(secret).hexdigest()


@dataclass(frozen=True)
class ControlLineageFacts:
    source_separate: bool | None
    authoring_separate: bool | None
    corpus_separate: bool | None
    infrastructure_separate: bool | None
    prompt_control_separate: bool | None
    input_selection_separate: bool | None
    finding_selection_separate: bool | None

    @classmethod
    def create(
        cls,
        *,
        source_separate: bool | None,
        authoring_separate: bool | None,
        corpus_separate: bool | None,
        infrastructure_separate: bool | None,
        prompt_control_separate: bool | None,
        input_selection_separate: bool | None,
        finding_selection_separate: bool | None,
    ) -> "ControlLineageFacts":
        return cls(*(
            _optional_bool(value, name)
            for name, value in (
                ("source_separate", source_separate),
                ("authoring_separate", authoring_separate),
                ("corpus_separate", corpus_separate),
                ("infrastructure_separate", infrastructure_separate),
                ("prompt_control_separate", prompt_control_separate),
                ("input_selection_separate", input_selection_separate),
                ("finding_selection_separate", finding_selection_separate),
            )
        ))

    def to_payload(self) -> dict[str, bool | None]:
        return {
            "source_separate": self.source_separate,
            "authoring_separate": self.authoring_separate,
            "corpus_separate": self.corpus_separate,
            "infrastructure_separate": self.infrastructure_separate,
            "prompt_control_separate": self.prompt_control_separate,
            "input_selection_separate": self.input_selection_separate,
            "finding_selection_separate": self.finding_selection_separate,
        }

    @property
    def lineage_id(self) -> str:
        return sha256_id({"schema_version": "sergeant.control-lineage-facts.v1", **self.to_payload()})

    def derived_independence(self) -> IndependenceState:
        values = tuple(self.to_payload().values())
        if any(value is False for value in values):
            return IndependenceState.NOT_INDEPENDENT
        if all(value is True for value in values):
            return IndependenceState.INDEPENDENT
        return IndependenceState.UNKNOWN_INDEPENDENCE


@dataclass(frozen=True)
class ProvenanceVerifierAuthorization:
    schema_version: str
    verifier_identity: str
    verifier_generation: str
    key_id: str
    verification_secret_digest: str
    state: ProvenanceVerifierState
    authorization_id: str

    @classmethod
    def create(
        cls,
        *,
        verifier_identity: str,
        verifier_generation: str,
        key_id: str,
        verification_secret_digest: str,
        state: ProvenanceVerifierState,
    ) -> "ProvenanceVerifierAuthorization":
        if not isinstance(state, ProvenanceVerifierState):
            raise ExternalEvidenceProvenanceError("provenance verifier state is invalid")
        identity = _string(verifier_identity, "provenance verifier identity")
        generation = _string(verifier_generation, "provenance verifier generation")
        key = _sha(key_id, "provenance verifier key id")
        digest = _sha(verification_secret_digest, "provenance verification secret digest")
        body = {
            "schema_version": "sergeant.provenance-verifier-authorization.v1",
            "verifier_identity": identity,
            "verifier_generation": generation,
            "key_id": key,
            "verification_secret_digest": digest,
            "state": state.value,
        }
        return cls(body["schema_version"], identity, generation, key, digest, state, sha256_id(body))


@dataclass(frozen=True)
class AuthenticatedProvenanceProof:
    schema_version: str
    evidence_id: str
    source_principal_id: str
    source_authority_generation: str
    lineage_id: str
    verifier_identity: str
    verifier_generation: str
    mac: str

    @classmethod
    def issue(
        cls,
        *,
        evidence_id: str,
        source_principal_id: str,
        source_authority_generation: str,
        lineage_facts: ControlLineageFacts,
        verifier_identity: str,
        verifier_generation: str,
        verification_secret: bytes,
    ) -> "AuthenticatedProvenanceProof":
        evidence = _sha(evidence_id, "authenticated provenance evidence id")
        principal = _string(source_principal_id, "authenticated provenance source principal")
        generation = _string(source_authority_generation, "authenticated provenance source generation")
        if not isinstance(lineage_facts, ControlLineageFacts):
            raise ExternalEvidenceProvenanceError("canonical control-lineage facts are required")
        verifier = _string(verifier_identity, "provenance verifier identity")
        verifier_generation = _string(verifier_generation, "provenance verifier generation")
        _secret_digest(verification_secret)
        payload = "\0".join((evidence, principal, generation, lineage_facts.lineage_id, verifier, verifier_generation)).encode()
        mac = hmac.new(verification_secret, payload, hashlib.sha256).hexdigest()
        return cls(
            "sergeant.authenticated-provenance-proof.v1", evidence, principal, generation,
            lineage_facts.lineage_id, verifier, verifier_generation, mac,
        )


def _provenance_authenticated(
    *,
    authorization: ProvenanceVerifierAuthorization | None,
    proof: AuthenticatedProvenanceProof | None,
    verification_secret: bytes | None,
    evidence_id: str,
    source_principal_id: str,
    source_authority_generation: str,
    lineage_facts: ControlLineageFacts,
) -> bool:
    if not isinstance(authorization, ProvenanceVerifierAuthorization) or not isinstance(proof, AuthenticatedProvenanceProof):
        return False
    if authorization.state is not ProvenanceVerifierState.ACTIVE or verification_secret is None:
        return False
    try:
        if _secret_digest(verification_secret) != authorization.verification_secret_digest:
            return False
    except ExternalEvidenceProvenanceError:
        return False
    if (
        proof.evidence_id != evidence_id
        or proof.source_principal_id != source_principal_id
        or proof.source_authority_generation != source_authority_generation
        or proof.lineage_id != lineage_facts.lineage_id
        or proof.verifier_identity != authorization.verifier_identity
        or proof.verifier_generation != authorization.verifier_generation
    ):
        return False
    payload = "\0".join((
        proof.evidence_id, proof.source_principal_id, proof.source_authority_generation,
        proof.lineage_id, proof.verifier_identity, proof.verifier_generation,
    )).encode()
    expected = hmac.new(verification_secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, proof.mac)


@dataclass(frozen=True)
class ExternalEvidenceProvenanceRecord:
    schema_version: str
    evidence_id: str
    evidence_digest: str
    review_world_id: str
    source_principal_id: str
    authenticated_source_provenance: str
    source_organization: str
    source_class: str
    source_authority_generation: str
    creation_generation: str
    candidate_authoring_relationship: str
    qualification_corpus_relationship: str
    candidate_infrastructure_relationship: str
    reviewer_tool_lineage: str
    prompt_controller: str
    input_selector: str
    finding_selector: str
    provenance_verification_method: str
    control_lineage_facts: ControlLineageFacts
    provenance_authenticated: bool
    provenance_verifier_authorization_id: str | None
    independence_state: IndependenceState
    eepr_id: str

    @classmethod
    def create(
        cls,
        *,
        evidence_id: str,
        evidence_digest: str,
        review_world_id: str,
        source_principal_id: str,
        authenticated_source_provenance: str,
        source_organization: str,
        source_class: str,
        source_authority_generation: str,
        creation_generation: str,
        candidate_authoring_relationship: str,
        qualification_corpus_relationship: str,
        candidate_infrastructure_relationship: str,
        reviewer_tool_lineage: str,
        prompt_controller: str,
        input_selector: str,
        finding_selector: str,
        provenance_verification_method: str,
        control_lineage_facts: ControlLineageFacts,
        provenance_authorization: ProvenanceVerifierAuthorization | None = None,
        authenticated_provenance_proof: AuthenticatedProvenanceProof | None = None,
        provenance_verification_secret: bytes | None = None,
    ) -> "ExternalEvidenceProvenanceRecord":
        if not isinstance(control_lineage_facts, ControlLineageFacts):
            raise ExternalEvidenceProvenanceError("control lineage facts are required")
        values = {
            "evidence_id": _sha(evidence_id, "evidence_id"),
            "evidence_digest": _sha(evidence_digest, "evidence_digest"),
            "review_world_id": _sha(review_world_id, "review_world_id"),
            "source_principal_id": _string(source_principal_id, "source_principal_id"),
            "authenticated_source_provenance": _string(authenticated_source_provenance, "authenticated source provenance"),
            "source_organization": _string(source_organization, "source organization"),
            "source_class": _string(source_class, "source class"),
            "source_authority_generation": _string(source_authority_generation, "source authority generation"),
            "creation_generation": _string(creation_generation, "creation generation"),
            "candidate_authoring_relationship": _string(candidate_authoring_relationship, "candidate authoring relationship"),
            "qualification_corpus_relationship": _string(qualification_corpus_relationship, "qualification corpus relationship"),
            "candidate_infrastructure_relationship": _string(candidate_infrastructure_relationship, "candidate infrastructure relationship"),
            "reviewer_tool_lineage": _string(reviewer_tool_lineage, "reviewer/tool/model lineage"),
            "prompt_controller": _string(prompt_controller, "prompt controller"),
            "input_selector": _string(input_selector, "input selector"),
            "finding_selector": _string(finding_selector, "finding selector"),
            "provenance_verification_method": _string(provenance_verification_method, "provenance verification method"),
        }
        authenticated = _provenance_authenticated(
            authorization=provenance_authorization,
            proof=authenticated_provenance_proof,
            verification_secret=provenance_verification_secret,
            evidence_id=values["evidence_id"],
            source_principal_id=values["source_principal_id"],
            source_authority_generation=values["source_authority_generation"],
            lineage_facts=control_lineage_facts,
        )
        independence = control_lineage_facts.derived_independence() if authenticated else IndependenceState.UNKNOWN_INDEPENDENCE
        verifier_id = provenance_authorization.authorization_id if authenticated and provenance_authorization is not None else None
        body = {
            "schema_version": "sergeant.external-evidence-provenance.v2",
            **values,
            "control_lineage_id": control_lineage_facts.lineage_id,
            "provenance_authenticated": authenticated,
            "provenance_verifier_authorization_id": verifier_id,
            "independence_state": independence.value,
        }
        return cls(
            body["schema_version"], values["evidence_id"], values["evidence_digest"], values["review_world_id"],
            values["source_principal_id"], values["authenticated_source_provenance"], values["source_organization"],
            values["source_class"], values["source_authority_generation"], values["creation_generation"],
            values["candidate_authoring_relationship"], values["qualification_corpus_relationship"],
            values["candidate_infrastructure_relationship"], values["reviewer_tool_lineage"], values["prompt_controller"],
            values["input_selector"], values["finding_selector"], values["provenance_verification_method"],
            control_lineage_facts, authenticated, verifier_id, independence, sha256_id(body),
        )


@dataclass(frozen=True)
class ExternalReviewLaneRequirement:
    lane_id: str
    minimum_instances: int
    minimum_source_classes: int
    requirement_id: str

    @classmethod
    def create(cls, *, lane_id: str, minimum_instances: int, minimum_source_classes: int) -> "ExternalReviewLaneRequirement":
        lane = _string(lane_id, "lane_id")
        for name, value in (("minimum_instances", minimum_instances), ("minimum_source_classes", minimum_source_classes)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ExternalEvidenceProvenanceError(f"{name} must be a positive integer")
        if minimum_source_classes > minimum_instances:
            raise ExternalEvidenceProvenanceError("minimum source classes cannot exceed minimum instances")
        body = {
            "schema_version": "sergeant.external-review-lane-requirement.v1",
            "lane_id": lane,
            "minimum_instances": minimum_instances,
            "minimum_source_classes": minimum_source_classes,
        }
        return cls(lane, minimum_instances, minimum_source_classes, sha256_id(body))


@dataclass(frozen=True)
class ExternalReviewLaneCensus:
    lane_id: str
    independent_instances: int
    source_classes: tuple[str, ...]
    satisfied: bool


@dataclass(frozen=True)
class ExternalReviewCensus:
    schema_version: str
    evidence_ids: tuple[str, ...]
    eligible_independent_evidence_ids: tuple[str, ...]
    lanes: tuple[ExternalReviewLaneCensus, ...]
    satisfied: bool
    census_id: str


def evaluate_external_review_census(
    *, records: Iterable[ExternalEvidenceProvenanceRecord], requirements: Iterable[ExternalReviewLaneRequirement],
) -> ExternalReviewCensus:
    if isinstance(records, (str, bytes)) or isinstance(requirements, (str, bytes)):
        raise ExternalEvidenceProvenanceError("records and requirements must be non-string iterables")
    records = tuple(records)
    requirements = tuple(requirements)
    if not requirements:
        raise ExternalEvidenceProvenanceError("at least one external-review lane requirement is required")
    for record in records:
        if not isinstance(record, ExternalEvidenceProvenanceRecord):
            raise ExternalEvidenceProvenanceError("external review census contains invalid EEPR")
    for requirement in requirements:
        if not isinstance(requirement, ExternalReviewLaneRequirement):
            raise ExternalEvidenceProvenanceError("external review census contains invalid lane requirement")
    ids = tuple(sorted(record.evidence_id for record in records))
    if len(set(ids)) != len(ids):
        raise ExternalEvidenceProvenanceError("external evidence census contains duplicate evidence identity")
    independent = tuple(
        record for record in records
        if record.provenance_authenticated and record.independence_state is IndependenceState.INDEPENDENT
    )
    eligible_ids = tuple(sorted(record.evidence_id for record in independent))
    classes = tuple(sorted({record.source_class for record in independent}))
    lanes = tuple(
        ExternalReviewLaneCensus(
            requirement.lane_id, len(independent), classes,
            len(independent) >= requirement.minimum_instances and len(classes) >= requirement.minimum_source_classes,
        )
        for requirement in sorted(requirements, key=lambda item: item.lane_id)
    )
    satisfied = all(lane.satisfied for lane in lanes)
    body = {
        "schema_version": "sergeant.external-review-census.v2",
        "evidence_ids": list(ids), "eligible_independent_evidence_ids": list(eligible_ids),
        "lanes": [
            {"lane_id": lane.lane_id, "independent_instances": lane.independent_instances,
             "source_classes": list(lane.source_classes), "satisfied": lane.satisfied}
            for lane in lanes
        ],
        "satisfied": satisfied,
    }
    return ExternalReviewCensus(body["schema_version"], ids, eligible_ids, lanes, satisfied, sha256_id(body))
