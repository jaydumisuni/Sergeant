from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/87-sae40-judge-assurance-ledger-candidate-manifest.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae40_manifest_binds_frozen_authority_and_proven_dependencies():
    manifest = _load(MANIFEST)
    assert manifest["node"] == "SAE-40"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["construction_base"] == "2a1d16f9772997d993d0f0d41e1c5161f222f136"
    assert manifest["proof_requires"] == ["SAE-10", "SAE-20"]
    for source in manifest["authority_sources"].values():
        path = ROOT / source["path"]
        assert path.is_file()
        assert _git_blob(path) == source["blob_sha"]

    sae10 = _load(ROOT / "docs/81-sae10-proven-lifecycle-closeout-manifest.json")
    sae20 = _load(ROOT / "docs/85-sae20-proven-lifecycle-closeout-manifest.json")
    assert sae10["lifecycle_state"] == "PROVEN"
    assert {"QUALIFIED_REVIEW_WORLD_CONTRACT", "QUALIFIED_RAB_CONTRACT"}.issubset(sae10["produces"])
    assert sae20["lifecycle_state"] == "PROVEN"
    assert "QUALIFIED_ACR_FOUNDATION" in sae20["produces"]


def test_sae40_manifest_binds_every_candidate_content_blob():
    manifest = _load(MANIFEST)
    expected = {
        "docs/86-sae40-judge-assurance-ledger-candidate.md",
        "docs/superpowers/specs/2026-09-06-sae-40-assurance-ledger-design.md",
        "docs/superpowers/plans/2026-09-06-sae-40-assurance-ledger.md",
        "main_review/assurance_ledger.py",
        "main_review/judge_assurance_adapter.py",
        "tests/test_assurance_ledger.py",
        "tests/test_judge_assurance_adapter.py",
        "tests/test_sae40_assurance_ledger_candidate_manifest.py",
    }
    assert set(manifest["content_blobs"]) == expected
    for relative, expected_blob in manifest["content_blobs"].items():
        path = ROOT / relative
        assert path.is_file()
        assert _git_blob(path) == expected_blob


def test_sae40_manifest_preserves_judge_and_verdict_authority_boundary():
    manifest = _load(MANIFEST)
    boundary = manifest["authority_boundary"]
    assert boundary == {
        "normal_sergeant_verdict_authority_changed": False,
        "second_judge_created": False,
        "sae30_general_qualification_authority_fabricated": False,
        "eepr_independence_claimed": False,
        "genesis_activated": False,
        "partial_generation_activation_allowed": False,
        "dependent_nodes_auto_qualified": False,
        "dependent_nodes_auto_proven": False,
    }
    assert manifest["produces_now"] == []
    assert manifest["produces_if_proven"] == ["QUALIFIED_ASSURANCE_LEDGER"]

    adapter = (ROOT / "main_review/judge_assurance_adapter.py").read_text(encoding="utf-8")
    core = (ROOT / "main_review/assurance_ledger.py").read_text(encoding="utf-8")
    assert "from .verdict" not in adapter
    assert "from .verdict" not in core
    assert "run_officer_council" not in adapter
    assert "run_officer_council" not in core
    assert "def build_judge_assurance_ledger" in adapter
    assert '"authority": "existing-sergeant-judge-and-verdict-path"' in adapter


def test_sae40_manifest_covers_all_founding_record_families_and_monotonic_laws():
    manifest = _load(MANIFEST)
    assert set(manifest["record_families"]) == {
        "review_world", "acr_evaluation", "collection_closure", "contract_instance", "claim",
        "obligation", "assumption", "evidence", "falsifier_instance", "contradiction",
        "qualification_evidence", "admission", "invalidation", "verdict_lineage",
    }
    laws = manifest["monotonic_laws"]
    assert laws["unknown_conserved"] is True
    assert laws["contradiction_conserved"] is True
    assert laws["required_multiplicity_conserved_by_occurrence"] is True
    assert laws["scope_bound_to_record_identity"] is True
    assert laws["legacy_finding_id_is_presentation_only"] is True
    assert laws["dangling_related_record_ids_rejected"] is True
    assert laws["cross_review_world_merge_rejected"] is True
    assert laws["cross_rab_merge_rejected"] is True
    assert laws["implicit_latest_authority_substitution_allowed"] is False


def test_sae40_frozen_roadmap_still_requires_only_sae10_and_sae20():
    roadmap = (ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md").read_text(encoding="utf-8")
    start = roadmap.index("### SAE-40 — Judge Assurance Ledger + authority-bearing identity")
    section = roadmap[start:roadmap.index("## 8. Rust identity foundation", start)]
    assert "**Proof requires:** `SAE-10`, `SAE-20`." in section
    assert "Positive proof uses full cryptographic instance identity." in section
    assert "dedup cannot erase multiplicity, UNKNOWN, contradiction or scope" in section


def test_sae40_candidate_document_and_manifest_are_not_self_qualification():
    manifest = _load(MANIFEST)
    document = (ROOT / "docs/86-sae40-judge-assurance-ledger-candidate.md").read_text(encoding="utf-8")
    assert "Status: **CANDIDATE ONLY**" in document
    assert "produces **no authority now**" in document
    assert manifest["local_construction_proof"]["repository_wide_proof_claimed"] is False
    assert manifest["qualification_boundary"]["candidate_self_qualification_allowed"] is False
    assert manifest["qualification_boundary"]["local_tests_equal_qualification"] is False
