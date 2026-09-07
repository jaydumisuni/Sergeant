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
    ContractClosureError,
    ContractInstanceEnumeration,
    ProvenNoMatch,
    compile_contract_closure,
)
from main_review.review_world import sha256_id


def contract(
    contract_id: str,
    *,
    framework: str,
    obligation: str,
    obligation_closure: ClosureGrade = ClosureGrade.EXACT,
) -> ACRContract:
    return ACRContract.create(
        contract_id=contract_id,
        generation="contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.v1",
            generation="domain-gen-1",
            dimensions={"max_files": 200, "max_routes": 500},
        ),
        applicability=ApplicabilityPredicate.all_of(
            ApplicabilityPredicate.fact_equals("language", "python"),
            ApplicabilityPredicate.fact_equals("framework", framework),
        ),
        bound_subject_variables=("route",),
        semantic_carrier_families=("routes",),
        consumer_interpretation_families=("router",),
        affected_relation_families=("route_to_handler",),
        collections=(
            CollectionRequirement.create(
                "routes",
                CollectionSemantics.SET,
                CardinalitySpec.bounded_n(500),
                ClosureGrade.EXACT,
            ),
        ),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create(obligation, obligation_closure),),
        admissible_proof_classes=("mechanical",),
        material_inputs=(ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        coherence_rules=("same-framework-generation",),
        temporal_rules=("evidence-not-older-than-world",),
        mandatory_falsifier_families=("delete-policy",),
        required_independence=("qualification-corpus-independent",),
        permitted_capabilities=("python.bounded-literal-dispatch.v1",),
        negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),
        external_review_lanes=(ExternalReviewLane.create("hostile-external", 1),),
        unsupported_fallback="UNKNOWN",
    )


def registry(*contracts: ACRContract) -> ACRRegistry:
    return ACRRegistry.create(generation="acr-gen-1", contracts=contracts)


def exact_context(framework: str) -> ApplicabilityContext:
    return ApplicabilityContext.exact({"language": "python", "framework": framework})


def instances(c: ACRContract, *routes: str) -> ContractInstanceEnumeration:
    return ContractInstanceEnumeration.create(
        contract=c,
        bindings=tuple({"route": route} for route in routes),
        closure=ClosureGrade.EXACT,
        source_basis_id=sha256_id({"instance-basis": c.contract_id, "routes": list(routes)}),
    )


def no_match(c: ACRContract, context: ApplicabilityContext) -> ProvenNoMatch:
    return ProvenNoMatch.create(
        contract=c,
        context=context,
        closure=ClosureGrade.EXACT,
        evidence_id=sha256_id({"no-match": c.contract_id, "framework": context.facts.get("framework")}),
    )


def test_all_mandatory_contracts_are_censused_and_true_contract_instances_are_total() -> None:
    flask = contract("flask-authz", framework="flask", obligation="authz-preserved")
    django = contract("django-authz", framework="django", obligation="authz-preserved")
    r = registry(flask, django)
    contexts = {"flask-authz": exact_context("flask"), "django-authz": exact_context("flask")}

    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations={"flask-authz": instances(flask, "/a", "/b")},
        proven_no_match={"django-authz": no_match(django, contexts["django-authz"])},
    )

    assert result.grade is ClosureGrade.EXACT
    assert tuple(entry.contract_id for entry in result.contract_census) == ("django-authz", "flask-authz")
    assert {entry.disposition for entry in result.contract_census} == {"ACTIVE", "PROVEN_NO_MATCH"}
    assert tuple(instance.bindings for instance in result.expected_instances) == (
        (("route", "/a"),),
        (("route", "/b"),),
    )


