# CodeRabbit / PwnedRabbit Lessons

This document captures the CodeRabbit lessons that matter for our reviewer design.

Primary sources:

- Kudelski Security original write-up: https://kudelskisecurity.com/research/how-we-exploited-coderabbit-from-a-simple-pr-to-rce-and-write-access-on-1m-repositories
- Endor Labs analysis: https://www.endorlabs.com/learn/when-coderabbit-became-pwnedrabbit-a-cautionary-tale-for-every-github-app-vendor-and-their-customers
- CodeRabbit response: https://www.coderabbit.ai/blog/our-response-to-the-january-2025-kudelski-security-vulnerability-disclosure-action-and-continuous-improvement

## What CodeRabbit proved works

CodeRabbit proved there is real market value in automated PR review.

Developers pay because it can:

- read pull requests quickly
- summarize changes
- leave comments in familiar GitHub review flow
- notice common issues
- integrate with linters/static analyzers
- reduce manual review load
- act as a second set of eyes

The lesson is not that we should depend on CodeRabbit. The lesson is that developers value an always-available reviewer that speaks inside their existing PR workflow.

## What went wrong

The core failure pattern was not simply “AI made a bad comment.”

The dangerous pattern was:

```text
Untrusted PR input
  -> reviewer/tool execution path
  -> privileged runtime/secrets
  -> broader GitHub App access risk
```

The review system reportedly encountered malicious PR-controlled configuration and execution behavior. The key design failure was allowing untrusted repository-controlled inputs to influence execution inside an environment that had access to secrets and privileged credentials.

## Critical lessons

### 1. Do not trust PR-controlled configuration

A pull request can change configuration files, tool settings, build scripts, package manifests, lint configs, CI files, and instructions.

The reviewer must treat all PR-controlled configuration as hostile until proven safe.

### 2. Detection is not protection

If the reviewer says “this PR is suspicious” but still executes the dangerous path, it has failed.

The safety engine must block execution before analysis tools run.

### 3. Analysis and write access must be separated

A review worker should not hold repository write privileges.

Preferred pattern:

```text
Read-only collector
  -> isolated analysis worker
  -> verdict/report artifact
  -> separate limited GitHub comment poster
```

### 4. Secrets must not live inside analyzers

An analyzer that runs tools against untrusted code must not have access to:

- GitHub App private keys
- installation write tokens
- cloud provider credentials
- production database credentials
- deployment secrets
- user OAuth tokens

### 5. Sandboxing is mandatory

Any tool execution must happen in a disposable sandbox with:

- no secrets
- no write token
- no production network
- strict timeout
- limited filesystem
- limited CPU/RAM
- clean teardown

### 6. External tools are evidence, not authority

Linters, RuboCop-like tools, Semgrep, CodeQL, and other tools can provide evidence. But the reviewer must decide when running them is safe and whether their findings matter.

### 7. Reviewers need threat models

A reviewer is not only a developer productivity tool. It is also a GitHub App, a CI-style runner, and a supply-chain attack surface.

That means it needs a threat model from day one.

## What we should copy as principles

Not code. Not branding.

Principles worth carrying forward:

- PR-native workflow.
- Clear summary before comments.
- Low-noise review comments.
- Useful prioritization.
- Pull request context.
- Tool evidence combined with AI reasoning.
- Human-readable final verdict.

## What we must avoid

- Running untrusted PR code with secrets.
- Letting PR-controlled config decide analyzer behavior.
- Giving the same worker analysis and write permissions.
- Posting many low-value comments.
- Treating AI confidence as proof.
- Treating static analyzer output as final truth.
- Hiding the reason for a block.

## Main Review rule

```text
Review first.
Execute only if safe.
Comment only with limited permission.
Never analyze with write power.
```

## Security posture for our reviewer

The default state must be defensive:

```text
Unknown input = untrusted
Unknown config = ignored or sandboxed
Unknown execution = blocked
Unknown secret access = forbidden
Unknown risk = NEEDS WORK or BLOCK
```

## Final design conclusion

The reviewer must be built as a gatekeeper, not a helper that blindly follows repo instructions.

Its most important sentence is:

> This is not safe or not good enough. Try again.