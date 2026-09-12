from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/123-sae100-sergeant-integration-candidate-manifest.json"


def blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / path)], text=True).strip()


def test_candidate_consumes_exact_merged_task17_amendment():
    data = json.loads(MANIFEST.read_text())
    assert data["node"] == "SAE-100"
    assert data["lifecycle_state"] == "CANDIDATE"
    assert data["mode"] == "SHADOW_OR_QUALIFICATION_ONLY"
    assert data["authority_amendment"]["proposal_head"] == "1ae04ad3b08edda18ff17ba4c29bb19e528a0084"
    assert data["authority_amendment"]["merge_commit"] == "0cd738ccbe392220ff6def65f6a07a1812f26e58"
    assert data["authority_amendment"]["replacement_rule"] == "SUCCESSOR_NON_MUTATING_INTEGRATION_SEAMS"
    assert data["candidate_merge_authorized"] is False
    assert data["genesis_activated"] is False
    assert data["normal_verdict_authority_gain"] is False


def test_candidate_preserves_all_three_frozen_predecessors_exactly():
    data = json.loads(MANIFEST.read_text())
    expected = {
        "main_review/officer_council.py": "0089e55db3493501e85fba30f502b36f59fc5433",
        "main_review/judge_assurance_adapter.py": "522b01881894e2acf5898a32964c04303b585307",
        "main_review/final_proof.py": "8ee97495afabd7828a5fc8c37b44e5b802cbeded",
    }
    assert data["frozen_predecessor_blobs"] == expected
    assert {path: blob(path) for path in expected} == expected


def test_candidate_uses_successor_seam_and_required_cpl_edit_only():
    data = json.loads(MANIFEST.read_text())
    assert data["changed_task17_surfaces"] == [
        "main_review/assurance_integration.py",
        "main_review/cpl_campaign.py",
        "tests/test_assurance_integration.py",
        "tests/test_sae100_post_amendment_candidate.py",
        "docs/122-sae100-sergeant-integration-candidate.md",
        "docs/123-sae100-sergeant-integration-candidate-manifest.json",
    ]
