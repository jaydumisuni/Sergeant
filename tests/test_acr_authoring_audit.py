from __future__ import annotations
import dataclasses
import pytest
from main_review.acr_authoring_audit import (
    ACREscapeDisposition,
    AuthoringAuditProfile,
    AuthoringAuditStatus,
    audit_contract_authoring,
    record_qualification_escape,
)
from main_review.assurance_contract_registry import (
    ACRContract,
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


def contract() -> ACRContract:
    return ACRContract.create(
        contract_id="route-authz", generation="contract-1",
        domain=BoundedDomain.create(domain_id="python.web-route.v1", generation="domain-1", dimensions={"max_files": 200, "max_routes": 500}),
        applicability=ApplicabilityPredicate.all_of(
            ApplicabilityPredicate.fact_equals("language", "python"),
            ApplicabilityPredicate.fact_equals("framework", "flask"),
        ),
        bound_subject_variables=("route",),
        semantic_carrier_families=("routes", "decorators"),
        consumer_interpretation_families=("flask-router",),
        affected_relation_families=("route_to_handler",),
        collections=(CollectionRequirement.create("routes", CollectionSemantics.MULTISET, CardinalitySpec.bounded_n(500), ClosureGrade.EXACT),),
        mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        repeated_authority_premise_families=("review-world",),
        mandatory_obligations=(ContractRequirement.create("authz-preserved", ClosureGrade.EXACT),),
        admissible_proof_classes=("mechanical",),
        material_inputs=(ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        coherence_rules=("same-framework-generation",), temporal_rules=("evidence-not-older-than-world",),
        mandatory_falsifier_families=("delete-authz-decorator", "swap-route-order"),
        required_independence=("qualification-corpus-independent",), permitted_capabilities=("python-ast",),
        negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),
        external_review_lanes=(ExternalReviewLane.create("hostile-external", 2),), unsupported_fallback="UNKNOWN",
    )


def profile() -> AuthoringAuditProfile:
    c = contract()
    return AuthoringAuditProfile.create(
        profile_id="route-authz-authoring-v2",
        generation="audit-profile-2",
        contract_id="route-authz",
        domain=c.domain,
        expected_applicability=c.applicability,
        independent_basis_ids=("1" * 64, "2" * 64),
        required_semantic_carriers=("routes", "decorators"),
        required_consumer_interpretation_families=("flask-router",),
        required_affected_relations=("route_to_handler",),
        required_collections=(CollectionRequirement.create("routes", CollectionSemantics.MULTISET, CardinalitySpec.bounded_n(500), ClosureGrade.EXACT),),
        required_premises=(ContractRequirement.create("route-discovery", ClosureGrade.EXACT),),
        required_repeated_authority_premise_families=("review-world",),
        required_obligations=(ContractRequirement.create("authz-preserved", ClosureGrade.EXACT),),
        required_material_inputs=(ContractRequirement.create("router-config", ClosureGrade.EXACT),),
        required_coherence_rules=("same-framework-generation",),
        required_temporal_rules=("evidence-not-older-than-world",),
        required_falsifier_families=("delete-authz-decorator", "swap-route-order"),
        required_independence=("qualification-corpus-independent",), required_external_review_lanes={"hostile-external": 2},
        require_negative_applicability_burden=True, require_unknown_fallback=True,
    )


def assert_attack(mutated: ACRContract, family: str) -> None:
    result = audit_contract_authoring(mutated, profile())
    assert result.status is AuthoringAuditStatus.DEFICIENT
    assert family in {finding.family for finding in result.findings}
    assert result.qualifies_contract is False


def rebuild(c: ACRContract, **overrides) -> ACRContract:
    kwargs = c.constructor_fields(); kwargs.update(overrides); return ACRContract.create(**kwargs)


def test_clean_contract_is_audit_clean_but_not_qualified() -> None:
    result = audit_contract_authoring(contract(), profile())
    assert result.status is AuthoringAuditStatus.CLEAN
    assert result.findings == ()
    assert result.qualifies_contract is False


def test_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), semantic_carrier_families=("routes",)), "semantic_carrier_omission")


def test_cardinality_semantics_weakening_attack_is_detected() -> None:
    weak = CollectionRequirement.create("routes", CollectionSemantics.SET, CardinalitySpec.bounded_n(500), ClosureGrade.EXACT)
    assert_attack(rebuild(contract(), collections=(weak,)), "collection_semantics_or_cardinality_weakening")


def test_applicability_trigger_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), applicability=ApplicabilityPredicate.fact_equals("language", "python")), "applicability_omission")


def test_same_facts_but_weaker_applicability_semantics_is_detected() -> None:
    weak = ApplicabilityPredicate.any_of(
        ApplicabilityPredicate.fact_equals("language", "python"),
        ApplicabilityPredicate.fact_equals("framework", "flask"),
    )
    assert_attack(rebuild(contract(), applicability=weak), "applicability_semantics_weakening")


def test_material_input_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), material_inputs=()), "material_input_omission")


def test_falsifier_family_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), mandatory_falsifier_families=("delete-authz-decorator",)), "falsifier_family_omission")


def test_mandatory_external_review_lane_cardinality_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), external_review_lanes=(ExternalReviewLane.create("hostile-external", 1),)), "external_review_lane_cardinality_weakening")


def test_negative_applicability_and_unknown_fallback_are_authoring_obligations() -> None:
    p = profile()
    malformed = dataclasses.replace(contract(), negative_applicability=None)
    result = audit_contract_authoring(malformed, p)
    assert result.status is AuthoringAuditStatus.DEFICIENT
    families = {x.family for x in result.findings}
    assert "noncanonical_contract" in families
    assert "negative_applicability_burden_missing" in families


