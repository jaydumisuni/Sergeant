import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/163-sae150-cog-formula-adaptive-successor-sidecar-manifest.json"
SIM = ROOT / "docs/evidence/sae150-cog-formula-successor-portable-simulation.py"

def load_manifest():
    return json.loads(MANIFEST.read_text())

def test_sidecar_is_non_authoritative_and_keeps_genesis_blocker():
    m = load_manifest()
    assert m["lifecycle_state"] == "SIDE_CAR_DESIGN_CANDIDATE"
    assert m["authority_gain"] == "none"
    assert m["merge_authorized"] is False
    assert m["genesis_activated"] is False
    assert m["normal_verdict_authority"] is False
    assert m["mandatory_external_blocker"] == "MISSING_MATERIALLY_INDEPENDENT_EXTERNAL_EVIDENCE"

def test_sidecar_binds_exact_current_sae150_and_stale_cog_generation():
    m = load_manifest()
    assert m["base_sae150"]["head"] == "ddf1b8b63680e124654fc6f0f541a3326c8f03c7"
    assert m["cog_formula"]["bound_srg_head"] == "3a19dffe398b2b2499383782b9c89684acf25d68"
    assert m["cog_formula"]["current_binding"] is False
    assert m["cog_formula"]["qualification_state"] == "SHADOW"

def test_rollout_preserves_separated_authority():
    m = load_manifest()
    rows = {row["step"]: row["authority"] for row in m["rollout"]}
    assert rows["advanced_formula_search"] == "recommendation_only_shadow"
    assert rows["cookpit_generation_ledger"] == "read_only_evidence"
    assert rows["sae140_learning_bridge"] == "proposal_only"
    assert rows["adaptive_tenfold"] == "tenfold_retains_dispatch_authority"
    assert rows["optional_external_donors"] == "lineage_bound_non_authoritative"

def test_portable_simulation_reproduces_expected_structural_shape():
    result = subprocess.run([sys.executable, str(SIM)], capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    assert payload["model_note"].startswith("Ordinal structural")
    rollout = payload["rollout"]
    assert [row["step"] for row in rollout] == [
        "advanced_formula_search",
        "cookpit_generation_ledger",
        "learning_bridge",
        "adaptive_tenfold",
        "optional_donors",
    ]
    assert rollout[0]["attack_coverage"] == 11
    assert rollout[1]["attack_coverage"] == 13
    assert rollout[2]["attack_coverage"] == 15
    assert rollout[3]["attack_coverage"] == 15
    assert rollout[4]["attack_coverage"] == 16
    assert payload["owned_without_donors"]["attack_coverage"]["count"] == 15
    assert payload["full_with_optional_donors"]["attack_coverage"]["count"] == 16

def test_formula_runtime_source_is_bound_as_p0_skeleton_evidence():
    m = load_manifest()
    assert m["sources"]["formula"]["blobs"]["engine_runtime"] == "b27f94ec970c0b400272c12d40dcb97859248d00"
    assert "P0 skeleton" in m["sources"]["formula"]["finding"]

def test_cookpit_ledger_is_reused_not_reimplemented():
    m = load_manifest()
    assert m["sources"]["cookpit"]["blobs"]["metrics"] == "7144bee681c5a6d4a0da9aa839676cd8c778fa7e"
    assert "should be reused" in m["sources"]["cookpit"]["finding"]
