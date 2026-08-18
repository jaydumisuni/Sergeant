# Sergeant tenfold operating doctrine

## Dual meaning

Hunter's **10-for-2 / tenfold method** is both:

1. a working method for any AI, chat, coding agent, or reviewer operating on Sergeant; and
2. a core Sergeant execution law used by Cpl, permanent officers, and private cells during code review and governed learning.

These meanings reinforce each other. The working agent should use the same disciplined parallelism that Sergeant uses internally.

## Sergeant command chain

```text
Owner
→ Sergeant
→ Cpl council
→ permanent officers
→ task workers / privates
→ models, tools, scanners, and workspace capabilities
```

Hermes carries orders, evidence, status, and provenance across the chain. Hermes does not command, promote lessons, or issue the final verdict.

## Private-force law

Sergeant estimates the normally justified human-equivalent worker requirement, then deploys a private force at ten times that estimate:

```text
2 human-equivalent workers  → 20 privates
5 human-equivalent workers  → 50 privates
12 human-equivalent workers → 120 privates
```

Twenty privates is the minimum machine-scale formation for work equivalent to two ordinary workers. It is not the mission ceiling.

Permanent officers split review or learning work into bounded evidence obligations. Privates investigate those obligations in parallel through distinct roles, tools, scanners, models, or deterministic checks. The responsible officer cross-checks and reconciles the evidence before it moves upward. Sergeant remains final authority.

## Dependency-frontier law

Tenfold is **machine-native execution doctrine**, not a faster imitation of a human team moving phase by phase.

For any substantial multi-stage mission, the coordinating lead must recover the dependency graph before dispatch and continuously occupy the complete **currently unblocked dependency frontier** with useful private lanes.

```text
recover authority + dependency DAG
→ identify every currently unblocked node
→ dispatch distinct tenfold lanes across the frontier
→ keep downstream preparation moving where dependencies permit
→ reconcile only at genuine dependency/evidence barriers
→ bind dependent work to the exact frozen upstream result
→ re-open the frontier immediately
→ finish on the critical path, with proof intact
```

Required interpretation:

1. **Roadmap phases are authority/scope boundaries, not automatic scheduling barriers.** Do not serialize A → B → C merely because the roadmap is written in that order when B or C contains work that is already independent and safe to prepare.
2. **Hard dependencies block claims, not all useful work.** A downstream item may recover contracts, prepare fixtures, conduct donor research, build isolated candidate work, design adversarial tests, or prepare proof lanes before its dependency freezes when those activities do not require the unresolved upstream truth. It must not freeze, merge, publish, or claim completion until it has reconciled against the exact accepted dependency.
3. **Keep the machine force occupied.** Do not park 50, 100, or more available privates on one phase while other independent dependency nodes are idle. Allocate lanes across the frontier according to critical-path value, risk, evidence needs, and write-conflict boundaries.
4. **Parallelize Build, Review, and Prove where safe.** Independent review, threat analysis, fixture generation, regression design, deterministic scans, documentation recovery, and downstream preparation should overlap whenever their inputs and write targets do not conflict. Destructive or same-target mutations remain serialized.
5. **Reconcile at true barriers.** When an upstream candidate freezes, dependent lanes must rebind to its exact SHA/evidence and reconcile any speculative assumptions before their own freeze or ship decision.
6. **Reallocate dynamically.** When one lane blocks, completes, or discovers new dependency truth, redistribute privates immediately rather than leaving the remainder of the campaign on the previous allocation.
7. **Optimize elapsed critical-path completion, not human calendar simulation.** The human-equivalent estimate exists to size the machine force. It is not a schedule model. Do not convert Tenfold work into artificial engineer-days, meetings, shifts, or phase-by-phase waiting unless a real physical or dependency constraint requires elapsed time.
8. **Synchronization is an advantage, not permission to weaken proof.** Shared authority and rapid reconciliation eliminate human handoff overhead; they do not authorize stale evidence, duplicate noise, speculative promotion, or bypassing Review/Freeze/Prove gates.

The default question is therefore not "which phase are we on?" but:

> **What is the entire unblocked dependency frontier right now, and how should the Tenfold force be distributed across it to minimize the proven critical path?**

## Why Sergeant depends on it

The tenfold method is what gives Sergeant rapid code review and rapid governed learning without replacing proof with speed:

- more independent investigation lanes can run at once;
- officers can compare findings rather than trusting one path;
- false positives and contradictions are exposed earlier;
- language, architecture, security, tests, lifecycle, concurrency, and regression risk can be covered in parallel;
- learning candidates can be challenged by Teacher, Prosecutor, Defender, negative controls, transfer tests, and holdouts without serial bottlenecks.

The multiplier never authorizes duplicate noise, uncontrolled scope growth, automatic lesson promotion, or weaker evidence gates.

## Working-agent rule

Any AI or chat picking up Sergeant work should mirror this method:

```text
one coordinating lead
→ recover authority and the dependency DAG
→ split substantial work into distinct specialist lanes
→ saturate the currently unblocked frontier safely
→ cross-check evidence while downstream-safe work continues
→ reconcile at genuine dependency barriers
→ bind dependent work to frozen upstream truth
→ deliver one clean result faster without sacrificing quality
```

This does not mean inventing a new tenfold subsystem. Sergeant already has the private-force mechanism. The instruction is to preserve and use it correctly, both in the product and in the way agents work on the product.
