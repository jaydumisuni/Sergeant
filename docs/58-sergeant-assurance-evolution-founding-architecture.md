# Sergeant Assurance Evolution — Founding Architecture

Status: **OWNER-APPROVED FOUNDING ARCHITECTURE CANDIDATE** on isolated roadmap authority.

This document defines the architecture that future implementation must satisfy. It does **not** claim current Sergeant already implements these mechanisms. Until the Genesis Exit Gate is proven and explicitly activated, current canonical Sergeant remains the active reviewer.

## 1. Product identity and preservation

Sergeant remains the independent engineering reviewer whose operating stance is:

```text
assume the candidate may be wrong
→ attack the claim
→ demand evidence
→ attempt falsification
→ admit only surviving evidence
→ PASS / NEEDS WORK / BLOCK
```

Sergeant is not Tenfold. Tenfold may execute the approved engineering campaign; Sergeant remains the subject being evolved and the final automated engineering-review authority.

The command chain remains:

```text
Owner / human constitutional + business-risk authority
→ Sergeant
→ Cpl
→ permanent officers
→ privates
→ tools / scanners / models / facilities
```

Permanent officers remain Quartermaster, Scout, Engineer, Medic, Mechanic, Analyst, Challenger, Archivist, Judge and Hermes.

The following are preservation requirements:

- model-free normal review;
- useful ordinary-CPU operation;
- no mandatory AI account;
- no GPU requirement;
- public verdict law remains `PASS / NEEDS WORK / BLOCK`;
- Sergeant remains final automated engineering-review authority;
- Cpl remains the single command/co-ordination layer;
- Judge remains evidence/admission authority beneath Sergeant;
- Challenger remains permanent adversarial authority beneath Sergeant;
- evidence providers create facts, not verdict votes;
- optional models remain evidence/reasoning providers beneath the hierarchy;
- scanner over-collection remains legal;
- generic risk signals do not automatically gate without grounded promotion;
- deterministic finding identity remains compatible for presentation/grouping;
- blind expected truth remains outside the review workspace;
- external reviewers remain witnesses, never Sergeant authority;
- governed learning remains provenance-bound, adversarial and owner-promoted;
- no automatic lesson promotion;
- read-only/default-deny GitHub review remains the normal public boundary;
- no PR-controlled project execution by default;
- no candidate-controlled reviewer authority;
- no self-granted repository writes;
- no automatic merge;
- existing dependency-frontier / 10-for-2 doctrine remains Sergeant doctrine;
- no second scheduler, Cpl, Judge or verdict engine;
- one verdict meaning is preserved across GitHub and richer local facilities;
- fast ordinary review remains fast through risk-adaptive assurance rather than ceremonial heavyweight proof everywhere.

## 2. Freeze-stage terminology

These states are distinct:

```text
FOUNDING ARCHITECTURE FREEZE
    reviewed specification becomes canonical implementation authority

IMPLEMENTED
    required machinery exists

QUALIFIED
    implementation/capability earned the authority it claims

INTEGRATED
    qualified components operate coherently inside Sergeant

FOUNDING GENERATION PROVEN
    exact integrated generation passed Genesis qualification and final proof
```

Therefore:

```text
architecture frozen != implemented
implemented != qualified
qualified != integrated
integrated != founding-generation proven
```

## 3. Seven founding mechanisms

The architecture has seven primary mechanisms and no additional command hierarchy:

1. **Review World + Review Authority Bundle (RAB)**
2. **Assurance Contract Registry (ACR)**
3. **Judge Assurance Ledger**
4. **Coverage + Fact Census + Contract-Instance Census + Expected Obligation Compiler**
5. **Capability Passports + Rooted Positive Authority**
6. **Evidence / Proof World / Falsification**
7. **Independent Rust Assurance Kernel**

The durable result is an **Assurance Capsule**.

Existing Cpl/officers/Judge/Sergeant/Hermes operate or transport these mechanisms; none is replaced.

