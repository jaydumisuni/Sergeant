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
    assert result.failed == (REQUIRED_EVIDENCE_KINDS[0],)
    assert result.missing == (REQUIRED_EVIDENCE_KINDS[-1],)


def test_incomplete_evidence_preserves_independent_sae150_prerequisite_blocker():
    rows = complete_evidence()[:-1]

    result = evaluate(rows, state="GENESIS_PROVISIONAL")

    assert result.state == SAE160_INCOMPLETE
    assert result.missing == (REQUIRED_EVIDENCE_KINDS[-1],)
    assert result.blockers == (REQUIRED_EVIDENCE_KINDS[-1], "sae150_prerequisite")
    assert result.authority_gain == "NONE"


def test_missing_and_failed_evidence_are_distinct_in_preparation_identity():
    missing_rows = complete_evidence()[:-1]
    failed_rows = complete_evidence()
    failed_rows[-1] = evidence(REQUIRED_EVIDENCE_KINDS[-1], passed=False, byte=len(REQUIRED_EVIDENCE_KINDS))

    missing = evaluate(missing_rows, state=SAE150_COMPLETE_STATE)
    failed = evaluate(failed_rows, state=SAE150_COMPLETE_STATE)

    assert missing.blockers == failed.blockers == (REQUIRED_EVIDENCE_KINDS[-1],)
    assert missing.missing == (REQUIRED_EVIDENCE_KINDS[-1],)
    assert missing.failed == ()
    assert failed.missing == ()
    assert failed.failed == (REQUIRED_EVIDENCE_KINDS[-1],)
    assert missing.preparation_id != failed.preparation_id


def test_failed_evidence_is_not_counted_as_satisfied():
    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)

    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert REQUIRED_EVIDENCE_KINDS[0] not in result.satisfied
    assert result.failed == (REQUIRED_EVIDENCE_KINDS[0],)
    assert result.state == SAE160_INCOMPLETE
    assert result.authority_gain == "NONE"


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


def test_sae150_transition_changes_preparation_identity_without_authority_gain():
    """A provisional package cannot replay its identity as a qualified prerequisite."""
    rows = complete_evidence()
    provisional = evaluate(rows, state="GENESIS_PROVISIONAL")
    complete = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert provisional.sae150_package_id == complete.sae150_package_id
    assert provisional.evidence_ids == complete.evidence_ids
    assert provisional.preparation_id != complete.preparation_id
    assert provisional.state == SAE160_WAITING_SAE150
    assert provisional.blockers == ("sae150_prerequisite",)
    assert complete.state == SAE160_READY
    assert complete.blockers == ()
    assert provisional.authority_gain == complete.authority_gain == "NONE"


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


def test_sae150_state_rejects_unknown_canonical_value():
    with pytest.raises(RepositoryOnlyQualificationError, match="unknown sae150_state"):
        evaluate(complete_evidence(), state="QUALIFIED_BY_LABEL")


