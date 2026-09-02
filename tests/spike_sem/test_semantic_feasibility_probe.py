from __future__ import annotations

import json
from pathlib import Path

from main_review.capability_engine import run_capability_engine
from tests.spike_sem.semantic_feasibility_probe import analyze_python_tree, relation_matrix


ROOT = Path(__file__).resolve().parents[2]

# Deliberately RED after review invalidated the first measurement. The next
# exact-head repository run must expose the corrected metrics after unresolved
# calls, lexical shadowing, and operation-budget charging are all represented.
EXPECTED_REAL_SERGEANT_METRICS: dict[str, object] = {
    "DISCOVERY_PENDING_AFTER_REVIEW_HARDENING": True,
}


def _write_required_construct_matrix(root: Path) -> None:
    package = root / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "target.py").write_text(
        "def direct():\n"
        "    return 1\n\n"
        "def indirect():\n"
        "    return 2\n\n"
        "def registered_handler():\n"
        "    return 3\n",
        encoding="utf-8",
    )
    (package / "decorators.py").write_text(
        "def audit(fn):\n"
        "    return fn\n",
        encoding="utf-8",
    )
    (package / "caller.py").write_text(
        "from pkg.target import direct, indirect, registered_handler\n"
        "from pkg.decorators import audit\n"
        "import pkg.target as target_mod\n\n"
        "dispatch = {'go': indirect}\n\n"
        "def call_direct():\n"
        "    return direct()\n\n"
        "def call_indirect():\n"
        "    return dispatch['go']()\n\n"
        "@audit\n"
        "def decorated():\n"
        "    return 1\n\n"
        "def call_getattr_literal():\n"
        "    return getattr(target_mod, 'direct')()\n\n"
        "def call_getattr_dynamic(name):\n"
        "    return getattr(target_mod, name)()\n\n"
        "class Registry:\n"
        "    def register(self, name, fn):\n"
        "        return fn\n\n"
        "registry = Registry()\n"
        "registry.register('handler', registered_handler)\n",
        encoding="utf-8",
    )
    (package / "generated.py").write_text(
        "import os\n"
        "name = os.getenv('HANDLER')\n"
        "handler_target = f'pkg.target:{name}'\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\n"
        "name = 'semantic-feasibility-fixture'\n"
        "version = '0.0.0'\n\n"
        "[project.entry-points.\"demo.plugins\"]\n"
        "worker = 'pkg.target:direct'\n",
        encoding="utf-8",
    )


def _relation_for(matrix: dict[str, list[dict[str, object]]], kind: str, target: str | None):
    matches = [entry for entry in matrix.get(kind, []) if entry.get("target") == target]
    assert len(matches) == 1, (kind, target, matches)
    return matches[0]


def test_required_construct_matrix_records_bounded_exact_partial_and_unknown(tmp_path: Path) -> None:
    _write_required_construct_matrix(tmp_path)

    report = analyze_python_tree(tmp_path)
    matrix = relation_matrix(report)
    summary = report.summary()

    assert _relation_for(matrix, "direct_call", "pkg.target.direct")["grade"] == "EXACT"
    assert _relation_for(matrix, "bounded_indirect_dispatch", "pkg.target.indirect")["grade"] == "EXACT"
    assert _relation_for(matrix, "decorator_binding", "pkg.decorators.audit")["grade"] == "EXACT"
    assert _relation_for(matrix, "getattr_literal_call", "pkg.target.direct")["grade"] == "EXACT"
    assert _relation_for(matrix, "framework_registration", "pkg.target.registered_handler")["grade"] == "PARTIAL"
    assert _relation_for(matrix, "plugin_entry_point", "pkg.target.direct")["grade"] == "EXACT"

    assert any(entry["grade"] == "UNKNOWN" for entry in matrix.get("getattr_dynamic_call", []))
    assert any(entry["grade"] == "UNKNOWN" for entry in matrix.get("generated_config_dynamic", []))

    # Every ast.Call is now represented. The two builtin getattr calls are
    # intentionally UNKNOWN in addition to the dynamic semantic relations.
    assert summary["grades"] == {
        "EXACT": 6,
        "CONSERVATIVE_SUPERSET": 0,
        "PARTIAL": 2,
        "UNKNOWN": 4,
    }
    assert summary["total_relations"] == 12
    assert summary["budget_exceeded"] is False
    assert summary["parse_error_count"] == 0


