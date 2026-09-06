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

