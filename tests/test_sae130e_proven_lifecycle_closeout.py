from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="5a3f32f0121efc37be408bcc1abd1ca6b6097e4b"
CANDIDATE_TREE="baca841f52f6194b67c41b73e2d4a96d1bcc9108"
MERGE="1c62082b533d329936b84ca2df8c095bd75d894e"
MERGE_TREE="baca841f52f6194b67c41b73e2d4a96d1bcc9108"
REVIEWER="948c450e15f71f3823be0df1fedf27650edec067"
DOC=ROOT/"docs/154-sae130e-proven-lifecycle-closeout.md"
MANIFEST=ROOT/"docs/155-sae130e-proven-lifecycle-closeout-manifest.json"
BLOBS={
 "docs/152-sae130e-relational-assurance-candidate.md":"1eb02c466ae3fec15c73e22b49f2ecde0483ff85",
 "docs/153-sae130e-relational-assurance-candidate-manifest.json":"8a1c6829de906ccb22bd58f0a5abf26d7f08ee5d",
 "main_review/relational_assurance.py":"0d84f6204cab87f6b48cfa6a43274381dd1cdd10",
 "tests/test_relational_assurance.py":"f5956460e1e20a67838b5ccffc6622b862db3a30",
 "tests/test_sae130e_qualification_campaign.py":"d9457f2aff543edc8e7d30a616f989d6d2089a91",
}
def ensure_ref(ref):
 try: subprocess.check_call(["git","cat-file","-e",f"{ref}^{{commit}}"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(["git","fetch","--no-tags","--depth","1","origin",ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def blob(ref,path):
 ensure_ref(ref); return subprocess.check_output(["git","rev-parse",f"{ref}:{path}"],cwd=ROOT,text=True).strip()
def test_required_inventory_exists():
 assert DOC.is_file() and MANIFEST.is_file() and (ROOT/"tests/test_sae130e_qualification_campaign.py").is_file()
def test_exact_candidate_and_guarded_merge_binding():
 m=json.loads(MANIFEST.read_text())
 assert m["candidate_generation"]["head"]==CANDIDATE
 assert m["candidate_generation"]["tree"]==CANDIDATE_TREE
 assert m["canonical_candidate_merge"]["commit"]==MERGE
 assert m["canonical_candidate_merge"]["tree"]==MERGE_TREE
 assert m["canonical_candidate_merge"]["parents"]==[REVIEWER,CANDIDATE]
 for path,expected in BLOBS.items():
  assert m["candidate_generation"]["authority_blobs"][path]==expected
  assert blob(CANDIDATE,path)==expected
  assert blob(MERGE,path)==expected
def test_proof_review_binding():
 p=json.loads(MANIFEST.read_text())["candidate_proof_identity"]
 assert p["full_suite"]=="1795 passed, 2 xfailed"
 assert p["independent_reviewer_generation"]==REVIEWER
 assert p["verdict"]=="APPROVE"
 assert p["confidence"]==0.88
 assert p["required_actions"]==[]
 assert p["heavy_evidence_sha256"]=="97673886e15e0a09cd044d48f5444658461c1e1972a796cce97ec95a464aeb9a"
 assert p["review_evidence_sha256"]=="d42dc9ad5ef33d3b820469849db7e5fe2c7ea6aaba9ac0981bad5dcb4dc78429"
def test_authority_gain_requires_closeout_guarded_merge():
 m=json.loads(MANIFEST.read_text())
 assert m["lifecycle_state"]=="PROVEN"
 assert m["produces"]==["QUALIFIED_RELATIONAL_ASSURANCE_CAPABILITY"]
 assert m["closeout_guarded_merge_required_before_authority"] is True
 assert m["genesis_activated"] is False
