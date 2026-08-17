# Project Harvest Source Disposition — 2026-08-16

This record prevents a recovery batch from being mistaken for a set of automatically accepted Sergeant lessons. Every source was checked against current repository truth before deciding whether it should train Sergeant.

Repository evidence below is pinned to immutable `owner/repository@commit` references. Where a source file is Git-tracked, its Git blob object ID is recorded as an additional content identity. A Git blob ID is not being presented as a SHA-256 digest. Recovered material that has no resolvable repository object is explicitly marked non-reproducible rather than used as learning lineage.

## 1. Transfer-set-8 battle snapshot — already integrated

The recovered battle snapshot described an earlier state where transfer set 8 remained `0/3` and three generalized officers had not yet been wired into the canonical review path.

The corresponding model-free detector families are already present at `jaydumisuni/Sergeant@ee4a152e25ae5965edbae32c9a50d6f2cc6c48d2` in `main_review/static_external_integrity_review.py` (Git blob `7276e92d6dc4a4b6a2e4650f1c1548d5c60468a5`) and its existing regressions:

- untrusted Git/submodule execution requires transport and hook hardening;
- persisted queue read-modify-write requires safe serialization and exhausted deliveries must not disappear;
- webhook failure acknowledgement and payment-credit paths require failure honesty, atomicity and idempotency.

Disposition: **already learned / no duplicate promotion**. The recovered battle snapshot itself is historical recovery material, not a new immutable training lineage.

## 2. Preserve-before-delete evidence — already accepted

The accepted lesson is pinned at `jaydumisuni/Sergeant@ee4a152e25ae5965edbae32c9a50d6f2cc6c48d2` as `.github/self-learning/lessons/preserve-before-delete-20260724.json` (Git blob `c9dfaf637562cb3f25ac3823680a163f95078350`). That lesson itself records its defective ref, fixing ref, merge ref, preserved-artifact counts and governed proof requirements.

Disposition: **already accepted / no duplicate lesson**. Preservation proof remains part of Sergeant's permanent governed knowledge; copying evidence never creates deletion authority.

## 3. Ptah donor pool — outside Sergeant learning truth

The recovered Ptah donor pool is Phase 0A architecture and repository research for Ptah. It explicitly separates confirmed donors from unresolved donors whose canonical repository, licence and implementation still require verification.

No immutable Sergeant repository object is asserted here for that recovered donor-pool attachment. It is therefore **not reproducible Sergeant defect/fix lineage** and must not be promoted as if it were one.

Disposition: **not Sergeant training evidence**. Ptah donor research may help Ptah architecture, but it must not become a Sergeant detector or learned rule merely because it appeared in the same recovery batch.

## 4. Hunter Employee OS requirement and UI material — evidence only until lineage exists

The Hunter acceptance authority is resolvable at `jaydumisuni/hunter@bbc3e57d6d83ed2a39fdf589854ec32d02068d55` in `docs/HUNTER_EMPLOYEE_OS_UI_ACCEPTANCE_CHECKLIST.md` (Git blob `7032ba06cdfd83a9717d87256ef33b28341ac42e`). It explicitly separates source, runtime, visual, employee-usability and owner-approval gates and states that a passing build or deployed preview is not completion proof.

The isolated review checkpoint is separately resolvable at `jaydumisuni/hunter@d0142d2782b930345b68497a14dd2c93531e4682`. Its direct review UI source `cloudflare/hunter-api-worker/src/review_full_ui.ts` is Git blob `bb4f0f83f550a3f4fcd02fd0ff6d662666cd3ffe`. The commit adjusts review-gate wording/source checks; this Sergeant record does **not** claim an immutable deployment artifact digest or production approval from that commit.

Disposition: **evidence only / needs behavioral lineage before learning**. These immutable references establish what the Hunter material actually says, but they do not establish a transferable Sergeant product defect/fix lineage. Do not invent a fixing commit from product requirements, screenshots or deployment success. A future Hunter candidate may enter the governed queue only after an exact defective ref, exact fixing ref, scored implementation paths, verified behavior change and blind-review boundary are recovered.

## 5. PR #159 project-learning disposition

PR #159 admitted exactly two provenance-complete TechGuyCheckm8 candidates from source records pinned on the Sergeant base at `jaydumisuni/Sergeant@ee4a152e25ae5965edbae32c9a50d6f2cc6c48d2`:

- `learn-tgcheckm8-checksum-path-namespace-20260723` — `.github/self-learning/signals/tgcheckm8-checksum-path-namespace-2026-07-23.json`, Git blob `98e435dcd498fdc16538c667047cca599d495d61`;
- `learn-tgcheckm8-checkout-credential-boundary-20260723` — `.github/self-learning/signals/tgcheckm8-checkout-credential-boundary-2026-07-23.json`, Git blob `f7cb4d7e9baa63afee06dc7617238fb8bf694df9`.

Both source records bind the same immutable TechGuyCheckm8 defect/fix pair, `3b9b5d2469fed602cd6b5c728109cf193b9ccba1` → `40291a738e866e53b7d1cdcd0cf31f6e860357f5`, while preserving separate learning objectives and scored paths.

### Checksum path-namespace candidate — accepted

The checksum candidate completed council, executable positive and clean controls, unrelated-language JavaScript transfer, a post-freeze hidden holdout, exact TechGuyCheckm8 defective/fixing replay, canonical integration, exact-head GitHub proof, durable evidence verification and explicit owner-controlled promotion.

Its permanent governed record is `.github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json`, first frozen at `jaydumisuni/Sergeant@874e83cd9363a8545e0bd87c4dbcd9a08dee9d12`. The implementation proof and promotion-authority head recorded by that lesson is `84faf9644b323792e1afd565fd4e65b653f668ee`.

Disposition: **accepted lesson**. This acceptance does not grant automatic promotion to future candidates and does not grant merge authority to PR #159.

### Checkout credential-boundary candidate — rejected

The credential-boundary candidate reached the governed council and was rejected because the Defender disproved the proposed lesson. It has no accepted-lesson record and must not be treated as learned truth or revived from the same evidence.

Disposition: **rejected / no promotion**. A future credential-boundary candidate would require new provenance-complete evidence and a new governed evaluation rather than reusing this rejected proposal.

The admitted PR #159 learning round is therefore dispositioned: one candidate accepted and one rejected. PR #159 remains a separate draft implementation/review vehicle; lesson acceptance does not authorize or imply merging that PR.

## Authority

- No recovered document can auto-promote a lesson.
- No model response can auto-promote a lesson.
- No green deployment or workflow can substitute for the evidence gates of the lesson being claimed.
- Existing accepted knowledge is reused instead of duplicated.
- Evidence that lacks verified defect/fix lineage stays evidence.
- Rejected proposals do not become learned truth without new provenance-complete evidence and a new governed evaluation.
- Research belonging to another THETECHGUY project stays in that project's authority lane.
- Sergeant remains final review authority and automatic merges remain forbidden.
