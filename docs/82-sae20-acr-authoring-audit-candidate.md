# SAE-20 — Assurance Contract Registry + Authoring Audit candidate

Date: 2026-09-06

Status: **CANDIDATE**.

Construction base: canonical Sergeant `main` at `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Authority

This candidate implements the SAE-20 foundation defined by:

- `docs/58-sergeant-assurance-evolution-founding-architecture.md`;
- `docs/59-sergeant-assurance-evolution-roadmap.md`;
- PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY` from `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.

SAE-20 has one proof dependency: SAE-00. SAE-10 is already PROVEN but is not fabricated as a proof dependency for SAE-20.

## Candidate foundation

`main_review/assurance_contract_registry.py` defines finite bounded domains, immutable content-addressed contract/registry identity, declarative `TRUE / FALSE / UNKNOWN` applicability, `PROVEN_NO_MATCH`, `SET / MULTISET / ORDER`, explicit cardinality and closure, mandatory premises/obligations/material inputs, coherence/temporal/falsifier/independence rules, mandatory-v1 evaluation and UNKNOWN fallback. Applicability expected values are recursively frozen and serialization returns detached values so later caller mutation cannot alter semantics under an existing content ID.

`main_review/acr_authoring_audit.py` defines a separately content-addressed Authoring Audit profile whose independent basis binds:

- exact bounded-domain hash, not merely a reusable domain label;
- exact applicability predicate semantics including operators, values and tree structure;
- bound subject variables;
- semantic carriers, consumer interpretation and affected relations;
- collection semantics, cardinality and closure grades;
- premise, obligation and material-input families **and their closure grades**;
- admissible proof classes and permitted capabilities;
- repeated authority premises, coherence, temporal, falsifier and independence rules;
- mandatory external-review lane cardinality;
- canonical negative-applicability burden and UNKNOWN fallback.

A malformed constructor-bypass contract fails closed as `contract_noncanonical_or_malformed`. `CLEAN` means only structurally eligible for later independent qualification; it never means `QUALIFIED`. ACR qualification escapes remain permanent qualification evidence, require suspension/revocation disposition and impact analysis, and cannot auto-promote a corrected contract.

## Hostile-review correction

Exact-head repository proof on predecessor candidate `f07bdef1e157d5dcf708f13ec9860ee5f4bf606f` established `1306 passed / 2 historical XFAIL / 0 failed`, clean-clone proof PASS and Main Review PASS. Hostile review then found valid authoring-audit and identity escapes, so that candidate was **not** merged.

The corrected local construction harness preserves the prior SAE-20 tests and adds regression cases for every accepted finding:

- exact-domain generation/dimension substitution;
- applicability `any_of`, negation and expected-value substitution;
- mutable expected-value aliasing through input or serialized payload;
- premise/obligation/material-input closure downgrade;
- malformed negative-applicability burden;
- bound-subject, admissible-proof-class and permitted-capability drift;
- arbitrary malformed constructor-bypass collection;
- complete manifest local-proof assertions.

Corrected focused production/hostile suite: **52 passed / 0 failed**. Python compile proof passes. The production modules contain no `str(...)`, `int(...)` or `bool(...)` coercion sites.

The corrected pushed head must independently earn repository-wide CI, clean-clone proof, Main Review and hostile-review closure. No predecessor result is transferred as current-head proof.

## Authority boundary

This candidate does **not** implement or claim SAE-30 qualification issuer authority, Judge Assurance Ledger integration, total contract-instance/obligation closure, Genesis activation, normal Sergeant verdict authority or automatic qualification of any contract/dependent programme.

Only a separately reviewed and proved SAE-20 lifecycle closeout may produce `QUALIFIED_ACR_FOUNDATION` for the exact merged candidate generation.
