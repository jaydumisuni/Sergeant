# SPIKE-ID — PROVEN feasibility lifecycle closeout

Date: 2026-09-02

Status: **PROVEN FEASIBILITY; SSHSIG IS NOT SAE-30 QUALIFICATION AUTHORITY**.

Authority gain: **none**.

This record closes the bounded `SPIKE-ID — Identity / authenticated provenance feasibility` roadmap node. It proves that a practical initial identity/authentication mechanism and falsifiable separation/currentness fixtures exist. It does **not** implement `SAE-30`, create a real Qualification Authority Registry, create or store a real issuer private key, issue a real Qualification Attestation, establish external independence, or change any current Sergeant verdict path.

## Authority chain

- Founding architecture: `docs/58-sergeant-assurance-evolution-founding-architecture.md`.
- Frozen roadmap: `docs/59-sergeant-assurance-evolution-roadmap.md`.
- Proven root: `docs/66-sae00-proven-lifecycle-closeout.md` / `docs/67-sae00-proven-lifecycle-closeout-manifest.json`.
- SAE-00 proven closeout merge: `5d1a3fe8cf4a1ba23c962eceb70fbd3a553cf910`.
- Historical isolated SPIKE-ID candidate head: `a703f009bd2ecd7e85aa01f259c01936d6114ec8`.
- Current reconciled SPIKE-ID authority: `docs/70-spike-id-identity-provenance-feasibility.md` / `docs/71-spike-id-feasibility-manifest.json`.
- Exact reviewed reconciled candidate head: `7ccaff5b32f09e3db38d7710f99fb38ac5bf616b`.
- Construction/reconciliation PR: `#174`.

The old isolated candidate used `docs/64`/`docs/65`; those numbers later became canonical SPIKE-EXT authority. The current generation therefore preserves the old head and blob identities as historical provenance while using `docs/70`/`docs/71` for current SPIKE-ID authority.

## Frozen charter and result

The roadmap requires SPIKE-ID to produce:

1. identity/authentication option analysis;
2. a selected initial mechanism or explicit no-safe-mechanism disposition;
3. key/credential custody threat model;
4. replay/revocation fixtures;
5. negative proof that candidate-controlled automation cannot acquire issuer authority.

All five bounded outputs are present and mechanically bound by `docs/71`.

The selected **initial feasibility mechanism** is OpenSSH SSHSIG with a dedicated ed25519 qualification-issuer key shape and verifier-trusted issuer registry state. The verifier trust state binds:

- authenticated issuer identity;
- public key;
- SSHSIG namespace;
- issuer generation.

The signed payload may repeat issuer identity/generation for coherence, but cannot choose the authenticated authority generation.

## Hostile findings dispositioned before closeout

The reconciled candidate was not accepted merely because the historical fixtures had passed. Current review found and corrected material boundary defects:

- exact expiry was made fail-closed: `now >= expires_at` is expired;
- future-issued attestations are not yet valid;
- signed `issuer_identity` must match the identity actually authenticated by SSHSIG verification;
- issuer-generation revocation is derived from verifier-trusted registry state rather than the payload's self-declared generation;
- a compromised generation-1 key claiming generation 2 is rejected as both generation-mismatched and still revoked;
- the roadmap dependency proof was corrected to the frozen inline dependency representation;
- historical SAE-00 candidate test-count evidence was separated from current-tree test-count semantics without rewriting the hash-bound historical generation;
- SAE-00 closeout lineage proof was made safe for both full-history and intentional depth-1 checkouts.

Both P1 review threads on PR #174 were dispositioned and resolved only after fresh exact-head execution.

## Execution confirmation

Fresh GitHub execution on exact reviewed head `7ccaff5b32f09e3db38d7710f99fb38ac5bf616b` confirmed:

- full pytest suite: **1083 passed, 1 deliberate historical XFAIL, 0 failed**;
- the XFAIL is only the immutable SAE-00 candidate-generation assertion that its own historical exact tree contained 1040 tests; it is no longer interpreted as an eternal invariant over later roadmap generations;
- clean-clone proof passed its test step and all Sergeant CLI gates, including scan, evidence, review, app bridge, IDE Bench contract, battle fixtures, verification standard, final gate, end-to-end proof suite, independent reviewer module and mocked live GitHub integration.

This execution is supporting confirmation, not a replacement for the frozen authority contracts. GitHub Actions availability is not itself authority.

## What is actually proven

SPIKE-ID proves only that the selected SSHSIG-based shape is a practical bounded starting mechanism with concrete negative controls:

- an issuer-signed current attestation can authenticate successfully;
- tampered bytes fail cryptographic verification;
- candidate-held keys do not acquire issuer authority merely by signing;
- a candidate-supplied trust file is not authoritative to a verifier that uses separately trusted registry state;
- exact-expiry, future issuance and replay are rejected;
- individual attestation revocation works in the bounded fixture;
- authenticated issuer-generation revocation works in the bounded fixture;
- a compromised key cannot evade generation revocation by self-relabeling its payload;
- signature authenticity remains distinct from external independence and from qualification validity.

## Residual SAE-30 obligations

The following remain explicitly unresolved and are **not** weakened by this closeout:

- production custody/distribution for the trusted issuer registry and revocation state;
- a real Qualification Authority Registry;
- real issuer key creation, custody, rotation, loss recovery and succession;
- full Qualification Attestation schema and subject/domain/generation/ceiling matching;
- malformed/timezone-naive timestamp schema validation;
- public transparency/currentness if later required;
- EEPR external-source identity/control-lineage/independence semantics;
- real qualification evidence roots and Judge-admitted evidence binding;
- qualification issuer authorization, suspension and revocation semantics.

If `SAE-30` cannot close its own obligations, it cannot become PROVEN regardless of this spike's result.

## Bootstrap authority boundary

The general Qualification Authority substrate is itself created by `SAE-30`, while `SAE-30` depends on PROVEN `SPIKE-ID` and PROVEN `SPIKE-EXT`. Requiring the not-yet-created SAE-30 qualification machinery to qualify its own prerequisite spike would be circular.

Therefore this bounded pre-SAE-30 lifecycle closeout uses only:

- the already-PROVEN SAE-00 `ROADMAP_EXECUTION_AUTHORITY`; and
- the founding architecture's permitted Owner/Root constitutional TCB.

That bootstrap may determine only whether this bounded feasibility charter was satisfied. It cannot issue a Qualification Attestation, qualify another roadmap node, create external independence, satisfy Genesis, turn Owner risk acceptance into engineering PASS, or activate a partial Assurance Evolution generation.

## Dependency effect

After this closeout is canonical, the roadmap dependency `SPIKE-ID` is resolved for dependency accounting.

Together with the already-PROVEN `SPIKE-EXT`, this means `SAE-30` has both feasibility-spike prerequisites available. It does **not** qualify or prove `SAE-30`; SAE-30 must still build and prove its complete authority substrate.

`SPIKE-SEM`, `SAE-10` and `SAE-20` remain independent frontier nodes whose proof requires SAE-00 and which must earn their own lifecycle closure.

## Recovery rule

A zero-context executor must treat:

- historical head `a703f009bd2ecd7e85aa01f259c01936d6114ec8` as the isolated pre-SAE-00 SPIKE-ID candidate;
- `docs/70` / `docs/71` and reviewed head `7ccaff5b32f09e3db38d7710f99fb38ac5bf616b` as the reconciled reviewed candidate generation;
- this document plus `docs/73-spike-id-proven-lifecycle-closeout-manifest.json` as the later lifecycle closeout authority.

Live GitHub remains authoritative for mutable repository/PR state. Historical artifact identities must not be rewritten to make later authority appear to have existed earlier.