def test_evaluator_rejects_string_like_evidence_through_domain_boundary():
    for invalid in ("clean_clone", b"clean_clone"):
        with pytest.raises(RepositoryOnlyQualificationError, match="non-string iterable"):
            evaluate_repository_only_preparation(
                subject_generation=HEAD,
                sae150_state=SAE150_COMPLETE_STATE,
                sae150_package_id="aa" * 32,
                evidence=invalid,
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


def test_evidence_factory_rejects_subclass_before_instantiation():
    class HostileEvidence(RepositoryOnlyEvidence):
        def __new__(cls, *args, **kwargs):
            raise AssertionError("subclass constructor must not execute")

    with pytest.raises(RepositoryOnlyQualificationError, match="non-canonical SAE-160 evidence factory"):
        HostileEvidence.create(
            kind=REQUIRED_EVIDENCE_KINDS[0],
            subject_generation=HEAD,
            basis_id="aa" * 32,
            passed=True,
        )


def test_evaluator_rejects_subclassed_evidence_before_attribute_access():
    class HostileEvidence(RepositoryOnlyEvidence):
        def __getattribute__(self, name):
            raise RuntimeError("untrusted evidence attributes must not be read")

    valid = evidence(REQUIRED_EVIDENCE_KINDS[0])
    hostile = HostileEvidence(
        kind=valid.kind,
        subject_generation=valid.subject_generation,
        basis_id=valid.basis_id,
        passed=valid.passed,
        evidence_id=valid.evidence_id,
    )
    with pytest.raises(RepositoryOnlyQualificationError, match="non-canonical SAE-160 records"):
        evaluate([hostile], state=SAE150_COMPLETE_STATE)


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

def test_evaluator_rejects_forged_malformed_evidence_subject_generation():
    valid = evidence(REQUIRED_EVIDENCE_KINDS[0])
    forged = replace(valid, subject_generation="not-a-git-object-id")

    with pytest.raises(RepositoryOnlyQualificationError, match="subject_generation"):
        evaluate([forged], state=SAE150_COMPLETE_STATE)


def test_evaluator_rejects_malformed_subject_generation_at_authority_boundary():
    with pytest.raises(RepositoryOnlyQualificationError, match="subject_generation"):
        evaluate_repository_only_preparation(
            subject_generation="not-a-git-object-id",
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=[],
        )


def test_evaluator_rejects_malformed_sae150_package_identity_at_authority_boundary():
    with pytest.raises(RepositoryOnlyQualificationError, match="sae150_package_id"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="not-a-sha256",
            evidence=complete_evidence(),
        )



def test_evaluator_fail_closes_when_evidence_iterator_raises_value_error():
    def broken_evidence():
        yield complete_evidence()[0]
        raise ValueError("collector failed while enumerating evidence")

    with pytest.raises(RepositoryOnlyQualificationError, match="evidence must be an iterable"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=broken_evidence(),
        )


@pytest.mark.parametrize("error_type", [RuntimeError, OSError, LookupError])
def test_evaluator_fail_closes_when_evidence_collector_raises(error_type):
    def broken_evidence():
        yield complete_evidence()[0]
        raise error_type("collector runtime failed while enumerating evidence")

    with pytest.raises(RepositoryOnlyQualificationError, match="evidence must be an iterable"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=broken_evidence(),
        )


def test_evaluator_bounds_untrusted_unending_evidence_stream():
    pulls = 0

    def endless_evidence():
        nonlocal pulls
        while True:
            pulls += 1
            kind = REQUIRED_EVIDENCE_KINDS[(pulls - 1) % len(REQUIRED_EVIDENCE_KINDS)]
            yield evidence(kind, byte=pulls)

    with pytest.raises(RepositoryOnlyQualificationError, match="duplicate SAE-160 evidence kind"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=endless_evidence(),
        )

    assert pulls == len(REQUIRED_EVIDENCE_KINDS) + 1


def test_noncanonical_evidence_kind_fails_closed_before_membership():
    class HostileKind:
        def __eq__(self, other):
            raise RuntimeError("hostile kind equality must not execute")

    for invalid in ([], HostileKind()):
        with pytest.raises(RepositoryOnlyQualificationError, match="non-string SAE-160 evidence kind"):
            RepositoryOnlyEvidence.create(
                kind=invalid, subject_generation=HEAD, basis_id="aa" * 32, passed=True
            )
        forged = replace(evidence(REQUIRED_EVIDENCE_KINDS[0]), kind=invalid)
        with pytest.raises(RepositoryOnlyQualificationError, match="non-string SAE-160 evidence kind"):
            evaluate([forged], state=SAE150_COMPLETE_STATE)


def test_evaluator_rejects_forged_string_subclass_kind_before_membership():
    class HostileString(str):
        def __eq__(self, other):
            raise RuntimeError("hostile equality must not execute")

        def __hash__(self):
            raise RuntimeError("hostile hash must not execute")

    forged = replace(
        evidence(REQUIRED_EVIDENCE_KINDS[0]),
        kind=HostileString(REQUIRED_EVIDENCE_KINDS[0]),
    )
    with pytest.raises(RepositoryOnlyQualificationError, match="non-string SAE-160 evidence kind"):
        evaluate([forged], state=SAE150_COMPLETE_STATE)


def test_evaluator_rejects_hostile_sae150_state_subclass_before_normalization():
    class HostileState(str):
        def strip(self, *args, **kwargs):
            raise RuntimeError("hostile state normalization must not execute")

        def __eq__(self, other):
            raise RuntimeError("hostile state equality must not execute")

    with pytest.raises(RepositoryOnlyQualificationError, match="sae150_state"):
        evaluate(complete_evidence(), state=HostileState(SAE150_COMPLETE_STATE))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("subject_generation", "non-string SAE-160 evidence subject_generation"),
        ("basis_id", "non-string SAE-160 evidence basis_id"),
        ("evidence_id", "non-string SAE-160 evidence identity"),
    ],
)
def test_evaluator_rejects_hostile_evidence_identity_field_subclasses(field, message):
    class HostileString(str):
        def __eq__(self, other):
            raise RuntimeError("hostile equality must not execute")

        def __ne__(self, other):
            raise RuntimeError("hostile inequality must not execute")

        def __hash__(self):
            raise RuntimeError("hostile hash must not execute")

    original = evidence(REQUIRED_EVIDENCE_KINDS[0])
    forged = replace(original, **{field: HostileString(getattr(original, field))})

    with pytest.raises(RepositoryOnlyQualificationError, match=message):
        evaluate([forged], state=SAE150_COMPLETE_STATE)


