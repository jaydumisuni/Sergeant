"""SPIKE-ID currentness proof: authentic signatures are not sufficient."""

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


def _signed_disposition(
    *,
    identity_environment: IdentityEnvironment,
    tmp_path: Path,
    payload: dict,
    now: datetime,
    filename_stem: str,
    seen_attestation_ids: set[str] | None = None,
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
        identity_environment.allowed_signers_path,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem=filename_stem,
    )
    assert verify_result.ok, verify_result.stderr
    return evaluate_attestation(
        verify_result=verify_result,
        payload=payload,
        revoked_attestation_ids=set(),
        revoked_issuer_generations=set(),
        seen_attestation_ids=seen_attestation_ids or set(),
        now=now,
    )


def test_expired_attestation_is_rejected_despite_valid_signature(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:11" + "0" * 62,
        attestation_id="attest-stale-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=(now - timedelta(days=60)).isoformat(),
        expires_at=(now - timedelta(days=30)).isoformat(),
    )
    disposition = _signed_disposition(
        identity_environment=identity_environment,
        tmp_path=tmp_path,
        payload=payload,
        now=now,
        filename_stem="stale-attestation",
    )
    assert disposition.cryptographically_valid
    assert disposition.expired
    assert not disposition.accepted


def test_attestation_is_rejected_at_exact_expiry_instant(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    """Expiry is an exclusive upper bound; equality must fail closed."""
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:12" + "0" * 62,
        attestation_id="attest-expiry-boundary-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=(now - timedelta(minutes=5)).isoformat(),
        expires_at=now.isoformat(),
    )
    disposition = _signed_disposition(
        identity_environment=identity_environment,
        tmp_path=tmp_path,
        payload=payload,
        now=now,
        filename_stem="expiry-boundary-attestation",
    )
    assert disposition.cryptographically_valid
    assert disposition.expired
    assert not disposition.accepted


def test_replayed_attestation_id_is_rejected_on_second_submission(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
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
