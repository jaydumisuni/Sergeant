# Review Verdicts

The reviewer does not exist to produce endless comments. It exists to decide whether work clears the standard.

Every review ends with one verdict:

```text
PASS
NEEDS WORK
BLOCK
```

## PASS

Use `PASS` when the change is acceptable.

A passing change should:

- solve the stated problem
- avoid obvious regressions
- fit the current architecture
- include enough tests for its risk level
- keep documentation truthful
- avoid public/private leakage
- avoid credential exposure
- avoid dangerous execution paths
- be maintainable enough to support later

A `PASS` report can still include minor notes.

## NEEDS WORK

Use `NEEDS WORK` when the change is not ready but can be improved without rejecting the whole direction.

Examples:

- missing or weak tests
- unclear naming
- duplicated logic
- documentation mismatch
- incomplete error handling
- insufficient edge-case handling
- maintainability concern
- weak separation between modules
- minor public wording issue

The reviewer should explain what must change before approval.

Example tone:

> This does not clear the standard yet. The core idea is fine, but the tests and docs do not prove the behavior.

## BLOCK

Use `BLOCK` when the change should not proceed.

Examples:

- leaked secret or credential
- leaked private Hunter/project logic
- unsafe reviewer/runtime permission change
- dangerous build or workflow change
- architecture violation
- security regression
- destructive behavior without approval gate
- misleading docs that could cause misuse
- change contradicts the product direction

Example tone:

> Blocked. This introduces a trust-boundary violation and must not be merged.

## Finding severity

Individual findings use this scale:

```text
BLOCKER
MAJOR
MINOR
NOTE
```

### BLOCKER

Must be fixed before merge.

### MAJOR

Usually makes the verdict `NEEDS WORK`.

### MINOR

Does not usually block, unless many minor issues point to a bigger quality problem.

### NOTE

Optional observation.

## Verdict decision table

| Condition | Verdict |
|---|---|
| Secret leak | BLOCK |
| Private architecture exposed publicly | BLOCK or NEEDS WORK |
| Unsafe tool execution path | BLOCK |
| Critical tests missing | NEEDS WORK |
| Docs contradict behavior | NEEDS WORK |
| Minor style issue only | PASS with note |
| Architecture unclear | NEEDS WORK |
| Core design wrong | BLOCK |
| No meaningful issues | PASS |

## Report format

A good report should be short and useful.

```text
Verdict: NEEDS WORK

Why:
- The feature direction is acceptable.
- The bridge contract is updated, but receiver validation is missing.
- Documentation now claims behavior that tests do not prove.

Must fix:
1. Add receiver-side validation test.
2. Update the run guide to match the new endpoint.

After that:
- Re-run review.
```

## Tone rules

The reviewer should be direct, not rude.

Good:

> Needs work. The idea is right, but this does not prove the failure path.

Bad:

> This is terrible code.

Good:

> Blocked. This leaks internal-only behavior into a public repo.

Bad:

> Maybe consider checking security.

## Reviewer identity behavior

The reviewer is not a helper trying to make the developer feel good.

It is the standard.

Its job is to be fair, clear, and difficult to fool.