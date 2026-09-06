# SAE-10 Review World + RAB Implementation Plan

> **Execution discipline:** Understand → Build → Review → Freeze → Prove → Ship. This plan is subordinate to the frozen SAE roadmap and the SAE-10 design contract. It establishes Review World and Review Authority Bundle machinery only; it does not activate normal Sergeant verdict authority or fabricate SAE-20/30+ authority.

## Goal

Implement an exact, immutable authority layer for GitHub and local Review Worlds, whole-RAB authorization, and fail-closed currentness. Every authority-bearing identity is content-addressed. Patch rendering is evidence only; Git object/tree transition plus explicit scope is normative. Historical Review Worlds never mutate when later repository state changes.

## Global constraints

- SAE-10 proof dependency is exactly proven SAE-00.
- Full authority IDs are lowercase 64-hex SHA-256 digests; Git object IDs may be full lowercase SHA-1 or SHA-256 according to repository object format.
- Canonical JSON is UTF-8, sorted-key, compact-separator, finite-number-only encoding with schema version inside the hashed payload.
- Unknown or ambiguous repository, merge, scope, submodule, LFS, generated-state, authorization, or currentness facts fail closed.
- Whole-RAB authorization is exact-manifest authorization. Known components do not authorize a new combination.
- Candidate repository content cannot self-authorize or replace verifier-trusted authorization state.
- Mutable aliases such as `latest`, `current`, branch tip, or filename-only authority references are invalid authority inputs.
- Git subprocesses must execute with an explicit allowlisted environment and must not inherit caller-controlled Git metadata including `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, or alternate-object-directory controls.
- PR #167 remains untouched.

## Task 1 — Canonical Review World identity

**Files:**
- `main_review/review_world.py`
- `tests/test_review_world_identity.py`
- `tests/test_review_world_persistence.py`

Implement and prove:

- `ReviewWorldError`
- `canonical_json_bytes(value)`
- `sha256_id(value)`
- `require_full_sha256(value, field)`
- `ReviewScope`
- `GitHubDiffIdentity`
- `GitHubReviewWorld`
- `LocalReviewWorld`

`ReviewScope` must normalize repository-relative POSIX paths, sort/deduplicate constructor inputs, reject absolute/traversal/NUL paths, and reject duplicate normalized entries when decoding an authority payload. GitHub world identity binds repository, PR, exact base/head commits and trees, exact scope, review mode, RAB ID, review generation, and merge-result tree when applicable. Local world identity binds exact local snapshot identity, scope, RAB ID, and review generation.

Proof command:

```bash
python -m pytest -q tests/test_review_world_identity.py tests/test_review_world_persistence.py -ra
```

## Task 2 — Immutable RAB manifest and whole-bundle authorization

**Files:**
- `main_review/review_authority_bundle.py`
- `tests/test_review_authority_bundle.py`

The frozen RAB slots are exactly:

```python
RAB_SLOTS = (
    "epistemic_constitution",
    "safety_constitution",
    "acr_generation",
    "capability_passport_registry",
    "obligation_law",
    "evidence_law",
    "independence_law",
    "rust_contract_kernel",
    "qualification_authority_registry",
    "root_authority",
)
```

Implement typed component descriptors, immutable bundle construction, verifier-trusted authorization records/sets, and `authorize_rab(bundle, authorization_set)`. Active descriptors require exact generation/content identity. Inactive/prohibited descriptors require a non-empty basis and cannot masquerade as active content. Authorization records must validate their state and only a record whose state is exactly `authorized` may authorize an exact `rab_id`; revoked, suspended, malformed, missing, or mismatched records fail closed.

Proof command:

```bash
python -m pytest -q tests/test_review_authority_bundle.py -ra
```

## Task 3 — Exact Git/GitHub fact derivation

**Files:**
- `main_review/review_world_git.py`
- `tests/test_review_world_git.py`

Implement `GitObjectResolver`, GitHub Review World builders, and exact local snapshot derivation. Required Git operations include exact commit-tree resolution and recursive merge-tree generation. Synthetic merge identity must use Git merge semantics and fail closed if one unambiguous result tree cannot be produced. Do not mutate the checkout.

Local snapshots bind HEAD commit/tree, index entries, tracked worktree content, symlink targets, submodule state, selected/untracked policy, LFS policy, and generated-state policy. Material-required states without material identity are unresolved.

All subprocesses use only the module's explicit environment allowlist; inherited Git metadata is excluded.

Proof command:

```bash
python -m pytest -q tests/test_review_world_git.py -ra
```

## Task 4 — Fail-closed currentness

**Files:**
- `main_review/review_world_currentness.py`
- `tests/test_review_world_currentness.py`

Implement `CurrentnessState`, `InvalidationReason`, `CurrentnessResult`, `check_github_currentness`, and `check_local_currentness`. Compare all material identity dimensions and return every material mismatch. Missing live facts yield `UNKNOWN_CURRENTNESS`, never silent equality. Historical frozen objects remain immutable. Stable reason vocabulary must cover repository/base/head/diff/scope/merge/local-snapshot/RAB/review-generation/unresolved-material mismatches.

Proof command:

```bash
python -m pytest -q tests/test_review_world_currentness.py -ra
```

## Task 5 — Cross-boundary hostile matrix

**File:** `tests/test_sae10_hostile_matrix.py`

The required named attacks are:

1. same head, different base cannot reuse a positive world;
2. wrong merge tree invalidates merge-readiness world;
3. local mutation after snapshot becomes stale without rewriting history;
4. scope downgrade cannot satisfy repository-wide Review World;
5. unauthorized RAB combination fails even when components are individually known;
6. candidate attempt to alter active review authority has zero effect.

Also prove deterministic identity, patch-render independence, repository substitution resistance, truncated-authority rejection, no mutable-alias substitution, untracked-policy identity, unresolved submodule/LFS/generated-state failure, revoked/suspended RAB behavior, symlink identity, selected-untracked policy, strict canonical round-trip, duplicate decoded-scope rejection, and Git environment metadata isolation.

Proof command:

```bash
python -m pytest -q tests/test_sae10_hostile_matrix.py -ra
```

## Task 6 — Historical SPIKE-SEM compatibility without weakening SAE-10

**Files:**
- `tests/conftest.py`
- `tests/spike_sem/test_semantic_feasibility_probe.py` (historical authority fixture; byte-preserved)
- `tests/test_spike_sem_historical_metric_supersession.py`

Preserve the historical fixture bytes exactly. The compatibility layer may classify only the exact historical node and must mechanically prove that node receives `strict=True`; it must not broaden XFAIL behavior to other tests or alter the historical fixture itself.

Proof command:

```bash
python -m pytest -q tests/test_spike_sem_historical_metric_supersession.py -ra
```

## Task 7 — Candidate authority record and exact manifest

**Files:**
- `docs/78-sae10-review-world-rab-contract.md`
- `docs/79-sae10-review-world-rab-manifest.json`
- `tests/test_sae10_review_world_rab_manifest.py`

The manifest lifecycle remains exactly `CANDIDATE`, proof dependency exactly `["SAE-00"]`, and `normal_verdict_authority` exactly `false`. Its `content_blobs` mapping must equal the exact repository-confined SAE-10 content roster and each value must equal `git hash-object` for that path. The frozen historical SPIKE-SEM fixture is bound separately as external authority content and must remain byte-identical.

Record every valid hostile-review finding and its actual repair. No anticipated pass counts, placeholder SHAs, self-activation, SAE-30 authority, or general Qualification Attestation may be fabricated.

Proof command:

```bash
python -m pytest -q tests/test_sae10_review_world_rab_manifest.py -ra
```

## Task 8 — Review, freeze, prove, close out, ship

Before candidate freeze:

- branch is reconciled with canonical main;
- changed-file scope is SAE-10-only except narrowly justified shared test infrastructure;
- every live hostile-review thread is dispositioned from evidence;
- focused SAE-10 suite is green;
- complete available repository proof is green except only an explicitly preserved historical expected-failure contract;
- Tenfold formation lanes are all green and recorded;
- no normal verdict authority has been activated.

Focused candidate proof:

```bash
python -m pytest -q \
  tests/test_review_world_identity.py \
  tests/test_review_world_persistence.py \
  tests/test_review_authority_bundle.py \
  tests/test_review_world_git.py \
  tests/test_review_world_currentness.py \
  tests/test_sae10_hostile_matrix.py \
  tests/test_spike_sem_historical_metric_supersession.py \
  tests/test_sae10_review_world_rab_manifest.py -ra
