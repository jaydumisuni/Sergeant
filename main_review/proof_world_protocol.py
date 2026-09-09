"""SAE-80 qualification boundary for Evidence + Proof World authority.

This module is intentionally an importable RED interface first.  Task 12 must
qualify an exact Task 11 Proof World only by canonical recomputation from the
same SAE-70 authority, registry, world coordinates, and evidence.  The protocol
does not activate Genesis or alter normal Sergeant verdict authority.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .assurance_contract_registry import ACRRegistry
from .contract_closure import ExpectedObligation
from .contract_closure_protocol import QualifiedContractClosure
from .proof_world import EvidenceProof, ProofWorld, WorldCoordinates
from .review_world import ReviewWorldError


QUALIFIED_EVIDENCE_CONTRACT = "QUALIFIED_EVIDENCE_CONTRACT"
QUALIFIED_PROOF_WORLD = "QUALIFIED_PROOF_WORLD"
QUALIFICATION_PROTOCOL_GENERATION = "sae80-qualification-v1"
_PROTOCOL_IDS = (QUALIFIED_EVIDENCE_CONTRACT, QUALIFIED_PROOF_WORLD)


class ProofWorldQualificationError(ReviewWorldError):
    """Raised when SAE-80 qualification authority cannot be issued."""


@dataclass(frozen=True)
class QualifiedProofWorld:
    schema_version: str
    protocol_ids: tuple[str, str]
    qualification_protocol_generation: str
    qualified_closure_id: str
    registry_id: str
    obligation_id: str
    world_id: str
    source_input_set_id: str
    proof_world_id: str
    evidence_ids: tuple[str, ...]
    material_input_ids: tuple[str, ...]
    qualification_id: str


def validate_qualified_proof_world(value: QualifiedProofWorld) -> QualifiedProofWorld:
    """Revalidate one persisted/in-memory SAE-80 qualification record."""
    raise NotImplementedError("SAE-80 Task 12 qualification validation is RED")


def qualify_proof_world(
    *,
    qualified_closure: QualifiedContractClosure,
    expected_obligation: ExpectedObligation,
    registry: ACRRegistry,
    world: WorldCoordinates,
    evidence: Sequence[EvidenceProof],
    result: ProofWorld,
) -> QualifiedProofWorld:
    """Qualify only a canonically reproduced exact Task 11 Proof World."""
    raise NotImplementedError("SAE-80 Task 12 qualification is RED")
