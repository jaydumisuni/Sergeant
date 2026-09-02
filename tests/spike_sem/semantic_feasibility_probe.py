"""SPIKE-SEM-only bounded semantic feasibility probe; never production authority."""
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
_FUNCTION_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_LEXICAL_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)


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
        grades = ("EXACT", "CONSERVATIVE_SUPERSET", "PARTIAL", "UNKNOWN")
        counts = Counter(r.grade for r in self.relations)
        kinds = Counter(r.kind for r in self.relations)
        total = len(self.relations)
        return {
            "total_relations": total,
            "grades": {g: counts.get(g, 0) for g in grades},
            "rates": {g: counts.get(g, 0) / total if total else 0.0 for g in grades},
            "by_kind": dict(sorted(kinds.items())),
            "states_visited": self.states_visited,
            "files_parsed": self.files_parsed,
            "parse_error_count": len(self.parse_errors),
            "budget_exceeded": self.budget_exceeded,
        }


@dataclass
class _Budget:
    limit: int
    used: int = 0
    phase: str | None = None

    def take(self, n: int = 1, phase: str = "analysis") -> None:
        if self.phase is not None:
            raise _BudgetStop
        if self.used + max(0, n) > self.limit:
            self.used = self.limit
            self.phase = phase
            raise _BudgetStop
        self.used += max(0, n)


class _BudgetStop(RuntimeError):
    pass


@dataclass(frozen=True)
class _Info:
    path: Path
    rel: str
    tree: ast.Module
    nodes: tuple[ast.AST, ...]
    scope_of: dict[int, int | None]
    bound_in_scope: dict[int, frozenset[str]]
    module_counts: Counter[str]


def _module_name(root: Path, path: Path) -> str:
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_import_from(current: str, level: int, module: str | None) -> str:
    if level <= 0:
        return module or ""
    package = current.split(".")[:-1]
    base = package[: max(0, len(package) - (level - 1))]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _python_files(root: Path, prefixes: tuple[str, ...] | None) -> list[Path]:
    found: set[Path] = set()
    for pattern in ("*.py", "*.pyw"):
        for path in root.rglob(pattern):
            rel = path.relative_to(root).as_posix()
            if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
                continue
            if prefixes and not rel.startswith(prefixes):
                continue
            found.add(path)
    return sorted(found)


