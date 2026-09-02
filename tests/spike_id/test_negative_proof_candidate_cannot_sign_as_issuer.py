"""SPIKE-ID's critical candidate/issuer separation negative proof."""

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
    registry_text = identity_environment.allowed_signers_path.read_text(encoding="utf-8")
    assert identity_environment.issuer_key.public_key_line.split()[1] in registry_text
    candidate_key_material = identity_environment.candidate_key.public_key_line.split()[1]
    assert candidate_key_material not in registry_text
    assert identity_environment.issuer_key.identity != identity_environment.candidate_key.identity


def test_candidate_signed_attestation_fails_verification_against_issuer_registry(
    identity_environment: IdentityEnvironment, tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    forged_payload = build_attestation_payload(
        subject_digest="sha256:" + "ff" * 32,
        attestation_id="attest-forged-0001",
        sequence=1,
        issuer_identity=identity_environment.issuer_key.identity,
        issuer_generation="qa-issuer-gen-1",
        issued_at=now.isoformat(),
        expires_at=(now + timedelta(days=30)).isoformat(),
    )
    payload_bytes = canonical_json(forged_payload)
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
    now = datetime.now(timezone.utc)
    payload = build_attestation_payload(
        subject_digest="sha256:" + "ee" * 32,
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

    verify_against_forged_registry = verify_signature(
        payload_bytes,
        forged_signature,
        candidate_forged_registry,
        identity_environment.issuer_key.identity,
        tmp_path,
        filename_stem="forged-registry-attempt-a",
    )
    assert verify_against_forged_registry.ok

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
    now = datetime.now(timezone.utc)
    honest_candidate_claim = build_attestation_payload(
        subject_digest="sha256:" + "dd" * 32,
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