## 4. Exact Review World

Every verdict binds one immutable Review World.

A GitHub/PR Review World binds at minimum:

- repository identity;
- base SHA;
- head SHA;
- candidate tree identity;
- diff identity;
- explicit scope;
- review mode;
- RAB ID;
- review generation.

Merge-readiness claims additionally bind the exact synthetic merge-result tree when the merge result is the claimed world.

A local Review World binds its exact declared local scope, potentially including HEAD, index, tracked worktree state, untracked state under explicit policy, and selected-scope digest.

Historical verdict truth is immutable for its Review World. Later mutable state may make that verdict stale for current use; it does not rewrite history.

Same head with a different base, wrong merge result, stale local state, scope substitution, unresolved submodule/LFS/generated-state identity, or other world ambiguity cannot reuse a positive verdict.

## 5. Review Authority Bundle

Every Review World binds one immutable content-addressed RAB containing the exact generations of authority used by the review, including at least:

- epistemic constitution;
- safety constitution;
- ACR generation;
- capability/passport registry generation;
- obligation law generation;
- evidence law generation;
- independence law generation;
- Rust contract/kernel generation;
- qualification-authority registry generation;
- Root authority generation.

Individually authorized components do **not** imply an authorized combination. The exact RAB manifest must be authorized as a whole.

Candidate changes to future authority are reviewed as candidate content. They cannot become active against their own review. No subsystem may perform `latest compatible authority` substitution during a frozen review.

## 6. Assurance Contract Registry

The ACR is the finite, qualified semantic specification under which Sergeant may make positive assurance claims. It is explicitly not universal program semantics.

Each contract may define:

- identity and generation;
- supported domain;
- declarative applicability predicate;
- bound subject variables;
- semantic carrier/fact families;
- affected-relation families;
- collection/cardinality semantics;
- required closure grades;
- mandatory premises;
- mandatory obligations;
- admissible proof classes;
- material Proof World inputs;
- coherence requirements;
- temporal validity;
- mandatory falsifier families;
- required independence;
- permitted capabilities;
- unsupported/UNKNOWN fallback.

Applicability uses at least `TRUE / FALSE / UNKNOWN` semantics. Missing fact is not false fact. `PROVEN_NO_MATCH` is an absence claim and requires sufficient closure to prove non-applicability.

Every active mandatory ACR contract must be evaluated. Missing evaluation is UNKNOWN.

Founding composition is conservative: all applicable mandatory contract instances contribute their obligations. There is no first-match, priority, specificity or silent subsumption rule capable of weakening assurance.

## 7. ACR qualification and authoring audit

A contract gains positive assurance authority only inside an explicitly declared bounded domain and only after an independent qualification campaign attacks the contract specification itself.

Qualification attacks omission and weakening in at least:

- semantic carrier families;
- consumer/framework interpretation families;
- applicability triggers;
- affected-relation families;
- cardinality declarations;
- SET/MULTISET/ORDER semantics;
- closure-grade requirements;
- mandatory premise families;
- mandatory obligation families;
- material Proof World inputs;
- coherence rules;
- temporal-validity rules;
- mandatory falsifier families;
- repeated authority-premise families;
- independent-review lane cardinality;
- independence requirements;
- negative/non-applicability requirements;
- unsupported/UNKNOWN fallback.

The ACR candidate cannot establish the completeness of its own qualification corpus. Qualification truth must include materially external evidence such as independently authored hostile cases, historical real defects/fixes, independent deletion/undercount mutations, authoritative framework/runtime behavior, unrelated-language or unrelated-project transfer, clean controls, hidden holdout and independent hostile review.

Qualification is bounded: `QUALIFIED_FOR_DOMAIN(D, generation G)`, never `UNIVERSALLY_COMPLETE`.

