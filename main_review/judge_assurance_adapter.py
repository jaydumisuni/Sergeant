"""SAE-40 adapter from Sergeant's existing Judge packet to the assurance ledger.

This module consumes the existing officer-council Judge disposition.  It never
re-adjudicates findings and never computes a Sergeant verdict.
"""
from __future__ import annotations

from collections.abc import Mapping

from .assurance_ledger import (
    AssuranceLedgerError,
    JudgeAssuranceLedger,
    LedgerEpistemicState,
    LedgerRecord,
    LedgerRecordKind,
    _generation,
    _sha,
    _string,
)


_JUDGE_DISPOSITION_STATES = ("admitted", "advisory", "rejected")
_JUDGE_DISPOSITION_KEYS = frozenset(_JUDGE_DISPOSITION_STATES)
_ASSURANCE_STATES = {
    "satisfied": LedgerEpistemicState.TRUE,
    "unresolved": LedgerEpistemicState.UNKNOWN,
    "advisory": LedgerEpistemicState.UNKNOWN,
}


def _judge_dispositions(council: Mapping[str, object]) -> dict[str, str]:
    reports = council.get("reports")
    if not isinstance(reports, list):
        raise AssuranceLedgerError("existing officer council packet has no reports array")
    judges = [item for item in reports if isinstance(item, Mapping) and item.get("officer") == "Judge"]
    if len(judges) != 1:
        raise AssuranceLedgerError("existing officer council packet must contain exactly one Judge report")
    admission_ledger = judges[0].get("admission_ledger")
    if not isinstance(admission_ledger, Mapping):
        raise AssuranceLedgerError("existing Judge report has no admission_ledger")
    if set(admission_ledger) != _JUDGE_DISPOSITION_KEYS:
        raise AssuranceLedgerError(
            "existing Judge admission_ledger must contain exactly admitted / advisory / rejected"
        )
    dispositions: dict[str, str] = {}
    for state in _JUDGE_DISPOSITION_STATES:
        values = admission_ledger.get(state)
        if not isinstance(values, list):
            raise AssuranceLedgerError(f"Judge admission_ledger.{state} must be an array")
        for value in values:
            finding_id = _string(value, "Judge finding_id")
            previous = dispositions.get(finding_id)
            if previous is not None:
                raise AssuranceLedgerError(
                    f"Judge finding {finding_id!r} appears more than once in the admission ledger"
                )
            dispositions[finding_id] = state
    return dispositions


def _epistemic_for_assurance(assurance: Mapping[str, object]) -> LedgerEpistemicState:
    status = assurance.get("status")
    if not isinstance(status, str) or status not in _ASSURANCE_STATES:
        raise AssuranceLedgerError(
            "required assurance status must be satisfied / unresolved / advisory"
        )
    return _ASSURANCE_STATES[status]


