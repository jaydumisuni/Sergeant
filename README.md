# Sergeant

Sergeant is the THETECHGUY/Hunter engineering reviewer.

It is not a patch writer. It does not edit code by itself. Its job is to understand a repository, inspect a pull request or change set, compare the work against project standards, and return one of three outcomes:

```text
PASS
NEEDS WORK
BLOCK
```

## Role inside Hunter

Hunter is the wider engineering brain and orchestrator.

Sergeant is Hunter's engineering review division:

- it inspects before merge
- it challenges assumptions
- it compares claims against implementation
- it checks tests, documentation, boundaries, security, maintainability, and project fit
- it learns from accepted reviewer and human feedback
- it treats CodeRabbit, Qodo, PR-Agent, reviewdog, Semgrep, and CodeQL as optional evidence sources, not authorities

## Core principle

> The reviewer must understand danger, but must not execute danger.

This comes directly from the CodeRabbit/PwnedRabbit security lessons: reviewer systems become dangerous when they execute untrusted pull-request-controlled code, load untrusted tool configuration, or run with powerful secrets/tokens in the same environment.

## Status

Sergeant's v1 foundation is implemented and self-verifying.

The current self-check target is:

```bash
main-review verify-standard --pretty
```

A complete self-check returns:

```json
{
  "status": "verified",
  "next_actions": []
}
```

## Intended product behavior

Sergeant should behave like the final engineering standard before merge:

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
