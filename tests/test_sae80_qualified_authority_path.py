from __future__ import annotations

from main_review.assurance_contract_registry import ClosureGrade
from main_review.proof_world import ProofClass, compile_proof_world
from tests.sae80_authority_fixtures import authority_fixture, evidence, qualified_fixture


def test_sae10_sae30_sae40_sae60_sae70_authority_can_issue_exact_mechanical_proof_world() -> None:
    qualified, obligation, registry = qualified_fixture()
    authority, world = authority_fixture(qualified, registry)
    proof_evidence = evidence(obligation, world, authority)

    assert proof_evidence.proof_class is ProofClass.MECHANICAL
    assert proof_evidence.proof_authority.world_authority_id == authority.authority_id

    proof = compile_proof_world(
        qualified_closure=qualified,
        expected_obligation=obligation,
        registry=registry,
        world=world,
        evidence=(proof_evidence,),
        world_authority=authority,
    )
    assert proof.grade is ClosureGrade.EXACT
    assert proof.blockers == ()
    assert proof.validate() == proof
