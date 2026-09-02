# SAE-10 Review World + RAB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the SAE-10 authority layer that gives Sergeant exact immutable Review World identity, exact whole-RAB authorization, local/GitHub snapshot identity, and fail-closed currentness without changing normal verdict authority.

**Architecture:** Add four focused standard-library modules under `main_review/`: canonical identity, RAB authorization, Git/GitHub/local fact derivation, and currentness. Reuse existing validated GitHub transport and repository-path hardening; do not move authority semantics into `PullRequestDiff`, `battle_compare`, or service transport. All authority-bearing IDs are full SHA-256 digests over canonical JSON and all candidate/self-activation paths fail closed.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `hashlib`, `json`, `pathlib`, `subprocess`, `typing`), pytest, existing Sergeant GitHub fetch/hardening helpers.

**Spec:** `docs/superpowers/specs/2026-09-02-sae-10-review-world-rab-design.md`

## Global Constraints

- Preserve existing Sergeant product behavior; SAE-10 construction has no normal verdict authority.
- `SAE-10` proof dependency is PROVEN `SAE-00` only.
- Do not fabricate SAE-20 ACR, SAE-30 Qualification Authority, SAE-R1 Rust identity, or later roadmap authority.
- Every authority-bearing identity is a full lowercase 64-hex SHA-256 digest; truncated IDs are presentation-only and invalid as authority input.
- Canonical JSON is UTF-8, sorted keys, separators `,` and `:`, no NaN/Infinity, with schema version inside the hashed object.
- Historical Review World truth is immutable; later mutation changes currentness, never the historical world object.
- Patch rendering is evidence only; Git object/tree transition plus explicit scope is normative diff identity.
- Whole-RAB authorization is exact-manifest authorization; individually authorized components never authorize a new combination.
- Candidate repository content cannot mutate or replace the verifier-trusted RAB authorization set during its own review.
- No mutable `latest`, `current`, branch-tip, or filename-only authority lookup is allowed.
- Unknown/ambiguous repository, merge, scope, submodule/LFS/generated state fails closed.
- PR #167 remains untouched.

---

## File Structure

- Create `main_review/review_world.py` — canonical encoding, digest validation, scope/diff/Review World immutable value objects.
- Create `main_review/review_authority_bundle.py` — typed RAB component descriptors, immutable RAB manifest, verifier-trusted authorization set, whole-bundle authorization checks.
- Create `main_review/review_world_git.py` — pure Git command adapter and constructors for GitHub PR facts and local snapshots; no network transport duplication.
- Create `main_review/review_world_currentness.py` — currentness comparison and stable invalidation reasons.
- Create `tests/test_review_world_identity.py` — canonical encoding, GitHub-world identity and malformed identity tests.
- Create `tests/test_review_authority_bundle.py` — exact RAB authorization and candidate self-activation hostile tests.
- Create `tests/test_review_world_git.py` — Git tree/diff, merge-tree and local snapshot hostile tests.
- Create `tests/test_review_world_currentness.py` — stale/current/unknown currentness behavior.
- Create `tests/test_sae10_hostile_matrix.py` — frozen roadmap hostile matrix across component boundaries.
- Create `docs/78-sae10-review-world-rab-contract.md` — human-readable candidate authority record after exact-head review proof.
- Create `docs/79-sae10-review-world-rab-manifest.json` — content-bound candidate manifest.
- Create `tests/test_sae10_review_world_rab_manifest.py` — machine proof of candidate authority record.
- Later, after reviewed candidate freeze: create `docs/80-sae10-proven-lifecycle-closeout.md`, `docs/81-sae10-proven-lifecycle-closeout-manifest.json`, and `tests/test_sae10_proven_lifecycle_closeout.py`.

---

### Task 1: Canonical Authority Identity and Review Scope

**Files:**
- Create: `main_review/review_world.py`
- Create: `tests/test_review_world_identity.py`

