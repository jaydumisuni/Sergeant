from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/124-sae100-proven-lifecycle-closeout.md"
MANIFEST = ROOT / "docs/125-sae100-proven-lifecycle-closeout-manifest.json"


def load():
    return json.loads(MANIFEST.read_text())


def blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", str(ROOT / path)], cwd=ROOT, text=True).strip()


def test_exact_candidate_and_guarded_merge_binding():
    m = load()
    g = m["candidate_generation"]
    merge = m["canonical_candidate_merge"]
    assert m["node"] == "SAE-100"
    assert m["lifecycle_state"] == "PROVEN"
    assert g["pull_request"] == 225
    assert g["head"] == "346569c1488926646aa01eb0e77cbee444023f0c"
    assert g["tree"] == "bcc5c4d7d1ebad45e4d9ffb80084a1562865406e"
    assert merge["commit"] == "1c990d87e60e334a92dce147a7cca5c743172783"
    assert merge["tree"] == g["tree"]
    assert merge["parents"] == ["0cd738ccbe392220ff6def65f6a07a1812f26e58", g["head"]]
    assert merge["exact_head_guard"] == g["head"]
    assert merge["authority_gain_at_candidate_merge"] == "none"


def test_candidate_authority_blobs_are_frozen():
    g = load()["candidate_generation"]
    expected = [
        ("docs/122-sae100-sergeant-integration-candidate.md", "candidate_document_blob"),
        ("docs/123-sae100-sergeant-integration-candidate-manifest.json", "candidate_manifest_blob"),
        ("main_review/assurance_integration.py", "integration_blob"),
        ("main_review/cpl_campaign.py", "cpl_campaign_blob"),
        ("tests/test_assurance_integration.py", "hostile_campaign_blob"),
        ("tests/test_sae100_post_amendment_candidate.py", "post_amendment_boundary_blob"),
    ]
    for path, key in expected:
        assert blob(path) == g[key]


def test_closeout_advances_only_integrated_shadow_assurance_authority():
    m = load()
    assert m["produces"] == ["INTEGRATED_SHADOW_ASSURANCE_SERGEANT"]
    assert m["normal_verdict_authority"] is False
    assert m["genesis_activated"] is False
    assert m["dependent_nodes_auto_proven"] is False
    assert m["partial_generation_activation"] is False


def test_document_keeps_genesis_and_downstream_authority_closed():
    text = DOC.read_text()
    assert "Status: **PROVEN**" in text
    assert "conditional on this exact closeout generation" in text
    assert "INTEGRATED_SHADOW_ASSURANCE_SERGEANT" in text
    assert "does **not**" in text
    assert "activate Genesis" in text
    assert "auto-prove SAE-110" in text