def test_missing_contract_evaluation_is_unknown_and_blocks_exact_closure() -> None:
    first = contract("first", framework="flask", obligation="one")
    second = contract("second", framework="flask", obligation="two")
    result = compile_contract_closure(
        registry=registry(first, second),
        contexts={"first": exact_context("flask")},
        instance_enumerations={"first": instances(first, "/a")},
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert any(entry.contract_id == "second" and entry.disposition == "UNKNOWN" for entry in result.contract_census)
    assert any("second" in blocker for blocker in result.blockers)


def test_unknown_applicability_cannot_be_coerced_to_false_or_no_match() -> None:
    c = contract("route-authz", framework="flask", obligation="authz-preserved")
    partial = ApplicabilityContext.partial({"language": "python"})
    result = compile_contract_closure(
        registry=registry(c),
        contexts={"route-authz": partial},
        instance_enumerations={},
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert result.contract_census[0].disposition == "UNKNOWN"

    with pytest.raises(ContractClosureError, match="FALSE applicability"):
        ProvenNoMatch.create(
            contract=c,
            context=partial,
            closure=ClosureGrade.EXACT,
            evidence_id=sha256_id({"fake": "no-match"}),
        )


def test_false_contract_requires_proven_no_match_with_sufficient_closure() -> None:
    c = contract("django-authz", framework="django", obligation="authz-preserved")
    ctx = exact_context("flask")

    absent = compile_contract_closure(
        registry=registry(c),
        contexts={c.contract_id: ctx},
        instance_enumerations={},
        proven_no_match={},
    )
    assert absent.grade is ClosureGrade.UNKNOWN
    assert absent.contract_census[0].disposition == "UNKNOWN"

    with pytest.raises(ContractClosureError, match="required closure"):
        ProvenNoMatch.create(
            contract=c,
            context=ctx,
            closure=ClosureGrade.PARTIAL,
            evidence_id=sha256_id({"weak": "no-match"}),
        )


def test_true_contract_without_instance_enumeration_is_not_silently_dropped() -> None:
    c = contract("route-authz", framework="flask", obligation="authz-preserved")
    result = compile_contract_closure(
        registry=registry(c),
        contexts={c.contract_id: exact_context("flask")},
        instance_enumerations={},
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert result.expected_instances == ()
    assert any("instance enumeration" in blocker for blocker in result.blockers)


def test_instance_binding_must_cover_exact_bound_subject_variables_and_be_unique() -> None:
    c = contract("route-authz", framework="flask", obligation="authz-preserved")
    with pytest.raises(ContractClosureError, match="bound subject variables"):
        ContractInstanceEnumeration.create(
            contract=c,
            bindings=({"handler": "home"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"bad": "binding"}),
        )
    with pytest.raises(ContractClosureError, match="duplicate contract instance"):
        instances(c, "/a", "/a")


def test_overlapping_active_contracts_use_conservative_union_not_first_match() -> None:
    authz = contract("authz", framework="flask", obligation="authz-preserved")
    audit = contract("audit", framework="flask", obligation="audit-event-emitted")
    r = registry(authz, audit)
    contexts = {"authz": exact_context("flask"), "audit": exact_context("flask")}

    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations={
            "authz": instances(authz, "/admin"),
            "audit": instances(audit, "/admin"),
        },
        proven_no_match={},
    )

    assert result.grade is ClosureGrade.EXACT
    assert {obligation.family for obligation in result.expected_obligations} == {
        "authz-preserved",
        "audit-event-emitted",
    }
    assert len(result.expected_instances) == 2


def test_same_obligation_from_overlapping_contracts_preserves_all_provenance() -> None:
    first = contract("first", framework="flask", obligation="authz-preserved")
    second = contract("second", framework="flask", obligation="authz-preserved")
    result = compile_contract_closure(
        registry=registry(first, second),
        contexts={"first": exact_context("flask"), "second": exact_context("flask")},
        instance_enumerations={
            "first": instances(first, "/admin"),
            "second": instances(second, "/admin"),
        },
        proven_no_match={},
    )
    assert len(result.expected_obligations) == 1
    obligation = result.expected_obligations[0]
    assert obligation.family == "authz-preserved"
    assert {origin.contract_id for origin in obligation.provenance} == {"first", "second"}
    assert len({origin.contract_instance_id for origin in obligation.provenance}) == 2


def test_conflicting_closure_requirements_resolve_conservatively_to_strongest_requirement() -> None:
    exact = contract("exact", framework="flask", obligation="same", obligation_closure=ClosureGrade.EXACT)
    partial = contract("partial", framework="flask", obligation="same", obligation_closure=ClosureGrade.PARTIAL)
    result = compile_contract_closure(
        registry=registry(exact, partial),
        contexts={"exact": exact_context("flask"), "partial": exact_context("flask")},
        instance_enumerations={"exact": instances(exact, "/x"), "partial": instances(partial, "/x")},
        proven_no_match={},
    )
    obligation = result.expected_obligations[0]
    assert obligation.required_closure is ClosureGrade.EXACT
    assert obligation.conflict_resolved_conservatively is True
    assert {origin.required_closure for origin in obligation.provenance} == {
        ClosureGrade.EXACT,
        ClosureGrade.PARTIAL,
    }


def test_instance_enumeration_with_non_exact_basis_cannot_create_exact_contract_closure() -> None:
    c = contract("route-authz", framework="flask", obligation="authz-preserved")
    weak = ContractInstanceEnumeration.create(
        contract=c,
        bindings=({"route": "/a"},),
        closure=ClosureGrade.PARTIAL,
        source_basis_id=sha256_id({"weak": "instances"}),
    )
    result = compile_contract_closure(
        registry=registry(c),
        contexts={c.contract_id: exact_context("flask")},
        instance_enumerations={c.contract_id: weak},
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.PARTIAL
    assert any("instance enumeration closure" in blocker for blocker in result.blockers)


def test_enumeration_contract_generation_or_registry_key_mismatch_fails_closed() -> None:
    c = contract("route-authz", framework="flask", obligation="authz-preserved")
    wrong_generation = replace(c, generation="contract-gen-2")
    enumeration = instances(c, "/a")
    with pytest.raises(ContractClosureError, match="registry key"):
        compile_contract_closure(
            registry=registry(c),
            contexts={c.contract_id: exact_context("flask")},
            instance_enumerations={"not-route-authz": enumeration},
            proven_no_match={},
        )
    with pytest.raises(ContractClosureError, match="contract generation"):
        ContractInstanceEnumeration.create(
            contract=wrong_generation,
            bindings=({"route": "/a"},),
            closure=ClosureGrade.EXACT,
            source_basis_id=sha256_id({"wrong": "generation"}),
        )
