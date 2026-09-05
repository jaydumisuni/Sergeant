from __future__ import annotations
import dataclasses
import pytest
from main_review.acr_authoring_audit import *
from main_review.assurance_contract_registry import *

def base_domain(): return BoundedDomain.create(domain_id='python.web-route.v1',generation='domain-1',dimensions={'max_files':200,'max_routes':500})
def base_app(): return ApplicabilityPredicate.all_of(ApplicabilityPredicate.fact_equals('language','python'),ApplicabilityPredicate.fact_equals('framework','flask'))
def contract():
    return ACRContract.create(contract_id='route-authz',generation='contract-1',domain=base_domain(),applicability=base_app(),bound_subject_variables=('route',),semantic_carrier_families=('routes','decorators'),consumer_interpretation_families=('flask-router',),affected_relation_families=('route_to_handler',),collections=(CollectionRequirement.create('routes',CollectionSemantics.MULTISET,CardinalitySpec.bounded_n(500),ClosureGrade.EXACT),),mandatory_premises=(ContractRequirement.create('route-discovery',ClosureGrade.EXACT),),repeated_authority_premise_families=('review-world',),mandatory_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.EXACT),),admissible_proof_classes=('mechanical',),material_inputs=(ContractRequirement.create('router-config',ClosureGrade.EXACT),),coherence_rules=('same-framework-generation',),temporal_rules=('evidence-not-older-than-world',),mandatory_falsifier_families=('delete-authz-decorator','swap-route-order'),required_independence=('qualification-corpus-independent',),permitted_capabilities=('python-ast',),negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),external_review_lanes=(ExternalReviewLane.create('hostile-external',2),),unsupported_fallback='UNKNOWN')
def profile():
    c=contract()
    return AuthoringAuditProfile.create(profile_id='route-authz-authoring-v3',generation='audit-profile-3',contract_id='route-authz',contract_generation=c.generation,domain_id=c.domain.domain_id,domain_hash=c.domain.domain_hash,expected_applicability=c.applicability,independent_basis_ids=('1'*64,'2'*64),required_applicability_facts=('language','framework'),required_bound_subject_variables=('route',),required_semantic_carriers=('routes','decorators'),required_consumer_interpretation_families=('flask-router',),required_affected_relations=('route_to_handler',),required_collections=(CollectionRequirement.create('routes',CollectionSemantics.MULTISET,CardinalitySpec.bounded_n(500),ClosureGrade.EXACT),),required_premises=(ContractRequirement.create('route-discovery',ClosureGrade.EXACT),),required_repeated_authority_premise_families=('review-world',),required_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.EXACT),),required_admissible_proof_classes=('mechanical',),required_material_inputs=(ContractRequirement.create('router-config',ClosureGrade.EXACT),),required_coherence_rules=('same-framework-generation',),required_temporal_rules=('evidence-not-older-than-world',),required_falsifier_families=('delete-authz-decorator','swap-route-order'),required_independence=('qualification-corpus-independent',),required_permitted_capabilities=('python-ast',),required_external_review_lanes={'hostile-external':2},require_negative_applicability_burden=True,require_unknown_fallback=True)
def rebuild(c,**overrides): kw=c.constructor_fields(); kw.update(overrides); return ACRContract.create(**kw)
def families(c): return {x.family for x in audit_contract_authoring(c,profile()).findings}
def assert_attack(c,f): r=audit_contract_authoring(c,profile()); assert r.status is AuthoringAuditStatus.DEFICIENT and f in {x.family for x in r.findings} and r.qualifies_contract is False

def test_clean_contract_is_audit_clean_but_not_qualified():
    r=audit_contract_authoring(contract(),profile()); assert r.status is AuthoringAuditStatus.CLEAN and r.findings==() and r.qualifies_contract is False
def test_omission_attack_is_detected(): assert_attack(rebuild(contract(),semantic_carrier_families=('routes',)),'semantic_carrier_omission')
def test_cardinality_semantics_weakening_attack_is_detected(): assert_attack(rebuild(contract(),collections=(CollectionRequirement.create('routes',CollectionSemantics.SET,CardinalitySpec.bounded_n(500),ClosureGrade.EXACT),)),'collection_semantics_or_cardinality_weakening')
def test_applicability_trigger_omission_attack_is_detected(): assert_attack(rebuild(contract(),applicability=ApplicabilityPredicate.fact_equals('language','python')),'applicability_omission')
def test_material_input_omission_attack_is_detected(): assert_attack(rebuild(contract(),material_inputs=()),'material_input_omission')
def test_falsifier_family_omission_attack_is_detected(): assert_attack(rebuild(contract(),mandatory_falsifier_families=('delete-authz-decorator',)),'falsifier_family_omission')
def test_mandatory_external_review_lane_cardinality_attack_is_detected(): assert_attack(rebuild(contract(),external_review_lanes=(ExternalReviewLane.create('hostile-external',1),)),'external_review_lane_cardinality_weakening')
def test_negative_applicability_and_unknown_fallback_are_authoring_obligations():
    malformed=dataclasses.replace(contract(),negative_applicability=None); fs={x.family for x in audit_contract_authoring(malformed,profile()).findings}; assert 'negative_applicability_burden_missing' in fs and 'contract_noncanonical_or_malformed' in fs