def _arg_names(args: ast.arguments) -> set[str]:
    out = {a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg:
        out.add(args.vararg.arg)
    if args.kwarg:
        out.add(args.kwarg.arg)
    return out


def _binding_names(node: ast.AST) -> set[str]:
    out: set[str] = set()
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
        out.add(node.id)
    elif isinstance(node, ast.ExceptHandler) and node.name:
        out.add(node.name)
    elif isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name:
        out.add(node.name)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        out.add(node.name)
    elif isinstance(node, ast.Import):
        out.update(a.asname or a.name.split(".")[0] for a in node.names)
    elif isinstance(node, ast.ImportFrom):
        out.update(a.asname or a.name for a in node.names if a.name != "*")
    return out


def _scope_census(tree: ast.Module, budget: _Budget):
    nodes: list[ast.AST] = []
    scope_of: dict[int, int | None] = {}
    bound: dict[int, set[str]] = defaultdict(set)
    stack: list[tuple[ast.AST, int | None]] = [(tree, None)]
    while stack:
        node, scope = stack.pop()
        budget.take(1, "scope traversal")
        nodes.append(node)
        scope_of[id(node)] = scope
        child_scope = scope
        if isinstance(node, _LEXICAL_SCOPES):
            child_scope = id(node)
            if isinstance(node, _FUNCTION_SCOPES):
                bound[child_scope].update(_arg_names(node.args))
        if scope is not None:
            bound[scope].update(_binding_names(node))
        children = list(ast.iter_child_nodes(node))
        budget.take(len(children), "scope child expansion")
        for child in reversed(children):
            stack.append((child, child_scope if isinstance(node, _LEXICAL_SCOPES) else scope))
    return tuple(nodes), scope_of, {k: frozenset(v) for k, v in bound.items()}


def _module_counts(nodes: tuple[ast.AST, ...], scope_of: dict[int, int | None], budget: _Budget):
    counts: Counter[str] = Counter()
    for node in nodes:
        budget.take(1, "module binding census")
        if scope_of.get(id(node)) is None:
            for name in _binding_names(node):
                counts[name] += 1
    return counts


def _exists(target: str, symbols: dict[str, set[str]]) -> bool:
    module, dot, name = target.rpartition(".")
    return bool(dot and name in symbols.get(module, set()))


def _grade(target: str, symbols: dict[str, set[str]]) -> SemanticGrade:
    return "EXACT" if _exists(target, symbols) else "PARTIAL"


def _resolve(expr: ast.AST, bindings: dict[str, Binding], unsafe: set[str] | frozenset[str]):
    if isinstance(expr, ast.Name):
        b = None if expr.id in unsafe else bindings.get(expr.id)
        return b.target if b and b.kind != "module" else None
    if isinstance(expr, ast.Attribute) and isinstance(expr.value, ast.Name):
        b = None if expr.value.id in unsafe else bindings.get(expr.value.id)
        return f"{b.target}.{expr.attr}" if b and b.kind == "module" else None
    return None


def _module_expr(expr: ast.AST, bindings: dict[str, Binding], unsafe: set[str] | frozenset[str]):
    if isinstance(expr, ast.Name) and expr.id not in unsafe:
        b = bindings.get(expr.id)
        if b and b.kind == "module":
            return b.target
    return None


def _spelling(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Subscript):
        return "subscript-call"
    if isinstance(call.func, ast.Call):
        return "returned-callable"
    return type(call.func).__name__


def analyze_python_tree(
    root: str | Path,
    *,
    include_prefixes: tuple[str, ...] | None = None,
    max_states: int = 2_000_000,
    max_alias_hops: int = 2,
) -> SemanticProbeReport:
    root = Path(root).resolve()
    budget = _Budget(max_states)
    infos: dict[str, _Info] = {}
    symbols: dict[str, set[str]] = {}
    errors: list[str] = []
    relations: list[SemanticRelation] = []
    stopped = "."

    try:
        for path in _python_files(root, include_prefixes):
            rel = path.relative_to(root).as_posix()
            stopped = rel
            text = path.read_text(encoding="utf-8", errors="ignore")
            budget.take(max(1, len(text) // 256), "source read sizing")
            try:
                tree = ast.parse(text)
            except SyntaxError as exc:
                errors.append(f"{rel}:{exc.lineno or 0}:{exc.msg}")
                relations.append(SemanticRelation(rel, exc.lineno or 0, "parse_failure", None, "UNKNOWN", "parse failure prevents semantic closure"))
                continue
            nodes, scope_of, bound = _scope_census(tree, budget)
            counts = _module_counts(nodes, scope_of, budget)
            module = _module_name(root, path)
            module_symbols = {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            budget.take(len(tree.body) + len(module_symbols), "module symbol census")
            symbols[module] = module_symbols
            infos[module] = _Info(path, rel, tree, nodes, scope_of, bound, counts)

        targets_by_name: dict[str, set[str]] = defaultdict(set)
        for module, names in symbols.items():
            budget.take(len(names), "global symbol index")
            for name in names:
                targets_by_name[name].add(f"{module}.{name}")

        for module, info in infos.items():
            stopped = info.rel
            ambiguous = {name for name, count in info.module_counts.items() if count > 1}
            bindings = {name: Binding(f"{module}.{name}", "local") for name in symbols[module] if name not in ambiguous}
            tables: dict[str, dict[str, str]] = {}

            for node in info.tree.body:
                budget.take(1, "module import binding")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        budget.take(1, "import alias binding")
                        local = alias.asname or alias.name.split(".")[0]
                        if local not in ambiguous:
                            bindings[local] = Binding(alias.name if alias.asname else alias.name.split(".")[0], "module")
                elif isinstance(node, ast.ImportFrom):
                    base = _resolve_import_from(module, node.level, node.module)
                    for alias in node.names:
                        budget.take(1, "from-import alias binding")
                        if alias.name == "*":
                            relations.append(SemanticRelation(info.rel, node.lineno, "star_import", base or None, "UNKNOWN", "star import prevents a closed binding census"))
                            continue
                        local = alias.asname or alias.name
                        if local not in ambiguous:
                            bindings[local] = Binding(f"{base}.{alias.name}" if base else alias.name, "import_symbol")

            assignments = [n for n in info.tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))]
            for _ in range(max_alias_hops):
                changed = False
                for node in assignments:
                    budget.take(1, "alias pass")
                    value = node.value
                    target_nodes = node.targets if isinstance(node, ast.Assign) else [node.target]
                    if value is None:
                        continue
                    resolved = _resolve(value, bindings, ambiguous)
                    for target_node in target_nodes:
                        budget.take(1, "alias target expansion")
                        if resolved and isinstance(target_node, ast.Name) and target_node.id not in bindings and target_node.id not in ambiguous:
                            bindings[target_node.id] = Binding(resolved, "alias")
                            changed = True
                        if isinstance(value, ast.Dict) and isinstance(target_node, ast.Name) and target_node.id not in ambiguous:
                            mapping: dict[str, str] = {}
                            for key, item in zip(value.keys, value.values):
                                budget.take(1, "dispatch table candidate expansion")
                                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                                    item_target = _resolve(item, bindings, ambiguous)
                                    if item_target:
                                        mapping[str(key.value)] = item_target
                            if mapping:
                                tables[target_node.id] = mapping
                if not changed:
                    break

            for node in assignments:
                budget.take(1, "dynamic configuration scan")
                target_nodes = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [n.id for n in target_nodes if isinstance(n, ast.Name)]
                if any(any(token in name.lower() for token in _DYNAMIC_CONFIG_NAMES) for name in names) and isinstance(node.value, (ast.JoinedStr, ast.BinOp)):
                    relations.append(SemanticRelation(info.rel, node.lineno, "generated_config_dynamic", None, "UNKNOWN", "generated target is assembled dynamically"))

            for node in info.nodes:
                budget.take(1, "semantic node analysis")
                scope = info.scope_of.get(id(node))
                unsafe = set(info.bound_in_scope.get(scope, frozenset())) if scope is not None else set()
                unsafe.update(ambiguous)

                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for decorator in node.decorator_list:
                        budget.take(1, "decorator expansion")
                        expr = decorator.func if isinstance(decorator, ast.Call) else decorator
                        target = _resolve(expr, bindings, unsafe)
                        relations.append(SemanticRelation(info.rel, getattr(decorator, "lineno", node.lineno), "decorator_binding", target, _grade(target, symbols) if target else "UNKNOWN", "decorator identity is statically bound" if target else "decorator is unresolved or shadowable"))

                if not isinstance(node, ast.Call):
                    continue

                if isinstance(node.func, ast.Call) and isinstance(node.func.func, ast.Name) and node.func.func.id == "getattr" and "getattr" not in unsafe and "getattr" not in bindings and len(node.func.args) >= 2:
                    inner = node.func
                    module_target = _module_expr(inner.args[0], bindings, unsafe)
                    attr = inner.args[1]
                    if module_target and isinstance(attr, ast.Constant) and isinstance(attr.value, str):
                        target = f"{module_target}.{attr.value}"
                        relations.append(SemanticRelation(info.rel, node.lineno, "getattr_literal_call", target, _grade(target, symbols), "literal getattr on a non-shadowable imported module is bounded"))
                    else:
                        relations.append(SemanticRelation(info.rel, node.lineno, "getattr_dynamic_call", None, "UNKNOWN", "dynamic or shadowable getattr cannot be closed statically"))
                    continue

                if isinstance(node.func, ast.Subscript) and isinstance(node.func.value, ast.Name) and node.func.value.id in tables:
                    name, key = node.func.value.id, node.func.slice
                    table = tables[name]
                    if name not in unsafe and isinstance(key, ast.Constant) and isinstance(key.value, str) and str(key.value) in table:
                        target = table[str(key.value)]
                        relations.append(SemanticRelation(info.rel, node.lineno, "bounded_indirect_dispatch", target, _grade(target, symbols), "constant-key dispatch resolves to one bound callable"))
                    else:
                        relations.append(SemanticRelation(info.rel, node.lineno, "bounded_indirect_dispatch", None, "UNKNOWN", "dispatch key/table is dynamic, missing, or shadowable"))
                    continue

                if isinstance(node.func, ast.Attribute) and node.func.attr in _REGISTER_METHODS:
                    callbacks = [_resolve(arg, bindings, unsafe) for arg in node.args]
                    callbacks += [_resolve(k.value, bindings, unsafe) for k in node.keywords]
                    budget.take(len(node.args) + len(node.keywords), "framework callback expansion")
                    known = sorted({x for x in callbacks if x})
                    relations.append(SemanticRelation(info.rel, node.lineno, "framework_registration", "|".join(known) if known else None, "PARTIAL" if known else "UNKNOWN", "callback identity is bound but framework invocation semantics are not proven" if known else "registration callback identity is unresolved"))
                    continue

                target = _resolve(node.func, bindings, unsafe)
                if target:
                    relations.append(SemanticRelation(info.rel, node.lineno, "direct_call", target, _grade(target, symbols), "call target is statically bound by non-shadowable module/import identity"))
                    continue

                if isinstance(node.func, ast.Name) and node.func.id in unsafe:
                    relations.append(SemanticRelation(info.rel, node.lineno, "lexical_shadowing", None, "UNKNOWN", "call spelling is locally bound/shadowable or multiply rebound"))
                    continue

                if isinstance(node.func, ast.Attribute):
                    candidates = sorted(targets_by_name.get(node.func.attr, set()))
                    budget.take(max(1, len(candidates)), "attribute candidate expansion")
                    if candidates:
                        relations.append(SemanticRelation(info.rel, node.lineno, "attribute_name_candidate", "|".join(candidates), "CONSERVATIVE_SUPERSET", "attribute name matches exported symbols but receiver identity is not bound"))
                        continue

                relations.append(SemanticRelation(info.rel, node.lineno, "unresolved_call", None, "UNKNOWN", f"call target {_spelling(node)!r} is outside the bounded static domain"))

        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            stopped = "pyproject.toml"
            budget.take(1, "entry-point document read")
            try:
                groups = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("entry-points", {})
                if isinstance(groups, dict):
                    for group, entries in groups.items():
                        budget.take(1, "entry-point group expansion")
                        if not isinstance(entries, dict):
                            continue
                        for name, raw in entries.items():
                            budget.take(1, "entry-point candidate expansion")
                            if not isinstance(raw, str) or ":" not in raw:
                                relations.append(SemanticRelation("pyproject.toml", 0, "plugin_entry_point", None, "UNKNOWN", f"entry point {group}.{name} has no concrete module:symbol target"))
                            else:
                                target = raw.replace(":", ".", 1)
                                relations.append(SemanticRelation("pyproject.toml", 0, "plugin_entry_point", target, _grade(target, symbols), f"entry point {group}.{name} names a concrete module:symbol target"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                errors.append(f"pyproject.toml:0:{exc}")
                relations.append(SemanticRelation("pyproject.toml", 0, "plugin_entry_point", None, "UNKNOWN", "entry-point configuration could not be parsed"))

    except _BudgetStop:
        relations.append(SemanticRelation(stopped, 0, "resource_budget", None, "UNKNOWN", f"semantic probe operation budget exceeded during {budget.phase or 'unknown phase'}; fail closed"))

    return SemanticProbeReport(tuple(relations), budget.used, len(infos), tuple(errors), budget.phase is not None)


def relation_matrix(report: SemanticProbeReport) -> dict[str, list[dict[str, object]]]:
    matrix: dict[str, list[dict[str, object]]] = defaultdict(list)
    for relation in report.relations:
        matrix[relation.kind].append(relation.to_dict())
    return dict(sorted(matrix.items()))


def summary_json(report: SemanticProbeReport) -> str:
    return json.dumps(report.summary(), sort_keys=True, separators=(",", ":"))