A later real-world defect proving that a qualified ACR omitted a mandatory family is an **ACR qualification escape**. The affected generation becomes subject to suspension/revocation and impact analysis; the escape becomes permanent qualification evidence; no automatic corrected-contract promotion is allowed.

## 8. Total Set-Valued Closure Law

The central constitutional invariant is:

```text
VALID MEMBERS != COMPLETE AUTHORITY-BEARING COLLECTION
```

Any PASS-bearing collection whose omission could reduce assurance must bind:

- collection identity;
- Review World;
- governing authority;
- independent source/basis identities;
- member identity semantics;
- SET/MULTISET/ORDER semantics where material;
- cardinality semantics;
- required closure grade;
- actual members;
- completeness witness/authority;
- generation;
- unresolved remainder/UNKNOWN.

Closure grades are:

- `EXACT`
- `CONSERVATIVE_SUPERSET`
- `PARTIAL`
- `UNKNOWN`

A valid positive subset remains `PARTIAL` unless independent authority proves the required closure grade. Empty-set/absence claims require the same completeness burden.

Collection semantics may distinguish `ZERO_OR_ONE`, `EXACTLY_ONE`, finite sets, finite multisets, ordered finite collections, bounded-N or open/unbounded domains. No generic cardinality upgrade is allowed.

Completeness may terminate only in a canonical exact source structure, frozen qualified specification constant, independently closed upstream collection, qualified bounded derivation, independently checkable world-to-collection certificate, or explicit finite TCB primitive. A collection may not define its own universe for purposes of proving its completeness.

This law applies to omission-sensitive:

- raw Review World sets;
- affected relations;
- semantic binding sets;
- contract instances;
- obligations;
- repeated authority premises;
- material Proof World inputs;
- mandatory falsifier instances;
- quantified path/endpoint/state-transition proof sets;
- mandatory independent evidence lanes.

Late member discovery creates a new closure generation and conservatively invalidates dependent positive proof until closure is rebuilt.

## 9. Contract-instance and obligation totality

Contract-level applicability is insufficient when one contract binds multiple subjects. Every applicable mandatory **contract instance** must be represented.

A contract instance identity binds at least Review World, contract ID and bound subjects.

The expected applicable contract-instance set is independently derived from closed world facts plus frozen ACR authority. All matched instances contribute obligations. Every mandatory obligation retains contract-instance provenance.

Presentation dedup may reduce repetition; proof-authority dedup may not erase contract instances, obligation multiplicity, UNKNOWN, contradiction or scope.

PASS requires the expected mandatory obligation set to close completely under admissible evidence or admissible non-applicability proof.

## 10. Judge Assurance Ledger

Existing Judge is amplified; there is no second Judge.

The ledger carries authority-bearing records such as:

- Review World;
- ACR evaluation;
- collection closure;
- contract instance;
- claim;
- obligation;
- assumption;
- evidence;
- falsifier instance;
- contradiction;
- qualification evidence;
- admission;
- invalidation;
- verdict lineage.

Existing generalized `finding_id` may remain for UI/grouping compatibility. Positive proof authority uses full cryptographic instance identity.

Ledger merge/dedup must be monotonic: it may never erase UNKNOWN, contradiction, required multiplicity, changed/affected provenance or evidence scope limits.

## 11. Capability Passports and semantic capability qualification

A load-bearing semantic capability may contribute positive mandatory assurance only when it is `QUALIFIED + ACTIVE + APPLICABLE` for the exact domain/generation.

A Capability Passport binds at least:

- capability identity and implementation digest;
- exact generation;
- supported domain;
- consumed ACR generation(s);
- claimed fact/collection families;
- claimed proof class and closure grades;
- declared cardinality capability;
- incompleteness behavior;
- environment/toolchain requirements;
- blind spots;
- parser/library/common-mode lineage;
- positive/negative controls;
- omission/undercount mutations;
- false-positive controls;
- historical real-defect replay;
- hidden holdout;
- transfer evidence;
- resource-exhaustion behavior;
- qualification/revocation state.

