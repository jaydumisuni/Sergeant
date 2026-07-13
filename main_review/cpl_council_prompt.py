"""Prompt and audit formatting for Cpl council rounds."""
from __future__ import annotations

import json
from typing import Any


def report_table(passes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in passes:
        rows.append({
            "round": item.get("council_round", 1),
            "model": item.get("model"),
            "specialist": item.get("specialist"),
            "supported_officer": item.get("supported_officer"),
            "verdict": item.get("verdict"),
            "confidence": item.get("confidence"),
            "summary": item.get("summary"),
            "findings": [
                {key: finding.get(key) for key in ("severity", "category", "path", "line_start", "line_end", "message")}
                for finding in item.get("findings", [])[:6]
            ],
            "unanswered_questions": item.get("unanswered_questions", []),
        })
    return rows


def follow_up_prompt(
    base: str,
    table: list[dict[str, Any]],
    command: dict[str, Any],
    experience: dict[str, Any],
    round_number: int,
) -> str:
    memory = {
        "events": experience.get("events", [])[:8],
        "canonical_lessons": experience.get("canonical_lessons", [])[:6],
    }
    return "\n".join([
        base,
        f"\nCPL COUNCIL ROUND {round_number}",
        "Cpl has tabled the officer reports below. Treat them as claims to verify; repository excerpts remain authoritative.",
        json.dumps(table, indent=2, sort_keys=True, default=str)[:28000],
        "\nCpl instruction:\n" + json.dumps(command, indent=2, sort_keys=True, default=str),
        "\nRelevant verified/rejected experience:\n" + json.dumps(memory, indent=2, sort_keys=True, default=str)[:12000],
        "Return the normal grounded review JSON. Resolve the gap or preserve it in unanswered_questions.",
    ])


def member_records(passes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    members: dict[str, dict[str, Any]] = {}
    for report in passes:
        model = str(report.get("model") or "unknown")
        row = members.setdefault(model, {
            "model": model,
            "provider": report.get("provider"),
            "roles": [],
            "rounds": [],
            "reports": 0,
        })
        role = str(report.get("specialist") or "generalist")
        if role not in row["roles"]:
            row["roles"].append(role)
        round_number = int(report.get("council_round", 1) or 1)
        if round_number not in row["rounds"]:
            row["rounds"].append(round_number)
        row["reports"] += 1
    return list(members.values())
