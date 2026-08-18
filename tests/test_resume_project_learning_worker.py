from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from main_review.self_learning_queue import (
    add_case,
    attach_worker,
    canonical_digest,
    new_queue,
    transition,
    write_queue,
)
from scripts import resume_project_learning_worker as resume


AUTHORITY = "a" * 40
CASE_ID = "case-resume"


def _evidence_root(
    tmp_path: Path,
    *,
    workers: tuple[str, ...] = (),
    errors: dict[str, str] | None = None,
    terminal_candidate_count: int | None = None,
) -> Path:
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
    candidate_count = terminal_candidate_count if terminal_candidate_count is not None else 1
    (root / "terminal-result.json").write_text(
        json.dumps({
            "schema_version": "sergeant.project-learning-terminal-result.v1",
            "authority_head": AUTHORITY,
            "round_id": "round-resume",
            "candidate_count": candidate_count,
            "automatic_promotions": 0,
            "automatic_merges": 0,
        }) + "\n",
        encoding="utf-8",
    )
    resume._write_evidence_manifest(root)
    return root


def _argv(
    root: Path,
    role: str,
    *,
    owner_authorized: bool = True,
    case_id: str = CASE_ID,
) -> list[str]:
    argv = [
        "resume_project_learning_worker.py",
        "--evidence-dir",
        str(root),
        "--case-id",
        case_id,
        "--role",
        role,
        "--authority-head",
        AUTHORITY,
    ]
    if owner_authorized:
        argv.append("--owner-authorized")
    return argv


def _invoke(monkeypatch, root: Path, role: str, packet: dict) -> int:
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(resume, "project_worker_request", lambda worker_role, truth: dict(packet))
    monkeypatch.setattr(sys, "argv", _argv(root, role))
    return resume.main()


def test_resume_requires_explicit_owner_authorization(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher", owner_authorized=False))

    with pytest.raises(SystemExit, match="explicit --owner-authorized"):
        resume.main()


def test_resume_rejects_non_segment_case_id_before_path_resolution(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher", case_id="../case-resume"))

    with pytest.raises(SystemExit, match="filesystem-safe path segment"):
        resume.main()


def test_resume_rejects_authority_head_mismatch(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    monkeypatch.setattr(resume, "_git_head", lambda: "d" * 40)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="head mismatch"):
        resume.main()


def test_resume_rejects_dirty_worktree(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: " M scripts/file.py")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="clean frozen Sergeant worktree"):
        resume.main()


def test_resume_requires_preserved_evidence_manifest(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    (root / "evidence-manifest.json").unlink()
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="preserved evidence manifest is missing"):
        resume.main()


def test_resume_rejects_tampered_preserved_truth_before_worker(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    truth_path = root / "round" / "cases" / CASE_ID / "truth-packet.json"
    truth_path.write_text(json.dumps({"case_id": CASE_ID, "fixing_diff": "tampered"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="integrity mismatch.*_write_evidence_manifest"):
        resume.main()


def test_resume_rejects_truth_digest_mismatch_even_if_file_manifest_was_refreshed(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    truth_path = root / "round" / "cases" / CASE_ID / "truth-packet.json"
    truth_path.write_text(json.dumps({"case_id": CASE_ID, "fixing_diff": "tampered"}) + "\n", encoding="utf-8")
    resume._write_evidence_manifest(root)
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="truth packet digest mismatch"):
        resume.main()


def test_resume_rejects_unsafe_path_in_preserved_manifest(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    manifest_path = root / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][0]["path"] = "../authority.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="unsafe or duplicate path"):
        resume.main()


def test_resume_requires_terminal_result_to_remain_manifest_bound(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    manifest_path = root / "evidence-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    terminal_row = next(row for row in manifest["files"] if row["path"] == "terminal-result.json")
    manifest["files"].remove(terminal_row)
    manifest["file_count"] -= 1
    manifest["total_bytes"] -= terminal_row["size_bytes"]
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="required preserved evidence is not bound"):
        resume.main()


def test_resume_rejects_already_preserved_role(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path, workers=("teacher",))
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="worker already preserved"):
        resume.main()


def test_resume_rejects_truth_packet_case_mismatch(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    truth_path = root / "round" / "cases" / CASE_ID / "truth-packet.json"
    truth = {"case_id": "different-case", "fixing_diff": "diff"}
    truth_path.write_text(json.dumps(truth) + "\n", encoding="utf-8")
    queue_path = root / "round" / "learning-queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    queue["cases"][0]["artifacts"]["truth_packet"]["digest"] = canonical_digest(truth)
    write_queue(queue, queue_path)
    resume._write_evidence_manifest(root)
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="truth packet case binding mismatch"):
        resume.main()


def test_resume_reports_worker_failure_as_governed_error(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(tmp_path)
    monkeypatch.setattr(resume, "_git_head", lambda: AUTHORITY)
    monkeypatch.setattr(resume, "_git_status_porcelain", lambda: "")

    def fail_worker(role, truth):
        raise resume.LearningWorkerError("bounded worker failure")

    monkeypatch.setattr(resume, "project_worker_request", fail_worker)
    monkeypatch.setattr(sys, "argv", _argv(root, "teacher"))

    with pytest.raises(SystemExit, match="project-learning teacher worker failed: bounded worker failure"):
        resume.main()
    assert not (root / "round" / "cases" / CASE_ID / "teacher.json").exists()


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


def test_resume_two_workers_sequentially_reverify_regenerated_manifest(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(
        tmp_path,
        workers=("defender",),
        errors={"teacher": "temporary failure", "prosecutor": "temporary failure"},
    )
    teacher = {"role": "teacher", "case_id": CASE_ID, "generalized_mechanism": "bounded"}
    prosecutor = {"role": "prosecutor", "case_id": CASE_ID, "claims": []}

    assert _invoke(monkeypatch, root, "teacher", teacher) == 0
    verified_after_teacher = resume._verify_preserved_evidence(root)
    assert "round/learning-queue.json" in verified_after_teacher

    assert _invoke(monkeypatch, root, "prosecutor", prosecutor) == 0

    queue = json.loads((root / "round" / "learning-queue.json").read_text(encoding="utf-8"))
    case = queue["cases"][0]
    assert case["state"] == "council_complete"
    assert set(case["workers"]) == {"teacher", "prosecutor", "defender"}
    assert "worker_errors" not in case
    verified_after_prosecutor = resume._verify_preserved_evidence(root)
    assert "terminal-result.json" in verified_after_prosecutor


def test_resume_preserves_authorized_candidate_count_and_records_queue_count(tmp_path: Path, monkeypatch) -> None:
    root = _evidence_root(
        tmp_path,
        workers=("prosecutor",),
        terminal_candidate_count=2,
    )
    packet = {"role": "teacher", "case_id": CASE_ID, "generalized_mechanism": "bounded"}

    assert _invoke(monkeypatch, root, "teacher", packet) == 0

    terminal = json.loads((root / "terminal-result.json").read_text(encoding="utf-8"))
    assert terminal["candidate_count"] == 2
    assert terminal["queue_case_count"] == 1


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