**Interfaces:**
- Produces: `ReviewWorldError`, `canonical_json_bytes(value: Mapping[str, object]) -> bytes`, `sha256_id(value: Mapping[str, object]) -> str`, `require_full_sha256(value: str, field: str) -> str`, `ReviewScope`, `GitHubDiffIdentity`, `GitHubReviewWorld`, `LocalReviewWorld`.
- Later tasks consume the exact object `to_payload()` methods and IDs from these types.

- [ ] **Step 1: Write failing canonical-identity tests**

```python
import pytest

from main_review.review_world import (
    ReviewScope,
    ReviewWorldError,
    canonical_json_bytes,
    require_full_sha256,
    sha256_id,
)


def test_canonical_json_is_order_independent_for_object_keys():
    left = {"schema_version": "v1", "b": 2, "a": 1}
    right = {"a": 1, "b": 2, "schema_version": "v1"}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert sha256_id(left) == sha256_id(right)


def test_non_json_numbers_fail_closed():
    with pytest.raises(ReviewWorldError, match="non-finite"):
        canonical_json_bytes({"schema_version": "v1", "value": float("nan")})


def test_truncated_authority_digest_is_rejected():
    with pytest.raises(ReviewWorldError, match="64-hex"):
        require_full_sha256("abc123", "rab_id")


def test_scope_paths_are_sorted_unique_and_normalized():
    scope = ReviewScope.selected_paths(["src/b.py", "src/a.py", "src/a.py"])
    assert scope.paths == ("src/a.py", "src/b.py")
    assert len(scope.scope_id) == 64


def test_scope_path_traversal_is_rejected():
    with pytest.raises(ReviewWorldError, match="repository-relative"):
        ReviewScope.selected_paths(["../secret.txt"])
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `pytest -q tests/test_review_world_identity.py -ra`
Expected: import/collection failure because `main_review.review_world` does not exist.

- [ ] **Step 3: Implement canonical encoding and scope identity**

Implement `canonical_json_bytes` with `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`, recursively reject unsupported values, and translate `ValueError` into `ReviewWorldError` with a stable message. Implement full-SHA validation with `re.fullmatch(r"[0-9a-f]{64}", value)`.

Implement immutable `ReviewScope` with fields:

```python
@dataclass(frozen=True)
class ReviewScope:
    schema_version: str
    kind: Literal["repository", "changed_files", "selected_paths"]
    paths: tuple[str, ...]
    generated_artifacts: Literal["excluded", "included", "unresolved"]
    submodules: Literal["excluded", "included", "unresolved"]
    untracked: Literal["excluded", "selected", "all_in_scope", "unresolved"]
    generation: str
    scope_id: str
```

Provide `repository()`, `changed_files(paths)`, and `selected_paths(paths)` constructors. Normalize paths to POSIX repository-relative spelling, reject absolute paths, `..`, empty components and NULs, and sort/deduplicate set-like path lists before hashing.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `pytest -q tests/test_review_world_identity.py -ra`
Expected: all Task-1 tests pass.

- [ ] **Step 5: Add failing GitHub diff/world identity tests**

```python
from main_review.review_world import GitHubDiffIdentity, GitHubReviewWorld

HEX_A = "a" * 40
HEX_B = "b" * 40
TREE_A = "c" * 40
TREE_B = "d" * 40
RAB = "1" * 64


def test_same_head_different_base_changes_diff_and_world_identity():
    scope = ReviewScope.repository()
    first = GitHubDiffIdentity.create(
        repository="owner/repo", base_commit=HEX_A, base_tree=TREE_A,
        head_commit=HEX_B, head_tree=TREE_B, scope=scope,
    )
    second = GitHubDiffIdentity.create(
        repository="owner/repo", base_commit="e" * 40, base_tree="f" * 40,
        head_commit=HEX_B, head_tree=TREE_B, scope=scope,
    )
    assert first.diff_id != second.diff_id
    world_a = GitHubReviewWorld.create(
        repository="owner/repo", pr_number=7, diff=first, scope=scope,
        review_mode="head", rab_id=RAB, review_generation="sae10-v1",
    )
    world_b = GitHubReviewWorld.create(
        repository="owner/repo", pr_number=7, diff=second, scope=scope,
        review_mode="head", rab_id=RAB, review_generation="sae10-v1",
    )
    assert world_a.review_world_id != world_b.review_world_id


