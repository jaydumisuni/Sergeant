#!/usr/bin/env python3
"""Build the next Sergeant training round from a bounded curriculum packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from main_review.adaptive_curriculum import plan_curriculum_round


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    candidates = packet.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("curriculum packet must contain candidate repositories")

    recent_results = packet.get("recent_results", [])
    language_history = packet.get("language_history", [])
    if not isinstance(recent_results, list):
        raise ValueError("recent_results must be a list")
    if not isinstance(language_history, list):
        raise ValueError("language_history must be a list")

    plan = plan_curriculum_round(
        candidates=candidates,
        current_tier=int(packet.get("current_tier", 0) or 0),
        recent_results=recent_results,
        language_history=[str(item) for item in language_history],
        count=int(packet.get("count", 3) or 3),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "target_tier": plan["target_tier"],
        "target_difficulty": plan["target_difficulty"],
        "case_count": len(plan["cases"]),
        "planned_private_count": plan["planned_private_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
