from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Shared repository proof infrastructure. New lifecycle nodes may add lineage
# cases here without changing the proof mechanism or test-node count.
LINEAGE_CASES = (
    {
        "manifest": "docs/79-sae10-review-world-rab-manifest.json",
        "reviewed_key": "exact_v13_completion_hostile_review",
        "reviewed_head": "f3f1f25da2f317fb7068fc22c0bc45da40e48718",
        "recorded_blob_key": "reviewed_head_regression_blob",
        "establishing_key": "exact_v8_generated_binding_hostile_review",
        "establishing_head": "16c623935549d7b87ae0b96eef58c8630d252c73",
        "artifact_path": "tests/test_review_world_git.py",
    },
)


def test_recorded_review_artifacts_are_chained_to_establishing_generation() -> None:
    for case in LINEAGE_CASES:
        manifest = json.loads((ROOT / case["manifest"]).read_text(encoding="utf-8"))
        reviews = manifest["github_hostile_review"]
        reviewed = reviews[case["reviewed_key"]]
        establishing = reviews[case["establishing_key"]]

        assert reviewed["reviewed_head"] == case["reviewed_head"]
        assert establishing["reviewed_head"] == case["establishing_head"]

        recorded_blob = reviewed[case["recorded_blob_key"]]
        assert len(recorded_blob) == 40 and all(char in "0123456789abcdef" for char in recorded_blob)

        # Historical provenance is a relation between immutable review
        # generations, not two independently editable literals in one record.
        assert establishing["replacement_content_blobs"][case["artifact_path"]] == recorded_blob