def build_judge_assurance_ledger(
    *,
    review_world_id: str,
    rab_id: str,
    scope_id: str,
    generation: str,
    council: Mapping[str, object],
) -> JudgeAssuranceLedger:
    """Lift the existing Judge packet into SAE-40 authority records.

    Raw source claims retain occurrence identity.  Canonical Judge disposition
    remains one admission per legacy ``finding_id`` and links every contributing
    raw claim, so source multiplicity is preserved without multiplying Judge
    authority.
    """
    world = _sha(review_world_id, "review_world_id")
    rab = _sha(rab_id, "rab_id")
    scope = _sha(scope_id, "scope_id")
    generation = _generation(generation, "ledger generation")
    if not isinstance(council, Mapping):
        raise AssuranceLedgerError("council must be an object")
    dispositions = _judge_dispositions(council)
    raw = council.get("raw_findings")
    if not isinstance(raw, list):
        raise AssuranceLedgerError("existing officer council packet has no raw_findings array")

    records: list[LedgerRecord] = []
    claim_by_occurrence: list[tuple[LedgerRecord, str]] = []
    record_generation = f"{generation}.record"
    for index, finding in enumerate(raw):
        if not isinstance(finding, Mapping):
            raise AssuranceLedgerError("raw_findings contains a non-object entry")
        finding_id = _string(finding.get("finding_id"), "finding_id")
        finding_payload = {key: value for key, value in finding.items() if key != "finding_id"}
        claim = LedgerRecord.create(
            kind=LedgerRecordKind.CLAIM,
            review_world_id=world,
            rab_id=rab,
            scope_id=scope,
            generation=record_generation,
            occurrence=index,
            epistemic_state=LedgerEpistemicState.ASSERTED,
            payload=finding_payload,
            presentation_ids=(finding_id,),
        )
        records.append(claim)
        claim_by_occurrence.append((claim, finding_id))

    claims_by_finding: dict[str, list[LedgerRecord]] = {}
    for claim, finding_id in claim_by_occurrence:
        claims_by_finding.setdefault(finding_id, []).append(claim)

    raw_ids = set(claims_by_finding)
    disposition_ids = set(dispositions)
    orphaned_dispositions = disposition_ids - raw_ids
    if orphaned_dispositions:
        raise AssuranceLedgerError(
            "Judge admission ledger references findings absent from raw_findings: "
            f"{sorted(orphaned_dispositions)!r}"
        )
    missing_dispositions = raw_ids - disposition_ids
    if missing_dispositions:
        raise AssuranceLedgerError(
            "raw_findings contain findings absent from the canonical Judge admission ledger: "
            f"{sorted(missing_dispositions)!r}"
        )

    admission_occurrence = 0
    for finding_id in sorted(claims_by_finding):
        related_claims = claims_by_finding[finding_id]
        disposition = dispositions[finding_id]
        records.append(LedgerRecord.create(
            kind=LedgerRecordKind.ADMISSION,
            review_world_id=world,
            rab_id=rab,
            scope_id=scope,
            generation=record_generation,
            occurrence=admission_occurrence,
            epistemic_state=LedgerEpistemicState.ASSERTED,
            related_record_ids=tuple(claim.record_id for claim in related_claims),
            payload={"disposition": disposition},
            presentation_ids=(finding_id,),
        ))
        admission_occurrence += 1

    assurances = council.get("required_assurances")
    if not isinstance(assurances, list):
        raise AssuranceLedgerError("required_assurances must be an array")
    for index, assurance in enumerate(assurances):
        if not isinstance(assurance, Mapping):
            raise AssuranceLedgerError("required_assurances contains a non-object entry")
        assurance_id = assurance.get("assurance_id")
        aliases = () if assurance_id is None else (_string(assurance_id, "assurance_id"),)
        _string(assurance.get("required_assurance"), "required_assurance")
        if not isinstance(assurance.get("gates_verdict"), bool):
            raise AssuranceLedgerError("required assurance gates_verdict must be a boolean")
        records.append(LedgerRecord.create(
            kind=LedgerRecordKind.OBLIGATION,
            review_world_id=world,
            rab_id=rab,
            scope_id=scope,
            generation=record_generation,
            occurrence=index,
            epistemic_state=_epistemic_for_assurance(assurance),
            payload=dict(assurance),
            presentation_ids=aliases,
        ))

    verdict = council.get("verdict")
    if not isinstance(verdict, str) or verdict not in {"PASS", "NEEDS WORK", "BLOCK"}:
        raise AssuranceLedgerError("existing officer council verdict must be PASS / NEEDS WORK / BLOCK")
    records.append(LedgerRecord.create(
        kind=LedgerRecordKind.VERDICT_LINEAGE,
        review_world_id=world,
        rab_id=rab,
        scope_id=scope,
        generation=record_generation,
        occurrence=0,
        epistemic_state=LedgerEpistemicState.ASSERTED,
        related_record_ids=tuple(record.record_id for record in records),
        payload={"verdict": verdict, "authority": "existing-sergeant-judge-and-verdict-path"},
    ))

    return JudgeAssuranceLedger.create(
        review_world_id=world,
        rab_id=rab,
        generation=generation,
        records=records,
    )
