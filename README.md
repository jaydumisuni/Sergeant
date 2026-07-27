<p align="center">
  <img src="resources/readme-top-image.png" alt="Sergeant - open-source engineering reviewer" width="960">
</p>

# Sergeant

**Sergeant (SRG)** is an open-source software engineering review system created by **THETECHGUY DIGITAL SOLUTIONS**.

Sergeant inspects repositories, reviews pull requests, verifies engineering standards, and produces evidence-based reports. It is not a one-shot coding assistant. It is the reviewer that challenges assumptions, checks proof, and reports what remains before merge or release.

```text
PASS
NEEDS WORK
BLOCK
```

## What Sergeant actually uses

Sergeant's normal review system is **model-free**.

```text
Repository / changed files
        ↓
Deterministic evidence and bounded field investigations
        ↓
Cpl coordinates the permanent officers
        ↓
Analyst reconciliation
        ↓
Challenger falsification
        ↓
Judge admission ledger
        ↓
Hermes evidence delivery
        ↓
Sergeant verdict
```

The permanent officers, Cpl coordination, learned deterministic rules, assurance gates, evidence admission, and final verdict do not require:

- an AI-provider login;
- a hosted inference API;
- a local language model;
- a large GPU;
- a multi-model council.

Models are an **optional extra-reasoning capability**. When an owner explicitly enables one model or a bounded multi-model council, that output supports the existing officers and enters the same evidence and Judge-admission boundary. It does not create Sergeant's officers, vote directly on the verdict, promote learning automatically, or become final authority.

See [`docs/55-model-free-core-and-optional-model-reasoning.md`](docs/55-model-free-core-and-optional-model-reasoning.md).

## Command relationship

```text
Owner
→ Sergeant
→ Cpl
→ permanent officers
→ deterministic tools, scanners, tests, and workspace evidence
→ optional model support when explicitly enabled
```

**Sergeant Main Review is the reviewer core. Cpl — Corporal Specialist — coordinates the permanent-officer formation.** Models and gateways are replaceable support engines beneath that formation, not the product identity and not a hidden dependency.

Deterministic tests, runtime proof, explicit contracts, and verified repository facts outrank unsupported model opinion. Every accepted blocker or major finding must remain grounded in supplied repository evidence.

## Permanent officers

Every independent review returns the permanent formation:

| Officer | Responsibility |
| --- | --- |
| Quartermaster | Capacity, model-support state, and execution boundary |
| Scout | Scope, language, manifests, tests, CI, and coverage |
| Engineer | Correctness, architecture, contracts, cross-file behavior, and proof impact |
| Medic | Security boundaries, tainted data, unsafe file access, secrets, and recovery |
| Mechanic | Runtime state, concurrency, lifecycle, and performance |
| Analyst | Root-cause reconciliation |
| Challenger | Falsifiers and adversarial challenge |
| Archivist | Evidence disposition for governed learning |
| Judge | Admission, advisory, rejection, and assurance disposition |
| Hermes | Canonical evidence and transaction delivery |

Models may attach optional evidence to the responsible officer packet. They never replace an officer.

## Who Sergeant is for

- Individual developers who want a second engineering review before shipping.
- Open-source maintainers reviewing pull requests and project changes.
- Teams that care about standards, evidence, and repeatable review flow.
- AI-assisted development workflows where generated code still needs independent review.
- Self-hosted and offline environments that should not depend on one provider.

## Core principles

- **Evidence before opinion.**
- **Standards before assumptions.**
- **Review before merge.**
- **Verification before release.**
- **Human judgment remains final.**
- **Finish, then prove.**
- **Claims must match implementation.**

## Engineering workflow

```text
Understand
    ↓
Build
    ↓
Review
    ↓
Freeze
    ↓
Prove
    ↓
Submit / Ship
```

## Current capability set

### Model-free review core

- Repository inspection and understanding.
- Pull-request, current-file, and changed-file review.
- Architecture and regression-risk checks.
- Static analysis and security signals.
- Documentation-drift checks.
- Deterministic permanent-officer formation.
- Evidence consensus and standards verification.
- Verified learning and reusable model-free lessons.
- Multi-language blind assurance with clean controls.

### Optional extra reasoning

- One explicitly configured model can deepen a named investigation.
- A bounded multi-model council can provide independent reasoning when the owner enables it.
- Local Cpl gateway, Ollama, LM Studio, Cloudflare Workers AI, or an explicit OpenAI-compatible endpoint.
- Model findings are reconciled against deterministic evidence before they can affect the action gate.
- Provider failures reduce optional amplification without removing Sergeant's core formation.

### Developer workflow

- CLI review flow.
- App Bridge contract.
- IDE Bench contract for VS Code, PyCharm, JetBrains, and AI handoff.
- VS Code Command Center.
- JetBrains Command Center preview.
- Read-only GitHub PR-comment ingestion.
- Live GitHub review bridge.

### Proof and battle validation

- Battle-test fixtures and validator.
- Static review-signal comparison.
- Live PR-patch fetch for battle comparison.
- CI and clean-clone proof.
- Browser-rendered Command Center proof at desktop and compact IDE widths.
- PyPI wheel/source validation, VSIX packaging, and JetBrains plugin packaging.

## Installation

### Python / CLI

Published stable package:

