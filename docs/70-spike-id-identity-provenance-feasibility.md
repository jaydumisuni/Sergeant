# SPIKE-ID — Identity / Authenticated Provenance Feasibility

Date: 2026-09-02

Status: **RECONCILED CANDIDATE, REVIEWED HISTORICAL EVIDENCE PRESERVED, PROOF FIXTURES ATTACHED**.

Authority gain: **none**.

This is the current-main authority record for the bounded `SPIKE-ID` node in `docs/59-sergeant-assurance-evolution-roadmap.md`. It does not implement `SAE-30`, does not create a Qualification Authority Registry, does not issue a real Qualification Attestation, and does not change any current Sergeant verdict path.

## 1. Recovery and provenance

The original isolated SPIKE-ID construction is preserved at exact GitHub head:

`a703f009bd2ecd7e85aa01f259c01936d6114ec8`

That candidate was built from `9976e43f0d4d318ee4ffd2c4389bd87f520a7757` while SAE-00 was still open. It contained the original `docs/64`/`docs/65` SPIKE-ID records plus the runnable `tests/spike_id/` fixture set.

Those document numbers later became canonical SPIKE-EXT authority, so the old SPIKE-ID documents cannot be copied into `main` under their original paths. This reconciliation therefore:

- preserves the old head and old document/blob identities as historical provenance in `docs/71-spike-id-feasibility-manifest.json`;
- moves the current SPIKE-ID authority record to `docs/70`/`docs/71`;
- transplants the real `tests/spike_id/` fixture set onto current-main ancestry;
- records corrections made during current review instead of pretending the old fixture bytes were unchanged.

SAE-00 is now PROVEN through `docs/66`/`docs/67`. SPIKE-ID's sole roadmap proof dependency is therefore available for later lifecycle closeout once this reconciled candidate earns its own review gate.

## 2. Frozen charter

SPIKE-ID must establish a practical bounded mechanism for:

- Qualification Authority identities;
- Qualification Attestations;
- EEPR source authentication;
- revocation/currentness;
- candidate-automation credential separation.

It must produce:

1. identity/authentication option analysis;
2. a selected initial mechanism or explicit no-safe-mechanism disposition;
3. a key/credential custody threat model;
4. replay/revocation fixtures;
5. negative proof that candidate-controlled automation cannot acquire issuer authority.

The selected disposition is **positive feasibility with explicit residual gaps**, not production qualification.

## 3. Option analysis

### 3.1 GPG signatures

GPG can provide strong asymmetric signatures and revocation certificates with low infrastructure cost. It was not selected initially because keyring/agent/passphrase-cache behavior adds custody surfaces that are unnecessary for this bounded spike. It remains technically viable.

### 3.2 GitHub OIDC / workload identity

OIDC is appropriate for authenticating a workflow to an external relying party, but a candidate repository's own workflow identity is the wrong trust shape for Qualification Authority issuance. The roadmap requires candidate-controlled operational principals to remain distinct from qualification issuers. A candidate-triggerable CI identity therefore cannot be the issuer merely because its OIDC claims are authentic.

This distinction is reinforced by Sergeant's prior rejected Oracle OIDC learning proposal: exact workflow identifiers and broad repository trust were specifically insufficient as a generalized authority rule.

### 3.3 Sigstore / cosign keyless

Sigstore offers strong signing plus public transparency, but introduces external CA/log/OIDC infrastructure and network dependence. Its transparency properties may be valuable later if SAE-30 requires independently visible issuance-time evidence. It is not required to prove initial mechanism feasibility.

### 3.4 Owner-held dedicated asymmetric keypair using SSHSIG — selected

The selected initial mechanism is OpenSSH SSHSIG using a **dedicated ed25519 qualification-issuer key**:

- sign: `ssh-keygen -Y sign`;
- verify: `ssh-keygen -Y verify`;
- domain separation namespace: `sergeant-qualification-attestation-v1`;
- verifier trust source: an `allowed_signers`-shaped registry binding issuer identity to public key and namespace;
- signed issuer coherence: payload `issuer_identity` must equal the identity the verifier actually authenticated;
- revocation units: `attestation_id` and `issuer_generation`;
- issue-time currentness: a future `issued_at` is not yet valid;
- expiry currentness: `expires_at` is an exclusive upper bound, so equality is already expired;
- replay protection: verifier-side consumed `attestation_id` state.

Why selected: it uses audited OpenSSH primitives, adds no Python cryptography dependency, has no mandatory third-party service, and makes candidate/issuer credential separation concrete: candidate automation may possess its own key, but the verifier trusts only a separately-custodied issuer key.

This does **not** mean an SSH signature is qualification. The founding architecture is explicit that authentic attestation is not automatically valid qualification. SAE-30 must later add authorized issuer/domain/generation binding, qualification evidence, proof ceilings, closure ceilings, revocation/currentness authority, and Judge-admitted evidence-root semantics.

## 4. Custody threat model

### 4.1 Issuer private key

The real issuer key must be dedicated to qualification issuance and held outside candidate-controlled repository, CI, build/runtime, generated-helper, and secret-store write paths. It must not be reused as a developer login key or ordinary deploy credential.

The current fixtures use passphrase-less throwaway keys under pytest temporary directories only. That is test convenience, not a production custody recommendation.

### 4.2 Candidate compromise

