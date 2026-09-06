from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WORKFLOWS = {
    ".github/workflows/model-free-core-transfer-7.yml": 2,
    ".github/workflows/model-free-core-transfer-8.yml": 3,
    ".github/workflows/model-free-core-transfer-9.yml": 3,
    ".github/workflows/model-free-core-auth-transfer-6.yml": 2,
    ".github/workflows/model-free-core-auth-transfer-7.yml": 3,
    ".github/workflows/model-free-core-auth-transfer-8.yml": 3,
    ".github/workflows/model-free-core-await-transfer-1.yml": 3,
    ".github/workflows/model-free-core-await-transfer-2.yml": 3,
    ".github/workflows/model-free-core-await-transfer-3.yml": 3,
    ".github/workflows/model-free-core-await-transfer-4.yml": 3,
    ".github/workflows/model-free-core-await-transfer-5.yml": 3,
    ".github/workflows/model-free-core-await-transfer-6.yml": 2,
}

ARCHIVED_CONTROLS = {
    ".github/transfer-evidence/model-free-core-transfer-7-c-archive.json": {
        "workflow": ".github/workflows/model-free-core-transfer-7.yml",
        "case_id": "transfer-7-c",
        "repository": "Ithastobe1/Velesia-codex",
        "defective_ref": "c81b3d80880a4181e5e0ec5bdef533fd5bad3807",
        "workflow_run_id": 29691505027,
        "artifact_id": 8443714087,
        "artifact_digest": "sha256:00407f5b9ed46283d3d79c876f4e972d352dde5475846f03bc4eb090a38b82a7",
        "verdict": "APPROVE",
        "historical_fixing_ref": None,
    },
    ".github/transfer-evidence/model-free-core-auth-transfer-6-c-archive.json": {
        "workflow": ".github/workflows/model-free-core-auth-transfer-6.yml",
        "case_id": "auth-transfer-6-c",
        "repository": "Magedemil/Claude",
        "defective_ref": "7f1c4c67a7f9a9131f07e9693bb290acb28ca67d",
        "workflow_run_id": 29691504987,
        "artifact_id": 8443712391,
        "artifact_digest": "sha256:512f0ac6072481a6906abab02217918addf39e21b0e4e18afc3b0047ba4de63c",
        "verdict": "REQUEST_CHANGES",
        "historical_fixing_ref": "1414d426688e68ce1430a68161a47fa70a837c49",
    },
    ".github/transfer-evidence/model-free-core-await-transfer-6-b-archive.json": {
        "workflow": ".github/workflows/model-free-core-await-transfer-6.yml",
        "case_id": "await-transfer-6-b",
        "repository": "amoghmokshit-blip/Scale-Chat",
        "defective_ref": "0eace8167c9b120954b0db4c929b969be23f6f07",
        "workflow_run_id": 29691504958,
        "artifact_id": 8443714148,
        "artifact_digest": "sha256:a128d8300fb9b5b5b37a96c936997b7c08ffc678abc708e5027c307319781a47",
        "verdict": "REQUEST_CHANGES",
        "historical_fixing_ref": "3d875ab139871cf44420d3133cd8041cf9123e9a",
    },
}


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


def test_dead_external_cases_are_archived_without_becoming_live_reruns() -> None:
    for relative, expected in ARCHIVED_CONTROLS.items():
        workflow = (ROOT / expected["workflow"]).read_text(encoding="utf-8")
        archive = json.loads((ROOT / relative).read_text(encoding="utf-8"))

        assert f'"case_id": "{expected["case_id"]}"' in workflow
        assert '"status": "archived_non_rerunnable_external_source"' in workflow
        assert f'"evidence_path": "{relative}"' in workflow

        assert archive["status"] == "archived_non_rerunnable_external_source"
        assert archive["repository"] == expected["repository"]
        assert archive["defective_ref"] == expected["defective_ref"]
        assert archive["workflow_run_id"] == expected["workflow_run_id"]
        assert archive["workflow_run_conclusion"] == "success"
        assert archive["artifact_id"] == expected["artifact_id"]
        assert archive["artifact_digest"] == expected["artifact_digest"]
        assert archive["frozen_summary"]["unavailable_requested_files"] == []
        assert archive["frozen_summary"]["verdict"] == expected["verdict"]

        historical_fixing_ref = expected["historical_fixing_ref"]
        if historical_fixing_ref is None:
            assert "historical_fixing_ref" not in archive
            assert "No fixing_ref is asserted" in archive["provenance_nonclaim"]
        else:
            assert archive["historical_fixing_ref"] == historical_fixing_ref
            assert "No claim is made" in archive["provenance_nonclaim"]


def test_live_case_counts_exclude_archived_external_sources() -> None:
    for workflow_path, live_case_count in WORKFLOWS.items():
        text = (ROOT / workflow_path).read_text(encoding="utf-8")
        assert text.count('"fixing_ref"') == live_case_count, workflow_path


def test_provenance_enforcement_remains_fail_closed() -> None:
    text = (ROOT / "scripts/run_static_training_set.py").read_text(encoding="utf-8")
    assert "if classification == _FRESH_CLASSIFICATION:" in text
    assert "if not provenance_requested:" in text
    assert '"rules.provenance_required must be true"' in text
    assert "return validate_training_manifest(manifest)" in text
