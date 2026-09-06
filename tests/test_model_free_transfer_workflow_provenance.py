from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = (
    ".github/workflows/model-free-core-transfer-7.yml",
    ".github/workflows/model-free-core-transfer-8.yml",
    ".github/workflows/model-free-core-transfer-9.yml",
    ".github/workflows/model-free-core-auth-transfer-6.yml",
    ".github/workflows/model-free-core-auth-transfer-7.yml",
    ".github/workflows/model-free-core-auth-transfer-8.yml",
    ".github/workflows/model-free-core-await-transfer-1.yml",
    ".github/workflows/model-free-core-await-transfer-2.yml",
    ".github/workflows/model-free-core-await-transfer-3.yml",
    ".github/workflows/model-free-core-await-transfer-4.yml",
    ".github/workflows/model-free-core-await-transfer-5.yml",
    ".github/workflows/model-free-core-await-transfer-6.yml",
)


def test_every_legacy_untouched_transfer_fixture_binds_required_provenance() -> None:
    for relative in WORKFLOWS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert '"classification": "untouched_transfer_validation"' in text, relative
        assert '"provenance_required": True' in text, relative
        assert '"provenance_contract": "sergeant.training-provenance.v1"' in text, relative
        assert text.count('"fixing_ref"') >= 3, relative
        assert text.count('"source_lineage"') >= 3, relative


def test_provenance_enforcement_remains_fail_closed() -> None:
    text = (ROOT / "scripts/run_static_training_set.py").read_text(encoding="utf-8")
    assert "if classification == _FRESH_CLASSIFICATION:" in text
    assert "if not provenance_requested:" in text
    assert '"rules.provenance_required must be true"' in text
    assert "return validate_training_manifest(manifest)" in text
