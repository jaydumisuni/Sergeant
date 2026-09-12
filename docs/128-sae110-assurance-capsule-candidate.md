# SAE-110 — Assurance Capsule / Recovery / Currentness / Owner Risk

Status: **CANDIDATE**

Canonical construction base: `73541e17e8ef7c208d2bfa91012695b6917e549b` — the guarded merge of SAE-100 PROVEN lifecycle closeout PR #228.

## Dependency authority

SAE-110 consumes the already-PROVEN SAE-10, SAE-30, SAE-40 and SAE-R2 authority generations carried by canonical main. SAE-100 is also PROVEN on the construction base, but is not a Task 19 proof dependency. No predecessor file is modified by this candidate.

## Candidate construction

`main_review/assurance_capsule.py` introduces a successor-only durable assurance surface:

- content-addressed `AssuranceCapsuleRecord`;
- explicit Review World, RAB, ACR generation, scope/domain, contract-evaluation root, Judge ledger, evidence, admitted findings/UNKNOWNs, qualification/facility generations, Rust admissibility, Sergeant engineering-verdict identity, provenance and temporal/currentness coordinates;
- `CollectionCommitment` values that bind each authority-bearing collection root to its closure-witness root;
- fail-closed scope/domain/generation currentness;
- append-only provenance-escape `InvalidationRecord`;
- Archivist-facing content-addressed durable archive and exact-ID/exact-generation replay;
- deliberately **no latest-compatible recovery API**;
- continued structural separation of `EngineeringVerdictRecord` from `BusinessRiskDecisionRecord`.

Historical records remain recoverable by exact identity. They do not become current merely because they once carried PASS. Invalidated, stale, wrong-scope or wrong-domain capsules fail currentness. Owner business-risk acceptance cannot substitute for an engineering verdict or become capsule evidence.

## Hostile qualification slice

`tests/test_assurance_capsule.py` proves:

1. collection member roots without closure witnesses cannot form an authority-bearing commitment;
2. capsule identity is canonical and detects payload mutation;
3. Owner risk records are rejected as engineering-verdict authority;
4. stale generation, wrong scope, wrong domain and provenance invalidation fail closed;
5. zero-context durable recovery requires the exact capsule ID and exact generation;
6. no latest-compatible recovery surface exists;
7. disk tampering is detected before replay; and
8. invalidation survives durable replay and blocks current rendering.

## Authority boundary

This is candidate construction only. It does not activate Genesis, alter normal Sergeant verdict semantics, rewrite a frozen predecessor, auto-prove SAE-120, or manufacture PROVEN authority from worker evidence. Candidate merge, if later authorized, grants no authority by itself; SAE-110 requires its own separate PROVEN lifecycle closeout.
