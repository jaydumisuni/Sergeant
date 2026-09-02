# SPIKE-SEM — Bounded Semantic Feasibility

Date: 2026-09-02

Status: **CANDIDATE — REVIEW-HARDENED REMEASUREMENT PENDING, NO PRODUCTION AUTHORITY**.

Authority gain: **none**.

This is the bounded `SPIKE-SEM` feasibility record required by the frozen Sergeant Assurance Evolution roadmap. It does not modify `main_review/`, activate an ACR supported domain, upgrade current call-graph findings to semantic proof, or grant verdict authority.

## 1. Authority and scope

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Required proof dependency: `SAE-00` only.
- Proven SAE-00 merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Canonical main used to start this spike: `9a42ceb4139f37e56e6a0725ae07f16bea58d48e`.
- Existing production mechanism inspected: `main_review/capability_engine.py`.
- Spike-only probe: `tests/spike_sem/semantic_feasibility_probe.py`.
- Spike-only proof: `tests/spike_sem/test_semantic_feasibility_probe.py`.
- Construction PR: `#175`.

The charter requires a defensible bounded semantic domain and practical measurement of `EXACT`, conservative-superset, `PARTIAL`/`UNKNOWN`, false-positive pressure, and resource/state-explosion behavior. Unsupported constructs must narrow to `UNKNOWN`; coverage numbers cannot weaken that rule.

## 2. Existing Sergeant mechanism recovered before reasoning

Sergeant already has a static Tier-1 capability engine. For Python it records exported symbol names and call spellings, then correlates changed exports with those names. That is useful repository intelligence, but receiver/import identity is not required, so equal spellings in unrelated modules can collide.

SPIKE-SEM therefore does not replace or modify the production engine. It measures what a stricter bounded relation model can actually establish.

## 3. Review-hardened classification law

The spike-only probe uses four feasibility grades:

- `EXACT` — a target is statically closed inside the bounded corpus with no detected lexical shadowing or ambiguous module rebinding.
- `CONSERVATIVE_SUPERSET` — exact receiver identity is unavailable, but a finite over-approximating candidate set is available.
- `PARTIAL` — useful identity is bound, but required implementation/framework semantics remain outside the bounded model.
- `UNKNOWN` — safe closure is unavailable, parsing fails, lexical binding is ambiguous, or the finite operation budget is exhausted.

These labels are not current Sergeant verdict authority and are not a future ACR schema by themselves.

### 3.1 Candidate EXACT families

The review-hardened probe may classify these narrow cases `EXACT`:

1. non-shadowed calls to top-level functions/classes defined in the bounded corpus;
2. non-shadowed explicitly imported symbol calls whose target exists in the corpus;
3. non-shadowed imported-module attribute calls whose module + attribute resolve in the corpus;
4. non-shadowed constant-key dispatch tables with statically bound values;
5. statically bound decorator identity;
6. literal `getattr(imported_module, "symbol")()` where the module spelling is not shadowed and the target exists;
7. concrete `pyproject.toml` `module:symbol` entry points whose target exists in the bounded corpus.

Any local/parameter binding that can shadow a module/import spelling prevents an `EXACT` claim for that call. Multiply rebound module spellings are also non-EXACT.

### 3.2 Non-EXACT boundary

- unresolved receiver attribute matching → `CONSERVATIVE_SUPERSET` when a finite exported-name candidate set exists;
- framework registration with a bound callback but unproved framework invocation semantics → `PARTIAL`;
- bound calls into implementation outside the bounded corpus → `PARTIAL`;
- unresolved calls, dynamic `getattr`, dynamic dispatch keys, generated target strings, star imports, lexical shadowing, ambiguous module rebinding, parse failures, and exhausted operation budgets → `UNKNOWN`.

Every Python `ast.Call` now receives one call-like relation. Unresolved calls are not silently dropped from the denominator.

## 4. Required construct matrix — review-hardened calibration

The synthetic roadmap matrix now measures:

| Grade | Count | Rate |
| --- | ---: | ---: |
| EXACT | 6 | 50% |
| CONSERVATIVE_SUPERSET | 0 | 0% |
| PARTIAL | 2 | 16.666666666666664% |
| UNKNOWN | 4 | 33.33333333333333% |
| **Total** | **12** | **100%** |

