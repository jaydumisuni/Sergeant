from __future__ import annotations

import json
from pathlib import Path

import pytest

from main_review.cross_repo_learning import classify_signal
from scripts.collect_github_learning_candidates import _signal_candidates
from scripts.run_project_driven_learning import _candidate_packet


ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / ".github" / "self-learning" / "signals"
ORACLE_SIGNAL = SIGNALS / "oracle-oidc-workflow-identity-2026-08-17.json"
ORACLE_SIGNIN_SIGNAL = SIGNALS / "oracle-native-browser-signin-boundary-2026-08-18.json"
ORACLE_UPDATE_SIGNAL = SIGNALS / "oracle-extension-update-install-authority-2026-08-18.json"
CHECKOUT_SIGNAL = SIGNALS / "tgcheckm8-checkout-credential-boundary-2026-07-23.json"
CHECKSUM_SIGNAL = SIGNALS / "tgcheckm8-checksum-path-namespace-2026-07-23.json"
SOURCES = ROOT / ".github" / "self-learning" / "cross-repository-sources.json"
ROUND = ROOT / ".github" / "self-learning" / "project-driven" / "oracle-oidc-workflow-round-1.json"
BROWSER_ROUND = ROOT / ".github" / "self-learning" / "project-driven" / "oracle-browser-repairs-round-2.json"
RESULT = ROOT / ".github" / "self-learning" / "results" / "project-oracle-oidc-workflow-20260818.json"


def test_oracle_oidc_signal_is_terminally_rejected_without_erasing_source_quality() -> None:
    signal = json.loads(ORACLE_SIGNAL.read_text(encoding="utf-8"))
    classified = classify_signal(signal)

    # Classification proves the source defect/fix lineage remains useful evidence.
    assert classified["disposition"] == "candidate_ready"
    candidate = classified["candidate"]
    assert candidate["case_id"] == "learn-oracle-oidc-workflow-identity-20260817"
    assert candidate["repository"] == "jaydumisuni/Oracle-"
    assert candidate["source_pr"] == 150
    assert candidate["defective_ref"] == "1439f05f6ff3b540d19acadd26f39641ae9a654a"
    assert candidate["fixing_ref"] == "234c1e98af529973b946fa338602bc576164bc44"
    assert candidate["language"] == "typescript"
    assert candidate["scored_paths"] == ["src/live-oidc-auth.ts"]

    # Lifecycle truth prevents the same evidence from being admitted again.
    assert signal["learning_state"] == "rejected"
    assert signal["accepted_lesson"] is False
    assert signal["council_authority_head"] == "b7b3be4ca9acf3c2f853ad03758e18131a69895b"
    assert signal["campaign_merge_commit"] == "5753c5d1cff953c4591d009cc819c3eca661b56c"
    assert signal["council_execution_node"] == "kratos-HP-290-G4-Microtower-PC"
    reason = signal["rejection_reason"]
    assert "copied exact fixing-patch workflow identifiers" in reason
    assert "third workflow identity" in reason
    assert signal["authority"] == {
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }


def test_oracle_native_browser_signin_signal_uses_recovered_merge_base_lineage() -> None:
    signal = json.loads(ORACLE_SIGNIN_SIGNAL.read_text(encoding="utf-8"))
    classified = classify_signal(signal)

    assert classified["disposition"] == "candidate_ready"
    assert classified["triage_private_count"] == 40
    candidate = classified["candidate"]
    assert candidate["case_id"] == "learn-oracle-native-browser-signin-boundary-20260818"
    assert candidate["repository"] == "jaydumisuni/Oracle-"
    assert candidate["source_pr"] == 153
    assert candidate["defective_ref"] == "4410254e9468a28aa528c9eed0add31375a37372"
    assert candidate["fixing_ref"] == "8d769e2a35c55778d08be5614d3e3abec16b213e"
    assert candidate["language"] == "javascript"
    assert candidate["scored_paths"] == [
        "scripts/oracle-local-browser-launch.mjs",
        "scripts/oracle-local-engine.mjs",
    ]
    assert signal["learning_state"] == "collected"
    assert signal["accepted_lesson"] is False
    assert signal["security_or_integrity"] is True
    assert signal["concurrency_or_lifecycle"] is True
    assert "32071512641" in " ".join(signal["evidence_refs"])
    assert "32071512631" in " ".join(signal["evidence_refs"])
    assert "32071512700" in " ".join(signal["evidence_refs"])


def test_oracle_extension_update_signal_preserves_inherited_red_check_context() -> None:
    signal = json.loads(ORACLE_UPDATE_SIGNAL.read_text(encoding="utf-8"))
    classified = classify_signal(signal)

    assert classified["disposition"] == "candidate_ready"
    assert classified["triage_private_count"] == 60
    candidate = classified["candidate"]
    assert candidate["case_id"] == "learn-oracle-extension-update-install-authority-20260818"
    assert candidate["repository"] == "jaydumisuni/Oracle-"
    assert candidate["source_pr"] == 158
    assert candidate["defective_ref"] == "547f40755a0fb5ef005ce224605fe6d1cd31a680"
    assert candidate["fixing_ref"] == "5b58f0f3d8543ddc29a9a578e4ed84a70fdeaa2f"
    assert candidate["language"] == "javascript"
    assert candidate["scored_paths"] == [
        "browser/bridge/extension-installer.mjs",
        "browser/bridge/server.mjs",
        "browser/extension/update-background.js",
        "browser/extension/options/app.js",
    ]
    assert signal["learning_state"] == "collected"
    assert signal["accepted_lesson"] is False
    assert signal["cross_component"] is True
    assert signal["security_or_integrity"] is True
    assert signal["concurrency_or_lifecycle"] is True
    evidence = " ".join(signal["evidence_refs"])
    assert "32148873820" in evidence
    assert "pull/157" in evidence
    assert "32139686124" in evidence
    assert "31/31" in signal["summary"]
    assert "pre-existing privacy-shield timeout" in signal["summary"]


