# SAE-50 — Total Coverage + Total Set-Valued Closure Core Candidate

Lifecycle: **CANDIDATE**.

Construction base: `535699dc5952f5309eaa843098b21457439af706`.

RED generation: `0877bcc59825c2a05a4bf7555f3e8c4d10744ae5` proved the closure core was genuinely absent: the repository suite retained its two historical XFAILs and failed only the eight new SAE-50 contract tests because `main_review.closure_core` did not exist.

First GREEN implementation generation: `c4d2a06b480768445410bad7fe6cb74d7e60468c`.

## Candidate contract

The candidate extends the already-PROVEN SAE-10 Review World/RAB, SAE-20 ACR and SAE-40 Assurance Ledger authority; it does not create a competing contract registry or Judge.

It establishes:

- externally rooted `ClosureBasis` identity rather than a self-declared universe;
- exact `SET`, `MULTISET`, and `ORDER` semantics inherited from the qualified ACR;
- source-basis and member-root binding;
- explicit `ClosureWitness` enumeration;
- EXACT completion only when an EXACT source basis and complete matching witness agree under the declared collection semantics;
- multiplicity preservation for MULTISET and order preservation for ORDER;
- `PROVEN_EMPTY` only as the empty case of an exact rooted basis plus complete witness;
- content-addressed `ClosureCertificate` invalidated by later basis/member/semantics changes;
- bounded affected-relation fixpoint computation whose resource exhaustion becomes `UNKNOWN` rather than incomplete PASS.

## Hostile properties already executable

The candidate test corpus proves that:

- a valid subset cannot become COMPLETE;
- a PARTIAL source basis cannot produce exact child closure;
- SET/MULTISET/ORDER cannot collapse into one another;
- multiplicity undercount cannot close a MULTISET;
- resource exhaustion conserves UNKNOWN;
- self-defining universes cannot provide positive closure authority;
- empty collections require exact rooted positive proof;
- late member discovery invalidates a prior certificate.

## Authority boundary

This document freezes a **candidate**, not `QUALIFIED_SET_VALUED_CLOSURE_CORE`.

No downstream node is auto-qualified or auto-proven. SAE-60, SAE-70, SAE-80 and SAE-R2 may not consume this candidate as PROVEN authority. A separate SAE-50 qualification campaign and lifecycle-closeout generation is required after guarded candidate merge.
