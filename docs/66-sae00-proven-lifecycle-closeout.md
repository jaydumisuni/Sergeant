# SAE-00 — PROVEN lifecycle closeout

Date: 2026-09-02

Status: **PROVEN**.

This document closes the lifecycle of `SAE-00 — Founding authority and preservation reference` after its construction candidate was reviewed, corrected, proved on its exact head, explicitly accepted for continued Sergeant completion by the Owner, and merged to canonical `main`.

## Authority chain

- Founding roadmap authority: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Construction record: `docs/62-sae00-founding-authority-and-preservation-reference.md`.
- Construction manifest: `docs/63-sae00-founding-authority-reference-manifest.json`.
- Construction PR: `#170`.
- Exact construction head: `7d8b163ae1694f6b1fce4dccee97ba58ac3977c6`.
- Canonical merge commit: `7052f6da8252a06907ec2fc4d0bd59abf4a2144d`.
- Owner disposition: on 2026-09-02 the Owner explicitly directed Sergeant to be finished first, using the proven Tenfold Gen 1 execution pattern and milestone pushes. That instruction supplies the Owner-controlled gate that the construction record was waiting for.

The original `docs/63` manifest remains `CANDIDATE` intentionally. It is historical evidence of the pre-merge construction state and must not be rewritten to pretend that later authority existed earlier.

## Lifecycle disposition

`SAE-00` now resolves as:

```text
AUTHORIZED
→ CANDIDATE
→ REVIEWED
→ QUALIFIED
→ PROVEN
```

The advancement is justified by the combination of:

1. exact-head construction proof and review already attached to PR #170;
2. all discovered review findings dispositioned before merge;
3. explicit Owner acceptance of the Sergeant-completion programme;
4. canonical merge of the exact reviewed head into `main`;
5. this separate closeout generation preserving the original candidate record unchanged.

### Root bootstrap authority

`SAE-00` is the dependency-DAG root and `SAE-30` — the programme that later creates the general Qualification Authority Registry and Qualification Attestation substrate — itself depends on `SAE-00`. Requiring SAE-30 qualification machinery to qualify SAE-00 would therefore create a circular bootstrap dependency that the frozen roadmap does not define.

The founding architecture explicitly permits **Owner/Root constitutional authority** inside the finite trusted-computing boundary (`docs/58`, section 26). SAE-00 therefore uses that already-frozen Owner/Root constitutional TCB as its one-time root bootstrap authority. The bootstrap is bounded to the exact SAE-00 generation identified above and to SAE-00's declared construction-authority outputs.

This bootstrap authority:

- is **not** a substitute for SAE-30's future Qualification Authority Registry;
- cannot qualify or prove any dependent node;
- cannot satisfy Genesis independent/external qualification requirements;
- cannot convert business-risk acceptance into engineering PASS;
- creates no normal Sergeant verdict authority and no partial-generation activation right.

Once SAE-30 exists, descendants that require its qualification/provenance substrate must use that substrate according to the roadmap. SAE-00's root bootstrap is not precedent for bypassing downstream qualification law.

No normal Sergeant verdict authority transfers as a result. `SAE-00` only produces the construction authorities declared by the roadmap: `SERGEANT_PRESERVATION_REFERENCE`, `FOUNDING_ARCHITECTURE_AUTHORITY`, and `ROADMAP_EXECUTION_AUTHORITY`.

## Dependency effect

The `SAE-00` proof dependency is now resolved for downstream roadmap nodes. Safe preparation that was already allowed remains allowed; additionally, nodes whose only unresolved proof dependency was `SAE-00` may now proceed through freeze, qualification and proof subject to their own requirements and any other dependencies.

This does not qualify or prove any dependent node automatically. In particular:

- `SPIKE-ID`, `SPIKE-EXT`, and `SPIKE-SEM` must each earn their own proof;
- `SAE-10` and `SAE-20` must earn their own qualification/proof;
- `SAE-30` additionally requires proven `SPIKE-ID` and `SPIKE-EXT`;
- no partial Assurance Evolution generation may replace canonical Sergeant before the Genesis/activation gates defined by the roadmap.

## Recovery rule

A zero-context executor recovering Assurance Evolution must treat `docs/62`/`docs/63` as the historical SAE-00 candidate generation and this document plus `docs/67-sae00-proven-lifecycle-closeout-manifest.json` as the later lifecycle-closeout authority. Live GitHub remains authoritative over stale prose.