def test_direct_collector_excludes_completed_signals_and_selects_only_new_oracle_repairs(tmp_path: Path) -> None:
    signals = tmp_path / "signals"
    signals.mkdir()
    for source in (
        CHECKOUT_SIGNAL,
        CHECKSUM_SIGNAL,
        ORACLE_SIGNAL,
        ORACLE_SIGNIN_SIGNAL,
        ORACLE_UPDATE_SIGNAL,
    ):
        (signals / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    candidates = _signal_candidates(signals)
    assert [row["case_id"] for row in candidates] == [
        "learn-oracle-extension-update-install-authority-20260818",
        "learn-oracle-native-browser-signin-boundary-20260818",
    ]
    assert [row["source_pr"] for row in candidates] == [158, 153]
    assert [row["private_count"] for row in candidates] == [60, 40]
    assert all(row["direct_event_candidate"] is True for row in candidates)
    assert all(row["provenance_complete"] is True for row in candidates)


def test_oracle_browser_project_round_binds_exact_two_new_candidates(monkeypatch) -> None:
    manifest = json.loads(BROWSER_ROUND.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "sergeant.project-learning-round.v1"
    assert manifest["round_id"] == "project-oracle-browser-repairs-20260818"
    assert manifest["candidate_count"] == 2
    assert manifest["signal_paths"] == [
        ".github/self-learning/signals/oracle-extension-update-install-authority-2026-08-18.json",
        ".github/self-learning/signals/oracle-native-browser-signin-boundary-2026-08-18.json",
    ]
    assert manifest["expected_case_ids"] == [
        "learn-oracle-extension-update-install-authority-20260818",
        "learn-oracle-native-browser-signin-boundary-20260818",
    ]
    assert manifest["authority"] == {
        "execution_lane": "oracle-direct-terminal",
        "direct_terminal_authorization_flag": "--owner-authorized",
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }

    monkeypatch.chdir(ROOT)
    packet = _candidate_packet(BROWSER_ROUND.relative_to(ROOT), "e" * 40)
    assert packet["candidate_count"] == 2
    assert packet["direct_signal_candidate_count"] == 2
    assert packet["reviewer_frozen_before_collection"] == "e" * 40
    assert [row["case_id"] for row in packet["candidates"]] == manifest["expected_case_ids"]
    assert [row["signal_path"] for row in packet["candidates"]] == manifest["signal_paths"]


def test_completed_oracle_project_round_is_historical_and_non_replayable(monkeypatch) -> None:
    manifest = json.loads(ROUND.read_text(encoding="utf-8"))
    assert manifest["round_id"] == "project-oracle-oidc-workflow-20260818"
    assert manifest["candidate_count"] == 1
    assert manifest["expected_case_ids"] == [
        "learn-oracle-oidc-workflow-identity-20260817"
    ]
    assert manifest["signal_paths"] == [
        ".github/self-learning/signals/oracle-oidc-workflow-identity-2026-08-17.json"
    ]
    assert manifest["authority"]["may_auto_promote"] is False
    assert manifest["authority"]["may_auto_merge"] is False
    assert manifest["authority"]["final_verdict"] == "Sergeant"

    monkeypatch.chdir(ROOT)
    with pytest.raises(
        SystemExit,
        match="manifest case is not currently candidate-ready and unprocessed",
    ):
        _candidate_packet(ROUND.relative_to(ROOT), "e" * 40)


def test_oracle_council_rejection_record_is_durable_and_unpromoted() -> None:
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    assert result["schema_version"] == "sergeant.project-learning-disposition.v1"
    assert result["round_id"] == "project-oracle-oidc-workflow-20260818"
    assert result["case_id"] == "learn-oracle-oidc-workflow-identity-20260817"
    assert result["authority_head"] == "b7b3be4ca9acf3c2f853ad03758e18131a69895b"
    assert result["campaign_merge_commit"] == "5753c5d1cff953c4591d009cc819c3eca661b56c"
    assert result["state"] == "rejected"
    assert result["sergeant_verdict"] == "reject"
    assert result["accepted_lesson"] is False
    assert result["accepted_lesson_path"] is None
    assert result["automatic_promotions"] == 0
    assert result["automatic_merges"] == 0
    assert result["preserved_workers"] == ["defender", "prosecutor", "teacher"]
    assert result["evidence_file_count"] == 15
    assert len(result["oracle_control_evidence"]) == 5


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
    assert "javascript" in row["languages"]
    assert "repair" in row["event_types"]
    assert row["collection_state"] == "enabled-for-signal-intake"
    assert row["learning_boundary"] == "behavioral defect/fix lineage required"
    assert registry["policy"]["automatic_promotions"] == 0
    assert registry["policy"]["automatic_merges"] == 0
