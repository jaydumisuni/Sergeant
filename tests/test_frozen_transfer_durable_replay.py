from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_frozen_transfer_replay import ALLOWED_REPLAY_DRIFT, validate_archive, validate_changed_paths


def test_auth7_archive_is_exact_and_intact():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evidence/frozen-transfer-replay/manifest.json").read_text())
    rec = manifest["sets"]["model-free-core-auth-transfer-7"]
    validate_archive(root, rec)
    assert rec["source_run_id"] == 34135754257
    assert rec["source_head"] == "8a25dbd69e9498b38c6f3f137e8140313a04a335"
    assert rec["fixture_repository"] == "jraversbcn21/PlayQAcademy"
    assert rec["fixture_fixing_ref"] == "90418d017ce04b41e643a044a52ead93c6fd03a0"


def test_await5_archive_is_exact_and_intact():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evidence/frozen-transfer-replay/manifest.json").read_text())
    rec = manifest["sets"]["model-free-core-await-transfer-5"]
    validate_archive(root, rec)
    assert rec["source_run_id"] == 34453497537
    assert rec["source_head"] == "6ad9b816f09fe26031305efa37548fbf701a9940"
    assert rec["fixture_repository"] == "shantanuchandra/cardcompass"
    assert rec["fixture_fixing_ref"] == "8941b53d4a016535c018540b4c1df0394614e061"


def test_replay_path_gate_rejects_review_engine_change():
    allowed = ["docs/", "main_review/proof_world.py", "tests/test_proof_world.py"]
    validate_changed_paths(["docs/x.md", "main_review/proof_world.py"], allowed)
    try:
        validate_changed_paths(["main_review/engine.py"], allowed)
    except ValueError as exc:
        assert "main_review/engine.py" in str(exc)
    else:
        raise AssertionError("review-engine drift must fail closed")


def test_replay_workflows_fetch_sergeant_history():
    root = Path(__file__).resolve().parents[1]
    for rel in [
        ".github/workflows/model-free-core-auth-transfer-7.yml",
        ".github/workflows/model-free-core-await-transfer-5.yml",
    ]:
        text = (root / rel).read_text()
        first_checkout = text.split("- name: Checkout frozen Sergeant reviewer", 1)[1].split("- name: Checkout candidate A fixing commit", 1)[0]
        assert "fetch-depth: 0" in first_checkout, f"{rel} must fetch source-success history for replay validation"


def test_replay_allows_proven_lifecycle_and_ci_ancestry_metadata_only():
    expected = [
        ".github/workflows/main-review.yml",
        "docs/112-sae80-proven-lifecycle-closeout.md",
        "docs/113-sae80-proven-lifecycle-closeout-manifest.json",
        "docs/114-sae90-falsification-frontier-candidate.md",
        "docs/115-sae90-falsification-frontier-candidate-manifest.json",
        "tests/test_main_review_workflow_merge_base.py",
        "tests/test_sae80_proven_lifecycle_closeout.py",
        "main_review/falsification_frontier_protocol.py",
        "tests/test_sae90_candidate_record_integrity.py",
        "tests/test_sae90_qualification_campaign.py",
        "docs/116-sae90-proven-lifecycle-closeout.md",
        "docs/117-sae90-proven-lifecycle-closeout-manifest.json",
        "tests/test_sae90_proven_lifecycle_closeout.py",
    ]
    validate_changed_paths(expected, ALLOWED_REPLAY_DRIFT)
    try:
        validate_changed_paths([".github/workflows/release.yml"], ALLOWED_REPLAY_DRIFT)
    except ValueError:
        pass
    else:
        raise AssertionError("unrelated workflow drift must remain forbidden")


