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
import main_review.contract_closure as closure
from main_review.contract_closure import (
    ContractClosureError,
    ContractInstanceEnumeration,
    ExpectedObligation,
    ProvenNoMatch,
    compile_contract_closure,
)
from main_review.review_world import sha256_id


def contract(
    contract_id: str,
    *,
    framework: str = "flask",
    obligation: str = "authz-preserved",
    obligation_closure: ClosureGrade = ClosureGrade.EXACT,
) -> ACRContract:
    """Separately authored bounded qualification fixture contract."""
    return ACRContract.create(
        contract_id=contract_id,
        generation="sae70-qual-contract-gen-1",
        domain=BoundedDomain.create(
            domain_id="python.web-route.sae70-qualification.v1",
            generation="sae70-qual-domain-gen-1",
            dimensions={"max_files": 12, "max_routes": 16},
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
                CardinalitySpec.bounded_n(16),
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
    return ACRRegistry.create(generation="sae70-qualification-acr-gen-1", contracts=contracts)


def exact_context(framework: str = "flask") -> ApplicabilityContext:
    return ApplicabilityContext.exact({"language": "python", "framework": framework})


def instances(c: ACRContract, *routes: str, closure_grade: ClosureGrade = ClosureGrade.EXACT) -> ContractInstanceEnumeration:
    return ContractInstanceEnumeration.create(
        contract=c,
        bindings=tuple({"route": route} for route in routes),
        closure=closure_grade,
        source_basis_id=sha256_id(
            {"sae70-qualification-instance-basis": c.contract_id, "routes": list(routes)}
        ),
    )


def no_match(c: ACRContract, context: ApplicabilityContext) -> ProvenNoMatch:
    return ProvenNoMatch.create(
        contract=c,
        context=context,
        closure=ClosureGrade.EXACT,
        evidence_id=sha256_id(
            {
                "sae70-qualification-no-match": c.contract_id,
                "framework": context.facts.get("framework"),
            }
        ),
    )


def qualification_api():
    qualify = getattr(closure, "qualify_contract_closure", None)
    assert callable(qualify), "SAE-70 exact-result qualification protocol is not implemented"
    return qualify


def protocol_ids() -> tuple[str, str]:
    first = getattr(closure, "QUALIFIED_CONTRACT_INSTANCE_CLOSURE", None)
    second = getattr(closure, "QUALIFIED_EXPECTED_OBLIGATION_COMPILER", None)
    assert first == "QUALIFIED_CONTRACT_INSTANCE_CLOSURE"
    assert second == "QUALIFIED_EXPECTED_OBLIGATION_COMPILER"
    return first, second


def exact_fixture():
    active = contract("active-authz", framework="flask", obligation="authz-preserved")
    inactive = contract("django-authz", framework="django", obligation="authz-preserved")
    r = registry(active, inactive)
    contexts = {
        active.contract_id: exact_context("flask"),
        inactive.contract_id: exact_context("flask"),
    }
    enumerations = {active.contract_id: instances(active, "/admin", "/billing")}
    no_matches = {inactive.contract_id: no_match(inactive, contexts[inactive.contract_id])}
    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match=no_matches,
    )
    assert result.grade is ClosureGrade.EXACT
    return r, contexts, enumerations, no_matches, result


def overlapping_fixture(*, same_obligation: bool = False):
    first = contract("first", obligation="authz-preserved")
    second = contract(
        "second",
        obligation="authz-preserved" if same_obligation else "audit-event-emitted",
    )
    r = registry(first, second)
    contexts = {first.contract_id: exact_context(), second.contract_id: exact_context()}
    enumerations = {
        first.contract_id: instances(first, "/admin"),
        second.contract_id: instances(second, "/admin"),
    }
    no_matches: dict[str, ProvenNoMatch] = {}
    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match=no_matches,
    )
    assert result.grade is ClosureGrade.EXACT
    return r, contexts, enumerations, no_matches, result


def qualify_fixture(fixture):
    r, contexts, enumerations, no_matches, result = fixture
    return qualification_api()(
        registry=r,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match=no_matches,
        result=result,
    )


def test_exact_bounded_census_instances_and_obligations_cross_qualification_boundary() -> None:
    fixture = exact_fixture()
    qualified = qualify_fixture(fixture)
    first, second = protocol_ids()

    assert qualified.protocol_ids == (first, second)
    assert qualified.registry_id == fixture[0].registry_id
    assert qualified.contract_closure_result_id == fixture[4].result_id
    assert qualified.expected_instance_ids == tuple(
        instance.contract_instance_id for instance in fixture[4].expected_instances
    )
    assert qualified.expected_obligation_ids == tuple(
        obligation.obligation_id for obligation in fixture[4].expected_obligations
    )
    assert len(qualified.qualification_id) == 64


