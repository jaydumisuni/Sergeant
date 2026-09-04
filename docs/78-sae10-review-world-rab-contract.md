# SAE-10 — Review World + Review Authority Bundle candidate contract

Date: 2026-09-04  
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

Additional proof covers persisted tamper, unknown fields, truncated IDs, mutable aliases, repository substitution, Git environment isolation, selected/untracked policy, symlink identity, generated-state binding, LFS/submodule ambiguity, revoked/suspended authorization, strict path canonicality, authority-manifest completeness, persisted primitive types, repository normalization, unresolved-state canonicality, local repository-null identity, construction/persistence generation-type symmetry, noncoercible GitHub transport identity, dangling symbolic/local HEAD discrimination, noncoercible generated binding identity, pull-request-number currentness, direct local-snapshot scope validation, replacement-object isolation, and scalar string/bytes rejection across public path-collection APIs.

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
- Fresh external exact-head review of corrected v8 head `16c623935549d7b87ae0b96eef58c8630d252c73` (CodeRabbit run `d33a4848-57e5-4cc8-bb65-d8715c6f987f`) exposed one additional authority-boundary defect: a bound `LocalSnapshotPolicy.generated_binding_id` was coerced through `str(...)`, allowing non-string values with SHA-256-shaped string representations to enter snapshot identity. A RED regression demonstrated the coercion before the v9 repair.
- Owner/Root authority audit of exact v9 head `940fd609ebc18a62bd678a09518f43ed35b04a68` found one documentation-level roadmap error before merge: the residual boundary incorrectly stated that SAE-20 could not advance until SAE-10 closed. The frozen roadmap gives SAE-20 its own proof dependency of SAE-00 and separately permits safe downstream preparation before unresolved dependencies. v10 corrected that wording without changing production behavior.
- The external exact-head completion review of the same v9 head did complete and is preserved rather than discarded: CodeRabbit run `2c410bcc-a73a-4929-b8de-e8c5b601cba1` reported three actionable findings—GitHub currentness omitted `pr_number`, local snapshot construction trusted a directly forged `ReviewScope` before validation, and the v9 completion review generation itself was not mechanically bound in the candidate history. Test-only head `14984cc377878d74802d7a4ec27ee6fa29732ddd` reproduced exactly all three failures before production changed.
- Fresh CodeRabbit exact-head review of v12 candidate `c3819455a32f93cbe6fddeccb6bffade69f33046` against canonical base `b5dd07b6a0d2cfed42a111750c0c2df6559a0fb5` (issue comment `5533028222`) verified the v12 replacement-object, blob-binding, UNKNOWN-currentness, nonactivation, and roadmap corrections, then exposed one remaining sibling canonicality defect: `ReviewScope.changed_files(...)` and `LocalSnapshotPolicy.include_selected_untracked(...)` still accepted scalar `str`/`bytes` path containers before iteration/tuple conversion.

## v8 root repair

The v8 repair:

- reads PR transport facts without `str(...)`/`int(...)` coercion and requires repository/base/head to be actual strings plus `type(pr_number) is int` before Review World construction;
- classifies local HEAD as `unborn` only when HEAD is a direct `refs/heads/...` symbolic ref and that branch ref is actually absent; nested symbolic refs, malformed/dangling object refs, detached ambiguity, and other resolution failures fail closed;
- validates every `unresolved_state` member as a string and rejects blank entries before any normalization/deduplication can erase evidence.

The strengthened local hostile case proof is **13 passed / 0 failed**. The repository test layout represents those cases in exactly **3** added repair regression nodes.

## v9 generated-binding repair

The v9 repair removes the remaining coercion at the generated-material binding boundary:

- `generated_state='bound'` now requires `generated_binding_id` to already be a string;
- non-string values fail closed before digest validation;
- the original string is passed directly to `require_full_sha256(...)` rather than reconstructed with `str(...)`;
- the repair regression exercises both an integer digest-shaped value and a stringable object, while the observed RED failure mechanically demonstrated the integer coercion path before production changed.

The test-only RED head is `d81f740e6e97d0882168f0475899d3ca8c945fab`. CI run `33752751547` produced **1242 passed, 2 intentional historical XFAILs, and 2 failed**: the new coercion regression failed because `GitCommandError` was not raised, and the candidate content-binding test failed because the regression test blob was intentionally not yet rebound.

