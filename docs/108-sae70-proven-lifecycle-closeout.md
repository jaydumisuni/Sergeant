# SAE-70 — Total Contract / Contract-Instance / Obligation Closure — PROVEN Lifecycle Closeout

Status: **PROVEN**, conditional on this exact closeout generation itself receiving exact-head repository proof, hostile-review closure, and guarded canonical merge.

## Authority advanced by this closeout

This closeout advances only the frozen SAE-70 candidate and its separately hardened qualification protocol.

Once this closeout generation is canonically guarded-merged, SAE-70 produces exactly:

- `QUALIFIED_CONTRACT_INSTANCE_CLOSURE`
- `QUALIFIED_EXPECTED_OBLIGATION_COMPILER`

No other authority is created.

Normal Sergeant verdict authority remains unchanged. Genesis remains inactive. No dependent node is auto-proven, and no partial Assurance Evolution generation may activate.

## Proven dependency basis

The frozen SAE-70 dependency law is unchanged from the candidate:

- `SAE-20` — PROVEN Assurance Contract Registry authority;
- `SAE-50` — PROVEN total set-valued closure core;
- `SAE-60` — PROVEN bounded semantic capability protocol.

Canonical dependency records:

- `docs/85-sae20-proven-lifecycle-closeout-manifest.json`
- `docs/101-sae50-proven-lifecycle-closeout-manifest.json`
- `docs/105-sae60-proven-lifecycle-closeout-manifest.json`

## Frozen candidate generation

The historical SAE-70 candidate was frozen at:

`9f6f5b9800e0143f4614a904b780f3767305eb12`

with tree:

`c2c8a2482b5b8ffbbeb1e8f9f9f4d3bcb39ccef4`

Candidate PR: `#196`.

The candidate was guarded-merged as:

`281b97c94fb77693d9c9df89b6a4ef67896185c0`

with parents:

1. `6d4ecc03782fa72d517e0b111a3757e4b2f65cf0`
2. `9f6f5b9800e0143f4614a904b780f3767305eb12`

and merge tree:

`c2c8a2482b5b8ffbbeb1e8f9f9f4d3bcb39ccef4`

The guarded merge advanced only the candidate. It explicitly did **not** grant either SAE-70 qualification authority.

Historical candidate content remains immutable:

- `docs/106-sae70-contract-obligation-closure-candidate.md` blob `04d453a619337b475ce5c7d2e34aa9933372fd54`
- `docs/107-sae70-contract-obligation-closure-candidate-manifest.json` blob `19976a9e39b6277ac82ce164b486bdc5507076ed`
- `main_review/contract_closure.py` blob `c531f57e58dfcc8f26d8c0a8cfe81017868782b3`
- `tests/test_contract_closure.py` blob `bfff5367a4c504af7613e6ad882094cd0fb0aa74`

This closeout does not rewrite those historical candidate artifacts.

## Qualification hardening discovery

Task 10 deliberately re-attacked the candidate as an authority-bearing result rather than assuming a green candidate compiler was sufficient qualification.

The RED qualification generation was:

`f85613d003ae7803311eeda4afc3fbbe364f46d4`

CI run `34135393353` proved the intended missing boundary:

- **10** SAE-70 qualification failures;
- **1523** existing passes;
- **2** historical XFAILs;
- every new failure was the absent exact-result qualification protocol, not a candidate-compiler regression.

The discovery was material: a `ContractClosureResult` is later consumed as authority, so Task 10 requires a distinct qualification boundary that does not trust a supplied result merely because it carries plausible IDs.

## Separate qualification protocol

The candidate compiler remains historical and unchanged. Qualification authority is isolated in:

`main_review/contract_closure_protocol.py`

The accepted hardening generation is:

`8a25dbd69e9498b38c6f3f137e8140313a04a335`

with tree:

`b2828cad58cb8bbc034582798f7ba8992208e381`

Frozen hardening blobs:

- `main_review/contract_closure_protocol.py` — `e55d2616cf831f0a96205e8e69c1523ab4e77c2e`
- `tests/test_sae70_qualification_campaign.py` — `3a395bc4771d8107dd4ed513f4fb44269ab3ad9f`

The protocol generation is `sae70-qualification-v1`.

Qualification is not trust-on-ID. `qualify_contract_closure(...)` must:

1. receive the exact ACR registry, applicability contexts, contract-instance enumerations, `PROVEN_NO_MATCH` proofs, and candidate result;
2. canonically recompute the total closure from those exact source inputs;
3. require full equality between the supplied result and canonical recomputation;
4. require `EXACT` closure with no blockers;
5. bind the registry ID, exact source-input-set ID, result ID, every expected contract-instance ID, and every expected-obligation ID;
6. issue a content-addressed qualification record carrying exactly the two SAE-70 protocol IDs;
7. permit the issued qualification record itself to be mechanically revalidated.

## Hostile qualification campaign

The qualification campaign proves that authority does not survive:

- dropped mandatory contract census entries;
- dropped contract instances;
- UNKNOWN applicability laundering into FALSE authority;
- first-match weakening of overlapping obligations;
- collapsed obligation provenance;
- PARTIAL instance enumeration presented as exact authority;
- historical result replay against a different registry generation;
- forged candidate-result identity;
- forged qualification identity.

The campaign also proves that qualification itself does not activate Genesis or normal Sergeant verdict authority.

## Exact-head hardening execution proof

On exact hardening head `8a25dbd69e9498b38c6f3f137e8140313a04a335`, GitHub proved:

- CI `34135754332` — success, including both ordinary tests and the full clean-clone proof chain;
- Main Review `34135754341` — success;
- Multiplatform Proof `34135754385` — success, including Python/VS Code/Command Center and JetBrains packaging;
- Review Intelligence Proof `34135754371` — success;
- Reviewer Comparison Proof `34135754345` — success;
- Standalone Service Proof `34135754411` — success;
- Live GitHub Ingestion Proof `34135754259` — success;
- Final Static Transfer Holdout `34135754195` — success;
- every triggered model-free transfer, await, auth, learned-closure and campaign workflow — success.

The clean-clone proof reached the final gate, independent reviewer module, and mocked live GitHub integration successfully.

## Qualified scope

The qualified SAE-70 authority is bounded to:

- total census of mandatory contracts from the exact SAE-20 ACR registry generation;
- three-valued applicability with UNKNOWN conservation;
- FALSE only through valid `PROVEN_NO_MATCH` burden;
- explicit contract-instance enumeration with exact subject-variable bindings;
- closure-grade propagation and EXACT-only qualification;
- conservative-union expected-obligation compilation;
- strongest-required-closure conflict handling;
- preservation of every contributing contract and contract-instance provenance edge;
- exact-generation replay protection through canonical recomputation and source-input identity;
- content-addressed qualification output.

## Authority boundary

This closeout does **not**:

- grant normal Sergeant PASS/FAIL/verdict authority;
- activate Genesis;
- qualify Proof World or evidence semantics;
- qualify mandatory falsification;
- qualify the Rust assurance kernel;
- prove or activate SAE-80 or any later node;
- permit first-match, priority, specificity or subsumption weakening;
- convert UNKNOWN/PARTIAL closure into exact authority;
- authorize a self-written or mutated `ContractClosureResult` without canonical recomputation.

SAE-80 may consume SAE-70 only after this exact closeout generation is itself proven, hostile-review clean, and guarded-merged.
