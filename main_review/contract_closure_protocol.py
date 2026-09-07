"""SAE-70 qualification authority for total contract / instance / obligation closure.

The historical SAE-70 candidate compiler remains a measurement/construction
mechanism.  Qualified authority is narrower: a supplied result must be EXACT,
blocker-free, and byte-for-byte equivalent at the dataclass level to a fresh
canonical recomputation from the exact registry, applicability contexts,
instance enumerations, and PROVEN_NO_MATCH proofs presented to this protocol.

This module does not activate Genesis and does not alter normal Sergeant verdict
authority.  Lifecycle authority for the two protocol IDs exists only after the
separate SAE-70 PROVEN closeout is guarded-merged.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .assurance_contract_registry import ACRRegistry, ApplicabilityContext, ClosureGrade
from .contract_closure import (
    ContractClosureError,
    ContractClosureResult,
    ContractInstanceEnumeration,
    ProvenNoMatch,
    compile_contract_closure,
)
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


QUALIFIED_CONTRACT_INSTANCE_CLOSURE = "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"
QUALIFIED_EXPECTED_OBLIGATION_COMPILER = "QUALIFIED_EXPECTED_OBLIGATION_COMPILER"
QUALIFICATION_PROTOCOL_GENERATION = "sae70-qualification-v1"
_PROTOCOL_IDS = (
    QUALIFIED_CONTRACT_INSTANCE_CLOSURE,
    QUALIFIED_EXPECTED_OBLIGATION_COMPILER,
)


def _require_sha(value: str, field: str) -> str:
    try:
        return require_full_sha256(value, field)
    except ReviewWorldError as exc:
        raise ContractClosureError(str(exc)) from exc


def _context_payload(context: ApplicabilityContext) -> dict[str, object]:
    if not isinstance(context, ApplicabilityContext):
        raise ContractClosureError("qualification applicability context must be ApplicabilityContext")
    if not isinstance(context.closure, ClosureGrade):
        raise ContractClosureError("qualification applicability context closure is invalid")
    return {"facts": dict(context.facts), "closure": context.closure.value}


def _source_input_set_id(
    *,
    registry: ACRRegistry,
    contexts: Mapping[str, ApplicabilityContext],
    instance_enumerations: Mapping[str, ContractInstanceEnumeration],
    proven_no_match: Mapping[str, ProvenNoMatch],
) -> str:
    return sha256_id(
        {
            "schema_version": "sergeant.sae70-qualification-input-set.v1",
            "registry_id": registry.registry_id,
            "contexts": {
                key: _context_payload(value) for key, value in sorted(contexts.items())
            },
            "instance_enumerations": {
                key: value.enumeration_id for key, value in sorted(instance_enumerations.items())
            },
            "proven_no_match": {
                key: value.proof_id for key, value in sorted(proven_no_match.items())
            },
        }
    )


def _qualification_body(
    *,
    registry_id: str,
    source_input_set_id: str,
    contract_closure_result_id: str,
    expected_instance_ids: tuple[str, ...],
    expected_obligation_ids: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.qualified-contract-closure.v1",
        "protocol_ids": list(_PROTOCOL_IDS),
        "qualification_protocol_generation": QUALIFICATION_PROTOCOL_GENERATION,
        "registry_id": registry_id,
        "source_input_set_id": source_input_set_id,
        "contract_closure_result_id": contract_closure_result_id,
        "expected_instance_ids": list(expected_instance_ids),
        "expected_obligation_ids": list(expected_obligation_ids),
    }


@dataclass(frozen=True)
class QualifiedContractClosure:
    schema_version: str
    protocol_ids: tuple[str, str]
    qualification_protocol_generation: str
    registry_id: str
    source_input_set_id: str
    contract_closure_result_id: str
    expected_instance_ids: tuple[str, ...]
    expected_obligation_ids: tuple[str, ...]
    qualification_id: str


def validate_qualified_contract_closure(
    value: QualifiedContractClosure,
) -> QualifiedContractClosure:
    """Revalidate a persisted/in-memory SAE-70 qualification record."""
    if not isinstance(value, QualifiedContractClosure):
        raise ContractClosureError("qualified SAE-70 authority has invalid record type")
    if value.schema_version != "sergeant.qualified-contract-closure.v1":
        raise ContractClosureError("unknown qualified SAE-70 authority schema")
    if value.protocol_ids != _PROTOCOL_IDS:
        raise ContractClosureError("qualified SAE-70 protocol identity mismatch")
    if value.qualification_protocol_generation != QUALIFICATION_PROTOCOL_GENERATION:
        raise ContractClosureError("qualified SAE-70 protocol generation mismatch")

    _require_sha(value.registry_id, "qualified SAE-70 registry_id")
    _require_sha(value.source_input_set_id, "qualified SAE-70 source_input_set_id")
    _require_sha(value.contract_closure_result_id, "qualified SAE-70 contract_closure_result_id")
    for identifier in value.expected_instance_ids:
        _require_sha(identifier, "qualified SAE-70 expected instance id")
    for identifier in value.expected_obligation_ids:
        _require_sha(identifier, "qualified SAE-70 expected obligation id")
    if len(set(value.expected_instance_ids)) != len(value.expected_instance_ids):
        raise ContractClosureError("qualified SAE-70 expected instance IDs contain duplicates")
    if len(set(value.expected_obligation_ids)) != len(value.expected_obligation_ids):
        raise ContractClosureError("qualified SAE-70 expected obligation IDs contain duplicates")

    expected = sha256_id(
        _qualification_body(
            registry_id=value.registry_id,
            source_input_set_id=value.source_input_set_id,
            contract_closure_result_id=value.contract_closure_result_id,
            expected_instance_ids=value.expected_instance_ids,
            expected_obligation_ids=value.expected_obligation_ids,
        )
    )
    if value.qualification_id != expected:
        raise ContractClosureError("qualified SAE-70 qualification identity mismatch")
    return value


def qualify_contract_closure(
    *,
    registry: ACRRegistry,
    contexts: Mapping[str, ApplicabilityContext],
    instance_enumerations: Mapping[str, ContractInstanceEnumeration],
    proven_no_match: Mapping[str, ProvenNoMatch],
    result: ContractClosureResult,
) -> QualifiedContractClosure:
    """Admit exactly one canonically reproduced SAE-70 closure result.

    Qualification is intentionally not a trust-on-ID operation. The candidate
    result is recomputed from the exact authority inputs and must compare equal
    in full before either SAE-70 qualified protocol ID can be issued.
    """
    if not isinstance(result, ContractClosureResult):
        raise ContractClosureError("SAE-70 qualification requires ContractClosureResult")

    canonical = compile_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=instance_enumerations,
        proven_no_match=proven_no_match,
    )
    if result != canonical:
        raise ContractClosureError(
            "supplied contract closure result differs from canonical recomputation"
        )
    if canonical.grade is not ClosureGrade.EXACT:
        raise ContractClosureError("SAE-70 qualification requires EXACT contract closure")
    if canonical.blockers:
        raise ContractClosureError("blocked SAE-70 contract closure cannot qualify")

    source_input_set_id = _source_input_set_id(
        registry=registry,
        contexts=contexts,
        instance_enumerations=instance_enumerations,
        proven_no_match=proven_no_match,
    )
    expected_instance_ids = tuple(
        instance.contract_instance_id for instance in canonical.expected_instances
    )
    expected_obligation_ids = tuple(
        obligation.obligation_id for obligation in canonical.expected_obligations
    )
    body = _qualification_body(
        registry_id=canonical.registry_id,
        source_input_set_id=source_input_set_id,
        contract_closure_result_id=canonical.result_id,
        expected_instance_ids=expected_instance_ids,
        expected_obligation_ids=expected_obligation_ids,
    )
    qualified = QualifiedContractClosure(
        schema_version="sergeant.qualified-contract-closure.v1",
        protocol_ids=_PROTOCOL_IDS,
        qualification_protocol_generation=QUALIFICATION_PROTOCOL_GENERATION,
        registry_id=canonical.registry_id,
        source_input_set_id=source_input_set_id,
        contract_closure_result_id=canonical.result_id,
        expected_instance_ids=expected_instance_ids,
        expected_obligation_ids=expected_obligation_ids,
        qualification_id=sha256_id(body),
    )
    return validate_qualified_contract_closure(qualified)
