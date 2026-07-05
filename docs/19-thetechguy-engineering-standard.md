# THETECHGUY Engineering Standard v1

This standard applies to THETECHGUY projects, Hunter, Main Review, Code Ops, and future internal tools.

## 1. Finish, then prove

Complete the intended implementation first.

Then review it thoroughly.

Then freeze it.

Then perform clean-clone and runtime proof.

## 2. Code should justify execution

Do not run code hoping to discover whether it works.

Run it expecting it to work because reasoning, review, and implementation already support that conclusion.

If runtime exposes a fundamental flaw, review happened too late.

## 3. Claims must match implementation

Documentation, README claims, submission text, marketing, and implementation must describe the same system.

If docs say "AI reasoning" but the implementation is regex-only, that is a review finding before runtime testing.

## 4. Evidence before conclusions

Use live evidence:

- source code
- Git tree
- raw files
- tests
- CI logs
- runtime output
- external review comments

If sources conflict, report the conflict instead of guessing.

## 5. Tests are proof, not discovery

Tests should confirm engineering work.

Most issues found after this stage should be polish, edge cases, or UX improvements.

They should not be fundamental design surprises.

## 6. External reviewers are training material, not authority

CodeRabbit, Qodo, PR-Agent, reviewdog, GitHub Actions, and human comments can all provide value.

But every comment must be classified:

```text
🟢 Correct
🟡 Good suggestion
🔴 Reject
🧠 Save the pattern
```

Only comments that survive scrutiny become THETECHGUY reviewer memory.

## 7. The reviewer earns trust

A reviewer must never assume trust.

It earns trust by:

- collecting evidence
- explaining decisions
- accepting correction
- saving verified lessons
- improving future reviews

## 8. Humility is part of the system

The reviewer must be able to say:

> The evidence suggests this, but stronger evidence may change the conclusion.

That is not weakness.

That is how the system improves.

## 9. Do not assume; verify the real surface

Do not assume a feature is useful because code exists.

Verify the actual surface the user will touch:

- installed extension state
- visible IDE views
- command execution path
- output channel results
- repository status
- pushed GitHub state

If a screenshot, command result, or live file contradicts the claim, treat the contradiction as the next engineering task.
