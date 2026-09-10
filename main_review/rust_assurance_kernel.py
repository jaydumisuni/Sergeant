"""SAE-R2 constitutional admissibility reference surface.

This Python module defines the frozen capsule contract and a reference evaluator
used to construct adversarial tests. It is not authority for the independent
Rust kernel and must never be treated as an expected-list oracle for Rust.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rust_identity_vectors import require_authority_id, RustIdentityError

ADMISSIBLE = "ADMISSIBLE"
INADMISSIBLE = "INADMISSIBLE"

_AUTHORITY_FIELDS = (
    "review_world_id",
    "rab_id",
    "active_contracts_id",
    "applicable_instances_id",
    "expected_obligations_id",
    "authority_premises_id",
    "closure_certificate_id",
    "capability_passports_id",
    "proof_world_id",
    "falsifier_frontier_id",
    "provenance_id",
)


@dataclass(frozen=True)
class AssuranceCapsule:
    review_world_id: str
    rab_id: str
    active_contracts_id: str
    applicable_instances_id: str
    expected_obligations_id: str
    authority_premises_id: str
    closure_certificate_id: str
    capability_passports_id: str
    proof_world_id: str
    falsifier_frontier_id: str
    provenance_id: str
    subject_generation: str
    current_generation: str
    review_world_qualified: bool
    rab_qualified: bool
    active_contracts_complete: bool
    applicable_instances_complete: bool
    expected_obligations_complete: bool
    authority_premises_typed: bool
    closure_certificate_valid: bool
    capability_passports_qualified: bool
    proof_world_bound: bool
    falsifier_frontier_complete: bool
    provenance_bound: bool
    unknowns_present: bool
    python_expected_list_authority: bool
    shared_implementation_claim: bool


def _ids_are_canonical(capsule: AssuranceCapsule) -> bool:
    try:
        for name in _AUTHORITY_FIELDS:
            require_authority_id(getattr(capsule, name))
    except RustIdentityError:
        return False
    return True


def evaluate_capsule(capsule: AssuranceCapsule) -> str:
    """Return constitutional admissibility only.

    This function intentionally cannot emit Sergeant engineering verdicts.
    Any uncertainty, incompleteness, stale generation, or unqualified premise
    fails closed to INADMISSIBLE.
    """
    if not isinstance(capsule, AssuranceCapsule):
        return INADMISSIBLE
    if not _ids_are_canonical(capsule):
        return INADMISSIBLE
    component_gates = (
        capsule.review_world_qualified,
        capsule.rab_qualified,
        capsule.active_contracts_complete,
        capsule.applicable_instances_complete,
        capsule.expected_obligations_complete,
        capsule.authority_premises_typed,
        capsule.closure_certificate_valid,
        capsule.capability_passports_qualified,
        capsule.proof_world_bound,
        capsule.falsifier_frontier_complete,
        capsule.provenance_bound,
    )
    if not all(component_gates):
        return INADMISSIBLE
    if capsule.unknowns_present:
        return INADMISSIBLE
    if capsule.python_expected_list_authority:
        return INADMISSIBLE
    if capsule.shared_implementation_claim:
        return INADMISSIBLE
    if not capsule.subject_generation or capsule.subject_generation != capsule.current_generation:
        return INADMISSIBLE
    return ADMISSIBLE
