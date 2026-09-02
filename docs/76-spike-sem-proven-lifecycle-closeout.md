# SPIKE-SEM — PROVEN feasibility lifecycle closeout

Date: 2026-09-02

Status: **PROVEN FEASIBILITY; NO PRODUCTION SEMANTIC OR ACR AUTHORITY**.

Authority gain: **none**.

This record closes the bounded `SPIKE-SEM — Real semantic qualification / false-UNKNOWN feasibility` roadmap node. It proves that a defensible initial semantic domain can be stated, hostile false-EXACT/false-UNKNOWN/resource cases can be falsified, and the current Sergeant corpus can be measured without hiding unresolved semantics. It does **not** implement a production semantic analyzer, qualify an ACR domain, create a Capability Passport, or alter any current Sergeant verdict path.

## Authority chain

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Proven root: `docs/66-sae00-proven-lifecycle-closeout.md` / `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.
- SAE-00 proven merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Current SPIKE-SEM candidate authority: `docs/74-spike-sem-semantic-feasibility.md` / `docs/75-spike-sem-feasibility-manifest.json`.
- Exact reviewed candidate head: `6c213a29bcc78ba80d2107ee28692faad931a58f`.
- Construction/review PR: `#175`.

## Frozen charter and result

The roadmap requires SPIKE-SEM to establish a defensible initial bounded semantic domain and measure practical UNKNOWN/false-positive behavior on real code. It explicitly requires direct calls, bounded indirect dispatch, decorators, `getattr`-style dispatch, framework registration, plugin/entry-point loading, generated configuration where practical, closure grades, false-positive pressure, and resource-explosion behavior.

That charter is satisfied by spike-only evidence under `tests/spike_sem/`. No production `main_review/` code was changed.

## Hostile review changed the answer

The first measurement was rejected rather than defended. It reported zero UNKNOWN because unresolved calls could disappear from the denominator, could false-grade a shadowed import as EXACT, and did not charge later candidate expansion against its resource counter.

PR #175 hostile review identified all three defects:

1. unresolved calls must remain explicit `UNKNOWN`;
2. lexical shadowing must prevent false `EXACT` binding;
3. semantic/candidate expansion must consume the finite operation budget.

The probe was rebuilt around those controls. The first measurement is permanently recorded as `WITHDRAWN` in `docs/75` and must not be reused.

All three review threads were replied to and resolved only after fresh exact-head execution proved the corrected behavior.

## Corrected measured result

Review-hardened discovery at head `6f47c742ffae3bf624e4147a15c0271ea435d3a9`, GitHub Actions run `33619547519`, intentionally failed only the measurement sentinel and produced:

- 136 parsed `main_review/` Python files;
- 14,439 semantic relations;
- 924,042 charged operations under a 2,000,000-operation spike ceiling;
- 0 parse errors;
- no budget exhaustion.

Exact observed grade counts:

- `EXACT`: 2,528 — `0.17508137682665004`;
- `CONSERVATIVE_SUPERSET`: 3 — `0.00020777062123415748`;
- `PARTIAL`: 2,008 — `0.13906780247939607`;
- `UNKNOWN`: 9,900 — `0.6856430500727198`.

The result is intentionally uncomfortable: **current `main_review/` is UNKNOWN-dominant under the narrow qualified-candidate domain**. That is a useful feasibility result. It prevents later ACR/semantic work from laundering unresolved calls into false coverage.

## Exact candidate proof

After the measurement was frozen into the tests and content-bound candidate records, exact head `6c213a29bcc78ba80d2107ee28692faad931a58f` completed:

- full pytest suite: **1108 passed, 1 deliberate historical XFAIL, 0 failed**;
- clean-clone proof: **success** through tests, scan, evidence, review, app bridge, IDE Bench contract, battle fixtures/live outputs, THETECHGUY verification standard, final gate, end-to-end review suite, independent reviewer module, and mocked live GitHub integration.

The single XFAIL remains only the already-documented immutable SAE-00 historical candidate-tree count assertion. It is unrelated to SPIKE-SEM.

GitHub execution is supporting confirmation, not authority by availability.

## What is actually proven

