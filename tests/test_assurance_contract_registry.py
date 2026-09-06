from __future__ import annotations
import dataclasses
import pytest
from main_review.assurance_contract_registry import (
    ACRContract,
    ACRRegistry,
    ApplicabilityContext,
    ApplicabilityPredicate,
    ApplicabilityTruth,
    BoundedDomain,
    CardinalityKind,
    CardinalitySpec,
    ClosureGrade,
    CollectionRequirement,
    CollectionSemantics,
    ContractRequirement,
    ExternalReviewLane,
    NegativeApplicabilityBurden,
    RegistryError,
)


def domain() -> BoundedDomain:
    return BoundedDomain.create(
        domain_id="python.web-route.v1",
        generation="domain-1",
        dimensions={"max_files": 200, "max_routes": 500},
    )


def predicate() -> ApplicabilityPredicate:
    return ApplicabilityPredicate.all_of(
        ApplicabilityPredicate.fact_equals("language", "python"),
        ApplicabilityPredicate.fact_equals("framework", "flask"),
    )


def contract() -> ACRContract:
    return ACRContract.create(
        contract_id="route-authz",
        generation="contract-1",
        domain=domain(),
        applicability=predicate(),
        bound_subject_variables=("route",),
        semantic_carrier_families=("routes", "decorators"),
        consumer_interpretation_families=("flask-router",),
        affected_relation_families=("route_to_handler",),
        collections=(
            CollectionRequirement.create(
                family="routes",
                semantics=CollectionSemantics.SET,
                cardinality=CardinalitySpec.bounded_n(500),
                required_closure=ClosureGrade.EXACT,
            ),
        ),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create("authz-preserved", ClosureGrade.EXACT),),
        admissible_proof_classes=("mechanical",),
        material_inputs=(ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        coherence_rules=("same-framework-generation",),
        temporal_rules=("evidence-not-older-than-world",),
        mandatory_falsifier_families=("delete-authz-decorator",),
        required_independence=("qualification-corpus-independent",),
        permitted_capabilities=("python-ast",),
        negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),
        external_review_lanes=(ExternalReviewLane.create("hostile-external", minimum_instances=1),),
        unsupported_fallback="UNKNOWN",
    )


def test_three_valued_applicability_conserves_unknown() -> None:
    c = contract()
    assert c.evaluate(ApplicabilityContext.exact({"language": "python", "framework": "flask"})).truth is ApplicabilityTruth.TRUE
    assert c.evaluate(ApplicabilityContext.exact({"language": "python", "framework": "django"})).truth is ApplicabilityTruth.FALSE
    result = c.evaluate(ApplicabilityContext.partial({"language": "python"}))
    assert result.truth is ApplicabilityTruth.UNKNOWN
    assert "framework" in result.unresolved_facts


def test_missing_fact_cannot_become_false_merely_because_it_is_absent() -> None:
    c = contract()
    result = c.evaluate(ApplicabilityContext.exact({"language": "python"}))
    assert result.truth is ApplicabilityTruth.UNKNOWN


def test_proven_absence_requires_sufficient_closure() -> None:
    p = ApplicabilityPredicate.fact_absent("framework")
    assert p.evaluate(ApplicabilityContext.partial({})).truth is ApplicabilityTruth.UNKNOWN
    assert p.evaluate(ApplicabilityContext.exact({})).truth is ApplicabilityTruth.TRUE
    assert p.evaluate(ApplicabilityContext.exact({"framework": "flask"})).truth is ApplicabilityTruth.FALSE


def test_registry_is_content_addressed_canonical_and_order_independent() -> None:
    a = contract()
    b = dataclasses.replace(a, contract_id="route-authn", contract_id_hash="")
    b = ACRContract.create(**b.constructor_fields())
    r1 = ACRRegistry.create(generation="acr-gen-1", contracts=(a, b))
    r2 = ACRRegistry.create(generation="acr-gen-1", contracts=(b, a))
    assert r1.registry_id == r2.registry_id
    assert [x.contract_id for x in r1.contracts] == ["route-authn", "route-authz"]
    assert ACRRegistry.from_payload(r1.to_payload()) == r1