The minimal production repair head is `5e8e34d4b2c8d342264bde9510a6900ce4e828b1`. Its replacement blobs were `main_review/review_world_git.py` `a0a30a410dd1478e9ed354b20c1b9e8886b3fecd` and `tests/test_review_world_git.py` `8e860e21b988be4a6cfde0ccb6a233056a8a5f61`.

Main Review run `33753103819` passed. Complete-repository CI run `33753103838` produced **1243 passed, 2 intentional historical XFAILs, and exactly 1 failure**, solely the deliberately stale candidate content binding.

## v10 roadmap dependency correction

The v10 correction changes no Review World/RAB production behavior and adds no test node. It narrows lifecycle prose back to the frozen DAG:

- SAE-10 closure controls only SAE-10's own PROVEN state and the availability of `QUALIFIED_REVIEW_WORLD_CONTRACT` / `QUALIFIED_RAB_CONTRACT` to nodes that explicitly depend on SAE-10;
- SAE-20 remains an independent frontier programme whose frozen proof dependency is SAE-00;
- safe downstream preparation remains allowed under the roadmap's dependency-frontier doctrine;
- no downstream node is auto-qualified or auto-proven by SAE-10 closeout.

## v11 completion-review repair

The v11 repair responds to the completed v9 external review without rewriting earlier evidence:

- GitHub currentness now compares `pr_number` as part of exact Review World identity and emits `pr_number_mismatch` when a different pull request is compared;
- `build_local_snapshot(...)` validates the supplied `ReviewScope` before any Git path selection, hashing, or snapshot identity construction;
- the completed v9 CodeRabbit run and its three findings are now an explicit mechanical review generation in the manifest proof.

The test-only RED head `14984cc377878d74802d7a4ec27ee6fa29732ddd`, CI `33761255366`, produced **3 failed / 1244 passed / 2 historical XFAIL**. The failures were exactly the three review findings: cross-PR currentness returned `CURRENT`, forged local scope did not raise, and the v9 completion-review record was missing.

The minimal production repair reached intermediate head `6903ba3caee39d86a397e45e270830651435253a`. CI `33761724692` produced **1245 passed / 2 historical XFAIL / exactly 2 failures**. Both production regressions were GREEN; the only remaining failures were the deliberately stale candidate content binding and missing v9 review-generation evidence. Main Review `33761724596` passed. The production diff from RED to intermediate is exactly **3 added lines across 2 files**: two lines for PR-number currentness and one `scope.validate()` call.

## v12 exact-head hostile repair

Fresh CodeRabbit completion review of exact v11 head `2d29b29c1f528ab5e792b9350efc27e61663809b` (run `1195252f-db18-4078-ac00-0a45ac1cac46`) completed with three actionable findings:

- Git subprocesses used for authority-bearing commit/tree/snapshot facts did not force replacement objects off, so repository-local `refs/replace/*` state could alter resolved Git identity.
- Public collection boundaries accepted `str`/`bytes` containers for selected paths and unresolved state, permitting scalar string-like values to be iterated or collapsed rather than rejected as noncanonical containers.
- The completed v9 review generation recorded replacement blobs and final counts in `docs/79`, but the mechanical manifest proof did not bind those fields back to current `content_blobs` and `tenfold_proof`.

The runtime findings were reproduced RED-first on test-only head `91c534bc4539604ec6509186f4d49155d11556f0`. CI `33812521132` produced **1246 passed / 2 historical XFAIL / 6 failed**: five hostile runtime cases failed exactly as designed and one additional failure was the deliberately stale candidate content binding. Main Review `33812521092` passed.

The minimal production repair head is `3cbda77bcca89f1066b09fc6f00a64540c2c3710`. It:

- injects `GIT_NO_REPLACE_OBJECTS=1` into the allowlisted Git subprocess environment used by Review World Git fact derivation;
- rejects `str` and `bytes` containers at `ReviewScope.selected_paths(...)` before path iteration;
- rejects `str` and `bytes` containers for `GitHubReviewWorld.create(... unresolved_state=...)` before member iteration/normalization.

The local bound hostile fixture re-proved **5 passed / 0 failed** and the broader Review World/RAB dependency surface executed **126 passed / 0 failed** in the isolated Tenfold worktree. Complete-repository intermediate CI `33813167874` produced **1251 passed / 2 historical XFAIL / exactly 1 failed**, solely the intentionally stale candidate content binding; Main Review `33813167919` passed.

