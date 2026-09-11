from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def test_task17_required_modifications_collide_with_frozen_predecessor_blobs():
    roadmap = (ROOT / "docs/superpowers/plans/2026-09-07-sae-30-through-100.md").read_text()
    sae00 = json.loads((ROOT / "docs/63-sae00-founding-authority-reference-manifest.json").read_text())
    sae40 = json.loads((ROOT / "docs/87-sae40-judge-assurance-ledger-candidate-manifest.json").read_text())
    required = {"main_review/officer_council.py", "main_review/final_proof.py", "main_review/judge_assurance_adapter.py"}
    assert all(path in roadmap for path in required)
    sae00_paths = {item["path"] for item in sae00["documents"]}
    sae40_paths = set(sae40["content_blobs"])
    assert {"main_review/officer_council.py", "main_review/final_proof.py"} <= sae00_paths
    assert "main_review/judge_assurance_adapter.py" in sae40_paths

def test_blocked_manifest_refuses_candidate_merge_authority():
    manifest = json.loads((ROOT / "docs/123-sae100-sergeant-integration-candidate-manifest.json").read_text())
    assert manifest["qualification_state"] == "BLOCKED_FROZEN_PREDECESSOR_COLLISION"
    assert manifest["candidate_merge_authorized"] is False
    assert manifest["genesis_activated"] is False
    assert manifest["normal_verdict_authority_gain"] is False
