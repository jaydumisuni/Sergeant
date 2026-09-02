# SAE-10 — Review World + Review Authority Bundle candidate contract

Date: 2026-09-02
Lifecycle state: **CANDIDATE**
Roadmap node: `SAE-10`
Proof dependency: PROVEN `SAE-00`
Produces if later lifecycle-proven: `QUALIFIED_REVIEW_WORLD_CONTRACT`, `QUALIFIED_RAB_CONTRACT`
Normal Sergeant verdict authority gained by this candidate: **none**

## Construction authority

Canonical construction base is `b5dd07b6a0d2cfed42a111750c0c2df6559a0fb5`.
The GitHub construction checkpoint imported into the local Tenfold workspace was `17c4240af1969e0fc999379c5243696347820def` on PR #176.
All work after that checkpoint was executed in the isolated local Tenfold Gen 1 workspace and is pushed only at the frozen milestone boundary.

## Implemented contract

The candidate establishes four isolated authority components:

- `main_review/review_world.py` — canonical JSON, full SHA-256 authority identity, exact scope/diff/Review World identity, and strict persisted-object decode with tamper rejection;
- `main_review/review_authority_bundle.py` — exact ten-slot immutable RAB, explicit future inactive slots, verifier-trusted whole-RAB authorization, revocation/suspension, and no mutable authority aliases;
- `main_review/review_world_git.py` — exact Git commit/tree and synthetic merge-tree derivation plus content-addressed local HEAD/index/worktree/untracked/submodule/LFS/generated-state snapshots;
- `main_review/review_world_currentness.py` — immutable historical world truth plus separate `CURRENT / STALE / UNKNOWN_CURRENTNESS` derivation and explicit invalidation reasons.

The existing GitHub fetch, battle-review transport, Cpl/officers/Judge, and normal verdict path are not replaced and do not gain SAE-10 authority from this candidate.

## Required hostile attacks

The frozen SAE-10 attacks are mechanically represented and pass in the workspace:

1. same head / different base cannot reuse a positive world;
2. wrong synthetic merge tree invalidates merge-readiness identity;
3. local mutation after snapshot is stale and does not rewrite historical identity;
4. scope downgrade cannot satisfy repository-wide identity;
5. an unauthorized RAB combination fails even when component generations are individually known;
6. candidate changes to future RAB authority have zero effect on the verifier-trusted active authorization set.

Additional falsifiers cover persisted-object tamper, unknown fields, truncated authority IDs, mutable `latest` aliases, repository substitution, selected-untracked policy, symlink identity, generated-state binding, LFS ambiguity, revocation/suspension, Git SHA-1/SHA-256 object formats, path traversal, deterministic identity repetition, and workspace non-mutation.

## Tenfold Gen 1 proof

The local candidate was reviewed through twenty distinct evidence lanes rather than using GitHub as the development surface. Before GitHub review, the exact candidate result was `63 passed, 0 failed`. GitHub hostile review of milestone `c977449177eb9c9f3d6034265ad97cc32180c069` exposed one valid cross-generation proof-infrastructure defect: the immutable SPIKE-SEM 14,439-relation historical measurement was still being asserted as a current-tree invariant after SAE-10 added four `main_review/` modules. The obsolete current-tree interpretation was superseded externally with an exact-node strict XFAIL, matching the existing SAE-00 historical-snapshot precedent. The first repaired candidate result was `66 passed, 1 intentional historical XFAIL, 0 failed`, and GitHub full-repository CI on replacement head `bf368b46cd0120736645d87e8dc7fec4904a046a` proved `1181 passed, 2 intentional historical XFAILs, 0 failed` plus a green clean-clone proof chain.

A second exact-head CodeRabbit review of `bf368b46cd0120736645d87e8dc7fec4904a046a` (review `5089723949`) produced seven valid findings. All seven were brought back into the Tenfold workspace: verifier-trusted RAB records now reject forged authorization states; Git subprocesses discard inherited Git metadata such as `GIT_DIR` and `GIT_INDEX_FILE`; strict ReviewScope decode rejects duplicate normalized paths; candidate-manifest proof requires an exact repository-confined content roster; the historical SPIKE-SEM fixture is mechanically byte-bound to Git blob `b2bf08d7103e490dc816a1a195c05c34b0d0d97d`; the exact historical node is mechanically proven to receive `strict=True`; and the implementation-plan RAB example now uses the frozen `epistemic_constitution` slot. The isolated replacement candidate suite is `71 passed, 0 failed`; the frozen historical SPIKE fixture is byte-preserved locally and is executed only by the complete GitHub repository proof because this reconstruction workspace intentionally contains only the SAE-10 dependency surface.

A third exact-head CodeRabbit review of `323b6f33223231b5d603a3a36ee5c07ef687a96a` produced three actionable findings. Two authority defects were accepted and repaired with regressions first: direct `RABComponent` construction now rejects empty or non-canonical `authority_domain` values across every lifecycle state, and `UNKNOWN_CURRENTNESS` now preserves all independently knowable world-mismatch reasons alongside `rab_authorization_unknown`. The design-status suggestion was dispositioned without mutating the historical design-freeze blob because `docs/79` binds that exact spec under `external_authority_blobs`; current lifecycle truth belongs to the candidate and separate closeout generations rather than rewriting the original design-state snapshot. After these accepted repairs, the isolated replacement candidate suite is `77 passed, 0 failed`.

A fourth exact-head Owner/Root hostile review of published head `97055f975c2fe76f77b7483df885f1aa9064c560` found one canonical-authority class that the prior persisted-object tests did not exercise: directly constructed in-memory authority objects could bypass factory normalization and then fail their own canonical persisted round-trip. The repair closes that class rather than one symptom: active RAB generations and inactive/prohibited RAB basis/domain values must already be canonical; a non-canonical direct `ReviewScope` cannot seed a diff identity; a forged direct `GitHubDiffIdentity` cannot seed a Review World; and currentness rejects forged direct GitHub/local Review World identities before comparison. Regressions were written RED first. After this repair, the isolated replacement candidate suite is `86 passed, 0 failed`.

The twenty lanes cover syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, historical-proof supersession, and full-suite reconciliation.

GitHub Actions are supplementary only and are not assumed available.

## Pre-SAE-30 lifecycle boundary

SAE-10 depends only on PROVEN SAE-00. General SAE-30 Qualification Authority machinery does not yet exist and is not fabricated here. Candidate construction/lifecycle review remains bounded by PROVEN SAE-00 roadmap execution authority plus the frozen Owner/Root constitutional TCB.

That bootstrap cannot issue a general Qualification Attestation, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. Four pushed review generations have been dispositioned: the first historical-proof defect, the second review's seven valid findings, the third exact-head review's two accepted authority defects plus one preservation-based design-status disposition, and the fourth exact-head Owner/Root review's in-memory canonical-authority finding class. SAE-10 is not lifecycle-PROVEN until the repaired replacement milestone is pushed and reviewed cleanly, reconciled against current `main`, and a separate immutable SAE-10 PROVEN closeout generation is recreated and proved against the final reviewed head.
