from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="39aaf3769a6d3582ba0d316152e1dfe271313c68"; CANDIDATE_TREE="ab775c5b7df181da6490a76d8bad43e72a7b09f9"; MERGE="cedf045782780cae8e6de24ea964f175d7acb305"; MERGE_TREE="01d00b84775892234a1342cb68b40a464c373da6"; REVIEWER="97c2d939df51a21828a6ea96f05458207ac0793c"
DOC=ROOT/'docs/142-sae130b-proven-lifecycle-closeout.md'; MANIFEST=ROOT/'docs/143-sae130b-proven-lifecycle-closeout-manifest.json'
BLOBS={"docs/140-sae130b-semantic-coupling-candidate.md":"4ec111ba35d359f040d243bbca779d047068ede1","docs/141-sae130b-semantic-coupling-candidate-manifest.json":"51b5abf7da0e3912f586e478012d4f4d910ca365","main_review/semantic_coupling.py":"f8597bf7d31dd6a14e087eac261a7da3210d1407","tests/test_semantic_coupling.py":"7179873af5a4cfd03ea50c6c9c2f96a774cffaee"}
def ensure_ref(ref):
 try: subprocess.check_call(['git','cat-file','-e',f'{ref}^{{commit}}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(['git','fetch','--no-tags','--depth','1','origin',ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def blob(ref,path):
 ensure_ref(ref); return subprocess.check_output(['git','rev-parse',f'{ref}:{path}'],cwd=ROOT,text=True).strip()
def test_required_inventory_exists(): assert DOC.is_file() and MANIFEST.is_file() and (ROOT/'tests/test_sae130b_qualification_campaign.py').is_file()
def test_exact_candidate_and_parallel_merge_binding():
 m=json.loads(MANIFEST.read_text()); assert m['candidate_generation']['head']==CANDIDATE; assert m['candidate_generation']['tree']==CANDIDATE_TREE; assert m['canonical_candidate_merge']['commit']==MERGE; assert m['canonical_candidate_merge']['tree']==MERGE_TREE; assert m['canonical_candidate_merge']['parents']==[REVIEWER,CANDIDATE]
 for p,h in BLOBS.items(): assert m['candidate_generation']['authority_blobs'][p]==h and blob(CANDIDATE,p)==h and blob(MERGE,p)==h
def test_proof_review_binding():
 p=json.loads(MANIFEST.read_text())['candidate_proof_identity']; assert p['full_suite']=='1712 passed, 2 xfailed'; assert p['independent_reviewer_generation']==REVIEWER; assert p['verdict']=='APPROVE'; assert p['confidence']==0.88; assert p['required_actions']==[]; assert p['heavy_evidence_sha256']=='a179131e9871cac41887e8bf6c1f9c5d7eab81b2840f6b07d72b9e620d883882'; assert p['review_evidence_sha256']=='1bb3e8afa904d7186e00cab31ea3f9d94a86a8668687b24d78da23ee2ee5bd64'
def test_authority_gain_requires_closeout_guarded_merge():
 m=json.loads(MANIFEST.read_text()); assert m['lifecycle_state']=='PROVEN'; assert m['produces']==['QUALIFIED_SEMANTIC_COUPLING_CAPABILITY']; assert m['closeout_guarded_merge_required_before_authority'] is True; assert m['genesis_activated'] is False
