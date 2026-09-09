from __future__ import annotations

from dataclasses import replace

import pytest

from main_review.assurance_contract_registry import ACRContract, ACRRegistry, ClosureGrade, ContractRequirement
from main_review.proof_world import (
    Assumption,
    AssumptionKind,
    ProofClass,
    ProofWorldError,
    WorldCoordinates,
    compile_proof_world,
)
from main_review.review_world import sha256_id
from tests.sae80_authority_fixtures import (
    authority_fixture,
    evidence,
    qualified_fixture,
)


def test_exact_evidence_world_binds_sae70_authority_obligation_and_material_inputs() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(evidence(obligation, world, authority),),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.EXACT
    assert proof.blockers == ()
    assert proof.qualified_closure_id == qualified.qualification_id
    assert proof.obligation_id == obligation.obligation_id
    assert proof.world_id == world.world_id
    assert {item.family for item in proof.material_inputs} == {"router-config", "policy-file"}
    assert proof.contradictions == ()
    assert len(proof.proof_world_id) == 64
    assert proof.validate() == proof


def test_registry_content_is_bound_to_sae70_qualification() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    original = registry.contracts[0]
    mutated = ACRContract.create(
        **{
            **original.constructor_fields(),
            "material_inputs": (ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        }
    )
    forged_registry = ACRRegistry.create(generation=registry.generation, contracts=(mutated,))
    assert forged_registry.registry_id != qualified.registry_id
    with pytest.raises(ProofWorldError, match="registry|SAE-70|ACR"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=forged_registry,
            world=world,
            evidence=(evidence(obligation, world, authority, materials=("router-config",)),),
            world_authority=authority,
        )


def test_overlapping_origins_require_conservative_union_of_material_inputs() -> None:
    qualified, obligation, registry = qualified_fixture(overlapping=True)
    authority, world = authority_fixture(qualified, registry)
    complete = evidence(
        obligation,
        world,
        authority,
        materials=("router-config", "policy-file", "audit-schema"),
    )
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(complete,),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.EXACT
    assert {item.family for item in proof.material_inputs} == {
        "router-config",
        "policy-file",
        "audit-schema",
    }


def test_omitted_material_input_prevents_exact_closure() -> None:
    qualified, obligation, registry = qualified_fixture(overlapping=True)
    authority, world = authority_fixture(qualified, registry)
    incomplete = evidence(obligation, world, authority, materials=("router-config", "policy-file"))
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(incomplete,),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert any("audit-schema" in blocker for blocker in proof.blockers)


@pytest.mark.parametrize(
    ("field", "coordinate_kwargs"),
    (
        ("candidate_generation", {"candidate_generation": "candidate-gen-forged"}),
        ("framework_generation", {"framework_generation": "framework-gen-forged"}),
        ("provider_generation", {"provider_generation": "provider-gen-forged"}),
        ("dependency_generation", {"dependency_generations": {"forged": "dependency-gen-forged"}}),
    ),
)
def test_wrong_world_generations_cannot_be_mixed_into_proof_world(
    field: str,
    coordinate_kwargs: dict[str, object],
) -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, canonical_world = authority_fixture(qualified, registry)
    fields = {
        "candidate_generation": canonical_world.candidate_generation,
        "framework_generation": canonical_world.framework_generation,
        "provider_generation": canonical_world.provider_generation,
        "dependency_generations": dict(canonical_world.dependency_generations),
        "epoch": canonical_world.epoch,
    }
    fields.update(coordinate_kwargs)
    mutated = WorldCoordinates.create(**fields)
    proof = evidence(obligation, canonical_world, authority)
    with pytest.raises(ProofWorldError, match="world|generation|authority"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=mutated,
            evidence=(proof,),
            world_authority=authority,
        )


def test_frankenworld_evidence_from_two_generations_is_rejected() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, canonical_world = authority_fixture(qualified, registry)
    other = WorldCoordinates.create(
        candidate_generation=canonical_world.candidate_generation,
        framework_generation=canonical_world.framework_generation,
        provider_generation="forged-provider-generation",
        dependency_generations=dict(canonical_world.dependency_generations),
        epoch=canonical_world.epoch,
    )
    first = evidence(obligation, canonical_world, authority, claims={"claim:a": "yes"})
    with pytest.raises(ProofWorldError, match="qualified|world|authority"):
        # Even evidence construction cannot cross into a self-declared second world.
        evidence(obligation, other, authority, claims={"claim:b": "yes"})
    with pytest.raises(ProofWorldError, match="world|generation|authority"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=other,
            evidence=(first,),
            world_authority=authority,
        )


def test_heuristic_evidence_cannot_self_label_exact() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    with pytest.raises(ProofWorldError, match="heuristic|ceiling|EXACT"):
        evidence(
            obligation,
            world,
            authority,
            proof_class=ProofClass.HEURISTIC,
            claimed_closure=ClosureGrade.EXACT,
        )


def test_unadmitted_proof_class_cannot_satisfy_contract() -> None:
    qualified, obligation, registry = qualified_fixture(proof_classes=("mechanical",))
    authority, world = authority_fixture(qualified, registry)
    oracle = evidence(obligation, world, authority, proof_class=ProofClass.EXHAUSTIVE_ORACLE)
    with pytest.raises(ProofWorldError, match="proof class|admissible"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=obligation,
            registry=registry,
            world=world,
            evidence=(oracle,),
            world_authority=authority,
        )


def test_stale_evidence_is_visible_and_cannot_produce_exact_world() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry, epoch=42)
    stale = evidence(obligation, world, authority, epoch=41)
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(stale,),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert any("temporal" in blocker.lower() or "stale" in blocker.lower() for blocker in proof.blockers)


def test_unresolved_assumption_is_preserved_and_caps_world_unknown() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
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
        evidence=(evidence(obligation, world, authority, assumptions=(assumption,)),),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert proof.assumptions == (assumption,)
    assert any("assumption" in blocker.lower() for blocker in proof.blockers)


def test_conflicting_claims_are_detected_preserved_and_block_exact() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    left = evidence(obligation, world, authority, claims={"authz:/admin": "preserved"})
    right = evidence(obligation, world, authority, claims={"authz:/admin": "removed"})
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(left, right),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.UNKNOWN
    assert len(proof.contradictions) == 1
    assert proof.contradictions[0].claim == "authz:/admin"
    assert set(proof.contradictions[0].values) == {"preserved", "removed"}
    assert any("contradiction" in blocker.lower() for blocker in proof.blockers)


def test_wrong_or_forged_expected_obligation_cannot_cross_sae70_binding() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    forged = replace(obligation, obligation_id="0" * 64)
    with pytest.raises(ProofWorldError, match="obligation|SAE-70|identity"):
        compile_proof_world(
            qualified_closure=qualified,
            expected_obligation=forged,
            registry=registry,
            world=world,
            evidence=(evidence(obligation, world, authority),),
            world_authority=authority,
        )


def test_proof_world_identity_is_content_addressed() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(evidence(obligation, world, authority),),
        world_authority=authority,
    )
    forged = replace(proof, proof_world_id="0" * 64)
    with pytest.raises(ProofWorldError, match="Proof World identity|proof world identity"):
        forged.validate()
    assert proof.validate() == proof
