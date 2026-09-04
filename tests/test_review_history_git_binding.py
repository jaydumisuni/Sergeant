from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/79-sae10-review-world-rab-manifest.json"
SAE10_V13_REVIEW = "exact_v13_completion_hostile_review"
ESTABLISHING_REVIEW = "exact_v8_generated_binding_hostile_review"
REGRESSION_PATH = "tests/test_review_world_git.py"


def test_reviewed_regression_blob_is_chained_to_establishing_review_generation() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reviews = manifest["github_hostile_review"]
    reviewed = reviews[SAE10_V13_REVIEW]
    establishing = reviews[ESTABLISHING_REVIEW]

    assert reviewed["reviewed_head"] == "f3f1f25da2f317fb7068fc22c0bc45da40e48718"
    assert establishing["reviewed_head"] == "16c623935549d7b87ae0b96eef58c8630d252c73"

    recorded_blob = reviewed["reviewed_head_regression_blob"]
    assert len(recorded_blob) == 40 and all(char in "0123456789abcdef" for char in recorded_blob)

    # Historical provenance must be a relation between review generations,
    # not two independently editable literals in the same proof generation.
    assert establishing["replacement_content_blobs"][REGRESSION_PATH] == recorded_blob