Compromise of candidate automation must expose only candidate-held credentials. It must not expose the qualification-issuer private key or give the candidate write authority over the verifier's trusted issuer registry/revocation state.

The negative fixture proves a candidate key cannot verify as the issuer against the real issuer-only registry, including when the candidate:

- claims the issuer identity string;
- signs honestly under its own identity;
- ships a self-serving replacement registry that trusts itself.

The third case is deliberately revealing: candidate verification succeeds against the candidate's forged registry, proving registry custody—not cryptographic syntax—is the load-bearing authority boundary.

### 4.3 Key compromise

If an issuer key generation is suspected compromised, revoking that `issuer_generation` must invalidate all attestations issued by that generation. Individual `attestation_id` revocation remains available for narrower correction.

### 4.4 Key loss and succession

A safe key-loss/rotation/succession protocol is **not solved by this spike**. SAE-30 must define registry generation, replacement authority, historical invalidation behavior, and recovery without allowing a candidate to self-enroll a replacement issuer.

### 4.5 Registry and revocation distribution

This is the largest remaining operational gap. The fixtures prove verifier behavior given a trustworthy registry and revocation set; they do not yet design the owner-controlled distribution channel that makes those inputs non-candidate-writable in production.

## 5. Mechanical fixture set

`tests/spike_id/` is deliberately outside `main_review/`: the code is feasibility evidence, not production capability.

- `qualification_attestation_fixture.py` — reference SSHSIG signing, verification, authenticated-issuer coherence, and application-layer disposition.
- `conftest.py` — generates independent issuer and candidate keypairs and an issuer-only verifier registry.
- `test_valid_attestation_verifies.py` — positive control, payload tamper rejection, and payload/authenticated-issuer mismatch rejection.
- `test_replay_and_staleness_rejected.py` — stale, exact-expiry, future-issued, and replay rejection.
- `test_revoked_attestation_rejected.py` — individual attestation and whole issuer-generation revocation.
- `test_negative_proof_candidate_cannot_sign_as_issuer.py` — required candidate non-authority proof.

Current static review made four explicit corrections relative to the historical fixture generation:

1. **Exact expiry now fails closed.** Historical code used `now > expires_at`, which admitted an attestation at the exact expiry instant. Current code uses `now >= expires_at` and carries an equality falsifier.
2. **Future-issued attestations are rejected.** `issued_at` is now checked; an attestation whose issue time is later than verifier time is `not_yet_valid`.
3. **Signed issuer identity is coherent with the authenticated principal.** A cryptographically valid issuer signature over a payload that names some other `issuer_identity` is rejected as `identity_mismatch`.
4. **Negative-proof subject digests were normalized.** Historical illustrative values used malformed repeated `sha256:` prefixes; current fixtures use ordinary `sha256:` plus 64 hex characters. This is fixture hygiene, not a change to the authority invariant.

The historical candidate recorded a real local fixture result of **10 passed** and real direct `ssh-keygen -Y sign/-Y verify` confirmation. Those are historical execution results, not claimed as fresh execution in this reconciliation session. The reconciled suite contains **13 test cases by construction** after the three new falsifiers; the manifest proof executes them when a runtime with OpenSSH is available, but this record does not fabricate a fresh run in the current GitHub-only workspace.

## 6. Negative-proof boundary

The core invariant under test is:

```text
candidate-controlled operational principal != qualification issuer principal
```

The mechanism succeeds only if the verifier's authority inputs remain outside candidate control. A candidate can generate arbitrary keys and signatures; that does not grant authority because its key is absent from the trusted issuer registry. If the candidate can replace the registry used by the verifier, the mechanism fails by design—exactly why registry custody is an explicit SAE-30 obligation rather than hidden behind the cryptographic primitive.

## 7. EEPR compatibility

SSHSIG can authenticate an external evidence submitter's bytes and declared identity, but **signature authenticity alone does not establish independence**. SPIKE-EXT's `INDEPENDENT / NOT_INDEPENDENT / UNKNOWN_INDEPENDENCE` control-lineage criteria remain separately required. This spike therefore addresses the authentication primitive, not the externality/independence disposition.

## 8. Residual gaps

The selected mechanism remains bounded by unresolved items that belong to SAE-30 qualification rather than this feasibility probe:

1. registry and revocation-list distribution custody;
2. no public transparency log;
3. key-holder loss/rotation/succession protocol;
4. fixture payload is only a subset of the full SAE-30 attestation schema;
5. no real Qualification Authority Registry exists yet;
6. no real qualification issuer key is created or stored by this spike;
7. external-source independence remains governed by SPIKE-EXT/SAE-30, not by signature validity;
8. issuer-generation authorization is not bound to a registry record beyond revocation behavior in the fixture;
9. subject/domain/ACR-generation/protocol-generation/evidence-root/proof-ceiling/closure-ceiling match checks are signed but not semantically qualified by this fixture;
10. malformed or timezone-naive timestamp schema validation is not modeled as a production fail-closed parser here.

None of these gaps authorizes weakening the founding architecture. If SAE-30 cannot close them, SAE-30 cannot become PROVEN.

## 9. Authority boundary

SPIKE-ID authority gain remains **none**. The node selects an initial feasible mechanism and supplies falsifiable evidence for it. It does not qualify the mechanism, does not issue authority, and cannot activate Assurance Evolution.

PR #167 remains fenced and untouched.
