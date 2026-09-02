# SPIKE-SEM — Bounded Semantic Feasibility

Date: 2026-09-02

Status: **CANDIDATE — MEASURED FEASIBILITY, NO PRODUCTION AUTHORITY**.

Authority gain: **none**.

This is the bounded `SPIKE-SEM` feasibility record required by the frozen Sergeant Assurance Evolution roadmap. It does not modify `main_review/`, does not activate an ACR supported domain, does not upgrade any current call-graph finding to semantic proof, and does not grant verdict authority.

## 1. Authority and scope

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Required proof dependency: `SAE-00` only.
- Proven SAE-00 merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Canonical main used for this spike: `9a42ceb4139f37e56e6a0725ae07f16bea58d48e`.
- Existing production mechanism inspected: `main_review/capability_engine.py`.
- Spike-only probe: `tests/spike_sem/semantic_feasibility_probe.py`.
- Spike-only proof: `tests/spike_sem/test_semantic_feasibility_probe.py`.
- Construction PR: `#175`.

The frozen charter requires a defensible initial bounded semantic domain and practical measurement of `EXACT`, conservative-superset, `PARTIAL`/`UNKNOWN`, false-positive pressure and resource/state-explosion behavior. Unsupported constructs must narrow to `UNKNOWN`; the architecture must not be weakened to obtain prettier coverage numbers.

## 2. Existing Sergeant mechanism recovered before reasoning

Sergeant already has a static Tier-1 capability engine. For Python it parses ASTs, records top-level exported symbol names, and records call names from `ast.Name` and `ast.Attribute`. Its current call-graph finding then correlates a changed file's exported names with call-name sets from other files.

That mechanism is useful repository intelligence, but it is deliberately lightweight. In particular, an attribute or local call name can collide across unrelated modules because the current call-graph finding does not require receiver/import identity to match the changed export.

SPIKE-SEM therefore does **not** replace or modify the production capability engine. It measures what a more explicitly bounded semantic relation model can and cannot establish.

## 3. Probe domain and classification law

The spike-only probe uses four grades:

- `EXACT` — the target is statically bound inside the bounded corpus by a closed local/import/module/configuration identity.
- `CONSERVATIVE_SUPERSET` — the exact receiver is not proven, but a finite over-approximating target set is available.
- `PARTIAL` — a useful portion of the relation is bound, but required semantics are outside the analyzed corpus or framework model.
- `UNKNOWN` — the target/semantics cannot be closed safely inside the bounded domain, parsing fails, or resource limits are exceeded.

The grade is a feasibility label only. It is **not** the future ACR semantic-proof schema and is not accepted by current Sergeant verdict code.

### 3.1 Initially defensible EXACT candidates

The probe supports the following as initial candidates for a future qualified semantic domain:

1. direct local calls to statically defined top-level functions/classes;
2. explicitly imported symbol calls where the module and symbol exist in the analyzed corpus;
3. explicitly imported module attribute calls where module + attribute resolve in the analyzed corpus;
4. bounded constant-key dispatch tables whose values are statically bound callables;
5. decorator callable identity where the decorator is statically bound;
6. literal `getattr(imported_module, "symbol")()` where both imported module and literal symbol resolve;
7. concrete `pyproject.toml` entry points of the form `module:symbol` when the target exists in the analyzed corpus.

This is a deliberately narrow starting set. Production qualification would still need subject/repository/generation binding, language-version constraints, alias semantics, mutation rules, import/package semantics and negative-control attacks.

### 3.2 CONSERVATIVE_SUPERSET candidate

An attribute call whose receiver identity is not statically bound may be mapped to the finite set of exported symbols with that attribute name. This is a useful over-approximation, but it is not `EXACT` and must not be promoted merely because the candidate set is small.

### 3.3 PARTIAL candidates

Framework registrations such as `register`, `add_route`, `connect`, or `subscribe` can bind a callback identity while leaving invocation timing, multiplicity, middleware, routing and lifecycle semantics unproved. These are therefore `PARTIAL` in the initial spike.

Calls into modules/symbols outside the bounded analyzed corpus are likewise `PARTIAL`: the local call identity may be known while external implementation semantics remain unmodeled.

### 3.4 UNKNOWN boundary

The initial domain fails closed to `UNKNOWN` for at least:

- dynamic `getattr` attribute names or receivers;
- dynamic dispatch-table keys;
- generated target/configuration strings assembled at runtime;
- star imports that prevent a closed binding census;
- state-budget exhaustion;
- constructs whose semantics cannot be closed by the bounded model.

`UNKNOWN` is not a failure of the architecture. It is the required honest result when proof is unavailable.

## 4. Required construct matrix — synthetic calibration

A deliberately small adversarial fixture covers the roadmap's required construct families.

Observed relation distribution:

| Grade | Count | Rate |
| --- | ---: | ---: |
| EXACT | 6 | 60% |
| CONSERVATIVE_SUPERSET | 0 | 0% |
| PARTIAL | 2 | 20% |
| UNKNOWN | 2 | 20% |
| **Total** | **10** | **100%** |

The cases include:

