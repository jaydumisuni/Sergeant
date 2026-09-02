"""SPIKE-SEM-only semantic feasibility probe.

This module is deliberately located under ``tests/spike_sem`` and is NOT
Sergeant production capability.  It exists to measure a bounded semantic
domain against the frozen Assurance Evolution SPIKE-SEM charter without
silently upgrading the current lightweight capability engine.

The probe is intentionally conservative:
- explicit, statically closed bindings may be EXACT;
- receiver-name candidate sets are CONSERVATIVE_SUPERSET;
- callback identity without framework invocation semantics is PARTIAL;
- dynamic dispatch/configuration and exhausted analysis budget are UNKNOWN.

Nothing here grants verdict or ACR authority.  A later programme may use the
findings to define a qualified domain, but must independently implement and
qualify any production analyzer.
"""

from __future__ import annotations

import ast
import json
import tomllib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

SemanticGrade = Literal["EXACT", "CONSERVATIVE_SUPERSET", "PARTIAL", "UNKNOWN"]

_REGISTER_METHODS = {"register", "add_route", "connect", "subscribe"}
_DYNAMIC_CONFIG_NAMES = ("handler", "target", "plugin", "entry", "callback")


@dataclass(frozen=True)
class Binding:
    target: str
    kind: str


@dataclass(frozen=True)
class SemanticRelation:
    source_path: str
    line: int
    kind: str
    target: str | None
    grade: SemanticGrade
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticProbeReport:
    relations: tuple[SemanticRelation, ...]
    states_visited: int
    files_parsed: int
    parse_errors: tuple[str, ...]
    budget_exceeded: bool

    def summary(self) -> dict[str, object]:
        counts = Counter(relation.grade for relation in self.relations)
        by_kind = Counter(relation.kind for relation in self.relations)
        total = len(self.relations)
        return {
            "total_relations": total,
            "grades": {
                grade: counts.get(grade, 0)
                for grade in ("EXACT", "CONSERVATIVE_SUPERSET", "PARTIAL", "UNKNOWN")
            },
            "rates": {
                grade: (counts.get(grade, 0) / total if total else 0.0)
                for grade in ("EXACT", "CONSERVATIVE_SUPERSET", "PARTIAL", "UNKNOWN")
            },
            "by_kind": dict(sorted(by_kind.items())),
            "states_visited": self.states_visited,
            "files_parsed": self.files_parsed,
            "parse_error_count": len(self.parse_errors),
            "budget_exceeded": self.budget_exceeded,
        }


