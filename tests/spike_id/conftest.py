from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.spike_id.qualification_attestation_fixture import (
    NAMESPACE,
    SSHKeyPair,
    TrustedIssuerEntry,
    TrustedIssuerRegistry,
    build_trusted_issuer_registry,
    generate_ssh_keypair,
)


@dataclass(frozen=True)
class IdentityEnvironment:
    """Independent issuer/candidate identities plus verifier-trusted authority state."""

    issuer_key: SSHKeyPair
    candidate_key: SSHKeyPair
    issuer_generation: str
    trusted_registry: TrustedIssuerRegistry

    @property
    def allowed_signers_path(self) -> Path:
        return self.trusted_registry.allowed_signers_path


@pytest.fixture()
def identity_environment(tmp_path: Path) -> IdentityEnvironment:
    issuer_key = generate_ssh_keypair(tmp_path, "qa-issuer")
    candidate_key = generate_ssh_keypair(tmp_path, "candidate-ci-bot")
    issuer_generation = "qa-issuer-gen-1"

    trusted_registry = build_trusted_issuer_registry(
        tmp_path,
        [
            TrustedIssuerEntry(
                identity=issuer_key.identity,
                namespace=NAMESPACE,
                issuer_generation=issuer_generation,
                public_key_line=issuer_key.public_key_line,
            )
        ],
    )

    return IdentityEnvironment(
        issuer_key=issuer_key,
        candidate_key=candidate_key,
        issuer_generation=issuer_generation,
        trusted_registry=trusted_registry,
    )
