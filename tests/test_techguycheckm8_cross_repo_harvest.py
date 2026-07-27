from __future__ import annotations

import json
from pathlib import Path

import pytest

from main_review.cross_repo_learning import classify_signal
from main_review.self_learning_queue import add_case, new_queue
from scripts.collect_github_learning_candidates import _signal_candidates


ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / ".github" / "self-learning" / "signals"
CHECKOUT_SIGNAL = SIGNALS / "tgcheckm8-checkout-credential-boundary-2026-07-23.json"
CHECKSUM_SIGNAL = SIGNALS / "tgcheckm8-checksum-path-namespace-2026-07-23.json"
SOURCES = ROOT / ".github" / "self-learning" / "cross-repository-sources.json"


@pytest.mark.parametrize(
    ("signal_path", "case_id", "language", "scored_paths"),
    [
        (
            CHECKOUT_SIGNAL,
            "learn-tgcheckm8-checkout-credential-boundary-20260723",
            "yaml",
            [".github/workflows/reviewed-apple-tools-build.yml"],
        ),
        (
            CHECKSUM_SIGNAL,
            "learn-tgcheckm8-checksum-path-namespace-20260723",
            "python",
            [
                "tools/apple-build/make_receipt.py",
                ".github/workflows/reviewed-apple-tools-build.yml",
            ],
        ),
    ],
)
def test_tgcheckm8_10_for_2_signal_is_candidate_ready_but_unpromoted(
    signal_path: Path,
    case_id: str,
    language: str,
    scored_paths: list[str],
) -> None:
    signal = json.loads(signal_path.read_text(encoding="utf-8"))
    result = classify_signal(signal)

    assert result["disposition"] == "candidate_ready"
    assert result["triage_private_count"] == 40
    assert result["authority"] == {
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }

    candidate = result["candidate"]
    assert candidate["case_id"] == case_id
    assert candidate["repository"] == "jaydumisuni/TechGuyCheckm8"
    assert candidate["source_pr"] == 18
    assert candidate["defective_ref"] == "3b9b5d2469fed602cd6b5c728109cf193b9ccba1"
    assert candidate["fixing_ref"] == "40291a738e866e53b7d1cdcd0cf31f6e860357f5"
    assert candidate["language"] == language
    assert candidate["scored_paths"] == scored_paths
    assert candidate["private_count"] == 40
    assert candidate["cross_repository"] is True
    assert signal["accepted_lesson"] is False

    queue = new_queue(
        "techguycheckm8-10-for-2",
        authority_head="e" * 40,
        target_branch="learning/techguycheckm8-10-for-2-v1",
    )
    case = add_case(queue, candidate)
    assert case["state"] == "collected"
    assert queue["authority"]["may_auto_promote"] is False
    assert queue["authority"]["may_auto_merge"] is False


def test_tgcheckm8_direct_collector_returns_both_10_for_2_candidates(tmp_path: Path) -> None:
    signals = tmp_path / "signals"
    signals.mkdir()
    for source in (CHECKOUT_SIGNAL, CHECKSUM_SIGNAL):
        (signals / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    candidates = _signal_candidates(signals)

    assert [row["case_id"] for row in candidates] == [
        "learn-tgcheckm8-checksum-path-namespace-20260723",
        "learn-tgcheckm8-checkout-credential-boundary-20260723",
    ]
    assert all(row["direct_event_candidate"] is True for row in candidates)
    assert all(row["provenance_complete"] is True for row in candidates)
    assert all(row["security_or_integrity"] is True for row in candidates)


def test_tgcheckm8_source_registry_covers_harvested_languages() -> None:
    registry = json.loads(SOURCES.read_text(encoding="utf-8"))
    row = next(
        item
        for item in registry["confirmed_sources"]
        if item["repository"] == "jaydumisuni/TechGuyCheckm8"
    )

    assert {"rust", "python", "yaml"} <= set(row["languages"])
    assert row["collection_state"] == "enabled-for-signal-intake"
    assert registry["policy"]["automatic_promotions"] == 0
    assert registry["policy"]["automatic_merges"] == 0
