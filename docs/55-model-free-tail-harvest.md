# Model-Free Product-Tail Harvest — 2026-07-27

## Purpose

PR #152 corrected Sergeant's primary product boundary and runtime defaults: normal review is model-free, while one-model or bounded multi-model reasoning is optional user-enabled support beneath Cpl.

Two earlier draft attempts, PRs #151 and #154, remained open after that merge. They were not closed immediately because branch cleanup must first inspect and harvest any unique useful work.

## Accepted lesson

The retrospective lesson is recorded at:

```text
.github/self-learning/lessons/product-identity-runtime-consistency-20260727.json
```

Generalized rule:

> Public identity, runtime defaults, IDE defaults, package metadata, persistent agent instructions, submission claims, and proof language must describe the same operational boundary. An optional capability must not be presented or configured as a default dependency. Clean configuration must fail closed, while explicit user opt-in remains supported without transferring authority.

## Useful work harvested

The following useful changes existed outside the merged PR #152 surface and were carried forward from current `main` rather than merging either stale draft branch:

- `CLAUDE.md` and `.github/copilot-instructions.md` now preserve the model-free product boundary for future AI workers;
- `pyproject.toml` and JetBrains `plugin.xml` now describe the published product accurately;
- `SUBMISSION_READY.md` and `docs/hackathon-submission.md` no longer present Cpl council reasoning as a core dependency;
- the Cpl noise-governor document is explicitly scoped to optional model evidence;
- the reviewer-intelligence proof identifies deterministic/model-free mode as the canonical Sergeant benchmark and one-model/council modes as optional comparisons;
- the Cloudflare council document requires deliberate activation and states that credentials alone do not enable model calls;
- regression tests bind these persistent, distribution, submission, and proof surfaces to the same product truth.

## Rejected or superseded work

### Duplicate canonical document

PRs #151 and #154 both proposed `docs/55-model-free-core-and-optional-model-reasoning.md`. PR #152 already merged the canonical boundary as `docs/54-model-free-core-and-optional-reasoning.md`. A second canonical document would create drift, so it was not added.

### Import-time environment mutation

PR #154 proposed setting `SERGEANT_CPL_ENABLED=false` during `main_review` package import. This was rejected because library import must not mutate process environment. PR #152 already implements the safer boundary inside `LLMSettings.from_environment()`:

- clean configuration resolves to disabled;
- credentials alone do not opt in;
- explicit enablement and explicit routes remain supported.

### Duplicate visual workflow

PR #151 proposed another heavyweight Markdown and Command Center visual workflow. PR #152 already added focused Command Center visual contracts and passed desktop and compact browser-rendered Multiplatform Proof. The duplicate workflow would consume additional Actions storage and compute without adding a new product mechanism, so it was not merged.

### Stale branch integration

Both draft branches were based on the pre-PR-152 `main` head and contain overlapping rewrites. Their useful changes were harvested selectively; their complete branch histories are not integration truth.

## Pull-request dispositions

### PR #151

- **Disposition:** duplicate / superseded after selective harvest.
- **Useful value retained:** persistent AI-worker doctrine and the principle that product-identity changes need visual confirmation.
- **Not merged:** duplicate canonical document, duplicate visual workflow, and overlapping stale rewrites.

### PR #154

- **Disposition:** duplicate / superseded after selective harvest.
- **Useful value retained:** package and JetBrains metadata, submission wording, optional-support documentation, and distribution-surface regressions.
- **Not merged:** import-time environment mutation, duplicate canonical document, and stale overlapping implementation.

## Deletion boundary

PRs #151 and #154 may be closed only after this harvest PR:

1. passes CI and clean-clone proof;
2. passes Main Review and the normal proof matrix;
3. verifies the accepted lesson record and product-contract regressions;
4. merges into `main`.

After that merge, branches `docs/model-free-core-optional-reasoning`, `correct/model-free-product-boundary`, `fix/model-free-default-and-docs`, and this harvest branch are safe to delete. No useful product truth will remain branch-only.

Automatic lesson promotion and automatic merge remain forbidden. Sergeant remains final authority.