The matrix includes direct calls, constant-key indirect dispatch, decorators, literal and dynamic `getattr`, framework registration, a concrete plugin entry point, generated configuration, an external module call, and local class construction. The two builtin `getattr` call nodes themselves remain explicit `UNKNOWN` call relations because builtin/external call semantics are outside this bounded in-repository target model.

Additional hostile fixtures prove:

- `from target import run; def invoke(run): return run()` is `UNKNOWN`, never a false `EXACT` to `target.run`;
- unresolved parameter callback and receiver calls remain explicit `UNKNOWN` relations;
- same-name attribute candidate expansion consumes the same finite operation budget as AST/scope/alias work and fails closed with a resource-budget `UNKNOWN`.

## 5. Real Sergeant measurement history

### 5.1 Invalidated first measurement

The first deliberate RED discovery at head `3667561baf731482d76be10a38c7cfa1ef54f2b5`, Actions run `33615685272`, produced `1096 passed, 1 expected discovery failure, 1 historical XFAIL` and reported 4,539 relations across 136 `main_review/` files.

That measurement is **withdrawn from candidate authority**. Hostile review proved its denominator omitted unresolved calls, its lexical binding model could false-grade shadowed imports `EXACT`, and its state counter did not charge later candidate expansion. The earlier `55.695% EXACT / 44.239% PARTIAL / 0% UNKNOWN` distribution must not be reused.

### 5.2 Corrected measurement boundary

The review-hardened probe now:

- classifies every `ast.Call` rather than dropping unresolved calls;
- tracks lexical scope conservatively enough to prevent shadowed-import false `EXACT` results;
- treats repeated module binding names as ambiguous;
- charges source sizing, scope traversal/child expansion, module binding/symbol census, alias passes, dispatch candidates, semantic-node analysis, framework callback expansion, attribute candidate expansion, and entry-point expansion to one finite operation budget;
- uses a 2,000,000-operation default ceiling for the current spike probe.

The exact corrected `main_review/` distribution is intentionally **pending fresh execution**. `tests/spike_sem/test_semantic_feasibility_probe.py` contains a discovery sentinel so the next run mechanically exposes the new values before they are frozen.

## 6. Production false-positive pressure

A dedicated adversarial fixture remains valid: when `src/target.py` and an unrelated module both define `handle`, the current production name-only call-graph heuristic reports both same-spelled callers for the changed target. In that two-reported-caller microcase there is one true caller and one false positive.

This is not a universal 50% real-world rate claim. It is a concrete counterexample proving bare-name correlation is not eligible for future `EXACT` semantic authority.

## 7. Resource/explosion law

The probe has finite controls:

- operation budget: default **2,000,000**;
- alias propagation: default **2 hops**.

The budget is not merely an AST-node counter. Candidate expansion and repeated semantic-analysis work consume it. A high-fanout same-name attribute fixture proves exhaustion can occur specifically during candidate expansion and returns `UNKNOWN` rather than silently truncating the candidate set.

No universal budget sufficiency is claimed. Production qualification must calibrate its own resource law against the qualified domain.

## 8. Initial semantic-domain recommendation

The recommendation remains intentionally narrow:

- admit only statically closed, non-shadowed direct/import/module relations, bounded constant-key dispatch, statically bound decorators, literal imported-module `getattr`, and concrete packaging entry points as candidate `EXACT` families;
- retain unresolved receiver matches as `CONSERVATIVE_SUPERSET`;
- retain framework registrations/external implementation semantics as `PARTIAL`;
- retain all unresolved/dynamic/ambiguous/exhausted cases as `UNKNOWN`.

A later ACR generation may recover precision with a fully qualified lexical/import/framework model. It must not recover precision by weakening UNKNOWN.

## 9. Open gaps

SPIKE-SEM does not solve production analyzer architecture, complete Python package/import resolution, dispatch-table mutation/escape analysis, framework lifecycle semantics, cross-language relations, native/reflection boundaries, generated-code provenance, external dependency closure, production resource ceilings, qualification corpus independence, or ACR language/runtime assumptions.

## 10. Authority boundary

`SPIKE-SEM` authority gain remains **none**. All probe code remains under `tests/spike_sem/`; `main_review/` remains unchanged. No current Sergeant verdict may treat these grades as qualification or proof, and no partial Assurance Evolution generation may be activated from this candidate.
