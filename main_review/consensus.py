"""Backward-compatible consensus adapter for Sergeant.

`evidence_consensus.py` owns the full Tier 3 evidence consensus engine. This
module keeps the older `build_consensus()` API used by the PR reviewer and tests,
while delegating the decision semantics to the same normalized verdict rules.
"""

from __future__ import annotations

from typing import Any

from .evidence_consensus import _norm_verdict


def build_consensus(reviewer_outputs: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the legacy consensus packet without duplicating evidence consensus logic."""
    signals: list[dict[str, object]] = []
    for output in reviewer_outputs:
        source = str(output.get("source", "reviewer"))
        verdict = _norm_verdict(output.get("verdict", output.get("decision", "unknown")))
        evidence = output.get("evidence", [])
        signals.append(
            {
                "source": source,
                "verdict": verdict,
                "evidence_count": len(evidence) if isinstance(evidence, list) else 0,
                "weight": 2 if source in {"sergeant", "main-review", "human"} else 1,
            }
        )

    blocking = [signal for signal in signals if signal["verdict"] in {"BLOCK", "REQUEST_CHANGES"}]
    needs_work = [signal for signal in signals if signal["verdict"] == "NEEDS WORK"]
    pass_like = [signal for signal in signals if signal["verdict"] == "PASS"]

    if blocking:
        consensus = "BLOCK"
    elif needs_work:
        consensus = "NEEDS WORK"
    elif pass_like:
        consensus = "PASS"
    else:
        consensus = "NO CONSENSUS"

    return {
        "consensus": consensus,
        "signals": signals,
        "summary": {
            "total_sources": len(signals),
            "blocking": len(blocking),
            "needs_work": len(needs_work),
            "pass_like": len(pass_like),
        },
        "rule": "Evidence beats vote count; blocking evidence wins until answered.",
    }
