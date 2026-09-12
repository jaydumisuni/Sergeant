from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="26d35a8885ef9d247e3616a39d2d156c65e6f161"
TREE="766cb78aca3c86a5d9725e37477c4a9f19a87324"
MERGE="3a19dffe398b2b2499383782b9c89684acf25d68"
REVIEWER="a889f512662e0b1d62a81582025677276967806d"
DOC=ROOT/"docs/158-sae140-proven-lifecycle-closeout.md"
MANIFEST=ROOT/"docs/159-sae140-proven-lifecycle-closeout-manifest.json"
BLOBS={"docs/156-sae140-assurance-learning-candidate.md":"f8858d8009720f341ec9e7d8caec286eb483d889","docs/157-sae140-assurance-learning-candidate-manifest.json":"b3bbacd1c3de6e93a70710a80a50c65e6c2e0eda","main_review/assurance_learning.py":"415387390be0c15660dc6a60540034b05b036014","tests/test_assurance_learning.py":"9dc96852d97f0782e7614c65262a054d1d21cef1","tests/test_sae140_qualification_campaign.py":"1c068f762401237d7bfcc895320038d0aabdc016"}
def ensure_ref(ref):
 try: subprocess.check_call(["git","cat-file","-e",f"{ref}^{{commit}}"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 except subprocess.CalledProcessError: subprocess.check_call(["git","fetch","--no-tags","--depth","1","origin",ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def blob(ref,path):
 ensure_ref(ref); return subprocess.check_output(["git","rev-parse",f"{ref}:{path}"],cwd=ROOT,text=True).strip()
def test_inventory(): assert DOC.is_file() and MANIFEST.is_file() and (ROOT/"tests/test_sae140_qualification_campaign.py").is_file()
def test_exact_candidate_merge_binding():
 m=json.loads(MANIFEST.read_text()); assert m["candidate_generation"]["head"]==CANDIDATE and m["candidate_generation"]["tree"]==TREE; assert m["canonical_candidate_merge"]["commit"]==MERGE and m["canonical_candidate_merge"]["tree"]==TREE and m["canonical_candidate_merge"]["parents"]==[REVIEWER,CANDIDATE]
 for path,expected in BLOBS.items(): assert m["candidate_generation"]["authority_blobs"][path]==expected and blob(CANDIDATE,path)==expected and blob(MERGE,path)==expected
def test_proof_review_binding():
 p=json.loads(MANIFEST.read_text())["candidate_proof_identity"]; assert p["full_suite"]=="1826 passed, 2 xfailed" and p["independent_reviewer_generation"]==REVIEWER and p["verdict"]=="APPROVE" and p["confidence"]==0.88 and p["required_actions"]==[]; assert p["heavy_evidence_sha256"]=="c1f998d4393cff2e88bf9ee8c2c6318a8683a1c3341d4e3c38914493cb72d516" and p["review_evidence_sha256"]=="d8687731a60a890dd8d4b887afcff9aa5fb363e4a857228762ab2a212da6673c"
def test_authority_requires_closeout_merge():
 m=json.loads(MANIFEST.read_text()); assert m["lifecycle_state"]=="PROVEN" and m["produces"]==["QUALIFIED_ASSURANCE_LEARNING_LOOP"] and m["closeout_guarded_merge_required_before_authority"] is True and m["genesis_activated"] is False