def _module_name(root: Path, path: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_import_from(current_module: str, level: int, module: str | None) -> str:
    if level <= 0:
        return module or ""
    package = current_module.split(".")[:-1]
    keep = len(package) - (level - 1)
    base = package[: max(0, keep)]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _iter_python_files(root: Path, include_prefixes: tuple[str, ...] | None) -> list[Path]:
    files: list[Path] = []
    for pattern in ("*.py", "*.pyw"):
        for path in root.rglob(pattern):
            relative = path.relative_to(root).as_posix()
            if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
                continue
            if include_prefixes and not relative.startswith(include_prefixes):
                continue
            files.append(path)
    return sorted(set(files))


def _target_exists(target: str, module_symbols: dict[str, set[str]]) -> bool:
    module, dot, symbol = target.rpartition(".")
    return bool(dot and module in module_symbols and symbol in module_symbols[module])


def _resolve_symbol_expr(expr: ast.AST, bindings: dict[str, Binding]) -> str | None:
    if isinstance(expr, ast.Name):
        binding = bindings.get(expr.id)
        if binding and binding.kind != "module":
            return binding.target
        return None
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
        base = bindings.get(expr.value.id)
        if base and base.kind == "module":
            return f"{base.target}.{expr.attr}"
    return None


def _module_from_expr(expr: ast.AST, bindings: dict[str, Binding]) -> str | None:
    if isinstance(expr, ast.Name):
        binding = bindings.get(expr.id)
        if binding and binding.kind == "module":
            return binding.target
    return None


def _grade_bound_target(target: str, module_symbols: dict[str, set[str]]) -> SemanticGrade:
    return "EXACT" if _target_exists(target, module_symbols) else "PARTIAL"


def analyze_python_tree(
    root: str | Path,
    *,
    include_prefixes: tuple[str, ...] | None = None,
    max_states: int = 500_000,
    max_alias_hops: int = 2,
) -> SemanticProbeReport:
    """Analyze only a deliberately bounded static Python domain.

    ``max_alias_hops`` and ``max_states`` are explicit anti-explosion bounds.
    Reaching the state ceiling emits UNKNOWN rather than silently truncating a
    result and calling it complete.
    """

    root_path = Path(root).resolve()
    paths = _iter_python_files(root_path, include_prefixes)
    trees: dict[str, tuple[Path, ast.Module]] = {}
    module_symbols: dict[str, set[str]] = {}
    parse_errors: list[str] = []
    states_visited = 0
    budget_exceeded = False
    relations: list[SemanticRelation] = []

    for path in paths:
        relative = path.relative_to(root_path).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError as exc:
            parse_errors.append(f"{relative}:{exc.lineno or 0}:{exc.msg}")
            continue
        node_count = sum(1 for _ in ast.walk(tree))
        if states_visited + node_count > max_states:
            relations.append(
                SemanticRelation(
                    source_path=relative,
                    line=0,
                    kind="resource_budget",
                    target=None,
                    grade="UNKNOWN",
                    reason="semantic probe state budget exceeded; fail closed rather than truncate as complete",
                )
            )
            budget_exceeded = True
            break
        states_visited += node_count
        module = _module_name(root_path, path)
        trees[module] = (path, tree)
        module_symbols[module] = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }

    symbol_targets: dict[str, set[str]] = defaultdict(set)
    for module, symbols in module_symbols.items():
        for symbol in symbols:
            symbol_targets[symbol].add(f"{module}.{symbol}")

    for module, (path, tree) in trees.items():
        relative = path.relative_to(root_path).as_posix()
        bindings: dict[str, Binding] = {
            symbol: Binding(f"{module}.{symbol}", "local")
            for symbol in module_symbols.get(module, set())
        }
        dict_bindings: dict[str, dict[str, str]] = {}

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    target = alias.name if alias.asname else alias.name.split(".")[0]
                    bindings[local] = Binding(target, "module")
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_import_from(module, node.level, node.module)
                for alias in node.names:
                    if alias.name == "*":
                        relations.append(
                            SemanticRelation(
                                relative,
                                node.lineno,
                                "star_import",
                                base or None,
                                "UNKNOWN",
                                "star import prevents a closed local binding census",
                            )
                        )
                        continue
                    local = alias.asname or alias.name
                    target = f"{base}.{alias.name}" if base else alias.name
                    bindings[local] = Binding(target, "import_symbol")

        assignments = [
            node for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        for _hop in range(max_alias_hops):
            changed = False
            for node in assignments:
                value = node.value
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if value is None:
                    continue
                resolved = _resolve_symbol_expr(value, bindings)
                if resolved:
                    for target_node in targets:
                        if isinstance(target_node, ast.Name) and target_node.id not in bindings:
                            bindings[target_node.id] = Binding(resolved, "alias")
                            changed = True
                if isinstance(value, ast.Dict):
                    for target_node in targets:
                        if not isinstance(target_node, ast.Name):
                            continue
                        mapping: dict[str, str] = {}
                        for key, item in zip(value.keys, value.values):
                            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                                continue
                            resolved_item = _resolve_symbol_expr(item, bindings)
                            if resolved_item:
                                mapping[str(key.value)] = resolved_item
                        if mapping:
                            dict_bindings[target_node.id] = mapping
            if not changed:
                break

        for node in assignments:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [target.id for target in targets if isinstance(target, ast.Name)]
            if not any(
                any(token in name.lower() for token in _DYNAMIC_CONFIG_NAMES)
                for name in names
            ):
                continue
            value = node.value
            if isinstance(value, (ast.JoinedStr, ast.BinOp)):
                relations.append(
                    SemanticRelation(
                        relative,
                        node.lineno,
                        "generated_config_dynamic",
                        None,
                        "UNKNOWN",
                        "generated configuration target is assembled dynamically",
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    expression = decorator.func if isinstance(decorator, ast.Call) else decorator
                    target = _resolve_symbol_expr(expression, bindings)
                    if target:
                        relations.append(
                            SemanticRelation(
                                relative,
                                getattr(decorator, "lineno", node.lineno),
                                "decorator_binding",
                                target,
                                _grade_bound_target(target, module_symbols),
                                "decorator callable identity is statically bound",
                            )
                        )

            if not isinstance(node, ast.Call):
                continue

            if (
                isinstance(node.func, ast.Call)
                and isinstance(node.func.func, ast.Name)
                and node.func.func.id == "getattr"
                and len(node.func.args) >= 2
            ):
                inner = node.func
                imported_module = _module_from_expr(inner.args[0], bindings)
                attr = inner.args[1]
                if imported_module and isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                    target = f"{imported_module}.{attr.value}"
                    relations.append(
                        SemanticRelation(
                            relative,
                            node.lineno,
                            "getattr_literal_call",
                            target,
                            _grade_bound_target(target, module_symbols),
                            "literal getattr on an explicitly imported module is bounded",
                        )
                    )
                else:
                    relations.append(
                        SemanticRelation(
                            relative,
                            node.lineno,
                            "getattr_dynamic_call",
                            None,
                            "UNKNOWN",
                            "dynamic getattr receiver or attribute cannot be closed statically",
                        )
                    )
                continue

            if isinstance(node.func, ast.Subscript) and isinstance(node.func.value, ast.Name):
                table = dict_bindings.get(node.func.value.id)
                key = node.func.slice
                if table and isinstance(key, ast.Constant) and isinstance(key.value, str):
                    target = table.get(str(key.value))
                    if target:
                        relations.append(
                            SemanticRelation(
                                relative,
                                node.lineno,
                                "bounded_indirect_dispatch",
                                target,
                                _grade_bound_target(target, module_symbols),
                                "constant-key dispatch table resolves to one statically bound callable",
                            )
                        )
                        continue
                if table:
                    relations.append(
                        SemanticRelation(
                            relative,
                            node.lineno,
                            "bounded_indirect_dispatch",
                            None,
                            "UNKNOWN",
                            "dispatch table key is dynamic or outside the statically closed table",
                        )
                    )
                    continue

            if isinstance(node.func, ast.Attribute) and node.func.attr in _REGISTER_METHODS:
                callbacks = [_resolve_symbol_expr(arg, bindings) for arg in node.args]
                callbacks.extend(
                    _resolve_symbol_expr(keyword.value, bindings) for keyword in node.keywords
                )
                callback_targets = [target for target in callbacks if target]
                for target in callback_targets:
                    relations.append(
                        SemanticRelation(
                            relative,
                            node.lineno,
                            "framework_registration",
                            target,
                            "PARTIAL",
                            "callback identity is bound but framework invocation semantics are not proven",
                        )
                    )
                if callback_targets:
                    continue

            target = _resolve_symbol_expr(node.func, bindings)
            if target:
                relations.append(
                    SemanticRelation(
                        relative,
                        node.lineno,
                        "direct_call" if isinstance(node.func, (ast.Name, ast.Attribute)) else "call",
                        target,
                        _grade_bound_target(target, module_symbols),
                        "call target is statically bound by local/import/module identity",
                    )
                )
                continue

            if isinstance(node.func, ast.Attribute):
                candidates = sorted(symbol_targets.get(node.func.attr, set()))
                if candidates:
                    relations.append(
                        SemanticRelation(
                            relative,
                            node.lineno,
                            "attribute_name_candidate",
                            "|".join(candidates),
                            "CONSERVATIVE_SUPERSET",
                            "attribute name matches exported symbols but receiver identity is not bound",
                        )
                    )

    pyproject = root_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            entry_points = data.get("project", {}).get("entry-points", {})
            if isinstance(entry_points, dict):
                for group, entries in entry_points.items():
                    if not isinstance(entries, dict):
                        continue
                    for name, raw_target in entries.items():
                        if not isinstance(raw_target, str) or ":" not in raw_target:
                            continue
                        target = raw_target.replace(":", ".", 1)
                        relations.append(
                            SemanticRelation(
                                "pyproject.toml",
                                0,
                                "plugin_entry_point",
                                target,
                                _grade_bound_target(target, module_symbols),
                                f"entry point {group}.{name} names a concrete module:symbol target",
                            )
                        )
        except (OSError, tomllib.TOMLDecodeError) as exc:
            parse_errors.append(f"pyproject.toml:0:{exc}")

    return SemanticProbeReport(
        relations=tuple(relations),
        states_visited=states_visited,
        files_parsed=len(trees),
        parse_errors=tuple(parse_errors),
        budget_exceeded=budget_exceeded,
    )


def relation_matrix(report: SemanticProbeReport) -> dict[str, list[dict[str, object]]]:
    matrix: dict[str, list[dict[str, object]]] = defaultdict(list)
    for relation in report.relations:
        matrix[relation.kind].append(relation.to_dict())
    return dict(sorted(matrix.items()))


def summary_json(report: SemanticProbeReport) -> str:
    return json.dumps(report.summary(), sort_keys=True, separators=(",", ":"))
