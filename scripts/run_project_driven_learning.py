#!/usr/bin/env python3
"""Run one owner-authorized project-learning round from a trusted terminal.

This is the execution lane for project-driven learning. GitHub Actions validates
contracts and exact heads only; it does not perform model inference. The runner
freezes a clean current Sergeant commit, binds the exact manifest signal files,
then injects the isolated project-learning worker transport after blind review
truth reveal. It preserves bounded proposals, hashes the durable evidence, and
fails closed on incomplete council work. It never promotes a lesson or merges
code.
"""

from __future__ import annotations

import argparse
import hashlib
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


def _git_status_porcelain() -> str:
    return subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    ).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_evidence_manifest(root: Path) -> dict[str, Any]:
    """Hash durable learning evidence without copying transient Git checkouts."""

    included: list[Path] = []
    for relative in ("authority.json", "candidates.json", "terminal-result.json"):
        path = root / relative
        if path.is_file():
            included.append(path)
    round_dir = root / "round"
    for relative in ("curriculum-plan.json", "learning-queue.json", "summary.json"):
        path = round_dir / relative
        if path.is_file():
            included.append(path)
    for base in (round_dir / "cases", root / "learning" / "proposals"):
        if base.is_dir():
            included.extend(path for path in base.rglob("*.json") if path.is_file())

    unique = sorted({path.resolve() for path in included}, key=lambda value: value.as_posix())
    files = []
    for path in unique:
        relative = path.relative_to(root.resolve()).as_posix()
        files.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    manifest = {
        "schema_version": "sergeant.project-learning-evidence-manifest.v1",
        "file_count": len(files),
        "total_bytes": sum(int(row["size_bytes"]) for row in files),
        "files": files,
        "excluded_transient_paths": ["round/checkouts/**"],
    }
    (root / "evidence-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


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

    round_id = str(manifest.get("round_id") or "").strip()
    if not round_id:
        raise SystemExit("project-learning manifest requires round_id")

    expected_ids = [str(value) for value in manifest.get("expected_case_ids", [])]
    signal_paths = [Path(str(value)) for value in manifest.get("signal_paths", [])]
    expected_count = int(manifest.get("candidate_count", 0) or 0)
    if not 1 <= expected_count <= 3:
        raise SystemExit("project-learning candidate_count must be between 1 and 3")
    if len(expected_ids) != expected_count or len(signal_paths) != expected_count:
        raise SystemExit("manifest candidate count does not match IDs and signal paths")
    if len(set(expected_ids)) != len(expected_ids):
        raise SystemExit("project-learning manifest contains duplicate case IDs")
    signal_names = [path.as_posix() for path in signal_paths]
    if len(set(signal_names)) != len(signal_names):
        raise SystemExit("project-learning manifest contains duplicate signal paths")

    actual_ids: list[str] = []
    for path in signal_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        actual_ids.append(str(payload.get("case_id") or ""))
    if actual_ids != expected_ids:
        raise SystemExit(f"manifest signal/case binding mismatch: {actual_ids!r} != {expected_ids!r}")

    candidates = _signal_candidates(Path(".github/self-learning/signals"))
    by_id = {str(row["case_id"]): row for row in candidates}
    selected: list[dict[str, Any]] = []
    for case_id, signal_path in zip(expected_ids, signal_paths, strict=True):
        row = by_id.get(case_id)
        if row is None:
            raise SystemExit(f"manifest case is not currently candidate-ready and unprocessed: {case_id}")
        actual_signal_path = Path(str(row.get("signal_path") or "")).as_posix()
        if actual_signal_path != signal_path.as_posix():
            raise SystemExit(
                f"manifest case resolved from unexpected signal path: {actual_signal_path} != {signal_path.as_posix()}"
            )
        selected.append(row)

    return {
        "schema_version": "sergeant.github-learning-candidates.v1",
        "week_id": round_id,
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
    if _git_status_porcelain():
        raise SystemExit("direct project learning requires a clean frozen Sergeant worktree")

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
        "clean_worktree_verified": True,
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
        "evidence_manifest_path": "evidence-manifest.json",
        "automatic_promotions": 0,
        "automatic_merges": 0,
    }
    (args.output_dir / "terminal-result.json").write_text(
        json.dumps(completion, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence_manifest = _write_evidence_manifest(args.output_dir)

    unresolved = int(summary.get("state_counts", {}).get("truth_revealed", 0) or 0)
    completed = int(summary.get("state_counts", {}).get("council_complete", 0) or 0) + int(
        summary.get("state_counts", {}).get("rejected", 0) or 0
    )
    worker_errors = int(summary.get("worker_error_cases", 0) or 0)
    expected = int(candidates["candidate_count"])
    print(json.dumps({**completion, "evidence_manifest": evidence_manifest}, sort_keys=True))
    if worker_errors != 0 or unresolved != 0 or completed != expected:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
