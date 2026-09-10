from __future__ import annotations

from dataclasses import replace

import pytest

from main_review.assurance_contract_registry import ACRRegistry, ClosureGrade
from main_review.review_world import sha256_id
from main_review.falsification_frontier import (
    CounterWorldEvidence,
    FalsifierParameterDomain,
    FalsifierSearchMode,
    FalsificationFrontierError,
    compile_falsification_frontier,
)
from tests.test_sae80_qualification_campaign import canonical_fixture, qualify


def qualified_sae80():
    parts = canonical_fixture()
    return parts, qualify(parts)


def domain(contract, *, values=("/admin", "/ops"), closed=True):
    return FalsifierParameterDomain.create(
        contract_id=contract.contract_id,
        contract_generation=contract.generation,
        family="delete-policy",
        parameters={"route": values},
        closed=closed,
    )


def evidence(instance, *, search_mode=FalsifierSearchMode.EXHAUSTIVE_BOUNDED, no_op=False):
    baseline = sha256_id({"baseline": instance.instance_id})
    mutated = baseline if no_op else sha256_id({"mutated": instance.instance_id})
    return CounterWorldEvidence.create(
        instance=instance,
        baseline_state_id=baseline,
        mutated_state_id=mutated,
        result="SURVIVED",
        search_mode=search_mode,
        basis_id=sha256_id({"basis": instance.instance_id, "mode": search_mode.value}),
    )


def compile_with(domain_builder, evidence_items=()):
    parts, qualified = qualified_sae80()
    contract = parts[0].contracts[0]
    domains = domain_builder(contract)
    return compile_falsification_frontier(
        qualified_proof_world=qualified,
        expected_obligation=parts[2],
        registry=parts[0],
        parameter_domains=domains,
        evidence=evidence_items,
    )


def test_closed_domain_compiles_exact_mandatory_instances() -> None:
    preview = compile_with(lambda c: (domain(c),))
    assert len(preview.expected_instances) == 2
    result = compile_with(lambda c: (domain(c),), tuple(evidence(item) for item in preview.expected_instances))
    assert result.grade is ClosureGrade.EXACT
    assert result.blockers == ()
    assert len(result.frontier_id) == 64


def test_family_name_only_completion_fails_without_exact_instances() -> None:
    result = compile_with(lambda c: (domain(c),), ())
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("missing falsifier instance" in item for item in result.blockers)


def test_one_parameter_instance_cannot_satisfy_another() -> None:
    preview = compile_with(lambda c: (domain(c),))
    result = compile_with(lambda c: (domain(c),), (evidence(preview.expected_instances[0]),))
    assert result.grade is ClosureGrade.UNKNOWN
    assert preview.expected_instances[1].instance_id in " \n".join(result.blockers)


def test_partial_or_open_parameter_domain_stays_unknown() -> None:
    result = compile_with(lambda c: (domain(c, closed=False),), ())
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("not closed" in item for item in result.blockers)


def test_noop_mutation_is_rejected() -> None:
    preview = compile_with(lambda c: (domain(c, values=("/admin",)),))
    with pytest.raises(FalsificationFrontierError, match="no-op"):
        evidence(preview.expected_instances[0], no_op=True)


def test_statistical_or_random_search_cannot_claim_exhaustive_closure() -> None:
    preview = compile_with(lambda c: (domain(c, values=("/admin",)),))
    result = compile_with(
        lambda c: (domain(c, values=("/admin",)),),
        (evidence(preview.expected_instances[0], search_mode=FalsifierSearchMode.STATISTICAL),),
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert any("statistical" in item.lower() for item in result.blockers)


def test_exact_falsifier_identity_is_content_addressed() -> None:
    preview = compile_with(lambda c: (domain(c, values=("/admin",)),))
    instance = preview.expected_instances[0]
    forged = replace(instance, instance_id="0" * 64)
    with pytest.raises(FalsificationFrontierError, match="identity"):
        CounterWorldEvidence.create(
            instance=forged,
            baseline_state_id=sha256_id({"baseline": 1}),
            mutated_state_id=sha256_id({"mutated": 1}),
            result="SURVIVED",
            search_mode=FalsifierSearchMode.EXHAUSTIVE_BOUNDED,
            basis_id=sha256_id({"basis": 1}),
        )


def test_wrong_registry_cannot_compile_against_qualified_proof_world() -> None:
    parts, qualified = qualified_sae80()
    wrong = ACRRegistry.create(generation="wrong-registry", contracts=parts[0].contracts)
    c = parts[0].contracts[0]
    with pytest.raises(FalsificationFrontierError, match="registry"):
        compile_falsification_frontier(
            qualified_proof_world=qualified,
            expected_obligation=parts[2],
            registry=wrong,
            parameter_domains=(domain(c),),
            evidence=(),
        )


def test_wrong_obligation_identity_cannot_compile() -> None:
    parts, qualified = qualified_sae80()
    forged = replace(parts[2], obligation_id="0" * 64)
    c = parts[0].contracts[0]
    with pytest.raises(FalsificationFrontierError, match="obligation"):
        compile_falsification_frontier(
            qualified_proof_world=qualified,
            expected_obligation=forged,
            registry=parts[0],
            parameter_domains=(domain(c),),
            evidence=(),
        )
