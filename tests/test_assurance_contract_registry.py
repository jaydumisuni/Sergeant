from __future__ import annotations
import dataclasses
import pytest
from main_review.assurance_contract_registry import *

def domain(): return BoundedDomain.create(domain_id='python.web-route.v1',generation='domain-1',dimensions={'max_files':200,'max_routes':500})
def predicate(): return ApplicabilityPredicate.all_of(ApplicabilityPredicate.fact_equals('language','python'),ApplicabilityPredicate.fact_equals('framework','flask'))
def contract():
    return ACRContract.create(contract_id='route-authz',generation='contract-1',domain=domain(),applicability=predicate(),bound_subject_variables=('route',),semantic_carrier_families=('routes','decorators'),consumer_interpretation_families=('flask-router',),affected_relation_families=('route_to_handler',),collections=(CollectionRequirement.create('routes',CollectionSemantics.SET,CardinalitySpec.bounded_n(500),ClosureGrade.EXACT),),mandatory_premises=(ContractRequirement.create('route-discovery',ClosureGrade.EXACT),),repeated_authority_premise_families=('review-world',),mandatory_obligations=(ContractRequirement.create('authz-preserved',ClosureGrade.EXACT),),admissible_proof_classes=('mechanical',),material_inputs=(ContractRequirement.create('router-config',ClosureGrade.EXACT),),coherence_rules=('same-framework-generation',),temporal_rules=('evidence-not-older-than-world',),mandatory_falsifier_families=('delete-authz-decorator',),required_independence=('qualification-corpus-independent',),permitted_capabilities=('python-ast',),negative_applicability=NegativeApplicabilityBurden.proven_no_match(ClosureGrade.EXACT),external_review_lanes=(ExternalReviewLane.create('hostile-external',1),),unsupported_fallback='UNKNOWN')

def test_three_valued_applicability_conserves_unknown():
    c=contract(); assert c.evaluate(ApplicabilityContext.exact({'language':'python','framework':'flask'})).truth is ApplicabilityTruth.TRUE; assert c.evaluate(ApplicabilityContext.exact({'language':'python','framework':'django'})).truth is ApplicabilityTruth.FALSE
    r=c.evaluate(ApplicabilityContext.partial({'language':'python'})); assert r.truth is ApplicabilityTruth.UNKNOWN and 'framework' in r.unresolved_facts

def test_missing_fact_cannot_become_false_merely_because_it_is_absent(): assert contract().evaluate(ApplicabilityContext.exact({'language':'python'})).truth is ApplicabilityTruth.UNKNOWN
def test_proven_absence_requires_sufficient_closure():
    p=ApplicabilityPredicate.fact_absent('framework'); assert p.evaluate(ApplicabilityContext.partial({})).truth is ApplicabilityTruth.UNKNOWN; assert p.evaluate(ApplicabilityContext.exact({})).truth is ApplicabilityTruth.TRUE; assert p.evaluate(ApplicabilityContext.exact({'framework':'flask'})).truth is ApplicabilityTruth.FALSE

def test_registry_is_content_addressed_canonical_and_order_independent():
    a=contract(); b=dataclasses.replace(a,contract_id='route-authn',contract_id_hash=''); b=ACRContract.create(**b.constructor_fields()); r1=ACRRegistry.create(generation='acr-gen-1',contracts=(a,b)); r2=ACRRegistry.create(generation='acr-gen-1',contracts=(b,a)); assert r1.registry_id==r2.registry_id; assert [x.contract_id for x in r1.contracts]==['route-authn','route-authz']; assert ACRRegistry.from_payload(r1.to_payload())==r1

def test_registry_rejects_duplicate_contract_identity():
    with pytest.raises(RegistryError,match='duplicate'): ACRRegistry.create(generation='acr-gen-1',contracts=(contract(),contract()))
def test_contract_payload_is_strict_and_id_tamper_is_rejected():
    p=contract().to_payload(); p['contract_id_hash']='0'*64
    with pytest.raises(RegistryError,match='contract_id_hash'): ACRContract.from_payload(p)
def test_collection_semantics_and_cardinality_are_not_interchangeable():
    m=CollectionRequirement.create('calls',CollectionSemantics.MULTISET,CardinalitySpec.exactly_one(),ClosureGrade.EXACT); o=CollectionRequirement.create('calls',CollectionSemantics.ORDER,CardinalitySpec.exactly_one(),ClosureGrade.EXACT); assert m.to_payload()!=o.to_payload(); assert CardinalitySpec.bounded_n(2).to_payload()!=CardinalitySpec.bounded_n(3).to_payload()
