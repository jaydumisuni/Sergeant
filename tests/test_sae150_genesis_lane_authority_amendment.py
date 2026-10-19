from __future__ import annotations

import json
import subprocess
from pathlib import Path

from main_review.genesis_qualification import (
    ACCEPTED_EXTERNAL_SOURCE_CLASSES,
    DEFAULT_GENESIS_LANE_ID,
    LANE_CARDINALITY_FLOOR,
    LANE_SOURCE_CLASS_FLOOR,
)

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/165-sae150-genesis-lane-cardinality-authority-amendment.md"
MANIFEST = ROOT / "docs/166-sae150-genesis-lane-cardinality-authority-amendment-manifest.json"

EXPECTED_BLOBS = {
    "docs/58-sergeant-assurance-evolution-founding-architecture.md": "b7d7ea0cec987046ece2aecb554cc29d86aa447b",
    "docs/59-sergeant-assurance-evolution-roadmap.md": "f54dd414da2c01284c94a3f7349030da0cda4457",
    "docs/85-sae20-proven-lifecycle-closeout-manifest.json": "292590bb429a0bbd7e5376afa3a79698e3705345",
    "docs/69-spike-ext-proven-lifecycle-closeout-manifest.json": "5a42072517efef7c1e621f12a99e9e2cbf610281",
}


def _blob(path: str) -> str:
    return subprocess.check_output(["git", "hash-object", path], cwd=ROOT, text=True).strip()


def test_authority_proposal_is_non_authoritative_until_guarded_merge():
    data = json.loads(MANIFEST.read_text())
    assert data["lifecycle_state"] == "AUTHORITY_PROPOSAL"
    assert data["authority_gain_before_guarded_merge"] == "none"
    assert data["explicit_owner_root_approval_required"] is True
    assert data["guarded_merge_required"] is True
    assert data["consumption_authorized_before_guarded_merge"] is False


def test_proposal_is_exactly_bound_to_current_sae150_generation():
    data = json.loads(MANIFEST.read_text())
    assert data["base_sae150_head"] == "ddf1b8b63680e124654fc6f0f541a3326c8f03c7"
    assert data["target_branch"] == "roadmap/sae150-genesis-qualification-20260912"


def test_proposal_adopts_proven_floor_without_weakening():
    data = json.loads(MANIFEST.read_text())
    lane = data["proposed_ratification"]
    assert lane["lane_id"] == DEFAULT_GENESIS_LANE_ID
    assert lane["minimum_instances"] == LANE_CARDINALITY_FLOOR == 2
    assert lane["minimum_distinct_source_classes"] == LANE_SOURCE_CLASS_FLOOR == 2
    assert lane["independence_required"] is True
    assert lane["accepted_source_classes"] == list(ACCEPTED_EXTERNAL_SOURCE_CLASSES)
    assert lane["excluded_standalone_source_classes"] == ["SC-5"]


def test_source_authority_blobs_are_exact():
    data = json.loads(MANIFEST.read_text())
    mapped = {entry["path"]: entry["blob"] for entry in data["sources"].values()}
    assert mapped == EXPECTED_BLOBS
    for path, expected in EXPECTED_BLOBS.items():
        assert _blob(path) == expected


def test_approval_would_remove_only_lane_ratification_blocker():
    data = json.loads(MANIFEST.read_text())
    effect = data["effect_if_approved_and_guarded_merged"]
    assert effect["lane_cardinality_ratified"] is True
    assert effect["removes_only_blocker"] == "GENESIS_LANE_CARDINALITY_UNRATIFIED"
    assert effect["materially_independent_external_evidence_created"] is False
    assert effect["provenance_verifier_rooted"] is False
    assert effect["genesis_activated"] is False
    assert effect["normal_verdict_authority_changed"] is False
    assert effect["candidate_merge_authorized"] is False


def test_authority_proposal_document_preserves_independence_boundary():
    text = DOC.read_text()
    assert "Owner-controlled AI" in text
    assert "carries no ratification authority" in text
    assert "No force-push or history rewrite is authorized." in text
