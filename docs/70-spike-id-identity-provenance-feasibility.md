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
- moves current SPIKE-ID authority to `docs/70`/`docs/71`;
- transplants the real `tests/spike_id/` fixture set onto current-main ancestry;
- records current-review corrections explicitly rather than pretending the historical fixture generation was already perfect.

SAE-00 is now PROVEN through `docs/66`/`docs/67`, so SPIKE-ID's only frozen roadmap proof dependency is available for lifecycle closeout once this reconciled candidate completes review.

## 2. Frozen charter

SPIKE-ID must establish a practical bounded mechanism for Qualification Authority identities, Qualification Attestations, EEPR source authentication, revocation/currentness, and candidate-automation credential separation.

It must produce:

1. identity/authentication option analysis;
2. a selected initial mechanism or explicit no-safe-mechanism disposition;
3. a key/credential custody threat model;
4. replay/revocation fixtures;
5. negative proof that candidate-controlled automation cannot acquire issuer authority.

The disposition is **positive feasibility with explicit residual gaps**, not production qualification.

## 3. Option analysis

### 3.1 GPG signatures

GPG can provide strong asymmetric signatures and revocation certificates with low infrastructure cost. It was not selected initially because keyring/agent/passphrase-cache behavior adds custody surfaces unnecessary for this bounded spike. It remains technically viable.

### 3.2 GitHub OIDC / workload identity

OIDC is appropriate for authenticating a workflow to an external relying party, but a candidate repository's own workflow identity is the wrong trust shape for Qualification Authority issuance. Candidate-controlled operational principals must remain distinct from qualification issuers; authentic CI identity is not issuer authority.

This distinction is reinforced by Sergeant's prior rejected Oracle OIDC learning proposal: exact workflow identifiers and broad repository trust were insufficient as generalized authority law.

### 3.3 Sigstore / cosign keyless

Sigstore offers strong signing plus public transparency, but introduces external CA/log/OIDC infrastructure and network dependence. Its transparency properties may be valuable later if SAE-30 requires independently visible issuance-time evidence. It is not required to prove initial mechanism feasibility.

### 3.4 Dedicated owner-held ed25519 SSHSIG issuer — selected

The selected initial mechanism is OpenSSH SSHSIG with a **dedicated qualification-issuer key** and verifier-trusted authority state:

- sign: `ssh-keygen -Y sign`;
- verify: `ssh-keygen -Y verify`;
- domain namespace: `sergeant-qualification-attestation-v1`;
- trusted registry: issuer identity + public key + namespace + issuer generation;
- signed issuer coherence: payload `issuer_identity` must equal the identity actually authenticated by the verifier;
- signed generation coherence: payload `issuer_generation` must equal the generation bound by verifier-trusted registry state;
- generation revocation is evaluated against that authenticated registry generation, never against a payload-selected generation;
- issue-time currentness: future `issued_at` is not yet valid;
- expiry: `expires_at` is an exclusive upper bound, so equality is expired;
- replay: verifier-side consumed `attestation_id` state;
- individual revocation: `attestation_id`;
- key-generation revocation: authenticated issuer generation.

Why selected: it uses audited OpenSSH primitives, adds no Python cryptography dependency, has no mandatory third-party service, and makes producer/issuer separation concrete. Candidate automation may own arbitrary keys and signatures; authority exists only when the verifier's independent trust state admits the authenticated issuer identity/key/generation.

An SSH signature is still **not qualification**. SAE-30 must later bind issuer authorization, artifact family/domain, ACR generation, qualification-protocol generation, Judge-admitted evidence roots, proof/closure ceilings, revocation/currentness authority, and full subject/coherence semantics.

## 4. Custody threat model

### 4.1 Issuer private key

A real issuer key must be dedicated to qualification issuance and remain outside candidate-controlled repository, CI, build/runtime, generated-helper, and secret-store write paths. It must not be reused as a developer login or ordinary deploy credential.

The fixtures use passphrase-less throwaway keys under pytest temporary directories only. That is test convenience, not production custody guidance.

### 4.2 Trusted issuer registry

The load-bearing verifier input is not merely an OpenSSH file containing a public key. The authority record must bind the authenticated issuer identity/key to an issuer **generation** as verifier-trusted state. This closes a valid hostile-review attack: a compromised generation-1 key cannot evade generation revocation by signing a payload that simply declares `issuer_generation = generation-2`.

The fixture projects identity/key/namespace into OpenSSH `allowed_signers` and retains the corresponding issuer-generation binding in the verifier-trusted registry object. `VerifyResult.authenticated_issuer_generation` is derived from that trusted registry; the signed payload may repeat the value for coherence but cannot choose which generation was authenticated.

### 4.3 Candidate compromise

Compromise of candidate automation must expose only candidate-held credentials. It must not expose the qualification-issuer private key or grant write authority over verifier-trusted issuer/revocation state.

