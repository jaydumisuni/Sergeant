from pathlib import Path
import hashlib
import json

import pytest

from scripts.run_project_driven_learning import _candidate_packet, _write_evidence_manifest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "project-driven-self-learning.yml"
MANIFEST = ROOT / ".github" / "self-learning" / "project-driven" / "techguycheckm8-round-1.json"
RUNNER = ROOT / "scripts" / "run_project_driven_learning.py"
CONTROLLED_RUNNER = ROOT / "scripts" / "run_controlled_self_learning.py"


def test_project_driven_learning_workflow_is_validation_only_and_read_only() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "permissions: {}" in text
    assert "persist-credentials: false" in text
    assert "contents: write" not in text
    assert "pull-requests: write" not in text
    assert "models: read" not in text
    assert "GITHUB_TOKEN" not in text
    assert "github_models" not in text
    assert "\n  learn:\n" not in text
    assert "\n  handoff:\n" not in text
    assert "scripts/run_project_driven_learning.py" in text
    assert "scripts/resume_project_learning_worker.py" in text
    assert "scripts/project_learning_workers.py" in text
    assert "scripts/export_learning_proposals.py" in text
    assert "tests/test_project_learning_workers.py" in text
    assert "tests/test_resume_project_learning_worker.py" in text
    assert "from scripts.run_project_driven_learning import _candidate_packet" in text
    assert 'test("^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")' in text
    assert '"execution_lane": "oracle-direct-terminal"' in text
    assert '"github_inference_enabled": false' in text


def test_techguycheckm8_project_round_binds_exact_harvest_candidates() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "sergeant.project-learning-round.v1"
    assert payload["candidate_count"] == 2
    assert payload["expected_case_ids"] == [
        "learn-tgcheckm8-checksum-path-namespace-20260723",
        "learn-tgcheckm8-checkout-credential-boundary-20260723",
    ]
    assert payload["signal_paths"] == [
        ".github/self-learning/signals/tgcheckm8-checksum-path-namespace-2026-07-23.json",
        ".github/self-learning/signals/tgcheckm8-checkout-credential-boundary-2026-07-23.json",
    ]
    assert payload["authority"] == {
        "execution_lane": "oracle-direct-terminal",
        "direct_terminal_authorization_flag": "--owner-authorized",
        "may_auto_promote": False,
        "may_auto_merge": False,
        "final_verdict": "Sergeant",
    }


def test_candidate_packet_resolves_only_the_manifest_signal_files(monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    packet = _candidate_packet(MANIFEST.relative_to(ROOT), "a" * 40)

    assert packet["candidate_count"] == 2
    assert packet["execution_lane"] == "oracle-direct-terminal"
    assert [row["case_id"] for row in packet["candidates"]] == [
        "learn-tgcheckm8-checksum-path-namespace-20260723",
        "learn-tgcheckm8-checkout-credential-boundary-20260723",
    ]
    assert [row["signal_path"] for row in packet["candidates"]] == [
        ".github/self-learning/signals/tgcheckm8-checksum-path-namespace-2026-07-23.json",
        ".github/self-learning/signals/tgcheckm8-checkout-credential-boundary-2026-07-23.json",
    ]


def test_candidate_packet_rejects_missing_round_id(tmp_path: Path) -> None:
    manifest = tmp_path / "round.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "sergeant.project-learning-round.v1",
                "candidate_count": 1,
                "expected_case_ids": ["case-a"],
                "signal_paths": ["signal-a.json"],
                "authority": {
                    "execution_lane": "oracle-direct-terminal",
                    "direct_terminal_authorization_flag": "--owner-authorized",
                    "may_auto_promote": False,
                    "may_auto_merge": False,
                    "final_verdict": "Sergeant",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="requires round_id"):
        _candidate_packet(manifest, "a" * 40)


def test_candidate_packet_rejects_path_traversing_case_id(tmp_path: Path) -> None:
    manifest = tmp_path / "round.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "sergeant.project-learning-round.v1",
                "round_id": "unsafe-case-id-proof",
                "candidate_count": 1,
                "expected_case_ids": ["../outside"],
                "signal_paths": ["does-not-need-to-exist.json"],
                "authority": {
                    "execution_lane": "oracle-direct-terminal",
                    "direct_terminal_authorization_flag": "--owner-authorized",
                    "may_auto_promote": False,
                    "may_auto_merge": False,
                    "final_verdict": "Sergeant",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="filesystem-safe path segment"):
        _candidate_packet(manifest, "a" * 40)


def test_direct_terminal_evidence_manifest_hashes_durable_files_and_excludes_checkout(tmp_path: Path) -> None:
    authority = tmp_path / "authority.json"
    authority.write_text('{"owner":true}\n', encoding="utf-8")
    (tmp_path / "terminal-result.json").write_text('{"result":"bounded"}\n', encoding="utf-8")
    case_dir = tmp_path / "round" / "cases" / "case-a"
    case_dir.mkdir(parents=True)
    (case_dir / "teacher.json").write_text('{"role":"teacher"}\n', encoding="utf-8")
    checkout = tmp_path / "round" / "checkouts" / "case-a" / ".git" / "objects"
    checkout.mkdir(parents=True)
    (checkout / "secret-transient-object").write_bytes(b"do-not-hash-checkout")

    manifest = _write_evidence_manifest(tmp_path)
    rows = {row["path"]: row for row in manifest["files"]}

    assert set(rows) == {
        "authority.json",
        "terminal-result.json",
        "round/cases/case-a/teacher.json",
    }
    assert rows["authority.json"]["sha256"] == hashlib.sha256(authority.read_bytes()).hexdigest()
    assert manifest["excluded_transient_paths"] == ["round/checkouts/**"]
    written = json.loads((tmp_path / "evidence-manifest.json").read_text(encoding="utf-8"))
    assert written == manifest


def test_direct_terminal_runner_preserves_governed_worker_boundary() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    controlled = CONTROLLED_RUNNER.read_text(encoding="utf-8")

    assert 'parser.add_argument("--owner-authorized", action="store_true")' in text
    assert "direct project learning requires a clean frozen Sergeant worktree" in text
    assert "manifest case resolved from unexpected signal path" in text
    assert 'os.environ["SERGEANT_LLM_ENABLED"] = "false"' in text
    assert 'os.environ["SERGEANT_CPL_ENABLED"] = "false"' in text
    assert 'os.environ["SERGEANT_LEARNING_BACKEND"] = "cloudflare"' in text
    assert "worker_request_fn=project_worker_request" in text
    assert "export_proposals(queue" in text
    assert '"evidence_manifest_path": "evidence-manifest.json"' in text
    assert "_write_evidence_manifest(args.output_dir)" in text
    assert '"automatic_promotions": 0' in text
    assert '"automatic_merges": 0' in text
    assert "worker_request_fn: WorkerRequest = _default_worker_request" in controlled
    assert "packet = worker_request_fn(role, truth)" in controlled
