# SAE-20 — Assurance Contract Registry + Authoring Audit candidate

Date: 2026-09-04

Status: **CANDIDATE — corrected after internal hostile review**.

Construction base: canonical Sergeant `main` at `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Authority

This candidate implements the SAE-20 foundation defined by:

- `docs/58-sergeant-assurance-evolution-founding-architecture.md`;
- `docs/59-sergeant-assurance-evolution-roadmap.md`;
- PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY` from `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.

SAE-20 has one proof dependency: SAE-00. SAE-10 is already PROVEN but is not fabricated as a proof dependency for SAE-20.

## Candidate foundation

The candidate adds two isolated authority layers:

1. `main_review/assurance_contract_registry.py`
   - finite bounded domain identity;
   - immutable content-addressed contract and registry identity;
   - declarative `TRUE / FALSE / UNKNOWN` applicability;
   - missing facts conserve UNKNOWN;
   - `PROVEN_NO_MATCH` negative-applicability burden;
   - `SET / MULTISET / ORDER` collection semantics;
   - explicit cardinality and closure-grade requirements;
   - mandatory premise, repeated-authority-premise, obligation, material-input, coherence, temporal, falsifier, independence, consumer/framework-interpretation and external-review-lane declarations;
   - every v1 contract is mandatory;
   - a missing mandatory evaluation is represented as UNKNOWN rather than disappearing;
   - candidate payloads have no writable qualification state and cannot self-qualify.

2. `main_review/acr_authoring_audit.py`
   - a content-addressed audit profile separate from the candidate contract;
   - independent-basis identities rather than a contract self-defining its audit universe;
   - the profile binds the **exact bounded domain** and the independently expected declarative applicability predicate;
   - premise, obligation and material-input requirements retain their required closure grades instead of collapsing to family names;
   - fail-closed canonical validation prevents direct dataclass construction/replacement from bypassing authoring authority;
   - mutable generation aliases are not authoring-clean authority;
   - explicit attacks for applicability omission/semantic weakening, semantic carrier, consumer interpretation, affected relations, cardinality/collection semantics, closure grade, premises, repeated authority premises, obligations, material inputs, coherence, temporal validity, falsifier families, independence and mandatory external-review-lane cardinality;
   - `CLEAN` means only structurally clean enough to enter later qualification; it never means QUALIFIED;
   - ACR qualification escapes become permanent qualification evidence and require suspension/revocation disposition plus impact analysis;
   - corrected contracts cannot auto-promote after an escape.

## Internal hostile-review correction

The exact first pushed candidate was hostile-reviewed before lifecycle promotion. That review is project-controlled and therefore **NOT_INDEPENDENT** for SAE-20 qualification.

It found four authority-integrity defects:

1. premise/obligation/material-input closure grades were reduced to family-name presence during authoring audit, allowing `EXACT -> PARTIAL` weakening to evade detection;
2. applicability audit checked only referenced fact names, so a predicate could retain the same facts while weakening `all_of` semantics to `any_of`;
3. authoring scope compared only `domain_id`, allowing bounded-domain generation/digest substitution;
4. direct construction/replacement of frozen dataclasses could bypass constructor/persistence invariants because the audit did not canonical-validate its inputs.

The corrected candidate fixes the authority model rather than patching symptoms. The first candidate commit is not promoted and is replaced by a new atomic candidate from the same canonical construction base.

## Authority boundary

This candidate does **not** implement or claim:

- SAE-30 Qualification Authority Registry or qualification issuer authority;
- `QUALIFIED` as producer-writable state;
- Judge Assurance Ledger integration;
- total contract-instance/obligation closure;
- Genesis qualification or activation;
- normal Sergeant verdict authority;
- automatic qualification of any contract or dependent programme.

Only a separately reviewed and proved SAE-20 lifecycle closeout may produce `QUALIFIED_ACR_FOUNDATION` for this exact generation, and only if the independent qualification obligations defined by the founding architecture are actually satisfied.

## Construction proof

Historical pre-review construction evidence:

- initial RED: modules absent, both test modules failed collection as expected;
- first GREEN: 22 passed / 0 failed;
- broadened architecture RED: 26 failures / 4 passed until the additional architecture families were implemented;
- broadened GREEN: 30 passed / 0 failed;
- final constitutional RED: four expected failures for missing mandatory-evaluation UNKNOWN, mandatory-v1 persistence, and durable qualification-escape evidence;
- initial production GREEN: **34 passed / 0 failed**;
- Python compile proof: PASS;
- coercive persistence scan over SAE-20 production modules: no `str(...)`, `int(...)`, or `bool(...)` coercion sites.

Post-review correction evidence:

- the closure-grade escape was independently reproduced from the old audit logic before correction;
- corrected audit compile proof: PASS;
- correction harness total: **35 passed / 0 failed** — 24 repository authoring-audit tests plus 11 focused hardening tests against the corrected production audit boundary with faithful minimal registry/base API harnesses;
- hostile cases cover premise/obligation/material-input closure weakening, same-facts applicability weakening, exact-domain generation substitution, noncanonical contract/profile bypass and mutable-generation aliases.

Repository-wide proof is intentionally not fabricated from the focused harness. The exact corrected pushed candidate must earn full repository proof in the real repository tree.