def test_patch_rendering_is_not_part_of_diff_identity():
    scope = ReviewScope.repository()
    left = GitHubDiffIdentity.create(
        repository="owner/repo", base_commit=HEX_A, base_tree=TREE_A,
        head_commit=HEX_B, head_tree=TREE_B, scope=scope,
    )
    right = GitHubDiffIdentity.create(
        repository="owner/repo", base_commit=HEX_A, base_tree=TREE_A,
        head_commit=HEX_B, head_tree=TREE_B, scope=scope,
    )
    assert left.diff_id == right.diff_id
```

- [ ] **Step 6: Run the new tests and confirm RED**

Run: `pytest -q tests/test_review_world_identity.py -ra`
Expected: failures because `GitHubDiffIdentity`/`GitHubReviewWorld` are not implemented.

- [ ] **Step 7: Implement immutable GitHub diff/world value objects**

`GitHubDiffIdentity.create(...)` must hash repository, base commit/tree, head commit/tree, algorithm generation `git-tree-transition-v1`, and the exact `scope_id`. Git object IDs accept full lowercase 40-hex SHA-1 or 64-hex SHA-256 because repositories may use either object format; authority IDs remain SHA-256 only.

`GitHubReviewWorld.create(...)` must bind repository, PR number, diff payload, scope payload, review mode (`head` or `merge_result`), optional exact merge commit/tree, `rab_id`, review generation, and unresolved-state tuple. `merge_result` requires a merge tree; positive construction rejects non-empty unresolved state.

- [ ] **Step 8: Run Task-1 tests and commit**

Run: `pytest -q tests/test_review_world_identity.py -ra`
Expected: PASS.

Commit message: `feat(sae-10): add canonical Review World identity`

---

### Task 2: Immutable RAB Manifest and Whole-Bundle Authorization

**Files:**
- Create: `main_review/review_authority_bundle.py`
- Create: `tests/test_review_authority_bundle.py`

**Interfaces:**
- Consumes: `canonical_json_bytes`, `sha256_id`, `require_full_sha256`, `ReviewWorldError`.
- Produces: `RABComponent`, `ReviewAuthorityBundle`, `RABAuthorization`, `RABAuthorizationSet`, `authorize_rab(bundle, authorization_set) -> RABAuthorizationResult`.

- [ ] **Step 1: Write failing exact-RAB tests**

```python
import pytest

from main_review.review_authority_bundle import (
    RABAuthorization,
    RABAuthorizationSet,
    RABComponent,
    ReviewAuthorityBundle,
    authorize_rab,
)


def component(name: str, generation: str) -> RABComponent:
    return RABComponent.active(
        name=name,
        generation=generation,
        content_id=(name[0].lower() if name else "a") * 64,
        authority_domain="sergeant-assurance",
    )


def test_individually_known_components_do_not_authorize_new_combination():
    first = ReviewAuthorityBundle.create(epistemic=component("epistemic", "g1"))
    second = ReviewAuthorityBundle.create(epistemic=component("epistemic", "g2"))
    trusted = RABAuthorizationSet.create([
        RABAuthorization.authorized(first.rab_id, "root-gen-1", "OWNER_ROOT_CONSTITUTIONAL_TCB")
    ])
    result = authorize_rab(second, trusted)
    assert result.authorized is False
    assert result.reason == "rab_not_authorized_as_whole"


