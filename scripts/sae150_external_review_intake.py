#!/usr/bin/env python3
"""Validate or ingest SAE-150 external-review evidence without putting secrets in Git."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main_review.external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ControlLineageFacts,
    ExternalEvidenceProvenanceRecord,
    IndependenceState,
    ProvenanceVerifierAuthorization,
    ProvenanceVerifierState,
)
from main_review.qualification_authority import (
    IssuerState,
    QualificationAuthorityRegistry,
    QualificationIssuerAuthorization,
)
from main_review.review_authority_bundle import ReviewAuthorityBundle
from main_review.review_world import GitHubReviewWorld, sha256_id

REGISTRY_PATH = ROOT / "docs/167-sae150-root-qualification-authority-registry.json"
VERIFIER_PATH = ROOT / "docs/168-sae150-provenance-verifier-authorization.json"
RAB_PATH = ROOT / "docs/169-sae150-external-review-rab.json"
WORLD_PATH = ROOT / "docs/170-sae150-external-review-world.json"
MANIFEST_PATH = ROOT / "docs/172-sae150-external-review-intake-manifest.json"
DEFAULT_AUTHORITY_DIR = Path.home() / ".local/state/ttg-cookpit/projects/srg/authority/sae150-genesis-v1"
ACCEPTED_SOURCE_CLASSES = {"SC-1", "SC-2", "SC-3", "SC-4", "SC-6"}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def issuer_from_payload(row: dict) -> QualificationIssuerAuthorization:
    obj = QualificationIssuerAuthorization.create(
        issuer_identity=row["issuer_identity"],
        key_id=row["key_id"],
        namespace=row["namespace"],
        issuer_generation=row["issuer_generation"],
        artifact_families=row["artifact_families"],
        domains=row["domains"],
        proof_classes=row["proof_classes"],
        closure_grades=row["closure_grades"],
        allowed_independence_states=row["allowed_independence_states"],
        control_lineage_id=row["control_lineage_id"],
        authentication_secret_digest=row["authentication_secret_digest"],
        state=IssuerState(row["state"]),
    )
    if obj.authorization_id != row["authorization_id"]:
        raise ValueError("qualification issuer authorization_id mismatch")
    return obj


def load_registry(path: Path = REGISTRY_PATH) -> QualificationAuthorityRegistry:
    row = load_json(path)
    obj = QualificationAuthorityRegistry.create(
        generation=row["generation"],
        issuers=tuple(issuer_from_payload(x) for x in row["issuers"]),
        revoked_attestation_ids=row["revoked_attestation_ids"],
        consumed_attestation_ids=row["consumed_attestation_ids"],
    )
    if obj.registry_id != row["registry_id"]:
        raise ValueError("qualification registry_id mismatch")
    return obj


def load_verifier(path: Path = VERIFIER_PATH) -> ProvenanceVerifierAuthorization:
    row = load_json(path)
    obj = ProvenanceVerifierAuthorization.create(
        verifier_identity=row["verifier_identity"],
        verifier_generation=row["verifier_generation"],
        key_id=row["key_id"],
        verification_secret_digest=row["verification_secret_digest"],
        state=ProvenanceVerifierState(row["state"]),
    )
    if obj.authorization_id != row["authorization_id"]:
        raise ValueError("provenance verifier authorization_id mismatch")
    return obj


def validate_public_packet() -> dict[str, str]:
    registry = load_registry()
    verifier = load_verifier()
    rab = ReviewAuthorityBundle.from_payload(load_json(RAB_PATH))
    world = GitHubReviewWorld.from_payload(load_json(WORLD_PATH))
    manifest = load_json(MANIFEST_PATH)
    checks = {
        "qualification_authority_registry_id": registry.registry_id,
        "provenance_verifier_authorization_id": verifier.authorization_id,
        "rab_id": rab.rab_id,
        "review_world_id": world.review_world_id,
    }
    for key, value in checks.items():
        if manifest[key] != value:
            raise ValueError(f"{key} does not match intake manifest")
    if world.rab_id != rab.rab_id:
        raise ValueError("Review World does not bind the intake RAB")
    if world.diff.head_commit != manifest["candidate_generation"]:
        raise ValueError("Review World candidate generation mismatch")
    if world.diff.base_commit != manifest["base_generation"]:
        raise ValueError("Review World base generation mismatch")
    return checks


def validate_external_authority(authority_dir: Path) -> dict[str, str]:
    public = validate_public_packet()
    external_registry = load_registry(authority_dir / "qualification-authority-registry.json")
    external_verifier = load_verifier(authority_dir / "provenance-verifier-authorization.json")
    if external_registry.registry_id != public["qualification_authority_registry_id"]:
        raise ValueError("external qualification registry differs from frozen public descriptor")
    if external_verifier.authorization_id != public["provenance_verifier_authorization_id"]:
        raise ValueError("external provenance verifier differs from frozen public descriptor")
    secret = (authority_dir / "provenance-verifier-secret.bin").read_bytes()
    if len(secret) < 16:
        raise ValueError("external provenance verifier secret is invalid")
    if hashlib.sha256(secret).hexdigest() != external_verifier.verification_secret_digest:
        raise ValueError("external provenance verifier secret digest mismatch")
    return {**public, "external_authority": "VALID"}


def _proof_payload(proof: AuthenticatedProvenanceProof) -> dict:
    return asdict(proof)


def _eepr_payload(record: ExternalEvidenceProvenanceRecord) -> dict:
    row = asdict(record)
    row["independence_state"] = record.independence_state.value
    row["control_lineage_facts"] = record.control_lineage_facts.to_payload()
    return row


def ingest(submission_path: Path, evidence_path: Path, output_dir: Path, authority_dir: Path) -> dict:
    frozen = validate_external_authority(authority_dir)
    manifest = load_json(MANIFEST_PATH)
    submission = load_json(submission_path)
    source_class = str(submission.get("source_class") or "")
    if source_class not in ACCEPTED_SOURCE_CLASSES:
        raise ValueError(f"source_class {source_class!r} is not accepted for the Genesis independent lane")

    required = (
        "source_principal_id", "source_organization", "source_authority_generation", "creation_generation",
        "authenticated_source_provenance", "candidate_authoring_relationship",
        "qualification_corpus_relationship", "candidate_infrastructure_relationship",
        "reviewer_tool_lineage", "prompt_controller", "input_selector", "finding_selector",
    )
    missing = [name for name in required if not str(submission.get(name) or "").strip()]
    if missing:
        raise ValueError(f"reviewer submission missing fields: {missing}")

    facts_row = submission.get("control_lineage_facts")
    if not isinstance(facts_row, dict):
        raise ValueError("control_lineage_facts must be an object")
    fact_names = (
        "source_separate", "authoring_separate", "corpus_separate", "infrastructure_separate",
        "prompt_control_separate", "input_selection_separate", "finding_selection_separate",
    )
    facts = ControlLineageFacts.create(**{name: facts_row.get(name) for name in fact_names})

    evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    evidence_id = sha256_id({
        "schema_version": "sergeant.sae150-external-evidence-identity.v1",
        "review_world_id": manifest["review_world_id"],
        "source_principal_id": str(submission["source_principal_id"]),
        "source_authority_generation": str(submission["source_authority_generation"]),
        "evidence_digest": evidence_digest,
    })

    verifier = load_verifier(authority_dir / "provenance-verifier-authorization.json")
    secret = (authority_dir / "provenance-verifier-secret.bin").read_bytes()
    proof = AuthenticatedProvenanceProof.issue(
        evidence_id=evidence_id,
        source_principal_id=str(submission["source_principal_id"]),
        source_authority_generation=str(submission["source_authority_generation"]),
        lineage_facts=facts,
        verifier_identity=verifier.verifier_identity,
        verifier_generation=verifier.verifier_generation,
        verification_secret=secret,
    )
    record = ExternalEvidenceProvenanceRecord.create(
        evidence_id=evidence_id,
        evidence_digest=evidence_digest,
        review_world_id=manifest["review_world_id"],
        source_principal_id=str(submission["source_principal_id"]),
        authenticated_source_provenance=str(submission["authenticated_source_provenance"]),
        source_organization=str(submission["source_organization"]),
        source_class=source_class,
        source_authority_generation=str(submission["source_authority_generation"]),
        creation_generation=str(submission["creation_generation"]),
        candidate_authoring_relationship=str(submission["candidate_authoring_relationship"]),
        qualification_corpus_relationship=str(submission["qualification_corpus_relationship"]),
        candidate_infrastructure_relationship=str(submission["candidate_infrastructure_relationship"]),
        reviewer_tool_lineage=str(submission["reviewer_tool_lineage"]),
        prompt_controller=str(submission["prompt_controller"]),
        input_selector=str(submission["input_selector"]),
        finding_selector=str(submission["finding_selector"]),
        provenance_verification_method="SAE-150 Owner/Root authenticated provenance verifier v1",
        control_lineage_facts=facts,
        provenance_authorization=verifier,
        authenticated_provenance_proof=proof,
        provenance_verification_secret=secret,
    )
    if not record.provenance_authenticated:
        raise ValueError("provenance authentication failed")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = evidence_id[:16]
    proof_path = output_dir / f"{stem}.authenticated-provenance-proof.json"
    eepr_path = output_dir / f"{stem}.eepr.json"
    binding_path = output_dir / f"{stem}.trusted-eepr-binding.json"
    proof_path.write_text(json.dumps(_proof_payload(proof), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    eepr_path.write_text(json.dumps(_eepr_payload(record), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    binding_path.write_text(json.dumps({
        "schema_version": "sergeant.sae150-trusted-eepr-binding.v1",
        "review_world_id": manifest["review_world_id"],
        "evidence_id": record.evidence_id,
        "eepr_id": record.eepr_id,
        "source_class": record.source_class,
        "independence_state": record.independence_state.value,
        "countable_for_genesis_lane": record.independence_state is IndependenceState.INDEPENDENT,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **frozen,
        "evidence_id": record.evidence_id,
        "eepr_id": record.eepr_id,
        "independence_state": record.independence_state.value,
        "countable_for_genesis_lane": record.independence_state is IndependenceState.INDEPENDENT,
        "proof_path": str(proof_path),
        "eepr_path": str(eepr_path),
        "binding_path": str(binding_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-dir", type=Path, default=DEFAULT_AUTHORITY_DIR)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    ing = sub.add_parser("ingest")
    ing.add_argument("--submission", type=Path, required=True)
    ing.add_argument("--evidence", type=Path, required=True)
    ing.add_argument("--output-dir", type=Path, required=True)
    ns = parser.parse_args(argv)
    if ns.command == "verify":
        result = validate_external_authority(ns.authority_dir)
    else:
        result = ingest(ns.submission, ns.evidence, ns.output_dir, ns.authority_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