def test_profile_requires_independent_basis_and_is_content_addressed() -> None:
    a = profile()
    assert len(a.independent_basis_ids) >= 1
    assert a.profile_hash
    assert AuthoringAuditProfile.from_payload(a.to_payload()) == a
    assert a.required_premises[0].required_closure is ClosureGrade.EXACT


def test_qualification_escape_requires_suspension_or_revocation_and_impact_analysis() -> None:
    record = record_qualification_escape(
        registry_id="3" * 64,
        contract_id="route-authz",
        escaped_generation="contract-1",
        defect_family="material_input_omission",
        evidence_ids=("4" * 64,),
    )
    assert record.disposition is ACREscapeDisposition.SUSPEND_OR_REVOKE
    assert record.impact_analysis_required is True
    assert record.automatic_corrected_contract_promotion_allowed is False


def test_authoring_profile_cannot_be_contract_self_defined() -> None:
    c = contract()
    with pytest.raises(ValueError, match="independent"):
        AuthoringAuditProfile.create(
            profile_id="bad", generation="g", contract_id="route-authz", domain=c.domain,
            expected_applicability=c.applicability, independent_basis_ids=(), required_semantic_carriers=(),
            required_consumer_interpretation_families=(), required_affected_relations=(), required_collections=(),
            required_premises=(), required_repeated_authority_premise_families=(), required_obligations=(),
            required_material_inputs=(), required_coherence_rules=(), required_temporal_rules=(), required_falsifier_families=(),
            required_independence=(), required_external_review_lanes={}, require_negative_applicability_burden=True,
            require_unknown_fallback=True,
        )


def test_consumer_interpretation_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), consumer_interpretation_families=()), "consumer_interpretation_omission")


def test_affected_relation_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), affected_relation_families=()), "affected_relation_omission")


def test_premise_and_obligation_omission_attacks_are_detected() -> None:
    assert_attack(rebuild(contract(), mandatory_premises=()), "premise_omission")
    assert_attack(rebuild(contract(), mandatory_obligations=()), "obligation_omission")


def test_premise_obligation_and_material_input_closure_weakening_attacks_are_detected() -> None:
    assert_attack(
        rebuild(contract(), mandatory_premises=(ContractRequirement.create("route-discovery", ClosureGrade.PARTIAL),)),
        "closure_grade_weakening",
    )
    assert_attack(
        rebuild(contract(), mandatory_obligations=(ContractRequirement.create("authz-preserved", ClosureGrade.PARTIAL),)),
        "closure_grade_weakening",
    )
    assert_attack(
        rebuild(contract(), material_inputs=(ContractRequirement.create("router-config", ClosureGrade.PARTIAL),)),
        "closure_grade_weakening",
    )


def test_repeated_authority_premise_omission_attack_is_detected() -> None:
    assert_attack(rebuild(contract(), repeated_authority_premise_families=()), "repeated_authority_premise_omission")


def test_coherence_temporal_and_independence_omissions_are_detected() -> None:
    assert_attack(rebuild(contract(), coherence_rules=()), "coherence_rule_omission")
    assert_attack(rebuild(contract(), temporal_rules=()), "temporal_rule_omission")
    assert_attack(rebuild(contract(), required_independence=()), "independence_rule_omission")


def test_closure_grade_weakening_attack_is_detected() -> None:
    weak = CollectionRequirement.create("routes", CollectionSemantics.MULTISET, CardinalitySpec.bounded_n(500), ClosureGrade.PARTIAL)
    assert_attack(rebuild(contract(), collections=(weak,)), "closure_grade_weakening")


def test_exact_bounded_domain_generation_is_authoring_scope() -> None:
    changed = BoundedDomain.create(
        domain_id="python.web-route.v1", generation="domain-2", dimensions={"max_files": 200, "max_routes": 500}
    )
    assert_attack(rebuild(contract(), domain=changed), "audit_scope_mismatch")


def test_direct_noncanonical_profile_cannot_return_clean() -> None:
    malformed = dataclasses.replace(profile(), profile_hash="0" * 64)
    result = audit_contract_authoring(contract(), malformed)
    assert result.status is AuthoringAuditStatus.DEFICIENT
    assert "noncanonical_profile" in {x.family for x in result.findings}


def test_mutable_generation_alias_is_not_authoring_clean() -> None:
    assert_attack(rebuild(contract(), generation="latest"), "mutable_generation_alias")


def test_qualification_escape_rejects_mutable_generation_alias() -> None:
    with pytest.raises(ValueError, match="mutable"):
        record_qualification_escape(
            registry_id="a" * 64,
            contract_id="route-authz",
            escaped_generation="latest",
            defect_family="falsifier_family_omission",
            evidence_ids=("b" * 64,),
        )


def test_qualification_escape_is_permanent_evidence_and_round_trips() -> None:
    from main_review.acr_authoring_audit import ACRQualificationEscapeRecord
    record = record_qualification_escape(
        registry_id="a" * 64,
        contract_id="route-authz",
        escaped_generation="contract-1",
        defect_family="falsifier_family_omission",
        evidence_ids=("b" * 64, "c" * 64),
    )
    assert record.permanent_qualification_evidence is True
    assert ACRQualificationEscapeRecord.from_payload(record.to_payload()) == record
    payload = record.to_payload(); payload["automatic_corrected_contract_promotion_allowed"] = True
    with pytest.raises(ValueError):
        ACRQualificationEscapeRecord.from_payload(payload)
