from __future__ import annotations
import copy
import pytest
from main_review.assurance_ledger import (
    AssuranceLedgerError,
    JudgeAssuranceLedger,
    LedgerEpistemicState,
    LedgerRecord,
    LedgerRecordKind,
)

H=lambda ch: ch*64
WORLD=H('a'); RAB=H('b'); SCOPE=H('c'); AUTH=H('d'); PROV=H('e')


def rec(*, kind=LedgerRecordKind.CLAIM, state=LedgerEpistemicState.ASSERTED,
        occurrence=0, scope_id=SCOPE, payload=None, aliases=('finding-demo',),
        related=(), authority_refs=(AUTH,), provenance_refs=(PROV,)):
    return LedgerRecord.create(
        kind=kind,
        review_world_id=WORLD,
        rab_id=RAB,
        scope_id=scope_id,
        generation='sae40-ledger-record-v1',
        occurrence=occurrence,
        epistemic_state=state,
        authority_refs=authority_refs,
        provenance_refs=provenance_refs,
        related_record_ids=related,
        payload=payload or {'message':'demo'},
        presentation_ids=aliases,
    )


def test_record_identity_is_full_crypto_and_legacy_id_is_not_authority():
    r=rec()
    assert len(r.record_id)==64
    assert r.record_id != 'finding-demo'
    assert r.presentation_ids == ('finding-demo',)


def test_record_identity_binds_world_rab_scope_state_and_occurrence():
    base=rec()
    variants=[
        LedgerRecord.create(**{**base.constructor_fields(), 'review_world_id':H('f')}),
        LedgerRecord.create(**{**base.constructor_fields(), 'rab_id':H('1')}),
        LedgerRecord.create(**{**base.constructor_fields(), 'scope_id':H('2')}),
        LedgerRecord.create(**{**base.constructor_fields(), 'epistemic_state':LedgerEpistemicState.UNKNOWN}),
        LedgerRecord.create(**{**base.constructor_fields(), 'occurrence':1}),
    ]
    assert all(v.record_id != base.record_id for v in variants)


def test_same_finding_id_different_occurrences_survive_ledger_dedup():
    a=rec(occurrence=0)
    b=rec(occurrence=1)
    ledger=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='ledger-v1',records=[a,b])
    assert len(ledger.records)==2
    assert {r.occurrence for r in ledger.records}=={0,1}


def test_unknown_is_not_erased_by_later_true_record():
    unknown=rec(state=LedgerEpistemicState.UNKNOWN,payload={'claim':'x'})
    true=rec(state=LedgerEpistemicState.TRUE,payload={'claim':'x'})
    left=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='ledger-v1',records=[unknown])
    right=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='ledger-v1',records=[true])
    merged=left.merge(right,generation='ledger-v2')
    assert {r.epistemic_state for r in merged.records} == {LedgerEpistemicState.UNKNOWN,LedgerEpistemicState.TRUE}


def test_contradiction_record_and_both_sides_survive_merge():
    yes=rec(state=LedgerEpistemicState.TRUE,payload={'claim':'x'})
    no=rec(state=LedgerEpistemicState.FALSE,payload={'claim':'x'})
    contradiction=rec(kind=LedgerRecordKind.CONTRADICTION,state=LedgerEpistemicState.CONTRADICTED,
                      payload={'reason':'conflict'},related=(yes.record_id,no.record_id),aliases=())
    ledger=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='ledger-v1',records=[yes,no,contradiction])
    assert len(ledger.records)==3
    assert any(r.kind is LedgerRecordKind.CONTRADICTION for r in ledger.records)


def test_merge_rejects_cross_world_or_cross_rab_substitution():
    left=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[rec()])
    other_world=JudgeAssuranceLedger.create(review_world_id=H('f'),rab_id=RAB,generation='v1',records=[])
    other_rab=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=H('1'),generation='v1',records=[])
    with pytest.raises(AssuranceLedgerError): left.merge(other_world,generation='v2')
    with pytest.raises(AssuranceLedgerError): left.merge(other_rab,generation='v2')


def test_merge_is_monotonic_and_preserves_parent_lineage():
    a=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[rec(occurrence=0)])
    b=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[rec(occurrence=1)])
    merged=a.merge(b,generation='v2')
    assert {a.ledger_id,b.ledger_id}.issubset(set(merged.parent_ledger_ids))
    assert {r.record_id for r in a.records}.issubset({r.record_id for r in merged.records})
    assert {r.record_id for r in b.records}.issubset({r.record_id for r in merged.records})


