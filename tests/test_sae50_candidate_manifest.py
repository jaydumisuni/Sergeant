from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/99-sae50-total-closure-candidate-manifest.json"


def _blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_sae50_candidate_binds_proven_dependencies_and_exact_content() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["node"] == "SAE-50"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert set(manifest["proof_requires"]) == {"SAE-10", "SAE-20", "SAE-40"}
    for record in manifest["proven_dependency_records"]:
        payload = json.loads((ROOT / record).read_text(encoding="utf-8"))
        assert payload["lifecycle_state"] == "PROVEN"
    for path, expected in manifest["content_blobs"].items():
        assert _blob(ROOT / path) == expected
    assert manifest["produces_now"] == []
    assert manifest["produces_if_proven"] == ["QUALIFIED_SET_VALUED_CLOSURE_CORE"]
    assert manifest["normal_verdict_authority"] is False
    assert manifest["partial_generation_activation"] is False
