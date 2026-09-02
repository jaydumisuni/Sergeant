"""Mechanical proof for the SPIKE-ID feasibility manifest.

Mirrors the structural precedent set by
`tests/test_assurance_evolution_roadmap_freeze.py`: a hash-bound JSON
manifest (`docs/65-spike-id-feasibility-manifest.json`) plus a pytest file
that re-checks it against live repository content, not asserted prose.

One deliberate deviation from that precedent: blob hashes here are computed
via `git hash-object` (a real subprocess call into git) rather than by
hashing raw working-tree bytes. `docs/62-sae00-founding-authority-and-
preservation-reference.md` section 4.4/5 documents that the raw-byte
approach is fragile on a Windows checkout with `core.autocrlf=true` (it can
report a false blob-hash mismatch for a file whose actual git-tracked
content is unchanged). Using `git hash-object` instead asks git itself what
the blob hash is, which matches what `git show`/`git cat-file` would report
regardless of local line-ending checkout behavior, and avoids reproducing
that known fragility class in this newly-written file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/65-spike-id-feasibility-manifest.json"
NEGATIVE_PROOF_PATH = ROOT / "tests/spike_id/test_negative_proof_candidate_cannot_sign_as_issuer.py"
SPIKE_ID_DIR = ROOT / "tests/spike_id"


def _git_blob_sha(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_spike_id_manifest_binds_authority_and_fixture_documents() -> None:
    manifest = _load_manifest()

    assert manifest["schema_version"] == "sergeant.spike-id-feasibility-manifest.v1"
    assert manifest["node"] == "SPIKE-ID"
    assert manifest["proof_requires"] == ["SAE-00"]
    assert manifest["authority_gain"] == "none"

    for document in manifest["documents"]:
        path = ROOT / document["path"]
        assert path.is_file(), document["path"]
        assert _git_blob_sha(path) == document["blob_sha"], document["path"]

    for fixture in manifest["proof_fixtures"]:
        path = ROOT / fixture["path"]
        assert path.is_file(), fixture["path"]
        assert _git_blob_sha(path) == fixture["blob_sha"], fixture["path"]
        assert fixture["assurance_evolution_runtime_implementation"] is False

    disposition = manifest["disposition"]
    assert disposition["outcome"] == "selected_initial_mechanism"
    assert disposition["no_safe_mechanism"] is False
    assert disposition["selected_mechanism"]

    prohibitions = set(manifest["prohibitions"])
    assert "do_not_treat_this_spike_as_sae30_implementation" in prohibitions
    assert "do_not_grant_normal_sergeant_verdict_authority_from_this_spike" in prohibitions
    assert "do_not_retrofit_pr_167" in prohibitions


def test_spike_id_negative_proof_file_actually_contains_its_declared_tests() -> None:
    """Confirm the manifest's negative_proof.test_names are real function
    definitions in the real file, not names that only exist in the
    manifest's own prose."""

    manifest = _load_manifest()
    negative_proof = manifest["negative_proof"]
    declared_path = ROOT / negative_proof["path"]
    assert declared_path == NEGATIVE_PROOF_PATH

    source = declared_path.read_text(encoding="utf-8")
    for test_name in negative_proof["test_names"]:
        assert f"def {test_name}(" in source, test_name


def test_spike_id_fixture_suite_genuinely_passes() -> None:
    """Mechanically execute the real SPIKE-ID fixture suite as a real
    pytest subprocess and require a real zero exit code -- not an
    assumption that files existing implies they pass."""

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(SPIKE_ID_DIR)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout
    assert "failed" not in result.stdout.lower(), result.stdout
    assert "passed" in result.stdout.lower(), result.stdout


def test_spike_id_negative_proof_subset_genuinely_passes_in_isolation() -> None:
    """Same mechanical-execution proof, narrowed to just the negative-proof
    file, so a reader does not have to trust that it passing is merely
    incidental to the whole spike_id suite passing."""

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(NEGATIVE_PROOF_PATH)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout
    assert "4 passed" in result.stdout, result.stdout
