# SAE-40 — Judge Assurance Ledger + Authority-Bearing Identity Candidate

Status: **CANDIDATE ONLY**.

Construction base: `2a1d16f9772997d993d0f0d41e1c5161f222f136`.

## Recovered authority

The frozen roadmap requires SAE-40 to prove only after SAE-10 and SAE-20. Both are already PROVEN on canonical main:

- `docs/81-sae10-proven-lifecycle-closeout-manifest.json` produces `QUALIFIED_REVIEW_WORLD_CONTRACT` and `QUALIFIED_RAB_CONTRACT`.
- `docs/85-sae20-proven-lifecycle-closeout-manifest.json` produces `QUALIFIED_ACR_FOUNDATION` and explicitly marks SAE-40's frozen upstream dependencies available.

The existing Judge remains in `main_review/officer_council.py`. SAE-40 does not replace it or the existing Sergeant verdict path.

## Candidate implementation

`main_review/assurance_ledger.py` adds the lower authority-bearing substrate:

- full cryptographic record IDs bound to Review World, RAB, scope, generation, occurrence, epistemic state, authority/provenance references, related records and canonical payload;
- all fourteen founding record families;
- immutable canonical payload snapshots and strict persisted round-trip validation;
- monotonic ledger merge that conserves UNKNOWN, contradiction, occurrence/multiplicity, scope and parent lineage;
- rejection of cross-world/RAB merge, dangling record links, forged identities, mutable generation aliases, non-finite payloads and non-canonical persistence;
- merged ledgers require an explicit generation distinct from both parent generations.

`main_review/judge_assurance_adapter.py` performs a one-way lift of the existing Judge packet:

- every raw source claim remains a distinct occurrence;
- legacy `finding_id` is required only to recover the existing Judge disposition and remains presentation-only;
- Claim authority excludes `finding_id` and Judge-stage `admission` / `gates_verdict` metadata;
- every canonical raw finding must have exactly one existing Judge disposition and every disposition must resolve to raw evidence;
- admission occurrence identity follows earliest contributing raw occurrence, never lexicographic presentation-alias ordering;
- required-assurance collection and canonical contract fields are mandatory;
- assurance status/gate pairs are exact: satisfied/false, unresolved/true, advisory/false;
- unresolved/advisory obligations remain `UNKNOWN`;
- the already-computed result is recorded only as verdict lineage.

Legacy `finding_id` remains compatible for UI/grouping and persisted presentation integrity but is never positive proof authority.

## Hostile review lineage — RED → GREEN

The originally published candidate was `bee2928bd4537afda4e87e7e2595666839489966`. Green CI was not accepted as qualification. Five distinct RED generations forced successor corrections.

### RED 1 — merge generation and malformed Judge state

Test-only head `e40bec3a92fef65cc84e9e46625fb73b47b125fc` exposed:

1. merged-ledger parent-generation reuse;
2. orphan Judge disposition loss;
3. malformed assurance-state normalization;
4. duplicate/unknown Judge disposition acceptance.

Correction: `2995a51e55afd8cb2af383f972930ec2e1d73180`.

### RED 2 — synthetic Judge authority

Test-only head `7bb7d4bc29a0b693a497b56892acae365bcfc45f` proved that synthetic `untracked` admissions violated the canonical producer contract. Correction `af6341a8c110f1f2f5665949f97e753c0aefde40` requires exact raw-finding ↔ Judge-disposition coverage.

### RED 3 — missing assurance collection

Test-only head `3a572fd9f2b0e8fd05d16410ae525d2cb9473446` proved missing `required_assurances` was being normalized to a proven-empty collection. Correction `9b0cbc6a2236073b34ee34911b63f14227a48e6f` removed default-empty behavior.

### External hostile review — legacy alias authority leak and malformed obligations

The corrected frozen head `ea96a0eb478f0f092edfcee25ea7581b3d4ef2f8` independently earned **1383 passed / 2 historical XFAIL / 0 failed**, exact Main Review APPROVE/PASS and a completed CodeRabbit review. CodeRabbit then produced three valid actionable findings rather than being treated as a ceremonial PASS:

1. the implementation plan still recorded 18 focused tests instead of 24;
2. `finding_id` remained inside the canonical Claim payload and therefore indirectly changed `record_id`, contradicting its presentation-only status;
3. malformed assurance entries could omit `required_assurance` or `gates_verdict` and still become obligations.

