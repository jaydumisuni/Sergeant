from __future__ import annotations

import copy

import pytest

from main_review.assurance_ledger import (
    AssuranceLedgerError,
    JudgeAssuranceLedger,
    LedgerEpistemicState,
    LedgerRecord,
    LedgerRecordKind,
)
from main_review.judge_assurance_adapter import build_judge_assurance_ledger


H = lambda ch: ch * 64
WORLD = H("a")
RAB = H("b")
SCOPE = H("c")
AUTH = H("d")
PROV = H("e")


def record(
    *,
    kind: LedgerRecordKind = LedgerRecordKind.CLAIM,
    state: LedgerEpistemicState = LedgerEpistemicState.ASSERTED,
    occurrence: int = 0,
    world: str = WORLD,
    rab: str = RAB,
    scope: str = SCOPE,
    payload: dict[str, object] | None = None,
    aliases: tuple[str, ...] = (),
    related: tuple[str, ...] = (),
) -> LedgerRecord:
    return LedgerRecord.create(
        kind=kind,
        review_world_id=world,
        rab_id=rab,
        scope_id=scope,
        generation="sae40-qualification-record-v1",
        occurrence=occurrence,
        epistemic_state=state,
        authority_refs=(AUTH,),
        provenance_refs=(PROV,),
        related_record_ids=related,
        payload=payload or {"claim": "same semantic proposition"},
        presentation_ids=aliases,
    )


def ledger(*records: LedgerRecord, world: str = WORLD, rab: str = RAB, generation: str = "sae40-qualification-ledger-v1") -> JudgeAssuranceLedger:
    return JudgeAssuranceLedger.create(
        review_world_id=world,
        rab_id=rab,
        generation=generation,
        records=records,
    )


def test_qualification_presentation_aliases_cannot_become_claim_authority() -> None:
    first = record(aliases=("finding-z",))
    renamed = record(aliases=("finding-a",))
    assert first.record_id == renamed.record_id
    assert first.authority_payload() == renamed.authority_payload()
    merged = ledger(first, renamed)
    assert len(merged.records) == 1
    assert merged.records[0].presentation_ids == ("finding-a", "finding-z")


def test_qualification_repeated_claim_and_admission_occurrences_cannot_collapse() -> None:
    claim0 = record(occurrence=0, aliases=("same",))
    claim1 = record(occurrence=1, aliases=("same",))
    admission0 = record(
        kind=LedgerRecordKind.ADMISSION,
        occurrence=0,
        payload={"disposition": "admitted"},
        related=(claim0.record_id,),
    )
    admission1 = record(
        kind=LedgerRecordKind.ADMISSION,
        occurrence=1,
        payload={"disposition": "admitted"},
        related=(claim1.record_id,),
    )
    qualified = ledger(claim0, claim1, admission0, admission1)
    assert len([r for r in qualified.records if r.kind is LedgerRecordKind.CLAIM]) == 2
    admissions = [r for r in qualified.records if r.kind is LedgerRecordKind.ADMISSION]
    assert len(admissions) == 2
    assert {r.occurrence for r in admissions} == {0, 1}
    assert len({r.record_id for r in admissions}) == 2


def test_qualification_unknown_and_contradiction_survive_monotonic_merge() -> None:
    unknown = record(state=LedgerEpistemicState.UNKNOWN, occurrence=0)
    yes = record(state=LedgerEpistemicState.TRUE, occurrence=1)
    no = record(state=LedgerEpistemicState.FALSE, occurrence=2)
    contradiction = record(
        kind=LedgerRecordKind.CONTRADICTION,
        state=LedgerEpistemicState.CONTRADICTED,
        occurrence=3,
        payload={"reason": "qualified hostile conflict"},
        related=(yes.record_id, no.record_id),
    )
    left = ledger(unknown, generation="sae40-qualification-left-v1")
    right = ledger(yes, no, contradiction, generation="sae40-qualification-right-v1")
    merged = left.merge(right, generation="sae40-qualification-merged-v2")
    states = {r.epistemic_state for r in merged.records}
    assert LedgerEpistemicState.UNKNOWN in states
    assert LedgerEpistemicState.CONTRADICTED in states
    assert {unknown.record_id, yes.record_id, no.record_id, contradiction.record_id}.issubset(
        {r.record_id for r in merged.records}
    )
    assert {left.ledger_id, right.ledger_id}.issubset(set(merged.parent_ledger_ids))


def test_qualification_world_rab_and_scope_substitution_remain_authority_bearing() -> None:
    base = record()
    changed_world = record(world=H("f"))
    changed_rab = record(rab=H("1"))
    changed_scope = record(scope=H("2"))
    assert len({base.record_id, changed_world.record_id, changed_rab.record_id, changed_scope.record_id}) == 4

    canonical = ledger(base, generation="canonical-v1")
    with pytest.raises(AssuranceLedgerError):
        canonical.merge(ledger(changed_world, world=H("f"), generation="other-world-v1"), generation="merged-v2")
    with pytest.raises(AssuranceLedgerError):
        canonical.merge(ledger(changed_rab, rab=H("1"), generation="other-rab-v1"), generation="merged-v2")


