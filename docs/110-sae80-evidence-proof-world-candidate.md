# SAE-80 — Evidence + Proof World Candidate

Lifecycle: **CANDIDATE**. Authority gain: **none** until a separate Task 12 qualification/lifecycle closeout is canonically proven and guarded-merged.

## Frozen dependency basis

The roadmap defines SAE-80 proof dependencies exactly as:

- `SAE-30`
- `SAE-40`
- `SAE-50`
- `SAE-60`
- `SAE-70`

Construction began from canonical SAE-70 PROVEN `main`:

`5ae80680a02562707a82064cc8d5f4e8196ddb8b`

Canonical dependency records:

- `docs/93-sae30-proven-lifecycle-closeout-manifest.json`
- `docs/89-sae40-proven-lifecycle-closeout-manifest.json`
- `docs/101-sae50-proven-lifecycle-closeout-manifest.json`
- `docs/105-sae60-proven-lifecycle-closeout-manifest.json`
- `docs/109-sae70-proven-lifecycle-closeout-manifest.json`

This candidate does not redefine any dependency.

## Candidate authority boundary

SAE-80 Task 11 creates an Evidence + Proof World **candidate substrate only**.

It does **not** produce:

- `QUALIFIED_EVIDENCE_CONTRACT`
- `QUALIFIED_PROOF_WORLD`

Those remain Task 12 outputs. Normal Sergeant verdict authority is unchanged. Genesis remains inactive. No dependent node is auto-proven.

## Exact SAE-70 authority consumption

`compile_proof_world(...)` consumes a real SAE-70 `QualifiedContractClosure`, an exact SAE-70 `ExpectedObligation`, and the exact SAE-20 ACR registry generation already sealed by SAE-70 qualification.

The candidate fails closed unless:

- the qualified closure itself validates;
- the supplied ACR registry canonicalizes and its `registry_id` equals the qualified SAE-70 `registry_id`;
- the expected obligation ID is among SAE-70's qualified expected obligations;
- every obligation provenance instance ID is among SAE-70's qualified contract instances;
- every provenance contract ID/generation exists in the exact qualified registry;
- each provenance edge matches the origin contract's actual mandatory obligation requirement;
- the obligation's strongest required closure, sorted provenance, conservative-conflict flag and content-addressed identity all recompute exactly.

This prevents a caller from replacing an origin contract with a same-named but weaker material-input or proof-class contract.

## Proof World coordinates and coherence

`WorldCoordinates` content-address exactly:

- candidate generation;
- framework generation;
- provider generation;
- dependency-generation map;
- non-negative world epoch.

Evidence is bound to one exact `world_id`. Evidence from another candidate/framework/provider/dependency generation cannot be mixed into the world. This mechanically blocks Frankenworld composition for the founding supported coherence rules:

- `same-candidate-generation`
- `same-framework-generation`
- `same-provider-generation`
- `same-dependency-generation`

Any unknown coherence rule remains unresolved and caps the Proof World at UNKNOWN rather than being silently accepted.

## Evidence classes and proof ceilings

The founding evidence classes are explicit:

- `mechanical` — ceiling `EXACT`;
- `exhaustive-oracle` — ceiling `EXACT`;
- `heuristic` — ceiling `CONSERVATIVE_SUPERSET`.

An evidence record cannot self-label a closure stronger than its proof-class ceiling. In particular, heuristic evidence cannot claim `EXACT`.

Even a globally recognized proof class is rejected if it is not admitted by **every** origin contract contributing to the expected obligation. Admissibility is therefore the conservative intersection of the origin contracts' ACR proof-class declarations.

## Material-input closure

Material-input requirements are derived exclusively from the exact qualified ACR registry, never from a free caller-supplied contract map.

For overlapping obligation origins, required material inputs are a conservative union by family. If multiple origins require the same family at different closure grades, the strongest required closure wins.

A missing required material input produces UNKNOWN. A present but weaker material-input proof lowers the world closure and leaves an explicit blocker.

Material-input proofs are themselves content-addressed by family, closure and basis identity.

## Temporal validity

The founding supported temporal rule is:

`evidence-not-older-than-world`

For an exact founding Proof World, evidence must be observed at the exact world epoch. Stale or generation-misaligned evidence remains visible and caps the world at UNKNOWN. Unknown temporal rules also fail closed.

## Explicit assumptions

Assumptions are first-class, content-addressed records with explicit kinds:

- `VERIFIED`
- `DECLARED`
- `UNRESOLVED`

Assumptions are preserved in the Proof World. Any assumption not mechanically marked `VERIFIED` prevents exact closure; it cannot disappear merely because other evidence looks strong.

