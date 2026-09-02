"""SPIKE-ID reference fixture: an SSHSIG-backed Qualification Attestation.

This module is **not** Sergeant production code and grants no authority. It
exists to give `docs/64-spike-id-identity-provenance-feasibility.md` real,
runnable evidence rather than prose assertions, per the roadmap's SPIKE-ID
node (`docs/59-sergeant-assurance-evolution-roadmap.md`, section 6):

    Must produce:
    - identity/authentication option analysis;
    - selected initial mechanism or explicit no-safe-mechanism disposition;
    - key/credential custody threat model;
    - replay/revocation fixtures;
    - negative proof that candidate-controlled automation cannot acquire
      issuer authority.

The selected initial mechanism is SSHSIG (`ssh-keygen -Y sign` /
`ssh-keygen -Y verify`), the same signature format git and GitHub already
use for signed commits/tags. It requires no new infrastructure, no new
Python dependency, and no account with a third-party service: only the
`ssh-keygen` binary that ships with OpenSSH (present on the GitHub Actions
`ubuntu-latest` image this repository's CI already runs on, and present on
this development machine).

A Qualification Attestation here is a canonical-JSON document (the fields
below are a deliberately small subset of `docs/58` section 12's required
attestation fields, sufficient to demonstrate feasibility, not a claim of
completeness) signed by an issuer's SSH private key inside an explicit
domain-separating namespace (`NAMESPACE`). Verification requires BOTH:

1. cryptographic validity against an `allowed_signers` file that binds an
   issuer identity string to one specific public key and namespace
   (`verify_signature`), and
2. application-layer currentness/replay/revocation checks
   (`evaluate_attestation`) that a bare signature check cannot express --
   `docs/58` section 12 is explicit that "Authentic attestation is not
   automatically valid qualification."

Nothing here decides real Sergeant qualification outcomes. It is fixture
code proving the mechanism is *practical*, not an implementation of
`SAE-30`.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Domain-separation string bound into every signature. A signature produced
# for a different namespace does not verify here, even with the correct key
# -- this is what stops a SPIKE-ID attestation signature from being replayed
# as, say, a signed git commit or an unrelated protocol's token.
NAMESPACE = "sergeant-qualification-attestation-v1"


@dataclass(frozen=True)
class SSHKeyPair:
    """One ed25519 SSH keypair used as a stand-in identity in the fixtures."""

    identity: str
    private_key_path: Path
    public_key_path: Path
    public_key_line: str


def generate_ssh_keypair(directory: Path, identity: str) -> SSHKeyPair:
    """Generate a fresh, passphrase-less ed25519 keypair under ``directory``.

    Every fixture test generates its own throwaway keys under pytest's
    ``tmp_path``; nothing here is a real, long-lived credential.
    """

    private_key_path = directory / f"{identity}.key"
    public_key_path = directory / f"{identity}.key.pub"
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            str(private_key_path),
            "-N",
            "",
            "-C",
            identity,
            "-q",
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    public_key_line = public_key_path.read_text(encoding="utf-8").strip()
    return SSHKeyPair(
        identity=identity,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
        public_key_line=public_key_line,
    )


def build_allowed_signers(entries: list[tuple[str, str, str]]) -> str:
    """Build an OpenSSH ``allowed_signers`` file body.

    Each entry is ``(identity, namespace, public_key_line)``. This file is
    the fixture stand-in for the roadmap's Qualification Authority
    Registry: it is the thing a verifier trusts, and it is exactly as
    trustworthy as its own custody (see the threat model doc, section on
    registry custody).
    """

    lines = [
        f'{identity} namespaces="{namespace}" {public_key_line}'
        for identity, namespace, public_key_line in entries
    ]
    return "\n".join(lines) + "\n"


def canonical_json(payload: dict[str, Any]) -> bytes:
    """Deterministic encoding so the same logical payload always signs the
    same bytes (sorted keys, no incidental whitespace)."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_attestation_payload(
    *,
    subject_digest: str,
    attestation_id: str,
    sequence: int,
    issuer_identity: str,
    issuer_generation: str,
    issued_at: str,
    expires_at: str,
    artifact_family: str = "spike-id-fixture-capability",
    qualified_domain: str = "spike-id-feasibility-demo",
    acr_generation: str = "unqualified-spike-demo-v0",
    qualification_protocol_generation: str = "spike-id-v0",
    evidence_root: str = "spike-id-demo-evidence-root",
    proof_class_ceiling: str = "HEURISTIC",
    closure_grade_ceiling: str = "PARTIAL",
    independence_disposition: str = "NOT_INDEPENDENT",
) -> dict[str, Any]:
    """Build a demo attestation payload covering the subset of `docs/58`
    section 12's mandatory Qualification Attestation fields this fixture
    exercises. This is illustrative fixture shape, not the frozen SAE-30
    schema -- that schema is SAE-30's job to define and qualify."""

    return {
        "schema": "spike-id.qualification-attestation-fixture.v1",
        "subject_digest": subject_digest,
        "attestation_id": attestation_id,
        "sequence": sequence,
        "artifact_family": artifact_family,
        "qualified_domain": qualified_domain,
        "acr_generation": acr_generation,
        "qualification_protocol_generation": qualification_protocol_generation,
        "evidence_root": evidence_root,
        "proof_class_ceiling": proof_class_ceiling,
        "closure_grade_ceiling": closure_grade_ceiling,
        "independence_disposition": independence_disposition,
        "issuer_identity": issuer_identity,
        "issuer_generation": issuer_generation,
        "issued_at": issued_at,
        "expires_at": expires_at,
    }


