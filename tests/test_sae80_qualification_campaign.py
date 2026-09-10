from __future__ import annotations

from dataclasses import replace
from pathlib import Path

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
    Assumption,
    AssumptionKind,
    EvidenceProof,
    MaterialInputProof,
    ProofClass,
    WorldCoordinates,
    compile_proof_world,
)
from main_review.proof_world_protocol import (
    QUALIFIED_EVIDENCE_CONTRACT,
    QUALIFIED_PROOF_WORLD,
    ProofWorldQualificationError,
    qualify_proof_world,
    validate_qualified_proof_world,
)
from main_review.review_world import sha256_id

from tests.sae80_authority_fixtures import (
    authority_fixture as rooted_authority_fixture,
    evidence as rooted_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


def contract() -> ACRContract:
    return ACRContract.create(
        contract_id="sae80-qualified-authz",
        generation="sae80-qualification-contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.sae80-qualification.v1",
            generation="sae80-qualification-domain-gen-1",
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
                "routes",
                CollectionSemantics.SET,
                CardinalitySpec.bounded_n(8),
                ClosureGrade.EXACT,
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


def world(*, candidate: str = "candidate-gen-1", epoch: int = 42) -> WorldCoordinates:
    return WorldCoordinates.create(
        candidate_generation=candidate,
        framework_generation="flask-gen-4",
        provider_generation="provider-gen-9",
        dependency_generations={"authz-lib": "authz-gen-12"},
        epoch=epoch,
    )


def fixture():
    c = contract()
    registry = ACRRegistry.create(
        generation="sae80-qualification-acr-gen-1",
        contracts=(c,),
    )
    contexts = {
        c.contract_id: ApplicabilityContext.exact(
            {"language": "python", "framework": "flask"}
        )
    }
    enumerations = {
        c.contract_id: ContractInstanceEnumeration.create(
            contract=c,
            bindings=({"route": "/admin"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"sae80-qualification-instance": "/admin"}),
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
    obligation = closure.expected_obligations[0]
    return registry, qualified, obligation


def material() -> MaterialInputProof:
    return MaterialInputProof.create(
        family="router-config",
        closure=ClosureGrade.EXACT,
        basis_id=sha256_id({"sae80-material": "router-config", "generation": 1}),
    )


def evidence(
    obligation,
    coordinates: WorldCoordinates,
    world_authority,
    *,
    proof_class: ProofClass = ProofClass.MECHANICAL,
    claimed_closure: ClosureGrade = ClosureGrade.EXACT,
    observed_epoch: int | None = None,
    claims: dict[str, object] | None = None,
    assumptions: tuple[Assumption, ...] = (),
) -> EvidenceProof:
    return rooted_evidence(
        obligation,
        coordinates,
        world_authority,
        proof_class=proof_class,
        claimed_closure=claimed_closure,
        materials=("router-config",),
        claims=claims,
        assumptions=assumptions,
        epoch=observed_epoch,
    )


def canonical_fixture():
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry)
    proof_evidence = (evidence(obligation, coordinates, authority),)
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=proof_evidence,
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.EXACT
    assert result.blockers == ()
    return registry, qualified, obligation, coordinates, proof_evidence, result, authority


def qualify(parts):
    registry, qualified, obligation, coordinates, proof_evidence, result, authority = parts
    return qualify_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=proof_evidence,
        world_authority=authority,
        result=result,
    )


def test_exact_canonical_proof_world_crosses_qualification_boundary() -> None:
    parts = canonical_fixture()
    qualified_world = qualify(parts)

    assert qualified_world.protocol_ids == (
        QUALIFIED_EVIDENCE_CONTRACT,
        QUALIFIED_PROOF_WORLD,
    )
    assert qualified_world.qualified_closure_id == parts[1].qualification_id
    assert qualified_world.registry_id == parts[0].registry_id
    assert qualified_world.obligation_id == parts[2].obligation_id
    assert qualified_world.world_id == parts[3].world_id
    assert qualified_world.proof_world_id == parts[5].proof_world_id
    assert qualified_world.evidence_ids == tuple(item.evidence_id for item in parts[4])
    assert len(qualified_world.qualification_id) == 64


def test_supplied_proof_world_must_equal_fresh_canonical_recomputation() -> None:
    parts = canonical_fixture()
    forged = replace(parts[5], grade=ClosureGrade.UNKNOWN)
    with pytest.raises(ProofWorldQualificationError, match="canonical recomputation"):
        qualify_proof_world(
            qualified_closure=parts[1],
            expected_obligation=parts[2],
            registry=parts[0],
            world=parts[3],
            evidence=parts[4],
            world_authority=parts[6],
            result=forged,
        )


def test_missing_evidence_never_qualifies_as_exact_proof_world() -> None:
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry)
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=(),
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.UNKNOWN
    with pytest.raises(ProofWorldQualificationError, match="EXACT|blocked"):
        qualify_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=coordinates,
            evidence=(),
            world_authority=authority,
            result=result,
        )


