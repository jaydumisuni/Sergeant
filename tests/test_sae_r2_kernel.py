from __future__ import annotations

import pytest
from pathlib import Path

from main_review.rust_assurance_kernel import (
    ADMISSIBLE,
    INADMISSIBLE,
    AssuranceCapsule,
    evaluate_capsule,
)


A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64


def valid_capsule(**overrides):
    values = dict(
        review_world_id=A,
        rab_id=B,
        active_contracts_id=C,
        applicable_instances_id=D,
        expected_obligations_id=E,
        authority_premises_id=F,
        closure_certificate_id=A,
        capability_passports_id=B,
        proof_world_id=C,
        falsifier_frontier_id=D,
        provenance_id=E,
        subject_generation="g90",
        current_generation="g90",
        review_world_qualified=True,
        rab_qualified=True,
        active_contracts_complete=True,
        applicable_instances_complete=True,
        expected_obligations_complete=True,
        authority_premises_typed=True,
        closure_certificate_valid=True,
        capability_passports_qualified=True,
        proof_world_bound=True,
        falsifier_frontier_complete=True,
        provenance_bound=True,
        unknowns_present=False,
        python_expected_list_authority=False,
        shared_implementation_claim=False,
    )
    values.update(overrides)
    return AssuranceCapsule(**values)


def test_complete_current_qualified_capsule_is_admissible():
    assert evaluate_capsule(valid_capsule()) == ADMISSIBLE


@pytest.mark.parametrize(
    "field,value",
    [
        ("review_world_qualified", False),
        ("rab_qualified", False),
        ("active_contracts_complete", False),
        ("applicable_instances_complete", False),
        ("expected_obligations_complete", False),
        ("authority_premises_typed", False),
        ("closure_certificate_valid", False),
        ("capability_passports_qualified", False),
        ("proof_world_bound", False),
        ("falsifier_frontier_complete", False),
        ("provenance_bound", False),
        ("unknowns_present", True),
        ("python_expected_list_authority", True),
        ("shared_implementation_claim", True),
        ("subject_generation", "stale"),
    ],
)
def test_constitutional_failures_are_inadmissible(field, value):
    assert evaluate_capsule(valid_capsule(**{field: value})) == INADMISSIBLE


def test_truncated_authority_identity_is_inadmissible():
    assert evaluate_capsule(valid_capsule(proof_world_id="a" * 16)) == INADMISSIBLE


def test_kernel_returns_only_constitutional_admissibility_tokens():
    assert {evaluate_capsule(valid_capsule()), evaluate_capsule(valid_capsule(unknowns_present=True))} == {
        ADMISSIBLE,
        INADMISSIBLE,
    }


def test_rust_workflow_proves_identity_and_kernel_crates():
    workflow = Path(".github/workflows/sae-r2-rust-proof.yml").read_text(encoding="utf-8")
    assert "cargo test --manifest-path rust/sergeant-assurance-identity/Cargo.toml --locked" in workflow
    assert "cargo test --manifest-path rust/sergeant-assurance-kernel/Cargo.toml --locked" in workflow
    frozen_r1 = Path(".github/workflows/sae-rust-proof.yml").read_text(encoding="utf-8")
    assert "rust/sergeant-assurance-kernel" not in frozen_r1


def test_candidate_record_remains_non_authoritative():
    import json
    record = json.loads(Path("docs/119-sae-r2-rust-assurance-kernel-candidate-manifest.json").read_text())
    assert record["node"] == "SAE-R2"
    assert record["lifecycle_state"] == "CANDIDATE"
    assert record["authority_gain"] == "none"
    assert record["requires_proven"] == ["SAE-R1", "SAE-30", "SAE-60", "SAE-70", "SAE-80", "SAE-90"]
    assert record["output_domain"] == ["ADMISSIBLE", "INADMISSIBLE"]


def test_kernel_has_no_aggregate_qualification_trust_switches():
    rust = Path("rust/sergeant-assurance-kernel/src/lib.rs").read_text(encoding="utf-8")
    python_ref = Path("main_review/rust_assurance_kernel.py").read_text(encoding="utf-8")
    for forbidden in ("all_inputs_qualified", "closure_exact", "capsule_complete"):
        assert forbidden not in rust
        assert forbidden not in python_ref


@pytest.mark.parametrize("field", [
    "review_world_qualified",
    "rab_qualified",
    "active_contracts_complete",
    "applicable_instances_complete",
    "expected_obligations_complete",
    "authority_premises_typed",
    "closure_certificate_valid",
    "capability_passports_qualified",
    "proof_world_bound",
    "falsifier_frontier_complete",
    "provenance_bound",
])
def test_each_typed_authority_gate_fails_closed_independently(field):
    assert evaluate_capsule(valid_capsule(**{field: False})) == INADMISSIBLE