def test_exact_rab_id_is_authorized_as_whole():
    bundle = ReviewAuthorityBundle.create(epistemic=component("epistemic", "g1"))
    trusted = RABAuthorizationSet.create([
        RABAuthorization.authorized(bundle.rab_id, "root-gen-1", "OWNER_ROOT_CONSTITUTIONAL_TCB")
    ])
    assert authorize_rab(bundle, trusted).authorized is True
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `pytest -q tests/test_review_authority_bundle.py -ra`
Expected: import failure.

- [ ] **Step 3: Implement fixed RAB slots and exact authorization**

Define the ten frozen slots exactly:

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

`RABComponent` lifecycle states are `active`, `inactive_not_yet_established`, `prohibited`. Active descriptors require exact generation and full content/root SHA-256 identity; inactive/prohibited descriptors require a non-empty basis and forbid a fake active content ID.

`ReviewAuthorityBundle.create(...)` fills omitted future slots as explicit `inactive_not_yet_established` descriptors with fixed pre-SAE generation basis; computes one full `rab_id` over the complete manifest.

`RABAuthorizationSet` is constructed only from passed verifier-trusted records; it does not read repository files. Authorization is exact `rab_id` membership plus non-revoked state.

- [ ] **Step 4: Add failing candidate self-activation tests**

```python

def test_candidate_manifest_cannot_authorize_itself():
    candidate = ReviewAuthorityBundle.create(epistemic=component("epistemic", "candidate-g2"))
    trusted = RABAuthorizationSet.create([])
    assert authorize_rab(candidate, trusted).authorized is False


def test_mutable_alias_is_rejected_as_component_generation():
    with pytest.raises(Exception, match="mutable authority alias"):
        RABComponent.active(
            name="epistemic_constitution",
            generation="latest",
            content_id="a" * 64,
            authority_domain="sergeant-assurance",
        )
```

- [ ] **Step 5: Run focused tests, implement alias/revocation checks, and confirm GREEN**

Run: `pytest -q tests/test_review_authority_bundle.py -ra`
Expected after implementation: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat(sae-10): add exact Review Authority Bundle authorization`

---

### Task 3: GitHub Git-Object Adapter and Merge-Result Identity

**Files:**
- Create: `main_review/review_world_git.py`
- Create: `tests/test_review_world_git.py`

**Interfaces:**
- Consumes: existing `PullRequestDiff` facts; `ReviewScope`, `GitHubDiffIdentity`, `GitHubReviewWorld`; `ReviewAuthorityBundle`.
- Produces: `GitCommandError`, `GitObjectResolver`, `build_github_review_world(...) -> GitHubReviewWorld`.

- [ ] **Step 1: Write failing fake-resolver tests**

Use a resolver protocol rather than invoking Git inside unit tests:

```python
class FakeResolver:
    def __init__(self, mapping):
        self.mapping = mapping
    def tree_for_commit(self, commit):
        return self.mapping[("tree", commit)]
    def synthetic_merge(self, base, head):
        return self.mapping[("merge", base, head)]


def test_github_world_binds_exact_head_tree():
    resolver = FakeResolver({
        ("tree", "a" * 40): "1" * 40,
        ("tree", "b" * 40): "2" * 40,
    })
    world = build_github_review_world(
        repository="owner/repo", pr_number=12,
        base_sha="a" * 40, head_sha="b" * 40,
        scope=ReviewScope.repository(), review_mode="head",
        rab_id="f" * 64, review_generation="sae10-v1", resolver=resolver,
    )
    assert world.diff.base_tree == "1" * 40
    assert world.diff.head_tree == "2" * 40


def test_wrong_merge_tree_cannot_reuse_merge_readiness_world():
    # Build two worlds differing only in synthetic merge tree and assert IDs differ.
    ...
