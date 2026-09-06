# SAE-20 ACR + Authoring Audit Design

Authority: canonical `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md` at construction base `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Boundary

SAE-20 defines the finite Assurance Contract Registry specification and an independent authoring-audit mechanism. It does not implement SAE-30 qualification issuance, Genesis activation, Judge ledger integration, total contract-instance closure, or normal verdict authority.

## Assurance Contract Registry

`main_review/assurance_contract_registry.py` owns immutable bounded-domain, contract, applicability and collection semantics. Applicability is three-valued and fail-closed: missing or unsupported runtime facts remain UNKNOWN; negative absence requires sufficient closure.

Contract payloads are strict and content-addressed. Expected JSON is recursively frozen, canonical-map validated, detached on serialization and compared with recursive type identity. Boolean/number aliases cannot change predicate truth. Authority-bearing iterables are materialized once so generators cannot be consumed and silently erased.

Cardinality identity is also type-strict. `ZERO_OR_ONE` and `EXACTLY_ONE` accept only integer maximum `1`, explicitly rejecting `True` and `1.0`; `BOUNDED_N` retains positive non-boolean integer validation. SET/MULTISET/ORDER, cardinality and closure distinctions remain explicit.

## Independent Authoring Audit

`main_review/acr_authoring_audit.py` owns an independently content-addressed audit profile requiring independent basis IDs. It binds exact contract ID/generation, exact bounded-domain hash, full applicability payload, bound subjects, proof classes, capabilities, requirement closure grades and all remaining SAE-20 authoring families.

Before its requirements are trusted, the profile must round-trip through canonical persistence with its hash intact. Tampered constructor-bypass profiles fail closed. Audit `CLEAN` never writes qualification state.

## Qualification escape

A real defect proving a qualified ACR omitted a mandatory family produces permanent qualification-escape evidence. Required disposition is suspension/revocation plus impact analysis; automatic corrected-contract promotion is forbidden.

## Proof boundary

SAE-20 proof must demonstrate canonical persistence/tamper rejection, bounded-domain and contract-generation identity, three-valued applicability, type-sensitive JSON and cardinality semantics, unsupported-value UNKNOWN conservation, one-shot collection preservation, complete authoring attacks, malformed-object fail-closed behavior, no self-qualification path and qualification-escape disposition.
