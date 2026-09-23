from __future__ import annotations

import pytest

from main_review.repository_only_qualification import (
    REQUIRED_EVIDENCE_KINDS,
    SAE150_COMPLETE_STATE,
    SAE160_INCOMPLETE,
    SAE160_READY,
    SAE160_WAITING_SAE150,
    RepositoryOnlyEvidence,
    RepositoryOnlyQualificationError,
    evaluate_repository_only_preparation,
)


def evidence(kind: str, *, passed: bool = True, byte: int = 1) -> RepositoryOnlyEvidence:
    return RepositoryOnlyEvidence.create(
        kind=kind,
        evidence_id=(f"{byte:02x}" * 32),
        passed=passed,
    )


def complete_evidence() -> list[RepositoryOnlyEvidence]:
    return [
        evidence(kind, byte=index + 1)
        for index, kind in enumerate(REQUIRED_EVIDENCE_KINDS)
    ]


def test_complete_repository_only_census_still_waits_while_sae150_is_provisional():
    result = evaluate_repository_only_preparation(
        sae150_state="GENESIS_PROVISIONAL",
        sae150_package_id="aa" * 32,
        evidence=complete_evidence(),
    )

    assert result.state == SAE160_WAITING_SAE150
    assert result.blockers == ("sae150_prerequisite",)
    assert len(result.satisfied) == len(REQUIRED_EVIDENCE_KINDS)


def test_complete_census_can_be_ready_only_after_exact_sae150_prerequisite():
    result = evaluate_repository_only_preparation(
        sae150_state=SAE150_COMPLETE_STATE,
        sae150_package_id="aa" * 32,
        evidence=complete_evidence(),
    )

    assert result.state == SAE160_READY
    assert result.blockers == ()


def test_missing_or_failed_repository_only_evidence_fails_closed():
    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)
    rows.pop()

    result = evaluate_repository_only_preparation(
        sae150_state=SAE150_COMPLETE_STATE,
        sae150_package_id="aa" * 32,
        evidence=rows,
    )

    assert result.state == SAE160_INCOMPLETE
    assert REQUIRED_EVIDENCE_KINDS[0] in result.blockers
    assert REQUIRED_EVIDENCE_KINDS[-1] in result.blockers


def test_duplicate_evidence_kind_is_rejected():
    rows = complete_evidence()
    rows.append(evidence(REQUIRED_EVIDENCE_KINDS[0], byte=99))

    with pytest.raises(RepositoryOnlyQualificationError, match="duplicate SAE-160 evidence kind"):
        evaluate_repository_only_preparation(
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=rows,
        )


def test_duplicate_evidence_identity_is_rejected():
    rows = complete_evidence()
    rows[1] = RepositoryOnlyEvidence.create(
        kind=REQUIRED_EVIDENCE_KINDS[1],
        evidence_id=rows[0].evidence_id,
        passed=True,
    )

    with pytest.raises(RepositoryOnlyQualificationError, match="duplicate SAE-160 evidence identity"):
        evaluate_repository_only_preparation(
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=rows,
        )


def test_unknown_kind_and_noncanonical_digest_are_rejected():
    with pytest.raises(RepositoryOnlyQualificationError, match="unknown SAE-160 evidence kind"):
        RepositoryOnlyEvidence.create(kind="owner_says_ok", evidence_id="aa" * 32, passed=True)

    with pytest.raises(RepositoryOnlyQualificationError):
        RepositoryOnlyEvidence.create(
            kind=REQUIRED_EVIDENCE_KINDS[0],
            evidence_id="not-a-digest",
            passed=True,
        )


def test_preparation_id_is_deterministic_for_same_evidence_set():
    left = evaluate_repository_only_preparation(
        sae150_state="GENESIS_PROVISIONAL",
        sae150_package_id="aa" * 32,
        evidence=complete_evidence(),
    )
    right = evaluate_repository_only_preparation(
        sae150_state="GENESIS_PROVISIONAL",
        sae150_package_id="aa" * 32,
        evidence=reversed(complete_evidence()),
    )

    assert left.preparation_id == right.preparation_id
