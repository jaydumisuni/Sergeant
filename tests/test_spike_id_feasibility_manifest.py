"""Mechanical proof for the reconciled SPIKE-ID feasibility candidate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/71-spike-id-feasibility-manifest.json"
DOC_PATH = ROOT / "docs/70-spike-id-identity-provenance-feasibility.md"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
SPIKE_ID_DIR = ROOT / "tests/spike_id"
NEGATIVE_PROOF_PATH = SPIKE_ID_DIR / "test_negative_proof_candidate_cannot_sign_as_issuer.py"
CURRENTNESS_PATH = SPIKE_ID_DIR / "test_replay_and_staleness_rejected.py"
FIXTURE_PATH = SPIKE_ID_DIR / "qualification_attestation_fixture.py"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_blob(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    return subprocess.check_output(
        ["git", "rev-parse", f"HEAD:{relative}"],
        cwd=ROOT,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def test_spike_id_manifest_binds_current_authority_and_fixture_artifacts() -> None:
    manifest = _load(MANIFEST_PATH)

    assert manifest["schema_version"] == "sergeant.spike-id-feasibility-manifest.v2"
    assert manifest["node"] == "SPIKE-ID"
    assert manifest["lifecycle_state"] == "CANDIDATE"
    assert manifest["proof_requires"] == ["SAE-00"]
    assert manifest["authority_gain"] == "none"
    assert manifest["disposition"]["qualified_for_sae30"] is False

    current_doc = manifest["current_document"]
    assert _tracked_blob(ROOT / current_doc["path"]) == current_doc["blob_sha"]

    for fixture in manifest["proof_fixtures"]:
        path = ROOT / fixture["path"]
        assert path.is_file(), fixture["path"]
        assert _tracked_blob(path) == fixture["blob_sha"], fixture["path"]
        assert fixture["assurance_evolution_runtime_implementation"] is False

    assert all(manifest["required_outputs"].values())


def test_spike_id_dependency_is_real_and_sae00_is_proven() -> None:
    manifest = _load(MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    roadmap = (ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md").read_text(encoding="utf-8")

    assert manifest["proof_requires"] == ["SAE-00"]
    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert "SPIKE-ID:" in roadmap
    dependency_section = roadmap.split("## 15. Dependency registry v1.1", 1)[1]
    assert "SPIKE-ID:\n  - SAE-00" in dependency_section


def test_spike_id_selected_mechanism_stays_feasibility_only() -> None:
    manifest = _load(MANIFEST_PATH)
    doc = DOC_PATH.read_text(encoding="utf-8")

    disposition = manifest["disposition"]
    assert disposition["outcome"] == "selected_initial_mechanism"
    assert disposition["no_safe_mechanism"] is False
    assert "sshsig" in disposition["selected_mechanism"]
    assert disposition["qualified_for_sae30"] is False

    prohibitions = set(manifest["prohibitions"])
    assert "do_not_treat_this_spike_as_sae30_implementation" in prohibitions
    assert "do_not_treat_selected_sshsig_mechanism_as_qualified_for_sae30" in prohibitions
    assert "do_not_treat_signature_authenticity_as_independence" in prohibitions
    assert "do_not_activate_partial_assurance_evolution_generation" in prohibitions

    assert "Authority gain: **none**" in doc
    assert "does not implement `SAE-30`" in doc


def test_spike_id_negative_proof_declarations_exist_in_real_file() -> None:
    manifest = _load(MANIFEST_PATH)
    negative = manifest["negative_proof"]
    source = NEGATIVE_PROOF_PATH.read_text(encoding="utf-8")

    assert Path(negative["path"]) == Path("tests/spike_id/test_negative_proof_candidate_cannot_sign_as_issuer.py")
    for test_name in negative["test_names"]:
        assert f"def {test_name}(" in source, test_name

    assert "registry" in negative["load_bearing_boundary"]
    assert "custody" in negative["load_bearing_boundary"]


def test_spike_id_exact_expiry_boundary_is_fail_closed() -> None:
    manifest = _load(MANIFEST_PATH)
    fixture_source = FIXTURE_PATH.read_text(encoding="utf-8")
    currentness_source = CURRENTNESS_PATH.read_text(encoding="utf-8")

    assert manifest["mechanism"]["expires_at_semantics"] == "exclusive_upper_bound_now_greater_than_or_equal_is_expired"
    assert "expired = now >= expires_at" in fixture_source
    assert "def test_attestation_is_rejected_at_exact_expiry_instant(" in currentness_source


def test_spike_id_fixture_suite_genuinely_passes_when_executed() -> None:
    """Execution is confirmation of the already-reviewed mechanism evidence."""
    assert shutil.which("ssh-keygen"), "SPIKE-ID requires OpenSSH ssh-keygen"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(SPIKE_ID_DIR)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout
    assert "11 passed" in result.stdout, result.stdout


def test_spike_id_known_gaps_remain_explicit() -> None:
    manifest = _load(MANIFEST_PATH)
    gaps = set(manifest["known_gaps"])

    assert "registry_and_revocation_list_distribution_custody_not_solved" in gaps
    assert "key_holder_loss_rotation_and_succession_protocol_undesigned" in gaps
    assert "no_real_qualification_authority_registry_exists" in gaps
    assert "no_real_qualification_issuer_key_is_created_or_stored_by_this_spike" in gaps
    assert "signature_authenticity_does_not_establish_external_independence" in gaps