For EXACT claims, qualification requires bounded ground-truth cases where the complete set is independently known and deletion/extra-member/multiplicity/order/partial-basis/late-member/timeout/state-explosion/stale-generation attacks are exercised. Conservative-superset claims must prove bounded soundness. If neither can be established, the capability ceiling remains PARTIAL/HEURISTIC/EMPIRICAL/UNKNOWN as appropriate.

Different implementation language or tool name alone does not establish independence.

## 12. Qualification issuance authority

`QUALIFIED` is not a producer-writable field. It is a derived authority state.

The exact RAB contains a Qualification Authority Registry binding authorized qualification issuers to artifact families, domains, proof ceilings, independence constraints, generation and revocation state.

A Qualification Attestation binds at minimum:

- exact subject identity/digest/generation;
- artifact family;
- qualified domain;
- ACR generation;
- qualification-protocol generation;
- Judge-admitted qualification-evidence root;
- authorized proof-class ceiling;
- authorized closure-grade ceiling;
- independence/lineage disposition;
- qualification-authority identity/generation;
- revocation/currentness;
- authenticated provenance.

Authentic attestation is not automatically valid qualification. Rust/Judge must also establish issuer authorization, subject/domain/generation match, qualification-protocol closure, evidence closure, required external lanes, ceilings and non-revocation.

The operational invariant is:

```text
candidate-controlled operational principal != qualification issuer principal
```

Candidate repository code, CI, build/runtime, analyzers, generated helpers and candidate-held credentials cannot issue their own authoritative qualification.

The authority chain terminates at explicit Owner/Root constitutional trust through the whole authorized RAB. This prevents automated producer self-certification without pretending to eliminate Root trust.

## 13. External Evidence Provenance Law

Evidence bytes plus content hash do not establish externality or independence.

Every evidence item counted toward a mandatory independent/external qualification lane must carry an authenticated **External Evidence Provenance Record (EEPR)** binding at minimum:

- evidence identity/digest;
- exact candidate/Review World;
- evidence-source principal identity;
- authenticated source provenance;
- source individual/organization where applicable;
- source authority generation;
- creation time/generation;
- relationship to candidate authoring lineage;
- relationship to qualification-corpus lineage;
- relationship to candidate-controlled infrastructure;
- reviewer/tool/model lineage where material;
- who controlled review prompt/instructions;
- who selected review inputs;
- who selected/accepted findings;
- provenance-verification method;
- independence disposition.

Independence disposition is exactly one of:

- `INDEPENDENT`
- `NOT_INDEPENDENT`
- `UNKNOWN_INDEPENDENCE`

Only `INDEPENDENT` may satisfy a mandatory independent lane. Missing provenance is `UNKNOWN_INDEPENDENCE`.

Independence is about control lineage, not surface variation. Different file/chat/model/account/session/tool does not create independence by itself.

A candidate author who writes the review prompt and asks AI to review the candidate produces useful internal hostile evidence, but that lane is `NOT_INDEPENDENT` for Genesis qualification. An independent reviewer may use AI as tooling if the independent reviewer controls and adopts the review and source provenance closes.

Mandatory external-review instance collections themselves obey Total Set-Valued Closure; cherry-picking one favorable review cannot satisfy a larger required review census.

A later discovery that an allegedly independent lane was fabricated, source-spoofed, candidate-controlled or materially misrepresented is an external-provenance escape requiring impact analysis and suspension/revocation where appropriate.

## 14. Genesis bootstrap

The first Assurance Evolution generation has no prior fully qualified Assurance Evolution generation to qualify it. Bootstrap trust is explicit and one-time.

The first generation begins as `GENESIS_PROVISIONAL`, not qualified/active/proven.

Genesis provisional may run shadow qualification, build candidate Review Worlds/RAB/ACR, execute Cpl/officer/Judge workflows, run Rust checks, replay historical defects, run mutations/falsifiers and produce candidate Assurance Capsules. It has **zero normal positive Assurance Evolution verdict authority**.

