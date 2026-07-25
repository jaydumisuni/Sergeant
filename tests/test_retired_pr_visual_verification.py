from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HARVEST = ROOT / "docs" / "53-retired-pr-lesson-harvest.md"
VISUAL_PROOF = ROOT / "docs" / "54-retired-pr-harvest-visual-verification.md"


def test_harvest_uses_mobile_readable_disposition_records() -> None:
    text = HARVEST.read_text(encoding="utf-8")
    assert "responsive records instead of a wide table" in text
    assert "| PRs | Disposition | Reason |" not in text
    assert text.count("- **Disposition:**") == 11
    assert text.count("- **Reason:**") == 11


def test_visual_proof_uses_mobile_readable_matrix_records() -> None:
    text = VISUAL_PROOF.read_text(encoding="utf-8")
    assert "matrix is written as responsive records" in text
    assert "| View | Width × initial height | Result |" not in text
    assert "Mobile disposition-table readability: FAILED initially → REPAIRED → PASS" in text
    assert "Visual-proof matrix readability: COMPRESSED initially → REPAIRED → PASS" in text
    assert "package SHA-256: d93bb4214daa1cb0d86be06bb473cfbc7fe4df9cc4659fb28733ad0882d3d139" in text
    assert "review collage SHA-256: f4db511969051dcb4e7329716218d6eba84e8b39b64edf9a2b81aa8031a584cf" in text
