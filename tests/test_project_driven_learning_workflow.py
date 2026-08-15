from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "project-driven-self-learning.yml"
MANIFEST = ROOT / ".github" / "self-learning" / "project-driven" / "techguycheckm8-round-1.json"


def test_project_driven_learning_workflow_is_owner_gated_and_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "permissions: {}" in text
    assert "self-learning-authorized" in text
    assert "START_PROJECT_LEARNING" in text
    assert text.count("persist-credentials: false") >= 2
    assert "contents: write" not in text
    assert "pull-requests: write" not in text
    assert "models: read" in text
    assert "may_auto_promote" in text
    assert "may_auto_merge" in text
    assert "SERGEANT_PROJECT_LEARNING_PROPOSALS_BEGIN" in text


def test_techguycheckm8_project_round_binds_exact_harvest_candidates() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "sergeant.project-learning-round.v1"
    assert payload["candidate_count"] == 2
    assert payload["expected_case_ids"] == [
        "learn-tgcheckm8-checksum-path-namespace-20260723",
        "learn-tgcheckm8-checkout-credential-boundary-20260723",
    ]
    assert payload["signal_paths"] == [
        ".github/self-learning/signals/tgcheckm8-checksum-path-namespace-2026-07-23.json",
        ".github/self-learning/signals/tgcheckm8-checkout-credential-boundary-2026-07-23.json",
    ]
    assert payload["authority"] == {
        "required_label": "self-learning-authorized",
        "required_commit_prefix": "START_PROJECT_LEARNING",
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }
