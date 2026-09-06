from __future__ import annotations
import pytest
from main_review.assurance_ledger import AssuranceLedgerError, LedgerEpistemicState, LedgerRecordKind
from main_review.judge_assurance_adapter import build_judge_assurance_ledger

H=lambda ch: ch*64
WORLD=H("a"); RAB=H("b"); SCOPE=H("c")

def test_adapter_lifts_existing_judge_packet_without_collapsing_duplicate_sources():
    council={
        'raw_findings':[
            {'finding_id':'finding-same','source':'repository','message':'unsafe','severity':'major','path':'a.py','line_start':3},
            {'finding_id':'finding-same','source':'offline-officer','message':'unsafe','severity':'major','path':'a.py','line_start':3},
        ],
        'required_assurances':[{'assurance_id':'assure-1','status':'unresolved','gates_verdict':True,'required_assurance':'coverage'}],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':['finding-same'],'advisory':[],'rejected':[]}}],
        'verdict':'NEEDS WORK',
    }
    ledger=build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='sae40-council-v1',council=council)
    claims=[r for r in ledger.records if r.kind is LedgerRecordKind.CLAIM]
    admissions=[r for r in ledger.records if r.kind is LedgerRecordKind.ADMISSION]
    obligations=[r for r in ledger.records if r.kind is LedgerRecordKind.OBLIGATION]
    lineage=[r for r in ledger.records if r.kind is LedgerRecordKind.VERDICT_LINEAGE]
    assert len(claims)==2
    assert len({r.record_id for r in claims})==2
    assert all(r.presentation_ids==('finding-same',) for r in claims)
    assert len(admissions)==1 and admissions[0].payload()['disposition']=='admitted'
    assert set(admissions[0].related_record_ids)=={r.record_id for r in claims}
    assert len(obligations)==1 and obligations[0].epistemic_state is LedgerEpistemicState.UNKNOWN
    assert len(lineage)==1 and lineage[0].payload()['verdict']=='NEEDS WORK'


def test_adapter_keeps_legacy_finding_id_out_of_claim_authority_identity():
    def build(finding_id: str):
        council={
            'raw_findings':[{'finding_id':finding_id,'source':'repository','message':'unsafe','severity':'major','path':'a.py','line_start':3}],
            'required_assurances':[],
            'reports':[{'officer':'Judge','admission_ledger':{'admitted':[finding_id],'advisory':[],'rejected':[]}}],
            'verdict':'NEEDS WORK',
        }
        return build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)

    first=build('finding-a')
    second=build('finding-renamed')
    first_claim=next(r for r in first.records if r.kind is LedgerRecordKind.CLAIM)
    second_claim=next(r for r in second.records if r.kind is LedgerRecordKind.CLAIM)
    assert first_claim.record_id == second_claim.record_id
    assert 'finding_id' not in first_claim.payload()
    assert first_claim.presentation_ids == ('finding-a',)
    assert second_claim.presentation_ids == ('finding-renamed',)
    assert first.ledger_id != second.ledger_id


