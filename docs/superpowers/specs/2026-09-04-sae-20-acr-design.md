# SAE-20 ACR + Authoring Audit Design

Authority: canonical `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md` at construction base `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Boundary

SAE-20 defines the finite Assurance Contract Registry specification and an independent authoring-audit mechanism. It does not implement SAE-30 qualification issuance, Genesis activation, Judge ledger integration, total contract-instance closure, or normal verdict authority.

## Assurance Contract Registry

`main_review/assurance_contract_registry.py` owns immutable bounded-domain, contract, applicability and collection semantics. Applicability is three-valued and fail-closed: missing facts remain UNKNOWN; unsupported present runtime fact values also become UNKNOWN; negative absence requires sufficient closure.

Contract payloads are strict and content-addressed. Applicability expected JSON is recursively frozen, validated for canonical map ordering/uniqueness, detached on serialization, and compared recursively with type identity. Thus boolean/number aliases, malformed frozen maps, mutable payload aliases, and unsupported runtime objects cannot silently alter content-addressed semantics.

SET/MULTISET/ORDER, cardinality and closure distinctions remain explicit. Authority-bearing iterables are materialized once before validation/sorting, preventing one-shot iterators from being consumed and erased.

## Independent Authoring Audit

`main_review/acr_authoring_audit.py` owns an independently content-addressed audit profile. The profile cannot define its basis from the candidate contract itself; it requires independent basis IDs.

The profile binds exact contract ID and **contract generation**, exact bounded-domain hash, full applicability predicate payload, bound subjects, proof classes, capabilities, requirement closure grades and all remaining SAE-20 authoring families. Before any requirements are trusted, the profile must round-trip through its canonical persistence contract with its hash intact. Tampered constructor-bypass profiles fail closed.

Audit comparison is fail-closed. `CLEAN` never writes qualification state.

## Qualification escape

A later real-world defect proving a qualified ACR omitted a mandatory family produces a content-addressed permanent qualification-escape record. Required disposition is suspension/revocation plus impact analysis. Automatic corrected-contract promotion is forbidden.

## Proof boundary

SAE-20 proof must demonstrate canonical persistence/tamper rejection, bounded-domain and contract-generation identity, three-valued applicability, type-sensitive JSON semantics, unsupported-value UNKNOWN conservation, one-shot collection preservation, complete authoring attacks, malformed-object fail-closed behavior, no self-qualification path and qualification-escape disposition.
