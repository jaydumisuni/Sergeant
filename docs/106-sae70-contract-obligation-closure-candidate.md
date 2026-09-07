# SAE-70 — Total Contract / Contract-Instance / Obligation Closure Candidate

Lifecycle: **CANDIDATE**. Authority gain: **none** until a separate exact-head lifecycle closeout is canonically merged.

## Frozen dependency basis

SAE-70 proof requires `SAE-20`, `SAE-50`, and `SAE-60`. Construction began only after all three dependencies were canonically PROVEN:

- `docs/85-sae20-proven-lifecycle-closeout-manifest.json`
- `docs/101-sae50-proven-lifecycle-closeout-manifest.json`
- `docs/105-sae60-proven-lifecycle-closeout-manifest.json`

Construction base: `6d4ecc03782fa72d517e0b111a3757e4b2f65cf0`, the guarded SAE-60 PROVEN merge on `main`.

No dependency is redefined by this candidate.

## Founding total-census rule

`compile_contract_closure(...)` consumes the existing SAE-20 `ACRRegistry`. It does not create a second registry or a parallel applicability authority.

Every mandatory ACR contract is accounted for in the result census:

- `TRUE` applicability → `ACTIVE`; an explicit contract-instance enumeration is required.
- `FALSE` applicability → `PROVEN_NO_MATCH` only when a content-bound proof satisfies that contract's declared negative-applicability closure burden.
- `UNKNOWN` applicability → remains `UNKNOWN`; it cannot be converted to FALSE or silently omitted.
- a missing contract evaluation is represented by the ACR registry as UNKNOWN and therefore blocks exact closure.

A TRUE contract with no instance enumeration is still recorded as ACTIVE, but total closure becomes UNKNOWN. A FALSE contract without sufficient `PROVEN_NO_MATCH` evidence is recorded unresolved and total closure becomes UNKNOWN.

## Contract-instance enumeration

`ContractInstanceEnumeration` binds:

- exact contract ID and generation;
- exact contract content identity;
- exact bound-subject-variable names;
- each canonical subject binding;
- enumeration closure grade;
- source-basis SHA-256 identity;
- content-addressed enumeration identity.

Bindings must cover exactly the ACR contract's declared bound subject variables. Duplicate instances are rejected. A contract-generation or contract-identity substitution is rejected before the enumeration can contribute authority.

Enumeration closure propagates conservatively into the compiled closure grade. A PARTIAL enumeration cannot produce an EXACT total contract closure.

## PROVEN_NO_MATCH

`ProvenNoMatch` is available only for a contract whose ACR applicability evaluation is actually FALSE in the bound applicability context.

The proof binds:

- contract ID, generation and contract identity;
- exact applicability-context identity;
- proof closure grade;
- independent evidence SHA-256 identity;
- content-addressed proof identity.

Its closure must meet the contract's explicit `NegativeApplicabilityBurden`. UNKNOWN applicability cannot be coerced into FALSE through a `ProvenNoMatch` record, and replaying a proof against another contract/context/generation fails closed.

## Conservative-union obligation compiler

The founding SAE-70 generation explicitly forbids first-match, priority, specificity and subsumption weakening.

Every instance of every ACTIVE contract contributes every mandatory obligation declared by that contract. Expected obligations are unioned by:

`(obligation family, exact subject binding)`

This preserves subject multiplicity while allowing overlapping contracts that require the same obligation for the same subject to share one expected-obligation record.

Each expected obligation retains every contributing origin:

- contract ID;
- contract generation;
- contract-instance ID;
- the origin contract's required closure grade.

If overlapping origins demand different closure grades, the compiled requirement uses the strongest requirement and marks the conflict as conservatively resolved. No origin is discarded.

## RED → GREEN evidence

The initial RED contract was committed at:

`4e344e4043cbb00b8cc84ec1c69c113649909c4d`

An import-only RED interface scaffold was then added at:

`664e39c93d5854ff226e179d4d710c8d2922d8b6`

CI run `34133911617` proved the intended RED state from the PR merge result: **11 SAE-70 failures, 1511 passes, 2 historical XFAILs**. The failures were the deliberate missing instance-enumeration / total-closure behavior, not import or fixture errors.

The minimal GREEN implementation generation is:

`60532ea0c33d7d4bd8443ac6434c6c6251836fe7`

On that exact generation GitHub reported success for:

- CI `34134248608` — both ordinary test and full clean-clone proof;
- Main Review `34134248503`;
- Multiplatform Proof `34134248510`, including Python/VS Code/Command Center and JetBrains packaging;
- Review Intelligence Proof `34134248631`;
- Reviewer Comparison Proof `34134248664`;
- Standalone Service Proof `34134248591`;
- Live GitHub Ingestion Proof `34134248617`;
- Final Static Transfer Holdout `34134248586`;
- all triggered model-free transfer / await / auth / campaign workflows.

The clean-clone CI path reached the final gate, independent reviewer module, and mocked live GitHub integration successfully.

## Frozen implementation scope

The accepted production blobs for this candidate generation are:

- `main_review/contract_closure.py` — `c531f57e58dfcc8f26d8c0a8cfe81017868782b3`
- `tests/test_contract_closure.py` — `bfff5367a4c504af7613e6ad882094cd0fb0aa74`

The implementation is intentionally limited to Task 9's founding closure substrate. It does not define Proof World evidence semantics, falsification closure, Rust admissibility, Genesis activation, or normal Sergeant verdict authority.

## Authority boundary

This document freezes a candidate implementation and hostile test surface only.

It does **not** produce:

- `QUALIFIED_CONTRACT_INSTANCE_CLOSURE`;
- `QUALIFIED_EXPECTED_OBLIGATION_COMPILER`;
- Genesis activation;
- ordinary Sergeant engineering-verdict authority;
- automatic proof of SAE-80 or any later node.

A separate SAE-70 lifecycle closeout must qualify the bounded mandatory-contract census, expected contract-instance enumeration and obligation compiler, bind this candidate's exact guarded merge and current-base proof, preserve UNKNOWN, and re-prove dropped-contract / dropped-instance / first-match / provenance-collapse attacks before SAE-70 becomes PROVEN.