def test_profile_requires_independent_basis_and_is_content_addressed():
    p=profile(); assert p.independent_basis_ids and p.profile_hash and AuthoringAuditProfile.from_payload(p.to_payload())==p
def test_qualification_escape_requires_suspension_or_revocation_and_impact_analysis():
    r=record_qualification_escape(registry_id='3'*64,contract_id='route-authz',escaped_generation='contract-1',defect_family='material_input_omission',evidence_ids=('4'*64,)); assert r.disposition is ACREscapeDisposition.SUSPEND_OR_REVOKE and r.impact_analysis_required is True and r.automatic_corrected_contract_promotion_allowed is False
def test_authoring_profile_cannot_be_contract_self_defined():
    c=contract()
    with pytest.raises(ValueError,match='independent'):
        AuthoringAuditProfile.create(profile_id='bad',generation='g',contract_id=c.contract_id,contract_generation=c.generation,domain_id=c.domain.domain_id,domain_hash=c.domain.domain_hash,expected_applicability=c.applicability,independent_basis_ids=(),required_applicability_facts=('language','framework'),required_bound_subject_variables=(),required_semantic_carriers=(),required_consumer_interpretation_families=(),required_affected_relations=(),required_collections=(),required_premises=(),required_repeated_authority_premise_families=(),required_obligations=(),required_admissible_proof_classes=(),required_material_inputs=(),required_coherence_rules=(),required_temporal_rules=(),required_falsifier_families=(),required_independence=(),required_permitted_capabilities=(),required_external_review_lanes={},require_negative_applicability_burden=True,require_unknown_fallback=True)
def test_consumer_interpretation_omission_attack_is_detected(): assert_attack(rebuild(contract(),consumer_interpretation_families=()),'consumer_interpretation_omission')
def test_affected_relation_omission_attack_is_detected(): assert_attack(rebuild(contract(),affected_relation_families=()),'affected_relation_omission')
def test_premise_and_obligation_omission_attacks_are_detected(): assert_attack(rebuild(contract(),mandatory_premises=()),'premise_omission'); assert_attack(rebuild(contract(),mandatory_obligations=()),'obligation_omission')
def test_repeated_authority_premise_omission_attack_is_detected(): assert_attack(rebuild(contract(),repeated_authority_premise_families=()),'repeated_authority_premise_omission')
def test_coherence_temporal_and_independence_omissions_are_detected(): assert_attack(rebuild(contract(),coherence_rules=()),'coherence_rule_omission'); assert_attack(rebuild(contract(),temporal_rules=()),'temporal_rule_omission'); assert_attack(rebuild(contract(),required_independence=()),'independence_rule_omission')
def test_closure_grade_weakening_attack_is_detected(): assert_attack(rebuild(contract(),collections=(CollectionRequirement.create('routes',CollectionSemantics.MULTISET,CardinalitySpec.bounded_n(500),ClosureGrade.PARTIAL),)),'closure_grade_weakening')
def test_qualification_escape_is_permanent_evidence_and_round_trips():
    r=record_qualification_escape(registry_id='a'*64,contract_id='route-authz',escaped_generation='contract-1',defect_family='falsifier_family_omission',evidence_ids=('b'*64,'c'*64)); assert r.permanent_qualification_evidence is True and ACRQualificationEscapeRecord.from_payload(r.to_payload())==r; p=r.to_payload(); p['automatic_corrected_contract_promotion_allowed']=True
    with pytest.raises(ValueError): ACRQualificationEscapeRecord.from_payload(p)

# Hostile review regressions

def test_profile_binds_exact_domain_hash_not_just_domain_id():
    changed=BoundedDomain.create(domain_id=contract().domain.domain_id,generation='domain-2',dimensions={'max_files':200,'max_routes':500}); assert_attack(rebuild(contract(),domain=changed),'audit_scope_mismatch')
def test_profile_rejects_dimension_expansion_under_same_domain_id_and_generation():
    changed=BoundedDomain.create(domain_id=contract().domain.domain_id,generation=contract().domain.generation,dimensions={'max_files':200,'max_routes':999}); assert_attack(rebuild(contract(),domain=changed),'audit_scope_mismatch')
