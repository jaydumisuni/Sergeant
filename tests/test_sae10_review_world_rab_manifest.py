import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/79-sae10-review-world-rab-manifest.json'
DOC=ROOT/'docs/78-sae10-review-world-rab-contract.md'
def blob(path):return subprocess.run(['git','hash-object',str(ROOT/path)],text=True,capture_output=True,check=True).stdout.strip()
def test_candidate_manifest_lifecycle_and_dependency():
 m=json.loads(MANIFEST.read_text());assert m['lifecycle_state']=='CANDIDATE';assert m['proof_dependency']==['SAE-00'];assert m['normal_verdict_authority'] is False
def test_candidate_manifest_outputs_are_exact():
 m=json.loads(MANIFEST.read_text());assert m['produces']==['QUALIFIED_REVIEW_WORLD_CONTRACT','QUALIFIED_RAB_CONTRACT']
def test_candidate_content_blob_bindings_match_workspace():
 m=json.loads(MANIFEST.read_text());assert all(blob(Path(p))==sha for p,sha in m['content_blobs'].items())
def test_tenfold_formation_and_local_proof_are_bound():
 m=json.loads(MANIFEST.read_text());assert m['tenfold_proof']=={'actions_required':False,'formation_lanes':20,'local_test_result':{'failed':0,'passed':66,'xfailed':1}}
def test_required_hostile_attacks_are_bound():
 m=json.loads(MANIFEST.read_text());assert set(m['required_hostile_attacks'])=={'same_head_different_base','wrong_merge_tree','local_mutation_after_snapshot','scope_downgrade','unauthorized_rab_combination','candidate_self_activation'}
def test_candidate_doc_preserves_nonactivation_boundary():
 text=DOC.read_text();assert 'still **CANDIDATE**' in text;assert 'not fabricated here' in text;assert 'zero effect' in text;assert 'GitHub Actions are supplementary only' in text

def test_github_hostile_review_finding_is_bound_and_repaired_locally():
 m=json.loads(MANIFEST.read_text());r=m['github_hostile_review'];assert r['initial_candidate_head']=='c977449177eb9c9f3d6034265ad97cc32180c069';assert r['valid_finding']=='spike_sem_historical_metric_current_tree_invariant';assert r['repair']=='external_exact_node_strict_xfail_preserve_historical_fixture';assert r['repair_local_reproof']=={'failed':0,'passed':66,'xfailed':1}
