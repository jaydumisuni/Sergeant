from __future__ import annotations

from pathlib import Path

import pytest

from main_review.cpl_campaign import advance_campaign, advance_tenfold_frontier, build_cpl_campaign
from main_review.operational_contracts import task_status_packet
from main_review.workspace_interfaces import dispatch_authorized_requests


def _campaign(tmp_path: Path) -> dict:
    source = tmp_path / "src" / "auth.py"
    source.parent.mkdir(parents=True)
    source.write_text("def refresh(token):\n    return token\n", encoding="utf-8")
    return build_cpl_campaign(
        tmp_path,
        ["src/auth.py", "pyproject.toml"],
        officer_reports=[],
        admitted=[],
        advisory=[],
        rejected=[],
        assurances=[],
        cpl={"status": "disabled", "passes": []},
        offline={"complete": True},
    )


def _status(task: dict, status: str, suffix: str = "x") -> dict:
    kwargs = {
        "mission_id": task["mission_id"],
        "task_id": task["task_id"],
        "worker_id": f"Private-{suffix}",
        "status": status,
    }
    if status == "completed":
        kwargs.update(
            source_revision=f"frozen-{suffix}",
            evidence_digest="sha256:" + suffix[0].lower() * 64,
            provenance={"adapter": "repository", "observed_at": "2026-09-07T00:00:00Z"},
        )
    return task_status_packet(**kwargs)


def test_blocked_and_failed_lanes_require_explicit_cpl_reauthorization(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    field = [
        next(item for item in campaign["tasks"] if item["responsible_officer"] == officer)
        for officer in ("Scout", "Engineer")
    ]
    blocked = advance_tenfold_frontier(
        campaign["tasks"],
        campaign["tenfold_execution"],
        [_status(field[0], "blocked")],
    )
    failed = advance_tenfold_frontier(
        campaign["tasks"],
        blocked,
        [_status(field[1], "failed")],
    )
    assert field[0]["task_id"] not in failed["frontier_task_ids"]
    assert field[1]["task_id"] not in failed["frontier_task_ids"]

    with pytest.raises(ValueError, match="current Cpl-authorized frontier"):
        advance_tenfold_frontier(campaign["tasks"], failed, [_status(field[0], "in_progress")])

    recovered = advance_tenfold_frontier(
        campaign["tasks"],
        failed,
        [],
        reauthorized_task_ids=[field[0]["task_id"], field[1]["task_id"]],
    )
    assert field[0]["task_id"] in recovered["frontier_task_ids"]
    assert field[1]["task_id"] in recovered["frontier_task_ids"]
    assert recovered["task_status"][field[0]["task_id"]] == "authorized"
    assert recovered["task_status"][field[1]["task_id"]] == "authorized"


def test_advance_campaign_rejects_malformed_persisted_frontier_state(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    campaign["tenfold_execution"] = {
        "schema_version": "sergeant.tenfold-frontier.v1",
        "task_status": {},
    }
    with pytest.raises(ValueError, match="malformed Tenfold execution state"):
        advance_campaign(campaign, [])


def test_authorized_tasks_keeps_one_meaning_and_frontier_is_separate(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    all_task_ids = [item["task_id"] for item in campaign["tasks"]]
    first_round = campaign["council_rounds"][0]
    assert first_round["authorized_tasks"] == all_task_ids
    assert first_round["frontier_task_ids"] == campaign["tenfold_execution"]["frontier_task_ids"]

    initial_frontier_tasks = [
        item for item in campaign["tasks"] if item["task_id"] in campaign["tenfold_execution"]["frontier_task_ids"]
    ]
    status_packets = [
        _status(task, "completed", chr(ord("a") + index))
        for index, task in enumerate(initial_frontier_tasks)
    ]
    advanced = advance_campaign(campaign, [], status_packets=status_packets)
    latest_round = advanced["council_rounds"][-1]
    assert latest_round["authorized_tasks"] == all_task_ids
    assert latest_round["frontier_task_ids"] == advanced["tenfold_execution"]["frontier_task_ids"]


def test_off_frontier_workspace_and_research_requests_remain_visible(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    challenger = next(item for item in campaign["tasks"] if item["responsible_officer"] == "Challenger")
    challenger_workspace = next(
        item for item in campaign["workspace_requests"] if item["task_id"] == challenger["task_id"]
    )
    scout_research = campaign["research_requests"][0]
    campaign["research_requests"] = [
        {**scout_research, "request_id": "deferred-research", "task_id": challenger["task_id"]}
    ]

    result = dispatch_authorized_requests(campaign)
    workspace_row = next(
        item for item in result["workspace_results"] if item["request_id"] == challenger_workspace["request_id"]
    )
    research_row = next(item for item in result["research_results"] if item["request_id"] == "deferred-research")
    assert workspace_row["status"] == "deferred"
    assert research_row["status"] == "deferred"
    assert "currently unblocked Tenfold frontier" in workspace_row["reason"]
    assert "currently unblocked Tenfold frontier" in research_row["reason"]


def test_dependent_dispatch_fails_closed_if_frozen_binding_is_missing(tmp_path: Path) -> None:
    campaign = _campaign(tmp_path)
    field = [
        next(item for item in campaign["tasks"] if item["responsible_officer"] == officer)
        for officer in ("Scout", "Engineer", "Medic")
    ]
    advanced = advance_campaign(
        campaign,
        [],
        status_packets=[
            _status(field[0], "completed", "a"),
            _status(field[1], "completed", "b"),
            _status(field[2], "completed", "c"),
        ],
    )
    challenger = next(item for item in advanced["tasks"] if item["responsible_officer"] == "Challenger")
    advanced["tenfold_execution"]["dependency_bindings"][challenger["task_id"]] = []

    class RecordingWorkspace:
        name = "recording-workspace"
        called: list[str] = []

        def capabilities(self) -> set[str]:
            return {"repository", "test_runner", "runtime"}

        def execute(self, request: dict, task: dict) -> dict:
            self.called.append(task["task_id"])
            return {"request_id": request["request_id"], "task_id": task["task_id"], "status": "completed"}

    adapter = RecordingWorkspace()
    result = dispatch_authorized_requests(advanced, workspace=adapter)
    challenger_row = next(
        item for item in result["workspace_results"] if item["task_id"] == challenger["task_id"]
    )
    assert challenger["task_id"] not in adapter.called
    assert challenger_row["status"] == "rejected"
    assert "frozen dependency bindings" in challenger_row["reason"]
