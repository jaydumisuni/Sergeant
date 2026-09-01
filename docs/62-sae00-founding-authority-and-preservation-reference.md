# SAE-00 — Founding Authority and Preservation Reference

Date: 2026-09-02

Status: **SAE-00 CANDIDATE, REVIEWED, PROOF ATTACHED** — isolated Assurance Evolution construction authority only. No normal Sergeant verdict authority transfers.

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

Binds to `docs/59-sergeant-assurance-evolution-roadmap.md` (roadmap v1.1) plus its own freeze proof, `docs/60-sergeant-assurance-evolution-freeze-record.md`, `docs/61-sergeant-assurance-evolution-freeze-manifest.json`, and `tests/test_assurance_evolution_roadmap_freeze.py`. All four are already merged and hash-bound in `docs/63`.

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

Binds to `docs/05-security-model.md` (the trust-zone specification: collector/analyzer/reasoner/poster separation, token model, sandbox model, verdict triggers including "Detected secret → block"), operationalized in code by `main_review/officer_council.py`'s `security`/`security_taint` → `Medic` capability mapping, and proved executable by `tests/test_live_pr_ingestion_and_secret_detection.py::test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test`.

Run fresh during this construction session:

```
python -m pytest -q tests/test_live_pr_ingestion_and_secret_detection.py::test_secret_detection_catches_planted_fake_secret_without_literal_secret_in_test
1 passed
```

### 3.7 Existing learning state

Binds to `PICKUP.md`'s "Current learning state" section, hash-bound in `docs/63`. The specific accepted-lesson record paths it names were verified to actually exist:

- `.github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json` — exists, `status: "accepted"`.
- `.github/self-learning/lessons/lumi-token-origin-20260723.json` — exists (the Lumi credential destination/origin lesson PICKUP.md describes as integrated before PR #159).

Both are hash-bound in `docs/63`. The full `lessons/` directory contains exactly six accepted-lesson files (`cpl-adjudication-noise-20260724.json`, `lumi-token-origin-20260723.json`, `preserve-before-delete-20260724.json`, `product-identity-runtime-consistency-20260727.json`, `review-evidence-integrity-20260724.json`, `tgcheckm8-checksum-path-namespace-20260723.json`).

### 3.8 Existing Cpl/officer hierarchy

Binds to `docs/44-deterministic-permanent-officer-formation.md` (the ten-permanent-officer formation and command path) and `docs/34-cpl-officer-amplification.md` (the Cpl support-mapping layer). Confirmed as genuinely implemented, not only documented, in `main_review/officer_council.py`:

- `OFFICER_ORDER = ("Quartermaster", "Scout", "Engineer", "Medic", "Mechanic", "Analyst", "Challenger", "Archivist", "Judge", "Hermes")` — an exact, order-preserved match to `docs/44`'s ten-officer table.
- `OFFICER_BY_CAPABILITY` maps specialist domains (e.g. `"security": "Medic"`, `"security_taint": "Medic"`) exactly as `docs/34`'s support-mapping table describes.
- `run_officer_council(...)` and `_officer_reports(...)` are live functions that build one report per permanent officer per review, not label wrappers around precomputed output.

All three files are hash-bound in `docs/63`.

### 3.9 Existing proof behavior

Binds to `main_review/verdict.py` (`review_repository`, the deterministic verdict engine) and `main_review/final_proof.py` (`run_final_proof`, the combined review-PASS + verification-verified gate — the same gate CI's `clean-clone-proof` job exercises via `main-review final-proof --pretty`).

Run fresh, directly, during this construction session:

```python
from main_review.final_proof import run_final_proof
result = run_final_proof(".")
# result["passed"]  -> True
# result["blockers"] -> []
# result["review_verdict"]["verdict"] -> "PASS"
```

Both files are hash-bound in `docs/63`.

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

## 6. Authority produced

This node produces exactly the three authority artifacts `docs/59` section 7 specifies, recorded as constants in `docs/63`:

- `SERGEANT_PRESERVATION_REFERENCE`
- `FOUNDING_ARCHITECTURE_AUTHORITY`
- `ROADMAP_EXECUTION_AUTHORITY`

## 7. Authority gain and boundary

Per `docs/59` section 7: **authority gain is isolated Assurance Evolution construction only; no normal verdict authority.** Current canonical Sergeant (`main_review/verdict.py`, `main_review/final_proof.py`) remains the active, final, normal engineering-review authority. Nothing in this document, `docs/63`, or `tests/test_sae00_founding_authority_reference.py` changes `PASS`/`NEEDS WORK`/`BLOCK` behavior, the Cpl/officer/Judge hierarchy, model-free defaults, or any existing verdict path. This node unblocks `SAE-10`, `SAE-20`, `SPIKE-ID`, `SPIKE-EXT`, and `SPIKE-SEM` (the only roadmap nodes whose sole proof dependency is `SAE-00`) and, transitively, every other node in the 28-node DAG. It does not itself implement any Assurance Evolution mechanism (no ACR, no Rust kernel, no qualification registry) — SAE-00 is recovery/binding/proof only.

## 8. Recovery statement for a future zero-context agent

A future zero-context agent has correctly recovered SAE-00 when it can state: current live `main` is `9976e43f0d4d318ee4ffd2c4389bd87f520a7757` at binding time (and may be newer now — re-recover before relying on it); PR #167 was open/draft/unmerged at the same head recorded at roadmap freeze and remains untouched by this node; the ten required bindings above each point to a real, checkable file or executable mechanism, not an assertion; no rejected lesson was revived; 1024 of 1025 tests passed with the one failure fully explained as a local Windows CRLF checkout artifact confirmed not to reflect real content divergence; and this node grants isolated Assurance Evolution construction authority only, never normal Sergeant verdict authority.
