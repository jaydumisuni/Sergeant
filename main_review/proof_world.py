"""SAE-80 RED interface surface for Evidence + Proof World.

This module intentionally contains only importable authority shapes. The
founding SAE-80 RED campaign in ``tests/test_proof_world.py`` must fail at the
missing Proof World behavior rather than at test collection. A later TDD
generation replaces these ``NotImplementedError`` boundaries with the minimal
implementation required by the frozen RED contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from .assurance_contract_registry import ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation
from .contract_closure_protocol import QualifiedContractClosure
from .review_world import ReviewWorldError


class ProofWorldError(ReviewWorldError):
    """Raised for malformed or inadmissible SAE-80 Proof World inputs."""


class ProofClass(str, Enum):
    MECHANICAL = "mechanical"
    EXHAUSTIVE_ORACLE = "exhaustive-oracle"
    HEURISTIC = "heuristic"


class AssumptionKind(str, Enum):
    VERIFIED = "VERIFIED"
    DECLARED = "DECLARED"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class WorldCoordinates:
    candidate_generation: str
    framework_generation: str
    provider_generation: str
    dependency_generations: tuple[tuple[str, str], ...]
    epoch: int
    world_id: str

    @classmethod
    def create(
        cls,
        *,
        candidate_generation: str,
        framework_generation: str,
        provider_generation: str,
        dependency_generations: Mapping[str, str],
        epoch: int,
    ) -> "WorldCoordinates":
        raise NotImplementedError("SAE-80 Proof World coordinates are not implemented")


@dataclass(frozen=True)
class MaterialInputProof:
    family: str
    closure: ClosureGrade
    basis_id: str
    material_input_id: str

    @classmethod
    def create(
        cls,
        *,
        family: str,
        closure: ClosureGrade,
        basis_id: str,
    ) -> "MaterialInputProof":
        raise NotImplementedError("SAE-80 material-input proof is not implemented")


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    kind: AssumptionKind
    basis_id: str
    record_id: str

    @classmethod
    def create(
        cls,
        *,
        assumption_id: str,
        kind: AssumptionKind,
        basis_id: str,
    ) -> "Assumption":
        raise NotImplementedError("SAE-80 assumption taxonomy is not implemented")


@dataclass(frozen=True)
class EvidenceProof:
    proof_class: ProofClass
    claimed_closure: ClosureGrade
    obligation_id: str
    contract_instance_ids: tuple[str, ...]
    world_id: str
    material_inputs: tuple[MaterialInputProof, ...]
    claims: tuple[tuple[str, object], ...]
    assumptions: tuple[Assumption, ...]
    observed_epoch: int
    evidence_basis_id: str
    proof_ceiling: ClosureGrade
    evidence_id: str

    @classmethod
    def create(
        cls,
        *,
        proof_class: ProofClass,
        claimed_closure: ClosureGrade,
        obligation_id: str,
        contract_instance_ids: Sequence[str],
        world: WorldCoordinates,
        material_inputs: Sequence[MaterialInputProof],
        claims: Mapping[str, object],
        assumptions: Sequence[Assumption],
        observed_epoch: int,
        evidence_basis_id: str,
    ) -> "EvidenceProof":
        raise NotImplementedError("SAE-80 evidence proof is not implemented")


@dataclass(frozen=True)
class Contradiction:
    claim: str
    values: tuple[object, ...]
    evidence_ids: tuple[str, ...]
    contradiction_id: str


@dataclass(frozen=True)
class ProofWorld:
    qualified_closure_id: str
    obligation_id: str
    world_id: str
    grade: ClosureGrade
    material_inputs: tuple[MaterialInputProof, ...]
    evidence: tuple[EvidenceProof, ...]
    assumptions: tuple[Assumption, ...]
    contradictions: tuple[Contradiction, ...]
    blockers: tuple[str, ...]
    proof_world_id: str

    def validate(self) -> "ProofWorld":
        raise NotImplementedError("SAE-80 Proof World identity validation is not implemented")


def compile_proof_world(
    *,
    qualified_closure: QualifiedContractClosure,
    expected_obligation: ExpectedObligation,
    registry: ACRRegistry,
    world: WorldCoordinates,
    evidence: Sequence[EvidenceProof],
) -> ProofWorld:
    raise NotImplementedError("SAE-80 Evidence + Proof World compilation is not implemented")
