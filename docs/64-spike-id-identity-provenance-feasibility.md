# SPIKE-ID — Identity / Authenticated Provenance Feasibility

Status: **SPIKE CANDIDATE, REVIEWED, PROOF ATTACHED**. Authority gain: **none**, per `docs/59-sergeant-assurance-evolution-roadmap.md` section 6 ("Authority gain: none"). This document does not implement `SAE-30`, does not create a Qualification Authority Registry, and does not change any current Sergeant verdict path.

This is the SPIKE-ID node of the Sergeant Assurance Evolution roadmap (`docs/59`, section 6). Its proof requirement is `SAE-00`. `SAE-00` (`docs/62-sae00-founding-authority-and-preservation-reference.md` / `docs/63-sae00-founding-authority-reference-manifest.json`) was open as PR #170 and not yet merged when this spike was built; per `docs/59` section 2, "independent recovery, fixtures, donor research, threat analysis and isolated candidate work may proceed early where inputs are not yet frozen" — this spike is exactly that category of early, isolated preparation. It does not depend on `SAE-00`'s content, only on `SAE-00` proving before `SAE-30` (the node that actually consumes SPIKE-ID's output) can prove. See section 8 below for the exact live-state recovery performed for this spike.

## 1. What SPIKE-ID requires

Quoted from `docs/59` section 6:

> Purpose: establish a practical bounded mechanism for Qualification Authority identities, Qualification Attestations, EEPR source authentication, revocation/currentness and candidate-automation credential separation.
>
> Must produce:
> - identity/authentication option analysis;
> - selected initial mechanism or explicit no-safe-mechanism disposition;
> - key/credential custody threat model;
> - replay/revocation fixtures;
> - negative proof that candidate-controlled automation cannot acquire issuer authority.

The terms this spike is bound to are defined in `docs/58-sergeant-assurance-evolution-founding-architecture.md`:

- **Qualification Authority** — section 12: the exact RAB contains a "Qualification Authority Registry binding authorized qualification issuers to artifact families, domains, proof ceilings, independence constraints, generation and revocation state." The operational invariant: `candidate-controlled operational principal != qualification issuer principal`.
- **Qualification Attestation** — section 12: a signed document binding subject identity/digest/generation, artifact family, qualified domain, ACR generation, qualification-protocol generation, Judge-admitted evidence root, proof-class/closure-grade ceilings, independence/lineage disposition, issuer identity/generation, revocation/currentness, and authenticated provenance. Critically: "Authentic attestation is not automatically valid qualification" — a verifier must *also* check issuer authorization, subject/domain/generation match, evidence closure, ceilings and non-revocation.
- **EEPR (External Evidence Provenance Record)** — section 13: every evidence item counted toward a mandatory independent/external qualification lane must carry an authenticated record binding evidence identity, exact Review World, source-principal identity, authenticated source provenance, source authority generation, relationship to candidate-authoring/qualification-corpus/candidate-infrastructure lineage, and an independence disposition (`INDEPENDENT` / `NOT_INDEPENDENT` / `UNKNOWN_INDEPENDENCE`). "Evidence bytes plus content hash do not establish externality or independence" — the authentication mechanism this spike evaluates is exactly what would let an EEPR's "authenticated source provenance" field be a real, checkable claim rather than an assertion.
- **Candidate-automation credential separation** — the requirement (section 12) that "Candidate repository code, CI, build/runtime, analyzers, generated helpers and candidate-held credentials cannot issue their own authoritative qualification." This is the property this spike's negative-proof fixture exists to test directly, not assert.

## 2. Option analysis

Four practical mechanism classes were evaluated for issuing/verifying an identity-bound Qualification Attestation. Each is weighed on: infrastructure cost for a small owner-operated project; genuine non-repudiation vs. spoofability; how revocation/currentness would work; and — the decisive axis — whether the private key/credential could ever become reachable by candidate-controlled automation.

### 2.1 GPG-signed commits/tags/artifacts

