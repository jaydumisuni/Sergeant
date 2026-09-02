"""SPIKE-ID fixture: revocation, at both attestation and issuer-generation
granularity, overrides an otherwise-valid, unexpired signature.

Two revocation shapes are proven separately because they answer different
questions in the threat model doc: (1) "this one attestation was wrong,
pull it" and (2) "this whole issuer key generation is suspected
compromised, distrust everything it ever signed" -- the second is the
generation-level currentness check the custody threat model depends on for
its blast-radius argument.
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


def test_individually_revoked_attestation_is_rejected(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:33" + "0" * 62,
        attestation_id="attest-revoke-0001",
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
        filename_stem="revoke-single-attestation",
    )
    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="revoke-single-attestation",
    )
    assert verify_result.ok, verify_result.stderr

    # Before revocation: accepted.
    before = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert before.accepted

    # Owner/registry revokes this specific attestation id.
    revoked_attestation_ids = {payload["attestation_id"]}

    after = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=revoked_attestation_ids,
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert after.cryptographically_valid
    assert after.revoked
    assert not after.accepted


def test_revoked_issuer_generation_rejects_every_attestation_it_ever_signed(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload_a = build_attestation_payload(
        subject_digest="sha256:44" + "0" * 62,
        attestation_id="attest-gen-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_b = build_attestation_payload(
        subject_digest="sha256:55" + "0" * 62,
        attestation_id="attest-gen-0002",
        sequence=2,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )

    dispositions = []
    for label, payload in (("a", payload_a), ("b", payload_b)):
        payload_bytes = canonical_json(payload)
        signature = sign_payload(
            payload_bytes,
            identity_environment.issuer_key.private_key_path,
            tmp_path,
            filename_stem=f"revoke-generation-{label}",
        )
        verify_result = verify_signature(
            payload_bytes,
            signature,
            identity_environment.allowed_signers_path,
            identity_environment.issuer_key.identity,
            tmp_path,
            filename_stem=f"revoke-generation-{label}",
        )
        assert verify_result.ok, verify_result.stderr
        dispositions.append(
            evaluate_attestation(
                verify_result=verify_result,
                payload=payload,
                revoked_attestation_ids=set(),
                # The owner has suspended/revoked the whole issuer key
                # generation (e.g. suspected key compromise), not any one
                # attestation id.
                revoked_issuer_generations={"qa-issuer-gen-1"},
                seen_attestation_ids=set(),
                now=now,
            )
        )

    assert all(d.cryptographically_valid for d in dispositions)
    assert all(d.revoked for d in dispositions)
    assert not any(d.accepted for d in dispositions)
