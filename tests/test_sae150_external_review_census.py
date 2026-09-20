from __future__ import annotations

import json
from pathlib import Path

from scripts.sae150_external_review_census import census_payload, derive_census

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/172-sae150-external-review-intake-manifest.json"
TEMPLATE = ROOT / "docs/174-sae150-external-review-submission-template.json"


def test_empty_external_evidence_census_remains_fail_closed():
    census = derive_census(())
    payload = census_payload(census, ())
    assert census.satisfied is False
    assert payload["eligible_independent_count"] == 0
    assert payload["eligible_source_classes"] == []
    assert payload["remaining_blocker"] == "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE"


def test_submission_template_is_bound_to_frozen_candidate_and_world():
    manifest = json.loads(MANIFEST.read_text())
    template = json.loads(TEMPLATE.read_text())
    assert template["frozen_candidate"] == manifest["candidate_generation"]
    assert template["review_world_id"] == manifest["review_world_id"]
    assert set(template["control_lineage_facts"]) == {
        "source_separate",
        "authoring_separate",
        "corpus_separate",
        "infrastructure_separate",
        "prompt_control_separate",
        "input_selection_separate",
        "finding_selection_separate",
    }
    assert all(value is None for value in template["control_lineage_facts"].values())
