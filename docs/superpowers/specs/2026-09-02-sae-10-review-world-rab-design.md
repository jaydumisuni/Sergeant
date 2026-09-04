# SAE-10 — Review World + Review Authority Bundle Design

Date: 2026-09-02
Status: DESIGN FREEZE CANDIDATE — IMPLEMENTATION NOT STARTED
Roadmap node: `SAE-10 — Review World + Review Authority Bundle`
Proof dependency: `SAE-00`
Produces: `QUALIFIED_REVIEW_WORLD_CONTRACT`, `QUALIFIED_RAB_CONTRACT`
Authority gain during construction: isolated Assurance Evolution construction only; no normal Sergeant verdict authority

## 1. Purpose

SAE-10 establishes the authority-bearing identity boundary for every future Assurance Evolution review. It does not replace Sergeant's existing GitHub fetch, patch review, standalone mission, Cpl, officer, Judge, or verdict machinery. It creates a separate immutable contract that those mechanisms may later bind to.

A review result is meaningful only for one exact Review World and one exact Review Authority Bundle (RAB). A positive result may never be reused merely because filenames, head SHA, policy names, or individual authority components appear compatible.

The implementation must satisfy the frozen founding architecture and roadmap without importing future SAE-20/SAE-30 authority prematurely.

## 2. Recovered existing substrate

The following current mechanisms are preserved and reused rather than reimplemented:

- `main_review/github_diff_fetch.py` already performs validated read-only GitHub PR ingestion and records repository identity, PR number, base SHA, head SHA, changed-file metadata and request evidence.
- `main_review/battle_compare.py` already materializes untrusted PR patch text only inside a temporary sandbox and keeps battle comparison blind to existing review comments by default.
- `main_review/service.py` already constrains standalone review missions to read-only execution and normalizes changed-file scope.
- Existing modules already use canonical JSON serialization and SHA-256 for content-addressed records in several non-authority subsystems.

These are transport, sandboxing and presentation substrates. They do not currently define Review World authority, candidate-tree identity, canonical diff identity, merge-result identity, local snapshot identity, whole-RAB authorization, non-self-activation, or currentness/invalidation.

SAE-10 fills that exact gap.

## 3. Selected architecture

SAE-10 adds a new authority layer with four isolated components:

1. `review_world.py` — canonical Review World schemas, encoding and identity.
2. `review_world_git.py` — Git/GitHub and local-snapshot fact derivation adapters.
3. `review_authority_bundle.py` — immutable RAB schema, whole-bundle identity and authorization verification.
4. `review_world_currentness.py` — currentness checks and explicit invalidation reasons.

The existing fetch/review modules may later call these components, but SAE-10 does not fold authority semantics into `PullRequestDiff`, `battle_compare`, or service transport objects.

This separation is intentional:

- network/API facts are not authority by themselves;
- patch text is not the normative diff identity;
- transport compatibility is not RAB authorization;
- candidate content cannot mutate the verifier's active authority set;
- historical Review World truth remains immutable even after currentness is lost.

## 4. Canonical encoding and IDs

Authority-bearing objects use a frozen canonical JSON encoding:

- UTF-8;
- JSON object keys sorted lexicographically;
- separators `,` and `:` with no insignificant whitespace;
- Unicode preserved as UTF-8 rather than escaped solely for presentation;
- no NaN/Infinity/non-JSON values;
- schema version included inside the hashed object;
- arrays retain declared order only where order is semantically part of the contract;
- sets are encoded as sorted duplicate-free arrays after validation.

Every authority ID is the full lowercase 64-hex SHA-256 digest of the canonical encoded object. Truncated hashes may be rendered for UI only and are never accepted as authority-bearing input.

Initial IDs:

- `review_world_id = sha256(canonical_review_world_without_id)`;
- `diff_id = sha256(canonical_diff_identity)`;
- `scope_id = sha256(canonical_scope)`;
- `local_snapshot_id = sha256(canonical_local_snapshot)`;
- `rab_id = sha256(canonical_rab_manifest_without_id)`;
- `rab_authorization_set_id = sha256(canonical_authorization_set_without_id)`.

