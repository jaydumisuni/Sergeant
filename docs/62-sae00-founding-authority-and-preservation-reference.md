# SAE-00 — Founding Authority and Preservation Reference

Date: 2026-09-02

Status: **SAE-00 CANDIDATE, PROOF ATTACHED, AWAITING OWNER/HUMAN REVIEW** — isolated Assurance Evolution construction authority only. No normal Sergeant verdict authority transfers. Per `docs/59` section 3's universal lifecycle (`AUTHORIZED → CANDIDATE → REVIEWED → QUALIFIED → PROVEN`), this node has not yet advanced past `CANDIDATE`: it is self-reviewed and CI-green, but not yet Owner-reviewed or merged.

This record is the founding node of the Sergeant Assurance Evolution roadmap (`docs/59-sergeant-assurance-evolution-roadmap.md`, section 7, `SAE-00 — Founding authority and preservation reference`). Its proof requirement is `none`; it is the DAG root every other programme (`SAE-10` through `SAE-180`, and the three feasibility spikes) depends on directly or transitively.

## 1. What SAE-00 requires

Quoted from `docs/59` section 7:

> Must bind: approved founding architecture; approved roadmap generation; freshly recovered live Sergeant main; preservation constitution; current model-free benchmark; current security boundary; existing learning state; existing Cpl/officer hierarchy; existing proof behavior; PR #167 non-retrofit fence or its terminal original-authority disposition.
>
> Must prove current canonical state was recovered without chat authority, no existing mechanism was misclassified as missing, no rejected lesson was revived, normal Sergeant baseline is reproducible and security baseline is reproducible.

This document, `docs/63-sae00-founding-authority-reference-manifest.json`, and `tests/test_sae00_founding_authority_reference.py` together satisfy that requirement. The manifest is the machine-checkable binding; this document explains what each binding concretely points to and why; the test mechanically verifies the manifest against live repository content (git blob SHAs, executed proof re-runs, and structural assertions), not asserted prose.

## 2. Recovery method

Recovery followed `AI_START_HERE.md`'s required order: `README.md` → `AGENTS.md` → `PICKUP.md` → `ASSURANCE_EVOLUTION_START_HERE.md` → `docs/58` → `docs/59` → `docs/60`/`docs/61` → live GitHub state via `gh pr view 167` and `git rev-parse origin/main` after a fresh `git fetch origin`. No prior chat transcript, cached belief, or copied evidence was treated as authority; every claim below was independently re-derived from the current working tree and live GitHub API responses captured during this construction session.

## 3. The ten bindings

### 3.1 Approved founding architecture

Binds to `docs/58-sergeant-assurance-evolution-founding-architecture.md`, already merged to `main` via PR #168 (merge commit `9976e43f0d4d318ee4ffd2c4389bd87f520a7757`). Hash-bound in `docs/63` by git blob SHA.

### 3.2 Approved roadmap generation

Binds to `docs/59-sergeant-assurance-evolution-roadmap.md` (roadmap v1.1) plus its own freeze proof, `docs/60-sergeant-assurance-evolution-freeze-record.md`, `docs/61-sergeant-assurance-evolution-freeze-manifest.json`, and `tests/test_assurance_evolution_roadmap_freeze.py`. All four are already merged and hash-bound in `docs/63`, and `tests/test_sae00_founding_authority_reference.py::test_sae00_roadmap_freeze_fixture_hash_matches_docs61` independently cross-checks the freeze-proof fixture's recorded hash against the value `docs/61` itself records for the same path, closing a gap an earlier review round correctly identified: `docs/61` names a `blob_sha` for its own proof fixture, but `docs/61`'s own test never verifies it — this reference now does, from outside that frozen generation, without editing it.

### 3.3 Freshly recovered live Sergeant main

Recovered fresh via `git fetch origin` then `git rev-parse origin/main` during this construction session:

`9976e43f0d4d318ee4ffd2c4389bd87f520a7757`

This is the merge commit of PR #168 (the roadmap freeze itself), independently re-derived rather than copied from `docs/59`'s planning-base SHA (`4a277cc5950aa08a98157b950c96fb88f2178c79`, which is now two commits behind current `main`: `4a277cc` → `171a0bd` (PR #169, a regex-to-structural-check fix) → `9976e43` (PR #168 merge)). SAE-00 binds to the *current* head, not the stale planning reference, exactly as `docs/59` section 1 requires ("This SHA is a planning reference, not a future construction-base assumption").

