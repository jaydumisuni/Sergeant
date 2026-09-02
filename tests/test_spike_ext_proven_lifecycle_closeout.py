from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT_MANIFEST_PATH = ROOT / "docs/69-spike-ext-proven-lifecycle-closeout-manifest.json"
HISTORICAL_MANIFEST_PATH = ROOT / "docs/65-spike-ext-external-review-sourcing-feasibility-manifest.json"
SAE00_MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
CLOSEOUT_DOC_PATH = ROOT / "docs/68-spike-ext-proven-lifecycle-closeout.md"
HISTORICAL_HEAD = "e6b7c2d8e92a2028d84ef955a608532a1ddb1e60"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def _current_blob(path: Path) -> str:
    return _git("hash-object", str(path))


def _blob_at(ref: str, path: str) -> str:
    return _git("rev-parse", f"{ref}:{path}")


def test_spike_ext_closeout_advances_new_generation_without_rewriting_candidate() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    historical = _load(HISTORICAL_MANIFEST_PATH)

    assert historical["node"] == "SPIKE-EXT"
    assert historical["lifecycle_state"] == "CANDIDATE"
    assert closeout["node"] == "SPIKE-EXT"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["authority_gain"] == "none"
    assert closeout["proof_requires"] == ["SAE-00"]
    assert all(closeout["required_outputs"].values())


def test_spike_ext_closeout_binds_reviewed_candidate_and_exact_transplant() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    historical = closeout["historical_candidate"]
    reconciliation = closeout["reconciliation"]

    _git("cat-file", "-e", f"{historical['head']}^{{commit}}")
    _git("cat-file", "-e", f"{reconciliation['transplant_commit']}^{{commit}}")

    assert _blob_at(HISTORICAL_HEAD, historical["document"]) == historical["document_blob_sha"]
    assert _blob_at(HISTORICAL_HEAD, historical["manifest"]) == historical["manifest_blob_sha"]
    assert _current_blob(ROOT / historical["document"]) == historical["document_blob_sha"]
    assert _current_blob(ROOT / historical["manifest"]) == historical["manifest_blob_sha"]
    assert reconciliation["reviewed_candidate_blobs_transplanted_unchanged"] is True

    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", reconciliation["transplant_commit"], "HEAD"], cwd=ROOT
    )


def test_spike_ext_closeout_requires_proven_sae00_roadmap_execution_authority() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    sae00 = _load(SAE00_MANIFEST_PATH)
    authority = closeout["sae00_proven_authority"]

    assert sae00["node"] == "SAE-00"
    assert sae00["lifecycle_state"] == "PROVEN"
    assert authority["required_output"] == "ROADMAP_EXECUTION_AUTHORITY"
    assert authority["required_output"] in sae00["produces"]
    assert _current_blob(ROOT / authority["closeout_document"]) == authority["closeout_document_blob_sha"]
    assert _current_blob(ROOT / authority["closeout_manifest"]) == authority["closeout_manifest_blob_sha"]


def test_spike_ext_bootstrap_authority_is_bounded_and_cannot_fake_independence() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    bootstrap = closeout["bootstrap_authority"]

    assert bootstrap["kind"] == "SAE00_ROADMAP_EXECUTION_PLUS_OWNER_ROOT_CONSTITUTIONAL_TCB"
    assert "SAE-30" in bootstrap["necessity"]
    assert "circularity" in bootstrap["necessity"]
    assert bootstrap["not_general_qualification_authority"] is True
    assert bootstrap["cannot_qualify_other_nodes"] is True
    assert bootstrap["cannot_declare_independence"] is True
    assert bootstrap["cannot_satisfy_genesis_external_lane"] is True
    assert bootstrap["cannot_convert_business_risk_to_pass"] is True
    assert bootstrap["partial_generation_activation_allowed"] is False


def test_spike_ext_proven_means_feasibility_not_external_lane_availability() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)
    sourcing = closeout["sourcing_disposition"]
    dependency = closeout["dependency_effect"]
    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")

    assert sourcing["status"] == "OPEN_GAP"
    assert sourcing["real_independent_lane_established"] is False
    assert sourcing["fresh_live_recheck_required_before_future_reliance"] is True
    assert sourcing["genesis_external_lane_satisfied"] is False
    assert dependency["spike_ext_proof_dependency_resolved"] is True
    assert dependency["sae30_still_requires_spike_id"] is True
    assert dependency["sae30_auto_qualified"] is False
    assert dependency["sae30_auto_proven"] is False
    assert dependency["genesis_auto_unblocked"] is False
    assert "EXTERNAL-LANE SOURCING REMAINS OPEN" in text
    assert "No real external reviewer was contacted" in text


def test_spike_ext_closeout_artifacts_are_content_bound() -> None:
    closeout = _load(CLOSEOUT_MANIFEST_PATH)

    closeout_doc = closeout["closeout_document"]
    assert _current_blob(ROOT / closeout_doc["path"]) == closeout_doc["blob_sha"]

    reconciliation = closeout["reconciliation"]
    assert _current_blob(ROOT / reconciliation["reconciliation_proof_fixture"]) == reconciliation["reconciliation_proof_fixture_blob_sha"]

    proof = closeout["proof_fixture"]
    assert _current_blob(ROOT / proof["path"]) == proof["blob_sha"]
