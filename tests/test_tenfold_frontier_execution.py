from __future__ import annotations

from pathlib import Path

import pytest

from main_review.cpl_campaign import (
    advance_campaign,
    advance_tenfold_frontier,
    build_cpl_campaign,
    build_tenfold_frontier,
)
from main_review.operational_contracts import task_packet, task_status_packet, validate_task_status_packet
from main_review.workspace_interfaces import dispatch_authorized_requests


def _tasks() -> list[dict]:
    mission_id = "mission-tenfold"
    scout = task_packet(
        mission_id=mission_id,
        officer="Scout",
        objective="Map repository",
        scope=("src/a.py",),
        questions=("What changed?",),
        required_evidence=("path",),
        allowed_capabilities=("repository_reader",),
        human_equivalent_workers=2,
    )
    security = task_packet(
        mission_id=mission_id,
        officer="Medic",
        objective="Trace trust boundary",
        scope=("src/auth.py",),
        questions=("Is it safe?",),
        required_evidence=("trace",),
        allowed_capabilities=("security_scanner",),
        human_equivalent_workers=5,
    )
    downstream = task_packet(
        mission_id=mission_id,
        officer="Engineer",
        objective="Reconcile implementation",
        scope=("src/a.py",),
        questions=("Does the contract hold?",),
        required_evidence=("trace",),
        allowed_capabilities=("repository_reader",),
        human_equivalent_workers=2,
        dependencies=(scout["task_id"],),
    )
    judge = task_packet(
        mission_id=mission_id,
        officer="Judge",
        objective="Adjudicate",
        scope=("src/a.py", "src/auth.py"),
        questions=("Is proof sufficient?",),
        required_evidence=("ledger",),
        allowed_capabilities=("evidence_ledger",),
        dependencies=(security["task_id"], downstream["task_id"]),
        execution_mode="officer",
    )
    return [scout, security, downstream, judge]


def _completed(task: dict, suffix: str) -> dict:
    return task_status_packet(
        mission_id=task["mission_id"],
        task_id=task["task_id"],
        worker_id=f"Private-{suffix}",
        status="completed",
        source_revision=f"frozen-{suffix}",
        evidence_digest="sha256:" + suffix.lower()[0] * 64,
        provenance={"adapter": "repository", "observed_at": "2026-09-06T22:00:00Z"},
    )


def test_tenfold_frontier_occupies_every_independent_unblocked_task() -> None:
    tasks = _tasks()
    state = build_tenfold_frontier(tasks)

    scout = next(item for item in tasks if item["responsible_officer"] == "Scout")
    security = next(item for item in tasks if item["responsible_officer"] == "Medic")
    downstream = next(item for item in tasks if item["responsible_officer"] == "Engineer")

    assert state["frontier_task_ids"] == [scout["task_id"], security["task_id"]]
    assert {item["task_id"] for item in state["allocations"]} == {scout["task_id"], security["task_id"]}
    assert state["allocated_private_count"] == 70
    assert next(item for item in state["blocked_tasks"] if item["task_id"] == downstream["task_id"])["waiting_for"] == [scout["task_id"]]
    assert state["authority_boundary"]["sergeant"] == "final_verdict_only"
    assert state["authority_boundary"]["cpl"] == "frontier_command"
    assert state["transport"]["hermes"] == "packet_transport_only"
    assert state["transport"]["may_schedule"] is False
    assert state["transport"]["may_issue_verdict"] is False


def test_completed_upstream_unlocks_downstream_without_parking_independent_lane() -> None:
    tasks = _tasks()
    initial = build_tenfold_frontier(tasks)
    scout = next(item for item in tasks if item["responsible_officer"] == "Scout")
    security = next(item for item in tasks if item["responsible_officer"] == "Medic")
    downstream = next(item for item in tasks if item["responsible_officer"] == "Engineer")

    advanced = advance_tenfold_frontier(tasks, initial, [_completed(scout, "a")])

    assert advanced["frontier_task_ids"] == [security["task_id"], downstream["task_id"]]
    assert advanced["reallocation"]["completed_task_ids"] == [scout["task_id"]]
    assert advanced["reallocation"]["newly_unblocked_task_ids"] == [downstream["task_id"]]
    binding = advanced["dependency_bindings"][downstream["task_id"]][0]
    assert binding == {
        "task_id": scout["task_id"],
        "source_revision": "frozen-a",
        "evidence_digest": "sha256:" + "a" * 64,
        "provenance": {"adapter": "repository", "observed_at": "2026-09-06T22:00:00Z"},
    }


def test_status_packets_fail_closed_and_cannot_acquire_command_authority() -> None:
    tasks = _tasks()
    scout = next(item for item in tasks if item["responsible_officer"] == "Scout")
    packet = _completed(scout, "a")
    assert validate_task_status_packet(packet, scout) == packet

    with pytest.raises(ValueError):
        validate_task_status_packet({**packet, "verdict": "PASS"}, scout)
    with pytest.raises(ValueError):
        task_status_packet(
            mission_id=scout["mission_id"], task_id=scout["task_id"], worker_id="Private-bad",
            status="completed", source_revision="", evidence_digest="sha256:" + "a" * 64,
            provenance={"adapter": "repository"},
        )
    with pytest.raises(ValueError):
        task_status_packet(
            mission_id=scout["mission_id"], task_id=scout["task_id"], worker_id="Private-bad",
            status="completed", source_revision="frozen-a", evidence_digest="not-a-digest",
            provenance={"adapter": "repository"},
        )


