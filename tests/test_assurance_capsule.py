from __future__ import annotations

import json
from pathlib import Path

import pytest

from main_review.assurance_capsule import (
    ADMISSIBLE,
    AssuranceCapsuleArchive,
    AssuranceCapsuleError,
    AssuranceCapsuleRecord,
    CollectionCommitment,
    InvalidationRecord,
    require_current_capsule,
)
from main_review.owner_risk import (
    BusinessRiskDecision,
    BusinessRiskDecisionRecord,
    EngineeringVerdict,
    EngineeringVerdictRecord,
)


def h(ch: str) -> str:
    return ch * 64


def verdict(world: str = h("a")) -> EngineeringVerdictRecord:
    return EngineeringVerdictRecord.create(
        review_world_id=world,
        evidence_root_id=h("b"),
        sergeant_authority_id=h("c"),
        verdict=EngineeringVerdict.PASS,
    )


def commitment(name: str, root: str, witness: str) -> CollectionCommitment:
    return CollectionCommitment.create(name=name, root_id=root, closure_witness_id=witness)


def capsule() -> AssuranceCapsuleRecord:
    return AssuranceCapsuleRecord.create(
        review_world_id=h("a"), rab_id=h("d"), acr_generation="acr-g1",
        scope_id=h("e"), domain_id=h("f"), contract_evaluation_root=h("1"),
        contract_instance=commitment("contract_instances", h("2"), h("3")),
        obligations=commitment("expected_obligations", h("4"), h("5")),
        ledger=commitment("judge_ledger", h("6"), h("7")),
        evidence=commitment("evidence", h("8"), h("9")),
        admitted_finding_ids=(h("0"),), unknown_ids=(h("a"),),
        qualification_generation="qualification-g1", facility_generation="facility-g1",
        rust_admissibility=ADMISSIBLE, engineering_verdict=verdict(),
        subject_generation="generation-g1", current_generation="generation-g1",
        provenance_root_id=h("b"), created_at_utc="2026-09-12T12:00:00Z",
    )


def test_capsule_is_content_addressed_and_commits_to_closure_witnesses():
    value = capsule()
    restored = AssuranceCapsuleRecord.from_payload(value.to_payload())
    assert restored == value
    assert restored.capsule_id == value.capsule_id
    with pytest.raises(AssuranceCapsuleError, match="closure witness"):
        CollectionCommitment.create(name="evidence", root_id=h("8"), closure_witness_id="")


def test_capsule_rejects_non_engineering_risk_authority():
    risk = BusinessRiskDecisionRecord.create(
        engineering_verdict_id=verdict().record_id, owner_authority_id=h("d"),
        decision=BusinessRiskDecision.ACCEPT, rationale="Business accepts release risk.",
    )
    with pytest.raises(AssuranceCapsuleError, match="engineering verdict"):
        AssuranceCapsuleRecord.create(
            review_world_id=h("a"), rab_id=h("d"), acr_generation="acr-g1",
            scope_id=h("e"), domain_id=h("f"), contract_evaluation_root=h("1"),
            contract_instance=commitment("contract_instances", h("2"), h("3")),
            obligations=commitment("expected_obligations", h("4"), h("5")),
            ledger=commitment("judge_ledger", h("6"), h("7")),
            evidence=commitment("evidence", h("8"), h("9")),
            admitted_finding_ids=(), unknown_ids=(), qualification_generation="qualification-g1",
            facility_generation="facility-g1", rust_admissibility=ADMISSIBLE,
            engineering_verdict=risk, subject_generation="generation-g1",
            current_generation="generation-g1", provenance_root_id=h("b"),
            created_at_utc="2026-09-12T12:00:00Z",
        )


def test_currentness_fails_closed_for_generation_scope_domain_and_invalidation():
    value = capsule()
    assert require_current_capsule(
        value, expected_generation="generation-g1", expected_scope_id=h("e"),
        expected_domain_id=h("f"), invalidations=(),
    ) == value
    for kwargs in (
        {"expected_generation": "generation-g2", "expected_scope_id": h("e"), "expected_domain_id": h("f")},
        {"expected_generation": "generation-g1", "expected_scope_id": h("9"), "expected_domain_id": h("f")},
        {"expected_generation": "generation-g1", "expected_scope_id": h("e"), "expected_domain_id": h("9")},
    ):
        with pytest.raises(AssuranceCapsuleError):
            require_current_capsule(value, invalidations=(), **kwargs)
    invalidation = InvalidationRecord.create(
        capsule_id=value.capsule_id, reason="provenance escape", provenance_escape_id=h("c"),
        invalidated_at_utc="2026-09-12T12:01:00Z",
    )
    with pytest.raises(AssuranceCapsuleError, match="invalidated"):
        require_current_capsule(
            value, expected_generation="generation-g1", expected_scope_id=h("e"),
            expected_domain_id=h("f"), invalidations=(invalidation,),
        )


def test_archive_recovers_only_exact_capsule_and_generation(tmp_path: Path):
    value = capsule()
    archive = AssuranceCapsuleArchive(tmp_path)
    archive.store(value)
    assert archive.recover_exact(value.capsule_id, expected_generation="generation-g1") == value
    with pytest.raises(AssuranceCapsuleError, match="generation"):
        archive.recover_exact(value.capsule_id, expected_generation="generation-g2")
    with pytest.raises(AssuranceCapsuleError, match="not found"):
        archive.recover_exact(h("f"), expected_generation="generation-g1")
    assert not hasattr(archive, "latest")
    assert not hasattr(archive, "recover_latest_compatible")


def test_archive_detects_tamper_and_replays_invalidation(tmp_path: Path):
    value = capsule()
    archive = AssuranceCapsuleArchive(tmp_path)
    archive.store(value)
    capsule_path = tmp_path / "capsules" / f"{value.capsule_id}.json"
    payload = json.loads(capsule_path.read_text())
    payload["facility_generation"] = "tampered"
    capsule_path.write_text(json.dumps(payload))
    with pytest.raises(AssuranceCapsuleError, match="identity"):
        archive.recover_exact(value.capsule_id, expected_generation="generation-g1")

    archive.store(value)
    record = archive.invalidate(
        value.capsule_id, reason="provenance escape", provenance_escape_id=h("c"),
        invalidated_at_utc="2026-09-12T12:01:00Z",
    )
    assert record.capsule_id == value.capsule_id
    with pytest.raises(AssuranceCapsuleError, match="invalidated"):
        archive.recover_current(
            value.capsule_id, expected_generation="generation-g1",
            expected_scope_id=h("e"), expected_domain_id=h("f"),
        )