def test_unbound_attribute_receiver_is_conservative_superset(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def handle():\n    return 'a'\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def handle():\n    return 'b'\n", encoding="utf-8")
    (tmp_path / "caller.py").write_text(
        "class Obj:\n"
        "    pass\n\n"
        "obj = Obj()\n"
        "obj.handle()\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path)
    candidates = [
        relation
        for relation in report.relations
        if relation.kind == "attribute_name_candidate" and relation.grade == "CONSERVATIVE_SUPERSET"
    ]

    assert len(candidates) == 1
    assert set((candidates[0].target or "").split("|")) == {"a.handle", "b.handle"}


def test_dynamic_dispatch_key_fails_closed_unknown(tmp_path: Path) -> None:
    (tmp_path / "target.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (tmp_path / "caller.py").write_text(
        "from target import run\n"
        "dispatch = {'run': run}\n"
        "def invoke(name):\n"
        "    return dispatch[name]()\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path)
    dynamic = [relation for relation in report.relations if relation.kind == "bounded_indirect_dispatch"]

    assert len(dynamic) == 1
    assert dynamic[0].grade == "UNKNOWN"
    assert dynamic[0].target is None


def test_import_shadowed_by_parameter_is_unknown_not_false_exact(tmp_path: Path) -> None:
    (tmp_path / "target.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (tmp_path / "caller.py").write_text(
        "from target import run\n"
        "def invoke(run):\n"
        "    return run()\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path)

    assert not any(
        relation.target == "target.run" and relation.grade == "EXACT"
        for relation in report.relations
    )
    assert any(
        relation.kind == "lexical_shadowing" and relation.grade == "UNKNOWN"
        for relation in report.relations
    )


def test_every_unresolved_call_is_explicit_unknown(tmp_path: Path) -> None:
    (tmp_path / "caller.py").write_text(
        "def invoke(callback, path):\n"
        "    callback()\n"
        "    path.read_text()\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path)
    call_like = [
        relation
        for relation in report.relations
        if relation.kind in {"lexical_shadowing", "unresolved_call", "attribute_name_candidate"}
    ]

    assert len(call_like) == 2
    assert all(relation.grade == "UNKNOWN" for relation in call_like)


def test_state_budget_exhaustion_fails_closed_unknown(tmp_path: Path) -> None:
    (tmp_path / "large.py").write_text(
        "\n".join(f"def f_{index}(): return {index}" for index in range(200)) + "\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path, max_states=20)

    assert report.budget_exceeded is True
    assert any(
        relation.kind == "resource_budget" and relation.grade == "UNKNOWN"
        for relation in report.relations
    )


def test_candidate_expansion_consumes_operation_budget(tmp_path: Path) -> None:
    for index in range(80):
        (tmp_path / f"m{index}.py").write_text(
            "def handle():\n    return 1\n",
            encoding="utf-8",
        )
    (tmp_path / "caller.py").write_text(
        "class Obj:\n    pass\n"
        "obj = Obj()\n"
        + "\n".join("obj.handle()" for _ in range(80))
        + "\n",
        encoding="utf-8",
    )

    report = analyze_python_tree(tmp_path, max_states=5_000)
    budget = [relation for relation in report.relations if relation.kind == "resource_budget"]

    assert report.budget_exceeded is True
    assert len(budget) == 1
    assert "attribute candidate expansion" in budget[0].reason
    assert budget[0].grade == "UNKNOWN"


def test_current_capability_engine_name_only_call_graph_has_measurable_false_positive_pressure(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "README.md").write_text("# semantic fixture\n", encoding="utf-8")
    (tmp_path / "src" / "target.py").write_text(
        "def handle():\n    return 'target'\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "caller.py").write_text(
        "from src.target import handle\n"
        "def invoke():\n"
        "    return handle()\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "unrelated.py").write_text(
        "def handle():\n"
        "    return 'local'\n\n"
        "def invoke():\n"
        "    return handle()\n",
        encoding="utf-8",
    )

    current = run_capability_engine(tmp_path, changed_files=["src/target.py"])
    finding = next(
        finding
        for finding in current["findings"]
        if finding["capability"] == "call_graph" and finding.get("path") == "src/target.py"
    )

    assert "src/caller.py" in finding["related_paths"]
    assert "src/unrelated.py" in finding["related_paths"]

    bounded = analyze_python_tree(tmp_path, include_prefixes=("src/",))
    exact_target_calls = [
        relation.source_path
        for relation in bounded.relations
        if relation.target == "src.target.handle" and relation.grade == "EXACT"
    ]
    assert "src/caller.py" in exact_target_calls
    assert "src/unrelated.py" not in exact_target_calls


def test_real_sergeant_main_review_semantic_metrics_are_frozen_from_observation() -> None:
    report = analyze_python_tree(
        ROOT,
        include_prefixes=("main_review/",),
        max_states=2_000_000,
    )
    summary = report.summary()

    assert summary["files_parsed"] > 20
    assert summary["total_relations"] > 0
    assert summary["grades"]["EXACT"] > 0
    assert summary["grades"]["UNKNOWN"] > 0
    assert summary["budget_exceeded"] is False
    assert summary["parse_error_count"] == 0

    assert summary == EXPECTED_REAL_SERGEANT_METRICS, (
        "SPIKE_SEM_REAL_METRICS=" + json.dumps(summary, sort_keys=True)
    )
