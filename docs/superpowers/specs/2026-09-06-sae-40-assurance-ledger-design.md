# SAE-40 Judge Assurance Ledger Design

## Authority

This executor design implements the already frozen SAE-40 charter from `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md`. It does not reinterpret those documents.

Construction base: `2a1d16f9772997d993d0f0d41e1c5161f222f136`.

Frozen prerequisites:

- SAE-10 lifecycle is PROVEN and provides `QUALIFIED_REVIEW_WORLD_CONTRACT` and `QUALIFIED_RAB_CONTRACT` through `docs/81-sae10-proven-lifecycle-closeout-manifest.json`.
- SAE-20 lifecycle is PROVEN and provides `QUALIFIED_ACR_FOUNDATION` through `docs/85-sae20-proven-lifecycle-closeout-manifest.json`.

## Design decision

SAE-40 amplifies the existing Judge rather than creating a second Judge. The existing deterministic officer council remains responsible for claim adjudication and the existing Sergeant verdict path remains final automated engineering authority.

The implementation is split into two units:

1. `main_review/assurance_ledger.py` — authority-bearing immutable record identity, canonical persistence, monotonic merge, and ledger lineage.
2. `main_review/judge_assurance_adapter.py` — a one-way adapter that consumes the existing Judge `admission_ledger`, raw claims, assurance obligations, and existing verdict. It does not re-adjudicate or calculate a verdict.

No existing `officer_council.py`, Cpl, Judge, or verdict implementation is replaced.

## Authority-bearing record identity

Every `LedgerRecord` binds:

- record family;
- exact `review_world_id`;
- exact `rab_id`;
- exact `scope_id`;
- immutable record generation;
- explicit occurrence index for multiplicity;
- epistemic state, including `UNKNOWN` and `CONTRADICTED`;
- authority references;
- provenance references;
- related authority-record IDs;
- canonical JSON payload.

The full body is SHA-256 content-addressed as `record_id`.

Legacy `finding_id` values are presentation aliases only. They are deliberately excluded from `record_id`, so changing a UI/grouping alias cannot become positive proof authority. Presentation aliases are still included in the containing ledger payload and therefore alter `ledger_id`, preserving persisted presentation integrity.

## Supported founding record families

The core defines exactly these SAE-40 families:

- Review World;
- ACR evaluation;
- collection closure;
- contract instance;
- claim;
- obligation;
- assumption;
- evidence;
- falsifier instance;
- contradiction;
- qualification evidence;
- admission;
- invalidation;
- verdict lineage.

SAE-40 provides the identity/container substrate only. Later roadmap nodes remain responsible for their stronger family-specific semantic closure, qualification and proof rules.

## Monotonic Judge ledger

`JudgeAssuranceLedger` binds one exact Review World and RAB. It:

- sorts and content-addresses authority records canonically;
- retains different occurrences even when they share one presentation `finding_id`;
- retains both UNKNOWN and later positive/negative records rather than replacing one with the other;
- retains contradictions explicitly;
- rejects cross-Review-World or cross-RAB merge;
- requires an explicit new generation on merge rather than selecting `latest` or `current` authority;
- unions presentation aliases only when two records have the exact same authority body/`record_id`;
- rejects dangling `related_record_ids` so a persisted admission, contradiction, invalidation or lineage record cannot claim unseen authority by digest alone;
- carries parent ledger IDs across monotonic merge.

## Existing-Judge adapter

The adapter requires exactly one existing Judge report. It lifts:

- every raw source finding into a distinct claim occurrence;
- one existing canonical Judge disposition per legacy `finding_id`, linked to all contributing raw claims;
- required assurances into obligation records, with unresolved/advisory status conserved as `UNKNOWN`;
- the already-computed Sergeant/Cpl result into a verdict-lineage record.

It intentionally does not multiply one canonical Judge admission merely because multiple source claims share the same `finding_id`.

## Fail-closed boundaries

The implementation rejects:

- shortened or malformed authority hashes;
- scalar strings where an authority-reference collection is required;
- duplicate authority references;
- mutable authority aliases such as `latest`, `current`, `head`, `main`, or `master`;
- bool masquerading as an integer occurrence;
- non-canonical JSON or non-finite numeric payloads;
- tampered record or ledger IDs;
- non-canonical persisted ordering;
- cross-world/cross-RAB record membership or merge;
- missing/multiple existing Judge reports;
- malformed existing Judge disposition arrays;
- dangling authority-record links.

## Authority boundary

This candidate does not:

- change normal Sergeant verdict authority;
- create a second Judge;
- create SAE-30 qualification authority or EEPR independence;
- activate Genesis;
- qualify SAE-R1, SAE-50 or any dependent node;
- treat a legacy `finding_id` as positive proof identity;
- claim that all later semantic record families are already populated or closed.

`QUALIFIED_ASSURANCE_LEDGER` may exist only after SAE-40's separate reviewed/qualified/proven lifecycle closeout.