```

Replace the ellipsis in the actual test with two explicit `FakeResolver` mappings and full assertions; do not commit ellipses.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `pytest -q tests/test_review_world_git.py -ra`
Expected: missing adapter symbols.

- [ ] **Step 3: Implement `GitObjectResolver`**

Use `subprocess.run([...], cwd=root, check=False, capture_output=True, text=True)` with argument arrays only. Required commands:

- `git rev-parse <commit>^{tree}` for commit tree identity.
- Synthetic merge generation through a temporary index: `git read-tree -m <base> <head>` is insufficient for true recursive merge semantics, so generation 1 must use `git merge-tree --write-tree <base> <head>` when available and fail closed if it cannot return one unambiguous tree. Do not mutate the checkout.

Stable error messages must distinguish missing object, merge conflict/unavailability, and malformed output.

- [ ] **Step 4: Implement GitHub-world constructor and merge-result requirements**

`build_github_review_world` resolves base/head trees from exact commits. For `review_mode="merge_result"`, require `synthetic_merge(base, head)` and bind the returned tree. For `head`, merge fields are absent.

- [ ] **Step 5: Add repository-substitution and patch-render-independence tests**

Explicitly construct otherwise-identical worlds for `owner/repo-a` and `owner/repo-b`; assert distinct diff/world IDs. Construct the same world with no patch-text parameter at all; this proves patch rendering is outside the authority API.

- [ ] **Step 6: Run focused tests and commit**

Run: `pytest -q tests/test_review_world_git.py tests/test_review_world_identity.py -ra`
Expected: PASS.

Commit message: `feat(sae-10): bind GitHub Review Worlds to exact Git objects`

---

### Task 4: Local Snapshot Identity

**Files:**
- Modify: `main_review/review_world.py`
- Modify: `main_review/review_world_git.py`
- Extend: `tests/test_review_world_git.py`

**Interfaces:**
- Produces: `LocalPathState`, `LocalSnapshot`, `LocalSnapshotPolicy`, `build_local_review_world(root, scope, policy, rab_id, review_generation, resolver) -> LocalReviewWorld`.

- [ ] **Step 1: Write failing local mutation and untracked-policy tests**

Use `tmp_path` plus a real temporary Git repository where Git is available; mark Git-dependent tests with `pytest.mark.skipif(shutil.which("git") is None, ...)` rather than weakening semantics.

```python

def test_local_selected_file_mutation_changes_snapshot_id(tmp_path):
    # init repo, commit src/a.txt, build snapshot, mutate selected file, rebuild
    assert first.local_snapshot_id != second.local_snapshot_id


def test_untracked_policy_changes_snapshot_identity(tmp_path):
    # same repository with extra.txt untracked
    excluded = build_local_review_world(... policy=LocalSnapshotPolicy.exclude_untracked())
    included = build_local_review_world(... policy=LocalSnapshotPolicy.include_all_untracked_in_scope())
    assert excluded.local_snapshot_id != included.local_snapshot_id
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `pytest -q tests/test_review_world_git.py -ra`
Expected: missing local snapshot APIs.

- [ ] **Step 3: Implement deterministic local census**

For selected scope derive:

- HEAD commit/tree via `git rev-parse` when available;
- index entries via `git ls-files -s -z`;
- tracked worktree membership/status via `git status --porcelain=v1 -z --untracked-files=all` plus direct content SHA-256 over regular file bytes;
- symlink content via `os.readlink` encoded as UTF-8/surrogateescape-safe bytes;
- Gitlink/submodule entries from mode `160000` and status; dirty/unavailable material submodule is unresolved;
- untracked files according to explicit policy.

Do not bind mtime, inode or absolute path. Canonical path entries sort by normalized repository-relative path.

- [ ] **Step 4: Add fail-closed LFS/generated/submodule tests**

Test pure policy behavior without requiring an LFS server:

```python

def test_material_lfs_pointer_without_object_identity_is_unresolved(tmp_path):
    # create a file with standard git-lfs pointer header under a policy declaring LFS material
    with pytest.raises(ReviewWorldError, match="LFS"):
        build_local_review_world(...)


def test_material_generated_state_without_binding_is_unresolved(tmp_path):
    policy = LocalSnapshotPolicy(... generated_state="material_unbound")
    with pytest.raises(ReviewWorldError, match="generated"):
        build_local_review_world(...)
```

