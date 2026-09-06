from __future__ import annotations
import dataclasses, math
import pytest
from main_review.assurance_contract_registry import *
from main_review.assurance_contract_registry import _FrozenJSONMap
from main_review.acr_authoring_audit import *


def domain(): return BoundedDomain.create(domain_id='python.web-route.v1',generation='domain-1',dimensions={'max_files':200,'max_routes':500})
def predicate(): return ApplicabilityPredicate.all_of(ApplicabilityPredicate.fact_equals('language','python'),ApplicabilityPredicate.fact_equals('framework','flask'))
def contract():
    return ACRContract.create(contract_id='route-authz',generation='contract-1',domain=domain(),applicability=predicate(),bound_subject_variables=('route',),semantic_carrier_families=('routes','decorators'),consumer_interpretation_families=('flask-router',),affected_relation_families=('route_to_handler',),collections=(CollectionRequirement.create('routes',CollectionSemantics.MULTISET,CardinalitySpec.bounded_n(500),ClosureGrade.EXACT),),mandatory_premises=(ContractRequirement.create('route-discovery',ClosureGrade.EXACT),),repeated_authority_premise_families=('review-world',),mandatory_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.EXACT),),admissible_proof_classes=('mechanical',),material_inputs=(ContractRequirement.create('router-config',ClosureGrade.EXACT),),coherence_rules=('same-framework-generation',),temporal_rules=('evidence-not-older-than-world',),mandatory_falsifier_families=('delete-authz-decorator','swap-route-order'),required_independence=('qualification-corpus-independent',),permitted_capabilities=('python-ast',),negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),external_review_lanes=(ExternalReviewLane.create('hostile-external',2),),unsupported_fallback='UNKNOWN')
def profile():
    c=contract()
    return AuthoringAuditProfile.create(profile_id='route-authz-authoring-v3',generation='audit-profile-3',contract_id=c.contract_id,contract_generation=c.generation,domain_id=c.domain.domain_id,domain_hash=c.domain.domain_hash,expected_applicability=c.applicability,independent_basis_ids=('1'*64,'2'*64),required_applicability_facts=('framework','language'),required_bound_subject_variables=('route',),required_semantic_carriers=('routes','decorators'),required_consumer_interpretation_families=('flask-router',),required_affected_relations=('route_to_handler',),required_collections=c.collections,required_premises=c.mandatory_premises,required_repeated_authority_premise_families=('review-world',),required_obligations=c.mandatory_obligations,required_admissible_proof_classes=('mechanical',),required_material_inputs=c.material_inputs,required_coherence_rules=('same-framework-generation',),required_temporal_rules=('evidence-not-older-than-world',),required_falsifier_families=('delete-authz-decorator','swap-route-order'),required_independence=('qualification-corpus-independent',),required_permitted_capabilities=('python-ast',),required_external_review_lanes={'hostile-external':2},require_negative_applicability_burden=True,require_unknown_fallback=True)
def rebuild(c,**overrides): kw=c.constructor_fields(); kw.update(overrides); return ACRContract.create(**kw)

# Existing foundation invariants.
def test_clean_roundtrip_and_audit():
    c=contract(); assert ACRContract.from_payload(c.to_payload())==c
    p=profile(); assert AuthoringAuditProfile.from_payload(p.to_payload())==p
    r=audit_contract_authoring(c,p); assert r.status is AuthoringAuditStatus.CLEAN and r.qualifies_contract is False

def test_three_valued_applicability():
    c=contract(); assert c.evaluate(ApplicabilityContext.exact({'language':'python','framework':'flask'})).truth is ApplicabilityTruth.TRUE
    assert c.evaluate(ApplicabilityContext.exact({'language':'python','framework':'django'})).truth is ApplicabilityTruth.FALSE
    assert c.evaluate(ApplicabilityContext.partial({'language':'python'})).truth is ApplicabilityTruth.UNKNOWN

def test_mutable_expected_is_detached():
    v={'roles':['admin']}; p=ApplicabilityPredicate.fact_equals('policy',v); before=p.to_payload(); v['roles'].append('guest'); assert p.to_payload()==before
    payload=p.to_payload(); payload['expected']['roles'].append('guest'); assert p.to_payload()==before

def test_registry_missing_evaluation_unknown():
    r=ACRRegistry.create(generation='g',contracts=(contract(),)); e=r.evaluate_all({})[0]; assert e.truth is ApplicabilityTruth.UNKNOWN and e.evaluation_present is False