Genesis qualification requires one immutable Genesis Qualification Package binding the exact candidate/RAB/ACR/Rust/qualification-protocol generations plus preservation proof, model-disabled and CPU proof, historical replay, clean controls, omission/undercount/cardinality/ACR/material-input/falsifier/authority/common-mode mutations, unrelated-language/project transfer, independently authored hidden cases, clean-clone/repository-only/no-private-helper proof, independent hostile implementation review evidence, residual UNKNOWNs and limitations.

At least one material hostile qualification lane must be independent of Genesis candidate implementation and qualification-corpus authoring lineage and must satisfy the EEPR law.

The **Genesis Exit Gate** requires all mandatory qualification obligations closed, no mandatory UNKNOWN, required independent/external evidence present and authenticated, mutations/falsifiers closed, preservation checks passed, Rust constitutional admissibility, Judge admission and explicit Owner/Root activation over the exact qualification-package digest.

Successful exit produces an immutable Genesis Activation Record. Only the exact bound generation becomes qualified/active. Successor generations cannot reuse the Genesis shortcut.

Same-human Owner/author reality is recorded honestly: the same human may author engineering and hold Root constitutional authority. That fact does not count as an independent qualification lane. External hostile evidence remains mandatory.

A later Genesis qualification escape triggers impact analysis and current-authority suspension/revocation where required; Genesis is not permanently infallible.

## 15. Owner business-risk separation

Owner/human remains above Sergeant for constitutional evolution and business-risk decisions, but Owner business action cannot rewrite engineering truth.

EngineeringVerdictRecord and BusinessRiskDecisionRecord are structurally disjoint artifact families.

Engineering verdict contains only `PASS / NEEDS WORK / BLOCK` under Sergeant authority.

Business risk may record actions such as `SHIP_WITH_ACCEPTED_RISK`, `MERGE_WITH_ACCEPTED_RISK`, `DEPLOY_WITH_ACCEPTED_RISK`, `DEFER` or `CANCEL`, referencing the exact engineering verdict.

There is no legal Risk→Verdict cast. Business risk cannot close obligations, remove UNKNOWN, create evidence, qualify capabilities/ACR, satisfy Rust admissibility or become automatic learning truth.

Canonical truth may therefore be:

```text
engineering_verdict = BLOCK
business_action = DEPLOY_WITH_ACCEPTED_RISK
```

never a rewritten PASS.

## 16. Evidence and Proof World

Every mandatory obligation defines admissible proof classes. Evidence binds the exact obligation, contract instance, Review World, capability generation, facility generation, relevant consumer/dependency/runtime/configuration/provider generations, assumptions and temporal validity as required by ACR.

Repeated material inputs themselves must close under Total Set-Valued Closure.

Where multiple values must represent one admissible world, ACR defines coherence requirements. Individually authentic values that never coexisted cannot form a Frankenworld proof.

Weak evidence cannot self-label itself as a stronger proof class.

## 17. Mandatory falsification

Existing Challenger and `falsifiers_checked` are amplified, not replaced.

A falsifier family name is not proof that falsification happened.

From closed ACR contracts, closed parameter domains and closed contract instances, Sergeant derives the expected mandatory falsifier-instance set. Each instance binds exact Review World, contract/obligation/claim, falsifier family, bound subjects, perturbation/counter-world parameters and generation.

Every mandatory falsifier instance requires admitted evidence proving the intended perturbation actually occurred. No-op mutation does not count.

Open-ended fuzzing/randomized exploration is empirical/statistical unless a genuinely exhaustive bounded domain is proven; budget/resource exhaustion remains UNKNOWN for completeness claims.

## 18. UNKNOWN conservation and invalidation

Mandatory UNKNOWN cannot disappear through provider output, normalization, dedup, officer synthesis, Judge, Rust, capsule or Hermes.