- [ ] **Step 5: Run focused tests and commit**

Run: `pytest -q tests/test_review_world_git.py -ra`
Expected: PASS (or explicit Git-only skips on a host without Git).

Commit message: `feat(sae-10): add content-addressed local Review Worlds`

---

### Task 5: Currentness and Explicit Invalidation

**Files:**
- Create: `main_review/review_world_currentness.py`
- Create: `tests/test_review_world_currentness.py`

**Interfaces:**
- Consumes frozen Review World objects, freshly derived comparison objects, and an optional current RAB authorization result.
- Produces: `CurrentnessState` (`CURRENT`, `STALE`, `UNKNOWN_CURRENTNESS`), `InvalidationReason`, `CurrentnessResult`, `check_github_currentness`, `check_local_currentness`.

- [ ] **Step 1: Write failing stale/current tests**

```python

def test_exact_identical_world_is_current():
    result = check_github_currentness(frozen, frozen, rab_authorized=True)
    assert result.state == "CURRENT"
    assert result.reasons == ()


def test_same_head_different_base_is_stale_with_specific_reason():
    result = check_github_currentness(frozen, changed_base_world, rab_authorized=True)
    assert result.state == "STALE"
    assert "base_identity_mismatch" in result.reasons


def test_unknown_live_fact_returns_unknown_currentness_not_current():
    result = check_github_currentness(frozen, None, rab_authorized=True)
    assert result.state == "UNKNOWN_CURRENTNESS"
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_review_world_currentness.py -ra`
Expected: import failure.

- [ ] **Step 3: Implement explicit comparison law**

Return all material mismatches, not first mismatch only. Stable reason vocabulary:

`repository_mismatch`, `base_identity_mismatch`, `head_identity_mismatch`, `diff_identity_mismatch`, `scope_mismatch`, `merge_result_mismatch`, `local_snapshot_mutation`, `rab_mismatch`, `rab_unauthorized_or_revoked`, `review_generation_mismatch`, `unresolved_material_state`.

`None`/unobtainable comparison facts produce `UNKNOWN_CURRENTNESS`; they never silently count as equal.

- [ ] **Step 4: Prove historical object immutability**

Test that calling currentness does not mutate `frozen.to_payload()` or its `review_world_id` when current facts differ.

- [ ] **Step 5: Run focused tests and commit**

Run: `pytest -q tests/test_review_world_currentness.py tests/test_review_world_identity.py tests/test_review_authority_bundle.py -ra`
Expected: PASS.

Commit message: `feat(sae-10): add Review World currentness and invalidation`

---

### Task 6: Frozen SAE-10 Hostile Matrix

**Files:**
- Create: `tests/test_sae10_hostile_matrix.py`

**Interfaces:**
- Consumes all Task 1-5 public APIs.
- Produces no production API; this is the cross-boundary falsification gate required by the frozen roadmap.

- [ ] **Step 1: Add the six roadmap-required hostile attacks as named tests**

Tests must be named exactly enough to recover intent:

```python
def test_sae10_same_head_different_base_cannot_reuse_positive_world(): ...
def test_sae10_wrong_merge_tree_invalidates_merge_readiness_world(): ...
def test_sae10_local_mutation_after_snapshot_is_stale_not_rewritten(): ...
def test_sae10_scope_downgrade_cannot_satisfy_repository_world(): ...
def test_sae10_unauthorized_rab_combination_fails_even_when_components_are_known(): ...
def test_sae10_candidate_attempt_to_alter_active_review_authority_has_zero_effect(): ...
```

Replace every ellipsis with concrete constructors and assertions before commit.

- [ ] **Step 2: Add the nine design-level boundary controls**

