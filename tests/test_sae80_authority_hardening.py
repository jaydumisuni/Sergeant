from __future__ import annotations

from dataclasses import replace

import pytest

from main_review.assurance_contract_registry import (
    ACRContract,
    ACRRegistry,
    ApplicabilityContext,
    ApplicabilityPredicate,
    BoundedDomain,
    CardinalitySpec,
    ClosureGrade,
    CollectionRequirement,
    CollectionSemantics,
    ContractRequirement,
    ExternalReviewLane,
    NegativeApplicabilityBurden,
)
from main_review.contract_closure import ContractInstanceEnumeration, compile_contract_closure
from main_review.contract_closure_protocol import qualify_contract_closure
from main_review.proof_world import (
    EvidenceProof,
    MaterialInputProof,
    ProofClass,
    ProofWorldError,
    WorldCoordinates,
    compile_proof_world,
)
from main_review.review_world import sha256_id
from tests.sae80_authority_fixtures import authority_fixture


def _fixture():
    contract = ACRContract.create(
        contract_id="sae80-authority-hardening",
        generation="sae80-authority-contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.sae80-authority-hardening.v1",
            generation="sae80-authority-domain-gen-1",
            dimensions={"max_routes": 8, "max_material_inputs": 4},
        ),
        applicability=ApplicabilityPredicate.all_of(
            ApplicabilityPredicate.fact_equals("language", "python"),
            ApplicabilityPredicate.fact_equals("framework", "flask"),
        ),
        bound_subject_variables=("route",),
        semantic_carrier_families=("routes",),
        consumer_interpretation_families=("router",),
        affected_relation_families=("route_to_handler",),
        collections=(
            CollectionRequirement.create(
                "routes", CollectionSemantics.SET, CardinalitySpec.bounded_n(8), ClosureGrade.EXACT
            ),
        ),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create("authz-preserved", ClosureGrade.EXACT),),
        admissible_proof_classes=("mechanical", "heuristic"),
        material_inputs=(ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        coherence_rules=(
            "same-candidate-generation",
            "same-framework-generation",
            "same-provider-generation",
            "same-dependency-generation",
        ),
        temporal_rules=("evidence-not-older-than-world",),
        mandatory_falsifier_families=("delete-policy",),
        required_independence=("qualification-corpus-independent",),
        permitted_capabilities=("python.bounded-literal-dispatch.v1",),
        negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),
        external_review_lanes=(ExternalReviewLane.create("hostile-external", 1),),
        unsupported_fallback="UNKNOWN",
    )
    registry = ACRRegistry.create(generation="sae80-authority-acr-gen-1", contracts=(contract,))
    contexts = {
        contract.contract_id: ApplicabilityContext.exact(
            {"language": "python", "framework": "flask"}
        )
    }
    enumerations = {
        contract.contract_id: ContractInstanceEnumeration.create(
            contract=contract,
            bindings=({"route": "/admin"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"sae80-authority-instance": "/admin"}),
        )
    }
    closure = compile_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
    )
    qualified = qualify_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
        result=closure,
    )
    return registry, qualified, closure.expected_obligations[0]


def _raw_world(*, provider: str = "provider-gen-7") -> WorldCoordinates:
    return WorldCoordinates.create(
        candidate_generation="candidate-gen-1",
        framework_generation="flask-gen-3",
        provider_generation=provider,
        dependency_generations={"authorization-library": "generation-11"},
        epoch=42,
    )


def _material() -> MaterialInputProof:
    return MaterialInputProof.create(
        family="router-config",
        closure=ClosureGrade.EXACT,
        basis_id=sha256_id({"sae80-authority-material": "router-config"}),
    )


def _raw_mechanical_evidence(obligation, world: WorldCoordinates) -> EvidenceProof:
    return EvidenceProof.create(
        proof_class=ProofClass.MECHANICAL,
        claimed_closure=ClosureGrade.EXACT,
        obligation_id=obligation.obligation_id,
        contract_instance_ids=tuple(origin.contract_instance_id for origin in obligation.provenance),
        world=world,
        material_inputs=(_material(),),
        claims={"authz:/admin": "preserved"},
        assumptions=(),
        observed_epoch=world.epoch,
        evidence_basis_id=sha256_id({"sae80-authority-evidence": obligation.obligation_id}),
    )


def _proof_world_id(proof) -> str:
    return sha256_id(
        {
            "schema_version": "sergeant.sae80-proof-world.v2",
            "basis_id": proof.basis.basis_id,
            "qualified_closure_id": proof.qualified_closure_id,
            "obligation_id": proof.obligation_id,
            "world_id": proof.world_id,
            "grade": proof.grade.value,
            "material_input_ids": [item.material_input_id for item in proof.material_inputs],
            "evidence_ids": [item.evidence_id for item in proof.evidence],
            "assumption_record_ids": [item.record_id for item in proof.assumptions],
            "contradiction_ids": [item.contradiction_id for item in proof.contradictions],
            "blockers": list(proof.blockers),
        }
    )


def test_public_validation_rejects_semantically_forged_stronger_world_even_with_rehashed_id() -> None:
    registry, qualified, obligation = _fixture()
    authority, world = authority_fixture(qualified, registry)
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    forged = replace(proof, grade=ClosureGrade.EXACT, blockers=(), proof_world_id="")
    forged = replace(forged, proof_world_id=_proof_world_id(forged))
    with pytest.raises(ProofWorldError, match="authority|semantic|recomput"):
        forged.validate()


def test_free_form_world_coordinates_cannot_supply_proof_world_authority() -> None:
    registry, qualified, obligation = _fixture()
    world = _raw_world()
    with pytest.raises(ProofWorldError, match="qualified|Review World|authority"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=world,
            evidence=(),
        )


def test_caller_cannot_self_label_mechanical_evidence_without_qualified_proof_authority() -> None:
    _, _, obligation = _fixture()
    world = _raw_world()
    with pytest.raises(ProofWorldError, match="mechanical|qualified|authority"):
        _raw_mechanical_evidence(obligation, world)
