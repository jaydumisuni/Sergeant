# SPIKE-SEM — Bounded Semantic Feasibility

Date: 2026-09-02

Status: **CANDIDATE — REVIEW-HARDENED MEASUREMENT FROZEN, NO PRODUCTION AUTHORITY**.

Authority gain: **none**.

This record is the bounded `SPIKE-SEM` feasibility candidate required by the frozen Sergeant Assurance Evolution roadmap. It does not modify `main_review/`, activate an ACR supported domain, upgrade any current call-graph finding to semantic proof, or grant verdict authority.

## 1. Authority and scope

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Frozen node title: `SPIKE-SEM — Real semantic qualification / false-UNKNOWN feasibility`.
- Required proof dependency: `SAE-00` only.
- Proven SAE-00 merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Canonical main used to start this spike: `9a42ceb4139f37e56e6a0725ae07f16bea58d48e`.
- Existing production mechanism inspected: `main_review/capability_engine.py`.
- Spike-only probe: `tests/spike_sem/semantic_feasibility_probe.py`.
- Spike-only proof: `tests/spike_sem/test_semantic_feasibility_probe.py`.
- Construction PR: `#175`.

The roadmap requires a defensible initial bounded semantic domain and measurement of `EXACT`, conservative-superset, `PARTIAL`/`UNKNOWN`, false-positive pressure, and state/resource-explosion behavior. Difficult constructs must narrow the initial supported domain and remain `UNKNOWN`; assurance requirements cannot be lowered for coverage.

## 2. Existing Sergeant mechanism recovered before reasoning

Sergeant already has a static Tier-1 capability engine. For Python it records exported symbol names and call spellings, then correlates changed exports with those names. This remains useful repository intelligence, but receiver/import identity is not required by that production heuristic, so unrelated same-spelled callables can collide.

SPIKE-SEM therefore does not replace or modify the production engine. It measures a stricter, spike-only bounded relation model so later ACR work starts from evidence rather than assumed semantic coverage.

## 3. Review-hardened classification law

The spike probe uses four feasibility grades:

- `EXACT` — a target is statically closed inside the bounded corpus with no detected lexical shadowing or ambiguous module rebinding.
- `CONSERVATIVE_SUPERSET` — exact receiver identity is unavailable, but a finite over-approximating candidate set is available.
- `PARTIAL` — useful identity is bound, but required implementation/framework semantics remain outside the bounded model.
- `UNKNOWN` — safe closure is unavailable, a call remains unresolved, parsing fails, lexical/module binding is ambiguous, or the finite operation budget is exhausted.

Every Python `ast.Call` receives one call-like disposition. An unresolved call may not disappear from the denominator merely because the probe cannot identify it.

### Candidate EXACT families

The evidence supports only a narrow initial candidate domain:

1. non-shadowed top-level local function/class calls;
2. non-shadowed explicitly imported symbol calls whose target exists in the bounded corpus;
3. non-shadowed imported-module attribute calls whose module + symbol exist in the corpus;
4. non-shadowed constant-key dispatch tables with statically bound callable values;
5. statically bound decorator identity;
6. literal `getattr(imported_module, "symbol")()` with a non-shadowed imported module and present target;
7. concrete `pyproject.toml` `module:symbol` entry points whose target exists in the bounded corpus.

A local/parameter binding that shadows an import/module spelling prevents an `EXACT` claim. Multiply rebound module spellings also fail closed.

### Non-EXACT boundary

- unresolved receiver attribute matching → `CONSERVATIVE_SUPERSET` when a finite exported-name candidate set exists;
- framework callback registration with bound callback identity but unproved framework invocation semantics → `PARTIAL`;
- statically identified external implementation outside the bounded corpus → `PARTIAL`;
- unresolved calls, dynamic `getattr`, dynamic dispatch keys, generated configuration targets, star imports, lexical shadowing, ambiguous module rebinding, parse failures, and exhausted budgets → `UNKNOWN`.

## 4. Required construct matrix

The review-hardened synthetic fixture covers the roadmap-required families and deliberately contains non-EXACT cases.

| Grade | Count | Exact rate |
| --- | ---: | ---: |
| EXACT | 6 | 0.5 |
| CONSERVATIVE_SUPERSET | 0 | 0.0 |
| PARTIAL | 2 | 0.16666666666666666 |
| UNKNOWN | 4 | 0.3333333333333333 |
| **Total** | **12** | **1.0** |

The fixture covers direct calls, constant-key indirect dispatch, decorators, literal/dynamic `getattr`, framework registration, a concrete plugin entry point, generated configuration, an external module call, and local class construction. Builtin `getattr` call nodes remain explicit `UNKNOWN` call relations because builtin/external implementation semantics are outside this bounded in-repository target model.

Additional hostile fixtures prove:

- `from target import run; def invoke(run): return run()` becomes `UNKNOWN`, never a false `EXACT` to `target.run`;
- unresolved parameter callback and receiver calls remain explicit `UNKNOWN` relations;
- same-name candidate expansion consumes the finite operation budget and returns a resource-budget `UNKNOWN` when exhausted.

