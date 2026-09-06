# SAE-20 — PROVEN lifecycle closeout

Date: 2026-09-06

Status: **PROVEN**.

This separate lifecycle generation closes `SAE-20 — Assurance Contract Registry + Authoring Audit` after the immutable candidate was hostile-reviewed through multiple generations, corrected under regression evidence, proved on its exact final head, merged with an exact-head guard, and then subjected to the ACR-specific qualification campaign required by the founding architecture.

## Authority chain

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- PROVEN root execution authority: `docs/66-sae00-proven-lifecycle-closeout.md` / `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.
- SAE-00 PROVEN closeout merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Historical SAE-20 candidate document: `docs/82-sae20-acr-authoring-audit-candidate.md`.
- Historical SAE-20 candidate manifest: `docs/83-sae20-acr-authoring-audit-candidate-manifest.json`.
- Construction/review PR: `#178`.
- Exact final candidate head: `4c00b54b578aed0f9925cff9345b4482c46ebc3e`.
- Canonical candidate merge commit: `3a5522c5a789e4ef5e512af4d491cad95a051307`.

The historical `docs/83` manifest remains **CANDIDATE** intentionally. It is immutable construction evidence and is not rewritten to manufacture later authority inside the candidate generation.

## Exact candidate execution proof

The final exact candidate head `4c00b54b578aed0f9925cff9345b4482c46ebc3e` independently earned:

- GitHub Actions CI run `33998093987`: **1338 passed / 2 historical XFAIL / 0 failed**;
- exact clean-clone proof from the same run: **1338 passed / 2 historical XFAIL / 0 failed**;
- ordinary pytest artifact digest `sha256:b22c7542c22d061d7550863675c61e1fe215b174f6ff3437387bbcaf52fdbffd`;
- clean-clone pytest artifact digest `sha256:82ae92b761280e4889cf50283a4db3b202fcbadeffc4173baa8de73259a33240`;
- exact Main Review run `33998093976`: **APPROVE / repository PASS / diff PASS / capability PASS**;
- Main Review result artifact digest `sha256:ff7463663b9aa31491e316c89c0a4ca07304e10a80951eee3ec5307c346655fe`;
- Main Review changed-scope repository defects: **0**;
- Main Review unresolved explicit assurances: **0**;
- local current-correction SAE-20 focused collection: **65 passed / 0 failed**, preserved only as construction evidence.

The two XFAILs are pre-existing historical fixtures outside SAE-20 and are preserved as XFAIL rather than relabeled as passes. GitHub Actions availability remains execution evidence, not authority by itself.

## ACR-specific qualification campaign

SAE-20 cannot become PROVEN merely because its code exists or its ordinary tests are green. The founding architecture requires the ACR itself to survive omission and weakening attacks inside a bounded domain and requires qualification truth to include materially external hostile evidence.

The closeout therefore adds `tests/test_sae20_acr_qualification_campaign.py` without changing the accepted SAE-20 production candidate. The fixture exercises an unrelated TypeScript/Express bounded-domain transfer and verifies:

- a clean transfer control remains `CLEAN` but never self-qualifies;
- TRUE / FALSE / UNKNOWN applicability and negative absence burden remain fail-closed;
- semantic-carrier, consumer-interpretation, affected-relation, premise, obligation, material-input and falsifier deletion attacks are detected;
- mandatory external-review-lane undercount is detected;
- SET/ORDER/cardinality/closure weakening cannot silently pass;
- applicability semantics, repeated authority premises, coherence, temporal and independence rules cannot drift;
- tampered Authoring Audit authority fails closed before its requirements are trusted.

This supplements, rather than replaces, the candidate's existing attack matrix for the roadmap-mandated omission, cardinality, applicability, material-input, falsifier-family and external-review-lane-cardinality attacks.

## Materially external hostile evidence

The qualification corpus did not establish its own completeness by internal tests alone. Two external holdout waves found real defects after prior generations had already earned green mechanical proof:

1. Fresh Codex review on hardened head `61f82eaa14478c409d684017663edccf6ee311e8` found six valid defects, including profile self-validation, exact contract-generation binding, frozen-map canonicality, unsupported-value UNKNOWN conservation, type-sensitive JSON equality and one-shot iterable preservation. Those findings were fixed in successor head `0fcb1141777c4309d8d4ed66f889870ab036f9ac` and retained as regressions.
2. Fresh CodeRabbit review after that successor found the additional unit-cardinality type-identity defect: `True` and `1.0` could alias integer `1`. Exact final head `4c00b54b578aed0f9925cff9345b4482c46ebc3e` fixed it and added the regression.

The current final head also has targeted CodeRabbit confirmation that the unit-cardinality defect is fixed and that the repeated one-shot-iterable report no longer applies to the exact current implementation.

These reviewer-originated defects function as materially external hostile/holdout evidence because they were discovered outside the candidate's then-green internal corpus and forced new generations rather than being waived.

External-review accounting remains explicit: there is **no claim of a new full Codex or CodeRabbit review submission over the complete exact `4c00b54...` tree**. Absence of such a full submission is not treated as a PASS. The closeout uses the bounded pre-SAE-30 Owner/Root exact-head completion audit plus targeted external current-head verification, while preserving that limitation.

## Exact-head completion audit

Bounded Owner/Root exact-head completion audit GitHub review `5124770297` was submitted as **COMMENT** evidence, not self-approval, against exact candidate head `4c00b54b578aed0f9925cff9345b4482c46ebc3e`.

It records zero remaining known actionable SAE-20 findings after reconciling the frozen charter, exact-head code, exact-head CI/clean-clone/Main Review evidence, and all review threads. All inline PR #178 review threads were resolved before the guarded merge.

## Qualification disposition

`SAE-20` now resolves as:

```text
AUTHORIZED
→ CANDIDATE
→ REVIEWED
→ QUALIFIED
→ PROVEN
```

The exact closed generation produces only the authority declared by the frozen roadmap:

- `QUALIFIED_ACR_FOUNDATION`.

This qualification is bounded to the SAE-20 foundation generation represented by the exact candidate artifacts and does not claim universal program semantics or universal contract completeness.

## Bootstrap authority boundary

The frozen roadmap gives SAE-20 exactly one proof dependency: PROVEN `SAE-00`. The general Qualification Authority Registry, EEPR machinery and Genesis qualification substrate are created later by `SAE-30`; retroactively requiring SAE-30 here would invert the approved dependency graph.

This closeout therefore uses the same bounded pre-SAE-30 constitutional bootstrap class as the earlier foundation closeout:

- PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY`;
- Owner/Root constitutional authority inside the finite founding TCB;
- materially external hostile evidence from the PR review lineage;
- exact-head deterministic execution and review proof.

This bootstrap:

- is not SAE-30's future general Qualification Authority Registry;
- cannot qualify or prove dependent nodes;
- cannot satisfy Genesis independent/external qualification lanes;
- cannot convert Owner business-risk acceptance into engineering PASS;
- cannot activate a partial Assurance Evolution generation;
- cannot grant candidate self-activation or normal Sergeant verdict authority.

## Dependency effect

SAE-20's proof dependency is resolved and `QUALIFIED_ACR_FOUNDATION` is canonical for downstream nodes that explicitly consume SAE-20.

This closeout does **not** auto-qualify or auto-prove any dependent node. `SAE-40` now has its two frozen upstream proof dependencies (`SAE-10` and `SAE-20`) available, but must still execute and prove its own Judge Assurance Ledger programme. `SAE-R1`, `SAE-50`, `SAE-60` and later nodes retain all other frozen dependencies.

No Genesis or partial-generation activation occurs.

## Recovery rule

A zero-context executor must treat `docs/82` / `docs/83` and exact final candidate head `4c00b54b578aed0f9925cff9345b4482c46ebc3e` as the immutable SAE-20 candidate generation, candidate merge `3a5522c5a789e4ef5e512af4d491cad95a051307` as the canonical construction merge, and this document plus `docs/85-sae20-proven-lifecycle-closeout-manifest.json` as the later lifecycle-closeout authority.

Live GitHub remains authoritative for mutable repository state. No future recovery may rewrite the historical candidate manifest from `CANDIDATE` to `PROVEN`.
