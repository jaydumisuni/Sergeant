"""SAE-60 qualification authority for the first bounded semantic capability.

The candidate analyzer can measure candidate passports from multiple generations.
Qualification authority is narrower: only the exact frozen SAE-60 generation,
domain, ceilings and lineages may cross this protocol.  Historical or future
candidate measurements therefore cannot inherit qualified authority by replay.
"""
from __future__ import annotations

from dataclasses import dataclass

from .assurance_contract_registry import BoundedDomain, ClosureGrade
from .capability_qualification import CapabilityPassport, SemanticCapabilityEvaluation
from .review_world import ReviewWorldError, sha256_id


class SemanticCapabilityProtocolError(ReviewWorldError):
    """Raised when candidate semantic evidence is outside qualified SAE-60 authority."""


PROTOCOL_ID = "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"
BOUNDED_CAPABILITY_ID = "python.bounded-literal-dispatch.v1"
DOMAIN_GENERATION = "domain-gen-1"
ARTIFACT_GENERATION = "sae60-candidate-gen-1"
PARSER_GENERATION = "cpython-ast-3.11-v1"
FRAMEWORK_GENERATION = "python-language-3.11"
QUALIFICATION_PROTOCOL_GENERATION = "sae60-qualification-v1"
PROOF_CEILING = "BOUNDED_EXHAUSTIVE_ORACLE"
IMPLEMENTATION_LINEAGE_ID = sha256_id({"implementation": "sae60-python-ast-bounded-dispatch-v1"})
PARSER_LINEAGE_ID = sha256_id({"parser": "cpython-ast", "generation": "3.11-v1"})
FRAMEWORK_LINEAGE_ID = sha256_id({"framework": "python-language-semantics", "generation": "3.11"})
COMMON_MODE_LINEAGE_ID = sha256_id({"common_mode": "production-static-analyzer-control-v1"})
CONTROL_LINEAGE_ID = sha256_id({"control": "sae60-candidate-authoring-v1"})
DOMAIN_DIMENSIONS = {
    "max_source_bytes": 20_000,
    "max_ast_nodes": 500,
    "max_dispatch_tables": 8,
    "max_table_entries": 32,
}


def qualified_domain() -> BoundedDomain:
    return BoundedDomain.create(
        domain_id=BOUNDED_CAPABILITY_ID,
        generation=DOMAIN_GENERATION,
        dimensions=DOMAIN_DIMENSIONS,
    )


@dataclass(frozen=True)
class QualifiedSemanticCapability:
    schema_version: str
    protocol_id: str
    capability_id: str
    domain_hash: str
    passport_id: str
    evaluation_id: str
    qualification_id: str


def _require_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise SemanticCapabilityProtocolError(
            f"{field} is outside the exact SAE-60 qualified generation"
        )


def qualify_bounded_literal_dispatch(
    *,
    passport: CapabilityPassport,
    evaluation: SemanticCapabilityEvaluation,
) -> QualifiedSemanticCapability:
    """Admit one exact candidate evaluation into SAE-60 qualified authority.

    This function grants only the bounded capability named by
    ``BOUNDED_CAPABILITY_ID``. It does not modify normal Sergeant verdict
    authority and does not activate Genesis.
    """
    if not isinstance(passport, CapabilityPassport):
        raise SemanticCapabilityProtocolError("qualified semantic capability requires CapabilityPassport")
    if not isinstance(evaluation, SemanticCapabilityEvaluation):
        raise SemanticCapabilityProtocolError(
            "qualified semantic capability requires SemanticCapabilityEvaluation"
        )

    integrity = passport.integrity_error()
    if integrity:
        raise SemanticCapabilityProtocolError(integrity)

    domain = qualified_domain()
    _require_equal(passport.domain, domain, "domain identity/generation/resource ceiling")
    _require_equal(passport.capability_name, "python-bounded-literal-dispatch", "capability name")
    _require_equal(passport.artifact_generation, ARTIFACT_GENERATION, "artifact generation")
    _require_equal(passport.parser_generation, PARSER_GENERATION, "parser generation")
    _require_equal(passport.framework_generation, FRAMEWORK_GENERATION, "framework generation")
    _require_equal(
        passport.qualification_protocol_generation,
        QUALIFICATION_PROTOCOL_GENERATION,
        "qualification protocol generation",
    )
    _require_equal(passport.proof_ceiling, PROOF_CEILING, "proof ceiling")
    _require_equal(passport.closure_ceiling, ClosureGrade.EXACT, "closure ceiling")
    _require_equal(passport.implementation_lineage_id, IMPLEMENTATION_LINEAGE_ID, "implementation lineage")
    _require_equal(passport.parser_lineage_id, PARSER_LINEAGE_ID, "parser lineage")
    _require_equal(passport.framework_lineage_id, FRAMEWORK_LINEAGE_ID, "framework lineage")
    _require_equal(passport.common_mode_lineage_id, COMMON_MODE_LINEAGE_ID, "common-mode lineage")
    _require_equal(passport.control_lineage_id, CONTROL_LINEAGE_ID, "control lineage")

    _require_equal(evaluation.passport_id, passport.passport_id, "evaluation passport binding")
    if evaluation.grade is not ClosureGrade.EXACT:
        raise SemanticCapabilityProtocolError("only EXACT bounded semantic evidence can qualify")
    if evaluation.blockers:
        raise SemanticCapabilityProtocolError("blocked semantic evidence cannot qualify")
    if evaluation.resource_exhausted:
        raise SemanticCapabilityProtocolError("resource-exhausted semantic evidence cannot qualify")

    body = {
        "schema_version": "sergeant.qualified-semantic-capability.v1",
        "protocol_id": PROTOCOL_ID,
        "capability_id": BOUNDED_CAPABILITY_ID,
        "domain_hash": domain.domain_hash,
        "passport_id": passport.passport_id,
        "evaluation_id": evaluation.evaluation_id,
    }
    return QualifiedSemanticCapability(
        schema_version=body["schema_version"],
        protocol_id=PROTOCOL_ID,
        capability_id=BOUNDED_CAPABILITY_ID,
        domain_hash=domain.domain_hash,
        passport_id=passport.passport_id,
        evaluation_id=evaluation.evaluation_id,
        qualification_id=sha256_id(body),
    )
