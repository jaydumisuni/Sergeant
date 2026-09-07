"""SAE-30 External Evidence Provenance Record and independence census.

Independence is derived from explicit control-lineage facts. Surface variation,
content hashes, model identity, or a self-declared label can never manufacture
an independent qualification lane.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class ExternalEvidenceProvenanceError(ReviewWorldError):
    """Raised when external-evidence provenance is incomplete or non-canonical."""


class IndependenceState(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    NOT_INDEPENDENT = "NOT_INDEPENDENT"
    UNKNOWN_INDEPENDENCE = "UNKNOWN_INDEPENDENCE"


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

    def independence_state(self) -> IndependenceState:
        values = tuple(self.to_payload().values())
        if any(value is False for value in values):
            return IndependenceState.NOT_INDEPENDENT
        if all(value is True for value in values):
            return IndependenceState.INDEPENDENT
        return IndependenceState.UNKNOWN_INDEPENDENCE


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
    ) -> "ExternalEvidenceProvenanceRecord":
        if not isinstance(control_lineage_facts, ControlLineageFacts):
            raise ExternalEvidenceProvenanceError("control lineage facts are required")
        independence = control_lineage_facts.independence_state()
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
        body = {
            "schema_version": "sergeant.external-evidence-provenance.v1",
            **values,
            "control_lineage_facts": control_lineage_facts.to_payload(),
            "independence_state": independence.value,
        }
        return cls(
            "sergeant.external-evidence-provenance.v1",
            values["evidence_id"], values["evidence_digest"], values["review_world_id"],
            values["source_principal_id"], values["authenticated_source_provenance"],
            values["source_organization"], values["source_class"], values["source_authority_generation"],
            values["creation_generation"], values["candidate_authoring_relationship"],
            values["qualification_corpus_relationship"], values["candidate_infrastructure_relationship"],
            values["reviewer_tool_lineage"], values["prompt_controller"], values["input_selector"],
            values["finding_selector"], values["provenance_verification_method"], control_lineage_facts,
            independence, sha256_id(body),
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
    lanes: tuple[ExternalReviewLaneCensus, ...]
    satisfied: bool
    census_id: str


def evaluate_external_review_census(
    *,
    records: Iterable[ExternalEvidenceProvenanceRecord],
    requirements: Iterable[ExternalReviewLaneRequirement],
) -> ExternalReviewCensus:
    if isinstance(records, (str, bytes)) or isinstance(requirements, (str, bytes)):
        raise ExternalEvidenceProvenanceError("records and requirements must be non-string iterables")
    records = tuple(records)
    requirements = tuple(requirements)
    for record in records:
        if not isinstance(record, ExternalEvidenceProvenanceRecord):
            raise ExternalEvidenceProvenanceError("external review census contains invalid EEPR")
    for requirement in requirements:
        if not isinstance(requirement, ExternalReviewLaneRequirement):
            raise ExternalEvidenceProvenanceError("external review census contains invalid lane requirement")
    ids = tuple(sorted(record.evidence_id for record in records))
    if len(set(ids)) != len(ids):
        raise ExternalEvidenceProvenanceError("external evidence census contains duplicate evidence identity")
    independent = tuple(record for record in records if record.independence_state is IndependenceState.INDEPENDENT)
    classes = tuple(sorted({record.source_class for record in independent}))
    lanes = tuple(
        ExternalReviewLaneCensus(
            requirement.lane_id,
            len(independent),
            classes,
            len(independent) >= requirement.minimum_instances and len(classes) >= requirement.minimum_source_classes,
        )
        for requirement in sorted(requirements, key=lambda item: item.lane_id)
    )
    satisfied = bool(lanes) and all(lane.satisfied for lane in lanes)
    body = {
        "schema_version": "sergeant.external-review-census.v1",
        "evidence_ids": list(ids),
        "lanes": [
            {
                "lane_id": lane.lane_id,
                "independent_instances": lane.independent_instances,
                "source_classes": list(lane.source_classes),
                "satisfied": lane.satisfied,
            }
            for lane in lanes
        ],
        "satisfied": satisfied,
    }
    return ExternalReviewCensus(
        "sergeant.external-review-census.v1", ids, lanes, satisfied, sha256_id(body)
    )
