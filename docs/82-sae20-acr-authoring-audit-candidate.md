# SAE-20 — Assurance Contract Registry + Authoring Audit candidate

Date: 2026-09-06

Status: **CANDIDATE**.

Construction base: canonical Sergeant `main` at `e4cd5af49823a97451a998a3ae553a1cefb2d97d`.

## Authority

This candidate implements SAE-20 under `docs/58-sergeant-assurance-evolution-founding-architecture.md`, `docs/59-sergeant-assurance-evolution-roadmap.md`, and PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY` from `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.

SAE-20 has one proof dependency: SAE-00. SAE-10 is already PROVEN but is not fabricated as a proof dependency for SAE-20.

## Candidate foundation

`main_review/assurance_contract_registry.py` defines bounded domains, immutable content-addressed contract/registry identity, declarative `TRUE / FALSE / UNKNOWN` applicability, `PROVEN_NO_MATCH`, `SET / MULTISET / ORDER`, explicit cardinality and closure, mandatory premises/obligations/material inputs, coherence/temporal/falsifier/independence rules, mandatory-v1 evaluation and UNKNOWN fallback.

Applicability expected JSON is immutable and detached from caller mutation. Frozen JSON maps require sorted unique keys. Unsupported runtime values conserve UNKNOWN. Equality is recursive and type-sensitive. One-shot authority-bearing iterables are materialized once before validation and sorting. Unit cardinalities `ZERO_OR_ONE` and `EXACTLY_ONE` require the canonical JSON integer `1`; Python-equal aliases such as `True` and `1.0` are rejected.

`main_review/acr_authoring_audit.py` defines a separately content-addressed Authoring Audit profile binding exact contract ID and generation, bounded-domain hash, applicability predicate semantics, bound subjects, semantic carriers, consumer interpretation, affected relations, collections/cardinality/closure, premises/obligations/material inputs and closure grades, proof classes, capabilities, repeated authority premises, coherence, temporal validity, falsifiers, independence and external-review lane cardinality.

The profile canonically round-trips with its content hash before any requirement is trusted. A malformed/tampered profile fails closed as `profile_noncanonical_or_malformed`; a malformed contract fails closed as `contract_noncanonical_or_malformed`. `CLEAN` never means `QUALIFIED`.

A later ACR qualification escape remains permanent qualification evidence, requires suspension/revocation plus impact analysis, and cannot auto-promote a corrected contract.

## Hostile-review lineage

Predecessor `f07bdef1e157d5dcf708f13ec9860ee5f4bf606f` was not merged after valid ACR authoring/identity findings.

First hardened head `61f82eaa14478c409d684017663edccf6ee311e8` earned repository CI `1324 passed / 2 historical XFAIL / 0 failed`, clean-clone proof PASS and Main Review PASS. Fresh Codex review found six additional valid defects, so its proof was not transferred.

Second hardened head `0fcb1141777c4309d8d4ed66f889870ab036f9ac` fixed all six and independently earned repository CI **1337 passed / 2 historical XFAIL / 0 failed**, clean-clone proof PASS and Main Review PASS. Fresh CodeRabbit review then found one additional valid type-identity defect: unit cardinalities accepted `True` and `1.0` because Python equality treats them as `1`. A second CodeRabbit thread duplicated the already-fixed one-shot iterable issue.

The current correction requires canonical integer `1` for `ZERO_OR_ONE` / `EXACTLY_ONE` and adds a regression for boolean/float aliases.

Local reconstructed SAE-20 suite for this correction: **65 passed / 0 failed**. Python compile proof passes. The production modules contain no `str(...)`, `int(...)`, or `bool(...)` coercion calls.

All predecessor results are historical construction/review evidence only. The exact newly published head must independently earn repository CI, clean-clone proof, Main Review and fresh hostile-review closure.

## Authority boundary

This candidate does **not** implement or claim SAE-30 qualification issuer authority, Judge Assurance Ledger integration, total contract-instance/obligation closure, Genesis activation, normal Sergeant verdict authority, or automatic qualification of any contract/dependent programme.

Only a separately reviewed and PROVEN SAE-20 lifecycle closeout may produce `QUALIFIED_ACR_FOUNDATION` for the exact accepted generation.
