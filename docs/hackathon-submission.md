# Sergeant Hackathon Submission Brief

## Project

**Sergeant** — an evidence-based engineering reviewer for repositories, pull requests, and AI-assisted development workflows.

## One-line pitch

Sergeant is the reviewer that checks whether code, claims, tests, architecture, and proof match before a project is merged or submitted.

## Problem

AI builders can now generate and patch software quickly, but teams still need an independent reviewer that can answer:

- What changed?
- What risk was introduced?
- Do the docs match the implementation?
- Are secrets or private boundaries exposed?
- Did the project actually prove what it claims?
- Should this change pass, need work, or be blocked?

Most coding assistants focus on writing code. Sergeant focuses on reviewing it.

## Solution

Sergeant analyzes a repository, diff, pull request payload, app bridge event, or IDE handoff contract and produces a clear review verdict:

```text
PASS
NEEDS WORK
BLOCK
```

The verdict is supported by evidence, affected files, risk level, confidence, and next steps.

Sergeant deliberately avoids being a blind patch writer. It is built around a safety principle:

```text
Understand danger, but do not execute danger.
```

## Completed sprint proof

The current sprint completed the submission-critical reviewer stack:

- [x] Live GitHub read-only fetch
- [x] CLI integration
- [x] App Bridge integration
- [x] IDE Bench contract for VS Code, JetBrains, and AI handoff
- [x] Mocked tests
- [x] CI proof
- [x] Clean-clone proof
- [x] Battle-test framework
- [x] First benchmark: Requests-style repository review
- [x] Second benchmark: Flask architecture review
- [x] Battle-test validator
- [x] Release proof through pull request checks where CI and Main Review are green

## Capability tiers

| Tier | Capability | Purpose |
| --- | --- | --- |
| Tier 1 | Capability Engine | Baseline repo/diff review, evidence collection, and verdict generation. |
| Tier 2 | Review Intelligence | Better reasoning over architecture, docs, risk, and expected behavior. |
| Tier 3 | Evidence Consensus | Combine multiple evidence sources before making a decision. |
| Tier 4 | Verified Learning Loop | Learn from accepted corrections and owner-approved review lessons. |
| Tier 5 | Graduation Benchmark | Use benchmarks to decide when Sergeant is ready for harder review work. |
| Tier 6 | Squad Intelligence | Coordinate specialized review roles without losing one final verdict. |

## What is genuinely proven

- Sergeant can review repositories and diffs.
- Sergeant can run through the CLI.
- Sergeant can receive app bridge review events.
- Sergeant has a documented IDE Bench contract for IDE and AI handoff workflows.
- Sergeant has mocked tests and CI proof.
- Sergeant has clean-clone proof.
- Sergeant has battle-test benchmark structure and validator logic.
- Secret detection is proven using a real planted temporary-file positive case.
- GitHub PR comment payload ingestion is verified using a GitHub-shaped fixture.

## Claim correction

Do not overstate live GitHub ingestion.

Accurate wording:

```text
Sergeant supports live GitHub read-only fetch and can ingest GitHub-shaped PR comment payloads. Secret detection is proven with a real planted temp-file positive case. Full live GitHub API ingestion remains a separate proof step when token/network access is available.
```

Avoid saying:

```text
Live PR ingestion is fully verified against real PR #16.
```

unless a real GitHub API call is captured and documented as proof.

## Why it matters for the hackathon

Sergeant strengthens the full submission because it is not only an AI tool; it is proof infrastructure around AI-built systems.

It shows that the project can:

- move fast without pretending unproven claims are proven
- review AI-generated code before trusting it
- distinguish implemented, tested, inferred, and pending work
- enforce public/private and secret-safety boundaries
- support a finish-then-prove engineering workflow

## Demo story

```text
Repository or pull request
        ↓
Sergeant collects evidence
        ↓
Sergeant checks claims, code, tests, security, and architecture
        ↓
Sergeant decides PASS / NEEDS WORK / BLOCK
        ↓
The builder fixes only what evidence supports
        ↓
Clean proof and release proof confirm the work
```

## Submission position

Sergeant should be presented as a working reviewer/proof system that complements Hunter Foreman:

- Hunter Foreman coordinates business operations work.
- Sergeant verifies engineering work before trust, merge, or submission.

Together they show an AI infrastructure pattern where AI systems do work and another AI-assisted system reviews the evidence before the work is accepted.
