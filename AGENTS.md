# Sergeant Agent Working Memory

This file is persistent operating context for every AI, coding agent, reviewer, or future chat working in this repository. Read it before planning or changing the project.

## Mandatory zero-context pickup

After reading this file, read [`PICKUP.md`](PICKUP.md) before planning or changing Sergeant. `PICKUP.md` is the canonical current-state handoff; it records accepted-versus-candidate learning state and the next valid work.

Do not answer from repository memory alone when the question depends on current activity. Query live GitHub for the current `main` head, open pull requests, exact-head workflow state, and review threads before claiming what is active, mergeable, blocked, releasable, or complete. If live GitHub state is newer than `PICKUP.md`, recover the newer evidence and update the pickup record through normal review and proof.

## Hunter tenfold / 10-for-2 doctrine

The **10-for-2 / tenfold method has two linked applications**:

1. it governs how any AI, chat, coding agent, or reviewer should execute substantial work on Sergeant; and
2. it is a core Sergeant operating law used by Cpl, permanent officers, and private cells for fast code review and governed learning.

Do not separate these meanings. Sergeant depends on the same disciplined parallelism that working agents should use.

## Sergeant command chain

```text
Owner
→ Sergeant
→ Cpl council
→ permanent officers
→ task workers / privates
→ models, tools, scanners, and workspace capabilities
```

Hermes carries orders, evidence, status, and provenance across every level. Hermes does not command, promote lessons, or issue Sergeant's final verdict.

## Model-free core and optional reasoning boundary

Sergeant's normal review is **model-free by default**. Cpl, permanent officers, privates, deterministic detectors, scanners, tools, verified memory, and proof gates must remain useful without an AI login, hosted provider, or major GPU.

Models are optional extra-reasoning engines beneath the command chain. They may be enabled only by an explicit owner or user choice. One model or several models may assist a named officer investigation, but they are evidence inputs rather than votes, never replace officers or privates, never become a dependency for normal review, and never issue the final verdict. Model discovery, credentials, and provider usage must remain visibly disabled until that opt-in occurs.

## Sergeant private-force law

Sergeant estimates the normally justified human-equivalent worker requirement and deploys ten times that number as privates:

```text
2 human-equivalent workers  → 20 privates
5 human-equivalent workers  → 50 privates
12 human-equivalent workers → 120 privates
```

Twenty privates is the minimum machine-scale formation for work equivalent to two ordinary workers. It is not a ceiling. Larger missions scale proportionally, and a mission may contain multiple bounded private cells.

Permanent officers own specialist doctrine and split code review or learning work into distinct evidence obligations. Privates investigate those obligations in parallel through deterministic checks, models, tools, scanners, repository evidence, or approved workspace capabilities. The responsible officer cross-checks and reconciles the evidence before it moves upward. Sergeant remains final authority.

This tenfold private-force system is one of the mechanisms that gives Sergeant rapid code review and rapid learning without sacrificing proof.

## Cross-repository learning memory

Sergeant must consider **all useful THETECHGUY and external repository signals**, not only activity inside the Sergeant repository. Commits, pull requests, workflow runs, review findings, runtime logs, shell traces, test failures, repairs, and release failures may contribute evidence.

Every signal is governed before it can teach Sergeant:

```text
repository event
→ sanitized signal intake
→ tenfold officer/private triage
→ evidence_only / needs_lineage / candidate_ready / rejected
→ frozen blind review
→ fixing truth reveal
→ Teacher / Prosecutor / Defender
→ negative controls
→ unrelated-language or unrelated-repository transfer
→ hidden holdout
→ owner-controlled promotion proposal
```

A bot commit, formatting change, shell transcript, successful build, or review comment is **not automatically a lesson**. It may be retained as evidence or sent for lineage recovery. A candidate needs exact repository and event provenance, a confirmed defective state, a verified fixing state, scored production paths, evidence references, and a blind-review boundary. No signal, candidate, or proposal has automatic promotion or merge authority.

`.github/self-learning/cross-repository-sources.json` records sources whose access and evidence boundaries are already confirmed. It is not an exclusion list: another useful repository remains eligible when its provenance and access can be verified.

## Working-agent tenfold method

Any AI or chat working on Sergeant should mirror the same discipline:

```text
one coordinating lead
→ recover authority and the dependency DAG
→ estimate independently useful work lanes
→ expand the normally justified worker estimate through Hunter's tenfold method
→ distribute distinct specialist roles across the complete unblocked frontier
→ cross-check evidence while downstream-safe work continues
→ reconcile at genuine dependency barriers
→ bind dependent work to exact frozen upstream truth
→ finish faster without sacrificing quality
```

### Required behaviour

1. Keep one coordinating lead responsible for scope, the dependency graph, final reconciliation, and the delivered answer.
2. Split substantial work into independent fronts such as implementation, tests, security, architecture, release integrity, evidence, documentation, regression review, and downstream preparation.
3. Apply the tenfold multiplier when parallel work genuinely reduces elapsed time: two normally justified workers map to twenty roles, five to fifty, and twelve to one hundred twenty. Do not treat twenty as a ceiling.
4. Run independent fronts in parallel when their inputs and write targets do not conflict.
5. Serialize destructive operations, true dependency barriers, and multiple writes to the same file, branch, release, or external record.
6. Give each role a distinct question or deliverable. Do not create duplicate noise.
7. Cross-check important conclusions with independent evidence. High-risk merge, release, deletion, security, integrity, preservation, lesson-promotion, or final-verdict decisions require proof appropriate to the risk.
8. Reconcile disagreements explicitly. The coordinating lead must remove duplication, verify claims against source evidence, and produce one consistent verdict.
9. Preserve existing quality, safety, provenance, test, learning, and review gates. Speed comes from parallel decomposition and clean coordination, never from skipping proof.
10. Report the consolidated result rather than flooding the user with internal worker chatter.

### Machine-native dependency-frontier law

Tenfold must not imitate human phase-by-phase project scheduling.

For a substantial multi-stage campaign, recover the dependency DAG once and continuously occupy **every currently unblocked dependency node** with useful machine lanes. Roadmap phase labels define scope and authority; they are not automatic waiting points.

Required consequences:

1. Do not send the whole private force to one phase while other independent nodes are idle. Distribute workers across the unblocked frontier according to critical-path value, risk and evidence needs.
2. A hard dependency blocks freeze/merge/completion claims, but does not block safe downstream work that does not require unresolved upstream truth. Contract recovery, donor analysis, fixtures, isolated implementation, adversarial-test design, documentation and proof preparation may proceed early when safe.
3. When an upstream result freezes, every dependent candidate must rebind and reconcile against that exact SHA/evidence before it may freeze or ship.
4. Build, Review and Prove lanes should overlap when they are independent and do not conflict on mutable targets. Same-target mutations and destructive actions remain serialized.
5. Reallocate privates immediately as blockers appear or lanes complete. Do not leave machine capacity idle because the original allocation was modeled after human teams.
6. Optimize the **proven critical path / elapsed makespan**, not engineer-days. Human-equivalent workers are an input to the tenfold multiplier, not a calendar model. Do not invent meetings, shifts, sleep, handoff delay, or phase waiting unless a real physical or dependency constraint creates elapsed time.
7. Shared authority and rapid reconciliation are a machine advantage. Use them to eliminate handoff overhead without weakening exact-head evidence, Review, Freeze, Prove, or final authority.

The scheduling question for substantial work is:

> **What is the complete unblocked dependency frontier now, and how should the Tenfold force be distributed across it to minimize the proven critical path?**

The full operating doctrine is recorded in [`docs/50-tenfold-operating-doctrine.md`](docs/50-tenfold-operating-doctrine.md).

## Interpretation boundary

The user's exact wording is the requirement. Do not erase an existing Sergeant mechanism merely because the same phrase is also a working instruction.

In particular:

- "Use 10-for-2" means work faster through coordinated tenfold parallel roles and cross-checking.
- Inside Sergeant, the same rule is already the private-force scaling law used by officers and privates for review and learning.
- It does not authorize uncontrolled scope growth, duplicate roles, automatic lesson promotion, automatic merge, or weaker evidence gates.
- It does not require inventing a second tenfold subsystem; preserve and use Sergeant's existing private-force implementation correctly.

## Completion standard

A task is complete when the coordinated lanes have produced a source-grounded, internally consistent result; required checks have passed; officers or working agents have reconciled contradictions; useful cross-repository signals have been retained, qualified, or rejected with evidence; risks and blockers are stated honestly; and no quality standard was dropped for speed.
