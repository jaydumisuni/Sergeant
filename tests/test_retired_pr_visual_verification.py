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
    assert "excluded from the core package hash" in text
    assert "Mobile disposition-table readability: FAILED initially → REPAIRED → PASS" in text
    assert "Visual-proof matrix readability: COMPRESSED initially → REPAIRED → PASS" in text
    assert "core package SHA-256: 73c8bcb798a02cf1cc25c86b3e959fdfa6b7476d98f6e2c31dd39a7f7e39dccb" in text
    assert "full core collage SHA-256: 8370677def147d099f4ddaa064ae3334707f6e001e29152e9847416dd7bff6b1" in text
    assert "review collage SHA-256: e1d4dd9db87bbcb20c4a7ab06c873aced9e7afc5555db67d92946dffc8bda211" in text


def test_corrected_durable_visual_copy_is_replayed_exactly() -> None:
    text = VISUAL_PROOF.read_text(encoding="utf-8")
    assert "Drive file name: pr149-visual-verification-evidence-exact.jpg" in text
    assert "size: 97,059 bytes" in text
    assert "SHA-256: e1d4dd9db87bbcb20c4a7ab06c873aced9e7afc5555db67d92946dffc8bda211" in text
    assert "matched the exact local collage at the byte length, SHA-256 digest, and raw bytes" in text
    assert "Corrected durable visual copy: PASS" in text
    assert "Corrected recovery byte replay: PASS" in text
