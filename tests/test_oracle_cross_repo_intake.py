from __future__ import annotations

import json
from pathlib import Path

from main_review.cross_repo_learning import classify_signal
from main_review.self_learning_queue import add_case, new_queue
from scripts.collect_github_learning_candidates import _signal_candidates
from scripts.run_project_driven_learning import _candidate_packet


ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / ".github" / "self-learning" / "signals"
ORACLE_SIGNAL = SIGNALS / "oracle-oidc-workflow-identity-2026-08-17.json"
CHECKOUT_SIGNAL = SIGNALS / "tgcheckm8-checkout-credential-boundary-2026-07-23.json"
CHECKSUM_SIGNAL = SIGNALS / "tgcheckm8-checksum-path-namespace-2026-07-23.json"
SOURCES = ROOT / ".github" / "self-learning" / "cross-repository-sources.json"
ROUND = ROOT / ".github" / "self-learning" / "project-driven" / "oracle-oidc-workflow-round-1.json"


def test_oracle_oidc_workflow_identity_signal_is_candidate_ready_but_unpromoted() -> None:
    signal = json.loads(ORACLE_SIGNAL.read_text(encoding="utf-8"))
    result = classify_signal(signal)

    assert result["disposition"] == "candidate_ready"
    assert result["triage_private_count"] == 30
    assert result["authority"] == {
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }

    candidate = result["candidate"]
    assert candidate["case_id"] == "learn-oracle-oidc-workflow-identity-20260817"
    assert candidate["repository"] == "jaydumisuni/Oracle-"
    assert candidate["source_pr"] == 150
    assert candidate["defective_ref"] == "1439f05f6ff3b540d19acadd26f39641ae9a654a"
    assert candidate["fixing_ref"] == "234c1e98af529973b946fa338602bc576164bc44"
    assert candidate["language"] == "typescript"
    assert candidate["scored_paths"] == ["src/live-oidc-auth.ts"]
    assert candidate["private_count"] == 30
    assert candidate["cross_repository"] is True
    assert signal["learning_state"] == "collected"
    assert signal["accepted_lesson"] is False

    queue = new_queue(
        "oracle-oidc-workflow-intake",
        authority_head="e" * 40,
        target_branch="learning/oracle-oidc-workflow-intake",
    )
    case = add_case(queue, candidate)
    assert case["state"] == "collected"
    assert queue["authority"]["may_auto_promote"] is False
    assert queue["authority"]["may_auto_merge"] is False


def test_direct_collector_excludes_completed_pr159_signals_and_keeps_oracle(tmp_path: Path) -> None:
    signals = tmp_path / "signals"
    signals.mkdir()
    for source in (CHECKOUT_SIGNAL, CHECKSUM_SIGNAL, ORACLE_SIGNAL):
        (signals / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    candidates = _signal_candidates(signals)

    assert [row["case_id"] for row in candidates] == [
        "learn-oracle-oidc-workflow-identity-20260817",
    ]
    assert candidates[0]["direct_event_candidate"] is True
    assert candidates[0]["provenance_complete"] is True
    assert candidates[0]["security_or_integrity"] is True


def test_oracle_project_round_binds_only_the_new_candidate() -> None:
    manifest = json.loads(ROUND.read_text(encoding="utf-8"))
    packet = _candidate_packet(ROUND, "e" * 40)

    assert manifest["round_id"] == "project-oracle-oidc-workflow-20260818"
    assert manifest["candidate_count"] == 1
    assert manifest["signal_paths"] == [
        ".github/self-learning/signals/oracle-oidc-workflow-identity-2026-08-17.json"
    ]
    assert manifest["expected_case_ids"] == [
        "learn-oracle-oidc-workflow-identity-20260817"
    ]
    assert manifest["authority"] == {
        "execution_lane": "oracle-direct-terminal",
        "direct_terminal_authorization_flag": "--owner-authorized",
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }
    assert packet["candidate_count"] == 1
    assert packet["candidates"][0]["case_id"] == "learn-oracle-oidc-workflow-identity-20260817"
    assert packet["reviewer_frozen_before_collection"] == "e" * 40


def test_pr159_signal_terminal_states_are_durable() -> None:
    checksum = json.loads(CHECKSUM_SIGNAL.read_text(encoding="utf-8"))
    checkout = json.loads(CHECKOUT_SIGNAL.read_text(encoding="utf-8"))

    assert checksum["learning_state"] == "accepted"
    assert checksum["accepted_lesson"] is True
    assert checksum["accepted_lesson_path"] == (
        ".github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json"
    )
    assert checkout["learning_state"] == "rejected"
    assert checkout["accepted_lesson"] is False
    assert "Defender rejected" in checkout["rejection_reason"]


def test_oracle_is_registered_as_confirmed_thetechguy_signal_source() -> None:
    registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    row = next(
        item
        for item in registry["confirmed_sources"]
        if item["repository"] == "jaydumisuni/Oracle-"
    )

    assert row["source_class"] == "thetechguy-owned"
    assert "typescript" in row["languages"]
    assert "repair" in row["event_types"]
    assert row["collection_state"] == "enabled-for-signal-intake"
    assert row["learning_boundary"] == "behavioral defect/fix lineage required"
    assert registry["policy"]["automatic_promotions"] == 0
    assert registry["policy"]["automatic_merges"] == 0
