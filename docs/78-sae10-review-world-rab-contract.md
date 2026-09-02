# SAE-10 — Review World + Review Authority Bundle candidate contract

Date: 2026-09-02  
Lifecycle state: **CANDIDATE**  
Roadmap node: `SAE-10`  
Proof dependency: PROVEN `SAE-00`  
Produces if later lifecycle-proven: `QUALIFIED_REVIEW_WORLD_CONTRACT`, `QUALIFIED_RAB_CONTRACT`  
Normal Sergeant verdict authority gained by this candidate: **none**

## Construction authority

Canonical construction base is `b5dd07b6a0d2cfed42a111750c0c2df6559a0fb5`.
The imported GitHub checkpoint remains `17c4240af1969e0fc999379c5243696347820def` on PR #176.
Construction and hostile repair work is isolated from canonical `main`; no SAE-20/30+ authority is fabricated here.

## Implemented contract

SAE-10 establishes four authority components:

- `main_review/review_world.py` — canonical JSON, exact ReviewScope/diff/world identity, strict decode, and canonical in-memory validation;
- `main_review/review_authority_bundle.py` — immutable ten-slot RAB construction, strict typed authority fields, whole-RAB authorization, revocation/suspension, and canonical authorization-set ordering;
- `main_review/review_world_git.py` — exact Git/GitHub tree derivation plus content-addressed local snapshots with explicit `attached`, `detached`, and `unborn` HEAD state;
- `main_review/review_world_currentness.py` — immutable historical world truth with separate fail-closed `CURRENT / STALE / UNKNOWN_CURRENTNESS` derivation.

Candidate content has **zero effect** on verifier-trusted authorization unless separately authorized. GitHub Actions are supplementary only and are not assumed available.

## Required hostile attacks

The frozen roadmap attacks remain mechanically represented:

1. same head / different base cannot reuse a positive world;
2. wrong merge tree invalidates merge-readiness identity;
3. local mutation after snapshot becomes stale without rewriting history;
4. scope downgrade cannot satisfy repository scope;
5. an unauthorized RAB combination fails even when component generations are known;
6. candidate authority changes cannot self-activate.

Additional proof covers persisted tamper, unknown fields, truncated IDs, mutable aliases, repository substitution, Git environment isolation, selected/untracked policy, symlink identity, generated-state binding, LFS/submodule ambiguity, revoked/suspended authorization, strict path canonicality, and authority-manifest completeness.

## Hostile-review history

The candidate preserves prior review generations rather than rewriting them.

- Initial review of `c977449177eb9c9f3d6034265ad97cc32180c069` exposed the historical SPIKE-SEM current-tree invariant defect; the exact historical node was externally superseded with strict XFAIL semantics while preserving the fixture bytes.
- Review of `bf368b46cd0120736645d87e8dc7fec4904a046a` produced seven valid findings covering exact manifest roster/path confinement, historical fixture binding, plan slot-name drift, authorization-state validation, Git environment isolation, duplicate decoded-scope rejection, and strict historical-node binding. All were repaired.
- Exact-head review of `323b6f33223231b5d603a3a36ee5c07ef687a96a` produced three actionable findings. Two authority defects were repaired; the historical design-status suggestion was dispositioned without rewriting the frozen design blob.
- Owner/Root exact-head review of `97055f975c2fe76f77b7483df885f1aa9064c560` exposed direct in-memory canonical-authority bypass. Direct RAB/ReviewScope/diff/world objects now validate before they can become authority-bearing.
- Fresh exact-head review of `f20d83a7620622e3f2e96ffc26960f40a6a2df92` exposed four remaining canonicality/proof classes: RAB authority-field type/order coercion, persisted ReviewScope path-order acceptance, incomplete mechanical enforcement of the external-authority roster, and inability to represent detached/unborn local HEAD state as required by the frozen design. Seven regressions were written RED first and failed for the reviewed reasons. The root-cause repairs make RAB authority fields type-strict, reject non-canonical direct authorization-set order, reject non-canonical persisted scope ordering, bind the exact eight-member external-authority roster, and encode local HEAD state explicitly without inventing a fake SHA.

The fifth repair was published atomically as intermediate head `4b4cc9264d1db769566b5d5defea75b72c94532b`. On that exact intermediate head, complete-repository CI executed `1213` tests: `1210 passed`, `2` intentional historical XFAILs, and exactly `1` failure. The sole failure was the intentionally stale candidate `content_blobs` binding, proving no second code regression was hidden behind the manifest transition.

## Current proof boundary

The exact focused command from the implementation plan collects **96 tests** across eight files. In the reconstructed Tenfold dependency surface, the six fully materialized authority/code suites execute **84 passed, 0 failed**. The remaining 12 focused nodes are repository-only in this runtime: two historical supersession nodes require frozen SPIKE authority documents and ten manifest nodes require the complete bound repository authority roster. Their source files are byte-verified against the published Git objects; their execution is closed by complete-repository proof on the exact candidate tree rather than by fabricating missing local authority files.

The eight external authority paths previously bound by `docs/79` were independently re-read from exact head `f20d83a7620622e3f2e96ffc26960f40a6a2df92`; all **8/8** Git blob SHAs match their declared authority objects.

The twenty Tenfold lanes remain syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, historical-proof supersession, and full-suite reconciliation.

## Pre-SAE-30 lifecycle boundary

General SAE-30 Qualification Authority machinery does not yet exist and is **not fabricated here**. The pre-SAE-30 bootstrap cannot issue general Qualification Attestations, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. SAE-10 is not lifecycle-PROVEN until the final candidate manifest is rebound to the repaired bytes, the exact published candidate survives complete-tree proof and fresh exact-head hostile review, current `main` is reconciled, and a separate immutable SAE-10 PROVEN closeout generation is created and proved. No SAE-20 work may advance across that boundary.
