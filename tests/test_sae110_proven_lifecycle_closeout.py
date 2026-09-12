from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "2f68974e67c0764712639bdefd6c526537d1795e"
CANDIDATE_TREE = "b2ae7d61a8c19c8f2b0617b582fa83429dc42cfd"
CANDIDATE_MERGE = "1eb29fe4aa61eb3e197bdd0f68cb54c703fc3421"
BASE_PROVEN = "73541e17e8ef7c208d2bfa91012695b6917e549b"
DOC = ROOT / "docs/130-sae110-proven-lifecycle-closeout.md"
MANIFEST = ROOT / "docs/131-sae110-proven-lifecycle-closeout-manifest.json"

EXPECTED_BLOBS = {
    "docs/128-sae110-assurance-capsule-candidate.md": "7b965007489c884a5bfc9067ccfe748b5ac3df52",
    "docs/129-sae110-assurance-capsule-candidate-manifest.json": "f4397469924b1ef129bdd2ec7c10b07980aaa1eb",
    "main_review/assurance_capsule.py": "80d477514d7fe19c36c4c980c139e14c59ef3a5b",
    "tests/test_assurance_capsule.py": "9d6e69e2ab9a0d3754d6e7596373c24a41b2193b",
    "scripts/verify_frozen_transfer_replay.py": "81f07e731976de8048aca330a8d53ad05a015acb",
    "tests/test_frozen_transfer_durable_replay.py": "2377207c6e0c3022f9e99b890baf3380316fd180",
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


def test_required_sae110_closeout_inventory_exists():
    assert DOC.is_file()
    assert MANIFEST.is_file()
    assert (ROOT / "tests/test_sae110_qualification_campaign.py").is_file()


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
    assert proof["full_suite"] == "1685 passed, 2 xfailed"
    assert proof["independent_reviewer_generation"] == BASE_PROVEN
    assert proof["verdict"] == "APPROVE"
    assert proof["confidence"] == 0.88
    assert proof["required_actions"] == []
    assert proof["heavy_evidence_sha256"] == "f5f16ba4903acc18638ab8a882713b3a19a2352c6ba5f63c8c085b6eaaf0b0e3"
    assert proof["review_evidence_sha256"] == "21d1805e9cafb5f83feba5e32ba9db2a5435fb89600f6d553b35edbf312bca95"


def test_closeout_only_grants_qualified_capsule_recovery_authority_after_guarded_merge():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["lifecycle_state"] == "PROVEN"
    assert manifest["produces"] == ["QUALIFIED_ASSURANCE_CAPSULE", "QUALIFIED_RECOVERY_PROTOCOL"]
    assert manifest["normal_verdict_authority"] is False
    assert manifest["genesis_activated"] is False
    assert manifest["dependent_nodes_auto_proven"] is False
    assert manifest["partial_generation_activation"] is False
    assert manifest["closeout_guarded_merge_required_before_authority"] is True
