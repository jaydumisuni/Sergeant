from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/67-sae00-proven-lifecycle-closeout-manifest.json"
CANDIDATE_MANIFEST_PATH = ROOT / "docs/63-sae00-founding-authority-reference-manifest.json"
CLOSEOUT_DOC_PATH = ROOT / "docs/66-sae00-proven-lifecycle-closeout.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT
    ).strip()


def test_sae00_closeout_preserves_candidate_history_and_advances_new_generation() -> None:
    closeout = _load(MANIFEST_PATH)
    candidate = _load(CANDIDATE_MANIFEST_PATH)

    assert candidate["node"] == "SAE-00"
    assert candidate["lifecycle_state"] == "CANDIDATE"
    assert closeout["node"] == "SAE-00"
    assert closeout["lifecycle_state"] == "PROVEN"
    assert closeout["historical_candidate_state"] == "CANDIDATE"
    assert closeout["dependency_effect"]["sae00_proof_dependency_resolved"] is True
    assert closeout["dependency_effect"]["dependent_nodes_auto_qualified"] is False
    assert closeout["dependency_effect"]["dependent_nodes_auto_proven"] is False
    assert closeout["dependency_effect"]["partial_generation_activation_allowed"] is False


def test_sae00_closeout_binds_exact_reviewed_head_to_canonical_merge() -> None:
    closeout = _load(MANIFEST_PATH)
    merge_commit = closeout["canonical_merge_commit"]
    construction_head = closeout["construction_head"]

    _git("cat-file", "-e", f"{merge_commit}^{{commit}}")
    _git("cat-file", "-e", f"{construction_head}^{{commit}}")

    merge_parents = _git("show", "-s", "--format=%P", merge_commit).split()
    assert construction_head in merge_parents

    subprocess.check_call(
        ["git", "merge-base", "--is-ancestor", merge_commit, "HEAD"], cwd=ROOT
    )


def test_sae00_closeout_requires_explicit_owner_authorization_record() -> None:
    closeout = _load(MANIFEST_PATH)
    authorization = closeout["owner_authorization"]

    assert authorization["date"] == "2026-09-02"
    assert "finish Sergeant first" in authorization["disposition"]
    assert "Tenfold Gen 1" in authorization["disposition"]
    assert "no weakening" in authorization["scope"]


def test_sae00_closeout_document_matches_manifest_authority() -> None:
    closeout = _load(MANIFEST_PATH)
    text = CLOSEOUT_DOC_PATH.read_text(encoding="utf-8")

    assert "Status: **PROVEN**" in text
    assert closeout["construction_head"] in text
    assert closeout["canonical_merge_commit"] in text
    for authority in closeout["produces"]:
        assert authority in text
