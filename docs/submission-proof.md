# Sergeant Submission Proof

This file is the submission proof checklist for Sergeant.

## Current status

```text
Status: submission-support ready
Code proof: complete for current sprint
Release proof: complete through PR checks
Remaining proof: live GitHub API ingestion evidence, if claiming real live PR ingestion
```

## Sprint checklist

- [x] Live GitHub read-only fetch
- [x] CLI integration
- [x] App Bridge integration
- [x] IDE Bench contract for VS Code, JetBrains, and AI handoff
- [x] Mocked tests
- [x] CI proof
- [x] Clean-clone proof
- [x] Battle-test framework
- [x] First benchmark: Requests
- [x] Second benchmark: Flask architecture
- [x] Battle-test validator
- [x] Release proof via pull request where CI and Main Review are green

## Proof categories

### 1. Local reviewer proof

Pass criteria:

- repository review runs from CLI
- diff/PR review produces a verdict
- verdict is one of `PASS`, `NEEDS WORK`, or `BLOCK`
- report includes evidence and reasoning

### 2. GitHub read-only proof

Pass criteria:

- GitHub data is fetched without write permissions
- token scope stays read-only for analysis
- untrusted PR code is not executed
- PR comment payload parsing is verified

Current caveat:

```text
A GitHub-shaped fixture verifies PR comment ingestion shape. Full live PR API ingestion should be captured separately before claiming it as fully verified live.
```

### 3. Secret detection proof

Pass criteria:

- a planted temp-file positive case is detected
- the finding is blocker/severe enough to stop a risky merge
- the test does not commit a real secret

Current state:

```text
Secret detection is genuinely proven with a real temporary test file containing a synthetic secret-shaped value.
```

### 4. App Bridge proof

Pass criteria:

- external systems can hand a review request to Sergeant
- request contract is stable
- output remains a review verdict, not a patch execution request

### 5. IDE Bench proof

Pass criteria:

- contract supports VS Code style handoff
- contract supports JetBrains style handoff
- contract supports AI tool handoff
- the IDE path remains evidence/report oriented

### 6. Battle-test proof

Pass criteria:

- benchmark cases exist
- validator confirms expected risk/verdict behavior
- Requests-style benchmark is covered
- Flask architecture benchmark is covered

## Claim wording rules

Use this wording:

```text
Sergeant supports live GitHub read-only fetch, CLI review, app bridge review handoff, IDE Bench contracts, battle-test benchmarks, CI proof, clean-clone proof, and release proof. Secret detection is proven with a planted temp-file positive case. PR comment ingestion is proven against GitHub-shaped payload fixtures, with full live GitHub API ingestion reserved for the next evidence capture.
```

Do not use this wording yet:

```text
Sergeant fully verified live PR ingestion against real PR #16.
```

unless live API evidence is captured.

## Final submission role

Sergeant should be included as a trust/proof layer in the hackathon submission:

```text
Sergeant is the reviewer that verifies claims, code, tests, risk, and proof before accepting a merge or submission.
```

It should support the main submission narrative without stealing the center from Hunter Foreman.