Conflicting records under the same assumption ID are rejected.

## Contradiction preservation

Evidence claims are canonical immutable JSON scalars. Claims are retained inside content-addressed evidence records.

If two evidence records assert type-sensitively different values for the same claim, SAE-80 creates an explicit content-addressed `Contradiction` record containing:

- the claim name;
- all distinct values;
- all contributing evidence IDs.

Contradictions are preserved in the Proof World and cap closure at UNKNOWN. They are never averaged, prioritized away or converted into confidence.

## Proof World identity

A `ProofWorld` content-addresses:

- SAE-70 qualified-closure ID;
- exact expected-obligation ID;
- exact world ID;
- resulting closure grade;
- selected material-input proof IDs;
- all evidence IDs;
- all assumption record IDs;
- all contradiction IDs;
- every blocker.

`ProofWorld.validate()` mechanically revalidates every child record and the world identity before returning authority-bearing candidate data.

## RED evidence

The first draft RED generation `2f35adeed41e731868c044018876a026eb59f3f5` failed during pytest collection because the test parametrization instantiated `WorldCoordinates` at module import. That generation is explicitly **not** accepted as behavioral RED evidence.

After correcting only the test construction, an intermediate behavioral RED proved the missing Proof World behavior. Review then found an authority-design gap: material-input/proof-class requirements were accepted from a free contract mapping and were therefore not sealed to SAE-70's qualified registry.

The RED contract was tightened before implementation.

The final accepted RED generation is:

`ad3c7b46a9b4e9db0e7e199ecf8cfde1d323288e`

CI run `34292463099` proved:

- **16 intended SAE-80 failures**;
- **1540 existing passes**;
- **2 historical XFAILs**;
- failures terminated at the deliberate missing Proof World behavior, not test collection or SAE-70 integration.

## GREEN implementation evidence

The minimal accepted GREEN implementation generation is:

`d2e3737b2300d42ba1bce434a65c71e44461c7f7`

with tree:

`b5a6c4f0bbfcd8c5d41981f03ed6caae753ae5c3`

Frozen accepted implementation blobs:

- `main_review/proof_world.py` — `ca73f85388d1d9f73a7240f78e26da7f47644484`
- `tests/test_proof_world.py` — `d21bc2a24977044306262ac69ebd23f9fb382530`

On that exact GREEN head GitHub proved:

- CI `34292776687` — success, both ordinary test and full clean-clone jobs;
- ordinary suite: **1556 passed, 2 historical XFAILs**;
- clean-clone proof reached final gate, end-to-end review, independent reviewer and mocked live GitHub integration;
- Main Review `34292776788` — success;
- Multiplatform Proof `34292776659` — success, including Python/VS Code/Command Center and JetBrains packaging;
- Review Intelligence Proof `34292776704` — success;
- Reviewer Comparison Proof `34292776798` — success;
- Standalone Service Proof `34292776660` — success;
- Live GitHub Ingestion Proof `34292776633` — success;
- Final Static Transfer Holdout `34292776640` — success;
- all completed model-free transfer/await/auth/campaign lanes except the known stale external Auth Transfer 7 fixture.

`Model-Free Core Auth Transfer 7` run `34292776690` failed before Sergeant execution because its historical third-party fixture repository `jraversbcn21/PlayQAcademy` returns `Repository not found`. The same external disappearance was independently established during SAE-70 closeout. This failure is preserved as infrastructure drift and is not represented as SAE-80 proof or success.

## Hostile candidate surface

The frozen test surface attacks at least:

- wrong candidate generation;
- wrong framework generation;
- wrong provider generation;
- wrong dependency generation;
- Frankenworld evidence mixing;
- omitted material input;
- overlapping-origin material-input union loss;
- qualified-registry requirement laundering;
- heuristic evidence claiming EXACT;
- proof classes not admitted by origin contracts;
- stale evidence;
- unresolved assumptions;
- hidden contradictory claims;
- forged expected-obligation identity;
- forged Proof World identity.

## What Task 12 must still prove

This candidate demonstrates that the substrate can represent and mechanically conserve the bounded Evidence + Proof World invariants above. It is not yet qualified authority.

Task 12 must independently qualify the evidence contract and Proof World semantics on the exact frozen candidate generation, re-attack replay/coherence/material-input/assumption/contradiction/proof-ceiling boundaries, freeze the lifecycle closeout, receive exact-head hostile review and repository proof, and only then guarded-merge:

- `QUALIFIED_EVIDENCE_CONTRACT`
- `QUALIFIED_PROOF_WORLD`
