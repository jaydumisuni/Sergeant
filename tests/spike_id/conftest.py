from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.spike_id.qualification_attestation_fixture import (
    NAMESPACE,
    SSHKeyPair,
    build_allowed_signers,
    generate_ssh_keypair,
)


@dataclass(frozen=True)
class IdentityEnvironment:
    """Two independent identities plus the registry that trusts only one.

    ``issuer_key`` stands in for the Qualification Authority: an
    owner-controlled key that never leaves owner custody (see the threat
    model doc). ``candidate_key`` stands in for candidate-controlled
    automation -- a CI bot token, a repo-scoped deploy key, anything a
    candidate/PR-producing pipeline could plausibly hold. ``allowed_signers``
    is the verifier-trusted registry file; by construction it lists only
    the issuer's public key, never the candidate's.
    """

    issuer_key: SSHKeyPair
    candidate_key: SSHKeyPair
    allowed_signers_path: Path


@pytest.fixture()
def identity_environment(tmp_path: Path) -> IdentityEnvironment:
    issuer_key = generate_ssh_keypair(tmp_path, "qa-issuer")
    candidate_key = generate_ssh_keypair(tmp_path, "candidate-ci-bot")

    allowed_signers_text = build_allowed_signers(
        [(issuer_key.identity, NAMESPACE, issuer_key.public_key_line)]
    )
    allowed_signers_path = tmp_path / "allowed_signers"
    allowed_signers_path.write_text(allowed_signers_text, encoding="utf-8")

    return IdentityEnvironment(
        issuer_key=issuer_key,
        candidate_key=candidate_key,
        allowed_signers_path=allowed_signers_path,
    )
