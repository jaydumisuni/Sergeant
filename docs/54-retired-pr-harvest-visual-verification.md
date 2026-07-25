# Retired PR Harvest Visual Verification — 2026-07-25

This record closes the visual-verification gap for PR #145. It is evidence of human-visible render inspection, not a replacement for the accepted lesson records, governed candidates, tests, or exact-head workflow proof.

## Scope

Every file changed by PR #145 was included:

- `.github/self-learning/lessons/cpl-adjudication-noise-20260724.json`;
- `.github/self-learning/lessons/review-evidence-integrity-20260724.json`;
- `.github/self-learning/lessons/preserve-before-delete-20260724.json`;
- `.github/self-learning/retrospective-candidates-20260724.json`;
- `docs/52-open-pr-closure-and-branch-retirement.md`;
- `docs/53-retired-pr-lesson-harvest.md`;
- `tests/test_retired_pr_lesson_harvest.py`.

The inspected authority began from `main` after PR #145 merged as `e7d0e99e8e3ef14d98707b60959c50748355726c`. The first visual-verification record entered `main` afterward, but this correction supersedes its mobile-readability verdict because the rendered 390-pixel evidence exposed compressed tables that were present yet not comfortably usable.

## Machine checks before rendering

- all four JSON records parsed successfully;
- `tests/test_retired_pr_lesson_harvest.py` compiled successfully;
- the syntax audit represented all seven PR #145 files;
- the structured dashboard contained exactly three accepted lessons and seven governed candidates;
- accepted lessons remained distinct from `needs_lineage` and `benchmark_only` records;
- automatic promotions and automatic merges remained zero.

## Visual render matrix

The matrix is written as responsive records so the proof document itself remains readable at 390 pixels.

### Retirement document 52

- **Desktop viewport:** 1600 × 1200 — PASS
- **Mobile viewport:** 390 × 844 — PASS

### Lesson-harvest document 53

- **Desktop viewport:** 1600 × 1200 — PASS after repair
- **Mobile viewport:** 390 × 844 — PASS after repair

### Accepted-lesson and candidate dashboard

- **Desktop viewport:** 1600 × 1200 — PASS
- **Mobile viewport:** 390 × 844 — PASS after responsive-card repair

### JSON and Python syntax audit

- **Desktop viewport:** 1600 × 1200 — PASS
- **Mobile viewport:** 390 × 844 — PASS

The proof document itself was rendered separately at both viewports after its final wording was frozen. It is intentionally excluded from the core package hash below so the evidence record does not attempt to contain a hash of itself.

## Visual defects found and repaired

The first render exposed a real mobile-readability failure: the three-column PR-disposition table in document 53 compressed into narrow columns at 390 pixels. The information technically remained present, but the table was not comfortably readable and therefore did not meet the THETECHGUY visual standard.

The repair replaced that wide table with responsive per-PR records containing explicit **Disposition** and **Reason** fields. The structured dashboard used for visual cross-checking was also changed from a clipped mobile table to stacked labelled candidate cards. The complete render matrix was regenerated after both repairs.

The proof document's own render matrix was then visually inspected. Its original table was readable but unnecessarily compressed on mobile, so it was also converted into responsive records before final verification.

This correction demonstrates the required rule:

> A green test or present source string does not prove visual usability. Inspect the rendered target viewport, repair what is actually visible, then rerender.

## Inspected visual boundaries

The corrected render inspection verified:

- headings, paragraphs, lists, blockquotes, inline code, and code blocks appear in their intended order;
- no document-wide horizontal overflow occurs at either viewport;
- long source-code blocks remain bounded and horizontally scrollable rather than overlapping surrounding content;
- long commit SHAs, file paths, and lesson IDs wrap without covering adjacent text;
- all PR dispositions are readable without a wide table on mobile;
- the visual proof matrix is readable without a wide table on mobile;
- the three accepted lessons are visibly distinct from the seven governed candidates;
- the PR #106/#107 original/replacement lineage remains visible in documentation and structured evidence;
- zero automatic promotions, zero automatic merges, and Sergeant final authority remain visible;
- no accepted lesson is visually represented as unresolved, and no governed candidate is represented as accepted.

## Post-merge wording correction

The first merged version of the retirement documents described deletion authorization only as a future condition. Because PR #145 had already merged, that wording was stale and could leave the reader unsure whether the gate had actually closed.

The verification pass updated documents 52 and 53 to record:

- PR #145 exact reviewed head `62691d0d1f99491f3440a52702a5dd5487bc8b6a`;
- merge commit `e7d0e99e8e3ef14d98707b60959c50748355726c`;
- the successful proof matrix;
- explicit authorization to delete the enumerated PR-backed historical branches;
- the requirement to inspect any branch that never had a PR separately.

## Corrected render evidence identifiers

The stable core package contains the four authoritative rendered views—documents 52 and 53, the accepted/candidate dashboard, and the JSON/Python syntax audit—at desktop and mobile sizes. The proof document is excluded from this package to avoid a self-referential digest.

```text
core package size: 5,934,676 bytes
core package SHA-256: 73c8bcb798a02cf1cc25c86b3e959fdfa6b7476d98f6e2c31dd39a7f7e39dccb
full core collage size: 546,015 bytes
full core collage SHA-256: 8370677def147d099f4ddaa064ae3334707f6e001e29152e9847416dd7bff6b1
review collage size: 97,059 bytes
review collage SHA-256: e1d4dd9db87bbcb20c4a7ab06c873aced9e7afc5555db67d92946dffc8bda211
```

The exact review collage replaced the earlier Drive evidence in place:

```text
Drive folder ID: 1ooIA_u_1MVmNO-GgdwWTOIg3fSvdosR4
Drive file ID: 1HWOLOtAnNBeL073Az0qnGOzp4LPNxQer
Drive file name: pr149-visual-verification-evidence-exact.jpg
size: 97,059 bytes
SHA-256: e1d4dd9db87bbcb20c4a7ab06c873aced9e7afc5555db67d92946dffc8bda211
```

The Drive file was downloaded again after replacement. The recovery copy matched the exact local collage at the byte length, SHA-256 digest, and raw bytes.

### Superseded intermediate evidence

The earlier correction attempt remains recorded as lineage, but it is not the final visual authority:

```text
intermediate package SHA-256: d93bb4214daa1cb0d86be06bb473cfbc7fe4df9cc4659fb28733ad0882d3d139
intermediate review collage SHA-256: f4db511969051dcb4e7329716218d6eba84e8b39b64edf9a2b81aa8031a584cf
intermediate Drive file name: pr146-visual-verification-evidence-corrected.jpg
intermediate size: 122,451 bytes
```

The repository documents and tests remain the authority. Render evidence does not authorize deletion of any branch outside the enumerated PR-backed set.

## Verdict

```text
PR #145 source and structured records: PASS
Desktop render after correction: PASS
390 × 844 mobile render after correction: PASS
Accepted/candidate visual separation: PASS
Overflow and overlap inspection: PASS
Mobile disposition-table readability: FAILED initially → REPAIRED → PASS
Visual-proof matrix readability: COMPRESSED initially → REPAIRED → PASS
Post-merge deletion-state wording: CORRECTED
Corrected durable visual copy: PASS
Corrected recovery byte replay: PASS
Unknown branch-only work: REQUIRES SEPARATE INSPECTION
```