```bash
python -m pip install sergeant-reviewer==0.4.1
```

Current source development:

```bash
git clone https://github.com/jaydumisuni/Sergeant.git
cd Sergeant
python -m pip install -e .
```

Requires Python 3.10 or newer.

### VS Code

Install Sergeant from the Visual Studio Marketplace or Open VSX. For a local package:

```bash
npx @vscode/vsce package --no-dependencies
code --install-extension sergeant-reviewer-0.4.1.vsix --force
```

Open **Sergeant** from the activity bar, then choose **Open Full Command Center**.

### JetBrains IDEs

Install the Sergeant CLI first:

```bash
python -m pip install sergeant-reviewer==0.4.1
```

Set `SERGEANT_CLI` when the executable is not on the IDE process path.

## Quick start

### Normal independent review — no model required

```bash
sergeant review . --pretty
sergeant pr-review . --pretty
```

Review explicit files:

```bash
sergeant pr-review . --files "src/app.py,tests/test_app.py" --pretty
```

### Optional one-model reasoning

The user must deliberately enable model support:

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=preferred
export SERGEANT_CPL_PROVIDER=ollama
export SERGEANT_CPL_MODEL=qwen3-coder-next
sergeant pr-review . --pretty
```

### Optional multi-model reasoning

A multi-model council is an extra capability for owners who want more independent reasoning. Configure an explicit provider roster, then enable Cpl support. It is not required for normal Sergeant review.

Cloudflare setup and proof are documented in [`docs/25-cloudflare-workers-ai.md`](docs/25-cloudflare-workers-ai.md).

### Strict owner-selected model gate

For a release where the owner explicitly requires model reasoning:

```bash
export SERGEANT_CPL_ENABLED=true
export SERGEANT_CPL_POLICY=required
export SERGEANT_CPL_DEPTH=maximum
sergeant pr-review . --pretty
```

That is a chosen mission policy—not Sergeant's default architecture and not a promise of perfect defect detection.

## Model configuration

```text
SERGEANT_CPL_ENABLED=false|true
SERGEANT_CPL_POLICY=disabled|preferred|required
SERGEANT_CPL_PROVIDER=disabled|auto|cpl|ollama|lm-studio|configured|cloudflare
SERGEANT_CPL_BASE_URL=<explicit /v1 endpoint>
SERGEANT_CPL_MODEL=<provider model slug>
SERGEANT_CPL_PROTOCOL=auto|responses|chat_completions
SERGEANT_CPL_DEPTH=adaptive|deep|maximum|single
SERGEANT_CPL_MAX_PASSES=3
SERGEANT_CPL_API_KEY=<runtime secret>
```

The earlier `SERGEANT_LLM_*` variables and `llm-status` command remain compatibility aliases for 0.4.0 integrations. New configuration should use Cpl naming.

## Sergeant Command Center

The VS Code extension provides a compact activity-bar launcher and a full editor Command Center. The JetBrains preview uses the same interface through JCEF and falls back to a native Swing panel when JCEF is unavailable.

The interface includes:

- Commander dashboard and live workspace state.
- Mission Planner.
- Permanent-officer deployment and evidence views.
- Evidence Locker and report history.
- Settings for optional model reasoning.
- One-active-mission gates in both VS Code and JetBrains.

### Writer safety boundary

- Disabled by default.
- Draft patches only.
- Human approval required.
- Never auto-merge.

## Safety boundary

Sergeant refuses to:

- execute untrusted pull-request-controlled code;
- run shell commands supplied by PR content;
- automatically modify project code;
- write or merge patches as part of review;
- use privileged write tokens during analysis;
- silently fake success after a failed live fetch;
- treat Cpl, any model, or an external reviewer as final authority;
- auto-discover remote model endpoints;
- emit model API keys in status or reports;
- automatically promote a learned rule.

## Proof and learning

Sergeant's learning path is governed:

```text
verified defective/fixing lineage
→ frozen blind review
→ generalized rule
→ positive and clean controls
→ unrelated transfer
→ hidden holdout
→ owner-controlled admission
```

Automatic promotion and automatic merge remain forbidden.

## Documentation

- [`docs/44-deterministic-permanent-officer-formation.md`](docs/44-deterministic-permanent-officer-formation.md) — canonical model-free officer formation.
- [`docs/45-model-free-multilanguage-assurance.md`](docs/45-model-free-multilanguage-assurance.md) — model-free language proof.
- [`docs/55-model-free-core-and-optional-model-reasoning.md`](docs/55-model-free-core-and-optional-model-reasoning.md) — current product boundary.
- [`docs/22-semantic-open-model-review.md`](docs/22-semantic-open-model-review.md) — optional model-support configuration.
- [`docs/39-review-intelligence-proof.md`](docs/39-review-intelligence-proof.md) — blind reviewer-intelligence proof.

## Public boundary

This repository contains reusable review infrastructure. Private project rules, customer evidence, deployment secrets, and write-token operations do not belong in the public repository.

## Contributing

Contributions, issue reports, feature requests, and engineering discussions are welcome. Sergeant values evidence-based changes, reproducible results, clear reasoning, respect for existing architecture, standards compliance, and useful signals over noisy output.

## Identity

Sergeant / SRG is created by **THETECHGUY DIGITAL SOLUTIONS**.

> Observe. Analyze. Verify.