def sign_payload(
    payload_bytes: bytes,
    private_key_path: Path,
    work_dir: Path,
    filename_stem: str,
    namespace: str = NAMESPACE,
) -> str:
    """Sign ``payload_bytes`` with ``private_key_path`` inside ``namespace``.

    Returns the SSHSIG armored signature text. Each call uses a unique
    filename so ``ssh-keygen`` never hits its interactive overwrite prompt
    (which would hang a non-interactive test run).
    """

    payload_path = work_dir / f"{filename_stem}.json"
    payload_path.write_bytes(payload_bytes)
    subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(private_key_path),
            "-n",
            namespace,
            str(payload_path),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sig_path = payload_path.with_suffix(payload_path.suffix + ".sig")
    return sig_path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str


def verify_signature(
    payload_bytes: bytes,
    signature_text: str,
    allowed_signers_path: Path,
    identity: str,
    work_dir: Path,
    filename_stem: str,
    namespace: str = NAMESPACE,
) -> VerifyResult:
    """Cryptographically verify ``signature_text`` over ``payload_bytes``
    against ``allowed_signers_path`` for ``identity``/``namespace``.

    This is the pure signature check only. It says nothing about
    revocation, replay, or currentness -- see ``evaluate_attestation``.
    """

    sig_path = work_dir / f"{filename_stem}.sig"
    sig_path.write_text(signature_text, encoding="utf-8")
    proc = subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "verify",
            "-f",
            str(allowed_signers_path),
            "-I",
            identity,
            "-n",
            namespace,
            "-s",
            str(sig_path),
        ],
        input=payload_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return VerifyResult(
        ok=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout.decode("utf-8", "replace"),
        stderr=proc.stderr.decode("utf-8", "replace"),
    )


@dataclass(frozen=True)
class AttestationDisposition:
    """The application-layer verdict on one attestation submission.

    Mirrors `docs/58` section 12's invariant that authentic-signature is a
    necessary but not sufficient condition: an attestation must also be
    unexpired, unrevoked (either directly, or via its issuer generation
    being revoked/superseded), and not a replay of an already-consumed
    attestation id.
    """

    cryptographically_valid: bool
    revoked: bool
    expired: bool
    replayed: bool

    @property
    def accepted(self) -> bool:
        return (
            self.cryptographically_valid
            and not self.revoked
            and not self.expired
            and not self.replayed
        )


def evaluate_attestation(
    *,
    verify_result: VerifyResult,
    payload: dict[str, Any],
    revoked_attestation_ids: set[str],
    revoked_issuer_generations: set[str],
    seen_attestation_ids: set[str],
    now: datetime,
) -> AttestationDisposition:
    expires_at = datetime.fromisoformat(payload["expires_at"])
    expired = now > expires_at
    revoked = (
        payload["attestation_id"] in revoked_attestation_ids
        or payload["issuer_generation"] in revoked_issuer_generations
    )
    replayed = payload["attestation_id"] in seen_attestation_ids
    return AttestationDisposition(
        cryptographically_valid=verify_result.ok,
        revoked=revoked,
        expired=expired,
        replayed=replayed,
    )
