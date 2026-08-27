from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs/61-sergeant-assurance-evolution-freeze-manifest.json"
ROADMAP_PATH = ROOT / "docs/59-sergeant-assurance-evolution-roadmap.md"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _dependency_registry() -> dict[str, list[str]]:
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    marker = "## 15. Dependency registry v1.1"
    assert marker in text
    section = text.split(marker, 1)[1]
    block = section.split("```yaml", 1)[1].split("```", 1)[0]

    dependencies: dict[str, list[str]] = {}
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
                dependencies[key] = [item.strip() for item in inner.split(",") if item.strip()]
                current = None
            else:
                dependencies[key] = []
                current = key
            continue
        if current and raw.strip().startswith("- "):
            dependencies[current].append(raw.strip()[2:].strip())
    return dependencies


def test_assurance_evolution_freeze_manifest_binds_authority_documents() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == "sergeant.assurance-evolution-freeze-manifest.v1"
    assert manifest["authority_state"] == "owner_approved_isolated_roadmap_authority"
    assert manifest["implementation_state"] == "not_started"
    assert manifest["normal_sergeant_activation"] == "unchanged_until_SAE-170_genesis_exit"

    for document in manifest["documents"]:
        path = ROOT / document["path"]
        assert path.is_file(), document["path"]
        assert _git_blob_sha(path) == document["blob_sha"], document["path"]

    graph = manifest["roadmap_graph"]
    assert graph == {
        "total_nodes": 28,
        "programme_nodes": 25,
        "feasibility_spikes": 3,
        "root": "SAE-00",
        "terminal": "SAE-180",
        "known_missing_dependency_references": 0,
        "known_dependency_cycles": 0,
    }

    review = manifest["review_disposition"]
    assert review["independent_genesis_lane_satisfied_by_planning_reviews"] is False
    assert review["planning_review_independence"] == "NOT_INDEPENDENT"

    fence = manifest["live_fence_at_freeze"]
    assert fence["pr"] == 167
    assert fence["retrofit_assurance_evolution"] is False
    assert fence["must_recover_live_state_before_execution"] is True

    prohibitions = set(manifest["prohibitions"])
    assert "do_not_merge_main_as_part_of_this_freeze_operation" in prohibitions
    assert "do_not_activate_partial_assurance_evolution" in prohibitions
    assert "do_not_retrofit_pr_167" in prohibitions


def test_assurance_evolution_v11_dependency_graph_is_closed_and_acyclic() -> None:
    dependencies = _dependency_registry()

    assert len(dependencies) == 28
    assert sum(name.startswith("SPIKE-") for name in dependencies) == 3
    assert sum(not name.startswith("SPIKE-") for name in dependencies) == 25

    referenced = {dependency for values in dependencies.values() for dependency in values}
    assert referenced <= set(dependencies)

    roots = sorted(name for name, values in dependencies.items() if not values)
    assert roots == ["SAE-00"]

    children: dict[str, list[str]] = defaultdict(list)
    indegree = {name: len(values) for name, values in dependencies.items()}
    for name, values in dependencies.items():
        for dependency in values:
            children[dependency].append(name)

    queue = deque(roots)
    ordered: list[str] = []
    depth: dict[str, int] = {"SAE-00": 0}
    while queue:
        node = queue.popleft()
        ordered.append(node)
        for child in children[node]:
            depth[child] = max(depth.get(child, 0), depth[node] + 1)
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)

    assert len(ordered) == len(dependencies)
    terminals = sorted(name for name in dependencies if not children[name])
    assert terminals == ["SAE-180"]
    assert depth["SAE-180"] == 14

    assert dependencies["SAE-30"] == ["SAE-00", "SPIKE-ID", "SPIKE-EXT"]
    assert dependencies["SAE-80"] == ["SAE-30", "SAE-40", "SAE-50", "SAE-60", "SAE-70"]


def test_sae60_initial_oracle_is_non_rust_and_non_circular() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8")

    assert "independently authored **non-Rust**, non-shared-implementation ground-truth/oracle path" in text
    assert "It **must not depend on SAE-R2**" in text

    dependencies = _dependency_registry()
    assert "SAE-R2" not in dependencies["SAE-60"]
    assert "SAE-60" in dependencies["SAE-R2"]
