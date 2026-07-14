"""Deterministic proof that verified experience improves later missions.

The proof uses an isolated temporary repository. It records explicit human/Judge
outcomes, retrieves relevant experience for a later but non-identical change,
detects recurrence, derives Cpl/officer/model/weapon profiles, and proves that
rejected experience is not promoted as recurrence evidence.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from .cpl_experience import (
    detect_recurrences,
    load_experience_events,
    record_human_outcomes,
    retrieve_experience,
)

PROOF_SCHEMA = "sergeant.verified-learning-proof.v1"


def run_verified_learning_proof() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sergeant-learning-proof-") as temp:
        root = Path(temp)
        accepted = record_human_outcomes(root, [{
            "mission_id": "LEARN-001",
            "finding_id": "unsafe-query",
            "status": "confirmed",
            "category": "security",
            "officer": "Medic",
            "path": "src/api.py",
            "message": "Untrusted request input reaches database query execution.",
            "evidence_refs": ["src/api.py:3"],
            "supporting_models": ["model-alpha"],
            "weapons": ["static-taint"],
        }])
        rejected = record_human_outcomes(root, [{
            "mission_id": "LEARN-002",
            "finding_id": "safe-config",
            "status": "false_positive",
            "category": "security",
            "officer": "Medic",
            "path": "src/config.py",
            "message": "Environment configuration is a command execution sink.",
            "supporting_models": ["model-beta"],
            "weapons": ["lexical-scan"],
        }])

        experience = retrieve_experience(root, ["src/api_v2.py"], officers=["Medic"])
        current_findings = [{
            "category": "security",
            "path": "src/api_v2.py",
            "message": "Request input reaches a database query without validation.",
        }]
        recurrences = detect_recurrences(current_findings, experience)
        rejected_only_experience = {
            **experience,
            "events": [event for event in experience["events"] if event.get("status") == "rejected"],
        }
        rejected_recurrences = detect_recurrences([{
            "category": "security",
            "path": "src/config.py",
            "message": "Environment configuration remains safely isolated.",
        }], rejected_only_experience)
        events = load_experience_events(root)
        profiles = experience["profiles"]
        required_profiles = ["cpl:Cpl", "officer:Medic", "model:model-alpha", "weapon:static-taint"]
        checks = {
            "accepted_outcome_recorded": len(accepted) == 4,
            "rejected_outcome_recorded": len(rejected) == 4,
            "later_mission_retrieved_experience": any(event.get("finding_id") == "unsafe-query" for event in experience["events"]),
            "similar_non_identical_issue_detected": bool(recurrences),
            "rejected_memory_not_recurrence_evidence": rejected_recurrences == [],
            "cpl_officer_model_weapon_profiles_exist": all(key in profiles for key in required_profiles),
            "verified_model_reliability_recorded": profiles.get("model:model-alpha", {}).get("observed_reliability") == 1.0,
            "rejected_model_reliability_recorded": profiles.get("model:model-beta", {}).get("observed_reliability") == 0.0,
            "ledger_is_append_only_and_mission_distinct": len(events) == 8 and len({event["event_id"] for event in events}) == 8,
            "current_evidence_remains_authoritative": experience["anti_repeat_rule"].startswith("Applicable verified experience"),
        }
        return {
            "schema_version": PROOF_SCHEMA,
            "passed": all(checks.values()),
            "checks": checks,
            "accepted_event_count": len(accepted),
            "rejected_event_count": len(rejected),
            "retrieved_event_count": len(experience["events"]),
            "recurrence_count": len(recurrences),
            "recurrences": recurrences,
            "profile_keys": sorted(profiles),
            "rule": "Verified experience informs later missions; rejected experience cannot override current repository evidence.",
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prove Sergeant's governed verified-learning loop.")
    parser.add_argument("--output")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_verified_learning_proof()
    text = json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
