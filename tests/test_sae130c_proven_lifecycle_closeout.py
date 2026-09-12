from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="08153330b85b01eb2b266fa14bbce459a6164258"
CANDIDATE_TREE="43719493b12ed056ff2e1e14fd0979fe07faf1ad"
MERGE="1f5a719f78e5ff9e81f9a8668fa6c95e437a79eb"
MERGE_TREE="43719493b12ed056ff2e1e14fd0979fe07faf1ad"
REVIEWER="7af19145d13e173a9fe727cd3977c483aa4c8057"
DOC=ROOT/'docs/146-sae130c-proven-lifecycle-closeout.md'
MANIFEST=ROOT/'docs/147-sae130c-proven-lifecycle-closeout-manifest.json'
BLOBS={
 "docs/144-sae130c-state-failure-candidate.md":"de765e00430f4526511e9d69ef0eaf3e10ac2279",
 "docs/145-sae130c-state-failure-candidate-manifest.json":"f91cd527f87c5dcbe2ffee3c94f7375ead5620ef",
 "main_review/state_failure_reasoning.py":"6f1c5ea243245945f27ce9aa14ccbe91006b74d4",
 "tests/test_sae130c_qualification_campaign.py":"d907f76a1f4b78d7db938547b9af7685a36a8b37",
 "tests/test_state_failure_reasoning.py":"acee9c704f1b97d6f61a0d8ae90703f6d35e8e55",
}
def ensure_ref(ref):
 try: subprocess.check_call(['git','cat-file','-e',f'{ref}^{{commit}}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(['git','fetch','--no-tags','--depth','1','origin',ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def blob(ref,path):
 ensure_ref(ref); return subprocess.check_output(['git','rev-parse',f'{ref}:{path}'],cwd=ROOT,text=True).strip()
def test_required_inventory_exists():
 assert DOC.is_file() and MANIFEST.is_file() and (ROOT/'tests/test_sae130c_qualification_campaign.py').is_file()
def test_exact_candidate_and_guarded_merge_binding():
 m=json.loads(MANIFEST.read_text())
 assert m['candidate_generation']['head']==CANDIDATE
 assert m['candidate_generation']['tree']==CANDIDATE_TREE
 assert m['canonical_candidate_merge']['commit']==MERGE
 assert m['canonical_candidate_merge']['tree']==MERGE_TREE
 assert m['canonical_candidate_merge']['parents']==[REVIEWER,CANDIDATE]
 for path,expected in BLOBS.items():
  assert m['candidate_generation']['authority_blobs'][path]==expected
  assert blob(CANDIDATE,path)==expected
  assert blob(MERGE,path)==expected
def test_proof_review_binding():
 p=json.loads(MANIFEST.read_text())['candidate_proof_identity']
 assert p['full_suite']=='1745 passed, 2 xfailed'
 assert p['independent_reviewer_generation']==REVIEWER
 assert p['verdict']=='APPROVE'
 assert p['confidence']==0.88
 assert p['required_actions']==[]
 assert p['heavy_evidence_sha256']=='692da373cf4148c56d0cb464135c46799f3866de628806b843e6bc48ccaf9c45'
 assert p['review_evidence_sha256']=='fb5cd1dceb37af7b24a74e192951b135297210a87ee2a7701238bdaed7cde4b5'
def test_authority_gain_requires_closeout_guarded_merge():
 m=json.loads(MANIFEST.read_text())
 assert m['lifecycle_state']=='PROVEN'
 assert m['produces']==['QUALIFIED_STATE_FAILURE_CAPABILITY']
 assert m['closeout_guarded_merge_required_before_authority'] is True
 assert m['genesis_activated'] is False