@pytest.mark.parametrize(
    "missing_field",
    ("kind", "subject_generation", "basis_id", "passed", "evidence_id"),
)
def test_evaluator_rejects_incomplete_canonical_records_before_next_pull(missing_field):
    original = evidence(REQUIRED_EVIDENCE_KINDS[0])
    forged = replace(original)
    object.__delattr__(forged, missing_field)
    pulls = []

    def collector():
        pulls.append("first")
        yield forged
        pulls.append("second")
        raise AssertionError("invalid first record must stop the collector")

    with pytest.raises(RepositoryOnlyQualificationError, match="incomplete canonical"):
        evaluate(collector(), state=SAE150_COMPLETE_STATE)

    assert pulls == ["first"]


def test_evaluator_rejects_first_noncanonical_row_without_pulling_next():
    pulls = []

    def hostile_collector():
        pulls.append("first")
        yield object()
        pulls.append("second")
        raise AssertionError("invalid first row must stop the collector")

    with pytest.raises(RepositoryOnlyQualificationError, match="non-canonical SAE-160 records"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=hostile_collector(),
        )

    assert pulls == ["first"]


def test_evaluator_rejects_invalid_kind_before_pulling_later_evidence():
    pulls = []

    def hostile_collector():
        pulls.append("first")
        yield replace(evidence(REQUIRED_EVIDENCE_KINDS[0]), kind="forged_kind")
        pulls.append("second")
        raise AssertionError("invalid first kind must stop the collector")

    with pytest.raises(RepositoryOnlyQualificationError, match="unknown SAE-160 evidence kind"):
        evaluate_repository_only_preparation(
            subject_generation=HEAD,
            sae150_state=SAE150_COMPLETE_STATE,
            sae150_package_id="aa" * 32,
            evidence=hostile_collector(),
        )

    assert pulls == ["first"]


def test_evaluator_fail_closes_when_iterator_construction_raises():
    class BrokenIterable:
        def __iter__(self):
            raise RuntimeError("collector initialization failed")

    with pytest.raises(RepositoryOnlyQualificationError, match="evidence must be an iterable"):
        evaluate(BrokenIterable(), state=SAE150_COMPLETE_STATE)