Add tests for deterministic identical world ID, patch-render independence, repository substitution, truncated ID rejection, no `latest` substitution, local untracked-policy identity, unresolved submodule/LFS/generated state, revoked RAB currentness, and malformed canonical-object rejection.

- [ ] **Step 3: Run the complete SAE-10 component test set**

Run:

`pytest -q tests/test_review_world_identity.py tests/test_review_authority_bundle.py tests/test_review_world_git.py tests/test_review_world_currentness.py tests/test_sae10_hostile_matrix.py -ra`

Expected: PASS with only environment-specific Git tests skipped if `git` is genuinely unavailable.

- [ ] **Step 4: Run the repository full suite**

Run: `pytest -q -ra`
Expected: no new failures; the existing strictly-scoped historical SAE-00 XFAIL may remain.

- [ ] **Step 5: Commit**

Commit message: `test(sae-10): freeze Review World and RAB hostile matrix`

---

### Task 7: Candidate Authority Record and Machine Manifest

**Files:**
- Create: `docs/78-sae10-review-world-rab-contract.md`
- Create: `docs/79-sae10-review-world-rab-manifest.json`
- Create: `tests/test_sae10_review_world_rab_manifest.py`

**Interfaces:**
- Consumes exact implementation blob IDs, SAE-00 proven authority record, frozen roadmap/spec, and exact tested branch head.
- Produces candidate-only authority record; lifecycle state remains `CANDIDATE` until hostile review and proof are complete.

- [ ] **Step 1: Write the candidate record from recovered facts**

`docs/78` must state:

- exact canonical main construction base `b5dd07b6a0d2cfed42a111750c0c2df6559a0fb5` unless main has legitimately advanced and branch is reconciled before freeze;
- exact design/spec path;
- each production module and its role;
- exact hostile matrix results actually observed;
- no normal verdict integration/authority yet;
- pre-SAE-30 bootstrap boundary;
- every unresolved residual gap.

Do not put anticipated pass counts or placeholder SHAs into the record.

- [ ] **Step 2: Write the machine manifest with Git blob identities**

Manifest schema: `sergeant.sae10-review-world-rab-candidate.v1`.

It must bind `docs/78`, four production modules, five SAE-10 test files, the design spec, frozen architecture/roadmap, and SAE-00 PROVEN lifecycle record. Use Git blob SHAs from the exact candidate tree, not raw working-tree byte hashes.

- [ ] **Step 3: Write manifest tests before considering it frozen**

Tests verify:

- lifecycle state is exactly `CANDIDATE`;
- proof dependency is exactly `SAE-00`;
- `produces` is exactly `QUALIFIED_REVIEW_WORLD_CONTRACT` and `QUALIFIED_RAB_CONTRACT` as candidate outputs, not active normal authority;
- every listed blob matches `git hash-object`/canonical Git blob identity when history is present, with a depth-1-safe fallback to content identity for current-tree files;
- required hostile test names exist;
- candidate record explicitly states no self-activation and no SAE-30 fabrication.

- [ ] **Step 4: Run candidate manifest test and full suite**

Run: `pytest -q tests/test_sae10_review_world_rab_manifest.py -ra`
Then: `pytest -q -ra`
Expected: PASS except the known historical SAE-00 XFAIL.

- [ ] **Step 5: Commit and open the SAE-10 construction PR**

Commit message: `docs(sae-10): bind Review World and RAB candidate authority`

PR title: `SAE-10: establish exact Review World and RAB contracts`

PR body must explicitly list the six required hostile attacks, current candidate head, test result, changed-file scope, and the fact that the PR does not activate normal verdict authority.

---

### Task 8: Hostile Review, Candidate Freeze, and PROVEN Lifecycle Closeout

**Files:**
- Review/fix any files from Tasks 1-7 as findings require.
- Create after candidate freeze: `docs/80-sae10-proven-lifecycle-closeout.md`
- Create after candidate freeze: `docs/81-sae10-proven-lifecycle-closeout-manifest.json`
- Create: `tests/test_sae10_proven_lifecycle_closeout.py`

