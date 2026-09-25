from __future__ import annotations

from dataclasses import replace

import pytest

from main_review.review_world import sha256_id

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

HEAD = "a" * 40


def evidence(
    kind: str,
    *,
    passed: bool = True,
    byte: int = 1,
    subject_generation: str = HEAD,
) -> RepositoryOnlyEvidence:
    return RepositoryOnlyEvidence.create(
        kind=kind,
        subject_generation=subject_generation,
        basis_id=(f"{byte:02x}" * 32),
        passed=passed,
    )


def complete_evidence(subject_generation: str = HEAD) -> list[RepositoryOnlyEvidence]:
    return [
        evidence(kind, byte=index + 1, subject_generation=subject_generation)
        for index, kind in enumerate(REQUIRED_EVIDENCE_KINDS)
    ]


def evaluate(rows, *, state="GENESIS_PROVISIONAL", subject_generation=HEAD):
    return evaluate_repository_only_preparation(
        subject_generation=subject_generation,
        sae150_state=state,
        sae150_package_id="aa" * 32,
        evidence=rows,
    )


def test_complete_repository_only_census_still_waits_while_sae150_is_provisional():
    result = evaluate(complete_evidence())

    assert result.state == SAE160_WAITING_SAE150
    assert result.subject_generation == HEAD
    assert result.sae150_state == "GENESIS_PROVISIONAL"
    assert result.sae150_package_id == "aa" * 32
    assert result.blockers == ("sae150_prerequisite",)
    assert len(result.satisfied) == len(REQUIRED_EVIDENCE_KINDS)
    assert result.authority_gain == "NONE"


def test_complete_census_can_be_ready_only_after_exact_sae150_prerequisite():
    result = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_READY
    assert result.blockers == ()
    assert result.authority_gain == "NONE"


def test_missing_or_failed_repository_only_evidence_fails_closed():
    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)
    rows.pop()

    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_INCOMPLETE
    assert REQUIRED_EVIDENCE_KINDS[0] in result.blockers
    assert REQUIRED_EVIDENCE_KINDS[-1] in result.blockers


def test_duplicate_evidence_kind_is_rejected():
    rows = complete_evidence()
    rows.append(evidence(REQUIRED_EVIDENCE_KINDS[0], byte=99))

    with pytest.raises(RepositoryOnlyQualificationError, match="duplicate SAE-160 evidence kind"):
        evaluate(rows, state=SAE150_COMPLETE_STATE)


def test_duplicate_evidence_identity_is_rejected():
    rows = complete_evidence()
    rows[1] = replace(
        rows[1],
        evidence_id=rows[0].evidence_id,
    )

    with pytest.raises(RepositoryOnlyQualificationError, match="identity"):
        evaluate(rows, state=SAE150_COMPLETE_STATE)


def test_unknown_kind_and_noncanonical_basis_are_rejected():
    with pytest.raises(RepositoryOnlyQualificationError, match="unknown SAE-160 evidence kind"):
        RepositoryOnlyEvidence.create(
            kind="owner_says_ok",
            subject_generation=HEAD,
            basis_id="aa" * 32,
            passed=True,
        )

    with pytest.raises(RepositoryOnlyQualificationError):
        RepositoryOnlyEvidence.create(
            kind=REQUIRED_EVIDENCE_KINDS[0],
            subject_generation=HEAD,
            basis_id="not-a-digest",
            passed=True,
        )


def test_evidence_identity_binds_kind_subject_basis_and_result():
    base = evidence(REQUIRED_EVIDENCE_KINDS[0], byte=1)
    changed_head = evidence(
        REQUIRED_EVIDENCE_KINDS[0],
        byte=1,
        subject_generation="b" * 40,
    )
    changed_basis = evidence(REQUIRED_EVIDENCE_KINDS[0], byte=2)
    changed_result = evidence(REQUIRED_EVIDENCE_KINDS[0], byte=1, passed=False)

    assert len({
        base.evidence_id,
        changed_head.evidence_id,
        changed_basis.evidence_id,
        changed_result.evidence_id,
    }) == 4


def test_mixed_generation_evidence_is_rejected_before_readiness():
    rows = complete_evidence()
    rows[0] = evidence(
        REQUIRED_EVIDENCE_KINDS[0],
        byte=1,
        subject_generation="b" * 40,
    )

    with pytest.raises(RepositoryOnlyQualificationError, match="exact candidate"):
        evaluate(rows, state=SAE150_COMPLETE_STATE)


def test_noncanonical_mutated_evidence_identity_is_rejected():
    rows = complete_evidence()
    rows[0] = replace(rows[0], passed=False)

    with pytest.raises(RepositoryOnlyQualificationError, match="non-canonical"):
        evaluate(rows, state=SAE150_COMPLETE_STATE)


def test_preparation_id_is_deterministic_for_same_evidence_set():
    left = evaluate(complete_evidence())
    right = evaluate(reversed(complete_evidence()))

    assert left.preparation_id == right.preparation_id