```

After the reviewed candidate head is frozen, create a new immutable lifecycle generation:

- `docs/80-sae10-proven-lifecycle-closeout.md`
- `docs/81-sae10-proven-lifecycle-closeout-manifest.json`
- `tests/test_sae10_proven_lifecycle_closeout.py`

The closeout binds the exact reviewed candidate head, candidate doc/manifest blobs, closeout proof fixture, proven SAE-00 dependency, dispositioned review state, and roadmap output boundary. Bootstrap authority cannot issue general Qualification Attestations, create external independence, satisfy Genesis, authorize self-activation, or activate later nodes.

Final proof must run the focused SAE-10 suite, repository suite/gates actually available in the execution environment, and all Tenfold lanes. Missing external execution evidence is recorded as missing; it is never inferred.

Only after the exact published head matches the frozen candidate and review state is clean may the guarded merge proceed. Record the resulting canonical merge commit without rewriting the historical candidate generation.

## Plan self-review

- Scope is one coherent SAE-10 subsystem; SAE-20/30+ construction is excluded.
- All ten RAB slots use the frozen names, including `epistemic_constitution`.
- Authority identity, whole-RAB authorization, exact local/GitHub state, UNKNOWN conservation, hostile falsification, candidate nonactivation, historical compatibility, and lifecycle closeout are explicitly covered.
- No placeholder authority IDs or forecasted proof results are introduced.