def test_applicability_operator_escape_is_detected():
    changed=ApplicabilityPredicate.any_of(ApplicabilityPredicate.fact_equals('language','python'),ApplicabilityPredicate.fact_equals('framework','flask')); assert_attack(rebuild(contract(),applicability=changed),'applicability_semantics_mismatch')
def test_applicability_expected_value_escape_is_detected():
    changed=ApplicabilityPredicate.all_of(ApplicabilityPredicate.fact_equals('language','python'),ApplicabilityPredicate.fact_equals('framework','django')); assert_attack(rebuild(contract(),applicability=changed),'applicability_semantics_mismatch')
def test_applicability_negation_escape_is_detected(): assert_attack(rebuild(contract(),applicability=ApplicabilityPredicate.negate(base_app())),'applicability_semantics_mismatch')
def test_premise_closure_downgrade_is_detected(): assert_attack(rebuild(contract(),mandatory_premises=(ContractRequirement.create('route-discovery',ClosureGrade.UNKNOWN),)),'premise_closure_grade_weakening')
def test_obligation_closure_downgrade_is_detected(): assert_attack(rebuild(contract(),mandatory_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.PARTIAL),)),'obligation_closure_grade_weakening')
def test_material_input_closure_downgrade_is_detected(): assert_attack(rebuild(contract(),material_inputs=(ContractRequirement.create('router-config',ClosureGrade.UNKNOWN),)),'material_input_closure_grade_weakening')
def test_malformed_negative_burden_with_wrong_mode_or_closure_is_detected():
    malformed=dataclasses.replace(contract(),negative_applicability=NegativeApplicabilityBurden('WRONG',ClosureGrade.UNKNOWN)); fs={x.family for x in audit_contract_authoring(malformed,profile()).findings}; assert 'negative_applicability_burden_missing' in fs and 'contract_noncanonical_or_malformed' in fs
def test_bound_subject_variable_drift_is_detected(): assert_attack(rebuild(contract(),bound_subject_variables=('handler',)),'bound_subject_variables_mismatch')
def test_admissible_proof_class_drift_is_detected(): assert_attack(rebuild(contract(),admissible_proof_classes=('heuristic',)),'admissible_proof_classes_mismatch')
def test_permitted_capability_drift_is_detected(): assert_attack(rebuild(contract(),permitted_capabilities=()),'permitted_capabilities_mismatch')
def test_profile_rejects_applicability_fact_roster_inconsistent_with_expected_predicate():
    c=contract(); p=profile().to_payload(); p['required_applicability_facts']=['language']
    with pytest.raises(ValueError,match='exactly match'): AuthoringAuditProfile.create(profile_id=p['profile_id'],generation=p['generation'],contract_id=p['contract_id'],contract_generation=p['contract_generation'],domain_id=p['domain_id'],domain_hash=p['domain_hash'],expected_applicability=ApplicabilityPredicate.from_payload(p['expected_applicability']),independent_basis_ids=p['independent_basis_ids'],required_applicability_facts=p['required_applicability_facts'],required_bound_subject_variables=p['required_bound_subject_variables'],required_semantic_carriers=p['required_semantic_carriers'],required_consumer_interpretation_families=p['required_consumer_interpretation_families'],required_affected_relations=p['required_affected_relations'],required_collections=tuple(CollectionRequirement.from_payload(x) for x in p['required_collections']),required_premises=tuple(ContractRequirement.from_payload(x) for x in p['required_premises']),required_repeated_authority_premise_families=p['required_repeated_authority_premise_families'],required_obligations=tuple(ContractRequirement.from_payload(x) for x in p['required_obligations']),required_admissible_proof_classes=p['required_admissible_proof_classes'],required_material_inputs=tuple(ContractRequirement.from_payload(x) for x in p['required_material_inputs']),required_coherence_rules=p['required_coherence_rules'],required_temporal_rules=p['required_temporal_rules'],required_falsifier_families=p['required_falsifier_families'],required_independence=p['required_independence'],required_permitted_capabilities=p['required_permitted_capabilities'],required_external_review_lanes=p['required_external_review_lanes'],require_negative_applicability_burden=True,require_unknown_fallback=True)

def test_arbitrary_constructor_bypass_malformed_collection_fails_closed_without_crashing():
    malformed=dataclasses.replace(contract(),collections=(object(),))
    result=audit_contract_authoring(malformed,profile())
    assert result.status is AuthoringAuditStatus.DEFICIENT
    assert 'contract_noncanonical_or_malformed' in {x.family for x in result.findings}