The proof-only finding is repaired in-place in the existing manifest-history test: the v9 `production_replacement_content_blobs`, `focused_collection_after_repair`, and `production_dependency_surface_after_repair` fields are now bound to the exact reviewed-generation snapshot rather than silently drifting with later repair generations, adding no new test node.

## v13 sibling path-collection repair

The fresh exact-head CodeRabbit review of v12 head `c3819455a32f93cbe6fddeccb6bffade69f33046` found one remaining sibling of the v12 sequence-container class. `ReviewScope.changed_files(...)` iterated scalar strings, while `LocalSnapshotPolicy.include_selected_untracked(...)` converted a scalar string with `tuple(paths)` before validation. In both cases a value such as `"ab"` could become the canonical collection `("a", "b")` instead of failing closed.

Four hostile cases were bound into the existing regression fixture and published RED-first on `572693665c8c5284d696a280f30485c3d4df4f04`: `str` and `bytes` inputs for each of the two public APIs. CI `33850508646` produced **1251 passed / 2 historical XFAIL / 5 failed**—exactly those four runtime failures plus the deliberately stale candidate content binding. Main Review `33850508701` passed.

The production repair is shared rather than duplicated:

- `require_non_string_sequence(...)` is now the common pre-iteration guard for all `ReviewScope` path construction;
- `_normalize_policy_paths(...)` applies the same guard before truthiness, iteration, or tuple conversion;
- `include_selected_untracked(...)` normalizes through that guarded path instead of calling `tuple(paths)` directly.

The repair is frozen at intermediate head `8aeafca35f3c35fb5388e552f7bf469bfc7503ef`. From RED head to intermediate, production changed only **2 files / 13 lines** (`+9 / -4`). Exact replacement blobs are `main_review/review_world.py` `f795b5c9dce74c6ec69cad52d4d34e9ce6107120` and `main_review/review_world_git.py` `cc913b3538f8b101907791209dfafdb31049ba2c`. Complete-repository CI `33851019846` produced **1255 passed / 2 historical XFAIL / exactly 1 failed**, solely the intentionally stale candidate content binding; all four sibling regressions are GREEN. Main Review `33851020089` passed.

## Current proof boundary

The final v8 focused SAE-10 collection was **128 tests** with a reconciled production dependency surface of **115 passed / 0 failed**. v9 added one production regression node, yielding **129 / 116**. v10 added no test node. v11 added **3 focused nodes**, two of which exercise production authority boundaries and one of which binds review evidence, yielding **132 / 118**. v12 added **5 hostile runtime cases** in the existing bound regression fixture and no new manifest-proof node, yielding **137 / 123**. v13 adds exactly **4** newly collected hostile path-container cases in that same fixture and no new manifest-proof node, yielding structurally reconciled accounting of **141 focused tests / 127 production cases**. The final v13 full-repository CI remains the authoritative execution measurement.

The manifest-history proof is extended rather than replaced: all prior review assertions remain present, completed external reviews are mechanically bound to the generation they actually reviewed, and later legitimate repairs do not rewrite historical blob/count facts.

The exact v9 rebound `940fd609ebc18a62bd678a09518f43ed35b04a68` proved **1244 passed / 2 historical XFAIL / 0 failed** in CI `33753660492`, clean-clone PASS, and Main Review `33753660693` PASS. v10 documentation head `9eb3dcfe0368847def72911d5e622c1adb48c624` independently proved the same **1244 / 2 / 0** in CI `33755080985` with clean-clone PASS and Main Review `33755080831` PASS. Both remain historical evidence only.

The eight external authority paths remain byte-stable and must continue to match their exact Git blob bindings.

The twenty Tenfold lanes remain syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, historical-proof supersession, and full-suite reconciliation.

## Pre-SAE-30 lifecycle boundary

General SAE-30 Qualification Authority machinery does not yet exist and is **not fabricated here**. The pre-SAE-30 bootstrap cannot issue general Qualification Attestations, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. Earlier candidate/rebound/repair heads are historical or non-freezeable once a later evidence rebound exists. SAE-10 is not lifecycle-PROVEN until the exact v13 rebound survives complete-repository and clean-clone proof, survives a fresh exact-head hostile review, is reconciled against current `main`, and the exact reviewed candidate is guarded-merged before a separate immutable SAE-10 PROVEN closeout generation is created and proved. SAE-20 remains governed by its own frozen SAE-00 proof dependency; SAE-10 closeout neither blocks safe SAE-20 preparation nor auto-qualifies or auto-proves SAE-20.