@pytest.mark.parametrize(
    "boundary",
    ["evaluator_subject", "evaluator_package", "factory_subject", "factory_basis"],
)
def test_hostile_top_level_and_factory_identity_subclasses_fail_closed(boundary):
    class HostileIdentity(str):
        def __eq__(self, other):
            raise RuntimeError("hostile identity equality must not execute")

        def __ne__(self, other):
            raise RuntimeError("hostile identity inequality must not execute")

        def __hash__(self):
            raise RuntimeError("hostile identity hash must not execute")

    if boundary == "evaluator_subject":
        with pytest.raises(RepositoryOnlyQualificationError, match="non-string SAE-160 subject_generation"):
            evaluate_repository_only_preparation(
                subject_generation=HostileIdentity(HEAD),
                sae150_state=SAE150_COMPLETE_STATE,
                sae150_package_id="aa" * 32,
                evidence=complete_evidence(),
            )
    elif boundary == "evaluator_package":
        with pytest.raises(RepositoryOnlyQualificationError, match="non-string SAE-160 sae150_package_id"):
            evaluate_repository_only_preparation(
                subject_generation=HEAD,
                sae150_state=SAE150_COMPLETE_STATE,
                sae150_package_id=HostileIdentity("aa" * 32),
                evidence=complete_evidence(),
            )
    else:
        kwargs = dict(kind=REQUIRED_EVIDENCE_KINDS[0], subject_generation=HEAD, basis_id="aa" * 32, passed=True)
        field = "subject_generation" if boundary == "factory_subject" else "basis_id"
        kwargs[field] = HostileIdentity(kwargs[field])
        with pytest.raises(RepositoryOnlyQualificationError, match=f"non-string SAE-160 {field}"):
            RepositoryOnlyEvidence.create(**kwargs)