UNKNOWN includes unsupported constructs, timeout, crash, missing facility, parser failure, state explosion, truncation, applicability uncertainty, affected-universe uncertainty, consumer uncertainty, Proof World uncertainty, qualification uncertainty, independence uncertainty and material contradiction.

Unqualified evidence may add concerns/scope/hypotheses and trigger stronger investigation; it may not reduce assurance, prove negative applicability, suppress contracts/instances/obligations or remove UNKNOWN.

New members, generation changes, revocations and qualification/provenance escapes conservatively invalidate dependent positive proof.

## 19. Rooted positive authority

Positive authority must be rooted and acyclic. Direct or transitive self-enabling cycles are forbidden.

Authority-bearing claim types use frozen typed mandatory premise schemas. Producers submit typed proof objects; they do not author arbitrary authoritative dependency graphs.

Rust reconstructs authority relationships from required typed references. Missing required premise is structurally invalid; unknown premise is UNKNOWN; stale/revoked premise is invalid; positive SCC/cycle is inadmissible.

Different names/languages do not establish independence if material lineage is shared.

## 20. Rust Assurance Kernel

Rust strengthens the deterministic/model-free core; it does not replace Sergeant or rewrite mature Python orchestration.

Rust may own:

- canonical encodings/IDs;
- exact candidate/RAB/contract validation;
- independent expected contract-instance and obligation derivation;
- set-closure/completeness verification;
- authority DAG/SCC checks;
- capability/qualification validation;
- evidence/Proof World binding checks;
- falsifier-instance closure;
- external-provenance structure;
- UNKNOWN conservation;
- invalidation/currentness;
- Assurance Capsule completeness;
- hardened deterministic/mutation/scanner kernels where justified.

Rust outputs only:

```text
ADMISSIBLE
INADMISSIBLE
```

Rust may not invent project intent, invent ACR contracts, classify business severity, remove findings or issue `PASS / NEEDS WORK / BLOCK`.

Python continues owning Sergeant/Cpl/officers/Judge workflow, reports, learning, adapters, GitHub/IDE/product integration and mature orchestration unless evidence justifies moving a specific deterministic kernel.

## 21. PASS law

Sergeant may issue PASS only when the exact Review World and whole RAB are frozen/authorized; raw and affected mandatory coverage closes; every active mandatory contract is evaluated; applicability has no unresolved mandatory UNKNOWN/out-of-domain/conflict; every applicable contract instance is represented; every applicable instance contributes obligations; every mandatory obligation closes with admissible proof or admissible non-applicability proof; every required authority-bearing collection achieves its required closure grade; every mandatory falsifier instance closes with admitted perturbation evidence; no material UNKNOWN or contradiction remains; required independence closes; Judge admission closes; and Rust returns ADMISSIBLE.

`No bug found` is not PASS.

BLOCK may require one grounded blocker/counterexample. NEEDS WORK includes grounded major defects, mandatory UNKNOWN, missing proof/falsifier/facility/independence, unsupported mandatory domain or contract conflict.

## 22. Assurance Capsule and currentness

A material review emits an immutable content-addressed Assurance Capsule containing at minimum Review World ID, RAB ID, ACR generation, scope/domain, contract-evaluation root, contract-instance root, obligation root, ledger root, admitted findings/UNKNOWNs, evidence roots, closure-witness roots, qualification/facility generations, Rust admissibility, Sergeant verdict and temporal/currentness metadata.

A capsule must commit to both the members and why authority-bearing collections were considered complete.

Hermes may transport/render capsules but never reinterpret them.

Historical PASS remains attached to its world. A stale or scoped PASS must not render as unqualified current repository PASS.

## 23. GitHub vs local capability gradient

GitHub Sergeant remains constrained/read-only and primarily performs repository/diff/PR analysis, architecture/contracts/security/lifecycle review, exact-head proof, CI/evidence reconciliation, deterministic assurance and reviewer comparison.

