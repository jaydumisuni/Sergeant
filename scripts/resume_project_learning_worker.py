#!/usr/bin/env python3
"""Resume one missing project-learning council worker from preserved terminal evidence.

This keeps Oracle/workstation RPC calls short and recoverable. It never repeats
the blind review or truth reveal, never accepts a lesson automatically, and
never changes repository contents beyond the caller's local evidence directory.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from main_review.self_learning_queue import (
    QUEUE_SCHEMA,
    QueueContractError,
    attach_worker,
    council_complete,
    get_case,
    write_queue,
)
from scripts.export_learning_proposals import export as export_proposals
from scripts.project_learning_workers import worker_request as project_worker_request
from scripts.run_project_driven_learning import (
    _git_head,
    _git_status_porcelain,
    _write_evidence_manifest,
)

_ROLES = ("teacher", "prosecutor", "defender")


def _refresh_summary(queue: dict, summary_path: Path) -> dict:
    previous = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    states = sorted({str(row.get("state")) for row in queue.get("cases", [])})
    previous["state_counts"] = {
        state: sum(1 for row in queue.get("cases", []) if row.get("state") == state)
        for state in states
    }
    previous["worker_error_cases"] = sum(
        1 for row in queue.get("cases", []) if row.get("worker_errors")
    )
    previous["automatic_promotions"] = 0
    previous["automatic_merges"] = 0
    summary_path.write_text(json.dumps(previous, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return previous


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--role", choices=_ROLES, required=True)
    parser.add_argument("--authority-head", required=True)
    parser.add_argument("--owner-authorized", action="store_true")
    args = parser.parse_args()

    if not args.owner_authorized:
        raise SystemExit("resuming project learning requires explicit --owner-authorized")

    authority_head = args.authority_head.lower().strip()
    if _git_head() != authority_head:
        raise SystemExit("frozen Sergeant head mismatch while resuming project learning")
    if _git_status_porcelain():
        raise SystemExit("resuming project learning requires a clean frozen Sergeant worktree")

    authority_path = args.evidence_dir / "authority.json"
    queue_path = args.evidence_dir / "round" / "learning-queue.json"
    case_dir = args.evidence_dir / "round" / "cases" / args.case_id
    truth_path = case_dir / "truth-packet.json"
    for path in (authority_path, queue_path, truth_path):
        if not path.is_file():
            raise SystemExit(f"required preserved evidence is missing: {path}")

    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    if authority.get("authority_head") != authority_head:
        raise SystemExit("preserved authority head does not match requested resume head")
    if authority.get("execution_lane") != "oracle-direct-terminal":
        raise SystemExit("preserved evidence is not a direct-terminal learning round")
    if authority.get("automatic_promotions") != 0 or authority.get("automatic_merges") != 0:
        raise SystemExit("preserved authority unexpectedly grants automatic action")

    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("schema_version") != QUEUE_SCHEMA or queue.get("authority_head") != authority_head:
        raise SystemExit("preserved queue authority is invalid")
    try:
        case = get_case(queue, args.case_id)
    except QueueContractError as exc:
        raise SystemExit(str(exc)) from exc
    if case.get("state") != "truth_revealed":
        raise SystemExit(f"case is not resumable from truth_revealed: {case.get('state')}")
    if args.role in case.get("workers", {}):
        raise SystemExit(f"worker already preserved for {args.case_id}: {args.role}")

    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    if truth.get("case_id") != args.case_id:
        raise SystemExit("truth packet case binding mismatch")

    packet = project_worker_request(args.role, truth)
    attach_worker(queue, args.case_id, args.role, packet)
    (case_dir / f"{args.role}.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    errors = case.get("worker_errors")
    if isinstance(errors, dict):
        errors.pop(args.role, None)
        if not errors:
            case.pop("worker_errors", None)

    if set(case.get("workers", {})) == set(_ROLES):
        case = council_complete(queue, args.case_id)
        (case_dir / "lesson-proposal.json").write_text(
            json.dumps(case, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    write_queue(queue, queue_path)
    summary = _refresh_summary(queue, args.evidence_dir / "round" / "summary.json")
    proposal_index = export_proposals(queue, args.evidence_dir / "learning" / "proposals")

    terminal_path = args.evidence_dir / "terminal-result.json"
    terminal = json.loads(terminal_path.read_text(encoding="utf-8")) if terminal_path.exists() else {}
    queue_case_count = len(queue.get("cases", []))
    terminal.update({
        "schema_version": "sergeant.project-learning-terminal-result.v1",
        "authority_head": authority_head,
        "round_id": queue["week_id"],
        "candidate_count": terminal.get("candidate_count", queue_case_count),
        "queue_case_count": queue_case_count,
        "summary": summary,
        "proposal_index": proposal_index,
        "evidence_manifest_path": "evidence-manifest.json",
        "automatic_promotions": 0,
        "automatic_merges": 0,
    })
    terminal_path.write_text(json.dumps(terminal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    evidence_manifest = _write_evidence_manifest(args.evidence_dir)

    result = {
        "case_id": args.case_id,
        "role": args.role,
        "state": case.get("state"),
        "workers": sorted(case.get("workers", {})),
        "proposal_count": proposal_index["proposal_count"],
        "evidence_file_count": evidence_manifest["file_count"],
        "automatic_promotions": 0,
        "automatic_merges": 0,
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
