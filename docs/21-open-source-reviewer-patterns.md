# Open Source Reviewer Patterns

Main Review should learn from open-source reviewer designs without copying blindly.

This document captures patterns worth carrying forward from tools such as Qodo Merge / PR-Agent, reviewdog, Semgrep, CodeQL, and similar reviewer ecosystems.

## Pattern 1 — Separate evidence from verdict

Open-source review systems often emit diagnostics or suggestions first, then a later layer decides whether they are blocking.

Main Review follows this:

```text
Evidence Provider
  ↓
Finding
  ↓
Verdict Engine
```

## Pattern 2 — Normalize all external signals

Different tools produce different formats.

Main Review should normalize them into one internal shape:

- source
- body
- path
- line
- severity/classification
- tags
- evidence
- confidence

## Pattern 3 — Review comments need classification

A useful reviewer does not accept every comment as truth.

Every external finding must be classified:

- correct
- suggestion
- reject
- save_pattern
- unclassified

## Pattern 4 — Static inspection before execution

Security incidents involving AI/GitHub review bots show that execution of untrusted code is dangerous.

Main Review defaults to static inspection and must not execute project code unless an explicit sandbox policy exists.

## Pattern 5 — Batch learning is valuable

Reviewer output should not disappear after a PR closes.

Accepted comments should become future rules, lessons, or memory candidates.

## Pattern 6 — Tool output is not authority

CodeRabbit, Qodo, PR-Agent, reviewdog, Semgrep, CodeQL, and human reviewers can all be wrong.

The THETECHGUY standard treats them as evidence sources, not final judges.

## Pattern 7 — Explain why, not only what

A reviewer that only says "change this" is incomplete.

Main Review should preserve:

- comment
- reason
- evidence
- classification
- outcome

## Pattern 8 — Trust compounds through correction

Every rejected or accepted external finding is useful.

Accepted comments teach what to catch.

Rejected comments teach what not to over-enforce.
