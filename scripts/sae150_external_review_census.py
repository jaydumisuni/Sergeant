#!/usr/bin/env python3
"""Re-verify ingested SAE-150 external evidence and derive the Genesis review census."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main_review.external_evidence_provenance import (
    AuthenticatedProvenanceProof,
    ControlLineageFacts,
    ExternalEvidenceProvenanceRecord,
    ExternalReviewLaneRequirement,
    IndependenceState,
    evaluate_external_review_census,
)
from scripts.sae150_external_review_intake import (
    ACCEPTED_SOURCE_CLASSES,
    DEFAULT_AUTHORITY_DIR,
    MANIFEST_PATH,
    load_json,
    load_verifier,
    validate_external_authority,
)

DEFAULT_EVIDENCE_SUBDIR = "external-evidence"


def _proof_from_payload(row: dict) -> AuthenticatedProvenanceProof:
    return AuthenticatedProvenanceProof(
        schema_version=str(row["schema_version"]),
        evidence_id=str(row["evidence_id"]),
        source_principal_id=str(row["source_principal_id"]),
        source_authority_generation=str(row["source_authority_generation"]),
        lineage_id=str(row["lineage_id"]),
        verifier_identity=str(row["verifier_identity"]),
        verifier_generation=str(row["verifier_generation"]),
        mac=str(row["mac"]),
    )


def _record_from_payload(row: dict, *, verifier, secret: bytes, proof: AuthenticatedProvenanceProof) -> ExternalEvidenceProvenanceRecord:
    facts_row = row.get("control_lineage_facts")
    if not isinstance(facts_row, dict):
        raise ValueError("EEPR control_lineage_facts must be an object")
    facts = ControlLineageFacts.create(
        source_separate=facts_row.get("source_separate"),
        authoring_separate=facts_row.get("authoring_separate"),
        corpus_separate=facts_row.get("corpus_separate"),
        infrastructure_separate=facts_row.get("infrastructure_separate"),
        prompt_control_separate=facts_row.get("prompt_control_separate"),
        input_selection_separate=facts_row.get("input_selection_separate"),
        finding_selection_separate=facts_row.get("finding_selection_separate"),
    )
    record = ExternalEvidenceProvenanceRecord.create(
        evidence_id=str(row["evidence_id"]),
        evidence_digest=str(row["evidence_digest"]),
        review_world_id=str(row["review_world_id"]),
        source_principal_id=str(row["source_principal_id"]),
        authenticated_source_provenance=str(row["authenticated_source_provenance"]),
        source_organization=str(row["source_organization"]),
        source_class=str(row["source_class"]),
        source_authority_generation=str(row["source_authority_generation"]),
        creation_generation=str(row["creation_generation"]),
        candidate_authoring_relationship=str(row["candidate_authoring_relationship"]),
        qualification_corpus_relationship=str(row["qualification_corpus_relationship"]),
        candidate_infrastructure_relationship=str(row["candidate_infrastructure_relationship"]),
        reviewer_tool_lineage=str(row["reviewer_tool_lineage"]),
        prompt_controller=str(row["prompt_controller"]),
        input_selector=str(row["input_selector"]),
        finding_selector=str(row["finding_selector"]),
        provenance_verification_method=str(row["provenance_verification_method"]),
        control_lineage_facts=facts,
        provenance_authorization=verifier,
        authenticated_provenance_proof=proof,
        provenance_verification_secret=secret,
    )
    if record.eepr_id != str(row["eepr_id"]):
        raise ValueError("EEPR identity mismatch after canonical re-derivation")
    if record.independence_state.value != str(row["independence_state"]):
        raise ValueError("EEPR independence state mismatch after canonical re-derivation")
    if bool(row["provenance_authenticated"]) is not record.provenance_authenticated:
        raise ValueError("EEPR provenance authentication state mismatch")
    return record


def load_verified_records(authority_dir: Path, evidence_dir: Path) -> tuple[ExternalEvidenceProvenanceRecord, ...]:
    validate_external_authority(authority_dir)
    verifier = load_verifier(authority_dir / "provenance-verifier-authorization.json")
    secret = (authority_dir / "provenance-verifier-secret.bin").read_bytes()
    manifest = load_json(MANIFEST_PATH)
    records: list[ExternalEvidenceProvenanceRecord] = []

    for eepr_path in sorted(evidence_dir.glob("*.eepr.json")):
        stem = eepr_path.name.removesuffix(".eepr.json")
        proof_path = evidence_dir / f"{stem}.authenticated-provenance-proof.json"
        binding_path = evidence_dir / f"{stem}.trusted-eepr-binding.json"
        if not proof_path.is_file() or not binding_path.is_file():
            raise ValueError(f"incomplete external evidence triplet for {stem}")

        row = load_json(eepr_path)
        proof = _proof_from_payload(load_json(proof_path))
        record = _record_from_payload(row, verifier=verifier, secret=secret, proof=proof)
        binding = load_json(binding_path)

        if record.review_world_id != manifest["review_world_id"]:
            raise ValueError(f"external evidence {record.evidence_id} targets another Review World")
        if record.source_class not in ACCEPTED_SOURCE_CLASSES:
            raise ValueError(f"external evidence {record.evidence_id} has unaccepted source class {record.source_class}")
        if binding.get("review_world_id") != record.review_world_id:
            raise ValueError("trusted binding Review World mismatch")
        if binding.get("evidence_id") != record.evidence_id or binding.get("eepr_id") != record.eepr_id:
            raise ValueError("trusted binding identity mismatch")
        expected_countable = record.independence_state is IndependenceState.INDEPENDENT
        if bool(binding.get("countable_for_genesis_lane")) is not expected_countable:
            raise ValueError("trusted binding countability mismatch")

        records.append(record)

    return tuple(records)


def derive_census(records: tuple[ExternalEvidenceProvenanceRecord, ...]):
    manifest = load_json(MANIFEST_PATH)
    lane = manifest["review_lane"]
    requirement = ExternalReviewLaneRequirement.create(
        lane_id=str(lane["lane_id"]),
        minimum_instances=int(lane["minimum_instances"]),
        minimum_source_classes=int(lane["minimum_distinct_source_classes"]),
    )
    return evaluate_external_review_census(records=records, requirements=(requirement,))


def census_payload(census, records) -> dict:
    by_id = {record.evidence_id: record for record in records}
    return {
        "schema_version": "sergeant.sae150-external-review-census-status.v1",
        "census_id": census.census_id,
        "satisfied": census.satisfied,
        "evidence_count": len(census.evidence_ids),
        "eligible_independent_count": len(census.eligible_independent_evidence_ids),
        "eligible_source_classes": sorted({
            by_id[evidence_id].source_class
            for evidence_id in census.eligible_independent_evidence_ids
        }),
        "evidence": [
            {
                "evidence_id": record.evidence_id,
                "eepr_id": record.eepr_id,
                "source_class": record.source_class,
                "independence_state": record.independence_state.value,
                "provenance_authenticated": record.provenance_authenticated,
                "counted": record.evidence_id in set(census.eligible_independent_evidence_ids),
            }
            for record in sorted(records, key=lambda value: value.evidence_id)
        ],
        "lanes": [
            {
                "lane_id": lane.lane_id,
                "independent_instances": lane.independent_instances,
                "source_classes": list(lane.source_classes),
                "satisfied": lane.satisfied,
            }
            for lane in census.lanes
        ],
        "remaining_blocker": None if census.satisfied else "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-dir", type=Path, default=DEFAULT_AUTHORITY_DIR)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--require-satisfied", action="store_true")
    ns = parser.parse_args(argv)

    evidence_dir = ns.evidence_dir or (ns.authority_dir / DEFAULT_EVIDENCE_SUBDIR)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    records = load_verified_records(ns.authority_dir, evidence_dir)
    census = derive_census(records)
    payload = census_payload(census, records)

    status_path = ns.authority_dir / "external-review-census.json"
    status_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({**payload, "status_path": str(status_path)}, indent=2, sort_keys=True))
    if ns.require_satisfied and not census.satisfied:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
