# SAE-40 — Judge Assurance Ledger + Authority-Bearing Identity Candidate

Status: **CANDIDATE ONLY**.

Construction base: `2a1d16f9772997d993d0f0d41e1c5161f222f136`.

## Recovered authority

The frozen roadmap requires SAE-40 to prove only after SAE-10 and SAE-20. Both are already PROVEN on canonical main:

- `docs/81-sae10-proven-lifecycle-closeout-manifest.json` produces `QUALIFIED_REVIEW_WORLD_CONTRACT` and `QUALIFIED_RAB_CONTRACT`.
- `docs/85-sae20-proven-lifecycle-closeout-manifest.json` produces `QUALIFIED_ACR_FOUNDATION` and explicitly marks SAE-40's frozen upstream dependencies available.

The existing Judge remains in `main_review/officer_council.py`. Its current `admission_ledger` is presentation-oriented and intentionally collapses source duplicates to one canonical `finding_id` disposition. SAE-40 does not replace it.

## Candidate implementation

`main_review/assurance_ledger.py` adds the lower authority-bearing substrate:

- full cryptographic record IDs bound to Review World, RAB, scope, generation, occurrence, epistemic state, authority/provenance references, related records and canonical payload;
- all fourteen founding record families;
- immutable canonical payload snapshots;
- strict persisted round-trip validation;
- a monotonic Judge ledger that conserves UNKNOWN, contradiction, source occurrence/multiplicity and scope;
- explicit parent-ledger lineage;
- rejection of cross-world/RAB merge and dangling record links;
- merged ledgers require an explicit generation distinct from both parent generations.

`main_review/judge_assurance_adapter.py` lifts the existing Judge packet without re-adjudicating it:

- raw source claims remain distinct occurrences;
- every raw claim must carry its existing canonical `finding_id`;
- every canonical raw finding must have exactly one existing Judge disposition and every Judge disposition must resolve to raw evidence;
- the Judge disposition ledger must contain exactly the canonical `admitted`, `advisory`, and `rejected` buckets with no duplicate finding occurrence across them;
- the required-assurance collection must exist and be an array; missing collection state is rejected rather than converted to proven-empty;
- only canonical assurance states are accepted, with unresolved/advisory obligations conserved as UNKNOWN;
- the already-computed result is recorded only as verdict lineage.

Legacy `finding_id` remains compatible for UI/grouping, but it is never positive proof authority.

## Fresh hostile review and RED → GREEN generations

The originally published candidate was `bee2928bd4537afda4e87e7e2595666839489966`. Fresh hostile review did not treat its green CI as qualification. The review attacked the authority lift and merge semantics directly and produced three bounded RED generations before freeze.

### Hostile generation 1 — merge generation and malformed Judge state

Test-only RED head: `e40bec3a92fef65cc84e9e46625fb73b47b125fc`.

It exposed four fail-open conditions:

1. a merged ledger could reuse a parent generation despite the frozen requirement for a new generation;
2. a Judge disposition could reference no raw claim and be silently dropped;
3. a non-canonical assurance status could be normalized instead of rejected;
4. duplicate Judge dispositions or unknown disposition buckets could be accepted.

The production correction converged at `2995a51e55afd8cb2af383f972930ec2e1d73180`. Exact-head clean-clone proof then reached **1380 passed / 2 xfailed**, with the sole failure being the intentionally stale SAE-40 candidate manifest.

### Hostile generation 2 — synthetic Judge disposition

Test-only RED head: `7bb7d4bc29a0b693a497b56892acae365bcfc45f`.

The canonical producer in `main_review/officer_council.py` was recovered before reasoning: normalized raw findings always receive deterministic `finding_id` values and the existing Judge produces one canonical disposition per canonical finding. Against that evidence, the adapter's synthetic `untracked` admission path was invalid because it invented Judge state instead of lifting existing Judge authority.

Exact-head RED proof reached **1380 passed / 2 xfailed** with exactly the synthetic-disposition hostile test plus the stale manifest failing. The correction at `af6341a8c110f1f2f5665949f97e753c0aefde40` required exact raw-finding ↔ Judge-disposition coverage. Exact-head clean-clone proof then reached **1381 passed / 2 xfailed**, again with only the intentionally stale manifest failing.

### Hostile generation 3 — missing assurance collection

Test-only RED head: `3a572fd9f2b0e8fd05d16410ae525d2cb9473446`.

It proved that a missing `required_assurances` collection was being interpreted as `[]`, which could convert malformed/unknown obligation state into apparent proven-empty state. Exact-head RED proof reached **1381 passed / 2 xfailed** with exactly that hostile test plus the stale manifest failing.

The correction at `9b0cbc6a2236073b34ee34911b63f14227a48e6f` removed the default-empty behavior. Exact-head clean-clone proof reached **1382 passed / 2 xfailed** with the **only** remaining failure being the deliberately stale candidate manifest.

These hostile-review generations are project-controlled review evidence. They are not claimed `INDEPENDENT` under future SAE-30/EEPR provenance law and do not manufacture SAE-30 qualification authority.

## Frozen hostile corpus

The focused SAE-40 corpus now contains **24 hostile tests** across `tests/test_assurance_ledger.py` and `tests/test_judge_assurance_adapter.py`. It attacks:

- world/RAB/scope/state/occurrence identity substitution;
- duplicate legacy `finding_id` source collapse;
- UNKNOWN replacement by later TRUE;
- contradiction erasure;
- cross-world and cross-RAB merge;
- non-monotonic parent lineage;
- parent-generation reuse during merge;
- forged record IDs;
- mutable authority aliases;
- bool-as-occurrence coercion;
- malformed authority refs;
- non-finite JSON;
- non-canonical record/alias ordering;
- dangling related-record links;
- missing or multiple existing Judge authority;
- orphan, duplicate, unknown-bucket, missing, or synthetic Judge dispositions;
- malformed or missing required-assurance state.

The pre-freeze repository proof on `9b0cbc6a2236073b34ee34911b63f14227a48e6f` establishes that every substantive test is green and that the manifest is the only intentionally stale artifact left to rebind. The final frozen candidate must still independently earn exact-head repository CI, clean-clone proof, Main Review and zero unresolved actionable review findings after the manifest is rebound.

## Authority boundary

This candidate produces **no authority now**.

It does not:

- change normal Sergeant verdict authority;
- create a second Judge, Cpl, scheduler or verdict engine;
- create SAE-30 general qualification/provenance authority;
- assert EEPR independence;
- activate Genesis or any partial Assurance Evolution generation;
- auto-qualify SAE-R1, SAE-50 or another dependent node.

Only a later separate SAE-40 lifecycle closeout may produce `QUALIFIED_ASSURANCE_LEDGER` after exact-head review, proof, bounded qualification and guarded merge.