**What it is.** Git and GitHub already support GPG-signed commits/tags natively (`git commit -S`, GitHub's "Verified" badge). An owner-held GPG key could sign a Qualification Attestation document directly.

**Infrastructure cost.** Low — `gpg` is a standard tool, present on this development machine and on GitHub Actions runners.

**Non-repudiation.** Genuine, assuming private key custody holds (see section 3). GPG's web-of-trust model is not needed here; a single owner-held key with an explicit fingerprint pin is sufficient — web-of-trust would in fact be a liability (it invites exactly the kind of "who else vouches for this key" ambiguity the roadmap's Total Set-Valued Closure Law warns against for authority-bearing collections).

**Revocation.** GPG has a native revocation-certificate mechanism, but it depends on relying parties fetching updated revocation status from a keyserver or an explicitly distributed revocation certificate — an extra moving part (keyserver availability, staleness) for a project that otherwise has zero server-side infrastructure.

**Credential separation.** Achievable in principle (the private key simply never touches CI), but GPG's key-management UX (keyring files, agent sockets, passphrase caching in `gpg-agent`) creates more incidental surface area where a key or an unlocked agent socket could accidentally end up reachable from an automation environment than a single opaque private-key file does.

**Disposition.** Viable but not selected as the *initial* mechanism — SSHSIG (2.4) achieves the same non-repudiation and a simpler credential-separation story with less incidental surface area, using a tool this repository's CI already has installed for git operations.

### 2.2 GitHub App / OIDC workload identity

**What it is.** A workload (e.g. a GitHub Actions job) requests a short-lived OIDC token from GitHub's OIDC provider, scoped to that exact workflow/repo/ref/run. A relying party (e.g. a cloud provider, or a custom verifier) checks the token's claims against an explicit allowlist.