def test_historical_proof_world_cannot_replay_against_another_world_generation() -> None:
    parts = canonical_fixture()
    changed_world = WorldCoordinates.create(
        candidate_generation="candidate-gen-2",
        framework_generation=parts[3].framework_generation,
        provider_generation=parts[3].provider_generation,
        dependency_generations=dict(parts[3].dependency_generations),
        epoch=parts[3].epoch,
    )
    with pytest.raises(ProofWorldQualificationError, match="canonical|world|generation"):
        qualify_proof_world(
            qualified_closure=parts[1],
            expected_obligation=parts[2],
            registry=parts[0],
            world=changed_world,
            evidence=parts[4],
            world_authority=parts[6],
            result=parts[5],
        )


def test_heuristic_only_world_cannot_cross_exact_qualification_boundary() -> None:
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry)
    heuristic = (
        evidence(
            obligation,
            coordinates,
            authority,
            proof_class=ProofClass.HEURISTIC,
            claimed_closure=ClosureGrade.CONSERVATIVE_SUPERSET,
        ),
    )
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=heuristic,
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.CONSERVATIVE_SUPERSET
    with pytest.raises(ProofWorldQualificationError, match="EXACT"):
        qualify_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=coordinates,
            evidence=heuristic,
            world_authority=authority,
            result=result,
        )


def test_stale_evidence_cannot_cross_exact_qualification_boundary() -> None:
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry, epoch=42)
    stale = (evidence(obligation, coordinates, authority, observed_epoch=41),)
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=stale,
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.UNKNOWN
    with pytest.raises(ProofWorldQualificationError, match="EXACT|blocked"):
        qualify_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=coordinates,
            evidence=stale,
            world_authority=authority,
            result=result,
        )


def test_unresolved_assumption_cannot_cross_exact_qualification_boundary() -> None:
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry)
    unresolved = Assumption.create(
        assumption_id="external-policy-completeness",
        kind=AssumptionKind.UNRESOLVED,
        basis_id=sha256_id({"assumption": "external-policy-completeness"}),
    )
    proof_evidence = (evidence(obligation, coordinates, authority, assumptions=(unresolved,)),)
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=proof_evidence,
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.UNKNOWN
    with pytest.raises(ProofWorldQualificationError, match="EXACT|blocked"):
        qualify_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=coordinates,
            evidence=proof_evidence,
            world_authority=authority,
            result=result,
        )


def test_contradictory_world_cannot_cross_exact_qualification_boundary() -> None:
    registry, qualified, obligation = fixture()
    authority, coordinates = rooted_authority_fixture(qualified, registry)
    proof_evidence = (
        evidence(obligation, coordinates, authority, claims={"authz:/admin": "preserved"}),
        evidence(obligation, coordinates, authority, claims={"authz:/admin": "removed"}),
    )
    result = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=coordinates,
        evidence=proof_evidence,
        world_authority=authority,
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert result.contradictions
    with pytest.raises(ProofWorldQualificationError, match="EXACT|blocked"):
        qualify_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=coordinates,
            evidence=proof_evidence,
            world_authority=authority,
            result=result,
        )


def test_forged_candidate_identity_cannot_cross_qualification_boundary() -> None:
    parts = canonical_fixture()
    forged = replace(parts[5], proof_world_id="0" * 64)
    with pytest.raises(ProofWorldQualificationError, match="canonical recomputation"):
        qualify_proof_world(
            qualified_closure=parts[1],
            expected_obligation=parts[2],
            registry=parts[0],
            world=parts[3],
            evidence=parts[4],
            world_authority=parts[6],
            result=forged,
        )


def test_qualified_record_is_content_addressed_and_not_self_mutable() -> None:
    qualified_world = qualify(canonical_fixture())
    forged = replace(qualified_world, qualification_id="0" * 64)
    with pytest.raises(ProofWorldQualificationError, match="qualification identity"):
        validate_qualified_proof_world(forged)
    assert validate_qualified_proof_world(qualified_world) == qualified_world


def test_task11_candidate_never_self_claims_task12_authority() -> None:
    text = (ROOT / "docs/111-sae80-evidence-proof-world-candidate-manifest.json").read_text(
        encoding="utf-8"
    )
    assert '"produces_now": []' in text
    assert '"normal_verdict_authority": false' in text
    assert '"genesis_activated": false' in text
    assert "QUALIFIED_EVIDENCE_CONTRACT" in text
    assert "QUALIFIED_PROOF_WORLD" in text
