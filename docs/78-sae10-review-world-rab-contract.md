# SAE-10 — Review World + Review Authority Bundle candidate contract

Date: 2026-09-03  
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

- `main_review/review_world.py` — canonical JSON, exact ReviewScope/diff/world identity, type-strict construction, strict pre-canonical persisted decode, canonical unresolved-state handling, and canonical in-memory validation;
- `main_review/review_authority_bundle.py` — immutable ten-slot RAB construction, strict typed authority fields, pre-canonical persisted decode, whole-RAB authorization, revocation/suspension, and canonical authorization-set ordering;
- `main_review/review_world_git.py` — exact typed GitHub transport facts plus exact Git/GitHub tree derivation and content-addressed local snapshots with fail-closed `attached`, `detached`, and genuinely `unborn` HEAD state;
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

Additional proof covers persisted tamper, unknown fields, truncated IDs, mutable aliases, repository substitution, Git environment isolation, selected/untracked policy, symlink identity, generated-state binding, LFS/submodule ambiguity, revoked/suspended authorization, strict path canonicality, authority-manifest completeness, persisted primitive types, repository normalization, unresolved-state canonicality, local repository-null identity, construction/persistence generation-type symmetry, noncoercible GitHub transport identity, and dangling symbolic/local HEAD discrimination.

## Hostile-review history

The candidate preserves prior review generations rather than rewriting them.

- Initial review of `c977449177eb9c9f3d6034265ad97cc32180c069` exposed the historical SPIKE-SEM current-tree invariant defect; the exact historical node was externally superseded with strict XFAIL semantics while preserving the fixture bytes.
- Review of `bf368b46cd0120736645d87e8dc7fec4904a046a` produced seven valid findings covering exact manifest roster/path confinement, historical fixture binding, plan slot-name drift, authorization-state validation, Git environment isolation, duplicate decoded-scope rejection, and strict historical-node binding. All were repaired.
- Exact-head review of `323b6f33223231b5d603a3a36ee5c07ef687a96a` produced three actionable findings. Two authority defects were repaired; the historical design-status suggestion was dispositioned without rewriting the frozen design blob.
- Owner/Root exact-head review of `97055f975c2fe76f77b7483df885f1aa9064c560` exposed direct in-memory canonical-authority bypass. Direct RAB/ReviewScope/diff/world objects now validate before they can become authority-bearing.
- Fresh exact-head review of `f20d83a7620622e3f2e96ffc26960f40a6a2df92` exposed four canonicality/proof classes: RAB authority-field type/order coercion, persisted ReviewScope path-order acceptance, incomplete mechanical enforcement of the external-authority roster, and inability to represent detached/unborn local HEAD state as required by the frozen design. Seven RED regressions demonstrated the class before repair.
- Owner/Root exact-head review of `924d33aa188dff673a9ca7eb7c843b6222e798fe` exposed persisted RAB decode normalization/coercion. Nine RED regressions demonstrated the class. `b3c4e409bfb7e0fd498d7790bef3b391f9595755` repaired RAB component/authorization payload canonicality and authorization-set order.
- A subsequent Owner/Root hostile audit of exact v5 head `b3c4e409bfb7e0fd498d7790bef3b391f9595755` found the sibling persisted Review World decode class. Fourteen RED regressions demonstrated coercion/normalization in `ReviewScope`, `GitHubDiffIdentity`, `GitHubReviewWorld`, and `LocalReviewWorld`; all passed after the shared v6 repair.
- Exact v6 rebound `ece5ae76b2d76763524d5be46be8bd619af300b2` proved `1234 passed`, `2` intentional XFAILs, `0 failed`, but Owner/Root hostile review found the rebound manifest test had dropped historical-review assertions. `8939f93eba730c3519f3ffe84c5e3793b6c15a90` restored that mechanical history without adding a test node.
- Fresh external exact-head review of `8939f93eba730c3519f3ffe84c5e3793b6c15a90` (CodeRabbit run `7c0b86f6-b27e-4b33-9641-62d2868b366c`) exposed a construction/persistence asymmetry: truthy non-string generation values could be hashed into Review World authority objects that their own persisted decoders would later reject. Five regressions reproduced the class before the v7 repair.
- Fresh external exact-head review of v7 head `64f420aaea40594c4165ad64601b4db5547e275f` (CodeRabbit run `83e3c959-0d29-414a-b2ab-78f7b76aa411`) exposed three additional authority-boundary defects: coercible PR transport facts, dangling/nested symbolic local HEAD collapsing into `unborn`, and invalid/blank unresolved-state entries collapsing before exact-world rejection. All three findings reproduced before repair. The final regression surface binds 13 hostile cases into three repository test nodes.

