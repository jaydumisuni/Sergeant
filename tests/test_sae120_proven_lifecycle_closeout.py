from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "0266492fff989698e5089c2b39ecf21d3bcd05ff"
CANDIDATE_TREE = "df34d5afc58cb42910ca7fb92bdaf5b65eb3e04c"
CANDIDATE_MERGE = "119cab7d1f335c33f134a52ef709d7eeb1617f57"
BASE_PROVEN = "1ba0fbbafc9423ed9b098137e0669fe941b052d0"
DOC = ROOT / "docs/134-sae120-proven-lifecycle-closeout.md"
MANIFEST = ROOT / "docs/135-sae120-proven-lifecycle-closeout-manifest.json"
EXPECTED_BLOBS = {
    "docs/132-sae120-facility-gradient-candidate.md": "d2fea3d819e07f4ac0ad492468a05b08ca752eed",
    "docs/133-sae120-facility-gradient-candidate-manifest.json": "b1d088749591b764841b0e17ba02f18d78b6109a",
    "main_review/facility_gradient.py": "883aadeea0ed0be5ce3bed567be6e51cb233fe3b",
    "tests/test_facility_gradient.py": "8c7f44be1395dc4d64f807b47ba8913a2a6f2f83",
    "scripts/verify_frozen_transfer_replay.py": "2d80168f00d80f96333b746fce29cb188e00385a",
    "tests/test_frozen_transfer_durable_replay.py": "05c8be6baa62f9b3bd07bf635e63e0646650850c",
}


def ensure_ref(ref: str) -> None:
    try:
        subprocess.check_call(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "fetch", "--no-tags", "--depth", "1", "origin", ref], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def tree_at(ref: str) -> str:
    ensure_ref(ref)
    return subprocess.check_output(["git", "rev-parse", f"{ref}^{{tree}}"], cwd=ROOT, text=True).strip()


def blob_at(ref: str, path: str) -> str:
    ensure_ref(ref)
    payload = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT)
    return subprocess.check_output(["git", "hash-object", "--stdin"], cwd=ROOT, input=payload).decode().strip()


def test_required_sae120_closeout_inventory_exists():
    assert DOC.is_file()
    assert MANIFEST.is_file()
    assert (ROOT / "tests/test_sae120_qualification_campaign.py").is_file()


def test_closeout_binds_exact_candidate_merge_tree_and_frozen_blobs():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["candidate_generation"]["head"] == CANDIDATE
    assert manifest["candidate_generation"]["tree"] == CANDIDATE_TREE
    assert manifest["canonical_candidate_merge"]["commit"] == CANDIDATE_MERGE
    assert manifest["canonical_candidate_merge"]["tree"] == CANDIDATE_TREE
    assert manifest["canonical_candidate_merge"]["parents"] == [BASE_PROVEN, CANDIDATE]
    assert tree_at(CANDIDATE) == CANDIDATE_TREE
    assert tree_at(CANDIDATE_MERGE) == CANDIDATE_TREE
    for path, expected in EXPECTED_BLOBS.items():
        assert manifest["candidate_generation"]["authority_blobs"][path] == expected
        assert blob_at(CANDIDATE, path) == expected


def test_closeout_binds_exact_proof_and_independent_review():
    manifest = json.loads(MANIFEST.read_text())
    proof = manifest["candidate_proof_identity"]
    assert proof["full_suite"] == "1699 passed, 2 xfailed"
    assert proof["independent_reviewer_generation"] == BASE_PROVEN
    assert proof["verdict"] == "APPROVE"
    assert proof["confidence"] == 0.88
    assert proof["required_actions"] == []
    assert proof["heavy_evidence_sha256"] == "f25c63f70ea28d381ba7fe57542fd4e9b78a79d741deccaaf232d2e3ddab4b04"
    assert proof["review_evidence_sha256"] == "d130522a60e5d931a308895a0d5955a54550204e26cdd456809171ee8bc6ab7b"


def test_closeout_only_grants_qualified_facility_gradient_after_guarded_merge():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["lifecycle_state"] == "PROVEN"
    assert manifest["produces"] == ["QUALIFIED_PRODUCT_CAPABILITY_GRADIENT"]
    assert manifest["normal_verdict_authority"] is False
    assert manifest["genesis_activated"] is False
    assert manifest["dependent_nodes_auto_proven"] is False
    assert manifest["partial_generation_activation"] is False
    assert manifest["closeout_guarded_merge_required_before_authority"] is True
