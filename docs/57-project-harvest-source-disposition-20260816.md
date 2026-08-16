# Project Harvest Source Disposition — 2026-08-16

This record prevents a recovery batch from being mistaken for a set of automatically accepted Sergeant lessons. Every source was checked against current repository truth before deciding whether it should train Sergeant.

## 1. Transfer-set-8 battle snapshot — already integrated

The recovered battle snapshot described an earlier state where transfer set 8 remained `0/3` and three generalized officers had not yet been wired into the canonical review path.

Current Sergeant already contains the corresponding model-free detector families and regressions in `main_review/static_external_integrity_review.py` and its tests:

- untrusted Git/submodule execution requires transport and hook hardening;
- persisted queue read-modify-write requires safe serialization and exhausted deliveries must not disappear;
- webhook failure acknowledgement and payment-credit paths require failure honesty, atomicity and idempotency.

Disposition: **already learned / no duplicate promotion**. The old snapshot is historical evidence only.

## 2. Preserve-before-delete evidence — already accepted

Current `main` already contains `.github/self-learning/lessons/preserve-before-delete-20260724.json`.

Disposition: **already accepted / no duplicate lesson**. Preservation proof remains part of Sergeant's permanent governed knowledge; copying evidence never creates deletion authority.

## 3. Ptah donor pool — outside Sergeant learning truth

The recovered Ptah donor pool is Phase 0A architecture and repository research for Ptah. It explicitly separates confirmed donors from unresolved donors whose canonical repository, licence and implementation still require verification.

Disposition: **not Sergeant training evidence**. Ptah donor research may help Ptah architecture, but it must not become a Sergeant detector or learned rule merely because it appeared in the same recovery batch.

## 4. Hunter Employee OS requirement and UI material — evidence only until lineage exists

The recovered Hunter material establishes an important product-governance boundary: a visible tab, passing build, deployed preview or source marker does not by itself prove an employee-operating-system requirement. Hunter's canonical acceptance checklist was added in `jaydumisuni/hunter` commit `bbc3e57d6d83ed2a39fdf589854ec32d02068d55` and explicitly separates source, runtime, visual, employee-usability and owner-approval gates.

The isolated review deployment evidence around `d0142d2782b930345b68497a14dd2c93531e4682` also remained an owner-review checkpoint rather than production approval. That commit itself adjusts review-gate wording and does not establish a transferable product defect/fix lineage.

Disposition: **evidence only / needs behavioral lineage before learning**. Do not invent a fixing commit from product requirements, screenshots or deployment success. A future Hunter candidate may enter the governed queue only after an exact defective ref, exact fixing ref, scored implementation paths, verified behavior change and blind-review boundary are recovered.

## 5. Current admitted project-learning work

The only candidates admitted by PR #159 remain the two provenance-complete TechGuyCheckm8 repairs:

- `learn-tgcheckm8-checksum-path-namespace-20260723`
- `learn-tgcheckm8-checkout-credential-boundary-20260723`

Their direct-terminal round may produce bounded proposals, but neither becomes permanent until council, positive controls, clean negative controls, unrelated transfer, hidden holdout, exact-head proof, durable evidence and explicit owner-controlled promotion complete.

## Authority

- No recovered document can auto-promote a lesson.
- No model response can auto-promote a lesson.
- No green deployment or workflow can substitute for the evidence gates of the lesson being claimed.
- Existing accepted knowledge is reused instead of duplicated.
- Evidence that lacks verified defect/fix lineage stays evidence.
- Research belonging to another THETECHGUY project stays in that project's authority lane.
- Sergeant remains final review authority and automatic merges remain forbidden.
