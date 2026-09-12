from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE="391d176c514aa15a3f217e803486b43007285929"
CANDIDATE_TREE="0d40113dfbf3c9bb25f84b94004920e63576fa4f"
CANDIDATE_MERGE="5a701f76477e46210ff4a7251d4e2b156778d396"
BASE_PROVEN="e29ffbcd6aad7336e5827cbb1e6469be398cf730"
DOC=ROOT/"docs/138-sae130a-proven-lifecycle-closeout.md"
MANIFEST=ROOT/"docs/139-sae130a-proven-lifecycle-closeout-manifest.json"
EXPECTED_BLOBS={
"docs/136-sae130a-authority-effect-candidate.md":"5b9bbc07339f2fb233713d16985aa31404448b5e",
"docs/137-sae130a-authority-effect-candidate-manifest.json":"d609dcdcf6ddb01bcc826ec2fa40216af68ffaf5",
"main_review/authority_effect_reasoning.py":"1cad4d801ac1ad376fcdfb49439dfdcf304f6c2d",
"tests/test_authority_effect_reasoning.py":"3f8fbad343a2608a844f187533b22ee52cc0408b",
}

def ensure_ref(ref):
    try: subprocess.check_call(["git","cat-file","-e",f"{ref}^{{commit}}"],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError: subprocess.check_call(["git","fetch","--no-tags","--depth","1","origin",ref],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def tree_at(ref):
    ensure_ref(ref); return subprocess.check_output(["git","rev-parse",f"{ref}^{{tree}}"],cwd=ROOT,text=True).strip()

def blob_at(ref,path):
    ensure_ref(ref); payload=subprocess.check_output(["git","show",f"{ref}:{path}"],cwd=ROOT); return subprocess.check_output(["git","hash-object","--stdin"],cwd=ROOT,input=payload).decode().strip()

def test_required_inventory_exists():
    assert DOC.is_file(); assert MANIFEST.is_file(); assert (ROOT/"tests/test_sae130a_qualification_campaign.py").is_file()

def test_closeout_binds_candidate_merge_tree_and_blobs():
    m=json.loads(MANIFEST.read_text()); assert m["candidate_generation"]["head"]==CANDIDATE; assert m["candidate_generation"]["tree"]==CANDIDATE_TREE; assert m["canonical_candidate_merge"]["commit"]==CANDIDATE_MERGE; assert tree_at(CANDIDATE)==CANDIDATE_TREE; assert tree_at(CANDIDATE_MERGE)==CANDIDATE_TREE
    for p,h in EXPECTED_BLOBS.items(): assert m["candidate_generation"]["authority_blobs"][p]==h and blob_at(CANDIDATE,p)==h

def test_closeout_binds_exact_proof_review_identity():
    p=json.loads(MANIFEST.read_text())["candidate_proof_identity"]; assert p["full_suite"]=="1712 passed, 2 xfailed"; assert p["independent_reviewer_generation"]==BASE_PROVEN; assert p["verdict"]=="APPROVE"; assert p["confidence"]==0.88; assert p["required_actions"]==[]; assert p["heavy_evidence_sha256"]=="13e837919445f627559145116e8998bbf2547f153a38970437c9f4c5cbc9be00"; assert p["review_evidence_sha256"]=="3c1c703d063029f5e4bbb03dad3bf3784ae7320bf48277156104c3c18795ee41"

def test_authority_gain_requires_guarded_closeout_merge():
    m=json.loads(MANIFEST.read_text()); assert m["lifecycle_state"]=="PROVEN"; assert m["produces"]==["QUALIFIED_AUTHORITY_EFFECT_CAPABILITY"]; assert m["normal_verdict_authority"] is False; assert m["genesis_activated"] is False; assert m["closeout_guarded_merge_required_before_authority"] is True
