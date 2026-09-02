"""SPIKE-ID positive controls plus authenticated-identity binding falsifier."""

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
    assert not disposition.identity_mismatch
    assert not disposition.not_yet_valid


def test_tampered_payload_fails_cryptographic_verification(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:cafebabe" + "0" * 56,
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
    tampered_payload["subject_digest"] = "sha256:" + "ff" * 32
    verify_result = verify_signature(
        canonical_json(tampered_payload),
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="tampered-attestation",
    )
    assert not verify_result.ok


def test_payload_issuer_identity_must_match_authenticated_signer_identity(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """A valid issuer signature cannot launder a contradictory issuer field."""
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:" + "ab" * 32,
        attestation_id="attest-identity-mismatch-0001",
        sequence=1,
        # The real issuer key signs bytes that incorrectly name the candidate
        # as issuer. Cryptography alone is valid; semantic identity binding
        # must still reject the attestation.
        issuer_identity=identity_environment.candidate_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(payload)
    signature = sign_payload(
        payload_bytes,
        identity_environment.issuer_key.private_key_path,
        tmp_path,
        filename_stem="identity-mismatch-attestation",
    )
    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="identity-mismatch-attestation",
    )
    assert verify_result.ok, verify_result.stderr

    disposition = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert disposition.cryptographically_valid
    assert disposition.identity_mismatch
    assert not disposition.accepted
