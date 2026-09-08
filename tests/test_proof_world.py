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
from main_review.contract_closure import (
    ContractInstanceEnumeration,
    ExpectedObligation,
    compile_contract_closure,
)
from main_review.contract_closure_protocol import qualify_contract_closure
from main_review.proof_world import (
    Assumption,
    AssumptionKind,
    EvidenceProof,
    MaterialInputProof,
    ProofClass,
    ProofWorldError,
    WorldCoordinates,
    compile_proof_world,
)
from main_review.review_world import sha256_id


DEFAULT_PROOF_CLASSES = ("mechanical", "exhaustive-oracle", "heuristic")


def contract(
    contract_id: str,
    *,
    obligation: str = "authz-preserved",
    material_inputs: tuple[str, ...] = ("router-config", "policy-file"),
    proof_classes: tuple[str, ...] = DEFAULT_PROOF_CLASSES,
) -> ACRContract:
    return ACRContract.create(
        contract_id=contract_id,
        generation="sae80-contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.sae80-proof-world.v1",
            generation="sae80-domain-gen-1",
            dimensions={"max_routes": 16, "max_material_inputs": 8},
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
                CardinalitySpec.bounded_n(16),
                ClosureGrade.EXACT,
            ),
        ),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create(obligation, ClosureGrade.EXACT),),
        admissible_proof_classes=proof_classes,
        material_inputs=tuple(
            ContractRequirement.create(name, ClosureGrade.EXACT) for name in material_inputs
        ),
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


def coordinates(
    *,
    candidate: str = "candidate-gen-1",
    framework: str = "flask-gen-3",
    provider: str = "provider-gen-7",
    dependency: str = "authz-lib-gen-11",
    epoch: int = 42,
) -> WorldCoordinates:
    return WorldCoordinates.create(
        candidate_generation=candidate,
        framework_generation=framework,
        provider_generation=provider,
        dependency_generations={"authz-lib": dependency},
        epoch=epoch,
    )


def qualified_fixture(
    *,
    overlapping: bool = False,
    proof_classes: tuple[str, ...] = DEFAULT_PROOF_CLASSES,
):
    first = contract("primary-authz", proof_classes=proof_classes)
    contracts = [first]
    if overlapping:
        contracts.append(
            contract(
                "secondary-authz",
                material_inputs=("policy-file", "audit-schema"),
                proof_classes=proof_classes,
            )
        )
    registry = ACRRegistry.create(generation="sae80-acr-gen-1", contracts=tuple(contracts))
    contexts = {
        item.contract_id: ApplicabilityContext.exact({"language": "python", "framework": "flask"})
        for item in contracts
    }
    enumerations = {
        item.contract_id: ContractInstanceEnumeration.create(
            contract=item,
            bindings=({"route": "/admin"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"sae80-instance-basis": item.contract_id}),
        )
        for item in contracts
    }
    closure = compile_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
    )
    assert closure.grade is ClosureGrade.EXACT
    assert len(closure.expected_obligations) == 1
    qualified = qualify_contract_closure(
        registry=registry,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
        result=closure,
    )
    return qualified, closure.expected_obligations[0], registry


def material(name: str, *, closure: ClosureGrade = ClosureGrade.EXACT) -> MaterialInputProof:
    return MaterialInputProof.create(
        family=name,
        closure=closure,
        basis_id=sha256_id({"material-input": name, "generation": 1}),
    )


def evidence(
    obligation: ExpectedObligation,
    world: WorldCoordinates,
    *,
    proof_class: ProofClass = ProofClass.MECHANICAL,
    claimed_closure: ClosureGrade = ClosureGrade.EXACT,
    materials: tuple[str, ...] = ("router-config", "policy-file"),
    claims: dict[str, object] | None = None,
    assumptions: tuple[Assumption, ...] = (),
    epoch: int | None = None,
) -> EvidenceProof:
    return EvidenceProof.create(
        proof_class=proof_class,
        claimed_closure=claimed_closure,
        obligation_id=obligation.obligation_id,
        contract_instance_ids=tuple(
            origin.contract_instance_id for origin in obligation.provenance
        ),
        world=world,
        material_inputs=tuple(material(name) for name in materials),
        claims=claims or {"authz:/admin": "preserved"},
        assumptions=assumptions,
        observed_epoch=world.epoch if epoch is None else epoch,
        evidence_basis_id=sha256_id(
            {
                "evidence": obligation.obligation_id,
                "proof_class": proof_class.value,
                "epoch": world.epoch if epoch is None else epoch,
                "materials": list(materials),
                "claims": claims or {"authz:/admin": "preserved"},
            }
        ),
    )


def test_exact_evidence_world_binds_sae70_authority_obligation_and_material_inputs() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates()
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(evidence(obligation, world),),
    )

    assert proof.grade is ClosureGrade.EXACT
    assert proof.blockers == ()
    assert proof.qualified_closure_id == qualified.qualification_id
    assert proof.obligation_id == obligation.obligation_id
    assert proof.world_id == world.world_id
    assert {item.family for item in proof.material_inputs} == {"router-config", "policy-file"}
    assert proof.contradictions == ()
    assert len(proof.proof_world_id) == 64


