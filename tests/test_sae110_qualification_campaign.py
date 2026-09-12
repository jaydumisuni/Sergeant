from __future__ import annotations

from pathlib import Path
import json

import pytest

from main_review.assurance_capsule import AssuranceCapsuleArchive, AssuranceCapsuleError, InvalidationRecord, require_current_capsule
from tests.test_assurance_capsule import capsule, h

ROOT = Path(__file__).resolve().parents[1]


def test_sae110_required_candidate_inventory_is_present_and_manifested():
    manifest = json.loads((ROOT / "docs/129-sae110-assurance-capsule-candidate-manifest.json").read_text())
    for rel in manifest["required_surfaces"]:
        assert (ROOT / rel).is_file(), rel
    assert manifest["protocol"]["exact_generation_recovery"] is True
    assert manifest["protocol"]["latest_compatible_recovery_forbidden"] is True
    assert manifest["protocol"]["owner_risk_disjoint_from_engineering_truth"] is True


def test_sae110_zero_context_recovery_is_exact_and_tamper_evident(tmp_path: Path):
    value = capsule()
    archive = AssuranceCapsuleArchive(tmp_path)
    archive.store(value)
    recovered = AssuranceCapsuleArchive(tmp_path).recover_exact(value.capsule_id, expected_generation=value.subject_generation)
    assert recovered == value
    assert not hasattr(archive, "latest")
    assert not hasattr(archive, "recover_latest_compatible")


def test_sae110_stale_or_wrong_world_cannot_render_current():
    value = capsule()
    with pytest.raises(AssuranceCapsuleError):
        require_current_capsule(value, expected_generation="new-generation", expected_scope_id=value.scope_id,
                                expected_domain_id=value.domain_id, invalidations=())
    with pytest.raises(AssuranceCapsuleError):
        require_current_capsule(value, expected_generation=value.subject_generation, expected_scope_id=h("9"),
                                expected_domain_id=value.domain_id, invalidations=())


def test_sae110_provenance_escape_invalidates_current_rendering():
    value = capsule()
    invalidation = InvalidationRecord.create(capsule_id=value.capsule_id, reason="provenance escape",
                                             provenance_escape_id=h("c"), invalidated_at_utc="2026-09-12T12:01:00Z")
    with pytest.raises(AssuranceCapsuleError, match="invalidated"):
        require_current_capsule(value, expected_generation=value.subject_generation,
                                expected_scope_id=value.scope_id, expected_domain_id=value.domain_id,
                                invalidations=(invalidation,))