**Infrastructure cost.** Requires either a cloud-side OIDC-trust configuration (as `docs/26-cloudflare-connector-assurance.md` reflects for the Cloudflare connector's credential model) or a self-hosted token verifier. Meaningful infrastructure for a small owner-operated project, and — critically for this specific use — **it authenticates a workflow/CI identity, not a human/Owner identity**. That is the wrong shape for a Qualification Authority: `docs/58` section 12 requires the issuer to be distinct from candidate-controlled operational principals, and a GitHub Actions OIDC identity is, by definition, a CI-workflow identity running in the repository's own automation. Using it as the *issuer* identity would make the qualification issuer and a candidate-triggerable CI run the same trust category — the opposite of the required separation.

**Directly relevant prior finding.** This repository has first-hand experience here: PICKUP.md records that a real Oracle repair (`jaydumisuni/Oracle-` PR #150, `.github/self-learning/results/project-oracle-oidc-workflow-20260818.json`) used OIDC workflow-identity binding to *authorize a private-deploy workflow* — a materially different problem (authorizing an already-trusted repository's own CI to deploy) from *issuing qualification authority over a candidate*. The rejected learning-lesson proposal drawn from that repair was rejected specifically for: copying exact fixing-patch workflow identifiers instead of generalizing, overly broad repository trust as a false-positive risk, and missing negative-control proof for an otherwise-valid third workflow identity. Those same three failure modes — narrow-but-uncopied identifier binding, avoiding over-broad trust, and mandatory negative controls — are exactly what this spike's fixtures were built to satisfy for SSHSIG (section 5). OIDC workload identity remains a reasonable mechanism for *authorizing CI to act as itself* (deploy, publish); it is a poor fit for *issuing Qualification Authority over that same CI's own candidate output*, because the issuing principal and the candidate-producing principal would share one trust root (GitHub's OIDC provider plus this repository's own workflow definitions).

**Disposition.** Not selected as the issuer mechanism, for the structural reason above (issuer/candidate-automation principal collision), independent of implementation cost. It remains a legitimate mechanism for `SPIKE-EXT`-adjacent external-source authentication questions and for ordinary CI-to-cloud-provider trust, which is a different problem.

### 2.3 Sigstore / cosign keyless signing

**What it is.** An ephemeral keypair is generated per signing operation; the public key is bound to an OIDC identity (e.g. a GitHub Actions or personal-account OIDC token) via a short-lived certificate from Sigstore's Fulcio CA, and the signing event is recorded in Sigstore's public Rekor transparency log.

**Infrastructure cost.** Requires trusting Sigstore's public infrastructure (Fulcio CA, Rekor log) as a third-party dependency, plus network access at signing and verification time. This is the heaviest-infrastructure option evaluated.

**Non-repudiation.** Strong, and it has a genuine advantage the other options lack: a public, append-only transparency log gives independently checkable evidence that a given signature was issued at a given time, which is directly useful for "currentness" claims and for `docs/58` section 13's EEPR "creation time/generation" requirement.

**Credential separation.** Keyless signing sidesteps long-lived private-key custody, but only by substituting it for OIDC-identity custody — whoever controls the signing identity's OIDC token controls signing capability for that identity, which is the same GitHub Actions-identity problem as 2.2 if the signing identity is ever a repository workflow. Using a *personal* (human Owner) OIDC identity as the Sigstore signing identity would avoid that collision, but then the mechanism's only real advantage over SSHSIG (the public transparency log) comes at the cost of a third-party service dependency this project does not otherwise have anywhere in its stack.

**Disposition.** Not selected as the initial mechanism — the infrastructure and third-party trust cost is disproportionate to what a *bounded initial* mechanism needs to prove, per `docs/59`'s framing of SPIKE-ID as an early bounded feasibility spike rather than the final `SAE-30` substrate. It is a legitimate later candidate if `SAE-30` needs stronger public-transparency currentness guarantees than an owner-held revocation list can provide.

### 2.4 Owner-held asymmetric keypair with an explicit revocation list (selected: SSHSIG)

**What it is.** A single owner-held asymmetric keypair signs Qualification Attestations; a small, explicitly owner-maintained registry file binds identity strings to public keys (and, separately, a revocation list tracks revoked attestation ids and revoked issuer-key generations). This is a general shape; the *specific* instantiation selected is OpenSSH's SSHSIG format (`ssh-keygen -Y sign` / `ssh-keygen -Y verify`), the same signature primitive git and GitHub already use for SSH-signed commits/tags.

**Infrastructure cost.** None beyond `ssh-keygen`, which ships with OpenSSH and is already present on this development machine and on the GitHub Actions `ubuntu-latest` runner image this repository's CI uses (confirmed in section 6). No new Python dependency, no third-party service, no keyserver.

**Non-repudiation.** Genuine ed25519 signatures verified by a real, audited implementation (OpenSSH), not a hand-rolled cryptographic primitive — this spike deliberately does not reimplement signature math.

**Revocation/currentness.** SSHSIG itself has no built-in revocation, so this is handled explicitly at the application layer (exactly as `docs/58` section 12 requires — "Authentic attestation is not automatically valid qualification" — signature validity is necessary, not sufficient): an attestation carries `attestation_id`, `issuer_generation`, `issued_at` and `expires_at`; a verifier checks cryptographic validity *and* that the attestation id is not in a revocation list *and* that the issuer generation is not itself revoked *and* that `expires_at` has not passed *and* (for replay) that the attestation id has not already been consumed. Section 5 below proves each of these independently.

**Credential separation.** The strongest of the four options for this specific project shape: the private key is one opaque file an Owner generates and holds outside the repository and outside any CI-reachable path (see the threat model, section 3). There is no keyring daemon, no agent socket, no OIDC token broker, no third-party service — fewer moving parts than GPG or OIDC, which means fewer places a credential-separation mistake could hide.

**Disposition.** **Selected as the initial mechanism** for Qualification Authority identities and Qualification Attestations. This is not a claim that SSHSIG is the final `SAE-30` mechanism forever — only that it is a genuinely practical, low-infrastructure, strong-separation *initial* mechanism, which is exactly what SPIKE-ID is scoped to establish.

## 3. Key/credential custody threat model

### 3.1 Who holds the private key, and where it lives

The issuer private key is generated once by the human Owner, on Owner-controlled hardware, using `ssh-keygen -t ed25519`. It is never committed to the repository, never placed in a GitHub Actions secret, never referenced by any workflow file, and never generated by or handed to any automation. Only the corresponding **public** key (and an identity label) is ever added to the repository, inside the `allowed_signers`-shaped registry file that a verifier reads.

This is a deliberately narrow custody model — a single Owner-held file — chosen because every additional custody path (a CI secret, a shared keyring, a cloud KMS with automation-reachable IAM policy) is a candidate credential-separation failure mode waiting to happen. `docs/58` section 26 explicitly allows "Owner/Root constitutional authority" as part of the finite trust boundary; this custody model spends that trust in exactly one place.

### 3.2 What happens if the machine running candidate automation is compromised

By construction, candidate automation (CI runners, any bot/PR-producing pipeline, any candidate-triggerable job) never has the issuer private key in its filesystem, environment, or secret store — so its compromise does not, by itself, expose the issuer key. This spike's negative-proof fixture (section 5, `test_negative_proof_candidate_cannot_sign_as_issuer.py`) demonstrates the concrete consequence: even a fully-capable candidate-automation identity that can sign *something* with *its own* key cannot produce a signature that verifies against the issuer-only registry.

The residual risk is not "candidate automation reads the key" but "a human or process with independent access to both the Owner's machine and the CI environment introduces a shared secret between them" (e.g. an Owner accidentally pasting the private key into a CI secret, or reusing the same key for both a personal `~/.ssh/id_ed25519` used for login *and* qualification issuance). This spike's recommendation, carried into the threat-model disposition below, is that the issuer key must be a **dedicated** key generated solely for this purpose, distinct from any key used for ordinary repository/SSH access — so that an ordinary developer-machine SSH-access compromise does not automatically imply issuer-key compromise, and vice versa.

### 3.3 Blast radius of a leaked key

If the issuer private key leaks, an attacker can sign attestations that verify as genuine issuer attestations until: (a) the leak is discovered, and (b) the issuer generation is revoked (section 5's `test_revoked_issuer_generation_rejects_every_attestation_it_ever_signed` proves that revoking an issuer *generation* invalidates every attestation that generation ever signed, not just attestations discovered to be malicious one at a time). The blast radius is therefore bounded by detection latency, not by an unbounded number of individually-tracked bad attestations — this is a materially better failure mode than a scheme with no generation-level revocation, where an Owner would have to enumerate and individually revoke every attestation a compromised key ever issued.

This is also why `issuer_generation` is a first-class field in the attestation payload (`qualification_attestation_fixture.build_attestation_payload`) rather than an afterthought: it is the unit revocation actually needs to operate on when the *key itself*, not one specific claim, is what's suspected compromised.

### 3.4 How revocation actually gets enforced

Revocation is enforced by the verifier consulting an explicit, Owner-maintained revocation list (of revoked `attestation_id`s and revoked `issuer_generation`s) as a mandatory, separate check *in addition to* cryptographic signature validity — never by the signature check alone, and never by trusting a claim inside the (possibly stale or malicious) attestation payload itself about its own revocation status. `evaluate_attestation` in the fixture module takes the revocation sets as verifier-supplied arguments precisely to make this structural: the attestation cannot vouch for its own currentness.

For a real `SAE-30` implementation, "the verifier consults an explicit revocation list" implies that list itself needs the same custody discipline as the registry (owner-controlled write path, not candidate-writable) — this spike does not solve that distribution problem, it only proves the *check* is sound once such a list is available, and flags list-distribution custody as a real open gap (section 7).

### 3.5 How "currentness" is checked

Two independent currentness signals are checked, and both are proven as separate failing cases in section 5: `expires_at` freshness (an attestation with a past `expires_at` is rejected regardless of signature validity — `test_expired_attestation_is_rejected_despite_valid_signature`), and replay/reuse (an `attestation_id` already recorded as consumed is rejected on resubmission even though the exact same bytes and signature verify cryptographically — `test_replayed_attestation_id_is_rejected_on_second_submission`). Neither currentness signal is derivable from the signature check alone; both require verifier-side state (a clock, and a "seen" set), which is exactly what `docs/58` section 12 means by "revocation/currentness" being a distinct requirement from "authentic."

## 4. Selected mechanism summary

- **Signature format:** SSHSIG (`ssh-keygen -Y sign` / `ssh-keygen -Y verify`), ed25519 keys.
- **Domain separation:** every signature is bound to the namespace string `sergeant-qualification-attestation-v1`, so a Qualification Attestation signature cannot be replayed as a signed git commit/tag or vice versa (proven structurally by OpenSSH's own namespace check; see section 6's empirical confirmation).
- **Registry:** an `allowed_signers`-shaped file binding one identity string to one specific public key and namespace, held and distributed under Owner custody, never candidate-writable.
- **Attestation payload:** canonical (sorted-key, no-whitespace) JSON covering a bounded subset of `docs/58` section 12's mandatory attestation fields (`tests/spike_id/qualification_attestation_fixture.py::build_attestation_payload` — explicitly documented in-module as illustrative fixture shape, not the frozen `SAE-30` schema).
- **Currentness/revocation:** enforced at the application layer via explicit `expires_at`, `attestation_id`-based replay tracking, `attestation_id`-based individual revocation, and `issuer_generation`-based blanket revocation — all four proven as real, separately-failing test cases.

This is an **initial** mechanism selection, not a claim that SSHSIG is qualified for `SAE-30` in the roadmap's full sense (`QUALIFIED` is a derived, attacked state per `docs/58` section 12 — this spike is feasibility evidence toward that qualification, not the qualification itself).

## 5. Fixtures

All fixtures live under `tests/spike_id/` (see section 9 for why this location, not `main_review/` or a top-level `spikes/`). Every claim in this document that a signature verifies, fails to verify, or is rejected for currentness/revocation/replay reasons is backed by a real subprocess call to the actual `ssh-keygen` binary and a real assertion on its actual exit code — not a mocked or asserted-in-prose result.

| File | Proves |
|---|---|
| `tests/spike_id/qualification_attestation_fixture.py` | The reference SSHSIG signing/verification/currentness-evaluation library the other files exercise. Explicitly documented in-module as non-authoritative fixture code. |
| `tests/spike_id/conftest.py` | Shared `identity_environment` fixture: generates one issuer keypair and one candidate keypair per test, and a registry that lists only the issuer. |
| `tests/spike_id/test_valid_attestation_verifies.py` | A genuinely issuer-signed, current attestation verifies and is accepted (positive control). A byte-tampered payload fails cryptographic verification. |
| `tests/spike_id/test_replay_and_staleness_rejected.py` | A cryptographically valid but expired attestation is rejected. A cryptographically valid attestation replayed a second time (same id, already consumed) is rejected. |
| `tests/spike_id/test_revoked_attestation_rejected.py` | An individually-revoked attestation id is rejected despite valid, unexpired signature. Revoking an issuer *generation* rejects every attestation that generation ever signed. |
| `tests/spike_id/test_negative_proof_candidate_cannot_sign_as_issuer.py` | **The negative proof.** The issuer-only registry structurally excludes the candidate's public key. A candidate-signed forged attestation fails verification against the real registry. A candidate-crafted replacement registry would succeed against *itself* but is inert against the real, owner-held registry — demonstrating why real-registry custody (not the check itself) is the load-bearing control. Even an honest (non-impersonating) candidate-signed claim fails, because the candidate identity was never enrolled as a qualification issuer at all. |

Run fresh during this construction session:

```
python -m pytest -q tests/spike_id/
10 passed in 3.92s
```

## 6. Empirical mechanism confirmation (pre-fixture manual verification)

Before writing the fixture library, the underlying SSHSIG primitives were manually exercised via direct `ssh-keygen -Y sign` / `-Y verify` calls (not through the Python fixture code) to confirm the mechanism actually behaves as the option analysis assumes, on this exact environment:

- A genuine issuer-signed payload verifies: `Good "sergeant-qualification-attestation-v1" signature for qa-issuer with ED25519 key SHA256:...` (exit 0).
- A payload signed by a second, separate keypair (standing in for candidate automation) fails verification against the issuer-only registry: `Signature verification failed: incorrect signature` (exit 255).
- A tampered payload against a genuinely valid signature fails: `Signature verification failed: incorrect signature` (exit 255).
- A signature produced under a different namespace string fails even against the correct key: `Couldn't verify signature: namespace does not match` (exit 255) — confirming the domain-separation property section 4 relies on.
- A lookup for an identity that was never enrolled in the registry fails: `Could not verify signature.` (exit 255).

`ssh-keygen` version used: OpenSSH_9.x (bundled Git-for-Windows OpenSSH client on the development machine; the GitHub Actions `ubuntu-latest` image ships its own current OpenSSH client — this spike depends on `ssh-keygen -Y sign`/`-Y verify` being present, which is standard OpenSSH client functionality, not a special build).

## 7. Genuine open gaps (stated honestly, not hidden)

1. **Registry/revocation-list distribution custody is not solved here.** This spike proves the *check* is sound given a trustworthy `allowed_signers`/revocation-list file; it does not design how that file itself gets distributed to verifiers with owner-controlled, candidate-writable-proof custody in a real CI/Rust-kernel context. That is `SAE-30`'s job.
2. **No public transparency log.** Unlike Sigstore/Rekor (section 2.3), this mechanism gives no independently-checkable public record that a given attestation was issued at a given time beyond the Owner's own records. If `SAE-30` later needs that property, Sigstore remains a candidate worth revisiting — at the cost of the third-party infrastructure dependency this spike avoided.
3. **Single-key-holder availability/succession is unaddressed.** What happens if the Owner's key is lost (not compromised, just lost) is not designed here — a real `SAE-30` implementation would need an explicit key-rotation/succession procedure, not just a compromise/revocation procedure.
4. **This is a bounded fixture schema, not the frozen `SAE-30` attestation schema.** `build_attestation_payload`'s fields are illustrative and deliberately smaller than the full field list `docs/58` section 12 requires (e.g. no `Judge-admitted qualification-evidence root` binding to a real Judge ledger, because no such ledger exists yet to bind to).
5. **EEPR source authentication is only partially addressed.** This spike demonstrates authenticated *issuer* identity for Qualification Attestations. `docs/58` section 13's EEPR also requires binding external-evidence source-principal identity and independence disposition — the same SSHSIG mechanism is a plausible fit (an external reviewer could sign their own evidence submission the same way), but that specific application is `SPIKE-EXT`'s territory, not proven here.

None of these gaps are a "no-safe-mechanism" disposition — they are exactly the kind of narrowed, honestly-scoped residue `docs/59` section 6 anticipates ("Failure does not weaken the architecture. `SAE-30` may prepare work but cannot become PROVEN"). SPIKE-ID's disposition is a **positive initial-mechanism selection with explicit residual gaps**, not a failure disposition.

## 8. Live-state recovery performed for this spike

Recovered fresh via `git fetch origin` then `git rev-parse origin/main` during this construction session:

`9976e43f0d4d318ee4ffd2c4389bd87f520a7757`

This matches the head `SAE-00`'s own binding (`docs/62` section 3.3) recorded on the still-open PR #170, confirming no canonical `main` movement between that construction session and this one. PR #167 (`learning/oracle-browser-repairs-round-2`) was checked via `gh pr view 167` and found unchanged from the state recorded in `docs/60`/`docs/61`/`docs/62` (open, draft, head `536dd6dcf99c4763a4b1ec9c86bcde7e03d5b13c`) — this spike does not touch PR #167, its branch, or any file exclusive to it.

`SAE-00` (PR #170) was open and not yet merged at spike-construction time. Per `docs/59` section 2, this spike proceeded as permitted early, isolated preparation; it does not itself claim `SAE-00`-dependent authority, and `SPIKE-ID` cannot become `PROVEN` until `SAE-00` proves (see `docs/59` section 15's dependency registry: `SPIKE-ID: [SAE-00]`).

## 9. Fixture location convention

No `spikes/` or `research/` directory convention exists elsewhere in this repository (checked: `tests/` is a single flat directory of 184 production test files, no subdirectories, no existing precedent for non-production spike code). This spike places its fixtures under `tests/spike_id/` — a clearly-labeled subdirectory, not mixed flat into `tests/` alongside production tests — because the fixture code and library module are explicitly non-authoritative (`qualification_attestation_fixture.py`'s module docstring states this directly) and this keeps that boundary visually obvious rather than relying on a reader noticing a docstring. `main_review/` (the production package) was intentionally not used for any spike code, since nothing here should be importable as if it were a real Sergeant capability.

## 10. Authority produced

Per `docs/59` section 6: **authority gain is none.** This document, its fixtures, and the manifest in `docs/65-spike-id-feasibility-manifest.json` do not create a Qualification Authority Registry, do not issue any real Qualification Attestation, do not change `main_review/verdict.py` or `main_review/final_proof.py`, and do not alter any current Sergeant verdict path. This node's sole effect on the roadmap DAG is to satisfy one of `SAE-30`'s two spike proof-dependencies (the other being `SPIKE-EXT`) once `SPIKE-ID` itself proves — which additionally requires `SAE-00` to prove first.