def test_registry_rejects_duplicate_contract_identity() -> None:
    with pytest.raises(RegistryError, match="duplicate"):
        ACRRegistry.create(generation="acr-gen-1", contracts=(contract(), contract()))


def test_contract_payload_is_strict_and_id_tamper_is_rejected() -> None:
    c = contract()
    payload = c.to_payload()
    payload["contract_id_hash"] = "0" * 64
    with pytest.raises(RegistryError, match="contract_id_hash"):
        ACRContract.from_payload(payload)


def test_collection_semantics_and_cardinality_are_not_interchangeable() -> None:
    multiset = CollectionRequirement.create(
        family="calls", semantics=CollectionSemantics.MULTISET,
        cardinality=CardinalitySpec.exactly_one(), required_closure=ClosureGrade.EXACT,
    )
    ordered = CollectionRequirement.create(
        family="calls", semantics=CollectionSemantics.ORDER,
        cardinality=CardinalitySpec.exactly_one(), required_closure=ClosureGrade.EXACT,
    )
    assert multiset.to_payload() != ordered.to_payload()
    assert CardinalitySpec.bounded_n(2).to_payload() != CardinalitySpec.bounded_n(3).to_payload()


def test_bounded_domain_rejects_unbounded_or_nonpositive_limits() -> None:
    with pytest.raises(RegistryError):
        BoundedDomain.create(domain_id="x", generation="g", dimensions={})
    with pytest.raises(RegistryError):
        BoundedDomain.create(domain_id="x", generation="g", dimensions={"n": 0})


def test_candidate_contract_has_no_self_qualification_field_or_path() -> None:
    payload = contract().to_payload()
    assert "qualified" not in payload
    assert "qualification_state" not in payload
    assert payload["self_qualification_allowed"] is False


def test_unknown_fallback_is_mandatory() -> None:
    kwargs = contract().constructor_fields()
    kwargs["unsupported_fallback"] = "FALSE"
    with pytest.raises(RegistryError, match="UNKNOWN"):
        ACRContract.create(**kwargs)


def test_negative_applicability_requires_proven_no_match_burden() -> None:
    kwargs = contract().constructor_fields()
    kwargs["negative_applicability"] = None
    with pytest.raises(RegistryError, match="negative applicability"):
        ACRContract.create(**kwargs)


def test_registry_rejects_two_generations_of_same_contract_id() -> None:
    first = contract()
    kwargs = first.constructor_fields(); kwargs["generation"] = "contract-2"
    second = ACRContract.create(**kwargs)
    with pytest.raises(RegistryError, match="duplicate contract_id"):
        ACRRegistry.create(generation="acr-gen-1", contracts=(first, second))


def test_persisted_boolean_fields_are_type_strict() -> None:
    payload = contract().to_payload()
    payload["self_qualification_allowed"] = 0
    with pytest.raises(RegistryError, match="self-qualify"):
        ACRContract.from_payload(payload)


def test_registry_missing_mandatory_evaluation_is_unknown_not_silently_absent() -> None:
    registry = ACRRegistry.create(generation="acr-gen-1", contracts=(contract(),))
    evaluations = registry.evaluate_all({})
    assert len(evaluations) == 1
    assert evaluations[0].contract_id == "route-authz"
    assert evaluations[0].truth is ApplicabilityTruth.UNKNOWN
    assert evaluations[0].evaluation_present is False
    assert evaluations[0].unresolved_facts == ("<missing-evaluation>",)


def test_registry_evaluates_every_mandatory_contract_and_rejects_unknown_context_keys() -> None:
    registry = ACRRegistry.create(generation="acr-gen-1", contracts=(contract(),))
    evaluations = registry.evaluate_all({"route-authz": ApplicabilityContext.exact({"language": "python", "framework": "flask"})})
    assert evaluations[0].truth is ApplicabilityTruth.TRUE
    assert evaluations[0].evaluation_present is True
    with pytest.raises(RegistryError, match="unknown contract"):
        registry.evaluate_all({"not-in-registry": ApplicabilityContext.exact({})})


def test_v1_contract_is_mandatory_and_persisted_downgrade_is_rejected() -> None:
    payload = contract().to_payload()
    assert payload["mandatory"] is True
    payload["mandatory"] = False
    with pytest.raises(RegistryError, match="mandatory"):
        ACRContract.from_payload(payload)
