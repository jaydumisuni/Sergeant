"""SPIKE-ID reference fixture for an SSHSIG-backed Qualification Attestation.

Feasibility evidence only: not Sergeant production code, not SAE-30, and no
qualification authority is granted by importing or executing this module.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

NAMESPACE = "sergeant-qualification-attestation-v1"


@dataclass(frozen=True)
class SSHKeyPair:
    identity: str
    private_key_path: Path
    public_key_path: Path
    public_key_line: str


@dataclass(frozen=True)
class TrustedIssuerEntry:
    """Verifier-trusted identity/key/generation binding for one issuer."""

    identity: str
    namespace: str
    issuer_generation: str
    public_key_line: str


@dataclass(frozen=True)
class TrustedIssuerRegistry:
    """The fixture stand-in for the future Qualification Authority Registry.

    OpenSSH authenticates the identity/key/namespace through the generated
    ``allowed_signers`` file. ``entries`` additionally binds the authenticated
    identity/key to a verifier-trusted issuer generation; that generation is
    never taken from the signed payload itself.
    """

    allowed_signers_path: Path
    entries: tuple[TrustedIssuerEntry, ...]

    def generation_for(self, identity: str) -> str | None:
        matches = [entry.issuer_generation for entry in self.entries if entry.identity == identity]
        if len(matches) != 1:
            return None
        return matches[0]


def generate_ssh_keypair(directory: Path, identity: str) -> SSHKeyPair:
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
    return SSHKeyPair(
        identity=identity,
        private_key_path=private_key_path,
        public_key_path=public_key_path,
        public_key_line=public_key_path.read_text(encoding="utf-8").strip(),
    )


def build_allowed_signers(entries: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'{identity} namespaces="{namespace}" {public_key_line}\n'
        for identity, namespace, public_key_line in entries
    )


def build_trusted_issuer_registry(
    directory: Path,
    entries: list[TrustedIssuerEntry],
    *,
    filename: str = "allowed_signers",
) -> TrustedIssuerRegistry:
    """Write the OpenSSH projection and retain verifier-trusted generation state."""

    allowed_signers_path = directory / filename
    allowed_signers_path.write_text(
        build_allowed_signers(
            [(entry.identity, entry.namespace, entry.public_key_line) for entry in entries]
        ),
        encoding="utf-8",
    )
    return TrustedIssuerRegistry(
        allowed_signers_path=allowed_signers_path,
        entries=tuple(entries),
    )


def canonical_json(payload: dict[str, Any]) -> bytes:
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
    return payload_path.with_suffix(payload_path.suffix + ".sig").read_text(encoding="utf-8")


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    returncode: int
    stdout: str
    stderr: str
    identity: str
    namespace: str
    authenticated_issuer_generation: str | None


def verify_signature(
    payload_bytes: bytes,
    signature_text: str,
    registry: TrustedIssuerRegistry | Path,
    identity: str,
    work_dir: Path,
    filename_stem: str,
    namespace: str = NAMESPACE,
) -> VerifyResult:
    """Verify signature bytes and recover generation only from trusted registry state.

    Passing a raw ``Path`` is supported only for negative-control experiments
    such as a candidate-supplied forged registry. Such a path has no trusted
    issuer-generation binding and therefore cannot produce an accepted
    attestation disposition even if raw SSHSIG verification succeeds.
    """

    if isinstance(registry, TrustedIssuerRegistry):
        allowed_signers_path = registry.allowed_signers_path
        authenticated_generation = registry.generation_for(identity)
    else:
        allowed_signers_path = registry
        authenticated_generation = None

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
        identity=identity,
        namespace=namespace,
        authenticated_issuer_generation=authenticated_generation,
    )


@dataclass(frozen=True)
class AttestationDisposition:
    cryptographically_valid: bool
    revoked: bool
    expired: bool
    replayed: bool
    identity_mismatch: bool
    issuer_generation_mismatch: bool
    not_yet_valid: bool

    @property
    def accepted(self) -> bool:
        return (
            self.cryptographically_valid
            and not self.revoked
            and not self.expired
            and not self.replayed
            and not self.identity_mismatch
            and not self.issuer_generation_mismatch
            and not self.not_yet_valid
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
    """Apply bounded verifier-side authority/currentness checks.

    Crucially, generation revocation is checked against the generation bound
    to the authenticated issuer in verifier-trusted registry state. The signed
    payload may repeat that generation for coherence, but cannot choose it.
    """

    issued_at = datetime.fromisoformat(payload["issued_at"])
    expires_at = datetime.fromisoformat(payload["expires_at"])
    expired = now >= expires_at
    not_yet_valid = now < issued_at
    identity_mismatch = payload["issuer_identity"] != verify_result.identity

    authenticated_generation = verify_result.authenticated_issuer_generation
    issuer_generation_mismatch = (
        authenticated_generation is None
        or payload["issuer_generation"] != authenticated_generation
    )
    revoked = (
        payload["attestation_id"] in revoked_attestation_ids
        or (
            authenticated_generation is not None
            and authenticated_generation in revoked_issuer_generations
        )
    )
    replayed = payload["attestation_id"] in seen_attestation_ids
    return AttestationDisposition(
        cryptographically_valid=verify_result.ok,
        revoked=revoked,
        expired=expired,
        replayed=replayed,
        identity_mismatch=identity_mismatch,
        issuer_generation_mismatch=issuer_generation_mismatch,
        not_yet_valid=not_yet_valid,
    )