def test_replay_allows_isolated_sae_r2_candidate_surface_only():
    expected = [
        ".github/workflows/sae-r2-rust-proof.yml",
        "docs/118-sae-r2-rust-assurance-kernel-candidate.md",
        "docs/119-sae-r2-rust-assurance-kernel-candidate-manifest.json",
        "main_review/rust_assurance_kernel.py",
        "rust/sergeant-assurance-kernel/Cargo.lock",
        "rust/sergeant-assurance-kernel/Cargo.toml",
        "rust/sergeant-assurance-kernel/src/lib.rs",
        "rust/sergeant-assurance-kernel/src/main.rs",
        "tests/test_sae_r2_kernel.py",
    ]
    validate_changed_paths(expected, ALLOWED_REPLAY_DRIFT)
    try:
        validate_changed_paths(["main_review/engine.py"], ALLOWED_REPLAY_DRIFT)
    except ValueError:
        pass
    else:
        raise AssertionError("existing review-engine drift must remain forbidden")


def test_replay_allows_post_sae_r2_and_sae100_authority_surfaces_without_broadening():
    expected = [
        "docs/120-sae-r2-proven-lifecycle-closeout.md",
        "docs/121-sae-r2-proven-lifecycle-closeout-manifest.json",
        "tests/test_sae_r2_proven_lifecycle_closeout.py",
        "tests/test_sae_r2_qualification_campaign.py",
        "docs/122-sae100-sergeant-integration-candidate.md",
        "docs/123-sae100-sergeant-integration-candidate-manifest.json",
        "docs/126-sae100-task17-frozen-predecessor-authority-amendment.md",
        "docs/127-sae100-task17-frozen-predecessor-authority-amendment-manifest.json",
        "main_review/assurance_integration.py",
        "main_review/cpl_campaign.py",
        "tests/test_assurance_integration.py",
        "tests/test_sae100_post_amendment_candidate.py",
        "tests/test_sae100_task17_authority_amendment_record.py",
    ]
    validate_changed_paths(expected, ALLOWED_REPLAY_DRIFT)
    for forbidden in [
        "main_review/engine.py",
        "main_review/officer_council.py",
        "main_review/judge_assurance_adapter.py",
        "main_review/final_proof.py",
        ".github/workflows/release.yml",
    ]:
        try:
            validate_changed_paths([forbidden], ALLOWED_REPLAY_DRIFT)
        except ValueError:
            continue
        raise AssertionError(f"unrelated or frozen predecessor drift must remain forbidden: {forbidden}")


def test_replay_allows_sae100_qualification_repair_test_without_broadening():
    validate_changed_paths(["tests/test_sae100_qualified_dependency_consumption.py"], ALLOWED_REPLAY_DRIFT)
    for forbidden in [
        "tests/test_unrelated_review_engine_rewrite.py",
        "main_review/officer_council.py",
        "main_review/judge_assurance_adapter.py",
        "main_review/final_proof.py",
    ]:
        try:
            validate_changed_paths([forbidden], ALLOWED_REPLAY_DRIFT)
        except ValueError:
            continue
        raise AssertionError(f"qualification replay repair must not broaden frozen drift: {forbidden}")


def test_replay_classifies_proof_metadata_generically_without_opening_frozen_review_engine():
    neutral = [
        "docs/124-sae100-proven-lifecycle-closeout.md",
        "docs/125-sae100-proven-lifecycle-closeout-manifest.json",
        "docs/128-sae110-assurance-capsule-candidate.md",
        "docs/129-sae110-assurance-capsule-candidate-manifest.json",
        "docs/superpowers/plans/2026-09-12-sae-110-assurance-capsule.md",
        "tests/test_sae100_proven_lifecycle_closeout.py",
        "tests/test_sae100_qualification_campaign.py",
        "tests/test_assurance_capsule.py",
        "main_review/assurance_capsule.py",
    ]
    validate_changed_paths(neutral, ALLOWED_REPLAY_DRIFT)
    for forbidden in [
        "main_review/engine.py",
        "main_review/officer_council.py",
        "main_review/judge_assurance_adapter.py",
        "main_review/final_proof.py",
        ".github/workflows/release.yml",
    ]:
        with __import__("pytest").raises(ValueError):
            validate_changed_paths([forbidden], ALLOWED_REPLAY_DRIFT)