## 5. Measurement history

### 5.1 First measurement — withdrawn

The first deliberate RED discovery at head `3667561baf731482d76be10a38c7cfa1ef54f2b5`, Actions run `33615685272`, reported 4,539 relations and zero UNKNOWN.

That result is **WITHDRAWN**. Hostile review proved three load-bearing defects:

1. unresolved `ast.Call` nodes could fall out of the denominator;
2. lexical shadowing could false-grade an imported target `EXACT`;
3. candidate expansion and later semantic work were not charged to the advertised resource counter.

The earlier `55.695% EXACT / 44.239% PARTIAL / 0% UNKNOWN` distribution must not be reused as SPIKE-SEM authority.

### 5.2 Corrected review-hardened discovery

After all three fixes, exact head `6f47c742ffae3bf624e4147a15c0271ea435d3a9` ran GitHub Actions CI run `33619547519`.

The full suite produced **1107 passed, 1 deliberate metrics-sentinel failure, 1 historical XFAIL**. The sentinel was the sole failure and mechanically exposed the corrected corpus measurement:

- files parsed: **136**;
- operation states charged: **924,042**;
- operation ceiling: **2,000,000**;
- total semantic relations: **14,439**;
- parse errors: **0**;
- budget exceeded: **false**.

Grade distribution:

| Grade | Count | Exact observed rate |
| --- | ---: | ---: |
| EXACT | 2,528 | 0.17508137682665004 |
| CONSERVATIVE_SUPERSET | 3 | 0.00020777062123415748 |
| PARTIAL | 2,008 | 0.13906780247939607 |
| UNKNOWN | 9,900 | 0.6856430500727198 |
| **Total** | **14,439** | **1.0** |

Relation kinds:

- `direct_call`: **4,479**;
- `decorator_binding`: **70**;
- `attribute_name_candidate`: **3**;
- `lexical_shadowing`: **25**;
- `unresolved_call`: **9,862**.

This is the central SPIKE-SEM result: once unresolved calls remain honestly inside the denominator, current `main_review/` is **UNKNOWN-dominant** under this deliberately narrow static domain. Approximately 68.56% of measured relations cannot be closed; only about 17.51% meet the spike's strict `EXACT` rule.

That is not a defect to hide. It is evidence that the initial ACR semantic domain must remain narrow and that future precision work must earn coverage through qualified lexical/import/framework semantics rather than converting UNKNOWN to confidence by assertion.

## 6. False-positive pressure in the current production heuristic

A dedicated adversarial fixture keeps one production limitation mechanically visible:

- `src/target.py` exports `handle`;
- `src/caller.py` imports/calls that target;
- `src/unrelated.py` defines/calls its own unrelated `handle`.

The current name-only production call-graph heuristic reports both same-spelled callers. In that two-reported-caller microcase there is one true caller and one false positive.

This is not a universal 50% real-world false-positive-rate claim. It is a reproducible counterexample proving bare-name correlation is not eligible for future `EXACT` semantic authority.

## 7. Resource/explosion law

The spike probe has finite controls:

- operation budget: **2,000,000**;
- alias propagation: **2 hops**.

The budget charges source sizing, scope traversal and child expansion, module binding/symbol census, imports, alias passes, dispatch candidates, semantic-node analysis, framework callbacks, attribute candidate expansion, and packaging entry-point expansion.

A high-fanout same-name attribute fixture proves candidate expansion itself can hit the ceiling and produces a resource-budget `UNKNOWN`. The real `main_review/` measurement used **924,042 operations**, about **46.2021%** of the spike ceiling, without exhaustion.

This proves feasibility for this corpus and bounded probe only. No universal production budget is established.

## 8. Initial semantic-domain recommendation

For the first future ACR-qualified semantic generation, start smaller than general Python semantics:

- candidate `EXACT`: only the statically closed, non-shadowed relation families listed above;
- `CONSERVATIVE_SUPERSET`: finite same-name receiver candidates where receiver identity is unresolved;
- `PARTIAL`: framework registration or known calls whose required implementation semantics are outside the bounded Review World;
- `UNKNOWN`: every unresolved, dynamic, ambiguous, parse-failed, or resource-exhausted construct.

A later qualified analyzer may recover precision. It must not recover precision by dropping unresolved calls, ignoring resource work, or weakening UNKNOWN.

## 9. Open gaps

SPIKE-SEM does not solve production semantic-analyzer architecture, complete Python import/package resolution, precise qualified lexical-scope semantics, dispatch-table mutation/escape analysis, framework lifecycle semantics, cross-language relations, native/reflection boundaries, generated-code provenance, external-dependency closure, production resource ceilings, qualification-corpus independence, or ACR language/runtime assumptions.

## 10. Authority boundary

`SPIKE-SEM` authority gain remains **none**. The probe and tests remain under `tests/spike_sem/`; `main_review/` is unchanged by the spike. These grades are feasibility evidence only. No current Sergeant verdict may treat them as qualification or proof, and no partial Assurance Evolution generation may be activated from this candidate.
