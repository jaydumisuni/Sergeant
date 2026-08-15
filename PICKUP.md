# Sergeant Zero-Context Pickup

This file is the canonical current-state handoff for a new AI, chat, coding agent, reviewer, or human returning to Sergeant with no conversation context.

Read in this order before planning or changing the project:

1. `README.md` — product identity, architecture, capabilities, safety boundary.
2. `AGENTS.md` — canonical persistent operating memory and 10-for-2 doctrine.
3. `PICKUP.md` — current state and next valid work.
4. Relevant files under `docs/` and `.github/self-learning/` named below.
5. Query GitHub for the current `main` head, open pull requests, current workflow state, and review threads before acting.

Do not treat old chat transcripts, stale branches, closed pull requests, or copied evidence as newer authority than current `main` plus live GitHub state.

## Current stable state

- Sergeant is model-free by default.
- Cpl, permanent officers, privates, deterministic detectors, scanners, memory, and proof gates remain the normal review path.
- Optional models are owner-enabled extra reasoning only; they are never Sergeant's identity, dependency, vote, or final authority.
- The 10-for-2 / tenfold doctrine has two linked meanings and both must be preserved:
  - working agents use coordinated parallel specialist lanes, cross-checking, and one reconciled answer;
  - Sergeant internally scales Cpl/officer/private review and governed learning through the 10× private-force law.
- Twenty privates is the minimum two-worker-equivalent formation, not a ceiling.
- Hermes transports orders, evidence, status, and provenance but does not command, promote lessons, or issue the final verdict.
- Automatic lesson promotion and automatic merge remain forbidden.

## Current learning state

Controlled self-learning week 1 is complete and integrated. The repository must now prefer project-driven continuous learning from verified real engineering work rather than starting another scheduled learning week unless the owner explicitly authorizes one.

The first accepted real-project model-free lesson remains the Lumi credential destination/origin lesson. It may be used by the normal review path because it already passed its governed promotion gates.

Two additional TechGuyCheckm8 repaired defect lineages are now preserved on `main` as candidate-ready inputs only:

1. `learn-tgcheckm8-checkout-credential-boundary-20260723`
   - source: `jaydumisuni/TechGuyCheckm8` PR #18
   - defective ref: `3b9b5d2469fed602cd6b5c728109cf193b9ccba1`
   - fixing ref: `40291a738e866e53b7d1cdcd0cf31f6e860357f5`
   - boundary: persisted checkout credentials must not remain available when third-party build or generation code runs in the same job.

2. `learn-tgcheckm8-checksum-path-namespace-20260723`
   - source: `jaydumisuni/TechGuyCheckm8` PR #18
   - defective ref: `3b9b5d2469fed602cd6b5c728109cf193b9ccba1`
   - fixing ref: `40291a738e866e53b7d1cdcd0cf31f6e860357f5`
   - boundary: integrity-manifest producers and downstream verifiers must share the same path namespace and runtime working-directory model.

These two records are not accepted lessons. Their next valid path is:

```text
frozen blind Sergeant review
→ fixing-truth reveal
→ Teacher / Prosecutor / Defender
→ executable positive and clean negative controls
→ unrelated-language or unrelated-repository transfer
→ hidden holdout
→ owner-controlled promotion proposal
```

Do not skip directly from candidate-ready to permanent officer/detector knowledge.

Authoritative candidate records:

- `.github/self-learning/signals/tgcheckm8-checkout-credential-boundary-2026-07-23.json`
- `.github/self-learning/signals/tgcheckm8-checksum-path-namespace-2026-07-23.json`
- `docs/56-techguycheckm8-10-for-2-harvest.md`

Unresolved TechGuyCheckm8 findings without verified fixing lineage remain evidence only and must not be promoted as truth.

## External donor state

KiloCode is recorded only as a future review/self-check donor. The canonical source is `Kilo-Org/kilocode`. A Kilo-derived mechanism must enter through Sergeant's existing governed cross-repository learning path and earn promotion; KiloCode does not replace Sergeant and CodeOps does not become the reviewer.

Relevant authority:

- `docs/01-research-sources.md`
- `docs/12-external-review-learning-loop.md`
- `docs/51-cross-repository-learning-intake.md`

## Live-state recovery rule

Before claiming the repository is ready, blocked, mergeable, releasable, or has no active work, query GitHub live. At minimum verify:

- current `main` head;
- all open pull requests and their exact heads;
- branch divergence from `main`;
- required workflow conclusions on the exact head being judged;
- CodeRabbit/external review comments and inline threads when applicable;
- whether a candidate, lesson, release, or preservation action still lacks an owner-controlled gate.

If live GitHub state conflicts with this file, recover the newer evidence, update `PICKUP.md` through normal review/proof, and treat current GitHub truth as authoritative.

## Next valid work

Unless the owner gives a different explicit instruction, the next substantive Sergeant learning work is to process the two TechGuyCheckm8 candidate-ready lineages through the governed learning path above. Real THETECHGUY project fixes from other repositories may also enter as candidates when exact defective/fixing provenance is verified.

Do not start a calendar-based Week 2 merely because Week 1 is complete.

## Completion boundary

A future chat has successfully recovered Sergeant only when it can state, without relying on prior conversation memory:

- what Sergeant is;
- the model-free/optional-model boundary;
- the dual 10-for-2 doctrine;
- the command chain and Hermes boundary;
- the governed cross-repository learning sequence;
- which lessons are accepted versus candidate-ready;
- the current live GitHub PR/check state;
- the next valid owner-authorized action.
