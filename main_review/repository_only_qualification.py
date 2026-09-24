"""SAE-160 repository-only qualification preparation.

This module is intentionally preparatory. It can determine whether the complete
SAE-160 evidence census is present and internally coherent, but it cannot freeze
or activate Genesis authority. SAE-150 remains an explicit prerequisite.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .review_world import (
    ReviewWorldError,
    require_full_sha256,
    require_git_object_id,
    sha256_id,
)

SAE150_COMPLETE_STATE = "GENESIS_QUALIFICATION_PACKAGE_CANDIDATE"
SAE160_READY = "READY_FOR_INDEPENDENT_QUALIFICATION"
SAE160_WAITING_SAE150 = "PREPARED_WAITING_SAE150"
SAE160_INCOMPLETE = "PREPARATION_INCOMPLETE"

REQUIRED_EVIDENCE_KINDS = (
    "clean_clone",
    "no_private_helper",
    "no_hidden_mutable_workspace_authority",
    "exact_package_install_path",
    "model_disabled",
    "cpu_operation",
    "rust_independence",
    "external_provenance",
    "complete_qualification_corpus",
    "exact_head_hostile_review",
    "no_unresolved_mandatory_threads",
)


class RepositoryOnlyQualificationError(ReviewWorldError):
    """Raised when SAE-160 preparation evidence is malformed."""


@dataclass(frozen=True)
class RepositoryOnlyEvidence:
    """One exact, content-addressed SAE-160 evidence item."""

    kind: str
    subject_generation: str
    basis_id: str
    passed: bool
    evidence_id: str

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        subject_generation: str,
        basis_id: str,
        passed: bool,
    ) -> "RepositoryOnlyEvidence":
        if kind not in REQUIRED_EVIDENCE_KINDS:
            raise RepositoryOnlyQualificationError(f"unknown SAE-160 evidence kind: {kind}")
        try:
            generation = require_git_object_id(subject_generation, "SAE-160 subject_generation")
            basis = require_full_sha256(basis_id, "SAE-160 basis_id")
        except (TypeError, ValueError, ReviewWorldError) as exc:
            raise RepositoryOnlyQualificationError(str(exc)) from exc
        if not isinstance(passed, bool):
            raise RepositoryOnlyQualificationError("passed must be boolean")
        body = {
            "schema_version": "sergeant.sae160.repository-only-evidence.v1",
            "kind": kind,
            "subject_generation": generation,
            "basis_id": basis,
            "passed": passed,
        }
        return cls(
            kind=kind,
            subject_generation=generation,
            basis_id=basis,
            passed=passed,
            evidence_id=sha256_id(body),
        )


@dataclass(frozen=True)
class RepositoryOnlyPreparation:
    """Fail-closed SAE-160 preparation result with no authority gain."""

    state: str
    subject_generation: str
    sae150_state: str
    sae150_package_id: str
    satisfied: tuple[str, ...]
    blockers: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    evidence_by_kind: tuple[tuple[str, str], ...]
    authority_gain: str
    preparation_id: str


def evaluate_repository_only_preparation(
    *,
    subject_generation: str,
    sae150_state: str,
    sae150_package_id: str,
    evidence: Iterable[RepositoryOnlyEvidence],
) -> RepositoryOnlyPreparation:
    """Evaluate exact-head SAE-160 readiness without freezing or activating authority."""
    try:
        generation = require_git_object_id(subject_generation, "subject_generation")
        package_id = require_full_sha256(sae150_package_id, "sae150_package_id")
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise RepositoryOnlyQualificationError(str(exc)) from exc

    if not isinstance(sae150_state, str) or not sae150_state.strip():
        raise RepositoryOnlyQualificationError("sae150_state must be a non-empty string")

    if isinstance(evidence, (str, bytes)):
        raise RepositoryOnlyQualificationError("evidence must be a non-string iterable")

    rows = tuple(evidence)
    if not all(isinstance(row, RepositoryOnlyEvidence) for row in rows):
        raise RepositoryOnlyQualificationError("evidence contains non-canonical SAE-160 records")

    by_kind: dict[str, RepositoryOnlyEvidence] = {}
    evidence_ids: set[str] = set()
    for row in rows:
        if row.subject_generation != generation:
            raise RepositoryOnlyQualificationError(
                "SAE-160 evidence subject_generation does not match exact candidate"
            )
        expected_id = sha256_id({
            "schema_version": "sergeant.sae160.repository-only-evidence.v1",
            "kind": row.kind,
            "subject_generation": row.subject_generation,
            "basis_id": row.basis_id,
            "passed": row.passed,
        })
        if row.evidence_id != expected_id:
            raise RepositoryOnlyQualificationError("SAE-160 evidence identity is non-canonical")
        if row.kind in by_kind:
            raise RepositoryOnlyQualificationError(f"duplicate SAE-160 evidence kind: {row.kind}")
        if row.evidence_id in evidence_ids:
            raise RepositoryOnlyQualificationError("duplicate SAE-160 evidence identity")
        by_kind[row.kind] = row
        evidence_ids.add(row.evidence_id)

    satisfied = tuple(
        kind for kind in REQUIRED_EVIDENCE_KINDS
        if kind in by_kind and by_kind[kind].passed
    )
    blockers = [
        kind for kind in REQUIRED_EVIDENCE_KINDS
        if kind not in by_kind or not by_kind[kind].passed
    ]

    if blockers:
        state = SAE160_INCOMPLETE
    elif sae150_state != SAE150_COMPLETE_STATE:
        state = SAE160_WAITING_SAE150
        blockers.append("sae150_prerequisite")
    else:
        state = SAE160_READY

    body = {
        "schema_version": "sergeant.sae160.repository-only-preparation.v1",
        "state": state,
        "subject_generation": generation,
        "sae150_state": sae150_state,
        "sae150_package_id": package_id,
        "satisfied": list(satisfied),
        "blockers": sorted(blockers),
        "evidence_ids": sorted(evidence_ids),
        "evidence_by_kind": [[kind, by_kind[kind].evidence_id] for kind in REQUIRED_EVIDENCE_KINDS if kind in by_kind],
        "authority_gain": "NONE",
    }
    return RepositoryOnlyPreparation(
        state=state,
        subject_generation=generation,
        sae150_state=sae150_state,
        sae150_package_id=package_id,
        satisfied=satisfied,
        blockers=tuple(sorted(blockers)),
        evidence_ids=tuple(sorted(evidence_ids)),
        evidence_by_kind=tuple((kind, by_kind[kind].evidence_id) for kind in REQUIRED_EVIDENCE_KINDS if kind in by_kind),
        authority_gain="NONE",
        preparation_id=sha256_id(body),
    )