def test_preparation_identity_changes_with_sae150_dependency_identity():
    left = evaluate_repository_only_preparation(
        subject_generation=HEAD,
        sae150_state="GENESIS_PROVISIONAL",
        sae150_package_id="aa" * 32,
        evidence=complete_evidence(),
    )
    right = evaluate_repository_only_preparation(
        subject_generation=HEAD,
        sae150_state="GENESIS_PROVISIONAL",
        sae150_package_id="bb" * 32,
        evidence=complete_evidence(),
    )

    assert left.sae150_package_id != right.sae150_package_id
    assert left.preparation_id != right.preparation_id


def test_preparation_identity_changes_with_exact_candidate_head():
    left = evaluate(complete_evidence("a" * 40), subject_generation="a" * 40)
    right = evaluate(complete_evidence("b" * 40), subject_generation="b" * 40)

    assert left.preparation_id != right.preparation_id


def test_preparation_exposes_canonical_evidence_map_for_collectors():
    result = evaluate(complete_evidence())

    assert tuple(kind for kind, _ in result.evidence_by_kind) == REQUIRED_EVIDENCE_KINDS
    assert dict(result.evidence_by_kind)[REQUIRED_EVIDENCE_KINDS[0]] == complete_evidence()[0].evidence_id
    assert len({evidence_id for _, evidence_id in result.evidence_by_kind}) == len(REQUIRED_EVIDENCE_KINDS)


def test_sae150_state_is_canonicalized_before_identity_and_readiness():
    canonical = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)
    padded = evaluate(complete_evidence(), state=f"  {SAE150_COMPLETE_STATE}  ")

    assert padded.state == SAE160_READY
    assert padded.sae150_state == SAE150_COMPLETE_STATE
    assert padded.preparation_id == canonical.preparation_id


def test_sae150_state_must_be_a_non_empty_string():
    for invalid in (None, 0, False, "", "   "):
        with pytest.raises(RepositoryOnlyQualificationError, match="sae150_state"):
            evaluate_repository_only_preparation(
                subject_generation=HEAD,
                sae150_state=invalid,
                sae150_package_id="aa" * 32,
                evidence=complete_evidence(),
            )


def test_evaluator_rejects_non_iterable_evidence_through_domain_boundary():
    for invalid in (None, 0, False, object()):
        with pytest.raises(RepositoryOnlyQualificationError, match="evidence must be an iterable"):
            evaluate_repository_only_preparation(
                subject_generation=HEAD,
                sae150_state=SAE150_COMPLETE_STATE,
                sae150_package_id="aa" * 32,
                evidence=invalid,
            )


def test_evaluator_rejects_forged_noncanonical_evidence_fields():
    generation = "a" * 40
    valid = RepositoryOnlyEvidence.create(
        kind=REQUIRED_EVIDENCE_KINDS[0],
        subject_generation=generation,
        basis_id="b" * 64,
        passed=True,
    )

    forged_kind = RepositoryOnlyEvidence(
        kind="not_a_canonical_kind",
        subject_generation=generation,
        basis_id=valid.basis_id,
        passed=True,
        evidence_id=sha256_id({
            "schema_version": "sergeant.sae160.repository-only-evidence.v1",
            "kind": "not_a_canonical_kind",
            "subject_generation": generation,
            "basis_id": valid.basis_id,
            "passed": True,
        }),
    )
    with pytest.raises(RepositoryOnlyQualificationError, match="unknown SAE-160 evidence kind"):
        evaluate_repository_only_preparation(
            subject_generation=generation,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="c" * 64,
            evidence=[forged_kind],
        )

    forged_basis = RepositoryOnlyEvidence(
        kind=REQUIRED_EVIDENCE_KINDS[0],
        subject_generation=generation,
        basis_id="not-a-sha256",
        passed=True,
        evidence_id=sha256_id({
            "schema_version": "sergeant.sae160.repository-only-evidence.v1",
            "kind": REQUIRED_EVIDENCE_KINDS[0],
            "subject_generation": generation,
            "basis_id": "not-a-sha256",
            "passed": True,
        }),
    )
    with pytest.raises(RepositoryOnlyQualificationError, match="basis_id"):
        evaluate_repository_only_preparation(
            subject_generation=generation,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="c" * 64,
            evidence=[forged_basis],
        )


def test_evaluator_rejects_forged_non_boolean_passed_field():
    generation = "a" * 40
    forged = RepositoryOnlyEvidence(
        kind=REQUIRED_EVIDENCE_KINDS[0],
        subject_generation=generation,
        basis_id="b" * 64,
        passed="yes",
        evidence_id=sha256_id({
            "schema_version": "sergeant.sae160.repository-only-evidence.v1",
            "kind": REQUIRED_EVIDENCE_KINDS[0],
            "subject_generation": generation,
            "basis_id": "b" * 64,
            "passed": "yes",
        }),
    )

    with pytest.raises(RepositoryOnlyQualificationError, match="passed must be boolean"):
        evaluate_repository_only_preparation(
            subject_generation=generation,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="c" * 64,
            evidence=[forged],
        )
