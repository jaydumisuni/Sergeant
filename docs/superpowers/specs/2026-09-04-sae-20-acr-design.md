# SAE-20 ACR + Authoring Audit Design

Authority: canonical `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md` at construction base `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Boundary

SAE-20 defines the finite Assurance Contract Registry specification and an independent authoring-audit mechanism. It does not implement SAE-30 qualification issuance, Genesis activation, Judge ledger integration, total contract-instance closure, or normal verdict authority.

## Assurance Contract Registry

`main_review/assurance_contract_registry.py` owns immutable bounded-domain, contract, applicability and collection semantics. Its applicability algebra is three-valued and fail-closed: missing facts remain UNKNOWN; negative absence requires sufficient closure. Contract payloads are strict and content-addressed. JSON applicability values are recursively frozen at construction and detached on serialization, so an external mutable object cannot alter later evaluation while preserving an earlier contract/registry ID.

The registry preserves SET/MULTISET/ORDER, cardinality and closure distinctions, mandatory-v1 status, explicit premise/obligation/material-input closures, and missing-evaluation UNKNOWN.

## Independent Authoring Audit

`main_review/acr_authoring_audit.py` owns an independently content-addressed audit profile. The profile cannot define its basis from the candidate contract itself; it requires independent basis IDs.

The profile binds the **exact bounded-domain hash** and the **exact applicability predicate payload**, plus exact bound-subject variables, admissible proof classes and permitted capabilities. It preserves expected closure grades for premise, obligation and material-input families rather than collapsing them to names. It also binds the remaining architecture families: semantic carriers, consumer interpretation, affected relations, collection/cardinality/closure, repeated authority premises, coherence, temporal validity, falsifiers, independence and external-review-lane cardinality.

Audit comparison is fail-closed. A constructor-bypass object that cannot round-trip through the canonical ACR persistence contract is deficient. Negative-applicability burden must itself validate as canonical `PROVEN_NO_MATCH` with sufficient closure. `CLEAN` never writes qualification state.

## Qualification escape

A later real-world defect proving a qualified ACR omitted a mandatory family produces a content-addressed permanent qualification-escape record. The required disposition is suspension/revocation plus impact analysis. Automatic corrected-contract promotion is forbidden.

## Proof boundary

SAE-20 proof must demonstrate canonical persistence/tamper rejection, bounded-domain identity, semantic/cardinality distinctions, UNKNOWN conservation, mutable-value detachment, no self-qualification path, complete authoring attacks including semantic/operator and closure-grade weakening, malformed-object fail-closed behavior, and qualification-escape disposition.
