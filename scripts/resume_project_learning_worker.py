#!/usr/bin/env python3
"""Resume one missing project-learning council worker from preserved terminal evidence.

This keeps Oracle/workstation RPC calls short and recoverable. It never repeats
the blind review or truth reveal, never accepts a lesson automatically, and
never changes repository contents beyond the caller's local evidence directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main_review.self_learning_queue import (
    QUEUE_SCHEMA,
    QueueContractError,
    attach_worker,
    canonical_digest,
    council_complete,
    get_case,
    write_queue,
)
from scripts.export_learning_proposals import export as export_proposals
from scripts.project_learning_workers import (
    LearningWorkerError,
    worker_request as project_worker_request,
)
from scripts.run_project_driven_learning import (
    _git_head,
    _git_status_porcelain,
    _sha256,
    _write_evidence_manifest,
)

_ROLES = ("teacher", "prosecutor", "defender")
_EVIDENCE_SCHEMA = "sergeant.project-learning-evidence-manifest.v1"
_RECOVERY_HINT = (
    " If this follows an interrupted owner-authorized resume, first verify that the changed "
    "files are exactly the expected partial resume transaction; only then regenerate "
    "evidence-manifest.json with _write_evidence_manifest(evidence_dir) before retrying. "
    "Never re-hash unexplained changes."
)


def _verify_preserved_evidence(root: Path) -> set[str]:
    """Verify every file bound by the preserved SHA-256 evidence manifest."""

    manifest_path = root / "evidence-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("preserved evidence manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("preserved evidence manifest is unreadable") from exc
    if manifest.get("schema_version") != _EVIDENCE_SCHEMA:
        raise SystemExit("preserved evidence manifest schema is invalid")

    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise SystemExit("preserved evidence manifest files are invalid")
    if manifest.get("file_count") != len(rows):
        raise SystemExit("preserved evidence manifest file count is invalid")

    resolved_root = root.resolve()
    verified: set[str] = set()
    total_bytes = 0
    for row in rows:
        if not isinstance(row, dict):
            raise SystemExit("preserved evidence manifest row is invalid")
        relative = str(row.get("path") or "").strip()
        relative_path = Path(relative)
        if (
            not relative
            or relative_path.is_absolute()
            or ".." in relative_path.parts
            or relative_path.as_posix() in verified
        ):
            raise SystemExit("preserved evidence manifest contains an unsafe or duplicate path")
        path = (root / relative_path).resolve()
        try:
            path.relative_to(resolved_root)
        except ValueError as exc:
            raise SystemExit("preserved evidence manifest path escapes the evidence root") from exc
        if not path.is_file():
            raise SystemExit(f"preserved evidence file is missing: {relative}")

        size_bytes = row.get("size_bytes")
        sha256 = str(row.get("sha256") or "").strip().lower()
        if not isinstance(size_bytes, int) or size_bytes < 0 or len(sha256) != 64:
            raise SystemExit(f"preserved evidence manifest metadata is invalid: {relative}")
        if path.stat().st_size != size_bytes or _sha256(path) != sha256:
            raise SystemExit(f"preserved evidence integrity mismatch: {relative}." + _RECOVERY_HINT)

        verified.add(relative_path.as_posix())
        total_bytes += size_bytes

    if manifest.get("total_bytes") != total_bytes:
        raise SystemExit("preserved evidence manifest total byte count is invalid." + _RECOVERY_HINT)
    return verified


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
    if (
        not args.case_id.strip()
        or args.case_id in {".", ".."}
        or "/" in args.case_id
        or "\\" in args.case_id
    ):
        raise SystemExit("project-learning case ID must be one filesystem-safe path segment")

    authority_head = args.authority_head.lower().strip()
    if _git_head() != authority_head:
        raise SystemExit("frozen Sergeant head mismatch while resuming project learning")
    if _git_status_porcelain():
        raise SystemExit("resuming project learning requires a clean frozen Sergeant worktree")

    authority_path = args.evidence_dir / "authority.json"
    terminal_path = args.evidence_dir / "terminal-result.json"
    queue_path = args.evidence_dir / "round" / "learning-queue.json"
    summary_path = args.evidence_dir / "round" / "summary.json"
    case_dir = args.evidence_dir / "round" / "cases" / args.case_id
    truth_path = case_dir / "truth-packet.json"
    verified_paths = _verify_preserved_evidence(args.evidence_dir)
    required_paths = {
        "authority.json",
        "terminal-result.json",
        "round/learning-queue.json",
        "round/summary.json",
        f"round/cases/{args.case_id}/truth-packet.json",
    }
    missing_bindings = sorted(required_paths - verified_paths)
    if missing_bindings:
        raise SystemExit(
            "required preserved evidence is not bound by the evidence manifest: "
            + ", ".join(missing_bindings)
        )
    for path in (authority_path, terminal_path, queue_path, summary_path, truth_path):
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
    truth_artifact = case.get("artifacts", {}).get("truth_packet", {})
    if truth_artifact.get("digest") != canonical_digest(truth):
        raise SystemExit("preserved truth packet digest mismatch")
    if truth.get("case_id") != args.case_id:
        raise SystemExit("truth packet case binding mismatch")

    try:
        packet = project_worker_request(args.role, truth)
    except LearningWorkerError as exc:
        raise SystemExit(f"project-learning {args.role} worker failed: {exc}") from exc
    try:
        attach_worker(queue, args.case_id, args.role, packet)
    except QueueContractError as exc:
        raise SystemExit(f"project-learning {args.role} worker packet was rejected: {exc}") from exc
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
    summary = _refresh_summary(queue, summary_path)
    proposal_index = export_proposals(queue, args.evidence_dir / "learning" / "proposals")

    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
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
