"""SPIKE-ID fixture: a cryptographically valid signature is not enough.

`docs/58` section 12 states plainly: "Authentic attestation is not
automatically valid qualification." These tests prove the application
layer, not just the signature check, rejects a stale (expired) attestation
and a replayed (previously-consumed) attestation id -- both cases where
``ssh-keygen -Y verify`` alone would say the signature is perfectly good.
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


def test_expired_attestation_is_rejected_despite_valid_signature(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    issued_at = now - timedelta(days=60)
    expired_at = now - timedelta(days=30)
    payload = build_attestation_payload(
        subject_digest="sha256:11" + "0" * 62,
        attestation_id="attest-stale-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=issued_at.isoformat(),
        expires_at=expired_at.isoformat(),
    )
    payload_bytes = canonical_json(payload)
    signature = sign_payload(
        payload_bytes,
        identity_environment.issuer_key.private_key_path,
        tmp_path,
        filename_stem="stale-attestation",
    )

    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="stale-attestation",
    )
    # The signature itself is genuinely valid -- the issuer really did sign
    # this payload. The point of this test is that validity alone is not
    # currentness.
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
    assert disposition.expired
    assert not disposition.accepted


def test_replayed_attestation_id_is_rejected_on_second_submission(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """First submission of a fresh, valid attestation is accepted and its id
    is recorded as consumed. Re-submitting the *exact same* signed
    attestation a second time (a classic replay) must be rejected even
    though the signature is, again, genuinely valid."""

    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:22" + "0" * 62,
        attestation_id="attest-replay-0001",
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
        filename_stem="replay-attestation",
    )

    seen_attestation_ids: set[str] = set()

    first_verify = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="replay-attestation-first",
    )
    first_disposition = evaluate_attestation(
        verify_result=first_verify,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=seen_attestation_ids,
        now=now,
    )
    assert first_disposition.accepted
    # Verifier records the attestation id as consumed after accepting it.
    seen_attestation_ids.add(payload["attestation_id"])

    second_verify = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="replay-attestation-second",
    )
    second_disposition = evaluate_attestation(
        verify_result=second_verify,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=seen_attestation_ids,
        now=now,
    )
    assert second_disposition.cryptographically_valid
    assert second_disposition.replayed
    assert not second_disposition.accepted
