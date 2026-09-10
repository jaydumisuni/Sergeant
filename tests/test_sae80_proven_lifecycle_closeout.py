from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/113-sae80-proven-lifecycle-closeout-manifest.json"
DOC = ROOT / "docs/112-sae80-proven-lifecycle-closeout.md"
CANDIDATE = ROOT / "docs/111-sae80-evidence-proof-world-candidate-manifest.json"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def working_tree_blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / path)], cwd=ROOT, text=True).strip()


def test_sae80_closeout_binds_exact_clean_candidate_and_guarded_merge():
    closeout = load(MANIFEST)
    assert closeout["node"] == "SAE-80"
    assert closeout["lifecycle_state"] == "PROVEN"
    generation = closeout["candidate_generation"]
    merge = closeout["canonical_candidate_merge"]
    assert generation["head"] == "e35d3b4d14f6fa45bb84375eb9b9bc481794e365"
    assert generation["tree"] == "8b96fe5ff3b5477c63540f5231076bc3cbba11af"
    assert generation["pull_request"] == 206
    assert merge["commit"] == "329ac37be70fcae86ece5c877ec31592a77c0f60"
    assert merge["tree"] == generation["tree"]
    assert merge["parents"] == ["5ae80680a02562707a82064cc8d5f4e8196ddb8b", generation["head"]]
    assert merge["exact_head_guard"] == generation["head"]


def test_sae80_closeout_preserves_exact_candidate_content():
    closeout = load(MANIFEST)
    blobs = closeout["candidate_generation"]["content_blobs"]
    for path, expected in blobs.items():
        assert working_tree_blob(path) == expected


def test_sae80_closeout_advances_only_qualified_evidence_and_proof_world():
    closeout = load(MANIFEST)
    assert closeout["produces"] == ["QUALIFIED_EVIDENCE_CONTRACT", "QUALIFIED_PROOF_WORLD"]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["genesis_activated"] is False
    assert closeout["dependent_nodes_auto_proven"] is False
    assert closeout["partial_generation_activation"] is False
    assert closeout["proof_requires"] == ["SAE-30", "SAE-40", "SAE-50", "SAE-60", "SAE-70"]


def test_sae80_qualification_scope_is_fail_closed_and_recomputed():
    scope = load(MANIFEST)["qualified_scope"]
    assert scope["exact_obligation_binding"] is True
    assert scope["qualified_sae70_closure_revalidated"] is True
    assert scope["proof_world_identity_recomputed"] is True
    assert scope["material_input_closure_required"] is True
    assert scope["frankenworld_allowed"] is False
    assert scope["heuristic_may_claim_exact"] is False
    assert scope["stale_evidence_yields_unknown"] is True
    assert scope["unresolved_assumption_caps_exact"] is True
    assert scope["hidden_contradiction_caps_exact"] is True


def test_sae80_closeout_document_and_roadmap_boundary_are_explicit():
    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "conditional on this exact closeout generation" in text
    assert "QUALIFIED_EVIDENCE_CONTRACT" in text
    assert "QUALIFIED_PROOF_WORLD" in text
    assert "does **not**" in text
    assert "activate Genesis" in text
    assert "auto-prove SAE-90" in text
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "### SAE-80" in roadmap
    assert "QUALIFIED_EVIDENCE_CONTRACT" in roadmap
    assert "QUALIFIED_PROOF_WORLD" in roadmap
