from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/126-sae100-task17-frozen-predecessor-authority-amendment.md"
MANIFEST = ROOT / "docs/127-sae100-task17-frozen-predecessor-authority-amendment-manifest.json"

EXPECTED = {
    "main_review/officer_council.py": "0089e55db3493501e85fba30f502b36f59fc5433",
    "main_review/judge_assurance_adapter.py": "522b01881894e2acf5898a32964c04303b585307",
    "main_review/final_proof.py": "8ee97495afabd7828a5fc8c37b44e5b802cbeded",
}


def _blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()


def test_amendment_record_binds_exact_source_authority_and_frozen_blobs():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_main"] == "4655d18e979e62baf31f301df295e11483d19c00"
    assert manifest["source_plan_blob"] == "b78b960430182216dfce4ce5a6e2c671f2f9e393"
    assert manifest["frozen_predecessor_blobs"] == EXPECTED
    for path, expected in EXPECTED.items():
        assert _blob(path) == expected


def test_amendment_preserves_lifecycle_and_replaces_only_impossible_in_place_edits():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["state"] == "PROPOSED_AUTHORITY_AMENDMENT"
    assert manifest["requires_explicit_approval_before_guarded_merge"] is True
    assert manifest["normal_verdict_authority_gain"] is False
    assert manifest["genesis_activated"] is False
    assert manifest["replacement_rule"] == "SUCCESSOR_NON_MUTATING_INTEGRATION_SEAMS"
    assert manifest["still_required_in_place"] == ["main_review/cpl_campaign.py"]
    assert set(manifest["preserve_unchanged"]) == set(EXPECTED)


def test_amendment_document_is_not_self_activating():
    text = DOC.read_text(encoding="utf-8")
    assert "does not amend Task 17 merely by existing" in text
    assert "explicit approval" in text
    assert "guarded merge" in text
    assert "PR #221 must not be merged" in text
    assert "successor/non-mutating integration seams" in text