def test_qualification_persisted_order_identity_and_links_fail_closed_under_tamper() -> None:
    first = record(occurrence=0)
    second = record(occurrence=1)
    original = ledger(first, second)
    persisted = original.to_payload()
    assert JudgeAssuranceLedger.from_payload(persisted) == original

    reversed_records = copy.deepcopy(persisted)
    reversed_records["records"].reverse()
    with pytest.raises(AssuranceLedgerError):
        JudgeAssuranceLedger.from_payload(reversed_records)

    forged_id = copy.deepcopy(persisted)
    forged_id["ledger_id"] = H("9")
    with pytest.raises(AssuranceLedgerError):
        JudgeAssuranceLedger.from_payload(forged_id)

    dangling = record(kind=LedgerRecordKind.ADMISSION, occurrence=2, related=(H("9"),))
    with pytest.raises(AssuranceLedgerError):
        ledger(first, dangling)


def test_qualification_malformed_authority_inputs_fail_closed() -> None:
    fields = record().constructor_fields()
    with pytest.raises(AssuranceLedgerError):
        LedgerRecord.create(**{**fields, "occurrence": True})
    with pytest.raises(AssuranceLedgerError):
        LedgerRecord.create(**{**fields, "generation": "latest"})
    with pytest.raises(AssuranceLedgerError):
        LedgerRecord.create(**{**fields, "authority_refs": ("presentation-id",)})


def _council(first_id: str, second_id: str) -> dict[str, object]:
    return {
        "raw_findings": [
            {
                "finding_id": first_id,
                "source": "repository",
                "message": "first hostile claim",
                "severity": "major",
                "path": "a.py",
                "line_start": 1,
            },
            {
                "finding_id": second_id,
                "source": "offline-officer",
                "message": "second hostile claim",
                "severity": "major",
                "path": "b.py",
                "line_start": 2,
            },
        ],
        "required_assurances": [],
        "reports": [
            {
                "officer": "Judge",
                "admission_ledger": {
                    "admitted": [first_id, second_id],
                    "advisory": [],
                    "rejected": [],
                },
            }
        ],
        "verdict": "NEEDS WORK",
    }


def test_qualification_adapter_alias_rename_cannot_reorder_admission_authority() -> None:
    first = build_judge_assurance_ledger(
        review_world_id=WORLD,
        rab_id=RAB,
        scope_id=SCOPE,
        generation="qualification-adapter-v1",
        council=_council("finding-a", "finding-z"),
    )
    renamed = build_judge_assurance_ledger(
        review_world_id=WORLD,
        rab_id=RAB,
        scope_id=SCOPE,
        generation="qualification-adapter-v1",
        council=_council("finding-z", "finding-a"),
    )

    def admission_map(value: JudgeAssuranceLedger) -> dict[str, str]:
        return {
            item.related_record_ids[0]: item.record_id
            for item in value.records
            if item.kind is LedgerRecordKind.ADMISSION
        }

    assert admission_map(first) == admission_map(renamed)


def test_qualification_adapter_excludes_judge_only_metadata_from_raw_claim_authority() -> None:
    def build(admission: str, gates: bool) -> LedgerRecord:
        council = {
            "raw_findings": [
                {
                    "finding_id": "finding-a",
                    "source": "repository",
                    "message": "same raw claim",
                    "severity": "major",
                    "path": "a.py",
                    "line_start": 3,
                    "admission": admission,
                    "gates_verdict": gates,
                }
            ],
            "required_assurances": [],
            "reports": [
                {
                    "officer": "Judge",
                    "admission_ledger": {"admitted": ["finding-a"], "advisory": [], "rejected": []},
                }
            ],
            "verdict": "NEEDS WORK",
        }
        result = build_judge_assurance_ledger(
            review_world_id=WORLD,
            rab_id=RAB,
            scope_id=SCOPE,
            generation="qualification-adapter-v1",
            council=council,
        )
        return next(r for r in result.records if r.kind is LedgerRecordKind.CLAIM)

    actionable = build("actionable", True)
    duplicate = build("duplicate", False)
    assert actionable.record_id == duplicate.record_id
    assert "admission" not in actionable.payload()
    assert "gates_verdict" not in actionable.payload()


def test_qualification_adapter_rejects_orphan_and_noncanonical_assurance_authority() -> None:
    orphan = {
        "raw_findings": [],
        "required_assurances": [],
        "reports": [
            {
                "officer": "Judge",
                "admission_ledger": {"admitted": ["finding-orphan"], "advisory": [], "rejected": []},
            }
        ],
        "verdict": "PASS",
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(
            review_world_id=WORLD,
            rab_id=RAB,
            scope_id=SCOPE,
            generation="qualification-adapter-v1",
            council=orphan,
        )

    mismatch = {
        "raw_findings": [],
        "required_assurances": [
            {
                "assurance_id": "assure-1",
                "status": "satisfied",
                "gates_verdict": True,
                "required_assurance": "coverage",
            }
        ],
        "reports": [
            {
                "officer": "Judge",
                "admission_ledger": {"admitted": [], "advisory": [], "rejected": []},
            }
        ],
        "verdict": "PASS",
    }
    with pytest.raises(AssuranceLedgerError):
        build_judge_assurance_ledger(
            review_world_id=WORLD,
            rab_id=RAB,
            scope_id=SCOPE,
            generation="qualification-adapter-v1",
            council=mismatch,
        )
