from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/115-sae90-falsification-frontier-candidate-manifest.json"
DOC = ROOT / "docs/114-sae90-falsification-frontier-candidate.md"
SAE80_PROVEN_MERGE = "b6e1fe5bbbead26e885e44eecec72b873b4b6ee6"
SAE80_CLOSEOUT_HEAD = "754ec015b648e60cd7cace978d76a1b6a1e749a2"
SAE90_MERGED_CANDIDATE = "f37cc9f3393f159ffacf42ce79567e9f13aa00d8"
SAE90_CANDIDATE_MERGE = "e663d4e69a00ea8d107b01eae5aad86b48b9c4fd"


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_candidate_record_binds_proven_sae80_authority() -> None:
    m = load()
    assert m["construction_base"] == SAE80_PROVEN_MERGE
    assert m["proven_sae80_authority"] == {
        "closeout_head": SAE80_CLOSEOUT_HEAD,
        "canonical_merge": SAE80_PROVEN_MERGE,
        "lifecycle_state": "PROVEN",
    }
    assert "current_blocker" not in m


def test_candidate_record_preserves_original_merged_candidate_identity() -> None:
    m = load()
    assert m["preserved_candidate_generation"]["head"] == SAE90_MERGED_CANDIDATE
    assert m["preserved_candidate_generation"]["canonical_merge"] == SAE90_CANDIDATE_MERGE
    assert m["preserved_candidate_generation"]["record_correction_required"] is True


def test_document_no_longer_claims_sae80_is_unproven() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert SAE80_PROVEN_MERGE in text
    assert SAE80_CLOSEOUT_HEAD in text
    assert "SAE-80 is not represented here as PROVEN" not in text
    assert "Qualification and lifecycle promotion therefore remain fail-closed" not in text
