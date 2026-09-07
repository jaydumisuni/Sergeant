# SAE-30 — Qualification, Provenance, Genesis and Owner-Authority Substrate Candidate

Lifecycle: **CANDIDATE**.

Construction base: `535699dc5952f5309eaa843098b21457439af706`.

Initial RED `67d80d29deb197fed18d0542838535d3a009c5ad` proved the entire SAE-30 substrate was absent: nine new contract tests failed only because the qualification, EEPR and owner-risk modules did not exist.

The first GREEN generation exposed a specification-coverage gap during Review: the attestation did not yet bind independence/lineage/authenticated-provenance authority. Second RED `12e2ddc3c883b6cdcb36aaac32a226b80a4f43fb` then failed exactly three new tests on those missing fields. Current hardened implementation generation: `073adfc69d65c9db7891bb1f3ed76781b8ed1b62`.

## Candidate contract

- trusted Qualification Authority Registry generation selects issuer authority;
- authenticated issuer identity/key/namespace/generation must match verifier-trusted authorization;
- attestation binds exact subject, artifact family/domain/generation, ACR generation, qualification-protocol generation, evidence root, proof/closure ceiling, independence state, qualification lineage and authenticated provenance;
- issuer authorization constrains artifact/domain/proof/closure/independence ceilings;
- future-issued, exact-expiry, stale/replayed, revoked, suspended, spoofed and candidate-controlled issuer paths fail closed;
- qualification is derived state, never candidate self-declaration;
- EEPR records source/principal/org/class/generation and explicit control-lineage facts; `INDEPENDENT`, `NOT_INDEPENDENT`, and `UNKNOWN_INDEPENDENCE` are derived rather than self-labeled;
- external-review census counts only independently established records and source classes;
- EngineeringVerdictRecord and BusinessRiskDecisionRecord are structurally disjoint, so Owner risk acceptance cannot become PASS, evidence or qualification;
- Genesis packages remain `GENESIS_PROVISIONAL`; only exact SAE-170 exit authority with complete qualifications, external-review census and founding final proof can authorize a one-time activation class.

## Authority boundary

This is a candidate implementation only. It does not create normal Sergeant verdict authority, does not satisfy a real Genesis external lane by itself, does not activate a partial Assurance Evolution generation and does not auto-prove downstream nodes. A separate SAE-30 qualification campaign and lifecycle-closeout generation is required after guarded candidate merge.
