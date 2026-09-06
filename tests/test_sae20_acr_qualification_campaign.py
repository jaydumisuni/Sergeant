from __future__ import annotations
import dataclasses
from main_review.acr_authoring_audit import AuthoringAuditProfile, AuthoringAuditStatus, audit_contract_authoring
from main_review.assurance_contract_registry import *

# Cross-domain ACR schema fixture only. It does not execute TypeScript or claim
# unrelated-language transfer evidence.

def contract() -> ACRContract:
    d=BoundedDomain.create(domain_id='typescript.express-route.v1',generation='transfer-domain-1',dimensions={'max_files':120,'max_routes':300})
    a=ApplicabilityPredicate.all_of(ApplicabilityPredicate.fact_equals('language','typescript'),ApplicabilityPredicate.fact_equals('framework','express'))
    return ACRContract.create(contract_id='express-route-authz',generation='transfer-contract-1',domain=d,applicability=a,bound_subject_variables=('route','handler'),semantic_carrier_families=('express-routes','middleware-chain'),consumer_interpretation_families=('express-router',),affected_relation_families=('route_to_handler','handler_to_middleware'),collections=(CollectionRequirement.create('middleware-chain',CollectionSemantics.ORDER,CardinalitySpec.bounded_n(32),ClosureGrade.EXACT),),mandatory_premises=(ContractRequirement.create('route-discovery',ClosureGrade.EXACT),),repeated_authority_premise_families=('review-world',),mandatory_obligations=(ContractRequirement.create('authz-middleware-preserved',ClosureGrade.EXACT),),admissible_proof_classes=('mechanical',),material_inputs=(ContractRequirement.create('express-router-config',ClosureGrade.EXACT),),coherence_rules=('same-express-generation',),temporal_rules=('evidence-not-older-than-world',),mandatory_falsifier_families=('delete-authz-middleware','reorder-middleware'),required_independence=('qualification-corpus-independent',),permitted_capabilities=('typescript-ast',),negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),external_review_lanes=(ExternalReviewLane.create('hostile-external',2),),unsupported_fallback='UNKNOWN')


def profile() -> AuthoringAuditProfile:
    c=contract()
    return AuthoringAuditProfile.create(profile_id='express-route-authz-authoring-v1',generation='transfer-audit-profile-1',contract_id=c.contract_id,contract_generation=c.generation,domain_id=c.domain.domain_id,domain_hash=c.domain.domain_hash,expected_applicability=c.applicability,independent_basis_ids=('a'*64,'b'*64),required_applicability_facts=('framework','language'),required_bound_subject_variables=c.bound_subject_variables,required_semantic_carriers=c.semantic_carrier_families,required_consumer_interpretation_families=c.consumer_interpretation_families,required_affected_relations=c.affected_relation_families,required_collections=c.collections,required_premises=c.mandatory_premises,required_repeated_authority_premise_families=c.repeated_authority_premise_families,required_obligations=c.mandatory_obligations,required_admissible_proof_classes=c.admissible_proof_classes,required_material_inputs=c.material_inputs,required_coherence_rules=c.coherence_rules,required_temporal_rules=c.temporal_rules,required_falsifier_families=c.mandatory_falsifier_families,required_independence=c.required_independence,required_permitted_capabilities=c.permitted_capabilities,required_external_review_lanes={'hostile-external':2},require_negative_applicability_burden=True,require_unknown_fallback=True)


def rebuild(**overrides: object) -> ACRContract:
    fields=contract().constructor_fields(); fields.update(overrides); return ACRContract.create(**fields)


def families(candidate: ACRContract) -> set[str]:
    result=audit_contract_authoring(candidate,profile()); assert result.qualifies_contract is False
    return {finding.family for finding in result.findings}


def test_cross_domain_clean_control_never_self_qualifies() -> None:
    result=audit_contract_authoring(contract(),profile())
    assert result.status is AuthoringAuditStatus.CLEAN and result.findings == () and result.qualifies_contract is False


def test_cross_domain_applicability_and_negative_burden_are_fail_closed() -> None:
    c=contract()
    assert c.evaluate(ApplicabilityContext.exact({'language':'typescript','framework':'express'})).truth is ApplicabilityTruth.TRUE
    assert c.evaluate(ApplicabilityContext.exact({'language':'typescript','framework':'koa'})).truth is ApplicabilityTruth.FALSE
    assert c.evaluate(ApplicabilityContext.partial({'language':'typescript'})).truth is ApplicabilityTruth.UNKNOWN
    absent=ApplicabilityPredicate.fact_absent('framework')
    assert absent.evaluate(ApplicabilityContext.partial({})).truth is ApplicabilityTruth.UNKNOWN
    assert absent.evaluate(ApplicabilityContext.exact({})).truth is ApplicabilityTruth.TRUE


def test_deletion_and_undercount_mutations_are_detected() -> None:
    attacks=((rebuild(semantic_carrier_families=('express-routes',)),'semantic_carrier_omission'),(rebuild(consumer_interpretation_families=()),'consumer_interpretation_omission'),(rebuild(affected_relation_families=('route_to_handler',)),'affected_relation_omission'),(rebuild(mandatory_premises=()),'premise_omission'),(rebuild(mandatory_obligations=()),'obligation_omission'),(rebuild(material_inputs=()),'material_input_omission'),(rebuild(mandatory_falsifier_families=('delete-authz-middleware',)),'falsifier_family_omission'),(rebuild(external_review_lanes=(ExternalReviewLane.create('hostile-external',1),)),'external_review_lane_cardinality_weakening'))
    for candidate, expected in attacks: assert expected in families(candidate)


def test_collection_semantics_cardinality_order_and_closure_cannot_weaken() -> None:
    set_version=CollectionRequirement.create('middleware-chain',CollectionSemantics.SET,CardinalitySpec.bounded_n(32),ClosureGrade.EXACT)
    undercount=CollectionRequirement.create('middleware-chain',CollectionSemantics.ORDER,CardinalitySpec.bounded_n(8),ClosureGrade.EXACT)
    partial=CollectionRequirement.create('middleware-chain',CollectionSemantics.ORDER,CardinalitySpec.bounded_n(32),ClosureGrade.PARTIAL)
    assert 'collection_semantics_or_cardinality_weakening' in families(rebuild(collections=(set_version,)))
    assert 'collection_semantics_or_cardinality_weakening' in families(rebuild(collections=(undercount,)))
    assert 'closure_grade_weakening' in families(rebuild(collections=(partial,)))


def test_applicability_and_authority_premises_cannot_drift() -> None:
    changed=ApplicabilityPredicate.any_of(*contract().applicability.children)
    assert 'applicability_semantics_mismatch' in families(rebuild(applicability=changed))
    assert 'repeated_authority_premise_omission' in families(rebuild(repeated_authority_premise_families=()))
    assert 'coherence_rule_omission' in families(rebuild(coherence_rules=()))
    assert 'temporal_rule_omission' in families(rebuild(temporal_rules=()))
    assert 'independence_rule_omission' in families(rebuild(required_independence=()))


def test_profile_tamper_fails_before_requirements_are_trusted() -> None:
    p=profile(); tampered=dataclasses.replace(p,required_semantic_carriers=(),profile_hash=p.profile_hash)
    result=audit_contract_authoring(rebuild(semantic_carrier_families=('express-routes',)),tampered)
    assert result.status is AuthoringAuditStatus.DEFICIENT
    assert {finding.family for finding in result.findings} == {'profile_noncanonical_or_malformed'}
