"""SAE-90 qualification boundary for mandatory falsification authority.

The SAE-90 compiler remains candidate construction.  This protocol issues only
``QUALIFIED_FALSIFICATION_FRONTIER`` after canonical recomputation from the
exact SAE-80 qualified Proof World, SAE-70 obligation, registry, closed
parameter domains, and counter-world evidence.  Lifecycle authority exists
only after the separate SAE-90 PROVEN closeout is guarded-merged.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .assurance_contract_registry import ACRRegistry, ClosureGrade
from .contract_closure import ExpectedObligation
from .falsification_frontier import (
    CounterWorldEvidence, FalsificationFrontier, FalsificationFrontierError,
    FalsifierParameterDomain, compile_falsification_frontier,
)
from .proof_world_protocol import QualifiedProofWorld, validate_qualified_proof_world
from .review_world import ReviewWorldError, require_full_sha256, sha256_id

QUALIFIED_FALSIFICATION_FRONTIER = "QUALIFIED_FALSIFICATION_FRONTIER"
QUALIFICATION_PROTOCOL_GENERATION = "sae90-qualification-v1"

class FalsificationFrontierQualificationError(ReviewWorldError):
    """Raised when SAE-90 qualification authority cannot be issued."""

def _sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise FalsificationFrontierQualificationError(str(exc)) from exc

def _body(*, qualified_proof_world_id: str, registry_id: str, obligation_id: str,
          source_input_set_id: str, frontier_id: str, parameter_domain_ids: tuple[str, ...],
          expected_instance_ids: tuple[str, ...], evidence_ids: tuple[str, ...]) -> dict[str, object]:
    return {
        "schema_version": "sergeant.qualified-falsification-frontier.v1",
        "protocol_id": QUALIFIED_FALSIFICATION_FRONTIER,
        "qualification_protocol_generation": QUALIFICATION_PROTOCOL_GENERATION,
        "qualified_proof_world_id": qualified_proof_world_id,
        "registry_id": registry_id, "obligation_id": obligation_id,
        "source_input_set_id": source_input_set_id, "frontier_id": frontier_id,
        "parameter_domain_ids": list(parameter_domain_ids),
        "expected_instance_ids": list(expected_instance_ids),
        "evidence_ids": list(evidence_ids),
    }

@dataclass(frozen=True)
class QualifiedFalsificationFrontier:
    schema_version: str
    protocol_id: str
    qualification_protocol_generation: str
    qualified_proof_world_id: str
    registry_id: str
    obligation_id: str
    source_input_set_id: str
    frontier_id: str
    parameter_domain_ids: tuple[str, ...]
    expected_instance_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    qualification_id: str

def validate_qualified_falsification_frontier(value: QualifiedFalsificationFrontier) -> QualifiedFalsificationFrontier:
    if not isinstance(value, QualifiedFalsificationFrontier):
        raise FalsificationFrontierQualificationError("qualified SAE-90 authority has invalid record type")
    if value.schema_version != "sergeant.qualified-falsification-frontier.v1":
        raise FalsificationFrontierQualificationError("unknown qualified SAE-90 authority schema")
    if value.protocol_id != QUALIFIED_FALSIFICATION_FRONTIER:
        raise FalsificationFrontierQualificationError("qualified SAE-90 protocol identity mismatch")
    if value.qualification_protocol_generation != QUALIFICATION_PROTOCOL_GENERATION:
        raise FalsificationFrontierQualificationError("qualified SAE-90 protocol generation mismatch")
    for field in ("qualified_proof_world_id", "registry_id", "obligation_id", "source_input_set_id", "frontier_id"):
        _sha(getattr(value, field), f"qualified SAE-90 {field}")
    for name in ("parameter_domain_ids", "expected_instance_ids", "evidence_ids"):
        values = tuple(_sha(x, f"qualified SAE-90 {name}") for x in getattr(value, name))
        if values != tuple(sorted(values)) or len(set(values)) != len(values):
            raise FalsificationFrontierQualificationError(f"qualified SAE-90 {name} are not canonical")
    expected = sha256_id(_body(
        qualified_proof_world_id=value.qualified_proof_world_id, registry_id=value.registry_id,
        obligation_id=value.obligation_id, source_input_set_id=value.source_input_set_id,
        frontier_id=value.frontier_id, parameter_domain_ids=value.parameter_domain_ids,
        expected_instance_ids=value.expected_instance_ids, evidence_ids=value.evidence_ids))
    if value.qualification_id != expected:
        raise FalsificationFrontierQualificationError("qualified SAE-90 qualification identity mismatch")
    return value

def qualify_falsification_frontier(*, qualified_proof_world: QualifiedProofWorld,
        expected_obligation: ExpectedObligation, registry: ACRRegistry,
        parameter_domains: Sequence[FalsifierParameterDomain], evidence: Sequence[CounterWorldEvidence],
        result: FalsificationFrontier) -> QualifiedFalsificationFrontier:
    if not isinstance(result, FalsificationFrontier):
        raise FalsificationFrontierQualificationError("SAE-90 qualification requires FalsificationFrontier")
    try:
        qualified = validate_qualified_proof_world(qualified_proof_world)
        canonical = compile_falsification_frontier(
            qualified_proof_world=qualified, expected_obligation=expected_obligation, registry=registry,
            parameter_domains=parameter_domains, evidence=evidence)
    except (ReviewWorldError, FalsificationFrontierError) as exc:
        raise FalsificationFrontierQualificationError(f"SAE-90 canonical recomputation failed: {exc}") from exc
    if result != canonical:
        raise FalsificationFrontierQualificationError("supplied falsification frontier differs from canonical recomputation")
    if canonical.grade is not ClosureGrade.EXACT:
        raise FalsificationFrontierQualificationError("SAE-90 qualification requires EXACT falsification closure")
    if canonical.blockers:
        raise FalsificationFrontierQualificationError("blocked SAE-90 falsification frontier cannot qualify")
    domain_ids = tuple(sorted(canonical.parameter_domain_ids))
    instance_ids = tuple(sorted(x.instance_id for x in canonical.expected_instances))
    evidence_ids = tuple(sorted(x.evidence_id for x in canonical.evidence))
    source_input_set_id = sha256_id({
        "schema_version": "sergeant.sae90-qualification-input-set.v1",
        "qualified_proof_world_id": qualified.qualification_id, "registry_id": registry.registry_id,
        "obligation_id": canonical.obligation_id, "parameter_domain_ids": list(domain_ids),
        "evidence_ids": list(evidence_ids)})
    body = _body(qualified_proof_world_id=qualified.qualification_id, registry_id=registry.registry_id,
        obligation_id=canonical.obligation_id, source_input_set_id=source_input_set_id,
        frontier_id=canonical.frontier_id, parameter_domain_ids=domain_ids,
        expected_instance_ids=instance_ids, evidence_ids=evidence_ids)
    value = QualifiedFalsificationFrontier(
        "sergeant.qualified-falsification-frontier.v1", QUALIFIED_FALSIFICATION_FRONTIER,
        QUALIFICATION_PROTOCOL_GENERATION, qualified.qualification_id, registry.registry_id,
        canonical.obligation_id, source_input_set_id, canonical.frontier_id, domain_ids, instance_ids,
        evidence_ids, sha256_id(body))
    return validate_qualified_falsification_frontier(value)
