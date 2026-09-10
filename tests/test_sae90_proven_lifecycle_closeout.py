from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/117-sae90-proven-lifecycle-closeout-manifest.json"
DOC = ROOT / "docs/116-sae90-proven-lifecycle-closeout.md"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"

def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))

def blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / path)], cwd=ROOT, text=True).strip()

def test_closeout_binds_corrected_candidate_and_guarded_merge() -> None:
    m=load(); g=m["candidate_generation"]; merge=m["canonical_candidate_merge"]
    assert m["node"] == "SAE-90" and m["lifecycle_state"] == "PROVEN"
    assert g["pull_request"] == 214
    assert g["head"] == "f6ae8c812516b95eefe4c57e5d21f27b5dd1838e"
    assert g["tree"] == "2d8ecba10ce3e1f5419fb3b9b1c4ce75c4f13fd2"
    assert merge["commit"] == "bfa4808f1c13753eb16c0442e2fdfc59b441c564"
    assert merge["tree"] == g["tree"]
    assert merge["parents"] == ["e663d4e69a00ea8d107b01eae5aad86b48b9c4fd", g["head"]]
    assert merge["exact_head_guard"] == g["head"]
    assert merge["authority_gain_at_candidate_merge"] == "none"

def test_historical_candidate_content_and_pr213_are_preserved() -> None:
    g=load()["candidate_generation"]
    assert g["historical_pr213_preserved"] is True
    assert blob("docs/114-sae90-falsification-frontier-candidate.md") == g["candidate_document_blob"]
    assert blob("docs/115-sae90-falsification-frontier-candidate-manifest.json") == g["candidate_manifest_blob"]

def test_separate_qualification_protocol_is_content_bound() -> None:
    h=load()["qualification_hardening_generation"]
    assert h["head"] == "5aa6d0ba68794ee4ea9b7ed873e7a27b9aa2312c"
    assert h["protocol_generation"] == "sae90-qualification-v1"
    assert blob(h["protocol_path"]) == h["protocol_blob"]
    assert blob(h["qualification_campaign_path"]) == h["qualification_campaign_blob"]
    assert h["candidate_compiler_rewritten"] is False

def test_closeout_advances_only_falsification_authority() -> None:
    m=load()
    assert m["produces"] == ["QUALIFIED_FALSIFICATION_FRONTIER"]
    assert m["qualification_protocol_id"] == "QUALIFIED_FALSIFICATION_FRONTIER"
    assert m["normal_verdict_authority"] is False
    assert m["genesis_activated"] is False
    assert m["dependent_nodes_auto_proven"] is False
    assert m["partial_generation_activation"] is False

def test_qualification_scope_remains_fail_closed() -> None:
    s=load()["qualified_scope"]
    assert s["closed_parameter_domains_required"] is True
    assert s["expected_falsifier_instances_exact"] is True
    assert s["exhaustive_bounded_search_required"] is True
    assert s["no_op_mutation_allowed"] is False
    assert s["statistical_search_may_claim_exhaustive"] is False
    assert s["missing_instance_evidence_may_qualify"] is False
    assert s["canonical_recomputation_required"] is True
    assert s["exact_closure_required"] is True and s["blocker_free_required"] is True

def test_document_and_roadmap_keep_downstream_authority_closed() -> None:
    text=DOC.read_text(encoding="utf-8"); roadmap=ROADMAP.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text and "conditional on this exact closeout generation" in text
    assert "QUALIFIED_FALSIFICATION_FRONTIER" in text
    assert "does **not**" in text and "activate Genesis" in text and "auto-prove SAE-R2" in text
    assert "### SAE-90" in roadmap and "QUALIFIED_FALSIFICATION_FRONTIER" in roadmap