### 3.4 Preservation constitution

**Judgment call, stated explicitly:** no single file in this repository is literally named "constitution." The closest and most defensible binding is `docs/58` section 1 ("Product identity and preservation"), which is the frozen, itemized list of preservation requirements that the Assurance Evolution architecture itself commits never to violate (model-free normal review, `PASS`/`NEEDS WORK`/`BLOCK` law, Sergeant/Cpl/officer/Judge hierarchy, no automatic merge/promotion, read-only/default-deny GitHub boundary, etc.). This is bound jointly with the two pre-existing operating-authority documents that `docs/58` section 1 preserves and that predate Assurance Evolution entirely: `README.md` ("Core principles", "Safety boundary") and `AGENTS.md` (command chain, model-free/optional-model boundary, tenfold doctrine, completion standard). All three are hash-bound in `docs/63`. Treat this triple binding, not a single named file, as the preservation constitution for SAE-00 purposes.

### 3.5 Current model-free benchmark

Binds to `tests/test_model_free_product_contract.py`, the executable benchmark that mechanically proves the product's default state is model-free with models strictly opt-in — across `README.md`, `AGENTS.md`, `docs/22-semantic-open-model-review.md`, `docs/54-model-free-core-and-optional-reasoning.md`, the CLI provider (`main_review/llm_provider.py`), the VS Code extension, the JetBrains adapter, the Command Center UI, `pyproject.toml`, `CLAUDE.md`, and `.github/copilot-instructions.md`.

Run fresh during this construction session:

```
python -m pytest -q tests/test_model_free_product_contract.py
6 passed
```

### 3.6 Current security boundary

Binds to `docs/05-security-model.md` (the trust-zone specification: collector/analyzer/reasoner/poster separation, token model, sandbox model, verdict triggers including "Detected secret → block"). The actual detection mechanism is `main_review/evidence.py`'s `SECRET_PATTERNS` tuple and `SecretEvidenceProvider` class — not `main_review/officer_council.py`, which only routes an already-produced `security`/`security_taint` finding to the `Medic` officer label and performs no detection itself. Both are hash-bound in `docs/63`, and proved executable by `tests/test_live_pr_ingestion_and_secret_detection.py::test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test`.

**Explicitly `PARTIAL`, not `EXACT`, closure (`docs/58` §8 vocabulary):** `docs/05` specifies more than secret detection — read-only token enforcement, sandbox isolation, stage separation, trusted-policy provenance. The live controls for the token/permission portion (`assess_token_scopes`, `enforce_mission_permissions`) are in `main_review/production_hardening.py`, which is **not** hash-bound by this binding. This binding is `EXACT` for the secret-detection sub-mechanism specifically — specification, real implementation, and a passing executable proof are all bound and re-run — and openly `PARTIAL` for `docs/05`'s full architecture. Chasing complete behavioral closure over the entire security boundary is out of scope for a recovery/binding node; a later SAE node (`SAE-20`'s ACR, or `SAE-80`'s Evidence/Proof World) is the appropriate place to qualify the full boundary if the roadmap requires it. Recorded explicitly in `docs/63`'s `residual_gaps`, not silently omitted.

Run fresh during this construction session:

```
python -m pytest -q tests/test_live_pr_ingestion_and_secret_detection.py::test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test
1 passed
```

### 3.7 Existing learning state

Binds to `PICKUP.md`'s "Current learning state" section, hash-bound in `docs/63`. The two accepted-lesson record paths it names by name were verified to actually exist:

