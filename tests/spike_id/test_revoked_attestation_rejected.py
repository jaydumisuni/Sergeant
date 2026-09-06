"""SPIKE-ID revocation proof at attestation and authenticated-key-generation scope."""

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


def _verify_issuer_payload(
    identity_environment: IdentityEnvironment,
    tmp_path: Path,
    payload: dict,
    filename_stem: str,
):
    payload_bytes = canonical_json(payload)
    signature = sign_payload(
        payload_bytes,
        identity_environment.issuer_key.private_key_path,
        tmp_path,
        filename_stem=filename_stem,
    )
    verify_result = verify_signature(
        payload_bytes,
        signature,
        identity_environment.trusted_registry,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem=filename_stem,
    )
    assert verify_result.ok, verify_result.stderr
    assert verify_result.authenticated_issuer_generation == identity_environment.issuer_generation
    return verify_result


def test_individually_revoked_attestation_is_rejected(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:33" + "0" * 62,
        attestation_id="attest-revoke-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation=identity_environment.issuer_generation,
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    verify_result = _verify_issuer_payload(
        identity_environment, tmp_path, payload, "revoke-single-attestation"
    )

    before = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert before.accepted

    after = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids={payload["attestation_id"]},
        revoked_issuer_generations=set(),
        seen_attestation_ids=set(),
        now=now,
    )
    assert after.cryptographically_valid
    assert after.revoked
    assert not after.accepted


def test_revoked_authenticated_issuer_generation_rejects_every_attestation_it_signed(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payloads = [
        build_attestation_payload(
            subject_digest="sha256:44" + "0" * 62,
            attestation_id="attest-gen-0001",
            sequence=1,
            issuer_identity=identity_environment.issuer_key.identity,
            issuer_generation=identity_environment.issuer_generation,
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(days=30)).isoformat(),
        ),
        build_attestation_payload(
            subject_digest="sha256:55" + "0" * 62,
            attestation_id="attest-gen-0002",
            sequence=2,
            issuer_identity=identity_environment.issuer_key.identity,
            issuer_generation=identity_environment.issuer_generation,
            issued_at=now.isoformat(),
            expires_at=(now + timedelta(days=30)).isoformat(),
        ),
    ]

    dispositions = []
    for index, payload in enumerate(payloads):
        verify_result = _verify_issuer_payload(
            identity_environment, tmp_path, payload, f"revoke-generation-{index}"
        )
        dispositions.append(
            evaluate_attestation(
                verify_result=verify_result,
                payload=payload,
                revoked_attestation_ids=set(),
                revoked_issuer_generations={identity_environment.issuer_generation},
                seen_attestation_ids=set(),
                now=now,
            )
        )

    assert all(disposition.cryptographically_valid for disposition in dispositions)
    assert all(disposition.revoked for disposition in dispositions)
    assert not any(disposition.accepted for disposition in dispositions)


def test_compromised_generation_cannot_evade_revocation_by_claiming_new_generation(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """The signed payload cannot choose which issuer generation was authenticated."""

    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:66" + "0" * 62,
        attestation_id="attest-generation-launder-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        # Same generation-1 private key signs bytes falsely claiming gen-2.
        issuer_generation="qa-issuer-gen-2",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    verify_result = _verify_issuer_payload(
        identity_environment, tmp_path, payload, "generation-launder-attestation"
    )
    disposition = evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations={identity_environment.issuer_generation},
        seen_attestation_ids=set(),
        now=now,
    )

    assert disposition.cryptographically_valid
    assert disposition.revoked
    assert disposition.issuer_generation_mismatch
    assert not disposition.accepted
