from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/105-sae60-proven-lifecycle-closeout-manifest.json"
CANDIDATE = ROOT / "docs/103-sae60-semantic-capability-candidate-manifest.json"
DOC = ROOT / "docs/104-sae60-proven-lifecycle-closeout.md"
CAMPAIGN = ROOT / "tests/test_sae60_qualification_campaign.py"
PROTOCOL = ROOT / "main_review/semantic_capability_protocol.py"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def blob(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def test_closeout_advances_only_the_frozen_sae60_authority() -> None:
    candidate = load(CANDIDATE)
    closeout = load(MANIFEST)

    assert candidate["node"] == closeout["node"] == "SAE-60"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert candidate["produces_now"] == []
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["produces"] == ["QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL"]
    assert closeout["bounded_qualified_capabilities"] == ["python.bounded-literal-dispatch.v1"]
    assert closeout["normal_verdict_authority"] is False
    assert closeout["genesis_activated"] is False
    assert closeout["dependent_nodes_auto_proven"] is False


def test_exact_candidate_and_guarded_merge_are_bound() -> None:
    closeout = load(MANIFEST)
    generation = closeout["candidate_generation"]
    merge = closeout["canonical_candidate_merge"]

    assert generation["pull_request"] == 194
    assert generation["head"] == "75c0b42ed3b6b29b62e4724c07f49ebaec836d05"
    assert generation["candidate_document_blob"] == "94af6650e08202dd675145d95b5b9122b0630519"
    assert generation["candidate_manifest_blob"] == "091919b30c67a433240f11580fb6ee8ddbc783db"

    assert merge["commit"] == "d0682886d2d4e6d8bc1a1a88055d294f11e40b17"
    assert merge["tree"] == "83899670d0062ace2d1da863b427dbd2f46c1950"
    assert merge["parents"] == [
        "8df705d3cc6237937a8ee0bde74d44481d352679",
        generation["head"],
    ]
    assert merge["exact_head_guard"] == generation["head"]


def test_candidate_content_blobs_remain_historical_and_unchanged() -> None:
    candidate = load(CANDIDATE)
    for path, expected in candidate["content_blobs"].items():
        assert blob(ROOT / path) == expected
    assert blob(ROOT / candidate["candidate_document"]) == candidate["candidate_document_blob"]
    assert blob(CANDIDATE) == "091919b30c67a433240f11580fb6ee8ddbc783db"


def test_qualification_hardening_generation_is_separately_bound() -> None:
    closeout = load(MANIFEST)
    hardening = closeout["qualification_hardening_generation"]

    assert hardening["head"] == "81c7291acc1eb7f4aa7812df2fa263be77f32e53"
    assert hardening["protocol_blob"] == blob(PROTOCOL)
    assert hardening["qualification_campaign_blob"] == blob(CAMPAIGN)
    assert hardening["discovery"] == "candidate analysis can measure later passport generations; qualified authority requires an exact-generation gate"
    assert hardening["evaluation_integrity_revalidated"] is True


def test_hardening_execution_confirmation_is_exact_head_and_green() -> None:
    proof = load(MANIFEST)["hardening_execution_confirmation"]
    assert proof["exact_head"] == "81c7291acc1eb7f4aa7812df2fa263be77f32e53"
    assert proof["ci_run_id"] == 34124129090
    assert proof["main_review_run_id"] == 34124129220
    assert proof["multiplatform_run_id"] == 34124129200
    assert proof["review_intelligence_run_id"] == 34124129189
    assert proof["reviewer_comparison_run_id"] == 34124129196
    assert proof["standalone_service_run_id"] == 34124129216
    assert proof["live_github_ingestion_run_id"] == 34124129151
    assert proof["final_static_transfer_holdout_run_id"] == 34124128976
    for key, value in proof.items():
        if key.endswith("_run_id") or key == "exact_head":
            continue
        assert value == "success"


def test_qualified_scope_is_exact_and_unknown_is_not_weakened() -> None:
    closeout = load(MANIFEST)
    scope = closeout["qualified_scope"]

    assert scope["domain_id"] == "python.bounded-literal-dispatch.v1"
    assert scope["domain_generation"] == "domain-gen-1"
    assert scope["artifact_generation"] == "sae60-candidate-gen-1"
    assert scope["parser_generation"] == "cpython-ast-3.11-v1"
    assert scope["framework_generation"] == "python-language-3.11"
    assert scope["qualification_protocol_generation"] == "sae60-qualification-v1"
    assert scope["proof_ceiling"] == "BOUNDED_EXHAUSTIVE_ORACLE"
    assert scope["closure_ceiling"] == "EXACT"
    assert scope["general_python_semantics_qualified"] is False
    assert scope["unknown_can_be_promoted_by_coverage_pressure"] is False


def test_closeout_artifacts_and_authority_boundary_are_content_bound() -> None:
    closeout = load(MANIFEST)
    assert blob(DOC) == closeout["closeout_document_blob"]
    assert blob(Path(__file__)) == closeout["closeout_test_blob"]
    assert blob(CAMPAIGN) == closeout["qualification_campaign_blob"]
    assert blob(PROTOCOL) == closeout["qualification_protocol_blob"]

    text = DOC.read_text(encoding="utf-8")
    assert "Status: **PROVEN**" in text
    assert "QUALIFIED_SEMANTIC_CAPABILITY_PROTOCOL" in text
    assert "python.bounded-literal-dispatch.v1" in text
    assert "does **not** qualify general Python call semantics" in text
    assert "does not activate Genesis" in text
