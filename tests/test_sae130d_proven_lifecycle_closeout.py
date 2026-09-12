from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="dcfd68bc10cbe7e04ca6def9a5f811942278d014"
CANDIDATE_TREE="d3ae52a29d922967529d3bee83a9074ff38eed29"
MERGE="15291dd7c59c4d6130325c6d629644165b0eb5fb"
MERGE_TREE="d3ae52a29d922967529d3bee83a9074ff38eed29"
REVIEWER="4b3a59117c6ccfac5d6d6d47f795cb4333566b69"
DOC=ROOT/'docs/150-sae130d-proven-lifecycle-closeout.md'
MANIFEST=ROOT/'docs/151-sae130d-proven-lifecycle-closeout-manifest.json'
BLOBS={
 "docs/148-sae130d-semantic-mutation-candidate.md":"c2e5d3b90b6a21d006243a080c43a2acbd57c6d8",
 "docs/149-sae130d-semantic-mutation-candidate-manifest.json":"10edcac35e2d8084fd347492f82aa2cc2e8cbbef",
 "main_review/semantic_mutation.py":"6e760bcef4c4a3dd3f03c56b786d0eb368203cec",
 "tests/test_sae130d_qualification_campaign.py":"5e4ccb52ea731102caef91fad6d512c61511d971",
 "tests/test_semantic_mutation.py":"d322f2897f9acb1aaa97b79962a5b411b7ba51e6",
}
def ensure_ref(ref):
 try: subprocess.check_call(['git','cat-file','-e',f'{ref}^{{commit}}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(['git','fetch','--no-tags','--depth','1','origin',ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def blob(ref,path):
 ensure_ref(ref); return subprocess.check_output(['git','rev-parse',f'{ref}:{path}'],cwd=ROOT,text=True).strip()
def test_required_inventory_exists():
 assert DOC.is_file() and MANIFEST.is_file() and (ROOT/'tests/test_sae130d_qualification_campaign.py').is_file()
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
 assert p['full_suite']=='1775 passed, 2 xfailed'
 assert p['independent_reviewer_generation']==REVIEWER
 assert p['verdict']=='APPROVE'
 assert p['confidence']==0.88
 assert p['required_actions']==[]
 assert p['heavy_evidence_sha256']=='fe7fb486bd11d089bbe6b5549db13b30f921fbee407ef32ffb909c776efa62ea'
 assert p['review_evidence_sha256']=='74264a9c0b314181188ebcae823b1a441dd0b806e3e6a1c7f10d6f5e52730a6d'
def test_authority_gain_requires_closeout_guarded_merge():
 m=json.loads(MANIFEST.read_text())
 assert m['lifecycle_state']=='PROVEN'
 assert m['produces']==['QUALIFIED_SEMANTIC_MUTATION_CAPABILITY']
 assert m['closeout_guarded_merge_required_before_authority'] is True
 assert m['genesis_activated'] is False
