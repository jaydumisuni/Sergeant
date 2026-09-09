"""SAE-80 qualification boundary for Evidence + Proof World authority.

Task 11's Proof World compiler remains a candidate construction mechanism.
Task 12 authority is narrower: a supplied Proof World must be byte-for-byte
equal at the dataclass level to a fresh canonical recomputation from the exact
SAE-70 authority, registry, expected obligation, world coordinates, and
EvidenceProof collection presented to this protocol.  Only an EXACT,
blocker-free recomputation can issue the two SAE-80 qualified protocol IDs.

This module does not activate Genesis and does not alter normal Sergeant verdict
authority.  Lifecycle authority for these IDs exists only after the separate
SAE-80 PROVEN closeout is guarded-merged.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .assurance_contract_registry import ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation
from .contract_closure_protocol import QualifiedContractClosure
from .proof_world import (
    EvidenceProof,
    ProofWorld,
    ProofWorldError,
    WorldCoordinates,
    compile_proof_world,
)
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


QUALIFIED_EVIDENCE_CONTRACT = "QUALIFIED_EVIDENCE_CONTRACT"
QUALIFIED_PROOF_WORLD = "QUALIFIED_PROOF_WORLD"
QUALIFICATION_PROTOCOL_GENERATION = "sae80-qualification-v1"
_PROTOCOL_IDS = (QUALIFIED_EVIDENCE_CONTRACT, QUALIFIED_PROOF_WORLD)


class ProofWorldQualificationError(ReviewWorldError):
    """Raised when SAE-80 qualification authority cannot be issued."""


def _require_sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise ProofWorldQualificationError(str(exc)) from exc


def _source_input_set_id(
    *,
    qualified_closure_id: str,
    registry_id: str,
    obligation_id: str,
    world_id: str,
    evidence_ids: tuple[str, ...],
) -> str:
    return sha256_id(
        {
            "schema_version": "sergeant.sae80-qualification-input-set.v1",
            "qualified_closure_id": qualified_closure_id,
            "registry_id": registry_id,
            "obligation_id": obligation_id,
            "world_id": world_id,
            "evidence_ids": list(evidence_ids),
        }
    )


def _qualification_body(
    *,
    qualified_closure_id: str,
    registry_id: str,
    obligation_id: str,
    world_id: str,
    source_input_set_id: str,
    proof_world_id: str,
    evidence_ids: tuple[str, ...],
    material_input_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.qualified-proof-world.v1",
        "protocol_ids": list(_PROTOCOL_IDS),
        "qualification_protocol_generation": QUALIFICATION_PROTOCOL_GENERATION,
        "qualified_closure_id": qualified_closure_id,
        "registry_id": registry_id,
        "obligation_id": obligation_id,
        "world_id": world_id,
        "source_input_set_id": source_input_set_id,
        "proof_world_id": proof_world_id,
        "evidence_ids": list(evidence_ids),
        "material_input_ids": list(material_input_ids),
    }


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
    if not isinstance(value, QualifiedProofWorld):
        raise ProofWorldQualificationError("qualified SAE-80 authority has invalid record type")
    if value.schema_version != "sergeant.qualified-proof-world.v1":
        raise ProofWorldQualificationError("unknown qualified SAE-80 authority schema")
    if value.protocol_ids != _PROTOCOL_IDS:
        raise ProofWorldQualificationError("qualified SAE-80 protocol identity mismatch")
    if value.qualification_protocol_generation != QUALIFICATION_PROTOCOL_GENERATION:
        raise ProofWorldQualificationError("qualified SAE-80 protocol generation mismatch")

    _require_sha(value.qualified_closure_id, "qualified SAE-80 closure ID")
    _require_sha(value.registry_id, "qualified SAE-80 registry ID")
    _require_sha(value.obligation_id, "qualified SAE-80 obligation ID")
    _require_sha(value.world_id, "qualified SAE-80 world ID")
    _require_sha(value.source_input_set_id, "qualified SAE-80 source input set ID")
    _require_sha(value.proof_world_id, "qualified SAE-80 Proof World ID")

    evidence_ids = tuple(sorted(_require_sha(item, "qualified SAE-80 evidence ID") for item in value.evidence_ids))
    if evidence_ids != value.evidence_ids or len(set(evidence_ids)) != len(evidence_ids):
        raise ProofWorldQualificationError("qualified SAE-80 evidence IDs are not canonical")
    material_input_ids = tuple(
        sorted(_require_sha(item, "qualified SAE-80 material-input ID") for item in value.material_input_ids)
    )
    if material_input_ids != value.material_input_ids or len(set(material_input_ids)) != len(material_input_ids):
        raise ProofWorldQualificationError("qualified SAE-80 material-input IDs are not canonical")

    expected = sha256_id(
        _qualification_body(
            qualified_closure_id=value.qualified_closure_id,
            registry_id=value.registry_id,
            obligation_id=value.obligation_id,
            world_id=value.world_id,
            source_input_set_id=value.source_input_set_id,
            proof_world_id=value.proof_world_id,
            evidence_ids=value.evidence_ids,
            material_input_ids=value.material_input_ids,
        )
    )
    if value.qualification_id != expected:
        raise ProofWorldQualificationError("qualified SAE-80 qualification identity mismatch")
    return value


def qualify_proof_world(
    *,
    qualified_closure: QualifiedContractClosure,
    expected_obligation: ExpectedObligation,
    registry: ACRRegistry,
    world: WorldCoordinates,
    evidence: Sequence[EvidenceProof],
    result: ProofWorld,
) -> QualifiedProofWorld:
    """Admit exactly one canonically reproduced Task 11 Proof World.

    Qualification is intentionally not trust-on-ID.  The candidate is rebuilt
    from the exact authority inputs and must compare equal in full before SAE-80
    qualified authority can be issued.
    """
    if not isinstance(result, ProofWorld):
        raise ProofWorldQualificationError("SAE-80 qualification requires ProofWorld")

    try:
        canonical = compile_proof_world(
            qualified_closure=qualified_closure,
            expected_obligation=expected_obligation,
            registry=registry,
            world=world,
            evidence=evidence,
        )
    except ProofWorldError as exc:
        raise ProofWorldQualificationError(
            f"SAE-80 canonical recomputation failed: {exc}"
        ) from exc

    if result != canonical:
        raise ProofWorldQualificationError(
            "supplied Proof World differs from canonical recomputation"
        )
    if canonical.grade is not ClosureGrade.EXACT:
        raise ProofWorldQualificationError("SAE-80 qualification requires EXACT Proof World closure")
    if canonical.blockers:
        raise ProofWorldQualificationError("blocked SAE-80 Proof World cannot qualify")

    evidence_ids = tuple(item.evidence_id for item in canonical.evidence)
    material_input_ids = tuple(item.material_input_id for item in canonical.material_inputs)
    source_input_set_id = _source_input_set_id(
        qualified_closure_id=canonical.qualified_closure_id,
        registry_id=registry.registry_id,
        obligation_id=canonical.obligation_id,
        world_id=canonical.world_id,
        evidence_ids=evidence_ids,
    )
    body = _qualification_body(
        qualified_closure_id=canonical.qualified_closure_id,
        registry_id=registry.registry_id,
        obligation_id=canonical.obligation_id,
        world_id=canonical.world_id,
        source_input_set_id=source_input_set_id,
        proof_world_id=canonical.proof_world_id,
        evidence_ids=evidence_ids,
        material_input_ids=material_input_ids,
    )
    qualified = QualifiedProofWorld(
        schema_version="sergeant.qualified-proof-world.v1",
        protocol_ids=_PROTOCOL_IDS,
        qualification_protocol_generation=QUALIFICATION_PROTOCOL_GENERATION,
        qualified_closure_id=canonical.qualified_closure_id,
        registry_id=registry.registry_id,
        obligation_id=canonical.obligation_id,
        world_id=canonical.world_id,
        source_input_set_id=source_input_set_id,
        proof_world_id=canonical.proof_world_id,
        evidence_ids=evidence_ids,
        material_input_ids=material_input_ids,
        qualification_id=sha256_id(body),
    )
    return validate_qualified_proof_world(qualified)
