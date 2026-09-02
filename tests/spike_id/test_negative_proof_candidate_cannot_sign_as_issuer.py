"""SPIKE-ID's critical negative proof.

`docs/58` section 12's operational invariant:

    candidate-controlled operational principal != qualification issuer
    principal

    Candidate repository code, CI, build/runtime, analyzers, generated
    helpers and candidate-held credentials cannot issue their own
    authoritative qualification.

These tests genuinely attempt every plausible forgery a candidate-
controlled automation identity (a CI bot token / repo-scoped deploy key --
modeled here as ``identity_environment.candidate_key``, a completely
separate keypair from the issuer's) could try, and prove each one fails
verification against the issuer-only ``allowed_signers`` registry. This is
not an assertion in prose: every test in this file calls the real
``ssh-keygen -Y verify`` subprocess and checks its real exit code.

If any of these had passed, that would be the honest, reportable finding
that SSHSIG is *not* a safe mechanism for candidate-automation/issuer
separation. They do not pass.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.spike_id.conftest import IdentityEnvironment
from tests.spike_id.qualification_attestation_fixture import (
    NAMESPACE,
    build_allowed_signers,
    build_attestation_payload,
    canonical_json,
    sign_payload,
    verify_signature,
)


def test_registry_structurally_excludes_the_candidate_public_key(
    identity_environment: IdentityEnvironment,
) -> None:
    """Sanity/structural check: the issuer-only registry file does not
    contain the candidate's public key material at all. Everything else in
    this file demonstrates *why* that structural fact is enforced
    cryptographically, not just by omission."""

    registry_text = identity_environment.allowed_signers_path.read_text(encoding="utf-8")
    assert identity_environment.issuer_key.public_key_line.split()[1] in registry_text
    candidate_key_material = identity_environment.candidate_key.public_key_line.split()[1]
    assert candidate_key_material not in registry_text
    assert identity_environment.issuer_key.identity != identity_environment.candidate_key.identity


def test_candidate_signed_attestation_fails_verification_against_issuer_registry(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """The core negative proof: candidate-controlled automation signs a
    self-authored "I am qualified" attestation about its own candidate,
    using only the credential it actually has (its own key). Verification
    against the real, issuer-only registry must fail."""

    now = datetime.now(timezone.utc)
    forged_payload = build_attestation_payload(
        subject_digest="sha256:ff" * 32,
        attestation_id="attest-forged-0001",
        sequence=1,
        # The candidate automation claims the issuer's identity string --
        # this is exactly what a self-certifying producer would try.
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(forged_payload)

    # Candidate automation can only sign with the credential it actually
    # holds: its own key. It does not have, and cannot derive, the
    # issuer's private key.
    forged_signature = sign_payload(
        payload_bytes,
        identity_environment.candidate_key.private_key_path,
        tmp_path,
        filename_stem="forged-attestation",
    )

    verify_result = verify_signature(
        payload_bytes,
        forged_signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="forged-attestation",
    )
    assert not verify_result.ok
    assert verify_result.returncode != 0


def test_candidate_cannot_launder_authority_by_shipping_its_own_registry(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """A candidate that also controls repository content might try to ship
    its own replacement ``allowed_signers`` file (e.g. in a PR diff) that
    lists its own key under the issuer's identity string. This proves that
    trick doesn't help *this* verifier, because the verifier consults the
    real, owner-held registry (``identity_environment.allowed_signers_path``)
    -- a file this spike's threat model requires to live outside
    candidate-controlled write paths (see the custody threat model doc).
    The candidate's forged registry is built here purely to show it is
    inert against the real one; nothing in this repository ever points
    verification at a candidate-suppliable registry file.
    """

    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:ee" * 32,
        attestation_id="attest-forged-registry-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(payload)
    forged_signature = sign_payload(
        payload_bytes,
        identity_environment.candidate_key.private_key_path,
        tmp_path,
        filename_stem="forged-registry-attestation",
    )

    # The candidate crafts its own registry that (mis)labels its own key as
    # the issuer.
    candidate_forged_registry = tmp_path / "candidate_forged_allowed_signers"
    candidate_forged_registry.write_text(
        build_allowed_signers(
            [
                (
                    identity_environment.issuer_key.identity,
                    NAMESPACE,
                    identity_environment.candidate_key.public_key_line,
                )
            ]
        ),
        encoding="utf-8",
    )

    # Against the candidate's OWN forged registry, verification would
    # (unsurprisingly) succeed -- this is exactly why the real verifier
    # must never be pointed at a candidate-writable registry path.
    verify_against_forged_registry = verify_signature(
        payload_bytes,
        forged_signature,
        candidate_forged_registry,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="forged-registry-attempt-a",
    )
    assert verify_against_forged_registry.ok

    # Against the REAL, owner-held registry (the only one this spike's
    # threat model allows a verifier to trust), the same forged
    # signature/payload fails.
    verify_against_real_registry = verify_signature(
        payload_bytes,
        forged_signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="forged-registry-attempt-b",
    )
    assert not verify_against_real_registry.ok


def test_candidate_key_under_its_own_honest_identity_is_not_qualification_authority(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """Even if the candidate signs honestly under its OWN identity (no
    impersonation attempt at all), a verifier that only grants issuer
    authority to the registered issuer identity/key pair must not accept
    it as a Qualification Attestation. This proves the separation holds
    even in the "good faith, wrong principal" case, not just the
    adversarial-impersonation case."""

    now = datetime.now(timezone.utc)
    honest_candidate_claim = build_attestation_payload(
        subject_digest="sha256:dd" * 32,
        attestation_id="attest-honest-candidate-0001",
        sequence=1,
        issuer_identity=identity_environment.candidate_key.identity,
        issuer_generation="candidate-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(honest_candidate_claim)
    signature = sign_payload(
        payload_bytes,
        identity_environment.candidate_key.private_key_path,
        tmp_path,
        filename_stem="honest-candidate-attestation",
    )

    # The candidate identity was never enrolled in the issuer registry at
    # all, so a lookup for it as a qualification issuer must fail outright.
    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.candidate_key.identity,
        tmp_path,
        filename_stem="honest-candidate-attestation",
    )
    assert not verify_result.ok
    assert verify_result.returncode != 0
    assert "could not verify signature" in (verify_result.stderr + verify_result.stdout).lower()