Self-referential ID fields are excluded from their own digest input and are verified on decode.

## 5. GitHub/PR Review World

A GitHub/PR Review World contains at minimum:

- schema version;
- review-world kind `github_pr`;
- normalized repository identity `owner/name`;
- PR number when the world originates from a PR;
- base commit SHA;
- base tree SHA;
- head commit SHA;
- head/candidate tree SHA;
- canonical diff identity;
- explicit scope;
- review mode;
- RAB ID;
- review generation;
- optional synthetic merge-result commit/tree identity when the claimed world is merge readiness;
- unresolved-state declarations, which must be empty for a positive exact world.

### 5.1 Repository identity

Repository identity is normalized once and included in every authority-bearing GitHub identity. A commit SHA from another repository is not substitutable merely because the object ID is identical or reachable through a fork.

### 5.2 Candidate tree identity

The candidate tree identity is the exact Git tree referenced by the reviewed head commit. Head commit identity and tree identity are both retained because commit metadata and content tree answer different questions.

### 5.3 Canonical diff identity

Patch formatting is not normative. GitHub may omit binary patches, truncate large patches, or render textual diffs differently while the underlying Git transition is unchanged.

The canonical diff identity is therefore a typed digest over:

- repository identity;
- base commit SHA and base tree SHA;
- head commit SHA and head tree SHA;
- frozen diff-identity algorithm generation;
- explicit review scope.

For SAE-10 generation 1, Git's exact base/head tree transition is the normative source of diff identity. Optional changed-entry manifests may be attached as evidence but do not replace the base/head tree binding.

This makes same-head/different-base a different `diff_id` by construction.

### 5.4 Merge-result identity

A merge-readiness Review World must additionally contain the exact synthetic merge-result tree it is judging. A head-tree review and a merge-result review are different worlds even when they reference the same PR.

If the synthetic merge result cannot be produced unambiguously, the merge-result world cannot be constructed as exact and must fail closed.

The current GitHub API `merge_commit_sha` is not trusted blindly as equivalent to a synthetic merge tree. The adapter must resolve the tree identity belonging to the exact merge-result object used by the claim.

### 5.5 Explicit scope

Scope is an authority-bearing object, not an informal file list. It records:

- scope kind: repository / changed-files / selected-paths;
- normalized repository-relative paths when applicable;
- inclusion/exclusion semantics;
- whether generated artifacts, submodules and untracked files are eligible;
- scope generation.

A narrower scope is never substitutable for a broader one. Scope equality is exact unless a later qualified contract explicitly defines a safe relation; SAE-10 does not invent such subsumption.

## 6. Local Review World and snapshot identity

A local Review World binds the exact declared local state rather than pretending local review is equivalent to a clean GitHub head.

Generation 1 local snapshot contains:

- repository identity when available;
- HEAD commit SHA or explicit unborn/detached state;
- HEAD tree SHA when available;
- index entry manifest for the selected scope;
- tracked worktree content manifest for the selected scope;
- explicit untracked-file policy and, when included, untracked content manifest;
- submodule/gitlink state for the selected scope;
- LFS state disposition;
- generated-state disposition;
- selected-scope digest;
- local snapshot ID;
- RAB ID and review generation.

### 6.1 Local content manifest

For each selected path, canonical entries bind at least:

- normalized path;
- object kind/mode;
- index Git object ID when applicable;
- worktree SHA-256 content digest when applicable;
- state classification such as unchanged/modified/deleted/untracked/type-changed;
- symlink target content where the platform exposes it deterministically.

File mtimes, inode numbers and absolute paths are not authority-bearing because they are host artifacts rather than content identity.

### 6.2 Untracked policy

The Review World must explicitly choose one of:

- `exclude_untracked` — untracked files are outside declared scope and this fact is bound;
- `include_selected_untracked` — only explicitly selected untracked files are bound;
- `include_all_untracked_in_scope` — all untracked members beneath the declared scope are bound.