def test_domain_identity_and_applicability_semantics_audited():
    c=contract(); d=BoundedDomain.create(domain_id=c.domain.domain_id,generation='domain-2',dimensions=dict(c.domain.dimensions)); assert audit_contract_authoring(rebuild(c,domain=d),profile()).status is AuthoringAuditStatus.DEFICIENT
    app=ApplicabilityPredicate.any_of(*predicate().children); assert audit_contract_authoring(rebuild(c,applicability=app),profile()).status is AuthoringAuditStatus.DEFICIENT

def test_requirement_closure_downgrade_detected():
    c=rebuild(contract(),mandatory_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.PARTIAL),)); fam={x.family for x in audit_contract_authoring(c,profile()).findings}; assert 'obligation_closure_grade_weakening' in fam

# Exact-head hostile findings from 61f82eaa.
def test_profile_tamper_is_fail_closed_before_requirements_are_trusted():
    p=dataclasses.replace(profile(),required_semantic_carriers=(),profile_hash=profile().profile_hash)
    r=audit_contract_authoring(rebuild(contract(),semantic_carrier_families=('routes',)),p)
    assert r.status is AuthoringAuditStatus.DEFICIENT
    assert {x.family for x in r.findings}=={'profile_noncanonical_or_malformed'}

def test_profile_is_bound_to_exact_contract_generation():
    changed=rebuild(contract(),generation='contract-2')
    r=audit_contract_authoring(changed,profile())
    assert 'audit_scope_mismatch' in {x.family for x in r.findings}

def test_constructor_bypass_frozen_map_rejects_duplicate_and_unsorted_keys():
    duplicate=_FrozenJSONMap((('roles',1),('roles',2)))
    raw=ApplicabilityPredicate('fact_equals','policy',duplicate,())
    with pytest.raises(RegistryError): raw.validate()
    unsorted=_FrozenJSONMap((('z',1),('a',2)))
    with pytest.raises(RegistryError): ApplicabilityPredicate('fact_equals','policy',unsorted,()).validate()

def test_runtime_unsupported_applicability_values_conserve_unknown():
    p=ApplicabilityPredicate.fact_equals('policy',{'role':'admin'})
    for value in ({'role':{'admin'}}, object(), float('inf'), float('nan')):
        r=p.evaluate(ApplicabilityContext.exact({'policy':value}))
        assert r.truth is ApplicabilityTruth.UNKNOWN and r.unresolved_facts==('policy',)

def test_applicability_json_equality_is_type_sensitive_recursively():
    assert ApplicabilityPredicate.fact_equals('x',True).evaluate(ApplicabilityContext.exact({'x':1})).truth is ApplicabilityTruth.FALSE
    assert ApplicabilityPredicate.fact_equals('x',False).evaluate(ApplicabilityContext.exact({'x':0})).truth is ApplicabilityTruth.FALSE
    p=ApplicabilityPredicate.fact_equals('x',{'a':[True,1]})
    assert p.evaluate(ApplicabilityContext.exact({'x':{'a':[1,True]}})).truth is ApplicabilityTruth.FALSE
    assert p.evaluate(ApplicabilityContext.exact({'x':{'a':[True,1]}})).truth is ApplicabilityTruth.TRUE

def test_one_shot_iterables_are_materialized_once_not_silently_deleted():
    c=contract(); kw=c.constructor_fields()
    kw['mandatory_premises']=(x for x in c.mandatory_premises)
    kw['mandatory_obligations']=(x for x in c.mandatory_obligations)
    kw['material_inputs']=(x for x in c.material_inputs)
    kw['collections']=(x for x in c.collections)
    kw['external_review_lanes']=(x for x in c.external_review_lanes)
    rebuilt=ACRContract.create(**kw)
    assert rebuilt.mandatory_premises==c.mandatory_premises
    assert rebuilt.mandatory_obligations==c.mandatory_obligations
    assert rebuilt.material_inputs==c.material_inputs
    assert rebuilt.collections==c.collections
    assert rebuilt.external_review_lanes==c.external_review_lanes


def test_unit_cardinality_requires_json_integer_one_not_python_equal_alias():
    for kind in (CardinalityKind.ZERO_OR_ONE, CardinalityKind.EXACTLY_ONE):
        assert CardinalitySpec(kind,1).to_payload()=={"kind":kind.value,"maximum":1}
        for invalid in (True, 1.0):
            with pytest.raises(RegistryError):
                CardinalitySpec.from_payload({"kind":kind.value,"maximum":invalid})