def test_blocked_downstream_cannot_self_complete_or_self_authorize() -> None:
    tasks = _tasks()
    initial = build_tenfold_frontier(tasks)
    downstream = next(item for item in tasks if item["responsible_officer"] == "Engineer")

    with pytest.raises(ValueError, match="current Cpl-authorized frontier"):
        advance_tenfold_frontier(tasks, initial, [_completed(downstream, "d")])

    unauthorized = task_status_packet(
        mission_id=downstream["mission_id"],
        task_id=downstream["task_id"],
        worker_id="Private-d",
        status="authorized",
    )
    with pytest.raises(ValueError, match="current Cpl-authorized frontier"):
        advance_tenfold_frontier(tasks, initial, [unauthorized])


def test_frontier_rejects_unknown_dependencies_and_cycles() -> None:
    tasks = _tasks()
    broken = [dict(item) for item in tasks]
    broken[0]["dependencies"] = ["missing-task"]
    with pytest.raises(ValueError, match="unknown dependency"):
        build_tenfold_frontier(broken)

    left = task_packet(
        mission_id="cycle", officer="Scout", objective="left", scope=("a",),
        questions=("q",), required_evidence=("e",), allowed_capabilities=("repository_reader",),
    )
    right = task_packet(
        mission_id="cycle", officer="Engineer", objective="right", scope=("b",),
        questions=("q",), required_evidence=("e",), allowed_capabilities=("repository_reader",),
        dependencies=(left["task_id"],),
    )
    left["dependencies"] = [right["task_id"]]
    with pytest.raises(ValueError, match="cycle"):
        build_tenfold_frontier([left, right])


def test_cpl_campaign_saturates_independent_field_frontier_and_gates_adapters(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def refresh(token):\n    return token\n", encoding="utf-8")
    campaign = build_cpl_campaign(
        tmp_path,
        ["src/auth.py", "pyproject.toml"],
        officer_reports=[], admitted=[], advisory=[], rejected=[], assurances=[],
        cpl={"status": "disabled", "passes": []}, offline={"complete": True},
    )
    frontier_ids = set(campaign["tenfold_execution"]["frontier_task_ids"])
    frontier_officers = {
        item["responsible_officer"] for item in campaign["tasks"] if item["task_id"] in frontier_ids
    }
    assert frontier_officers == {"Scout", "Engineer", "Medic"}
    challenger = next(item for item in campaign["tasks"] if item["responsible_officer"] == "Challenger")
    assert challenger["task_id"] not in frontier_ids

    class RecordingWorkspace:
        name = "recording"
        called: list[str] = []
        def capabilities(self) -> set[str]:
            return {"repository", "test_runner", "runtime"}
        def execute(self, request: dict, task: dict) -> dict:
            self.called.append(task["task_id"])
            return {"request_id": request["request_id"], "task_id": task["task_id"], "status": "completed"}

    adapter = RecordingWorkspace()
    dispatch_authorized_requests(campaign, workspace=adapter)
    expected_workspace_frontier = {
        item["task_id"] for item in campaign["workspace_requests"] if item["task_id"] in frontier_ids
    }
    assert set(adapter.called) == expected_workspace_frontier
    assert challenger["task_id"] not in adapter.called

    field = [
        next(item for item in campaign["tasks"] if item["responsible_officer"] == officer)
        for officer in ("Scout", "Engineer", "Medic")
    ]
    updated = advance_campaign(
        campaign,
        [],
        status_packets=[_completed(field[0], "a"), _completed(field[1], "b"), _completed(field[2], "c")],
    )
    assert challenger["task_id"] in updated["tenfold_execution"]["frontier_task_ids"]
    bindings = updated["tenfold_execution"]["dependency_bindings"][challenger["task_id"]]
    assert {item["task_id"] for item in bindings} == {item["task_id"] for item in field}
    assert {item["source_revision"] for item in bindings} == {"frozen-a", "frozen-b", "frozen-c"}


def test_dependent_adapter_request_carries_exact_frozen_upstream_bindings(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "auth.py").write_text("def refresh(token):\n    return token\n", encoding="utf-8")
    campaign = build_cpl_campaign(
        tmp_path,
        ["src/auth.py", "pyproject.toml"],
        officer_reports=[], admitted=[], advisory=[], rejected=[], assurances=[],
        cpl={"status": "disabled", "passes": []}, offline={"complete": True},
    )
    field = [
        next(item for item in campaign["tasks"] if item["responsible_officer"] == officer)
        for officer in ("Scout", "Engineer", "Medic")
    ]
    challenger = next(item for item in campaign["tasks"] if item["responsible_officer"] == "Challenger")
    updated = advance_campaign(
        campaign,
        [],
        status_packets=[_completed(field[0], "a"), _completed(field[1], "b"), _completed(field[2], "c")],
    )

    class BindingWorkspace:
        name = "binding-workspace"
        seen: list[dict] = []
        def capabilities(self) -> set[str]:
            return {"repository", "test_runner", "runtime"}
        def execute(self, request: dict, task: dict) -> dict:
            if task["task_id"] == challenger["task_id"]:
                self.seen = list(request.get("dependency_bindings", []))
            return {"request_id": request["request_id"], "task_id": task["task_id"], "status": "completed"}

    adapter = BindingWorkspace()
    dispatch_authorized_requests(updated, workspace=adapter)
    assert {item["task_id"] for item in adapter.seen} == {item["task_id"] for item in field}
    assert {item["source_revision"] for item in adapter.seen} == {"frozen-a", "frozen-b", "frozen-c"}
    assert {item["evidence_digest"] for item in adapter.seen} == {
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "sha256:" + "c" * 64,
    }
