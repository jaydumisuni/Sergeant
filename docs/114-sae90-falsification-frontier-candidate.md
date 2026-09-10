# SAE-90 — Mandatory Falsification / Challenger Evolution Candidate

## Lifecycle

This record defines the SAE-90 candidate construction only. It creates no new Sergeant verdict authority and does not activate `QUALIFIED_FALSIFICATION_FRONTIER`.

SAE-90 proof requires SAE-70 and SAE-80. The construction is based on the exact reconciled SAE-80 closeout head `013171c8773f1b396e859c96eb387d9d0f228d26`, but SAE-80 is not represented here as PROVEN while live GitHub currentness/check evidence is unavailable. Qualification and lifecycle promotion therefore remain fail-closed.

## Candidate construction

The candidate compiles mandatory contract falsifier families into exact falsifier instances. Each instance is content-addressed over the qualified SAE-80 Proof World identity, exact SAE-70 expected-obligation identity, exact contract and contract generation, exact contract-instance provenance, falsifier family, parameter-domain identity, and canonical parameter assignment.

Parameter domains must be closed before exhaustive identity can be claimed. Open domains remain UNKNOWN. Counter-world evidence is bound to one exact falsifier instance and rejects no-op mutation. Statistical or open-search evidence may be preserved as evidence but cannot claim exhaustive bounded closure.

An EXACT frontier requires every mandatory falsifier instance to have bounded-exhaustive evidence whose perturbation is non-no-op and whose result survives the falsifier. Missing instances, UNKNOWN results, successful falsification, open domains, or non-exhaustive search keep the frontier UNKNOWN.

## Hostile proof obligations covered

- Family-name-only completion cannot satisfy the instance frontier.
- One parameter instance cannot satisfy another instance.
- Partial/open parameter domains remain UNKNOWN.
- No-op mutations are inadmissible.
- Statistical/random search cannot self-label exhaustive closure.
- Forged falsifier-instance identities are rejected.
- A registry from another generation cannot be substituted for the qualified Proof World registry.
- A forged or different SAE-70 expected-obligation identity cannot be substituted.

## Evidence at freeze

Accepted production generation: `f6af7478d87ab3bb55b592154e28d6d45f42b02d`.

Focused SAE-90 campaign: 9 passed. Full repository regression: 1582 passed, 2 historical XFAIL. `git diff --check` passed before freeze. Independent last-PROVEN Sergeant review from SAE-70 returned APPROVE at confidence 0.88 with no required actions. Its call-graph and nested-iteration signals remained advisory and were not admitted as blockers.

## Authority boundary

This candidate produces no qualified lifecycle token. `QUALIFIED_FALSIFICATION_FRONTIER` may only be issued by a later qualification/closeout generation after exact live SAE-80 PROVEN authority is recovered and all SAE-90 proof gates are satisfied.
