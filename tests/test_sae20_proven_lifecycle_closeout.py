from __future__ import annotations
import json,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/85-sae20-proven-lifecycle-closeout-manifest.json'
CANDIDATE=ROOT/'docs/83-sae20-acr-authoring-audit-candidate-manifest.json'
DOC=ROOT/'docs/84-sae20-proven-lifecycle-closeout.md'
QUAL=ROOT/'tests/test_sae20_acr_qualification_campaign.py'
SAE00=ROOT/'docs/67-sae00-proven-lifecycle-closeout-manifest.json'
ROADMAP=ROOT/'docs/59-sergeant-assurance-evolution-roadmap.md'
ARCH=ROOT/'docs/58-sergeant-assurance-evolution-founding-architecture.md'
HEAD='4c00b54b578aed0f9925cff9345b4482c46ebc3e'; MERGE='3a5522c5a789e4ef5e512af4d491cad95a051307'; SAE00_MERGE='5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910'

def load(path: Path)->dict: return json.loads(path.read_text(encoding='utf-8'))
def git(*args:str)->str: return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()
def blob(path:Path)->str: return git('rev-parse',f"HEAD:{path.relative_to(ROOT).as_posix()}")
def available(commit:str)->bool: return subprocess.run(['git','cat-file','-e',f'{commit}^{{commit}}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0

def test_lifecycle_advances_without_rewriting_candidate() -> None:
    c,m=load(CANDIDATE),load(MANIFEST)
    assert c['node']=='SAE-20' and c['lifecycle_state']=='CANDIDATE'
    assert m['node']=='SAE-20' and m['lifecycle_state']=='PROVEN' and m['normal_verdict_authority'] is False
    assert m['candidate_generation']['historical_candidate_preserved_not_rewritten'] is True

def test_exact_candidate_artifacts_are_bound() -> None:
    c=load(MANIFEST)['candidate_generation']; assert c['pull_request']==178 and c['head']==HEAD
    for key in ('candidate_document','candidate_manifest','candidate_manifest_proof','hostile_regression_proof'):
        e=c[key]; assert blob(ROOT/e['path'])==e['blob_sha']
    for path,expected in c['authority_implementation_blobs'].items(): assert blob(ROOT/path)==expected

def test_execution_proof_is_exact_head_bound() -> None:
    e=load(MANIFEST)['candidate_execution_confirmation']; expected={'passed':1338,'xfailed':2,'failed':0,'historical_xfails_only':True}
    assert e['exact_head']==HEAD and e['ci_run_id']==33998093987 and e['full_suite']==expected and e['clean_clone_suite']==expected
    assert e['clean_clone_proof']=='success' and e['main_review_run_id']==33998093976 and e['main_review']=='APPROVE'
    assert e['main_review_repository_verdict']==e['main_review_diff_verdict']==e['main_review_capability_verdict']=='PASS'
    assert e['main_review_changed_scope_defects']==0 and e['main_review_unresolved_explicit_assurances']==0

def test_external_holdout_evidence_is_preserved_not_relabelled() -> None:
    r=load(MANIFEST)['hostile_review_confirmation']; assert r['reviewed_head']==HEAD and r['owner_root_exact_head_review_id']==5124770297
    assert r['owner_root_review_kind']=='COMMENT' and r['owner_root_actionable_findings']==0 and r['owner_root_review_is_self_approval'] is False
    assert r['codex_external_holdout_finding_ids']==[3942298804,3942298806,3942298807,3942298808,3942298810,3942298811]
    assert r['coderabbit_external_holdout_finding_id']==3942313482
    assert r['coderabbit_current_head_cardinality_confirmation_id']==3942357968 and r['coderabbit_current_head_iterable_confirmation_id']==3942358802
    assert r['full_exact_head_codex_review_submission'] is None and r['full_exact_head_coderabbit_review_submission'] is None
    assert r['full_exact_head_external_review_absence_treated_as_pass'] is False and r['all_inline_review_threads_resolved'] is True

def test_acr_qualification_campaign_is_bounded_and_content_bound() -> None:
    q=load(MANIFEST)['acr_qualification_campaign']; assert blob(QUAL)==q['fixture_blob_sha'] and q['bounded_domain']=='typescript.express-route.v1'
    for key in ('clean_control','unrelated_language_transfer','deletion_mutations','undercount_mutations','collection_semantics_cardinality_order_attacks','unknown_and_negative_applicability_attacks','external_holdout_defects_replayed_as_regressions'): assert q[key] is True
    assert q['universal_completeness_claimed'] is False

def test_exact_candidate_head_is_parent_of_canonical_merge() -> None:
    m=load(MANIFEST); assert m['canonical_candidate_merge']=={'commit':MERGE,'exact_head_guard':HEAD,'merge_method':'merge_commit'}
    assert re.fullmatch(r'[0-9a-f]{40}',MERGE) and MERGE in DOC.read_text() and HEAD in DOC.read_text()
    if available(MERGE) and available(HEAD):
        assert HEAD in git('show','-s','--format=%P',MERGE).split(); subprocess.check_call(['git','merge-base','--is-ancestor',MERGE,'HEAD'],cwd=ROOT)
    else: assert git('rev-parse','--is-shallow-repository')=='true'

def test_proven_sae00_authority_and_bounded_bootstrap() -> None:
    m,s=load(MANIFEST),load(SAE00); a=m['sae00_proven_authority']; b=m['bootstrap_authority']
    assert s['node']=='SAE-00' and s['lifecycle_state']=='PROVEN' and a['merge_commit']==SAE00_MERGE and a['required_output'] in s['produces']
    assert b['kind']=='SAE00_ROADMAP_EXECUTION_PLUS_OWNER_ROOT_CONSTITUTIONAL_TCB' and b['not_general_qualification_authority'] and b['cannot_qualify_dependents'] and b['cannot_satisfy_genesis_external_lane'] and b['cannot_convert_business_risk_to_pass'] and b['partial_generation_activation_allowed'] is False
    assert m['produces']==['QUALIFIED_ACR_FOUNDATION'] and m['authority_boundary']['universal_acr_completeness_claimed'] is False

def test_dependency_effect_matches_frozen_authority() -> None:
    m=load(MANIFEST); e=m['dependency_effect']; road=ROADMAP.read_text(); arch=ARCH.read_text()
    assert 'Produces `QUALIFIED_ACR_FOUNDATION`.' in road and '**Proof requires:** `SAE-10`, `SAE-20`.' in road
    assert 'The ACR candidate cannot establish the completeness of its own qualification corpus.' in arch
    assert e['sae20_proof_dependency_resolved'] and e['qualified_acr_foundation_available'] and e['sae40_frozen_upstream_dependencies_available']
    assert e['sae40_auto_qualified'] is False and e['sae40_auto_proven'] is False and e['dependent_nodes_auto_qualified'] is False and e['dependent_nodes_auto_proven'] is False

def test_closeout_artifacts_are_content_bound_and_documented() -> None:
    m=load(MANIFEST); text=DOC.read_text()
    for key in ('closeout_document','proof_fixture'):
        e=m[key]; assert blob(ROOT/e['path'])==e['blob_sha']
    assert 'Status: **PROVEN**' in text and HEAD in text and MERGE in text and 'QUALIFIED_ACR_FOUNDATION' in text
    assert 'no claim of a new full Codex or CodeRabbit review submission' in text and 'does not claim universal program semantics' in text
