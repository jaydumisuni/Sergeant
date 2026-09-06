# SAE-40 Judge Assurance Ledger Implementation Plan

## Construction boundary

Base exact canonical `main` at `2a1d16f9772997d993d0f0d41e1c5161f222f136`. Do not edit the existing Judge or verdict path during the SAE-40 candidate.

## Execution

1. Recover SAE-10/SAE-20 PROVEN dependency manifests and current Judge implementation.
2. Freeze hostile tests before production implementation.
3. Implement full-SHA authority records covering every frozen SAE-40 family.
4. Implement canonical persistence and immutable canonical JSON payload snapshots.
5. Implement monotonic ledger creation/merge with occurrence preservation, UNKNOWN conservation, contradiction retention, parent lineage and referential integrity.
6. Implement a separate existing-Judge adapter that consumes, but never replaces, Judge adjudication.
7. Attack duplicate legacy finding IDs, source multiplicity, cross-world/RAB substitution, mutable-generation aliases, forged IDs, non-finite payloads, non-canonical persistence, dangling links and missing/multiple Judge reports.
8. Freeze candidate docs/manifest with no current authority gain.
9. Publish one atomic candidate milestone from exact base.
10. Require exact-head repository CI, clean-clone proof, Main Review and hostile review before candidate merge.
11. After guarded candidate merge, create a separate closeout generation that binds the accepted candidate, actual merge commit and bounded qualification evidence.
12. Only a guarded merge of the exact closeout generation may produce `QUALIFIED_ASSURANCE_LEDGER`.

## Local proof before publication

- hostile focused tests: 26 passed / 0 failed;
- Python compile: PASS;
- no change to `officer_council.py` or verdict implementation;
- repository-wide proof is not claimed until the published exact head runs in the real repository.