There is no implicit ignore of untracked state for repository-wide positive review.

### 6.3 Submodule, LFS and generated-state ambiguity

SAE-10 generation 1 fails closed when an exact selected-scope identity cannot be established.

- A submodule entry binds the gitlink commit plus a clean/dirty/unresolved disposition. Dirty or unavailable required submodule content is unresolved.
- An LFS pointer without the required object-content identity is unresolved when review claims the materialized file semantics.
- Generated state that is declared material but not reproducibly or explicitly bound is unresolved.

These unresolved conditions invalidate exact positive reuse rather than being silently skipped.

## 7. Review Authority Bundle

Every Review World binds exactly one immutable RAB.

The RAB manifest contains fixed named slots for the authority generations required by the founding architecture:

- epistemic constitution;
- safety constitution;
- ACR generation;
- capability/passport registry generation;
- obligation law generation;
- evidence law generation;
- independence law generation;
- Rust contract/kernel generation;
- qualification-authority registry generation;
- Root authority generation.

Each slot is a typed descriptor with:

- component name;
- lifecycle state for this RAB (`active`, `inactive_not_yet_established`, or `prohibited`);
- exact generation identifier when active;
- exact content/root identity when active;
- reason/basis when inactive;
- authority-domain label.

Generation-1 SAE-10 does not fabricate SAE-20, SAE-30, SAE-R1 or later mechanisms. Those slots are explicitly `inactive_not_yet_established` until the relevant roadmap node creates qualified authority. This inactive state is itself part of the RAB digest.

No lookup of `latest`, `latest compatible`, branch tip, filename alone or mutable registry alias is permitted during a frozen review.

## 8. Whole-RAB authorization

Component-level acceptability does not authorize a combination.

The verifier receives an authorization set from outside candidate-controlled content. An authorization record contains the exact full `rab_id`, authorization state, authorization generation, and root basis.

A RAB is usable only if:

1. its canonical encoding verifies its full `rab_id`;
2. every active component descriptor verifies its own exact generation/content identity;
3. the exact `rab_id` appears in the verifier-trusted authorization set as authorized;
4. no revocation/invalidation entry applies;
5. the Review World binds exactly that same `rab_id`.

Two independently authorized components combined into a never-authorized manifest must fail.

The candidate repository may carry proposed future RAB manifests for review, but candidate-controlled files are never themselves the verifier's active authorization source.

## 9. Bootstrap boundary before SAE-30

SAE-10 itself depends only on PROVEN SAE-00. SAE-30's general Qualification Authority substrate does not yet exist and must not be invented early.

For SAE-10 construction and lifecycle qualification only, the design uses the already-established pre-SAE-30 bootstrap boundary:

- PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY`;
- founding Owner/Root constitutional TCB.

This bootstrap may determine whether the exact SAE-10 generation satisfies its frozen roadmap charter. It cannot:

- issue a general Qualification Attestation;
- qualify unrelated future nodes;
- create external independence;
- satisfy Genesis;
- activate a partial Assurance Evolution generation;
- turn candidate RAB content into active review authority;
- turn Owner business risk acceptance into engineering PASS.

Runtime RAB authorization remains a distinct exact-manifest verification problem even during this bootstrap generation.

## 10. Candidate-policy non-self-activation

A frozen review evaluates candidate changes under the RAB selected before candidate content can influence authority selection.

The following are forbidden:

- reading a candidate-modified policy file and automatically replacing the active RAB;
- promoting a candidate RAB because all of its component generations are individually known;
- resolving mutable names such as `current`, `latest` or branch tips after Review World freeze;
- allowing candidate code to mutate the trusted RAB authorization set during its own review.

Candidate authority changes may be reported as proposed future authority only. A later separately authorized review world may activate them after the required roadmap process.

## 11. Currentness and invalidation

Historical verdict truth is immutable for the exact Review World that produced it. Currentness is a separate derived check.

Currentness verification accepts a frozen Review World plus freshly derived facts and returns one of:

- `CURRENT`;
- `STALE` with one or more explicit invalidation reasons;
- `UNKNOWN_CURRENTNESS` when the required comparison fact cannot be obtained.

Initial invalidation reasons include:

- repository mismatch;
- base commit/tree mismatch;
- head commit/tree mismatch;
- diff identity mismatch;
- scope mismatch;
- merge-result mismatch;
- local snapshot mutation;
- RAB mismatch;
- RAB unauthorized/revoked;
- unresolved submodule/LFS/generated state;
- review-generation mismatch.

The verifier never rewrites the frozen Review World in place and never silently upgrades it to newer authority.

## 12. Data flow

### 12.1 GitHub PR review

1. Existing validated GitHub fetch obtains repository/PR/base/head facts.
2. SAE-10 Git adapter resolves exact commit/tree identities and constructs the canonical scope.
3. The adapter constructs `diff_id` from the exact repository/base/head/tree/scope transition.
4. If merge readiness is claimed, the exact synthetic merge-result tree is resolved and bound.
5. A preselected verifier-trusted RAB is canonicalized and authorized as a whole.
6. Review World is canonicalized, receives the full `rab_id`, and receives its full `review_world_id`.
7. Existing Sergeant review mechanisms may consume the scope/evidence, but their verdict must later be attached to this immutable world rather than to mutable PR state.

### 12.2 Local review

1. Normalize the declared repository-local scope.
2. Derive HEAD/index/worktree/untracked/submodule/LFS/generated-state facts according to explicit policy.
3. Fail closed on required unresolved identity.
4. Canonicalize the local snapshot and compute `local_snapshot_id`.
5. Verify the selected RAB as a whole.
6. Build immutable local Review World and `review_world_id`.
7. Re-snapshot before positive reuse/current rendering; mutations return `STALE` rather than rewriting history.

## 13. Error handling and fail-closed law

Authority construction rejects malformed or ambiguous inputs rather than coercing them.

Examples:

- invalid/non-full Git object IDs in fields requiring exact Git identity;
- duplicate set members after normalization;
- path traversal or non-normalized repository paths;
- missing tree identity;
- ambiguous merge-result identity;
- mutable RAB aliases;
- malformed full SHA-256 authority IDs;
- self-inconsistent manifest IDs;
- unknown schema generation;
- unknown review/scope kind;
- unauthorized whole-RAB combination.

Errors are structured and stable enough for hostile tests to assert the violated invariant. They are not converted to PASS, compatible defaults, or best-effort authority.

## 14. Hostile proof matrix

The SAE-10 proof suite must mechanically include the frozen roadmap attacks and additional boundary falsifiers.

Required attacks:

1. **Same head / different base** — same repository and head commit with another base produces a different diff/world identity and cannot reuse verdict authority.
2. **Wrong merge tree** — a merge-readiness verdict bound to tree A is rejected for synthetic merge tree B.
3. **Local mutation after snapshot** — changing selected tracked or included-untracked content makes currentness `STALE` while preserving the historical world record.
4. **Scope downgrade** — changed-files or selected-path scope cannot satisfy a repository-wide world.
5. **Unauthorized RAB combination** — individually recognized component generations assembled into an unlisted `rab_id` are rejected.
6. **Candidate self-activation** — candidate-modified proposed RAB/policy files cannot change the verifier-trusted active RAB for that review.

Additional required controls:

7. exact identical GitHub facts reproduce the same `review_world_id`;
8. patch-format/render differences do not change `diff_id` when Git base/head/tree/scope identity is unchanged;
9. repository substitution fails even with identical SHA spellings;
10. truncated authority IDs are rejected;
11. unknown RAB component generation does not resolve via `latest`;
12. local untracked-policy change changes snapshot/world identity;
13. unresolved material submodule/LFS/generated state prevents exact positive world construction;
14. stale RAB authorization returns stale/unauthorized currentness without rewriting the historical Review World;
15. malformed canonical objects cannot round-trip into a different accepted authority object.

## 15. Integration boundary

SAE-10 generation 1 should introduce the contracts and their adapters first. It should not immediately rewrite every Sergeant verdict path.

Initial integration is limited to:

- reusable construction/verification APIs;
- deterministic tests and vectors;
- a candidate SAE-10 authority manifest documenting the exact implementation generation;
- optional shadow reporting proving that existing PR/local review inputs can be represented as Review Worlds without changing current verdict semantics.

Normal Sergeant PASS/NEEDS WORK behavior remains unchanged until later integration nodes explicitly grant and wire stronger authority.

## 16. Rejected alternatives

### 16.1 Extend `PullRequestDiff` into the authority object

Rejected because it mixes network transport and incomplete patch rendering with constitutional identity. It also cannot represent local snapshots or whole-RAB authorization cleanly.

### 16.2 Hash GitHub patch text as the diff identity

Rejected because patch text can be omitted/truncated for binary/large changes and rendering is not the underlying Git transition.

### 16.3 Build a generic qualification/attestation envelope now

Rejected because that belongs to SAE-30 and would collapse the roadmap's separation between Review World/RAB identity and Qualification Authority.

### 16.4 Authorize RABs component-by-component

Rejected explicitly by the founding architecture: individually authorized components do not imply an authorized combination.

## 17. Planned implementation decomposition

Implementation should be delivered in small independently testable slices:

- Slice A: canonical encoding, full authority digest validation and immutable scope model.
- Slice B: RAB manifest + whole-RAB authorization verifier.
- Slice C: GitHub Review World model and deterministic diff identity.
- Slice D: merge-result binding.
- Slice E: local snapshot model and mutation detection.
- Slice F: currentness/invalidation engine.
- Slice G: hostile proof fixtures covering the full roadmap matrix.
- Slice H: shadow integration adapters proving reuse of existing GitHub/local review substrate without changing normal verdict authority.
- Slice I: SAE-10 candidate authority document/manifest and exact-head proof closeout.

Each slice must be test-first and frozen before the next slice depends on it.

## 18. Acceptance criteria

SAE-10 implementation is acceptable only when all of the following are true:

- exact GitHub repository/base/head/tree/diff/scope identity is mechanically bound;
- merge-result identity is mandatory for merge-readiness claims;
- local snapshots bind explicit HEAD/index/worktree/untracked policy and fail closed on unresolved material state;
- all authority IDs are full SHA-256 values;
- a RAB is immutable and content-addressed;
- exact whole-RAB authorization is mandatory;
- candidate content cannot self-activate authority;
- currentness is derived separately from immutable historical truth;
- every frozen hostile attack is mechanically proven;
- existing GitHub fetch, battle-review sandboxing and standalone mission boundaries are reused rather than replaced;
- no SAE-20/SAE-30 qualification authority is fabricated;
- no current Sergeant verdict meaning changes in SAE-10 construction;
- PR #167 remains fenced and untouched;
- the exact candidate generation passes the normal Sergeant proof suite and clean-clone proof boundary before lifecycle advancement.

## 19. Frozen design decisions

This design intentionally leaves no implementation-semantic TODOs:

- authority encoding is canonical JSON + full SHA-256;
- GitHub diff identity is rooted in repository/base/head/tree/scope transition, not patch text;
- merge-result identity is a distinct optional field required by merge-readiness mode;
- local snapshots use explicit content manifests and explicit untracked policy;
- unresolved material submodule/LFS/generated state fails closed;
- RAB manifests contain fixed named slots with explicit inactive state for not-yet-created roadmap authorities;
- RAB authorization is exact whole-manifest authorization from verifier-trusted state outside candidate control;
- pre-SAE-30 lifecycle bootstrap is bounded to PROVEN SAE-00 roadmap authority plus the frozen Owner/Root constitutional TCB;
- currentness never rewrites historical Review World truth;
- initial integration is shadow/contract-first and does not alter normal verdict authority.