## v8 root repair

The v8 repair:

- reads PR transport facts without `str(...)`/`int(...)` coercion and requires repository/base/head to be actual strings plus `type(pr_number) is int` before Review World construction;
- classifies local HEAD as `unborn` only when HEAD is a direct `refs/heads/...` symbolic ref and that branch ref is actually absent; nested symbolic refs, malformed/dangling object refs, detached ambiguity, and other resolution failures fail closed;
- validates every `unresolved_state` member as a string and rejects blank entries before any normalization/deduplication can erase evidence.

The strengthened local hostile case proof is **13 passed / 0 failed**. The repository test layout represents those cases in exactly **3** added test nodes.

## Current proof boundary

The v7 focused SAE-10 collection was **124 tests**. The v8 repair adds exactly **3** repository regression nodes, producing a focused collection of **127 tests**.

The prior conservative local dependency reconciliation was **112 passed / 0 failed**. Reconciliation with the three v8 regression nodes produces **115 passed / 0 failed**, backed by the fresh 13-case local hostile proof and the intermediate complete-repository run. This remains explicitly a reconciliation, not a claim that unavailable unchanged modules were rerun in the reduced scratch workspace.

The four-file v8 intermediate was published atomically as `30b1f922453c63f473e38a39a70e82a1e9914d11`. Its replacement blobs are:

- `main_review/review_world.py` — `af4a32de1717f706d07377dcfaf65b2558f2d617`;
- `main_review/review_world_git.py` — `5f194b67cdceafb4b7098c5b3a8cfaa4015f3a51`;
- `tests/test_review_world_git.py` — `8a6e77ff54ed030184769129d186621b19423026`;
- `tests/test_review_world_persistence.py` — `8e8258ef7285eef59e34a2e9bd7d7f7eda7ee65e`.

Main Review run `33733303192` passed. Complete-repository CI run `33733303167` produced **1241 passed, 2 intentional historical XFAILs, and exactly 1 failure**. The sole failure was the deliberately stale v7 candidate content binding (`main_review/review_world.py` expected `34692d55...`, actual `af4a32de...`). No production or new regression node failed.

The eight external authority paths remain byte-stable and must continue to match their exact Git blob bindings.

The twenty Tenfold lanes remain syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, historical-proof supersession, and full-suite reconciliation.

## Pre-SAE-30 lifecycle boundary

General SAE-30 Qualification Authority machinery does not yet exist and is **not fabricated here**. The pre-SAE-30 bootstrap cannot issue general Qualification Attestations, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. Heads `924d33aa188dff673a9ca7eb7c843b6222e798fe`, `b3c4e409bfb7e0fd498d7790bef3b391f9595755`, `ece5ae76b2d76763524d5be46be8bd619af300b2`, `8939f93eba730c3519f3ffe84c5e3793b6c15a90`, and `64f420aaea40594c4165ad64601b4db5547e275f` are superseded by later hostile findings. Intermediate `30b1f922453c63f473e38a39a70e82a1e9914d11` is not freezeable because its candidate content bindings are deliberately stale. SAE-10 is not lifecycle-PROVEN until the rebound v8 candidate is published atomically, survives complete-repository and clean-clone proof, survives a fresh exact-head hostile review, is reconciled against current `main`, and the exact reviewed candidate is guarded-merged before a separate immutable SAE-10 PROVEN closeout generation is created and proved. No SAE-20 work may advance across that boundary.
