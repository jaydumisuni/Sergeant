# Sergeant Agent Working Memory

This file is persistent operating context for every AI, coding agent, reviewer, or future chat working in this repository. Read it before planning or changing the project.

## Sergeant 10-for-2 doctrine

The **10-for-2 / tenfold method is a core Sergeant operating law and also the working method agents should mirror when maintaining Sergeant.**

It is not merely a prompt-writing shortcut. Sergeant's speed in code review and controlled learning depends on officers decomposing missions into distinct evidence obligations and commanding proportionally larger private formations.

```text
Sergeant defines the mission, proof gates, and final verdict
→ Cpl is the reasoning council and commands the operation
→ permanent officers own specialist missions
→ each officer decomposes work into distinct private evidence obligations
→ private force = normally justified human-equivalent workers × 10
→ independent private lanes investigate, falsify, and cross-check
→ officers reconcile their cells
→ Cpl reconciles the officer council
→ Sergeant issues the final verdict
```

Hermes transports orders, evidence, and preserved learning packets. Hermes does not command, decide, promote lessons, or issue verdicts.

### Private-force scaling

- The force law is `human-equivalent workers × 10`.
- A task that normally needs 2 workers receives 20 privates.
- A task that normally needs 5 workers receives 50 privates.
- A task that normally needs 12 workers receives 120 privates.
- Twenty is the minimum meaningful private formation and the machine-scale equivalent of two ordinary workers; it is not a mission ceiling.
- An unresolved contradiction, hypothesis, repair world, transfer question, or proof gap may spawn another bounded private cell under the responsible officer.
- More privates must mean more distinct obligations, ecosystems, falsifiers, controls, or evidence paths—not duplicated reasoning.

The implemented source of truth is `main_review.operational_contracts.PRIVATE_FORCE_MULTIPLIER`, `private_force_size`, officer task packets, and the adaptive curriculum planner. Documentation and agent memory must remain consistent with those contracts.

## Code-review operation

For repository and pull-request review:

1. Sergeant fixes the review scope, authority, safety boundary, and required proof.
2. Cpl forms the council and assigns specialist missions to permanent officers.
3. Officers split correctness, security, architecture, contracts/tests, performance/concurrency, release integrity, provenance, and other justified fronts into private evidence obligations.
4. Safe independent fronts run in parallel; dependent or destructive steps remain serialized.
5. Private packets cannot expand scope or issue verdicts.
6. Officers cross-check source evidence, tests, runtime proof, negative controls, and competing explanations.
7. Cpl reconciles officer disagreements and returns the canonical evidence ledger.
8. Sergeant alone issues `PASS`, `NEEDS WORK`, or `BLOCK`.

Speed comes from parallel decomposition and disciplined reconciliation, never from skipping evidence, provenance, tests, or review gates.

## Controlled-learning operation

Sergeant may learn from **any useful repository**, including THETECHGUY projects and external repositories, not only changes made inside the Sergeant repository.

A GitHub commit, pull request, failed workflow, repair, review thread, or repository lineage is useful training evidence only when it can be converted into a governed case with enough truth and provenance to test a transferable lesson. Useful signals include:

- a defective commit or reproducible failing state;
- a fixing commit or independently verified correction;
- exact repository, commit, file, and line provenance;
- a frozen blind Sergeant result before the fix is revealed;
- tests, logs, review findings, or runtime evidence that establish the defect and repair;
- clean counterexamples and negative controls;
- unrelated-language or unrelated-repository transfer evidence;
- retained rejections and false-positive evidence.

The learning sequence remains:

```text
collect cross-repository candidate
→ verify provenance and usefulness
→ freeze Sergeant's blind result
→ reveal fixing truth
→ deploy tenfold private evidence cells under the learning officers
→ Teacher proposes
→ Prosecutor strengthens and challenges
→ Defender attempts to disprove
→ executable negative controls
→ unrelated-language or unrelated-repository transfer
→ hidden holdout
→ owner-controlled promotion proposal
```

A routine commit notification, shell transcript, successful build, or AI-generated change is not automatically a lesson. It becomes a candidate only after its before/after meaning and evidence are recovered. Models may teach inside explicitly authorized rounds, but normal Sergeant review remains able to operate model-free. No lesson is automatically promoted and no proposal is automatically merged.

## Agent execution method

Agents working on Sergeant should mirror the same doctrine:

```text
one coordinating lead
→ estimate the normally justified worker lanes
→ apply the tenfold method where parallel work is genuinely useful
→ assign distinct specialist questions
→ run safe fronts in parallel
→ independently cross-check important conclusions
→ reconcile into one clean result
→ finish faster without sacrificing quality
```

This agent-side use does not replace or negate Sergeant's product architecture. It is the same operational principle applied while building and maintaining the system.

### Required behaviour

1. Preserve the user's exact meaning and the established Sergeant hierarchy.
2. Keep one coordinating lead responsible for scope, dependencies, reconciliation, and delivery.
3. Give every officer, private, or agent lane a distinct question or evidence obligation.
4. Serialize destructive operations and conflicting writes.
5. Cross-check high-risk merge, release, deletion, security, preservation, and learning decisions with independent evidence.
6. Preserve all quality, provenance, safety, and promotion gates.
7. Report the reconciled result rather than flooding the user with internal worker chatter.

## Completion standard

A task is complete when the coordinated officer/private or agent lanes have produced a source-grounded, internally consistent result; required checks have passed; risks and blockers are stated honestly; useful cross-repository evidence has been retained or deliberately rejected with a reason; and no quality standard was dropped for speed.
