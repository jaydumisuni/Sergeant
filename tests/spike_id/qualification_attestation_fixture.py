"""SPIKE-ID reference fixture for an SSHSIG-backed Qualification Attestation.

This module is feasibility evidence only. It is not Sergeant production code,
does not implement SAE-30, and grants no qualification authority.
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


def generate_ssh_keypair(directory: Path, identity: str) -> SSHKeyPair:
    """Generate one throwaway ed25519 fixture identity under ``directory``."""
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
    """Build the verifier-trusted OpenSSH ``allowed_signers`` registry body."""
    return "".join(
        f'{identity} namespaces="{namespace}" {public_key_line}\n'
        for identity, namespace, public_key_line in entries
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
    """Build the bounded illustrative payload exercised by the spike fixtures."""
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


def verify_signature(
    payload_bytes: bytes,
    signature_text: str,
    allowed_signers_path: Path,
    identity: str,
    work_dir: Path,
    filename_stem: str,
    namespace: str = NAMESPACE,
) -> VerifyResult:
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
    """Apply verifier-side currentness/replay/revocation checks.

    ``expires_at`` is an exclusive upper bound: an attestation is stale at
    the exact expiry instant, so the fail-closed comparison is ``>=``.
    """
    expires_at = datetime.fromisoformat(payload["expires_at"])
    expired = now >= expires_at
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
