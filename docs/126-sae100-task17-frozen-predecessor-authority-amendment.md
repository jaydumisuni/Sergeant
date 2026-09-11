# SAE-100 Task 17 Frozen-Predecessor Authority Amendment Proposal

This record does not amend Task 17 merely by existing. It is an authority proposal that requires explicit approval and guarded merge before any downstream construction may consume it.

## Bound source authority

- Canonical source main: `4655d18e979e62baf31f301df295e11483d19c00`.
- Canonical roadmap blob: `b78b960430182216dfce4ce5a6e2c671f2f9e393`.
- Task 17 currently requires narrow in-place modification of `main_review/officer_council.py`, `main_review/judge_assurance_adapter.py`, and `main_review/final_proof.py`. Those three files are already frozen predecessor authority blobs and cannot be changed without violating predecessor preservation.

## Proposed replacement rule

If this exact proposal is explicitly approved and guarded-merged, only the impossible in-place edits are superseded. `main_review/cpl_campaign.py` remains a required narrow in-place integration edit. The three frozen predecessor files remain byte-for-byte unchanged and their existing public outputs are consumed through successor/non-mutating integration seams implemented in `main_review/assurance_integration.py`.

The original Task 17 interfaces, hostile tests, candidate/guarded-merge/separate-closeout lifecycle, `SHADOW_OR_QUALIFICATION_ONLY` pre-Genesis mode, Judge evidence-admission ownership, officer specialist ownership, Rust constitutional-admissibility-only role, and Sergeant final engineering-verdict ownership remain unchanged. No Genesis activation or normal-verdict authority gain is created.

## Frozen predecessor bindings

- `main_review/officer_council.py` -> `0089e55db3493501e85fba30f502b36f59fc5433`
- `main_review/judge_assurance_adapter.py` -> `522b01881894e2acf5898a32964c04303b585307`
- `main_review/final_proof.py` -> `8ee97495afabd7828a5fc8c37b44e5b802cbeded`

## Consumption boundary

PR #221 must not be merged under the current contradictory Task 17 authority. After explicit approval and guarded merge of this exact amendment generation, SAE-100 construction must be reconciled onto the new canonical main on a new branch/PR if ancestry requires it; old histories remain preserved and no force-push is permitted.
