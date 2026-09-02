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

The local candidate was reviewed through twenty distinct evidence lanes rather than using GitHub as the development surface. The core reconciled local suite is `57 passed, 0 failed`; candidate-manifest binding adds six proof tests for a final exact candidate result of `63 passed, 0 failed`.

The twenty lanes cover syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, canonical re-encoding, and full-suite reconciliation.

GitHub Actions are supplementary only and are not assumed available.

## Pre-SAE-30 lifecycle boundary

SAE-10 depends only on PROVEN SAE-00. General SAE-30 Qualification Authority machinery does not yet exist and is not fabricated here. Candidate construction/lifecycle review remains bounded by PROVEN SAE-00 roadmap execution authority plus the frozen Owner/Root constitutional TCB.

That bootstrap cannot issue a general Qualification Attestation, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. It is not lifecycle-PROVEN until the milestone is pushed, live PR review is recovered and dispositioned, the exact pushed head is reconciled against current `main`, and a separate immutable SAE-10 PROVEN closeout generation is created and proved.