The branch was reopened instead of merged.

### RED 4 — presentation-only Claim identity and assurance contract fields

Test-only head `5bae7edf7413b73e4770190ae9f066b98f8793ca` recorded exact RED proof: **1382 passed / 2 historical XFAIL / 3 failed**, where two failures were the new substantive hostile tests and the third was the deliberately stale candidate manifest.

Correction `c8f4620bec9b8e870362994b81a45b9741b1f260` removed `finding_id` from Claim authority and required canonical assurance contract fields. Plan accounting was corrected in the following documentation generation.

### RED 5 — alias-ordered admissions, Judge metadata leakage and status/gate mismatch

A deeper contract audit recovered `docs/44-deterministic-permanent-officer-formation.md` before reasoning: `raw_findings` are pre-Judge claims even though the current producer mutates those objects with Judge-stage `admission` and `gates_verdict` metadata during adjudication.

Test-only head `be0ff9ecac62ff94bb282b93dc2c7e53df521cee` then recorded exact RED proof: **1384 passed / 2 historical XFAIL / 4 failed**. Three failures were new hostile behaviors and the fourth was the deliberately stale manifest:

- admission record identity depended on lexicographic legacy-alias ordering;
- Judge-stage `admission` / `gates_verdict` leaked into raw Claim authority;
- inconsistent assurance status/gate combinations were accepted.

Correction `36058c1fc491adc7a5d83c78b5f869883aac4b48` removes Judge-only fields from Claim authority, derives admission occurrence from raw occurrence, and enforces canonical status/gate pairs. Documentation generation `1971877ade6b95ef4308ccb24013a6e11e60ef73` records the resulting 29-test focused hostile corpus.

## Pre-freeze proof

Exact generation `1971877ade6b95ef4308ccb24013a6e11e60ef73` was executed before manifest rebinding.

Both ordinary repository CI and clean-clone execution independently reached:

- **1387 passed**;
- **2 historical XFAIL**;
- **0 substantive failures**;
- exactly **1 expected failure**, the intentionally stale SAE-40 candidate-manifest blob binding.

This establishes that the implementation and complete hostile corpus are green before the manifest is rebound. It does not itself create qualification authority.

## Frozen hostile corpus

The focused SAE-40 corpus contains **29 hostile tests** across `tests/test_assurance_ledger.py` and `tests/test_judge_assurance_adapter.py`. It attacks, among other boundaries:

- world/RAB/scope/state/occurrence identity substitution;
- duplicate source multiplicity under one legacy presentation ID;
- presentation-alias influence on Claim or admission authority;
- Judge-stage metadata leakage into raw Claim authority;
- UNKNOWN replacement by later TRUE;
- contradiction erasure;
- cross-world and cross-RAB merge;
- non-monotonic parent lineage and parent-generation reuse;
- forged record IDs and mutable authority aliases;
- bool-as-occurrence coercion, malformed refs and non-finite JSON;
- non-canonical persistence and dangling record links;
- missing/multiple Judge reports;
- orphan, duplicate, unknown-bucket, missing or synthetic Judge dispositions;
- missing assurance collection/contract fields, non-canonical state and status/gate mismatch.

The CodeRabbit-originated defects are materially external to the then-green internal hostile corpus because they forced successor generations. They are useful hostile evidence but are **not** relabelled `INDEPENDENT` under future SAE-30/EEPR law. Self-authored hostile review is likewise project-controlled and not an independent Genesis lane.

## Freeze and qualification boundary

The candidate manifest must bind the exact corrected code, design, plan, hostile corpus and this candidate record. Any later content change creates another candidate generation and requires rebinding/re-proof.

This candidate produces **no authority now**. It does not:

- change normal Sergeant verdict authority;
- create a second Judge, Cpl, scheduler or verdict engine;
- create SAE-30 general qualification/provenance authority;
- assert EEPR independence;
- activate Genesis or any partial Assurance Evolution generation;
- auto-qualify SAE-R1, SAE-50 or another dependent node.

Only a later separate SAE-40 lifecycle closeout, after exact frozen-head proof, hostile-review closure and guarded candidate merge, may produce `QUALIFIED_ASSURANCE_LEDGER`.