def test_dropped_contract_census_entry_cannot_be_qualified() -> None:
    r, contexts, enumerations, no_matches, result = exact_fixture()
    dropped = replace(result, contract_census=result.contract_census[:-1])
    with pytest.raises(ContractClosureError, match="canonical recomputation"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=dropped,
        )


def test_dropped_contract_instance_cannot_be_qualified() -> None:
    r, contexts, enumerations, no_matches, result = exact_fixture()
    dropped = replace(result, expected_instances=result.expected_instances[:-1])
    with pytest.raises(ContractClosureError, match="canonical recomputation"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=dropped,
        )


def test_unknown_applicability_cannot_cross_qualification_as_false() -> None:
    c = contract("unknown-authz")
    r = registry(c)
    contexts = {c.contract_id: ApplicabilityContext.partial({"language": "python"})}
    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations={},
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.UNKNOWN
    assert result.contract_census[0].disposition == "UNKNOWN"

    with pytest.raises(ContractClosureError, match="EXACT"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations={},
            proven_no_match={},
            result=result,
        )


def test_first_match_weakening_cannot_drop_an_overlapping_obligation() -> None:
    r, contexts, enumerations, no_matches, result = overlapping_fixture()
    assert {item.family for item in result.expected_obligations} == {
        "authz-preserved",
        "audit-event-emitted",
    }
    weakened = replace(result, expected_obligations=result.expected_obligations[:1])

    with pytest.raises(ContractClosureError, match="canonical recomputation"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=weakened,
        )


def test_obligation_provenance_collapse_cannot_be_qualified() -> None:
    r, contexts, enumerations, no_matches, result = overlapping_fixture(same_obligation=True)
    assert len(result.expected_obligations) == 1
    obligation = result.expected_obligations[0]
    assert len(obligation.provenance) == 2
    collapsed_obligation = replace(obligation, provenance=obligation.provenance[:1])
    collapsed = replace(result, expected_obligations=(collapsed_obligation,))

    with pytest.raises(ContractClosureError, match="canonical recomputation"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=collapsed,
        )


def test_partial_instance_enumeration_never_becomes_qualified_exact_closure() -> None:
    c = contract("partial-authz")
    r = registry(c)
    contexts = {c.contract_id: exact_context()}
    enumerations = {c.contract_id: instances(c, "/a", closure_grade=ClosureGrade.PARTIAL)}
    result = compile_contract_closure(
        registry=r,
        contexts=contexts,
        instance_enumerations=enumerations,
        proven_no_match={},
    )
    assert result.grade is ClosureGrade.PARTIAL

    with pytest.raises(ContractClosureError, match="EXACT"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match={},
            result=result,
        )


def test_historical_result_cannot_replay_against_another_registry_generation() -> None:
    r, contexts, enumerations, no_matches, result = exact_fixture()
    changed_registry = ACRRegistry.create(generation="sae70-qualification-acr-gen-2", contracts=r.contracts)
    assert changed_registry.registry_id != r.registry_id

    with pytest.raises(ContractClosureError, match="canonical recomputation|registry"):
        qualification_api()(
            registry=changed_registry,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=result,
        )


def test_forged_result_identity_is_rejected_before_authority_is_issued() -> None:
    r, contexts, enumerations, no_matches, result = exact_fixture()
    forged = replace(result, result_id="0" * 64)

    with pytest.raises(ContractClosureError, match="canonical recomputation|identity"):
        qualification_api()(
            registry=r,
            contexts=contexts,
            instance_enumerations=enumerations,
            proven_no_match=no_matches,
            result=forged,
        )


def test_qualified_record_is_content_addressed_and_not_self_mutable() -> None:
    qualified = qualify_fixture(exact_fixture())
    forged = replace(qualified, qualification_id="0" * 64)
    validate = getattr(closure, "validate_qualified_contract_closure", None)
    assert callable(validate), "qualified SAE-70 authority must be independently revalidatable"
    with pytest.raises(ContractClosureError, match="qualification identity"):
        validate(forged)
    assert validate(qualified) == qualified


def test_qualification_does_not_activate_genesis_or_normal_sergeant_verdict_authority() -> None:
    candidate_manifest = __import__("pathlib").Path(
        "docs/107-sae70-contract-obligation-closure-candidate-manifest.json"
    ).read_text(encoding="utf-8")
    assert '"produces_now": []' in candidate_manifest
    assert '"normal_verdict_authority": false' in candidate_manifest
    assert '"genesis_activated": false' in candidate_manifest
    assert "QUALIFIED_CONTRACT_INSTANCE_CLOSURE" in candidate_manifest
    assert "QUALIFIED_EXPECTED_OBLIGATION_COMPILER" in candidate_manifest
