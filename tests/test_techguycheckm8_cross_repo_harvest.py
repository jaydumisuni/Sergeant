from __future__ import annotations

import json
from pathlib import Path

from scripts.collect_github_learning_candidates import _signal_candidates


ROOT = Path(__file__).resolve().parents[1]
SIGNALS = ROOT / ".github" / "self-learning" / "signals"
CHECKOUT_SIGNAL = SIGNALS / "tgcheckm8-checkout-credential-boundary-2026-07-23.json"
CHECKSUM_SIGNAL = SIGNALS / "tgcheckm8-checksum-path-namespace-2026-07-23.json"
SOURCES = ROOT / ".github" / "self-learning" / "cross-repository-sources.json"


def test_tgcheckm8_signals_preserve_final_pr159_disposition() -> None:
    checkout = json.loads(CHECKOUT_SIGNAL.read_text(encoding="utf-8"))
    checksum = json.loads(CHECKSUM_SIGNAL.read_text(encoding="utf-8"))

    assert checksum["case_id"] == "learn-tgcheckm8-checksum-path-namespace-20260723"
    assert checksum["repository"] == "jaydumisuni/TechGuyCheckm8"
    assert checksum["source_pr"] == 18
    assert checksum["defective_ref"] == "3b9b5d2469fed602cd6b5c728109cf193b9ccba1"
    assert checksum["fixing_ref"] == "40291a738e866e53b7d1cdcd0cf31f6e860357f5"
    assert checksum["learning_state"] == "accepted"
    assert checksum["accepted_lesson"] is True
    assert checksum["accepted_lesson_path"] == (
        ".github/self-learning/lessons/tgcheckm8-checksum-path-namespace-20260723.json"
    )

    assert checkout["case_id"] == "learn-tgcheckm8-checkout-credential-boundary-20260723"
    assert checkout["repository"] == "jaydumisuni/TechGuyCheckm8"
    assert checkout["source_pr"] == 18
    assert checkout["defective_ref"] == "3b9b5d2469fed602cd6b5c728109cf193b9ccba1"
    assert checkout["fixing_ref"] == "40291a738e866e53b7d1cdcd0cf31f6e860357f5"
    assert checkout["learning_state"] == "rejected"
    assert checkout["accepted_lesson"] is False
    assert "Defender rejected" in checkout["rejection_reason"]

    for signal in (checksum, checkout):
        assert signal["authority"] == {
            "may_auto_promote": False,
            "may_auto_merge": False,
            "final_verdict": "Sergeant",
        }


def test_tgcheckm8_direct_collector_excludes_processed_pr159_signals(tmp_path: Path) -> None:
    signals = tmp_path / "signals"
    signals.mkdir()
    for source in (CHECKOUT_SIGNAL, CHECKSUM_SIGNAL):
        (signals / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    assert _signal_candidates(signals) == []


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
