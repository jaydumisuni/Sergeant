from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/91-sae30-qualification-provenance-genesis-candidate-manifest.json"


def _blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae30_candidate_binds_proven_dependencies_and_exact_authority_surface() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["node"] == "SAE-30"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert set(manifest["proof_requires"]) == {"SAE-00", "SPIKE-ID", "SPIKE-EXT"}
    for record in manifest["proven_dependency_records"]:
        assert json.loads((ROOT / record).read_text(encoding="utf-8"))["lifecycle_state"] == "PROVEN"
    for path, expected in manifest["content_blobs"].items():
        assert _blob(ROOT / path) == expected
    assert manifest["produces_now"] == []
    assert manifest["normal_verdict_authority"] is False
    assert manifest["genesis_activation"] is False
    assert manifest["partial_generation_activation"] is False
    assert "attestation_provenance_and_independence_binding" in manifest["authority_properties"]
    assert "engineering_business_risk_separation" in manifest["authority_properties"]
