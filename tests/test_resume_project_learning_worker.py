from __future__ import annotations

import json
import sys
from pathlib import Path

from main_review.self_learning_queue import (
    add_case,
    attach_worker,
    new_queue,
    transition,
    write_queue,
)
from scripts import resume_project_learning_worker as resume


AUTHORITY = "a" * 40
CASE_ID = "case-resume"


def _evidence_root(tmp_path: Path, *, workers: tuple[str, ...] = (), errors: dict[str, str] | None = None) -> Path:
    root = tmp_path / "evidence"
    case_dir = root / "round" / "cases" / CASE_ID
    case_dir.mkdir(parents=True)
    authority = {
        "schema_version": "sergeant.project-learning-terminal-authority.v1",
        "authority_head": AUTHORITY,
        "target_branch": "learning/test",
        "round_id": "round-resume",
        "execution_lane": "oracle-direct-terminal",
        "owner_authorized": True,
        "automatic_promotions": 0,
        "automatic_merges": 0,
        "final_verdict": "Sergeant",
    }
    (root / "authority.json").write_text(json.dumps(authority) + "\n", encoding="utf-8")

    queue = new_queue("round-resume", authority_head=AUTHORITY, target_branch="learning/test")
    add_case(
        queue,
        {
            "case_id": CASE_ID,
            "repository": "jaydumisuni/example",
            "source_event_url": "https://github.com/jaydumisuni/example/commit/abc",
            "defective_ref": "b" * 40,
            "fixing_ref": "c" * 40,
            "scored_paths": ["src/example.py"],
            "language": "python",
        },
    )
    transition(queue, CASE_ID, "blind_frozen", artifact_name="blind_result", artifact={"frozen": True})
    truth = {"case_id": CASE_ID, "fixing_diff": "diff"}
    transition(queue, CASE_ID, "truth_revealed", artifact_name="truth_packet", artifact=truth)
    case = queue["cases"][0]
    for role in workers:
        packet = {"role": role, "case_id": CASE_ID}
        if role == "defender":
            packet["verdict"] = "supports"
        attach_worker(queue, CASE_ID, role, packet)
        (case_dir / f"{role}.json").write_text(json.dumps(packet) + "\n", encoding="utf-8")
    if errors:
        case["worker_errors"] = dict(errors)
    write_queue(queue, root / "round" / "learning-queue.json")
    (case_dir / "truth-packet.json").write_text(json.dumps(truth) + "\n", encoding="utf-8")
    (root / "round" / "summary.json").write_text(
        json.dumps({"week_id": "round-resume", "worker_error_cases": int(bool(errors))}) + "\n",
        encoding="utf-8",
    )
    return root


def _invoke(monkeypatch, root: Path, role: str, packet: dict) -> int:
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(resume, "project_worker_request", lambda worker_role, truth: dict(packet))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "resume_project_learning_worker.py",
            "--evidence-dir",
            str(root),
            "--case-id",
            CASE_ID,
            "--role",
            role,
            "--authority-head",
            AUTHORITY,
            "--owner-authorized",
        ],
    )
    return resume.main()


def test_resume_worker_preserves_completed_workers_and_clears_role_error(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(
        tmp_path,
        workers=("prosecutor",),
        errors={"teacher": "temporary failure", "defender": "temporary failure"},
    )
    packet = {"role": "teacher", "case_id": CASE_ID, "generalized_mechanism": "bounded"}

    assert _invoke(monkeypatch, root, "teacher", packet) == 0

    queue = json.loads((root / "round" / "learning-queue.json").read_text(encoding="utf-8"))
    case = queue["cases"][0]
    assert case["state"] == "truth_revealed"
    assert set(case["workers"]) == {"teacher", "prosecutor"}
    assert case["worker_errors"] == {"defender": "temporary failure"}
    assert (root / "evidence-manifest.json").is_file()


def test_resume_final_worker_completes_council_and_exports_bounded_proposal(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(
        tmp_path,
        workers=("teacher", "prosecutor"),
        errors={"defender": "temporary failure"},
    )
    packet = {"role": "defender", "case_id": CASE_ID, "verdict": "supports"}

    assert _invoke(monkeypatch, root, "defender", packet) == 0

    queue = json.loads((root / "round" / "learning-queue.json").read_text(encoding="utf-8"))
    case = queue["cases"][0]
    assert case["state"] == "council_complete"
    assert "worker_errors" not in case
    index = json.loads(
        (root / "learning" / "proposals" / "round-resume" / "index.json").read_text(encoding="utf-8")
    )
    assert index["proposal_count"] == 1
    proposal = json.loads(
        (root / "learning" / "proposals" / "round-resume" / f"{CASE_ID}.json").read_text(encoding="utf-8")
    )
    assert "fixing_diff" not in json.dumps(proposal)
    assert proposal["authority"]["may_auto_promote"] is False
    manifest = json.loads((root / "evidence-manifest.json").read_text(encoding="utf-8"))
    assert manifest["file_count"] > 0
