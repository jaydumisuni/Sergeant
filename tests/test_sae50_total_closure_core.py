from __future__ import annotations

import importlib.util

import pytest


ZERO = "0" * 64
ONE = "1" * 64
TWO = "2" * 64
THREE = "3" * 64


def _contract():
    assert importlib.util.find_spec("main_review.closure_core") is not None, "SAE-50 total-closure core is missing"
    from main_review.closure_core import (
        ClosureBasis,
        ClosureCoreError,
        ClosureGrade,
        ClosureWitness,
        CollectionSemantics,
        affected_relation_fixpoint,
        evaluate_closure,
    )
    return locals()


def test_valid_subset_cannot_become_exact_complete_collection() -> None:
    c = _contract()
    basis = c["ClosureBasis"].create(
        source_basis_id=ZERO,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b", "c"),
        grade=c["ClosureGrade"].EXACT,
    )
    witness = c["ClosureWitness"].create(basis_id=basis.basis_id, members=("a", "b"), declared_complete=True)
    result = c["evaluate_closure"](basis=basis, witness=witness)
    assert result.grade is c["ClosureGrade"].PARTIAL
    assert result.complete is False
    assert "missing" in " ".join(result.blockers).lower()


def test_witness_bound_to_another_basis_is_rejected() -> None:
    c = _contract()
    basis = c["ClosureBasis"].create(
        source_basis_id=ZERO,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b"),
        grade=c["ClosureGrade"].EXACT,
    )
    other = c["ClosureBasis"].create(
        source_basis_id=ONE,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b"),
        grade=c["ClosureGrade"].EXACT,
    )
    witness = c["ClosureWitness"].create(basis_id=other.basis_id, members=("a", "b"), declared_complete=True)
    with pytest.raises(c["ClosureCoreError"], match="different basis"):
        c["evaluate_closure"](basis=basis, witness=witness)


def test_partial_basis_cannot_produce_exact_child_collection() -> None:
    c = _contract()
    basis = c["ClosureBasis"].create(
        source_basis_id=ZERO,
        source_basis_kind="semantic_probe",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b"),
        grade=c["ClosureGrade"].PARTIAL,
    )
    witness = c["ClosureWitness"].create(basis_id=basis.basis_id, members=("a", "b"), declared_complete=True)
    result = c["evaluate_closure"](basis=basis, witness=witness)
    assert result.grade is c["ClosureGrade"].PARTIAL
    assert result.complete is False


def test_set_multiset_and_order_semantics_do_not_collapse() -> None:
    c = _contract()
    cases = (
        (c["CollectionSemantics"].SET, ("a", "b"), ("b", "a"), True),
        (c["CollectionSemantics"].MULTISET, ("a", "a", "b"), ("a", "b", "a"), True),
        (c["CollectionSemantics"].ORDER, ("a", "b"), ("b", "a"), False),
    )
    for semantics, expected, observed, should_close in cases:
        basis = c["ClosureBasis"].create(
            source_basis_id=ZERO,
            source_basis_kind="independent_census",
            semantics=semantics,
            members=expected,
            grade=c["ClosureGrade"].EXACT,
        )
        witness = c["ClosureWitness"].create(basis_id=basis.basis_id, members=observed, declared_complete=True)
        assert c["evaluate_closure"](basis=basis, witness=witness).complete is should_close


def test_multiplicity_undercount_cannot_close_multiset() -> None:
    c = _contract()
    basis = c["ClosureBasis"].create(
        source_basis_id=ZERO,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].MULTISET,
        members=("a", "a", "b"),
        grade=c["ClosureGrade"].EXACT,
    )
    witness = c["ClosureWitness"].create(basis_id=basis.basis_id, members=("a", "b"), declared_complete=True)
    assert c["evaluate_closure"](basis=basis, witness=witness).complete is False


def test_resource_exhaustion_conserves_unknown() -> None:
    c = _contract()
    result = c["affected_relation_fixpoint"](
        seeds=("a",),
        edges=(("a", "b"), ("b", "c"), ("c", "d")),
        budget=2,
    )
    assert result.grade is c["ClosureGrade"].UNKNOWN
    assert result.resource_exhausted is True


def test_affected_relation_fixpoint_completes_within_budget_even_with_cycle() -> None:
    c = _contract()
    result = c["affected_relation_fixpoint"](
        seeds=("a",),
        edges=(("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")),
        budget=20,
    )
    assert result.members == ("a", "b", "c", "d")
    assert result.grade is c["ClosureGrade"].EXACT
    assert result.resource_exhausted is False
    assert result.operations > 0


def test_self_declared_universe_cannot_be_positive_closure_authority() -> None:
    c = _contract()
    with pytest.raises(c["ClosureCoreError"], match="self-defining"):
        c["ClosureBasis"].create(
            source_basis_id=ZERO,
            source_basis_kind="self_declared",
            semantics=c["CollectionSemantics"].SET,
            members=("a",),
            grade=c["ClosureGrade"].EXACT,
        )


def test_proven_empty_requires_exact_independent_basis_and_complete_witness() -> None:
    c = _contract()
    exact = c["ClosureBasis"].create(
        source_basis_id=ONE,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=(),
        grade=c["ClosureGrade"].EXACT,
    )
    complete_witness = c["ClosureWitness"].create(basis_id=exact.basis_id, members=(), declared_complete=True)
    complete_result = c["evaluate_closure"](basis=exact, witness=complete_witness)
    assert complete_result.complete is True
    assert complete_result.proven_empty is True
    assert complete_result.certificate is not None

    incomplete_witness = c["ClosureWitness"].create(basis_id=exact.basis_id, members=(), declared_complete=False)
    incomplete_result = c["evaluate_closure"](basis=exact, witness=incomplete_witness)
    assert incomplete_result.complete is False
    assert incomplete_result.proven_empty is False
    assert incomplete_result.certificate is None


def test_late_member_discovery_invalidates_prior_certificate() -> None:
    c = _contract()
    old = c["ClosureBasis"].create(
        source_basis_id=ONE,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b"),
        grade=c["ClosureGrade"].EXACT,
    )
    result = c["evaluate_closure"](
        basis=old,
        witness=c["ClosureWitness"].create(basis_id=old.basis_id, members=("a", "b"), declared_complete=True),
    )
    assert result.certificate is not None
    new = c["ClosureBasis"].create(
        source_basis_id=TWO,
        source_basis_kind="independent_census",
        semantics=c["CollectionSemantics"].SET,
        members=("a", "b", "c"),
        grade=c["ClosureGrade"].EXACT,
    )
    with pytest.raises(c["ClosureCoreError"], match="invalidated"):
        result.certificate.validate_against(new)
