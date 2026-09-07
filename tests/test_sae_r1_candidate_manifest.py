from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/95-sae-r1-rust-canonical-identity-candidate-manifest.json"


def _blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae_r1_candidate_binds_proven_dependencies_and_independent_implementations() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["node"] == "SAE-R1"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert set(manifest["proof_requires"]) == {"SAE-10", "SAE-20", "SAE-40"}
    for record in manifest["proven_dependency_records"]:
        assert json.loads((ROOT / record).read_text(encoding="utf-8"))["lifecycle_state"] == "PROVEN"
    for path, expected in manifest["content_blobs"].items():
        assert _blob(ROOT / path) == expected
    assert manifest["independence"] == {
        "shared_implementation": False,
        "shared_frozen_specification_vectors": True,
        "rust_third_party_dependencies": False,
        "python_and_rust_both_checked_against_exact_frozen_bytes": True,
    }
    assert manifest["hostile_review_findings_closed_by_candidate"] == [
        "both_encoders_checked_against_exact_frozen_bytes_and_ids"
    ]
    cargo = (ROOT / "rust/sergeant-assurance-identity/Cargo.toml").read_text(encoding="utf-8")
    assert cargo.strip().endswith("[dependencies]")
    rust = (ROOT / "rust/sergeant-assurance-identity/src/lib.rs").read_text(encoding="utf-8")
    assert "use pyo" not in rust.lower()
    assert "python" not in rust.lower().split("#[cfg(test)]", 1)[0]
    assert manifest["produces_now"] == []
    assert manifest["produces_if_proven"] == ["QUALIFIED_RUST_IDENTITY_FOUNDATION"]
