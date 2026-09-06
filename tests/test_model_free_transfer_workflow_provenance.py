from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WORKFLOWS = {
    ".github/workflows/model-free-core-transfer-7.yml": 2,
    ".github/workflows/model-free-core-transfer-8.yml": 3,
    ".github/workflows/model-free-core-transfer-9.yml": 3,
    ".github/workflows/model-free-core-auth-transfer-6.yml": 3,
    ".github/workflows/model-free-core-auth-transfer-7.yml": 3,
    ".github/workflows/model-free-core-auth-transfer-8.yml": 3,
    ".github/workflows/model-free-core-await-transfer-1.yml": 3,
    ".github/workflows/model-free-core-await-transfer-2.yml": 3,
    ".github/workflows/model-free-core-await-transfer-3.yml": 3,
    ".github/workflows/model-free-core-await-transfer-4.yml": 3,
    ".github/workflows/model-free-core-await-transfer-5.yml": 3,
    ".github/workflows/model-free-core-await-transfer-6.yml": 3,
}

ARCHIVED_TRANSFER_7_C = (
    ROOT / ".github/transfer-evidence/model-free-core-transfer-7-c-archive.json"
)


def test_every_legacy_untouched_transfer_fixture_binds_required_provenance() -> None:
    for relative, live_case_count in WORKFLOWS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert '"classification": "untouched_transfer_validation"' in text, relative
        assert '"provenance_required": True' in text, relative
        assert (
            '"provenance_contract": "sergeant.training-provenance.v1"' in text
        ), relative
        assert '"reviewer_code_frozen_before_target_selection"' in text, relative
        assert text.count('"fixing_ref"') >= live_case_count, relative
        assert text.count('"source_lineage"') >= live_case_count, relative


def test_transfer_7_dead_external_case_is_archived_without_invented_lineage() -> None:
    workflow = (
        ROOT / ".github/workflows/model-free-core-transfer-7.yml"
    ).read_text(encoding="utf-8")
    archive = json.loads(ARCHIVED_TRANSFER_7_C.read_text(encoding="utf-8"))

    assert workflow.count('"fixing_ref"') == 2
    assert '"case_id": "transfer-7-c"' in workflow
    assert '"status": "archived_non_rerunnable_external_source"' in workflow
    assert (
        '"evidence_path": ".github/transfer-evidence/model-free-core-transfer-7-c-archive.json"'
        in workflow
    )

    assert archive["status"] == "archived_non_rerunnable_external_source"
    assert archive["repository"] == "Ithastobe1/Velesia-codex"
    assert archive["defective_ref"] == "c81b3d80880a4181e5e0ec5bdef533fd5bad3807"
    assert archive["workflow_run_id"] == 29691505027
    assert archive["workflow_run_conclusion"] == "success"
    assert archive["artifact_id"] == 8443714087
    assert archive["artifact_digest"] == (
        "sha256:00407f5b9ed46283d3d79c876f4e972d352dde5475846f03bc4eb090a38b82a7"
    )
    assert archive["frozen_summary"]["unavailable_requested_files"] == []
    assert archive["frozen_summary"]["verdict"] == "APPROVE"
    assert "No fixing_ref is asserted" in archive["provenance_nonclaim"]


def test_provenance_enforcement_remains_fail_closed() -> None:
    text = (ROOT / "scripts/run_static_training_set.py").read_text(encoding="utf-8")
    assert "if classification == _FRESH_CLASSIFICATION:" in text
    assert "if not provenance_requested:" in text
    assert '"rules.provenance_required must be true"' in text
    assert "return validate_training_manifest(manifest)" in text