def test_bounded_domain_rejects_unbounded_or_nonpositive_limits():
    with pytest.raises(RegistryError): BoundedDomain.create(domain_id='x',generation='g',dimensions={})
    with pytest.raises(RegistryError): BoundedDomain.create(domain_id='x',generation='g',dimensions={'n':0})
def test_candidate_contract_has_no_self_qualification_field_or_path():
    p=contract().to_payload(); assert 'qualified' not in p and 'qualification_state' not in p and p['self_qualification_allowed'] is False
def test_unknown_fallback_is_mandatory():
    kw=contract().constructor_fields(); kw['unsupported_fallback']='FALSE'
    with pytest.raises(RegistryError,match='UNKNOWN'): ACRContract.create(**kw)
def test_negative_applicability_requires_proven_no_match_burden():
    kw=contract().constructor_fields(); kw['negative_applicability']=None
    with pytest.raises(RegistryError,match='negative applicability'): ACRContract.create(**kw)
def test_registry_rejects_two_generations_of_same_contract_id():
    first=contract(); kw=first.constructor_fields(); kw['generation']='contract-2'; second=ACRContract.create(**kw)
    with pytest.raises(RegistryError,match='duplicate contract_id'): ACRRegistry.create(generation='acr-gen-1',contracts=(first,second))
def test_persisted_boolean_fields_are_type_strict():
    p=contract().to_payload(); p['self_qualification_allowed']=0
    with pytest.raises(RegistryError,match='self-qualify'): ACRContract.from_payload(p)
def test_registry_missing_mandatory_evaluation_is_unknown_not_silently_absent():
    e=ACRRegistry.create(generation='acr-gen-1',contracts=(contract(),)).evaluate_all({}); assert len(e)==1 and e[0].truth is ApplicabilityTruth.UNKNOWN and e[0].evaluation_present is False and e[0].unresolved_facts==('<missing-evaluation>',)
def test_registry_evaluates_every_mandatory_contract_and_rejects_unknown_context_keys():
    r=ACRRegistry.create(generation='acr-gen-1',contracts=(contract(),)); e=r.evaluate_all({'route-authz':ApplicabilityContext.exact({'language':'python','framework':'flask'})}); assert e[0].truth is ApplicabilityTruth.TRUE and e[0].evaluation_present is True
    with pytest.raises(RegistryError,match='unknown contract'): r.evaluate_all({'not-in-registry':ApplicabilityContext.exact({})})
def test_v1_contract_is_mandatory_and_persisted_downgrade_is_rejected():
    p=contract().to_payload(); assert p['mandatory'] is True; p['mandatory']=False
    with pytest.raises(RegistryError,match='mandatory'): ACRContract.from_payload(p)

# Review regressions

def test_mutable_expected_input_is_detached_from_content_addressed_predicate():
    expected={'roles':['admin']}; p=ApplicabilityPredicate.fact_equals('policy',expected); before=p.to_payload(); expected['roles'].append('guest'); assert p.to_payload()==before; assert p.evaluate(ApplicabilityContext.exact({'policy':{'roles':['admin']}})).truth is ApplicabilityTruth.TRUE

def test_serialized_expected_value_is_detached_from_predicate_identity():
    p=ApplicabilityPredicate.fact_equals('policy',{'roles':['admin']}); payload=p.to_payload(); payload['expected']['roles'].append('guest'); assert p.to_payload()['expected']=={'roles':['admin']}

def test_raw_mutable_expected_constructor_bypass_is_rejected():
    raw=ApplicabilityPredicate('fact_equals','policy',{'roles':['admin']},())
    with pytest.raises(RegistryError,match='immutable'): raw.validate()

def test_nested_expected_json_roundtrips_and_evaluates_structurally():
    p=ApplicabilityPredicate.fact_equals('policy',{'roles':['admin'],'limits':[1,2]}); assert ApplicabilityPredicate.from_payload(p.to_payload())==p; assert p.evaluate(ApplicabilityContext.exact({'policy':{'limits':[1,2],'roles':['admin']}})).truth is ApplicabilityTruth.TRUE
