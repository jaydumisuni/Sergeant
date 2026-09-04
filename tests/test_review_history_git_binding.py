from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/79-sae10-review-world-rab-manifest.json"
SAE10_V13_REVIEW = "exact_v13_completion_hostile_review"
ESTABLISHING_REVIEW = "exact_v8_generated_binding_hostile_review"
REGRESSION_PATH = "tests/test_review_world_git.py"


def _git_blob_at(commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{commit}:{path}"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    blob = result.stdout.strip()
    assert len(blob) == 40 and all(char in "0123456789abcdef" for char in blob)
    return blob


def test_reviewed_regression_blob_is_bound_to_exact_historical_git_tree() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    reviews = manifest["github_hostile_review"]
    reviewed = reviews[SAE10_V13_REVIEW]
    establishing = reviews[ESTABLISHING_REVIEW]

    assert reviewed["reviewed_head"] == "f3f1f25da2f317fb7068fc22c0bc45da40e48718"
    recorded_blob = reviewed["reviewed_head_regression_blob"]

    # Bind the evidence to Git history itself, not to a second free literal.
    assert _git_blob_at(reviewed["reviewed_head"], REGRESSION_PATH) == recorded_blob
    assert establishing["replacement_content_blobs"][REGRESSION_PATH] == recorded_blob