The negative fixture proves candidate non-authority when the candidate:

- claims the issuer identity string;
- signs under its own honest identity;
- ships a self-serving replacement `allowed_signers` file.

The forged-registry case is intentionally instructive: raw SSHSIG verification can succeed against candidate-controlled trust material, but that raw path carries no trusted issuer-generation binding and therefore cannot yield an accepted qualification disposition. Registry custody and provenance—not signature syntax—are the authority boundary.

### 4.4 Key compromise and revocation

If an authenticated issuer generation is compromised, revoking that trusted generation invalidates all attestations produced by that key generation. A signed payload cannot relabel the compromised key as a new generation; the direct falsifier signs a “generation 2” payload with the generation-1 private key and proves it remains generation-mismatched and revoked.

Individual `attestation_id` revocation remains available for narrower correction.

### 4.5 Key loss, succession, and distribution

Safe key loss/rotation/succession and production distribution of trusted registry/revocation state are **not solved by this spike**. SAE-30 must define registry generation, replacement authority, historical invalidation, custody, and recovery without permitting candidate self-enrollment.

## 5. Mechanical fixture set

`tests/spike_id/` remains outside `main_review/`: these are feasibility fixtures, not production capability.

- `qualification_attestation_fixture.py` — SSHSIG signing/verification plus authenticated identity/generation and currentness disposition.
- `conftest.py` — independent issuer/candidate keys and verifier-trusted issuer identity/key/generation registry.
- `test_valid_attestation_verifies.py` — positive control, tamper rejection, issuer-identity coherence.
- `test_replay_and_staleness_rejected.py` — stale, exact-expiry, future-issued, and replay rejection.
- `test_revoked_attestation_rejected.py` — individual revocation, authenticated-generation revocation, and compromised-generation self-relabel attack.
- `test_negative_proof_candidate_cannot_sign_as_issuer.py` — candidate key and candidate-registry non-authority.

Current review made these explicit corrections relative to the historical fixture generation:

1. exact expiry changed from `now > expires_at` to fail-closed `now >= expires_at`;
2. future `issued_at` is rejected;
3. signed `issuer_identity` must match the principal actually authenticated by SSHSIG verification;
4. issuer generation is derived from verifier-trusted registry state and the signed payload must match it;
5. generation revocation is checked against the authenticated trusted generation, preventing a compromised key from self-relabeling;
6. historical negative-proof digest strings were normalized to ordinary `sha256:` + 64 hex characters;
7. the manifest proof was corrected to match the frozen roadmap's actual inline dependency form (`SPIKE-ID: [SAE-00]`) rather than a block-style assumption.

The historical candidate recorded a real local fixture result of **10 passed** and direct `ssh-keygen -Y sign/-Y verify` confirmation. Those remain historical execution results, not fresh claims. The reconciled fixture set contains **14 test cases by static structure** after the added falsifiers. The manifest proof executes them when an OpenSSH runtime is available, but this GitHub-only construction session does not fabricate a fresh run.

## 6. Negative-proof boundary

The invariant remains:

```text
candidate-controlled operational principal != qualification issuer principal
```

A candidate can create arbitrary keys, payloads, signatures, and repository files. None becomes qualification authority unless verifier-trusted state independently binds the authenticated identity/key/generation as an authorized issuer. SAE-30 must turn this feasibility shape into a production Qualification Authority Registry with provenance, domain ceilings, revocation and generation law.

## 7. EEPR compatibility

SSHSIG can authenticate evidence bytes and a source identity, but **signature authenticity alone does not establish independence**. SPIKE-EXT's `INDEPENDENT / NOT_INDEPENDENT / UNKNOWN_INDEPENDENCE` control-lineage criteria remain separately required.

## 8. Residual gaps

The selected mechanism remains bounded by unresolved SAE-30 work:

1. registry and revocation-list distribution custody;
2. no public transparency log;
3. key-holder loss/rotation/succession protocol;
4. fixture payload is only a subset of the full SAE-30 attestation schema;
5. no real Qualification Authority Registry exists yet;
6. no real qualification issuer key is created or stored by this spike;
7. external-source independence remains governed by SPIKE-EXT/SAE-30, not signature validity;
8. subject/domain/ACR-generation/protocol-generation/evidence-root/proof-ceiling/closure-ceiling match checks are signed but not semantically qualified here;
9. malformed or timezone-naive timestamp schema validation is not modeled as a production fail-closed parser.

None of these gaps authorizes weakening the founding architecture. If SAE-30 cannot close them, SAE-30 cannot become PROVEN.

## 9. Authority boundary

SPIKE-ID authority gain remains **none**. It selects an initial feasible mechanism and supplies falsifiable evidence. It does not qualify the mechanism, issue real authority, or activate Assurance Evolution.

PR #167 remains fenced and untouched.