def test_merge_requires_a_new_generation_distinct_from_both_parents():
    left=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='left-v1',records=[rec(occurrence=0)])
    right=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='right-v1',records=[rec(occurrence=1)])
    with pytest.raises(AssuranceLedgerError):
        left.merge(right,generation='left-v1')
    with pytest.raises(AssuranceLedgerError):
        left.merge(right,generation='right-v1')


def test_exact_duplicate_authority_record_unions_presentation_aliases_without_changing_record_id():
    a=rec(aliases=('finding-a',))
    b=LedgerRecord.create(**{**a.constructor_fields(), 'presentation_ids':('finding-b',)})
    assert a.record_id==b.record_id
    ledger=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[a,b])
    assert len(ledger.records)==1
    assert ledger.records[0].presentation_ids==('finding-a','finding-b')


def test_round_trip_is_strict_and_forged_record_id_fails():
    original=rec(payload={'message':'demo','nested':{'x':[1,True,None]}})
    decoded=LedgerRecord.from_payload(original.to_payload())
    assert decoded==original
    forged=copy.deepcopy(original.to_payload()); forged['record_id']=H('9')
    with pytest.raises(AssuranceLedgerError): LedgerRecord.from_payload(forged)


def test_payload_is_immutable_by_canonical_snapshot():
    payload={'members':['a']}
    r=rec(payload=payload)
    payload['members'].append('b')
    assert r.payload()=={'members':['a']}


def test_rejects_bool_occurrence_mutable_generation_and_non_sha_refs():
    fields=rec().constructor_fields()
    with pytest.raises(AssuranceLedgerError): LedgerRecord.create(**{**fields,'occurrence':True})
    with pytest.raises(AssuranceLedgerError): LedgerRecord.create(**{**fields,'generation':'latest'})
    with pytest.raises(AssuranceLedgerError): LedgerRecord.create(**{**fields,'authority_refs':('not-a-sha',)})


def test_all_founding_record_families_are_supported():
    expected={
        'review_world','acr_evaluation','collection_closure','contract_instance','claim','obligation','assumption',
        'evidence','falsifier_instance','contradiction','qualification_evidence','admission','invalidation','verdict_lineage'
    }
    assert {kind.value for kind in LedgerRecordKind}==expected


def test_ledger_round_trip_rejects_record_from_wrong_world():
    ledger=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[rec()])
    assert JudgeAssuranceLedger.from_payload(ledger.to_payload())==ledger
    payload=copy.deepcopy(ledger.to_payload())
    payload['records'][0]['review_world_id']=H('f')
    # Even if attacker recomputed child record_id, the ledger must reject the cross-world member.
    child=LedgerRecord.from_payload({**payload['records'][0], 'record_id': LedgerRecord.create(**{**rec().constructor_fields(),'review_world_id':H('f')}).record_id})
    payload['records'][0]=child.to_payload()
    with pytest.raises(AssuranceLedgerError): JudgeAssuranceLedger.from_payload(payload)


def test_ledger_rejects_dangling_authority_record_links():
    target=rec(occurrence=0)
    dangling=rec(kind=LedgerRecordKind.ADMISSION, occurrence=1, related=(H('9'),), aliases=())
    with pytest.raises(AssuranceLedgerError):
        JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[target,dangling])


def test_persisted_record_order_and_alias_order_are_canonical():
    a=rec(occurrence=0,aliases=('z','a'))
    b=rec(occurrence=1,aliases=('b',))
    ledger=JudgeAssuranceLedger.create(review_world_id=WORLD,rab_id=RAB,generation='v1',records=[b,a])
    payload=ledger.to_payload()
    assert [r['record_id'] for r in payload['records']]==sorted(r['record_id'] for r in payload['records'])
    assert next(r for r in payload['records'] if r['record_id']==a.record_id)['presentation_ids']==['a','z']
    tampered=copy.deepcopy(payload); tampered['records'].reverse()
    with pytest.raises(AssuranceLedgerError): JudgeAssuranceLedger.from_payload(tampered)


def test_payload_json_is_type_sensitive_and_rejects_nonfinite_numbers():
    boolean=rec(payload={'value':True})
    integer=rec(payload={'value':1})
    assert boolean.record_id != integer.record_id
    with pytest.raises(AssuranceLedgerError): rec(payload={'value':float('nan')})
