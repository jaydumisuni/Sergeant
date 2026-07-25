# Retired PR Harvest Visual Verification — 2026-07-25

This record closes the visual-verification gap for PR #145. It is evidence of inspection, not a replacement for the accepted lesson records, governed candidates, tests, or exact-head workflow proof.

## Scope

Every file changed by PR #145 was included:

- `.github/self-learning/lessons/cpl-adjudication-noise-20260724.json`;
- `.github/self-learning/lessons/review-evidence-integrity-20260724.json`;
- `.github/self-learning/lessons/preserve-before-delete-20260724.json`;
- `.github/self-learning/retrospective-candidates-20260724.json`;
- `docs/52-open-pr-closure-and-branch-retirement.md`;
- `docs/53-retired-pr-lesson-harvest.md`;
- `tests/test_retired_pr_lesson_harvest.py`.

The inspected source was current `main` after PR #145 merged as `e7d0e99e8e3ef14d98707b60959c50748355726c`.

## Machine checks before rendering

- all four JSON records parsed successfully;
- `tests/test_retired_pr_lesson_harvest.py` compiled successfully;
- the rendered audit represented all seven changed files;
- the structured dashboard contained exactly three accepted lessons and seven governed candidates.

## Visual render matrix

| View | Width × initial height | Result |
|---|---:|---|
| Retirement document 52 — desktop | 1600 × 1200 | PASS |
| Retirement document 52 — mobile | 390 × 844 | PASS |
| Lesson-harvest document 53 — desktop | 1600 × 1200 | PASS |
| Lesson-harvest document 53 — mobile | 390 × 844 | PASS |
| Accepted-lesson/candidate dashboard — desktop | 1600 × 1200 | PASS |
| Accepted-lesson/candidate dashboard — mobile | 390 × 844 | PASS |
| JSON and Python syntax audit — desktop | 1600 × 1200 | PASS |
| JSON and Python syntax audit — mobile | 390 × 844 | PASS |

## Inspected visual boundaries

The render inspection verified:

- headings, paragraphs, lists, blockquotes, inline code, code blocks, and the PR-disposition table render in the intended order;
- no document-wide horizontal overflow occurs at either viewport;
- long tables and source-code blocks remain bounded or horizontally scrollable rather than overlapping surrounding content;
- long commit SHAs, file paths, and lesson IDs wrap without covering adjacent text;
- the three accepted lessons are visibly distinct from the seven `needs_lineage` / `benchmark_only` candidates;
- the PR #106/#107 original/replacement lineage is visible in both documentation and structured candidate evidence;
- zero automatic promotions, zero automatic merges, and Sergeant final authority remain visible;
- no accepted lesson is visually represented as an unresolved candidate, and no governed candidate is represented as accepted.

## Correction found during visual review

The first merged version of the retirement documents described deletion authorization only as a future condition. Because PR #145 had already merged, that wording was stale and could leave the reader unsure whether the gate had actually closed.

The same verification pass therefore updated documents 52 and 53 to record:

- PR #145 exact reviewed head `62691d0d1f99491f3440a52702a5dd5487bc8b6a`;
- merge commit `e7d0e99e8e3ef14d98707b60959c50748355726c`;
- the successful proof matrix;
- explicit authorization to delete the enumerated PR-backed historical branches;
- the requirement to inspect any branch that never had a PR separately.

## Render evidence identifiers

A local visual package containing eight full-page screenshots, four rendered HTML views, a structured dashboard, and the syntax audit was generated during this verification.

```text
package size: 4,701,909 bytes
package SHA-256: 6a9b466a09f497920e545f9bbc665e540c5aa48405fd5bcf71d3105316947c65
visual collage SHA-256: 64e219bc065767e032d98439eb7547ed60adf625c6af4a732ec623981e9bbb3e
```

The repository documents and tests remain the authority. These hashes identify the render evidence inspected in this session; they do not authorize deletion of any branch outside the enumerated PR-backed set.

## Verdict

```text
PR #145 source and structured records: PASS
Desktop render: PASS
390 × 844 mobile render: PASS
Accepted/candidate visual separation: PASS
Overflow and overlap inspection: PASS
Post-merge deletion-state wording: CORRECTED
Unknown branch-only work: REQUIRES SEPARATE INSPECTION
```