**Interfaces:**
- Consumes exact reviewed candidate head and dispositioned review threads.
- Produces SAE-10 lifecycle closeout only; does not auto-qualify SAE-20/30/40/R1/50/110.

- [ ] **Step 1: Recover and disposition every live review thread**

For each finding, classify it as valid/invalid from evidence. Valid findings require a failing regression test first, then minimal implementation correction, then exact-head execution proof. Do not resolve a valid thread before the corrected test suite passes.

- [ ] **Step 2: Freeze the reviewed candidate head**

Required evidence before freeze:

- branch is 0 commits behind canonical `main` or has been reconciled and re-proven;
- changed-file scope contains only SAE-10 design/plan/modules/tests/docs plus any narrowly justified shared test-infrastructure correction;
- all review threads resolved;
- focused SAE-10 suite green;
- full suite green except the one deliberate historical SAE-00 XFAIL;
- clean-clone proof chain green when Actions are available; if Actions are unavailable, record the exact infrastructure gap and rely only on evidence actually recovered.

- [ ] **Step 3: Write lifecycle closeout as a new immutable generation**

`docs/80` must preserve `docs/78`/`docs/79` as the historical candidate generation. It records the exact reviewed candidate head and the bounded bootstrap authority: PROVEN SAE-00 roadmap execution authority plus Owner/Root constitutional TCB.

It must explicitly state that bootstrap cannot issue general Qualification Attestations, create external independence, satisfy Genesis, authorize candidate self-activation, or activate later nodes.

- [ ] **Step 4: Write closeout manifest and failing proof test**

Manifest schema: `sergeant.sae10-proven-lifecycle-closeout.v1`.

Bind the exact candidate head, candidate doc/manifest blobs, `docs/80`, the final proof fixture blob, SAE-00 proven merge, and exact roadmap outputs. Use a temporary impossible fixture digest first so the new proof test is RED.

- [ ] **Step 5: Bind the proof fixture content and turn GREEN**

Content-address `tests/test_sae10_proven_lifecycle_closeout.py`, update the manifest with that exact blob ID, then run:

`pytest -q tests/test_sae10_proven_lifecycle_closeout.py -ra`

Expected: PASS.

- [ ] **Step 6: Run final exact-head proof**

Run focused SAE-10 suite, then `pytest -q -ra`, then existing Sergeant proof gates (`main-review scan --pretty`, `main-review evidence --pretty`, `main-review review --pretty`, `main-review verify-standard --pretty`, `main-review final-proof --pretty`, `main-review proof-suite --pretty`) when the execution environment exposes them.

Do not infer missing execution evidence.

- [ ] **Step 7: Guarded merge**

Before merge re-read PR metadata, compare `main...head`, review threads, and exact-head workflow/test evidence. Merge only with an expected-head guard. Record the canonical merge commit in recovery authority after merge; do not rewrite the historical candidate generation.

Commit title: `SAE-10: prove exact Review World and RAB contracts`

---

## Plan Self-Review Result

- Spec coverage: all design sections are mapped—canonical encoding, GitHub world, merge result, explicit scope, local snapshot, untracked/submodule/LFS/generated state, immutable RAB, whole-RAB authorization, pre-SAE-30 bootstrap, non-self-activation, currentness, fail-closed errors, hostile matrix, integration boundary, and lifecycle closeout.
- Placeholder scan: implementation steps prohibit committed ellipses and placeholders; candidate/lifecycle records are explicitly forbidden from anticipated pass counts or fake SHAs.
- Type consistency: `ReviewScope`, `GitHubDiffIdentity`, `GitHubReviewWorld`, `LocalReviewWorld`, `ReviewAuthorityBundle`, `RABAuthorizationSet`, and currentness APIs are defined once and consumed under the same names throughout later tasks.
- Scope: one coherent SAE-10 subsystem; no SAE-20/30 implementation is included.
