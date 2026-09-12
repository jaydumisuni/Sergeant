"""Fail-closed SAE-150 integrated Genesis qualification package assembly."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from typing import Any

REQUIRED_NODES=("SAE-100","SAE-110","SAE-120","SAE-130A","SAE-130B","SAE-130C","SAE-130D","SAE-130E","SAE-140","SPIKE-EXT")
REQUIRED_MUTATIONS=("omission","undercount","cardinality","acr","material_input","falsifier","authority","common_mode")
REQUIRED_BOOLEAN_PROOFS=("preservation_proof","model_blackout_proof","cpu_proof","historical_replay","clean_controls","unrelated_transfer","eepr_complete","external_review_instance_census_complete")

class GenesisQualificationError(ValueError):
    """Raised when mandatory Genesis package structure is absent or malformed."""

def _text(value: object) -> str:
    return "" if value is None else str(value).strip()

def _independent_lane(rows: Sequence[Mapping[str, Any]]) -> bool:
    for raw in rows:
        row=dict(raw)
        if (row.get("authenticated") is True and row.get("materially_independent") is True
            and row.get("owner_controlled") is False and _text(row.get("source_id"))
            and _text(row.get("evidence_digest"))):
            return True
    return False

def qualify_genesis_package(package: Mapping[str, Any]) -> dict[str, Any]:
    row=dict(package)
    for field in ("candidate_generation","rab_generation","acr_generation","rust_generation"):
        if not _text(row.get(field)):
            raise GenesisQualificationError(f"{field} is required")
    nodes=dict(row.get("required_proven_nodes") or {})
    if set(nodes) != set(REQUIRED_NODES) or any(not _text(nodes.get(node)) for node in REQUIRED_NODES):
        raise GenesisQualificationError("all canonical SAE-150 prerequisite generations are required")
    for field in REQUIRED_BOOLEAN_PROOFS:
        if row.get(field) is not True:
            raise GenesisQualificationError(f"{field} is required")
    mutations=dict(row.get("mutation_families") or {})
    if set(mutations) != set(REQUIRED_MUTATIONS) or any(mutations.get(name) is not True for name in REQUIRED_MUTATIONS):
        raise GenesisQualificationError("all required mutation families must survive qualification")
    evidence=list(row.get("external_evidence") or [])
    blockers=[]
    if not _independent_lane(evidence):
        blockers.append("MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE")
    unknowns=[_text(x) for x in (row.get("residual_unknowns") or []) if _text(x)]
    if any(x.lower().startswith("mandatory:") for x in unknowns):
        blockers.append("MANDATORY_UNKNOWN")
    qualified=not blockers
    return {
        "qualified":qualified,
        "state":"GENESIS_QUALIFICATION_PACKAGE_CANDIDATE" if qualified else "GENESIS_PROVISIONAL",
        "blockers":blockers,
        "required_nodes":list(REQUIRED_NODES),
        "mutation_families":list(REQUIRED_MUTATIONS),
        "external_evidence_count":len(evidence),
        "residual_unknowns":unknowns,
        "authority_gain":[],
        "normal_verdict_authority":False,
        "activation_authorized":False,
    }