- `.github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json` — exists, `status: "accepted"`.
- `.github/self-learning/lessons/lumi-token-origin-20260723.json` — exists (the Lumi credential destination/origin lesson PICKUP.md describes as integrated before PR #159).

The full `lessons/` directory contains exactly six accepted-lesson files. All six — not only the two PICKUP.md names explicitly — are individually git-blob-SHA-hash-bound in `docs/63`, each verified `status: "accepted"`: `cpl-adjudication-noise-20260724.json`, `lumi-token-origin-20260723.json`, `preserve-before-delete-20260724.json`, `product-identity-runtime-consistency-20260727.json`, `review-evidence-integrity-20260724.json`, `tgcheckm8-checksum-path-namespace-20260723.json`. This closes the full accepted-learning-state collection, not only the two records PICKUP.md happens to name in prose — modifying or replacing any of the other four would now change a recorded hash and fail `tests/test_sae00_founding_authority_reference.py`.

### 3.8 Existing Cpl/officer hierarchy

Binds to `docs/44-deterministic-permanent-officer-formation.md` (the ten-permanent-officer formation and command path) and `docs/34-cpl-officer-amplification.md` (the Cpl support-mapping layer). Confirmed as genuinely implemented, not only documented, in `main_review/officer_council.py`:

- `OFFICER_ORDER = ("Quartermaster", "Scout", "Engineer", "Medic", "Mechanic", "Analyst", "Challenger", "Archivist", "Judge", "Hermes")` — an exact, order-preserved match to `docs/44`'s ten-officer table.
- `OFFICER_BY_CAPABILITY` maps specialist domains (e.g. `"security": "Medic"`, `"security_taint": "Medic"`) exactly as `docs/34`'s support-mapping table describes.
- `run_officer_council(...)` and `_officer_reports(...)` are live functions that build one report per permanent officer per review, not label wrappers around precomputed output.

All three files are hash-bound in `docs/63`.

**Explicitly `PARTIAL`, not `EXACT`, closure:** the constants and entry-point function above are genuinely implemented, not misclassified as missing — that is what this binding is `EXACT` about. But `run_officer_council` directly executes `run_offline_investigations` (`main_review/offline_investigation.py`) and `build_cpl_campaign` (`main_review/cpl_campaign.py`), and neither is hash-bound here, so their behavior — the actual investigation runtime — is not frozen by this reference. Full behavioral closure over the entire officer-investigation pipeline is, like the security boundary above, out of scope for a recovery/binding node and is recorded as such in `docs/63`'s `residual_gaps`.

### 3.9 Existing proof behavior

Binds to `main_review/verdict.py` (`review_repository`, the deterministic verdict engine) and `main_review/final_proof.py` (`run_final_proof`, the combined review-PASS + verification-verified gate — the same gate CI's `clean-clone-proof` job exercises via `main-review final-proof --pretty`).

The binding traces `run_final_proof`'s complete transitive local-import closure rather than stopping one hop from the entry point, because two review rounds correctly showed that a shallower binding left load-bearing behavior unfrozen: `final_proof.py` → `verdict.py` (which itself imports `evidence.collect_evidence`, already separately hash-bound under the security-boundary binding) and `verification.py`; both `verification.py` and `evidence.py` import `scanner.scan_repository`; `scanner.py` imports `classify_role`/`detect_language`/`is_high_risk_path` from `languages.py` and `FileInsight`/`RepositoryInsight` from `models.py`. `languages.py` and `models.py` have zero further local `main_review.*` imports, so the closure terminates there. All seven reachable modules — `final_proof.py`, `verdict.py`, `verification.py`, `scanner.py`, `evidence.py`, `languages.py`, `models.py` — are hash-bound in `docs/63`, and `tests/test_sae00_founding_authority_reference.py::test_sae00_final_proof_dependency_closure_is_exhaustive` mechanically parses every bound file's own `from .X import ...` lines and asserts each resolves to another module already in the bound set — so a future import edge this binding missed would fail that test immediately, rather than requiring another review round to discover. This is an **exact closure of the local-module import graph specifically**, not a claim of exhaustive whole-program closure over every stdlib/third-party dependency reachable from these seven files — that broader claim is out of scope for a binding/recovery node.

Run fresh, directly, during this construction session:

```python
from main_review.final_proof import run_final_proof
result = run_final_proof(".")
# result["passed"]  -> True
# result["blockers"] -> []
# result["review_verdict"]["verdict"] -> "PASS"
```

All seven files are hash-bound in `docs/63`.

### 3.10 PR #167 non-retrofit fence

Live-recovered during this construction session via `gh pr view 167 --json state,headRefOid,isDraft,baseRefName,baseRefOid,headRefName`:

```json
{
  "state": "OPEN",
  "isDraft": true,
  "baseRefName": "main",
  "baseRefOid": "4a277cc5950aa08a98157b950c96fb88f2178c79",
  "headRefName": "learning/oracle-browser-repairs-round-2",
  "headRefOid": "536dd6dcf99c4763a4b1ec9c86bcde7e03d5b13c"
}
```

Identical to the state recorded at roadmap freeze in `docs/60` section 6 and `docs/61`'s `live_fence_at_freeze`. PR #167 has not advanced, closed, or merged since the freeze. **This SAE-00 binding does not retrofit or alter PR #167's authority or lifecycle in any way.** PR #167 remains a pre-Assurance-Evolution governed-learning campaign that must finish or be terminally dispositioned under the authority under which it began. This construction session did not touch PR #167, its branch, or any file exclusive to it.

## 4. Proof of the five required assurances

### 4.1 Current canonical state recovered without chat authority

Every fact bound above was independently re-derived this session from the live working tree and live GitHub API responses (`git fetch`, `git rev-parse`, `gh pr view`, `git hash-object`, direct test execution) rather than copied from a prior conversation or cached belief.

### 4.2 No existing mechanism was misclassified as missing

Before writing this record, the Cpl/officer hierarchy, the proof engine, the model-free benchmark, and the security-boundary detector were each confirmed present and executable in code (section 3.5, 3.6, 3.8, 3.9 above) rather than assumed absent or reinvented.

### 4.3 No rejected lesson was revived

The two candidates PICKUP.md records as terminally rejected — `learn-tgcheckm8-checkout-credential-boundary-20260723` (PR #159) and `learn-oracle-oidc-workflow-identity-20260817` (PR #165, called out via its authoritative disposition record `.github/self-learning/results/project-oracle-oidc-workflow-20260818.json`) — were checked against the accepted-lesson directory:

```
grep -ril "checkout-credential-boundary" .github/self-learning/lessons/   -> no match
grep -ril "oracle-oidc-workflow-identity" .github/self-learning/lessons/  -> no match
```

Both rejected candidates exist only as retained evidence in `.github/self-learning/signals/` and (for the Oracle case) `.github/self-learning/results/`, each with an explicit rejected disposition (`.github/self-learning/results/project-oracle-oidc-workflow-20260818.json`: `"state": "rejected"`, `"accepted_lesson": false`, `"sergeant_verdict": "reject"`). Neither appears in `.github/self-learning/lessons/`, which contains exactly six files, none of which are either rejected candidate. No lesson was revived.

### 4.4 Normal Sergeant baseline is reproducible

The full test suite was run fresh from the current branch (`main` at construction time) using the exact invocation the repository's continuous-integration `test` job uses (`pytest -q -ra`):

```
python -m pytest -q -ra
1024 passed, 1 failed in 63.04s
```

The one failure, `tests/test_assurance_evolution_roadmap_freeze.py::test_assurance_evolution_freeze_manifest_binds_authority_documents`, is a **pre-existing, environment-only artifact unrelated to this construction session**, root-caused as follows: that test computes a document's git blob SHA by reading raw bytes off the working-tree copy (`path.read_bytes()`), rather than through git's own blob machinery. On this Windows development machine, `git config core.autocrlf` is `true`, which had converted `ASSURANCE_EVOLUTION_START_HERE.md`'s line endings from LF to CRLF in the working-tree checkout, changing the raw bytes the test hashes while leaving the actual git-tracked content unchanged. This was confirmed directly:

```
git hash-object ASSURANCE_EVOLUTION_START_HERE.md        -> 75d462b5989c4bbfacae4e991a61a24ae6e7fb8d
git show HEAD:ASSURANCE_EVOLUTION_START_HERE.md | sha1    -> 75d462b5989c4bbfacae4e991a61a24ae6e7fb8d
docs/61 manifest recorded blob_sha for that path          -> 75d462b5989c4bbfacae4e991a61a24ae6e7fb8d
```

All three agree. The canonical git-tracked content exactly matches the frozen manifest; there is no real content divergence. `.gitattributes` does not exist in this repository, so nothing repo-tracked forces this behavior — it is solely a local Windows `core.autocrlf` checkout effect. CI's Linux runners (`ubuntu-latest`) do not perform this conversion by default, so this failure is not expected to reproduce there, and it predates this SAE-00 branch (it reproduces identically on unmodified `main`). This is recorded as a genuine residual gap in `docs/63` rather than papered over — see section 5 below. It does not affect any binding this document makes, and it was not fixed here because touching `tests/test_assurance_evolution_roadmap_freeze.py` or `docs/61` is out of SAE-00's scope (both belong to the already-frozen roadmap generation, and SAE-00 must not retrofit prior frozen authority).

Excluding that one pre-existing, explained, environment-only failure, all 1024 other tests — spanning the CLI, the verdict/proof engine, the officer council, the learning loop, the multi-platform adapters, and every other existing capability — passed.

That `1024 passed, 1 failed` count was captured once, deliberately, immediately after branching off `main` and **before** adding any SAE-00 file — it isolates whether the pre-existing Sergeant suite reproduces, independent of this construction's own new tests. It was not re-run after every subsequent edit round, so a static reading of it against the *final* candidate tree (which now includes SAE-00's own 13+ tests) would be stale — a review round correctly flagged this. `docs/63` now records it explicitly as `pre_construction_baseline`, separate from a new `exact_candidate_tree_full_suite` field capturing the final tree's actual numbers at the commit this PR lands on. The `total_collected` figure in `exact_candidate_tree_full_suite` specifically is not just a recorded number to trust: `tests/test_sae00_founding_authority_reference.py::test_sae00_exact_candidate_tree_collection_count_is_current` re-runs `pytest --collect-only -q` live, every time the suite runs, and asserts the manifest's recorded count still matches current reality.

### 4.5 Security baseline is reproducible

Run fresh, standalone, during this construction session:

```
python -m pytest -q tests/test_live_pr_ingestion_and_secret_detection.py::test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test
1 passed
```

This test is also included in, and passed as part of, the full 1024-passing run in section 4.4.

## 5. Residual gaps and judgment calls (stated explicitly, not hidden)

1. **"Preservation constitution" naming.** No file is literally named "constitution." SAE-00 binds this requirement to `docs/58` section 1 plus `README.md` plus `AGENTS.md` jointly (section 3.4). A future SAE node may choose to consolidate these into one explicitly named preservation-constitution document; SAE-00 does not do that here because doing so would be new authority-document creation, not recovery/binding.
2. **Pre-existing CRLF-sensitive blob-hash test fragility.** `tests/test_assurance_evolution_roadmap_freeze.py`'s `_git_blob_sha` helper hashes raw working-tree bytes rather than git's canonical blob content, which is fragile on any Windows checkout with `core.autocrlf=true`. This is a genuine, currently-reproducing gap in the already-frozen roadmap generation's own proof fixture (see section 4.4). SAE-00 documents it honestly but does not modify that file, since it belongs to prior frozen authority (`docs/59`/`docs/60`/`docs/61`) and altering it is outside SAE-00's binding/recovery mandate. `tests/test_sae00_founding_authority_reference.py`, written fresh for this node, deliberately computes blob SHAs via `git hash-object` (subprocess) rather than raw-byte hashing, specifically to avoid reproducing this class of platform-dependent false failure.
3. **No dedicated "current model-free benchmark" existed as a single named artifact before this recovery; `tests/test_model_free_product_contract.py` is the closest genuine mechanical benchmark** and is bound as such. If a future SAE node wants a benchmark with a more explicit "benchmark" identity/name, that is new work, not something SAE-00 invents.
4. **PR #167's base SHA (`4a277cc5950aa08a98157b950c96fb88f2178c79`) is now behind current `main`.** This is expected and does not require action from SAE-00: PR #167 is fenced from Assurance Evolution requirements entirely, and its own eventual rebase/merge/close is governed by its original pre-existing authority, not this roadmap.
5. **Canonical zero-context entrypoint discoverability.** `ASSURANCE_EVOLUTION_START_HERE.md` is the file a zero-context agent actually reads to recover "Assurance Evolution authority in this order," and today that numbered list still ends at `docs/60`. Ideally it would also point at `docs/62`/`docs/63`. It was deliberately **not edited here**: that file, together with `AI_START_HERE.md`, is one of the five documents `docs/61`'s freeze manifest git-blob-SHA-binds as immutable historical proof of the roadmap freeze event, and `tests/test_assurance_evolution_roadmap_freeze.py` mechanically enforces that binding. Editing its content — even to add a purely navigational pointer — would either break that already-merged, currently-green proof test, or require also rewriting `docs/61`'s recorded hash, which would make a manifest whose entire purpose is proving "what was true at the freeze" instead describe a later state, corrupting its function as an immutable point-in-time proof (the same immutable-Review-World principle `docs/58` section 4 states generally). SAE-00 has no Owner-approved mandate to reopen that freeze generation over a navigation-only concern. Instead, `PICKUP.md` (not frozen, already read earlier in the same zero-context recovery order per `AI_START_HERE.md`) now carries an explicit pointer explaining this exact tension and directing a recovering agent to check `docs/` past `docs/61` for newer SAE binding records. A future roadmap amendment, or `SAE-180`'s own canonical-recovery-update mandate (`docs/59` section 14), is the appropriate place to fold newly landed node pointers back into the frozen entrypoint itself, if the Owner chooses to open a new freeze generation for that purpose.
6. **`current_security_boundary` and `existing_cpl_officer_hierarchy` are explicitly `PARTIAL`, not `EXACT`, closures (`docs/58` §8 vocabulary).** Two review rounds correctly showed each binding covers only a slice of what it names: the security binding covers secret detection specifically, not `docs/05`'s full architecture (`main_review/production_hardening.py`'s token/mission-permission enforcement remains unbound); the officer-hierarchy binding covers the declared formation structure and constants specifically, not the full investigation runtime (`main_review/offline_investigation.py`, `main_review/cpl_campaign.py` remain unbound). Both are now labeled `PARTIAL` in `docs/63` rather than left to read as implicitly complete. SAE-00 draws the line here deliberately: proving one call-graph closed exactly (`existing_proof_behavior`, item 9 below, which does terminate in a small, genuinely closed graph) was a reasonable, bounded fix; fully closing the security boundary's and officer hierarchy's much larger subsystems is disproportionate scope for a recovery/binding node and would not converge to a stopping point in this PR. A later SAE node with the actual qualification/closure machinery (`SAE-20`, `SAE-50`, `SAE-60`) is the right place to complete either closure if the roadmap requires it.

## 6. Authority produced

This node produces exactly the three authority artifacts `docs/59` section 7 specifies, recorded as constants in `docs/63`:

- `SERGEANT_PRESERVATION_REFERENCE`
- `FOUNDING_ARCHITECTURE_AUTHORITY`
- `ROADMAP_EXECUTION_AUTHORITY`

## 7. Authority gain and boundary

Per `docs/59` section 7: **authority gain is isolated Assurance Evolution construction only; no normal verdict authority.** Current canonical Sergeant (`main_review/verdict.py`, `main_review/final_proof.py`) remains the active, final, normal engineering-review authority. Nothing in this document, `docs/63`, or `tests/test_sae00_founding_authority_reference.py` changes `PASS`/`NEEDS WORK`/`BLOCK` behavior, the Cpl/officer/Judge hierarchy, model-free defaults, or any existing verdict path.

`SAE-10`, `SAE-20`, `SPIKE-ID`, `SPIKE-EXT`, and `SPIKE-SEM` are the only roadmap nodes whose entire proof-dependency list is `[SAE-00]` (`docs/59` section 15) — `docs/63` records this as a **structural DAG fact**, not an authority grant. Per `docs/59` section 3's universal lifecycle and forbidden equivalences (`TESTS GREEN != QUALIFIED`, `QUALIFIED != INTEGRATED`), those direct dependents may not freeze, qualify, or prove their own obligations against SAE-00 as unresolved upstream truth while SAE-00 itself remains short of a completion state sufficient to ground that trust — this PR's own manifest records SAE-00 at `lifecycle_state: "CANDIDATE"` (self-reviewed, CI-green, not yet Owner-reviewed or merged), not `QUALIFIED` or `PROVEN`. Safe preparatory work on those five nodes was already permitted independently of SAE-00 under the existing dependency-frontier doctrine (`docs/59` section 2), and remains the only thing this binding enables until SAE-00 itself advances further through the lifecycle. This node does not itself implement any Assurance Evolution mechanism (no ACR, no Rust kernel, no qualification registry) — SAE-00 is recovery/binding/proof only.

## 8. Recovery statement for a future zero-context agent

A future zero-context agent has correctly recovered SAE-00 when it can state: current live `main` is `9976e43f0d4d318ee4ffd2c4389bd87f520a7757` at binding time (and may be newer now — re-recover before relying on it); PR #167 was open/draft/unmerged at the same head recorded at roadmap freeze and remains untouched by this node; the ten required bindings above each point to a real, checkable file or executable mechanism, not an assertion (with two — the security boundary and the officer hierarchy — honestly labeled `PARTIAL` closure rather than overclaimed as `EXACT`); no rejected lesson was revived; the pre-construction baseline (1024 of 1025 tests, captured before SAE-00's own additions) and the exact final-candidate-tree collection count (live-reverified on every run) both reproduce with the same single, fully explained, pre-existing CRLF checkout artifact; and this node grants isolated Assurance Evolution construction authority only, never normal Sergeant verdict authority.
