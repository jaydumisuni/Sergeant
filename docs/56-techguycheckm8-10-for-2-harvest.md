# TechGuyCheckm8 10-for-2 Harvest

Date: 2026-07-27

## Scope

The first cross-repository Sergeant harvest inspected ten consecutive merged TechGuyCheckm8 pull requests: #9 through #18. The pass selected two provenance-complete, repaired, transferable defect lineages. It did not treat feature additions, green workflows, formatting, or unresolved review findings as learned knowledge.

## Selected candidate 1 — checkout credential boundary

- source: `jaydumisuni/TechGuyCheckm8` PR #18
- defective ref: `3b9b5d2469fed602cd6b5c728109cf193b9ccba1`
- fixing ref: `40291a738e866e53b7d1cdcd0cf31f6e860357f5`
- scored path: `.github/workflows/reviewed-apple-tools-build.yml`
- defect: checkout credentials remained persisted while freshly cloned third-party build tooling executed in the same job
- verified repair: `persist-credentials: false` is present at the fixing ref and the exact-head Reviewed Apple Tools Build passed
- state: `candidate_ready`, collected only

Transfer target: CI jobs that execute third-party build or generation steps must remove repository credentials from the worktree before those steps run.

## Selected candidate 2 — checksum path namespace

- source: `jaydumisuni/TechGuyCheckm8` PR #18
- defective ref: `3b9b5d2469fed602cd6b5c728109cf193b9ccba1`
- fixing ref: `40291a738e866e53b7d1cdcd0cf31f6e860357f5`
- scored paths: `tools/apple-build/make_receipt.py`, `.github/workflows/reviewed-apple-tools-build.yml`
- defect: the receipt emitted bare basenames while verification ran from the output root against binaries stored under `bin/`
- verified repair: the fixing ref emits `bin/gaster` and `bin/irecovery` relative paths into `SHA256SUMS`, and the exact-head workflow passed
- state: `candidate_ready`, collected only

Transfer target: integrity-manifest producers and downstream verifiers must share the same path namespace and runtime working-directory model.

## Retained but not admitted

The pass also found unresolved signals in PRs #10, #11, #15 and #17 involving substring-based protocol error detection, candidate-ambiguity masking, a Unix-only serial builder call, and missing Gaster-proof session binding. They are not candidate-ready because a verified fixing state was not established. PRs #9, #12, #13, #14 and #16 supplied no qualifying resolved review lineage in this pass.

## Authority

These two records are inputs to the governed queue only. Blind review, fixing-truth reveal, Teacher/Prosecutor/Defender challenge, executable negative controls, unrelated transfer, hidden holdout and owner-controlled promotion remain required. Automatic promotion and automatic merge remain forbidden.
