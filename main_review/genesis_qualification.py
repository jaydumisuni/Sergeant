"""Fail-closed SAE-150 integrated Genesis qualification package assembly."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .external_evidence_provenance import (
    ExternalEvidenceProvenanceError,
    ExternalEvidenceProvenanceRecord,
    ExternalReviewLaneRequirement,
    IndependenceState,
    evaluate_external_review_census,
    sha256_id,
)

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
REQUIRED_NODES = tuple(REQUIRED_PROVEN_NODE_BINDINGS)
REQUIRED_MUTATIONS = ("omission", "undercount", "cardinality", "acr", "material_input", "falsifier", "authority", "common_mode")
REQUIRED_BOOLEAN_PROOFS = ("preservation_proof", "model_blackout_proof", "cpu_proof", "historical_replay", "clean_controls", "unrelated_transfer", "eepr_complete")
GENESIS_EXTERNAL_REVIEW_REQUIREMENTS = (
    ExternalReviewLaneRequirement.create(
        lane_id="genesis-independent", minimum_instances=1, minimum_source_classes=1
    ),
)
GENERATION_FIELDS = ("candidate_generation", "rab_generation", "acr_generation", "rust_generation")


class GenesisQualificationError(ValueError):
    """Raised when mandatory Genesis package structure is absent or malformed."""


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


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


def _generation(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GenesisQualificationError(f"{field} must be a non-empty canonical generation identifier")
    return value.strip()


def _review_world(value: object) -> str:
    if not isinstance(value, str):
        raise GenesisQualificationError("review_world_id must be a canonical sha256 identity")
    text = value.strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise GenesisQualificationError("review_world_id must be a canonical sha256 identity")
    return text


def _independent_lane(records: Sequence[ExternalEvidenceProvenanceRecord], *, review_world_id: str) -> bool:
    for record in records:
        if not isinstance(record, ExternalEvidenceProvenanceRecord):
            raise GenesisQualificationError("external_evidence must contain canonical ExternalEvidenceProvenanceRecord values")
        if (
            record.review_world_id == review_world_id
            and record.provenance_authenticated
            and record.provenance_verifier_authorization_id is not None
            and record.independence_state is IndependenceState.INDEPENDENT
            and _text(record.evidence_id)
            and _text(record.evidence_digest)
        ):
            return True
    return False


def qualify_genesis_package(package: Mapping[str, Any]) -> dict[str, Any]:
    row = _require_mapping(package, "package")
    generations = {field: _generation(row.get(field), field) for field in GENERATION_FIELDS}
    review_world_id = _review_world(row.get("review_world_id"))

    nodes = _require_mapping(row.get("required_proven_nodes"), "required_proven_nodes")
    if nodes != REQUIRED_PROVEN_NODE_BINDINGS:
        raise GenesisQualificationError("canonical SAE-150 prerequisite generations must match the frozen manifest exactly")

    for field in REQUIRED_BOOLEAN_PROOFS:
        if row.get(field) is not True:
            raise GenesisQualificationError(f"{field} is required")

    mutations = _require_mapping(row.get("mutation_families"), "mutation_families")
    if set(mutations) != set(REQUIRED_MUTATIONS) or any(mutations.get(name) is not True for name in REQUIRED_MUTATIONS):
        raise GenesisQualificationError("all required mutation families must survive qualification")

    evidence_values = _require_sequence(row.get("external_evidence"), "external_evidence")
    evidence: list[ExternalEvidenceProvenanceRecord] = []
    for value in evidence_values:
        if not isinstance(value, ExternalEvidenceProvenanceRecord):
            raise GenesisQualificationError("external_evidence must contain canonical ExternalEvidenceProvenanceRecord values")
        evidence.append(value)

    blockers: list[str] = []
    bound_evidence = [record for record in evidence if record.review_world_id == review_world_id]
    if len(bound_evidence) != len(evidence):
        blockers.append("EXTERNAL_EVIDENCE_REVIEW_WORLD_MISMATCH")
    if not _independent_lane(bound_evidence, review_world_id=review_world_id):
        blockers.append("MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE")
    try:
        census = evaluate_external_review_census(
            records=bound_evidence, requirements=GENESIS_EXTERNAL_REVIEW_REQUIREMENTS
        )
    except ExternalEvidenceProvenanceError as exc:
        raise GenesisQualificationError(f"external review census invalid: {exc}") from exc
    if not census.satisfied:
        blockers.append("EXTERNAL_REVIEW_CENSUS_INCOMPLETE")

    unknown_values = _require_sequence(row.get("residual_unknowns"), "residual_unknowns")
    if any(not isinstance(value, str) for value in unknown_values):
        raise GenesisQualificationError("residual_unknowns must contain strings")
    unknowns = [_text(value) for value in unknown_values if _text(value)]
    if any(value.lower().startswith("mandatory:") for value in unknowns):
        blockers.append("MANDATORY_UNKNOWN")

    qualified = not blockers
    generation_binding = {**generations, "review_world_id": review_world_id}
    return {
        "qualified": qualified,
        "state": "GENESIS_QUALIFICATION_PACKAGE_CANDIDATE" if qualified else "GENESIS_PROVISIONAL",
        "blockers": blockers,
        "generation_bindings": generations,
        "generation_bindings_digest": sha256_id(generation_binding),
        "review_world_id": review_world_id,
        "required_nodes": list(REQUIRED_NODES),
        "mutation_families": list(REQUIRED_MUTATIONS),
        "external_evidence_count": len(evidence),
        "external_review_census_id": census.census_id,
        "external_review_census_satisfied": census.satisfied,
        "residual_unknowns": unknowns,
        "authority_gain": [],
        "normal_verdict_authority": False,
        "activation_authorized": False,
    }