def test_adapter_fails_closed_without_real_judge_report_or_exact_ids():
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council={'raw_findings':[],'reports':[]})
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id='bad',rab_id=RAB,scope_id=SCOPE,generation='v1',council={'raw_findings':[],'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}]})


def test_adapter_rejects_judge_disposition_without_a_raw_claim():
    council={
        'raw_findings':[],
        'required_assurances':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':['finding-orphan'],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)


def test_adapter_rejects_raw_claim_without_existing_canonical_disposition():
    missing_disposition={
        'raw_findings':[{'finding_id':'finding-a','source':'repository','message':'unsafe','severity':'major','path':'a.py','line_start':3}],
        'required_assurances':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=missing_disposition)

    missing_id={
        'raw_findings':[{'source':'repository','message':'unsafe','severity':'major','path':'a.py','line_start':3}],
        'required_assurances':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=missing_id)


def test_adapter_rejects_missing_required_assurances_collection():
    council={
        'raw_findings':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)


def test_adapter_rejects_malformed_required_assurance_contract_fields():
    base={
        'raw_findings':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    missing_requirement={**base,'required_assurances':[{'assurance_id':'assure-1','status':'satisfied','gates_verdict':False}]}
    missing_gate={**base,'required_assurances':[{'assurance_id':'assure-1','status':'unresolved','required_assurance':'coverage'}]}
    nonboolean_gate={**base,'required_assurances':[{'assurance_id':'assure-1','status':'unresolved','required_assurance':'coverage','gates_verdict':0}]}
    for council in (missing_requirement,missing_gate,nonboolean_gate):
        with pytest.raises(AssuranceLedgerError):
            build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)


def test_adapter_rejects_noncanonical_assurance_status():
    council={
        'raw_findings':[],
        'required_assurances':[{'assurance_id':'assure-1','status':'dismissed','gates_verdict':False,'required_assurance':'coverage'}],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)


def test_adapter_rejects_duplicate_or_unknown_judge_disposition_buckets():
    raw=[{'finding_id':'finding-a','source':'repository','message':'unsafe','severity':'major','path':'a.py','line_start':3}]
    duplicate={
        'raw_findings':raw,
        'required_assurances':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':['finding-a','finding-a'],'advisory':[],'rejected':[]}}],
        'verdict':'NEEDS WORK',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=duplicate)

    unknown_bucket={
        'raw_findings':raw,
        'required_assurances':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':['finding-a'],'advisory':[],'rejected':[],'waived':[]}}],
        'verdict':'NEEDS WORK',
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=unknown_bucket)


def test_adapter_admission_identity_does_not_depend_on_legacy_alias_sort_order():
    def build(first_id: str, second_id: str):
        council={
            'raw_findings':[
                {'finding_id':first_id,'source':'repository','message':'first','severity':'major','path':'a.py','line_start':1},
                {'finding_id':second_id,'source':'repository','message':'second','severity':'major','path':'b.py','line_start':2},
            ],
            'required_assurances':[],
            'reports':[{'officer':'Judge','admission_ledger':{'admitted':[first_id,second_id],'advisory':[],'rejected':[]}}],
            'verdict':'NEEDS WORK',
        }
        return build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)

    first=build('finding-a','finding-z')
    renamed=build('finding-z','finding-a')
    def admission_by_claim(ledger):
        admissions=[r for r in ledger.records if r.kind is LedgerRecordKind.ADMISSION]
        return {r.related_record_ids[0]:r.record_id for r in admissions}
    assert admission_by_claim(first) == admission_by_claim(renamed)


def test_adapter_keeps_existing_judge_metadata_out_of_raw_claim_authority():
    def build(admission: str, gates: bool):
        council={
            'raw_findings':[{
                'finding_id':'finding-a','source':'repository','message':'unsafe','severity':'major',
                'path':'a.py','line_start':3,'admission':admission,'gates_verdict':gates,
            }],
            'required_assurances':[],
            'reports':[{'officer':'Judge','admission_ledger':{'admitted':['finding-a'],'advisory':[],'rejected':[]}}],
            'verdict':'NEEDS WORK',
        }
        return build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)

    first=build('actionable',True)
    second=build('duplicate',False)
    first_claim=next(r for r in first.records if r.kind is LedgerRecordKind.CLAIM)
    second_claim=next(r for r in second.records if r.kind is LedgerRecordKind.CLAIM)
    assert first_claim.record_id == second_claim.record_id
    assert 'admission' not in first_claim.payload()
    assert 'gates_verdict' not in first_claim.payload()


def test_adapter_rejects_assurance_status_gate_mismatch():
    base={
        'raw_findings':[],
        'reports':[{'officer':'Judge','admission_ledger':{'admitted':[],'advisory':[],'rejected':[]}}],
        'verdict':'PASS',
    }
    mismatches=(
        {'assurance_id':'a','status':'satisfied','gates_verdict':True,'required_assurance':'coverage'},
        {'assurance_id':'b','status':'unresolved','gates_verdict':False,'required_assurance':'coverage'},
        {'assurance_id':'c','status':'advisory','gates_verdict':True,'required_assurance':'none'},
    )
    for assurance in mismatches:
        council={**base,'required_assurances':[assurance]}
        with pytest.raises(AssuranceLedgerError):
            build_judge_assurance_ledger(review_world_id=WORLD,rab_id=RAB,scope_id=SCOPE,generation='v1',council=council)
