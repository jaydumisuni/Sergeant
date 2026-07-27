# Sergeant Hackathon Submission Brief

## Project

**Sergeant** — an evidence-based engineering reviewer for repositories, pull requests, and AI-assisted development workflows.

## One-line pitch

Sergeant is the model-free reviewer that checks whether code, claims, tests, architecture, and proof match before a project is merged or submitted, with optional owner-enabled model reasoning when extra semantic depth is wanted.

## Problem

AI builders can generate and patch software quickly, but teams still need an independent reviewer that can answer:

- What changed?
- What risk was introduced?
- Do the docs match the implementation?
- Are secrets or private boundaries exposed?
- Did the project prove what it claims?
- Should this change pass, need work, or be blocked?

Most coding assistants focus on writing code. Sergeant focuses on reviewing it.

## Solution

Sergeant analyzes a repository, diff, validated pull-request evidence, App Bridge event, or IDE handoff contract and produces:

```text
PASS
NEEDS WORK
BLOCK
```

The verdict is supported by evidence, affected files, risk level, confidence, assurance state, and next actions.

Sergeant deliberately avoids being a blind patch writer:

```text
Understand danger, but do not execute danger.
```

## Actual architecture

```text
Repository / changed files
        ↓
Deterministic evidence and bounded investigations
        ↓
Cpl coordinates the permanent officers
        ↓
Analyst + Challenger + Judge adjudication
        ↓
Hermes evidence ledger
        ↓
Sergeant verdict
```

This normal path is model-free. It does not require an AI login, hosted API, local model, large GPU, or multi-model council.

An owner may optionally enable one model or a bounded multi-model council for extra reasoning. Optional model evidence supports the permanent officers and enters the same Judge-admission boundary. It is not Sergeant's identity, dependency, or final authority.

## Completed proof

The current build includes:

- [x] Production-hardened GitHub read-only fetch
- [x] CLI integration
- [x] App Bridge integration
- [x] IDE Bench contract for VS Code, JetBrains, and AI handoff
- [x] Mocked and adversarial tests
- [x] CI and clean-clone proof
- [x] Battle-test framework and validators
- [x] Deterministic permanent-officer formation
- [x] Model-free multi-language assurance
- [x] Verified owner-controlled learning
- [x] Production sandbox and permission boundary
- [x] Real GitHub API ingestion proof
- [x] Sanitized proof artifacts
- [x] Optional one-model and multi-model comparison capability

## Capability tiers

| Tier | Capability | Purpose |
| --- | --- | --- |
| Tier 1 | Capability Engine | Baseline repo/diff review, evidence collection, and verdict generation. |
| Tier 2 | Review Intelligence | Better model-free reasoning over architecture, docs, risk, and expected behavior. |
| Tier 3 | Evidence Consensus | Reconcile evidence sources before making a decision. |
| Tier 4 | Verified Learning Loop | Learn only from accepted corrections and owner-approved proof. |
| Tier 5 | Graduation Benchmark | Decide when Sergeant is ready for harder review work. |
| Tier 6 | Squad Intelligence | Coordinate permanent officers without losing one final verdict. |
| Optional | Model Reasoning Support | Add one model or a bounded council when the owner requests extra reasoning. |
| Phase 7 | Production Hardening | Enforce sandbox, permission, token, identity, pagination, and leak boundaries. |

## What is genuinely proven

- Sergeant reviews repositories and diffs without a model route.
- Sergeant's permanent officers, Cpl coordination, Judge ledger, and verdict remain available offline.
- Sergeant runs through the CLI and App Bridge.
- Sergeant has an IDE Bench contract for IDE and AI handoff workflows.
- Sergeant has mocked, adversarial, CI, clean-clone, and installed-package proof.
- Sergeant has blind battle-test and multi-language benchmark structures.
- Secret detection is proven using planted temporary-file positive cases and clean controls.
- Live GitHub API ingestion is verified with GET-only requests and read-only workflow permissions.
- Uploaded proof records request evidence, counts, hashes, and identity metadata without comment bodies or credentials.
- Optional model reasoning can be measured as a delta over the model-free baseline.

## Accurate live-ingestion wording

```text
Sergeant performs production-hardened live GitHub read-only ingestion. It validates the requested repository and PR, refuses unsafe hosts, redirects, pagination, private evidence, and write-capable classic scopes, and produces a body-free proof artifact. Secret detection is proven with planted positive and clean-control cases.
```

Do not say that Sergeant writes GitHub reviews, applies patches, executes pull-request-controlled code, requires models, or automatically promotes learned rules. Those actions remain outside its authority.

## Why it matters

Sergeant strengthens an AI-built submission because it is proof infrastructure around fast software development. It shows that a project can:

- move quickly without pretending unproven claims are proven;
- review AI-generated code without depending on another AI model;
- distinguish implemented, tested, inferred, and pending work;
- enforce credential, token, permission, and sandbox boundaries;
- learn verified defect patterns under owner control;
- optionally request extra model reasoning without making it foundational.

## Demo story

```text
Repository or pull request
        ↓
Sergeant validates the boundary and collects evidence
        ↓
Cpl and permanent officers inspect code, tests, security, architecture, and experience
        ↓
Optional model support may deepen a named question when enabled
        ↓
Sergeant decides PASS / NEEDS WORK / BLOCK
        ↓
The builder fixes only what evidence supports
        ↓
Clean proof confirms the work
```

## Submission position

Sergeant should be presented as a working model-free reviewer and proof system that complements Hunter Foreman:

- Hunter Foreman coordinates business operations work.
- Sergeant verifies engineering work before trust, merge, or submission.
- Optional model routes are extra reasoning tools, not Sergeant's core.