def test_registry_content_is_bound_to_sae70_qualification() -> None:
    qualified, obligation, registry = qualified_fixture()
    original = registry.contracts[0]
    mutated = ACRContract.create(
        **{
            **original.constructor_fields(),
            "material_inputs": (ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        }
    )
    forged_registry = ACRRegistry.create(generation=registry.generation, contracts=(mutated,))
    assert forged_registry.registry_id != qualified.registry_id
    world = coordinates()
    with pytest.raises(ProofWorldError, match="registry|SAE-70"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=forged_registry,
            world=world,
            evidence=(evidence(obligation, world, materials=("router-config",)),),
        )


def test_overlapping_origins_require_conservative_union_of_material_inputs() -> None:
    qualified, obligation, registry = qualified_fixture(overlapping=True)
    world = coordinates()
    complete = evidence(
        obligation,
        world,
        materials=("router-config", "policy-file", "audit-schema"),
    )
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(complete,),
    )
    assert proof.grade is ClosureGrade.EXACT
    assert {item.family for item in proof.material_inputs} == {
        "router-config",
        "policy-file",
        "audit-schema",
    }


def test_omitted_material_input_prevents_exact_closure() -> None:
    qualified, obligation, registry = qualified_fixture(overlapping=True)
    world = coordinates()
    incomplete = evidence(obligation, world, materials=("router-config", "policy-file"))
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(incomplete,),
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert any("audit-schema" in blocker for blocker in proof.blockers)


@pytest.mark.parametrize(
    ("field", "coordinate_kwargs"),
    (
        ("candidate_generation", {"candidate": "candidate-gen-2"}),
        ("framework_generation", {"framework": "flask-gen-4"}),
        ("provider_generation", {"provider": "provider-gen-8"}),
        ("dependency_generation", {"dependency": "authz-lib-gen-12"}),
    ),
)
def test_wrong_world_generations_cannot_be_mixed_into_proof_world(
    field: str,
    coordinate_kwargs: dict[str, str],
) -> None:
    qualified, obligation, registry = qualified_fixture()
    canonical_world = coordinates()
    mutated = coordinates(**coordinate_kwargs)
    wrong = evidence(obligation, mutated)
    with pytest.raises(ProofWorldError, match="world|generation|coherence"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=canonical_world,
            evidence=(wrong,),
        )


def test_frankenworld_evidence_from_two_generations_is_rejected() -> None:
    qualified, obligation, registry = qualified_fixture()
    canonical_world = coordinates()
    other_world = coordinates(provider="provider-gen-8")
    first = evidence(obligation, canonical_world, claims={"claim:a": "yes"})
    second = evidence(obligation, other_world, claims={"claim:b": "yes"})
    with pytest.raises(ProofWorldError, match="world|coherence"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=canonical_world,
            evidence=(first, second),
        )


def test_heuristic_evidence_cannot_self_label_exact() -> None:
    _, obligation, _ = qualified_fixture()
    world = coordinates()
    with pytest.raises(ProofWorldError, match="heuristic|ceiling|EXACT"):
        evidence(
            obligation,
            world,
            proof_class=ProofClass.HEURISTIC,
            claimed_closure=ClosureGrade.EXACT,
        )


def test_unadmitted_proof_class_cannot_satisfy_contract() -> None:
    qualified, obligation, registry = qualified_fixture(proof_classes=("mechanical",))
    world = coordinates()
    oracle = evidence(obligation, world, proof_class=ProofClass.EXHAUSTIVE_ORACLE)
    with pytest.raises(ProofWorldError, match="proof class|admissible"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=world,
            evidence=(oracle,),
        )


def test_stale_evidence_is_visible_and_cannot_produce_exact_world() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates(epoch=42)
    stale = evidence(obligation, world, epoch=41)
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(stale,),
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert any("temporal" in blocker.lower() or "stale" in blocker.lower() for blocker in proof.blockers)


def test_unresolved_assumption_is_preserved_and_caps_world_unknown() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates()
    assumption = Assumption.create(
        assumption_id="external-policy-completeness",
        kind=AssumptionKind.UNRESOLVED,
        basis_id=sha256_id({"assumption": "external-policy-completeness"}),
    )
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(evidence(obligation, world, assumptions=(assumption,)),),
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert proof.assumptions == (assumption,)
    assert any("assumption" in blocker.lower() for blocker in proof.blockers)


def test_conflicting_claims_are_detected_preserved_and_block_exact() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates()
    left = evidence(obligation, world, claims={"authz:/admin": "preserved"})
    right = evidence(obligation, world, claims={"authz:/admin": "removed"})
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(left, right),
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert len(proof.contradictions) == 1
    assert proof.contradictions[0].claim == "authz:/admin"
    assert set(proof.contradictions[0].values) == {"preserved", "removed"}
    assert any("contradiction" in blocker.lower() for blocker in proof.blockers)


def test_wrong_or_forged_expected_obligation_cannot_cross_sae70_binding() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates()
    forged = replace(obligation, obligation_id="0" * 64)
    with pytest.raises(ProofWorldError, match="obligation|SAE-70|identity"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=forged,
            registry=registry,
            world=world,
            evidence=(evidence(obligation, world),),
        )


def test_proof_world_identity_is_content_addressed() -> None:
    qualified, obligation, registry = qualified_fixture()
    world = coordinates()
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(evidence(obligation, world),),
    )
    forged = replace(proof, proof_world_id="0" * 64)
    with pytest.raises(ProofWorldError, match="Proof World identity|proof world identity"):
        forged.validate()
    assert proof.validate() == proof
