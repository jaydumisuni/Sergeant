"""SPIKE-ID fixture: a genuinely issuer-signed, current, non-revoked
attestation verifies and is accepted.

This is the positive control the other three fixture files depend on: if
this did not pass, the negative results elsewhere would be meaningless
(a verifier that rejects everything trivially "resists" forgery too).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.spike_id.conftest import IdentityEnvironment
from tests.spike_id.qualification_attestation_fixture import (
    build_attestation_payload,
    canonical_json,
    evaluate_attestation,
    sign_payload,
    verify_signature,
)


def test_genuinely_issuer_signed_current_attestation_is_accepted(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:deadbeef" + "0" * 56,
        attestation_id="attest-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(payload)

    signature = sign_payload(
        payload_bytes,
        identity_environment.issuer_key.private_key_path,
        tmp_path,
        filename_stem="valid-attestation",
    )

    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="valid-attestation",
    )
    assert verify_result.ok, verify_result.stderr
    assert "Good" in verify_result.stderr or "Good" in verify_result.stdout

    disposition = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert disposition.accepted
    assert disposition.cryptographically_valid
    assert not disposition.revoked
    assert not disposition.expired
    assert not disposition.replayed


def test_tampered_payload_fails_cryptographic_verification(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """A byte-for-byte tampered payload must fail verification even though
    a signature file exists and "looks" plausible -- proving the fixture
    checks real signature bytes, not just presence of a .sig file."""

    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:cafebabe" + "0" * 55,
        attestation_id="attest-0002",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(payload)
    signature = sign_payload(
        payload_bytes,
        identity_environment.issuer_key.private_key_path,
        tmp_path,
        filename_stem="tampered-attestation",
    )

    tampered_payload = dict(payload)
    tampered_payload["subject_digest"] = "sha256:ff" + "0" * 62
    tampered_bytes = canonical_json(tampered_payload)

    verify_result = verify_signature(
        tampered_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="tampered-attestation",
    )
    assert not verify_result.ok