Local/IDE Sergeant may add owner-approved facilities such as working tree/uncommitted changes, IDE symbols/project graph, local tests/runtime evidence, formal tools, bounded experiments, evidence history and draft remediation assistance.

Richer facilities may strengthen evidence but never change verdict meaning. If GitHub lacks mandatory proof safely, the result is NEEDS WORK/UNKNOWN rather than a weaker PASS. Local writes remain explicit; no silent patching or auto-merge.

## 24. Governed learning

Learning may propose detectors, ACR contracts, invariants, falsifier families, mutation operators, evidence rules, capability/passport improvements and relation types.

Proposal is not authority. Unqualified learning may add scope/concern/hypotheses and trigger stronger assurance; it may not suppress contracts, instances or obligations, prove non-applicability, lower proof requirements, activate ACR, qualify capabilities, rewrite verdicts, use Owner risk acceptance as engineering truth, self-promote or auto-merge.

Qualification/provenance escapes become permanent learning evidence but never auto-promote a correction.

## 25. Self-qualification

Sergeant may review itself, but Sergeant alone is never sufficient qualification evidence that Sergeant is correct. Rust + Sergeant agreement is also insufficient when both depend on one bad trusted specification.

Major assurance generations require frozen qualified ancestor evidence where available, independent Rust, constitutional mutation corpus, historical defect/fix replay, clean controls, hidden externally authored cases, unrelated-language/project transfer, model-disabled qualification, clean clone, repository-only proof, no-private-helper proof and independent hostile review.

Mandatory mutation families include missing-member/undercount, cardinality, ordering, partial-basis, late-member, dropped contract/instance/obligation, authority-premise/material-input/falsifier omission, no-op falsifier, ACR omission and shared incomplete Python/Rust basis.

## 26. Explicit finite trust boundary

The architecture does not claim universal software correctness or omniscient social independence.

The finite TCB may include Owner/Root constitutional authority, canonical ACR specifications, Review World/RAB identity law, cryptographic primitives, Rust Assurance Kernel, small certificate validators and explicit runtime/toolchain assumptions.

Large semantic analyzers, Cpl/officers/models/scanners/fuzzers/external reviewers/learning proposals are not automatically TCB.

A perfect implementation can still prove the wrong proposition if the trusted bounded specification/root is wrong. That is handled through qualification, external truth, revocation, escape analysis and explicit Root trust, not by pretending infinite recursive proof exists.

## 27. Review-evidence classification for this founding architecture

The hostile AI review rounds used to derive this architecture are valuable **internal hostile evidence** but are `NOT_INDEPENDENT` for future Genesis qualification because the review mandate/prompting was controlled from the same project lineage.

They must not be grandfathered into the mandatory Genesis external lane. The eventual Genesis qualification campaign must obtain genuinely independent evidence satisfying the EEPR law and the ACR-audited review-lane cardinality.

## 28. Architecture reopen law

Implementation difficulty alone does not reopen this architecture. A narrow capability may be qualified for a smaller bounded domain and remain UNKNOWN outside it.

Architecture reopens only if implementation/proof evidence establishes an actual contradiction such as:

- a frozen constitutional requirement is unimplementable within its claimed bounded domain; or
- legal compliance with the frozen laws still permits an internal false PASS.

Implementation strategies and roadmap programmes may be regenerated without rewriting the whole constitution when the architecture itself remains sound.

## 29. Current activation status

At this founding freeze stage:

- architecture is approved as implementation authority on the isolated roadmap branch;
- Assurance Evolution mechanisms are not implemented;
- current Sergeant remains canonical normal reviewer;
- Genesis independent external lane has not yet been obtained;
- Genesis qualification/final proof has not started;
- no normal verdict authority transfers until the roadmap's Genesis Exit programme proves and Owner/Root explicitly activates the exact generation.
