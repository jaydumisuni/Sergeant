from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/superpowers/plans/2026-09-07-sae-30-through-100.md"
ROADMAP = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"

EXPECTED_NODES = (
    "SAE-30",
    "SAE-R1",
    "SAE-50",
    "SAE-60",
    "SAE-70",
    "SAE-80",
    "SAE-90",
    "SAE-R2",
    "SAE-100",
)

EXPECTED_DEPENDENCIES = {
    "SAE-30": {"SAE-00", "SPIKE-ID", "SPIKE-EXT"},
    "SAE-R1": {"SAE-10", "SAE-20", "SAE-40"},
    "SAE-50": {"SAE-10", "SAE-20", "SAE-40"},
    "SAE-60": {"SAE-20", "SAE-30", "SAE-50", "SPIKE-SEM"},
    "SAE-70": {"SAE-20", "SAE-50", "SAE-60"},
    "SAE-80": {"SAE-30", "SAE-40", "SAE-50", "SAE-60", "SAE-70"},
    "SAE-90": {"SAE-70", "SAE-80"},
    "SAE-R2": {"SAE-R1", "SAE-30", "SAE-60", "SAE-70", "SAE-80", "SAE-90"},
    "SAE-100": {"SAE-70", "SAE-90", "SAE-R2"},
}


def _dependency_registry(text: str) -> dict[str, set[str]]:
    marker = "## 15. Dependency registry v1.1"
    assert marker in text
    block = text.split(marker, 1)[1].split("```yaml", 1)[1].split("```", 1)[0]
    result: dict[str, set[str]] = {}
    current: str | None = None
    for raw in block.splitlines():
        if not raw.strip():
            continue
        if raw == raw.lstrip():
            key, remainder = raw.split(":", 1)
            key = key.strip()
            remainder = remainder.strip()
            if remainder.startswith("["):
                inner = remainder[1:-1].strip()
                result[key] = {item.strip() for item in inner.split(",") if item.strip()}
                current = None
            else:
                result[key] = set()
                current = key
        elif current and raw.strip().startswith("- "):
            result[current].add(raw.strip()[2:].strip())
    return result


def test_execution_plan_covers_every_roadmap_node_through_sae100() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    for node in EXPECTED_NODES:
        assert node in plan
    task_numbers = [int(value) for value in re.findall(r"^### Task (\d+):", plan, re.MULTILINE)]
    assert task_numbers == list(range(1, 19))
    assert "SAE-100 PROVEN Closeout" in plan


def test_execution_plan_dependency_order_matches_frozen_roadmap() -> None:
    roadmap = ROADMAP.read_text(encoding="utf-8")
    registry = _dependency_registry(roadmap)
    for node, expected in EXPECTED_DEPENDENCIES.items():
        assert registry[node] == expected


def test_execution_plan_preserves_activation_and_independence_law() -> None:
    plan = PLAN.read_text(encoding="utf-8")
    roadmap = ROADMAP.read_text(encoding="utf-8")
    assert "No partial Assurance Evolution generation activates before `SAE-170` Genesis Exit." in plan
    assert "project-controlled AI review is never relabeled `INDEPENDENT`" in plan
    assert "Only here does normal Assurance Evolution verdict authority become available" in roadmap
    assert "SHADOW_OR_QUALIFICATION_ONLY" in plan
