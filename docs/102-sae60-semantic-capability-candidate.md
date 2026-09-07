# SAE-60 — Semantic Capability Qualification Candidate

Lifecycle: **CANDIDATE**. Authority gain: **none** until a separate exact-head lifecycle closeout is canonically merged.

## Frozen dependency basis

SAE-60 proof requires `SAE-20`, `SAE-30`, `SAE-50`, and `SPIKE-SEM`. The branch was constructed only after all four dependencies were already canonically PROVEN:

- `docs/85-sae20-proven-lifecycle-closeout-manifest.json`
- `docs/93-sae30-proven-lifecycle-closeout-manifest.json`
- `docs/101-sae50-proven-lifecycle-closeout-manifest.json`
- `docs/77-spike-sem-proven-lifecycle-closeout-manifest.json`

No dependency is redefined by this candidate.

## Deliberately narrow initial domain

This candidate qualifies no general Python semantics. Its only candidate exact family is:

`python.bounded-literal-dispatch.v1`

A positive `EXACT` result is possible only for calls through a single-assignment, module-level, literal-string-key dictionary whose values resolve to unique undecorated top-level functions and whose table and callable identities remain closed. The call must use a literal string key present in that exact table.

The candidate fails closed to `UNKNOWN` for dynamic keys, table mutation, alias/argument/return escape, lexical shadowing, lambda/class/comprehension scope, target decoration or rebinding, duplicate or non-literal keys, unsupported parser/framework/domain generations, malformed or forged passports, parse failure, source/AST/table/entry resource exhaustion, absent literal keys, and every construct outside the bounded family.

This is intentionally narrower than the seven candidate families measured by SPIKE-SEM. Coverage is not assurance.

## Capability Passport

`CapabilityPassport` binds:

- capability name;
- exact bounded-domain identity, generation, hash and resource dimensions;
- artifact generation;
- parser generation;
- framework generation;
- qualification-protocol generation;
- proof ceiling;
- closure ceiling;
- implementation lineage;
- parser lineage;
- framework lineage;
- common-mode lineage;
- control lineage.

The passport is content-addressed. Mutating a frozen dataclass instance without canonically reissuing the passport invalidates its identity and returns `UNKNOWN`. A canonically reissued passport for an unsupported parser or domain generation also returns `UNKNOWN` through the explicit generation/domain gate.

The candidate passport remains `CANDIDATE`; the analyzer cannot self-issue qualified authority.

## Independent oracle and holdouts

Ground truth is separately authored in `tests/semantic_oracle/bounded_call_oracle.py`. It does not import the production analyzer and does not parse source. Expected relations are authored independently and bound to exact source SHA-256 digests.

Three distinct corpora are frozen:

1. training fixture — Sergeant-like command routing;
2. hidden holdout — release routing with different names and declaration order;
3. transfer fixture — incident-response routing with a new table and new target names.

The oracle implementation lineage is different from the production implementation lineage. Deletion/undercount mutations of candidate output fail exact oracle comparison.

## Hostile qualification surface

`tests/test_capability_qualification.py` freezes attacks for:

- independent training, hidden-holdout and transfer agreement;
- relation deletion/undercount;
- dynamic-key ambiguity;
- table mutation and read/argument/return escape;
- function, lambda, comprehension and class-scope shadowing;
- decorated or rebound callable identity;
- malformed/forged passport identity;
- wrong parser generation;
- wrong domain generation;
- proof-ceiling and domain-generation identity drift;
- parse failure;
- source and AST resource exhaustion.

Unsupported or unclosed cases are not converted to PARTIAL confidence or an inferred target. They remain `UNKNOWN`.

## Accepted production generation

The review-hardened production generation is:

`dd96affea3a3d1072b8cae176ac15c2725a68ca4`

On that exact head GitHub reported success for CI run `34116706898`, Main Review `34116706843`, Multiplatform Proof `34116706911`, Review Intelligence Proof `34116706951`, Reviewer Comparison Proof `34116706886`, Standalone Service Proof `34116706994`, Live GitHub Ingestion Proof `34116706933`, Final Static Transfer Holdout `34116706897`, and all triggered model-free transfer/await/auth/campaign workflows.

PR #194 had no inline hostile-review threads at candidate-freeze entry.

## Authority boundary

This document freezes a candidate implementation and qualification corpus only. It does not produce `QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL`, does not qualify `python.bounded-literal-dispatch.v1`, does not activate any ACR domain for normal Sergeant verdict authority, does not activate Genesis, does not change SAE-170 exit authority, and does not auto-prove SAE-70 or any later node.

If the separate lifecycle closeout succeeds, SAE-60 may produce `QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL` together with the first bounded qualified semantic capability, limited to the exact `python.bounded-literal-dispatch.v1` domain and frozen passport ceiling. No broader semantic capability is implied.

A separate lifecycle closeout must bind the exact reviewed candidate head, guarded canonical merge, current-base integration proof, frozen content blobs, qualification/holdout evidence, and authority boundary before SAE-60 becomes PROVEN.
