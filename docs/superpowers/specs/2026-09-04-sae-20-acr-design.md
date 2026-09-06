# SAE-20 ACR + Authoring Audit Design

Authority: canonical `docs/58-sergeant-assurance-evolution-founding-architecture.md` and `docs/59-sergeant-assurance-evolution-roadmap.md` at main `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Boundary

SAE-20 defines the finite Assurance Contract Registry specification and an independent authoring-audit mechanism. It does not implement SAE-30 qualification issuance, Genesis activation, Judge ledger integration, total contract-instance closure, or normal verdict authority.

## Components

1. `main_review/assurance_contract_registry.py`
   - immutable bounded domains;
   - declarative three-valued applicability AST;
   - exact UNKNOWN conservation and PROVEN_NO_MATCH burden;
   - SET/MULTISET/ORDER collection semantics;
   - cardinality and closure-grade requirements;
   - premise, obligation, material-input, coherence, temporal, falsifier, independence and external-review-lane declarations;
   - canonical content-addressed contract and registry identity;
   - no contract-writable QUALIFIED state.

2. `main_review/acr_authoring_audit.py`
   - independently content-addressed audit profile with independent basis IDs;
   - exact bounded-domain identity and independently expected applicability AST are part of audit scope;
   - premise, obligation and material-input audit requirements preserve closure grades;
   - omission/weakening checks are against the profile, not the candidate's self-declared universe;
   - direct/noncanonical authority objects fail closed before semantic audit;
   - mutable authority-generation aliases cannot produce an authoring-clean result;
   - explicit attacks cover applicability omission and semantic weakening, cardinality/collection semantics, closure grades, material inputs, falsifier families and external-review-lane cardinality;
   - CLEAN means only structurally eligible for later independent qualification;
   - qualification escapes require suspension/revocation disposition and impact analysis, never automatic corrected-contract promotion.

## Fail-closed law

Missing applicability facts are UNKNOWN, not FALSE. A negative/absence predicate may become TRUE only under sufficient closure. Unsupported domains fall back to UNKNOWN. Any missing active mandatory evaluation remains UNKNOWN at later SAE-70 integration.

An audit profile is itself authority-bearing input: its content hash, exact bounded domain, exact expected applicability semantics and closure-bearing requirement declarations must survive canonical round-trip validation before the audit may return CLEAN.

## Proof boundary

SAE-20 proof must demonstrate canonical persistence/tamper rejection, bounded domains, semantic/cardinality distinctions, UNKNOWN conservation, no self-qualification path, all mandatory authoring attacks, closure-grade weakening resistance outside collections, exact audit-scope binding, applicability semantic weakening resistance, noncanonical-object fail-closed behavior and qualification-escape disposition.

Internal project-controlled hostile review remains `NOT_INDEPENDENT`; it can correct the candidate but cannot satisfy the founding architecture's mandatory independent qualification campaign.
