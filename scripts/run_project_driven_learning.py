#!/usr/bin/env python3
"""Run one owner-authorized project-learning round from a trusted terminal.

This is the execution lane for project-driven learning. GitHub Actions validates
contracts and exact heads only; it does not perform model inference. The runner
freezes the current Sergeant commit, binds the exact manifest candidates, then
injects the isolated project-learning worker transport after blind review truth
reveal. It preserves bounded proposals and fails closed on incomplete council
work. It never promotes a lesson or merges code.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from scripts.collect_github_learning_candidates import _signal_candidates
from scripts.export_learning_proposals import export as export_proposals
from scripts.project_learning_workers import worker_request as project_worker_request
from scripts.run_controlled_self_learning import run_round


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    ).strip().lower()


def _candidate_packet(manifest_path: Path, authority_head: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "sergeant.project-learning-round.v1":
        raise SystemExit("unsupported project-learning manifest schema")
    authority = manifest.get("authority")
    if not isinstance(authority, dict):
        raise SystemExit("project-learning manifest requires authority")
    if authority.get("may_auto_promote") is not False or authority.get("may_auto_merge") is not False:
        raise SystemExit("project-learning manifest must forbid automatic promotion and merge")
    if authority.get("final_verdict") != "Sergeant":
        raise SystemExit("project-learning manifest must preserve Sergeant final authority")
    if authority.get("execution_lane") != "oracle-direct-terminal":
        raise SystemExit("project-learning manifest is not authorized for the direct-terminal lane")
    if authority.get("direct_terminal_authorization_flag") != "--owner-authorized":
        raise SystemExit("project-learning manifest has an unexpected owner-authorization contract")

    expected_ids = [str(value) for value in manifest.get("expected_case_ids", [])]
    signal_paths = [Path(str(value)) for value in manifest.get("signal_paths", [])]
    expected_count = int(manifest.get("candidate_count", 0) or 0)
    if not 1 <= expected_count <= 3:
        raise SystemExit("project-learning candidate_count must be between 1 and 3")
    if len(expected_ids) != expected_count or len(signal_paths) != expected_count:
        raise SystemExit("manifest candidate count does not match IDs and signal paths")

    actual_ids: list[str] = []
    for path in signal_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual_ids.append(str(payload.get("case_id") or ""))
    if actual_ids != expected_ids:
        raise SystemExit(f"manifest signal/case binding mismatch: {actual_ids!r} != {expected_ids!r}")

    candidates = _signal_candidates(Path(".github/self-learning/signals"))
    by_id = {str(row["case_id"]): row for row in candidates}
    selected: list[dict[str, Any]] = []
    for case_id in expected_ids:
        row = by_id.get(case_id)
        if row is None:
            raise SystemExit(f"manifest case is not currently candidate-ready and unprocessed: {case_id}")
        selected.append(row)

    return {
        "schema_version": "sergeant.github-learning-candidates.v1",
        "week_id": str(manifest["round_id"]),
        "reviewer_frozen_before_collection": authority_head,
        "truth_persisted_before_blind_review": False,
        "project_driven": True,
        "execution_lane": "oracle-direct-terminal",
        "manifest": manifest_path.as_posix(),
        "candidate_count": len(selected),
        "direct_signal_candidate_count": len(selected),
        "candidates": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--authority-head", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--owner-authorized", action="store_true")
    args = parser.parse_args()

    if not args.owner_authorized:
        raise SystemExit("direct project learning requires explicit --owner-authorized")

    authority_head = args.authority_head.lower().strip()
    actual_head = _git_head()
    if actual_head != authority_head:
        raise SystemExit(f"frozen Sergeant head mismatch: {actual_head} != {authority_head}")

    candidates = _candidate_packet(args.manifest, authority_head)
    history = (
        json.loads(args.history.read_text(encoding="utf-8"))
        if args.history and args.history.exists()
        else {}
    )

    os.environ["SERGEANT_LLM_ENABLED"] = "false"
    os.environ["SERGEANT_CPL_ENABLED"] = "false"
    os.environ["SERGEANT_CPL_POLICY"] = "disabled"
    os.environ["SERGEANT_LEARNING_BACKEND"] = "cloudflare"

    args.output_dir.mkdir(parents=True, exist_ok=False)
    authority_record = {
        "schema_version": "sergeant.project-learning-terminal-authority.v1",
        "authority_head": authority_head,
        "target_branch": args.target_branch,
        "round_id": candidates["week_id"],
        "execution_lane": "oracle-direct-terminal",
        "owner_authorized": True,
        "automatic_promotions": 0,
        "automatic_merges": 0,
        "final_verdict": "Sergeant",
    }
    (args.output_dir / "authority.json").write_text(
        json.dumps(authority_record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "candidates.json").write_text(
        json.dumps(candidates, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    round_dir = args.output_dir / "round"
    summary = run_round(
        candidates_packet=candidates,
        history=history,
        output_dir=round_dir,
        authority_head=authority_head,
        target_branch=args.target_branch,
        count=int(candidates["candidate_count"]),
        worker_request_fn=project_worker_request,
    )

    queue = json.loads((round_dir / "learning-queue.json").read_text(encoding="utf-8"))
    proposal_index = export_proposals(queue, args.output_dir / "learning" / "proposals")
    completion = {
        "schema_version": "sergeant.project-learning-terminal-result.v1",
        "authority_head": authority_head,
        "round_id": candidates["week_id"],
        "candidate_count": int(candidates["candidate_count"]),
        "summary": summary,
        "proposal_index": proposal_index,
        "automatic_promotions": 0,
        "automatic_merges": 0,
    }
    (args.output_dir / "terminal-result.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    unresolved = int(summary.get("state_counts", {}).get("truth_revealed", 0) or 0)
    completed = int(summary.get("state_counts", {}).get("council_complete", 0) or 0) + int(
        summary.get("state_counts", {}).get("rejected", 0) or 0
    )
    worker_errors = int(summary.get("worker_error_cases", 0) or 0)
    expected = int(candidates["candidate_count"])
    print(json.dumps(completion, sort_keys=True))
    if worker_errors != 0 or unresolved != 0 or completed != expected:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
