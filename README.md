# Main Review R&D

This repository is the research and design home for the THETECHGUY/Hunter engineering reviewer.

The current working name is temporary. The repository may later be renamed to `main-review` or another final identity once the reviewer role and product name are locked.

## Mission

Build an independent engineering reviewer that learns from the best review systems but does not depend on CodeRabbit, Qodo, PR-Agent, or any single third-party product.

The reviewer is not a patch writer. It does not edit code by itself. Its job is to understand the repository, inspect a PR or change set, compare the work against project standards, and return one of three outcomes:

```text
PASS
NEEDS WORK
BLOCK
```

## Core principle

> The reviewer must understand danger, but must not execute danger.

This comes directly from the CodeRabbit/PwnedRabbit security lessons: reviewer systems become dangerous when they execute untrusted pull-request-controlled code, load untrusted tool configuration, or run with powerful secrets/tokens in the same environment.

## What this repo contains

```text
docs/
  00-product-brief.md
  01-research-sources.md
  02-coderabbit-lessons.md
  03-comparison-matrix.md
  04-architecture.md
  05-security-model.md
  06-review-verdicts.md
  07-identity-notes.md
  08-roadmap.md

.github/
  pull_request_template.md
```

## Intended product behavior

The reviewer should behave like the final engineering standard before merge:

- It understands code and architecture.
- It checks documentation, tests, public/private boundaries, security, maintainability, and project fit.
- It studies external systems for ideas but does not depend on them.
- It can use static analyzers as evidence, but it does not blindly trust them.
- It does not execute untrusted code unless isolated by a hardened sandbox.
- It does not hold write tokens during analysis.
- It gives clear reasons when it says `NEEDS WORK` or `BLOCK`.

## Research sources

Key starting references:

- Kudelski Security: CodeRabbit exploit technical write-up — https://kudelskisecurity.com/research/how-we-exploited-coderabbit-from-a-simple-pr-to-rce-and-write-access-on-1m-repositories
- Endor Labs: PwnedRabbit architectural lessons — https://www.endorlabs.com/learn/when-coderabbit-became-pwnedrabbit-a-cautionary-tale-for-every-github-app-vendor-and-their-customers
- CodeRabbit response — https://www.coderabbit.ai/blog/our-response-to-the-january-2025-kudelski-security-vulnerability-disclosure-action-and-continuous-improvement
- Qodo/PR-Agent open-source reviewer lineage — https://github.com/qodo-ai/pr-agent
- reviewdog — https://github.com/reviewdog/reviewdog
- Semgrep — https://semgrep.dev/
- CodeQL — https://codeql.github.com/

## Status

R&D foundation started. Implementation should not begin until the review model, trust boundary, and identity are clear enough to avoid building the wrong thing.