- direct call → `EXACT`;
- constant-key indirect dispatch → `EXACT`;
- decorator binding → `EXACT`;
- literal imported-module `getattr` → `EXACT`;
- dynamic `getattr` → `UNKNOWN`;
- framework registration → `PARTIAL`;
- concrete plugin entry point → `EXACT`;
- dynamically generated configuration target → `UNKNOWN`;
- external module call (`os.getenv`) → `PARTIAL` because its implementation is outside the bounded corpus;
- local class construction → `EXACT`.

This matrix intentionally contains non-EXACT results. It is a calibration artifact, not an all-green demonstration.

## 5. Real Sergeant `main_review/` measurement

The first deliberate RED measurement run on PR #175 head `3667561baf731482d76be10a38c7cfa1ef54f2b5` executed the probe against the complete `main_review/` Python corpus and failed only the discovery sentinel, exposing the metrics mechanically.

Observed exact values:

- files parsed: **136**;
- AST states visited: **225,231**;
- total semantic relations: **4,539**;
- parse errors: **0**;
- state-budget exceeded: **false**.

Grade distribution:

| Grade | Count | Exact observed rate |
| --- | ---: | ---: |
| EXACT | 2,528 | 0.5569508702357348 |
| CONSERVATIVE_SUPERSET | 3 | 0.0006609385327164573 |
| PARTIAL | 2,008 | 0.4423881912315488 |
| UNKNOWN | 0 | 0.0 |

Relation kinds observed:

- direct calls: **4,479**;
- decorator bindings: **57**;
- attribute-name candidate sets: **3**.

The zero `UNKNOWN` count is a property of what this bounded probe encountered in the current `main_review/` corpus. It is **not** evidence that dynamic dispatch or generated configuration is absent from all future code, and it cannot justify treating unrecognized constructs as exact.

The dominant practical pressure in this corpus is therefore **precision/closure**, not resource explosion: roughly 44.24% of observed relations are only `PARTIAL` because the bounded model cannot establish complete in-corpus target semantics.

## 6. False-positive pressure

A dedicated adversarial fixture demonstrates a real weakness in the current production capability-engine call-graph heuristic:

- `src/target.py` exports `handle`;
- `src/caller.py` imports and calls that target;
- `src/unrelated.py` defines and calls its own unrelated local `handle`.

The current name-only call-graph finding reports **both** files as callers of `src/target.py`, producing one true caller and one false positive in this two-caller microcase: **50% false-positive pressure in the adversarial reported-caller set**.

The spike-only bound-import relation resolves `src/caller.py` to `src.target.handle` and keeps `src/unrelated.py` bound to `src.unrelated.handle`, avoiding that collision in the measured fixture.

This is not a claim that Sergeant has a 50% real-world call-graph false-positive rate. It is a reproducible counterexample proving that bare-name correlation is not eligible for future `EXACT` semantic authority.

## 7. State/resource explosion

The probe has explicit finite controls:

- maximum AST-state budget, default 500,000;
- bounded alias propagation, default 2 hops.

When the AST-state budget is exceeded, the probe emits an `UNKNOWN` resource-budget relation and stops rather than silently truncating analysis and claiming completeness.

The current `main_review/` measurement used 225,231 states, approximately 45.05% of the 500,000-state spike budget, and did not exhaust it.

This establishes feasibility only for the measured repository/domain. It does not prove the bound is universally sufficient.

## 8. Initial semantic-domain recommendation

For the first future ACR-qualified semantic analyzer generation, start narrower than the full Python language.

Recommended initial admissible relation families:

- statically bound local/imported direct calls;
- imported-module attribute calls with exact module resolution;
- constant-key, immutable-at-analysis-point dispatch tables with statically bound values;
- statically bound decorator identity;
- literal `getattr` on an exactly resolved imported module;
- concrete packaging entry points whose module/symbol exists in the exact Review World.

Recommended non-EXACT treatment:

- unresolved receiver attribute matching → `CONSERVATIVE_SUPERSET`;
- framework callback registration without qualified framework semantics → `PARTIAL`;
- external implementation outside the Review World → `PARTIAL` or `UNKNOWN` according to the future ACR contract;
- dynamic reflection, dynamic dispatch keys, runtime-generated configuration, star-import ambiguity and exhausted budgets → `UNKNOWN`.

This recommended domain is intentionally smaller than what many static analyzers attempt. The objective is defensible assurance, not maximum apparent coverage.

## 9. Open gaps for later roadmap nodes

SPIKE-SEM does not solve:

- production semantic analyzer architecture;
- complete import/package resolution across every supported Python packaging layout;
- mutation/alias/escape analysis for dispatch tables;
- framework-specific registration and lifecycle semantics;
- cross-language semantic relations;
- native/extension/reflection boundaries;
- generated code/configuration provenance;
- closure proof for external dependencies;
- calibrated production resource ceilings;
- qualification corpus construction and independence;
- ACR language/version/runtime assumptions.

These are inputs to later ACR/Review World/qualification work, not excuses to weaken `UNKNOWN`.

## 10. Authority boundary

`SPIKE-SEM` authority gain remains **none**. The probe and its tests are feasibility evidence only and live under `tests/spike_sem/`; `main_review/` remains unchanged by this spike.

No current Sergeant verdict may interpret these grades as qualification or proof. No partial Assurance Evolution generation may be activated from this record.
