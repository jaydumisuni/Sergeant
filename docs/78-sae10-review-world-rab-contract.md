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

- `main_review/review_world.py` — canonical JSON, exact ReviewScope/diff/world identity, strict pre-canonical persisted decode, and canonical in-memory validation;
- `main_review/review_authority_bundle.py` — immutable ten-slot RAB construction, strict typed authority fields, pre-canonical persisted decode, whole-RAB authorization, revocation/suspension, and canonical authorization-set ordering;
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

Additional proof covers persisted tamper, unknown fields, truncated IDs, mutable aliases, repository substitution, Git environment isolation, selected/untracked policy, symlink identity, generated-state binding, LFS/submodule ambiguity, revoked/suspended authorization, strict path canonicality, authority-manifest completeness, persisted primitive types, repository normalization, unresolved-state normalization, and local repository-null identity.

## Hostile-review history

The candidate preserves prior review generations rather than rewriting them.

- Initial review of `c977449177eb9c9f3d6034265ad97cc32180c069` exposed the historical SPIKE-SEM current-tree invariant defect; the exact historical node was externally superseded with strict XFAIL semantics while preserving the fixture bytes.
- Review of `bf368b46cd0120736645d87e8dc7fec4904a046a` produced seven valid findings covering exact manifest roster/path confinement, historical fixture binding, plan slot-name drift, authorization-state validation, Git environment isolation, duplicate decoded-scope rejection, and strict historical-node binding. All were repaired.
- Exact-head review of `323b6f33223231b5d603a3a36ee5c07ef687a96a` produced three actionable findings. Two authority defects were repaired; the historical design-status suggestion was dispositioned without rewriting the frozen design blob.
- Owner/Root exact-head review of `97055f975c2fe76f77b7483df885f1aa9064c560` exposed direct in-memory canonical-authority bypass. Direct RAB/ReviewScope/diff/world objects now validate before they can become authority-bearing.
- Fresh exact-head review of `f20d83a7620622e3f2e96ffc26960f40a6a2df92` exposed four canonicality/proof classes: RAB authority-field type/order coercion, persisted ReviewScope path-order acceptance, incomplete mechanical enforcement of the external-authority roster, and inability to represent detached/unborn local HEAD state as required by the frozen design. Seven RED regressions demonstrated the class before repair.
- Owner/Root exact-head review of `924d33aa188dff673a9ca7eb7c843b6222e798fe` exposed persisted RAB decode normalization/coercion. Nine RED regressions demonstrated the class. `b3c4e409bfb7e0fd498d7790bef3b391f9595755` repaired RAB component/authorization payload canonicality and authorization-set order, and its complete-repository proof was `1220 passed`, `2` intentional historical XFAILs, `0 failed` with clean-clone and Main Review PASS.
- A subsequent Owner/Root hostile audit of exact v5 head `b3c4e409bfb7e0fd498d7790bef3b391f9595755` found the sibling persisted Review World decode class: `ReviewScope`, `GitHubDiffIdentity`, `GitHubReviewWorld`, and `LocalReviewWorld` still admitted `str(...)`/`int(...)` coercion or normalization. Fourteen regressions were constructed with canonical normalized identities so ordinary ID-mismatch checks could not hide the defect. All 14 failed on v5 for the predicted reasons, then passed after the shared root repair.

The v6 root repair makes persisted authority primitives type-strict, requires PR numbers to be actual positive integers rather than bool/float/string coercions, prevents repository case/whitespace normalization from silently changing evidence, prevents empty or noncanonical unresolved-state entries from disappearing, prevents local `""` repository identity from collapsing to `None`, and requires each decoded Review World structure to reproduce the exact incoming canonical payload.

The two-file v6 intermediate was published atomically as `0e67e3116e9d7a6a3945550eef3fdf485f25f634`. Its production blob is `9d6081641506bcdb205271b9a6aa5e3e60c3bc65`. Main Review passed. Complete-repository CI run `33693267282` executed `1236` outcomes: `1232 passed`, `2` intentional historical XFAILs, and exactly `2` failures. One was the intentionally stale candidate content binding. The other was a stale test-message regex: production correctly rejected `7.0` immediately with `pr_number must be a positive integer`, while the old test accepted only `mismatch|non-canonical` wording. The assertion was corrected without changing production behavior and the affected decoder selection then passed `15/15` locally.

## Current proof boundary

The exact v5 focused command collected **105 tests** across eight files. Exact v5→v6 comparison changes only `main_review/review_world.py` and `tests/test_review_world_persistence.py`, and the persistence suite adds **14** test nodes. Complete-repository outcome cardinality independently increased by the same 14 nodes. The v6 focused collection is therefore mechanically reconciled to **119 tests**.

The prior v5 local dependency surface was **93 passed, 0 failed**. All unchanged dependency-surface files remain byte-identical, and the 14 new v6 hostile nodes are freshly RED→GREEN. The v6 local dependency surface is mechanically reconciled to **107 passed, 0 failed**. This is explicitly a reconciliation of the frozen 93-test proof plus the 14 new executed nodes, not a claim that unavailable unchanged modules were rerun in the reduced scratch workspace.

The eight external authority paths bound by `docs/79` remain byte-stable; all **8/8** Git blob SHAs remain bound by the candidate manifest.

The twenty Tenfold lanes remain syntax, identity/persistence, RAB, Git/local state, currentness, hostile matrix, static security, repeated determinism, tamper mutation, workspace non-mutation, strict decode, Git object formats, path attacks, RAB roster, revocation/suspension, symlink identity, generated binding, selected-untracked scope, historical-proof supersession, and full-suite reconciliation.

## Pre-SAE-30 lifecycle boundary

General SAE-30 Qualification Authority machinery does not yet exist and is **not fabricated here**. The pre-SAE-30 bootstrap cannot issue general Qualification Attestations, create external independence, satisfy Genesis, activate a partial Assurance Evolution generation, authorize candidate self-activation, or turn Owner risk acceptance into engineering PASS.

## Residual boundary

This is still **CANDIDATE**. Heads `924d33aa188dff673a9ca7eb7c843b6222e798fe` and `b3c4e409bfb7e0fd498d7790bef3b391f9595755` are explicitly superseded by later hostile findings. Intermediate `0e67e3116e9d7a6a3945550eef3fdf485f25f634` is not freezeable because its candidate bindings are intentionally stale and its stale regex assertion was corrected after complete-tree proof. SAE-10 is not lifecycle-PROVEN until the rebound v6 candidate is published atomically, survives complete-repository and clean-clone proof, survives a fresh exact-head hostile review, is reconciled against current `main`, and the exact reviewed candidate is guarded-merged before a separate immutable SAE-10 PROVEN closeout generation is created and proved. No SAE-20 work may advance across that boundary.