def test_evaluator_snapshots_validated_evidence_before_collector_mutates_it():
    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)

    def mutable_collector():
        yield rows[0]
        # Frozen dataclasses can still be mutated through object.__setattr__.
        # The collector must not rewrite already-validated authority evidence.
        object.__setattr__(rows[0], "passed", True)
        yield from rows[1:]

    result = evaluate(mutable_collector(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_INCOMPLETE
    assert result.failed == (REQUIRED_EVIDENCE_KINDS[0],)
    assert REQUIRED_EVIDENCE_KINDS[0] not in result.satisfied
    assert result.authority_gain == "NONE"


def test_evaluator_snapshots_validated_basis_before_collector_mutates_it():
    baseline = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)
    rows = complete_evidence()

    def mutable_collector():
        yield rows[0]
        # The collector must not rewrite an already-admitted basis binding.
        object.__setattr__(rows[0], "basis_id", "f" * 64)
        yield from rows[1:]

    result = evaluate(mutable_collector(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_READY
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.evidence_ids == baseline.evidence_ids
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


def test_evaluator_snapshots_validated_kind_before_collector_mutates_it():
    baseline = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)
    rows = complete_evidence()

    def mutable_collector():
        yield rows[0]
        # A yielded frozen record can be rewritten by its collector.
        object.__setattr__(rows[0], "kind", REQUIRED_EVIDENCE_KINDS[1])
        yield from rows[1:]

    result = evaluate(mutable_collector(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_READY
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.satisfied == baseline.satisfied
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


def test_evaluator_snapshots_validated_generation_before_collector_mutates_it():
    baseline = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)
    rows = complete_evidence()

    def mutable_collector():
        yield rows[0]
        object.__setattr__(rows[0], "subject_generation", "b" * 40)
        yield from rows[1:]

    result = evaluate(mutable_collector(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_READY
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


def test_evaluator_snapshots_validated_evidence_identity_before_collector_mutates_it():
    baseline = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)
    rows = complete_evidence()

    def mutable_collector():
        yield rows[0]
        # A hostile collector may mutate a frozen record after it was yielded.
        # Neither the evidence map nor the preparation digest may be rewritten.
        object.__setattr__(rows[0], "evidence_id", "f" * 64)
        yield from rows[1:]

    result = evaluate(mutable_collector(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_READY
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.evidence_ids == baseline.evidence_ids
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


def test_evaluator_snapshots_record_before_hashing_against_concurrent_collector_mutation(monkeypatch):
    import main_review.repository_only_qualification as qualification

    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)
    original = rows[0]
    original_hash = qualification.sha256_id
    mutated = False

    def hash_with_interleaved_collector_mutation(body):
        nonlocal mutated
        digest = original_hash(body)
        if body.get("schema_version") == "sergeant.sae160.repository-only-evidence.v1" and not mutated:
            # Simulate the collector's concurrent mutation during digest validation.
            object.__setattr__(original, "passed", True)
            mutated = True
        return digest

    monkeypatch.setattr(qualification, "sha256_id", hash_with_interleaved_collector_mutation)
    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert mutated
    assert result.state == SAE160_INCOMPLETE
    assert result.failed == (REQUIRED_EVIDENCE_KINDS[0],)
    assert result.authority_gain == "NONE"


def test_evaluator_keeps_snapshot_identity_when_hash_callback_mutates_source(monkeypatch):
    import main_review.repository_only_qualification as qualification

    rows = complete_evidence()
    baseline = evaluate(rows, state=SAE150_COMPLETE_STATE)
    source = rows[0]
    original_hash = qualification.sha256_id
    mutated = False

    def interleaved_hash(body):
        nonlocal mutated
        digest = original_hash(body)
        if body.get("schema_version") == "sergeant.sae160.repository-only-evidence.v1" and not mutated:
            object.__setattr__(source, "evidence_id", "f" * 64)
            mutated = True
        return digest

    monkeypatch.setattr(qualification, "sha256_id", interleaved_hash)
    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert mutated
    assert result.state == SAE160_READY
    assert result.evidence_ids == baseline.evidence_ids
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("kind", REQUIRED_EVIDENCE_KINDS[1]),
        ("basis_id", "ee" * 32),
        ("subject_generation", "b" * 40),
    ],
)
def test_evaluator_keeps_snapshot_fields_when_hash_callback_mutates_source(
    monkeypatch, field, replacement
):
    import main_review.repository_only_qualification as qualification

    rows = complete_evidence()
    baseline = evaluate(rows, state=SAE150_COMPLETE_STATE)
    source = rows[0]
    original_hash = qualification.sha256_id
    mutated = False

    def interleaved_hash(body):
        nonlocal mutated
        digest = original_hash(body)
        if body.get("schema_version") == "sergeant.sae160.repository-only-evidence.v1" and not mutated:
            object.__setattr__(source, field, replacement)
            mutated = True
        return digest

    monkeypatch.setattr(qualification, "sha256_id", interleaved_hash)
    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert mutated
    assert result.state == SAE160_READY
    assert result.evidence_ids == baseline.evidence_ids
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


def test_evaluator_keeps_passed_snapshot_when_hash_callback_flips_success(monkeypatch):
    import main_review.repository_only_qualification as qualification

    rows = complete_evidence()
    baseline = evaluate(rows, state=SAE150_COMPLETE_STATE)
    source = rows[0]
    original_hash = qualification.sha256_id
    mutated = False

    def interleaved_hash(body):
        nonlocal mutated
        digest = original_hash(body)
        if body.get("schema_version") == "sergeant.sae160.repository-only-evidence.v1" and not mutated:
            object.__setattr__(source, "passed", False)
            mutated = True
        return digest

    monkeypatch.setattr(qualification, "sha256_id", interleaved_hash)
    result = evaluate(rows, state=SAE150_COMPLETE_STATE)

    assert mutated
    assert result.state == SAE160_READY
    assert result.satisfied == baseline.satisfied
    assert result.evidence_ids == baseline.evidence_ids
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize(
    ("extra_row", "expected_error"),
    [
        ("malformed_digest", "evidence identity is non-canonical"),
        ("forged_full_digest", "evidence identity is non-canonical"),
        ("valid_duplicate", "duplicate SAE-160 evidence kind"),
        ("wrong_generation", "does not match exact candidate"),
        ("nonboolean_pass", "passed must be boolean"),
        ("unknown_kind", "unknown SAE-160 evidence kind"),
    ],
)
def test_overfull_collector_rejects_twelfth_row_without_thirteenth_read(extra_row, expected_error):
    pulls = []

    def hostile_collector():
        for row in complete_evidence():
            pulls.append("required")
            yield row
        pulls.append("extra")
        extra = evidence(REQUIRED_EVIDENCE_KINDS[0], byte=99)
        if extra_row == "malformed_digest":
            extra = replace(extra, evidence_id="not-a-digest")
        elif extra_row == "forged_full_digest":
            extra = replace(extra, evidence_id="f" * 64)
        elif extra_row == "wrong_generation":
            extra = replace(extra, subject_generation="b" * 40)
        elif extra_row == "nonboolean_pass":
            extra = replace(extra, passed=1)
        elif extra_row == "unknown_kind":
            extra = replace(extra, kind="owner_says_ok")
        yield extra
        pulls.append("forbidden")
        raise AssertionError("thirteenth evidence read must not execute")

    with pytest.raises(RepositoryOnlyQualificationError, match=expected_error):
        evaluate(hostile_collector(), state=SAE150_COMPLETE_STATE)

    assert pulls == ["required"] * len(REQUIRED_EVIDENCE_KINDS) + ["extra"]


@pytest.mark.parametrize("error_type", [RuntimeError, OSError, ValueError])
def test_complete_census_rejects_failed_iterator_finalization(error_type):
    """Eleven valid records cannot conceal a failing exhaustion probe."""
    pulls = []

    def failing_finalization():
        for row in complete_evidence():
            pulls.append("required")
            yield row
        pulls.append("finalization")
        raise error_type("collector failed after complete census")

    with pytest.raises(RepositoryOnlyQualificationError, match="evidence must be an iterable"):
        evaluate(failing_finalization(), state=SAE150_COMPLETE_STATE)

    assert pulls == ["required"] * len(REQUIRED_EVIDENCE_KINDS) + ["finalization"]


def test_overfull_collector_rejects_hostile_record_subclass_without_thirteenth_read():
    class HostileRecord(RepositoryOnlyEvidence):
        def __getattribute__(self, name):
            raise AssertionError("hostile twelfth-record attributes must not be accessed")

    canonical = evidence(REQUIRED_EVIDENCE_KINDS[0], byte=99)
    hostile = HostileRecord(
        kind=canonical.kind,
        subject_generation=canonical.subject_generation,
        basis_id=canonical.basis_id,
        passed=canonical.passed,
        evidence_id=canonical.evidence_id,
    )
    pulls = []

    def hostile_collector():
        for row in complete_evidence():
            pulls.append("required")
            yield row
        pulls.append("extra")
        yield hostile
        pulls.append("forbidden")
        raise AssertionError("thirteenth evidence read must not execute")

    with pytest.raises(RepositoryOnlyQualificationError, match="non-canonical SAE-160 records"):
        evaluate(hostile_collector(), state=SAE150_COMPLETE_STATE)

    assert pulls == ["required"] * len(REQUIRED_EVIDENCE_KINDS) + ["extra"]


def test_complete_census_never_consults_collector_length_or_truthiness():
    """Hostile size/truthiness callbacks must not influence bounded enumeration."""
    class HostileSizedCollector:
        def __iter__(self):
            return iter(complete_evidence())

        def __len__(self):
            raise AssertionError("collector length must not be consulted")

        def __bool__(self):
            raise AssertionError("collector truthiness must not be consulted")

        def __length_hint__(self):
            raise AssertionError("collector length hint must not be consulted")

    result = evaluate(HostileSizedCollector(), state=SAE150_COMPLETE_STATE)
    assert result.state == SAE160_READY
    assert len(result.satisfied) == len(REQUIRED_EVIDENCE_KINDS)
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("invalid_passed", [None, 0, 1, [], {}, "true"])
def test_evaluator_rejects_nonboolean_passed_before_collector_advances(invalid_passed):
    forged = replace(evidence(REQUIRED_EVIDENCE_KINDS[0]), passed=invalid_passed)
    pulls = []

    def collector():
        pulls.append("first")
        yield forged
        pulls.append("second")
        raise AssertionError("invalid passed must stop collector before another pull")

    with pytest.raises(RepositoryOnlyQualificationError, match="passed must be boolean"):
        evaluate(collector(), state=SAE150_COMPLETE_STATE)

    assert pulls == ["first"]


@pytest.mark.parametrize("invalid_passed", [None, 0, 1, [], {}, "true"])
def test_factory_rejects_nonboolean_passed_before_hashing(monkeypatch, invalid_passed):
    import main_review.repository_only_qualification as qualification

    def forbidden_hash(_body):
        raise AssertionError("invalid factory verdict must not reach identity hashing")

    monkeypatch.setattr(qualification, "sha256_id", forbidden_hash)
    with pytest.raises(RepositoryOnlyQualificationError, match="passed must be boolean"):
        RepositoryOnlyEvidence.create(
            kind=REQUIRED_EVIDENCE_KINDS[0],
            subject_generation=HEAD,
            basis_id="aa" * 32,
            passed=invalid_passed,
        )


def test_failed_census_identity_is_order_independent_and_cannot_inherit_ready():
    rows = complete_evidence()
    rows[0] = evidence(REQUIRED_EVIDENCE_KINDS[0], passed=False, byte=1)
    failed = evaluate(rows, state=SAE150_COMPLETE_STATE)
    replay = evaluate(reversed(rows), state=SAE150_COMPLETE_STATE)
    passing = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)

    assert failed.state == SAE160_INCOMPLETE
    assert failed.failed == (REQUIRED_EVIDENCE_KINDS[0],)
    assert failed.preparation_id == replay.preparation_id
    assert failed.evidence_by_kind == replay.evidence_by_kind
    assert failed.preparation_id != passing.preparation_id
    assert failed.authority_gain == replay.authority_gain == "NONE"


def test_collector_finalization_cannot_rewrite_validated_census_identity():
    """A collector's exhaustion hook must not rewrite already-admitted rows."""
    rows = complete_evidence()
    baseline = evaluate(rows, state=SAE150_COMPLETE_STATE)

    def mutating_finalization():
        yield from rows
        object.__setattr__(rows[0], "passed", False)
        object.__setattr__(rows[0], "evidence_id", "f" * 64)

    result = evaluate(mutating_finalization(), state=SAE150_COMPLETE_STATE)

    assert rows[0].passed is False
    assert rows[0].evidence_id == "f" * 64
    assert result.state == SAE160_READY
    assert result.satisfied == baseline.satisfied
    assert result.evidence_ids == baseline.evidence_ids
    assert result.evidence_by_kind == baseline.evidence_by_kind
    assert result.preparation_id == baseline.preparation_id
    assert result.authority_gain == "NONE"


@pytest.mark.parametrize("kind", REQUIRED_EVIDENCE_KINDS)
@pytest.mark.parametrize("defect", ("omitted", "failed"))
def test_each_mandatory_census_kind_independently_blocks_readiness(kind, defect):
    """Every mandatory SAE-160 kind is a separate fail-closed obligation."""
    rows = complete_evidence()
    index = REQUIRED_EVIDENCE_KINDS.index(kind)
    if defect == "omitted":
        rows.pop(index)
    else:
        rows[index] = evidence(kind, passed=False, byte=index + 1)

    result = evaluate(rows, state=SAE150_COMPLETE_STATE)
    complete = evaluate(complete_evidence(), state=SAE150_COMPLETE_STATE)

    assert result.state == SAE160_INCOMPLETE
    assert result.blockers == (kind,)
    assert result.satisfied == tuple(k for k in REQUIRED_EVIDENCE_KINDS if k != kind)
    assert result.missing == ((kind,) if defect == "omitted" else ())
    assert result.failed == ((kind,) if defect == "failed" else ())
    assert (kind in dict(result.evidence_by_kind)) is (defect == "failed")
    assert result.preparation_id != complete.preparation_id
    assert result.authority_gain == "NONE"


def test_all_failed_census_preserves_every_failure_and_sae150_blocker():
    """An entirely failed census cannot mask failures or an upstream gate."""
    rows = [
        evidence(kind, passed=False, byte=index + 1)
        for index, kind in enumerate(REQUIRED_EVIDENCE_KINDS)
    ]
    forward = evaluate(rows, state="GENESIS_PROVISIONAL")
    reverse = evaluate(reversed(rows), state="GENESIS_PROVISIONAL")

    assert forward.state == SAE160_INCOMPLETE
    assert forward.satisfied == ()
    assert forward.missing == ()
    assert forward.failed == REQUIRED_EVIDENCE_KINDS
    assert forward.blockers == tuple(sorted((*REQUIRED_EVIDENCE_KINDS, "sae150_prerequisite")))
    assert forward.preparation_id == reverse.preparation_id
    assert forward.authority_gain == reverse.authority_gain == "NONE"