SPIKE-SEM proves only the following bounded feasibility statements:

- a narrow static relation domain can produce defensible candidate `EXACT` results for non-shadowed statically closed cases;
- every unresolved Python call can remain visible as `UNKNOWN` rather than disappearing from coverage accounting;
- finite same-name receiver candidates can be represented as `CONSERVATIVE_SUPERSET` rather than false exactness;
- framework registration can remain `PARTIAL` when callback identity is known but invocation semantics are not qualified;
- dynamic dispatch/configuration, lexical ambiguity, parse failure, and resource exhaustion can fail closed to `UNKNOWN`;
- candidate expansion can be bounded by the same finite operation budget as the rest of semantic analysis;
- the current production name-only call-graph heuristic has a reproducible same-name false-positive counterexample and is not eligible for future `EXACT` semantic authority;
- current real-code UNKNOWN pressure is high enough that the first future qualified semantic domain must remain deliberately narrow.

## Initial domain recommendation — not activation

The candidate recommends future `EXACT` eligibility only for non-shadowed statically closed local/import/module calls, bounded constant-key dispatch, statically bound decorators, literal imported-module `getattr`, and concrete entry points with present targets.

That recommendation is **not** an activated ACR domain. `SAE-20` must define/qualify the ACR foundation, and `SAE-60` must later establish Capability Passports, exact domains/generations/ceilings, qualified parser/framework lineage, hidden holdout/transfer evidence, and fail-closed unsupported/resource behavior.

## Residual obligations

Still unresolved by construction:

- production semantic analyzer architecture;
- complete qualified Python import/package and lexical-scope semantics;
- dispatch-table mutation/alias/escape analysis;
- framework-specific invocation semantics;
- cross-language semantic relations;
- native/reflection boundaries;
- generated-code/configuration provenance;
- external dependency semantic closure;
- production resource ceilings;
- independent qualification corpus/holdouts;
- ACR language/runtime assumptions;
- Capability Passports and semantic qualification generations.

No later programme may treat this spike as having solved those obligations.

## Bootstrap authority boundary

The frozen roadmap gives SPIKE-SEM exactly one proof dependency: PROVEN `SAE-00`. General qualification machinery is introduced only later by `SAE-30`, while semantic capability qualification itself is `SAE-60` and depends on `SAE-20`, `SAE-30`, `SAE-50`, and PROVEN `SPIKE-SEM`.

Requiring those later mechanisms to qualify their own early feasibility input would invert the frozen dependency graph and fabricate authority that the roadmap does not grant.

Therefore this bounded lifecycle closeout uses only:

- PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY`; and
- the founding architecture's permitted Owner/Root constitutional TCB.

That bootstrap can determine only whether this bounded feasibility charter was satisfied. It cannot qualify `SAE-20`, `SAE-50`, `SAE-60`, an ACR contract/domain, a parser/framework, or a Capability Passport; it cannot create semantic verdict authority, convert UNKNOWN into PASS, satisfy Genesis, convert business risk into engineering PASS, or activate a partial Assurance Evolution generation.

## Dependency effect

After this closeout is canonical, the roadmap dependency `SPIKE-SEM` is resolved for dependency accounting.

The direct downstream dependency is `SAE-60 — Semantic Capability Qualification Foundation`, whose proof still requires `SAE-20`, `SAE-30`, and `SAE-50` in addition to SPIKE-SEM. This closeout does **not** qualify, prove, or activate SAE-60.

`SAE-10`, `SAE-20`, and `SAE-30` remain separate roadmap programmes and must earn their own lifecycle state.

## Recovery rule

A zero-context executor must treat `docs/74` / `docs/75` and reviewed candidate head `6c213a29bcc78ba80d2107ee28692faad931a58f` as the measured SPIKE-SEM candidate generation, and this document plus `docs/77-spike-sem-proven-lifecycle-closeout-manifest.json` as the later lifecycle disposition.

The withdrawn first measurement must remain visible as historical failed evidence. Live GitHub remains authoritative for mutable repository/PR state. No future recovery may reinterpret the 68.56% UNKNOWN result as a requirement to weaken UNKNOWN for better coverage.
