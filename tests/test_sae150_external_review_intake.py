from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from main_review.genesis_qualification import (
    ACCEPTED_EXTERNAL_SOURCE_CLASSES,
    PROVENANCE_VERIFIER_ARTIFACT_FAMILY,
    PROVENANCE_VERIFIER_DOMAIN,
    PROVENANCE_VERIFIER_NAMESPACE,
    PROVENANCE_VERIFIER_PROOF_CLASS,
)
from main_review.review_authority_bundle import ReviewAuthorityBundle
from main_review.review_world import GitHubReviewWorld
from scripts.sae150_external_review_intake import load_registry, load_verifier, validate_public_packet

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/167-sae150-root-qualification-authority-registry.json"
VERIFIER = ROOT / "docs/168-sae150-provenance-verifier-authorization.json"
RAB = ROOT / "docs/169-sae150-external-review-rab.json"
WORLD = ROOT / "docs/170-sae150-external-review-world.json"
INTAKE = ROOT / "docs/172-sae150-external-review-intake-manifest.json"

AUTHORITY = {
    "epistemic_constitution": ("5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910", "docs/67-sae00-proven-lifecycle-closeout-manifest.json"),
    "safety_constitution": ("5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910", "docs/67-sae00-proven-lifecycle-closeout-manifest.json"),
    "acr_generation": ("2a1d16f9772997d993d0f0d41e1c5161f222f136", "docs/85-sae20-proven-lifecycle-closeout-manifest.json"),
    "capability_passport_registry": ("6d4ecc03782fa72d517e0b111a3757e4b2f65cf0", "docs/105-sae60-proven-lifecycle-closeout-manifest.json"),
    "obligation_law": ("5ae80680a02562707a82064cc8d5f4e8196ddb8b", "docs/109-sae70-proven-lifecycle-closeout-manifest.json"),
    "evidence_law": ("b6e1fe5bbbead26e885e44eecec72b873b4b6ee6", "docs/113-sae80-proven-lifecycle-closeout-manifest.json"),
    "independence_law": ("8df705d3cc6237937a8ee0bde74d44481d352679", "docs/93-sae30-proven-lifecycle-closeout-manifest.json"),
    "rust_contract_kernel": ("54154fd4490f437a580ea500c3ab215ee01d50ab", "docs/121-sae-r2-proven-lifecycle-closeout-manifest.json"),
    "root_authority": ("5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910", "docs/67-sae00-proven-lifecycle-closeout-manifest.json"),
}


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", ROOT, *args], text=True).strip()


def test_public_authority_packet_rederives_exact_identities():
    checks = validate_public_packet()
    manifest = json.loads(INTAKE.read_text())
    assert checks["qualification_authority_registry_id"] == manifest["qualification_authority_registry_id"]
    assert checks["provenance_verifier_authorization_id"] == manifest["provenance_verifier_authorization_id"]
    assert checks["rab_id"] == manifest["rab_id"]
    assert checks["review_world_id"] == manifest["review_world_id"]


def test_rooted_provenance_verifier_is_bound_into_qualification_registry():
    registry = load_registry(REGISTRY)
    verifier = load_verifier(VERIFIER)
    issuer = registry.find(verifier.verifier_identity, verifier.verifier_generation)
    assert issuer.namespace == PROVENANCE_VERIFIER_NAMESPACE
    assert issuer.key_id == verifier.key_id
    assert issuer.authentication_secret_digest == verifier.verification_secret_digest
    assert PROVENANCE_VERIFIER_ARTIFACT_FAMILY in issuer.artifact_families
    assert PROVENANCE_VERIFIER_DOMAIN in issuer.domains
    assert PROVENANCE_VERIFIER_PROOF_CLASS in issuer.proof_classes


def test_review_world_is_exact_pr245_head_world():
    world = GitHubReviewWorld.from_payload(json.loads(WORLD.read_text()))
    manifest = json.loads(INTAKE.read_text())
    assert world.repository == "jaydumisuni/sergeant"
    assert world.pr_number == 245
    assert world.review_mode == "head"
    assert world.diff.base_commit == "126eeea5a70a0723a1bfb65b2a5dbeb6a84cf2e0"
    assert world.diff.head_commit == "cd757111559b920db2a843d7ca837b2ae51eb774"
    assert world.diff.base_tree == git("rev-parse", f"{world.diff.base_commit}^{{tree}}")
    assert world.diff.head_tree == git("rev-parse", f"{world.diff.head_commit}^{{tree}}")
    assert world.rab_id == manifest["rab_id"]


def test_rab_slots_bind_proven_ancestor_generations_and_content():
    rab = ReviewAuthorityBundle.from_payload(json.loads(RAB.read_text()))
    slots = {item.name: item for item in rab.components}
    for slot, (generation, relpath) in AUTHORITY.items():
        item = slots[slot]
        assert item.lifecycle_state == "active"
        assert item.generation == generation
        assert subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", generation, "cd757111559b920db2a843d7ca837b2ae51eb774"]).returncode == 0
        data = (ROOT / relpath).read_bytes()
        assert item.content_id == hashlib.sha256(data).hexdigest()
        assert json.loads(data)["lifecycle_state"] == "PROVEN"


def test_intake_lane_is_exact_ratified_two_by_two_floor_and_stays_open():
    manifest = json.loads(INTAKE.read_text())
    lane = manifest["review_lane"]
    assert lane["minimum_instances"] == 2
    assert lane["minimum_distinct_source_classes"] == 2
    assert lane["accepted_source_classes"] == list(ACCEPTED_EXTERNAL_SOURCE_CLASSES)
    assert lane["standalone_excluded_source_classes"] == ["SC-5"]
    assert manifest["current_external_evidence_count"] == 0
    assert manifest["external_evidence_satisfied"] is False
    assert manifest["remaining_blocker"] == "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE"
    assert manifest["candidate_merge_authorized"] is False
    assert manifest["genesis_activated"] is False


def test_public_descriptors_contain_no_secret_material():
    tracked = git("ls-files").splitlines()
    assert not any(name.endswith("qualification-secret.bin") or name.endswith("provenance-verifier-secret.bin") for name in tracked)
    reg = json.loads(REGISTRY.read_text())
    ver = json.loads(VERIFIER.read_text())
    assert "verification_secret" not in ver
    assert "verification_secret_digest" in ver
    assert all("authentication_secret_digest" in issuer for issuer in reg["issuers"])
