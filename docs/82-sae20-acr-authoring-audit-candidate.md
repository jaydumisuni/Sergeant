# SAE-20 — Assurance Contract Registry + Authoring Audit candidate

Date: 2026-09-06

Status: **CANDIDATE**.

Construction base: canonical Sergeant `main` at `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Authority

This candidate implements the SAE-20 foundation defined by `docs/58-sergeant-assurance-evolution-founding-architecture.md`, `docs/59-sergeant-assurance-evolution-roadmap.md`, and PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY` from `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.

SAE-20 has one proof dependency: SAE-00. SAE-10 is already PROVEN but is not fabricated as a proof dependency for SAE-20.

## Candidate foundation

`main_review/assurance_contract_registry.py` defines bounded domains, immutable content-addressed contract/registry identity, declarative `TRUE / FALSE / UNKNOWN` applicability, `PROVEN_NO_MATCH`, `SET / MULTISET / ORDER`, explicit cardinality and closure, mandatory premises/obligations/material inputs, coherence/temporal/falsifier/independence rules, mandatory-v1 evaluation and UNKNOWN fallback.

Applicability expected JSON is immutable and detached from caller mutation. Frozen JSON maps are canonical only when keys are unique and sorted. Runtime facts that cannot be normalized as JSON become UNKNOWN rather than aborting mandatory evaluation. Equality is recursive and type-sensitive, so JSON boolean and number identities cannot collapse. One-shot authority-bearing iterables are materialized once before validation and sorting so validation cannot consume and silently erase them.

`main_review/acr_authoring_audit.py` defines a separately content-addressed Authoring Audit profile. The profile binds the exact contract ID **and contract generation**, bounded-domain hash, applicability predicate semantics, bound subjects, semantic carriers, consumer interpretation, affected relations, collections/cardinality/closure, premises/obligations/material inputs and closure grades, proof classes, capabilities, repeated authority premises, coherence, temporal validity, falsifiers, independence and external-review lane cardinality.

The profile itself must canonically round-trip and preserve its content hash before any of its requirements are trusted. A malformed/tampered profile therefore fails closed as `profile_noncanonical_or_malformed`; a malformed contract fails closed as `contract_noncanonical_or_malformed`. `CLEAN` means only structurally eligible for later independent qualification and never means `QUALIFIED`.

A later ACR qualification escape remains permanent qualification evidence, requires suspension/revocation plus impact analysis, and cannot auto-promote a corrected contract.

## Hostile-review lineage

Predecessor candidate `f07bdef1e157d5dcf708f13ec9860ee5f4bf606f` was not merged after hostile review found valid ACR authoring/identity escapes.

First hardened head `61f82eaa14478c409d684017663edccf6ee311e8` independently earned repository CI and clean-clone proof. Exact CI evidence was **1324 passed / 2 historical XFAIL / 0 failed**. Main Review and the major proof workflows also passed. Fresh exact-head Codex review then found six additional valid issues, so that head is not treated as proof for this corrected generation.

The second correction adds regressions for all six findings:

- canonical validation of the authority-bearing audit profile before use;
- exact contract-generation binding;
- duplicate/unsorted constructor-bypass frozen-map rejection;
- unsupported runtime applicability values conserve UNKNOWN;
- recursive type-sensitive JSON equality;
- one-shot requirements/collections/external-review lanes cannot be consumed and dropped.

Local reconstructed SAE-20 suite for this second correction: **64 passed / 0 failed**. Python compile proof passes. The production modules contain no `str(...)`, `int(...)`, or `bool(...)` coercion calls.

These local and predecessor results are construction evidence only. The exact newly published head must independently earn repository CI, clean-clone proof, Main Review and fresh hostile-review closure.

## Authority boundary

This candidate does **not** implement or claim SAE-30 qualification issuer authority, Judge Assurance Ledger integration, total contract-instance/obligation closure, Genesis activation, normal Sergeant verdict authority, or automatic qualification of any contract/dependent programme.

Only a separately reviewed and PROVEN SAE-20 lifecycle closeout may produce `QUALIFIED_ACR_FOUNDATION` for the exact accepted generation.
