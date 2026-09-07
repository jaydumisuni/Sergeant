"""SAE-60 bounded semantic capability candidate.

This module implements one deliberately narrow semantic family: Python calls
through immutable module-level literal-key dispatch tables whose values are
unique top-level functions. It is fail-closed by construction. Dynamic keys,
mutation/escape, lexical shadowing, parser/framework drift, parse failure and
resource exhaustion conserve UNKNOWN.

Capability passports produced here are CANDIDATE records only. This module has
no authority to self-qualify a capability; positive qualification is a later
SAE-30-backed lifecycle operation.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from typing import Iterable

from .assurance_contract_registry import BoundedDomain, ClosureGrade
from .review_world import ReviewWorldError, require_full_sha256, sha256_id


class CapabilityQualificationError(ReviewWorldError):
    """Raised for malformed capability/passport authority inputs."""


CANDIDATE_STATE = "CANDIDATE"
_SUPPORTED_DOMAIN = "python.bounded-literal-dispatch.v1"
_SUPPORTED_PARSER = "cpython-ast-3.11-v1"
_SUPPORTED_FRAMEWORK = "python-language-3.11"
_REQUIRED_DIMENSIONS = {
    "max_source_bytes",
    "max_ast_nodes",
    "max_dispatch_tables",
    "max_table_entries",
}
_MUTATING_METHODS = {
    "clear", "pop", "popitem", "setdefault", "update", "__setitem__", "__delitem__"
}


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise CapabilityQualificationError(f"{field} must be canonical and non-empty")
    return value


def _sha(value: object, field: str) -> str:
    try:
        return require_full_sha256(value, field)  # type: ignore[arg-type]
    except (TypeError, ValueError, ReviewWorldError) as exc:
        raise CapabilityQualificationError(str(exc)) from exc


def _source_digest(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _passport_body(
    *,
    capability_name: str,
    domain: BoundedDomain,
    artifact_generation: str,
    parser_generation: str,
    framework_generation: str,
    qualification_protocol_generation: str,
    proof_ceiling: str,
    closure_ceiling: ClosureGrade,
    implementation_lineage_id: str,
    parser_lineage_id: str,
    framework_lineage_id: str,
    common_mode_lineage_id: str,
    control_lineage_id: str,
) -> dict[str, object]:
    return {
        "schema_version": "sergeant.capability-passport.v1",
        "lifecycle_state": CANDIDATE_STATE,
        "capability_name": capability_name,
        "domain_id": domain.domain_id,
        "domain_generation": domain.generation,
        "domain_hash": domain.domain_hash,
        "artifact_generation": artifact_generation,
        "parser_generation": parser_generation,
        "framework_generation": framework_generation,
        "qualification_protocol_generation": qualification_protocol_generation,
        "proof_ceiling": proof_ceiling,
        "closure_ceiling": closure_ceiling.value,
        "implementation_lineage_id": implementation_lineage_id,
        "parser_lineage_id": parser_lineage_id,
        "framework_lineage_id": framework_lineage_id,
        "common_mode_lineage_id": common_mode_lineage_id,
        "control_lineage_id": control_lineage_id,
    }


@dataclass(frozen=True)
class CapabilityPassport:
    schema_version: str
    lifecycle_state: str
    capability_name: str
    domain: BoundedDomain
    artifact_generation: str
    parser_generation: str
    framework_generation: str
    qualification_protocol_generation: str
    proof_ceiling: str
    closure_ceiling: ClosureGrade
    implementation_lineage_id: str
    parser_lineage_id: str
    framework_lineage_id: str
    common_mode_lineage_id: str
    control_lineage_id: str
    passport_id: str

    @classmethod
    def create(
        cls,
        *,
        capability_name: str,
        domain: BoundedDomain,
        artifact_generation: str,
        parser_generation: str,
        framework_generation: str,
        qualification_protocol_generation: str,
        proof_ceiling: str,
        closure_ceiling: ClosureGrade,
        implementation_lineage_id: str,
        parser_lineage_id: str,
        framework_lineage_id: str,
        common_mode_lineage_id: str,
        control_lineage_id: str,
    ) -> "CapabilityPassport":
        if not isinstance(domain, BoundedDomain):
            raise CapabilityQualificationError("capability passport requires canonical BoundedDomain")
        dimensions = dict(domain.dimensions)
        if set(dimensions) != _REQUIRED_DIMENSIONS:
            raise CapabilityQualificationError(
                f"bounded literal-dispatch domain must declare exactly {sorted(_REQUIRED_DIMENSIONS)!r}"
            )
        if not all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in dimensions.values()):
            raise CapabilityQualificationError("capability domain dimensions must be positive integers")
        if not isinstance(closure_ceiling, ClosureGrade):
            raise CapabilityQualificationError("closure_ceiling must be ClosureGrade")
        values = {
            "capability_name": _string(capability_name, "capability_name"),
            "artifact_generation": _string(artifact_generation, "artifact_generation"),
            "parser_generation": _string(parser_generation, "parser_generation"),
            "framework_generation": _string(framework_generation, "framework_generation"),
            "qualification_protocol_generation": _string(
                qualification_protocol_generation, "qualification_protocol_generation"
            ),
            "proof_ceiling": _string(proof_ceiling, "proof_ceiling"),
            "implementation_lineage_id": _sha(implementation_lineage_id, "implementation_lineage_id"),
            "parser_lineage_id": _sha(parser_lineage_id, "parser_lineage_id"),
            "framework_lineage_id": _sha(framework_lineage_id, "framework_lineage_id"),
            "common_mode_lineage_id": _sha(common_mode_lineage_id, "common_mode_lineage_id"),
            "control_lineage_id": _sha(control_lineage_id, "control_lineage_id"),
        }
        body = _passport_body(domain=domain, closure_ceiling=closure_ceiling, **values)
        return cls(
            "sergeant.capability-passport.v1",
            CANDIDATE_STATE,
            values["capability_name"],
            domain,
            values["artifact_generation"],
            values["parser_generation"],
            values["framework_generation"],
            values["qualification_protocol_generation"],
            values["proof_ceiling"],
            closure_ceiling,
            values["implementation_lineage_id"],
            values["parser_lineage_id"],
            values["framework_lineage_id"],
            values["common_mode_lineage_id"],
            values["control_lineage_id"],
            sha256_id(body),
        )

    def integrity_error(self) -> str | None:
        try:
            rebuilt_domain = BoundedDomain.create(
                domain_id=self.domain.domain_id,
                generation=self.domain.generation,
                dimensions=dict(self.domain.dimensions),
            )
            if rebuilt_domain != self.domain:
                return "capability passport domain integrity mismatch"
            if self.schema_version != "sergeant.capability-passport.v1" or self.lifecycle_state != CANDIDATE_STATE:
                return "capability passport lifecycle/schema integrity mismatch"
            body = _passport_body(
                capability_name=_string(self.capability_name, "capability_name"),
                domain=self.domain,
                artifact_generation=_string(self.artifact_generation, "artifact_generation"),
                parser_generation=_string(self.parser_generation, "parser_generation"),
                framework_generation=_string(self.framework_generation, "framework_generation"),
                qualification_protocol_generation=_string(
                    self.qualification_protocol_generation, "qualification_protocol_generation"
                ),
                proof_ceiling=_string(self.proof_ceiling, "proof_ceiling"),
                closure_ceiling=self.closure_ceiling,
                implementation_lineage_id=_sha(self.implementation_lineage_id, "implementation_lineage_id"),
                parser_lineage_id=_sha(self.parser_lineage_id, "parser_lineage_id"),
                framework_lineage_id=_sha(self.framework_lineage_id, "framework_lineage_id"),
                common_mode_lineage_id=_sha(self.common_mode_lineage_id, "common_mode_lineage_id"),
                control_lineage_id=_sha(self.control_lineage_id, "control_lineage_id"),
            )
            if sha256_id(body) != self.passport_id:
                return "capability passport content-addressed identity mismatch"
        except (CapabilityQualificationError, ReviewWorldError, ValueError, TypeError) as exc:
            return f"capability passport integrity failure: {exc}"
        return None


@dataclass(frozen=True)
class IndirectCallRelation:
    table: str
    key: str | None
    target: str | None
    line: int
    grade: ClosureGrade
    reason: str
    relation_id: str

    @classmethod
    def create(
        cls,
        *,
        table: str,
        key: str | None,
        target: str | None,
        line: int,
        grade: ClosureGrade,
        reason: str,
    ) -> "IndirectCallRelation":
        table = _string(table, "dispatch table")
        if key is not None:
            key = _string(key, "dispatch key")
        if target is not None:
            target = _string(target, "dispatch target")
        if not isinstance(line, int) or isinstance(line, bool) or line <= 0:
            raise CapabilityQualificationError("indirect call line must be positive integer")
        if not isinstance(grade, ClosureGrade):
            raise CapabilityQualificationError("indirect relation grade must be ClosureGrade")
        reason = _string(reason, "indirect relation reason")
        body = {
            "schema_version": "sergeant.indirect-call-relation.v1",
            "table": table,
            "key": key,
            "target": target,
            "line": line,
            "grade": grade.value,
            "reason": reason,
        }
        return cls(table, key, target, line, grade, reason, sha256_id(body))


@dataclass(frozen=True)
class SemanticCapabilityEvaluation:
    schema_version: str
    passport_id: str
    source_digest: str
    relations: tuple[IndirectCallRelation, ...]
    grade: ClosureGrade
    blockers: tuple[str, ...]
    resource_exhausted: bool
    operations: int
    evaluation_id: str


def _evaluation(
    *,
    passport: CapabilityPassport,
    source_digest: str,
    relations: Iterable[IndirectCallRelation] = (),
    grade: ClosureGrade,
    blockers: Iterable[str] = (),
    resource_exhausted: bool = False,
    operations: int = 0,
) -> SemanticCapabilityEvaluation:
    normalized_relations = tuple(relations)
    normalized_blockers = tuple(sorted({_string(value, "capability blocker") for value in blockers}))
    if not isinstance(operations, int) or isinstance(operations, bool) or operations < 0:
        raise CapabilityQualificationError("capability operation count must be non-negative integer")
    body = {
        "schema_version": "sergeant.semantic-capability-evaluation.v1",
        "passport_id": passport.passport_id,
        "source_digest": _sha(source_digest, "source_digest"),
        "relation_ids": [item.relation_id for item in normalized_relations],
        "grade": grade.value,
        "blockers": list(normalized_blockers),
        "resource_exhausted": resource_exhausted,
        "operations": operations,
    }
    return SemanticCapabilityEvaluation(
        body["schema_version"], passport.passport_id, source_digest, normalized_relations,
        grade, normalized_blockers, resource_exhausted, operations, sha256_id(body),
    )


def _function_locals(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names = {arg.arg for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
    if node.args.vararg:
        names.add(node.args.vararg.arg)
    if node.args.kwarg:
        names.add(node.args.kwarg.arg)

    class Locals(ast.NodeVisitor):
        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            if child is node:
                for statement in child.body:
                    self.visit(statement)
            else:
                names.add(child.name)

        def visit_AsyncFunctionDef(self, child: ast.AsyncFunctionDef) -> None:
            if child is node:
                for statement in child.body:
                    self.visit(statement)
            else:
                names.add(child.name)

        def visit_ClassDef(self, child: ast.ClassDef) -> None:
            names.add(child.name)

        def visit_Lambda(self, child: ast.Lambda) -> None:
            return

        def visit_Name(self, child: ast.Name) -> None:
            if isinstance(child.ctx, (ast.Store, ast.Del)):
                names.add(child.id)

        def visit_Import(self, child: ast.Import) -> None:
            names.update(alias.asname or alias.name.split(".")[0] for alias in child.names)

        def visit_ImportFrom(self, child: ast.ImportFrom) -> None:
            names.update(alias.asname or alias.name for alias in child.names if alias.name != "*")

    Locals().visit(node)
    return names


def _unknown(
    passport: CapabilityPassport,
    source_digest: str,
    blockers: Iterable[str],
    *,
    relations: Iterable[IndirectCallRelation] = (),
    operations: int = 0,
    resource_exhausted: bool = False,
) -> SemanticCapabilityEvaluation:
    return _evaluation(
        passport=passport,
        source_digest=source_digest,
        relations=relations,
        grade=ClosureGrade.UNKNOWN,
        blockers=blockers,
        resource_exhausted=resource_exhausted,
        operations=operations,
    )


def analyze_bounded_indirect_calls(source: str, *, passport: CapabilityPassport) -> SemanticCapabilityEvaluation:
    """Analyze the one SAE-60 candidate semantic family.

    Positive EXACT is limited to immutable module-level dicts of literal string
    keys to unique top-level functions, invoked by literal keys. Any observed
    uncertainty affecting that family makes the whole evaluation UNKNOWN.
    """
    if not isinstance(source, str):
        raise CapabilityQualificationError("semantic capability source must be text")
    if not isinstance(passport, CapabilityPassport):
        raise CapabilityQualificationError("semantic capability requires CapabilityPassport")
    digest = _source_digest(source)
    integrity = passport.integrity_error()
    if integrity:
        return _unknown(passport, digest, (integrity,))
    if passport.domain.domain_id != _SUPPORTED_DOMAIN:
        return _unknown(passport, digest, (f"unsupported capability domain {passport.domain.domain_id!r}",))
    if passport.parser_generation != _SUPPORTED_PARSER:
        return _unknown(passport, digest, (f"unsupported parser generation {passport.parser_generation!r}",))
    if passport.framework_generation != _SUPPORTED_FRAMEWORK:
        return _unknown(passport, digest, (f"unsupported framework generation {passport.framework_generation!r}",))
    if passport.proof_ceiling != "BOUNDED_EXHAUSTIVE_ORACLE" or passport.closure_ceiling is not ClosureGrade.EXACT:
        return _unknown(passport, digest, ("passport proof/closure ceiling is outside the implemented exact domain",))

    dimensions = dict(passport.domain.dimensions)
    source_bytes = len(source.encode("utf-8"))
    if source_bytes > dimensions["max_source_bytes"]:
        return _unknown(
            passport, digest,
            (f"resource ceiling exceeded: source bytes {source_bytes} > {dimensions['max_source_bytes']}",),
            operations=source_bytes, resource_exhausted=True,
        )
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return _unknown(passport, digest, (f"parse failure at line {exc.lineno or 0}: {exc.msg}",))

    nodes = tuple(ast.walk(tree))
    operations = len(nodes)
    if operations > dimensions["max_ast_nodes"]:
        return _unknown(
            passport, digest,
            (f"resource ceiling exceeded: AST nodes {operations} > {dimensions['max_ast_nodes']}",),
            operations=operations, resource_exhausted=True,
        )

    definitions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    duplicate_definitions: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in definitions:
                duplicate_definitions.add(node.name)
            definitions[node.name] = node

    module_assignments: dict[str, int] = {}
    table_nodes: dict[str, ast.Dict] = {}
    invalid_tables: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            for name in targets:
                module_assignments[name] = module_assignments.get(name, 0) + 1
                if isinstance(node.value, ast.Dict):
                    if name in table_nodes:
                        invalid_tables.add(name)
                    table_nodes[name] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            module_assignments[name] = module_assignments.get(name, 0) + 1
            if isinstance(node.value, ast.Dict):
                if name in table_nodes:
                    invalid_tables.add(name)
                table_nodes[name] = node.value

    if len(table_nodes) > dimensions["max_dispatch_tables"]:
        return _unknown(
            passport, digest,
            (f"resource ceiling exceeded: dispatch tables {len(table_nodes)} > {dimensions['max_dispatch_tables']}",),
            operations=operations, resource_exhausted=True,
        )

    tables: dict[str, dict[str, str]] = {}
    blockers: list[str] = []
    for name, node in sorted(table_nodes.items()):
        if module_assignments.get(name) != 1:
            invalid_tables.add(name)
        if len(node.keys) > dimensions["max_table_entries"]:
            invalid_tables.add(name)
            blockers.append(
                f"resource ceiling exceeded: table {name} entries {len(node.keys)} > {dimensions['max_table_entries']}"
            )
            continue
        mapping: dict[str, str] = {}
        for key, value in zip(node.keys, node.values):
            operations += 1
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str) or not key.value:
                invalid_tables.add(name)
                blockers.append(f"dispatch table {name} has non-literal or non-string key")
                continue
            if key.value in mapping:
                invalid_tables.add(name)
                blockers.append(f"dispatch table {name} has duplicate literal key {key.value!r}")
                continue
            if not isinstance(value, ast.Name) or value.id not in definitions or value.id in duplicate_definitions:
                invalid_tables.add(name)
                blockers.append(f"dispatch table {name} target for {key.value!r} is not one unique top-level function")
                continue
            mapping[key.value] = value.id
        if name not in invalid_tables:
            tables[name] = mapping

    all_table_names = set(table_nodes)
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets: list[ast.AST] = []
            if isinstance(node, ast.Assign):
                targets.extend(node.targets)
            else:
                targets.append(node.target)
            for target in targets:
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id in all_table_names:
                    invalid_tables.add(target.value.id)
                if isinstance(target, ast.Name) and target.id in all_table_names and node not in tree.body:
                    # Function/local rebinding is handled as shadowing at call sites.
                    continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            receiver = node.func.value
            if isinstance(receiver, ast.Name) and receiver.id in all_table_names and node.func.attr in _MUTATING_METHODS:
                invalid_tables.add(receiver.id)
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id in all_table_names:
            if not any(isinstance(target, ast.Name) and target.id == node.value.id for target in node.targets):
                invalid_tables.add(node.value.id)
        if isinstance(node, ast.Call):
            for argument in (*node.args, *(keyword.value for keyword in node.keywords)):
                if isinstance(argument, ast.Name) and argument.id in all_table_names:
                    invalid_tables.add(argument.id)

    if invalid_tables:
        blockers.extend(f"dispatch table {name} is mutated or escaped" for name in sorted(invalid_tables))

    function_locals = {
        id(node): _function_locals(node)
        for node in nodes
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    relations: list[IndirectCallRelation] = []

    class Calls(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope_stack: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.scope_stack.append(node)
            for statement in node.body:
                self.visit(statement)
            self.scope_stack.pop()

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.scope_stack.append(node)
            for statement in node.body:
                self.visit(statement)
            self.scope_stack.pop()

        def visit_Lambda(self, node: ast.Lambda) -> None:
            # Lambda-local semantics are outside the founding bounded slice.
            for child in ast.iter_child_nodes(node):
                self.visit(child)

        def visit_Call(self, node: ast.Call) -> None:
            nonlocal operations
            operations += 1
            func = node.func
            if isinstance(func, ast.Subscript) and isinstance(func.value, ast.Name) and func.value.id in all_table_names:
                table_name = func.value.id
                shadowed = any(table_name in function_locals.get(id(scope), set()) for scope in self.scope_stack)
                key_node = func.slice
                literal_key = key_node.value if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str) else None
                if shadowed:
                    blockers.append(f"dispatch table {table_name} is lexically shadowed at line {node.lineno}")
                    relations.append(IndirectCallRelation.create(
                        table=table_name, key=literal_key, target=None, line=node.lineno,
                        grade=ClosureGrade.UNKNOWN, reason="dispatch table identity is shadowed in lexical scope",
                    ))
                elif table_name in invalid_tables or table_name not in tables:
                    blockers.append(f"dispatch table {table_name} is mutated or escaped at line {node.lineno}")
                    relations.append(IndirectCallRelation.create(
                        table=table_name, key=literal_key, target=None, line=node.lineno,
                        grade=ClosureGrade.UNKNOWN, reason="dispatch table is not immutable and closed",
                    ))
                elif literal_key is None:
                    blockers.append(f"dynamic dispatch key for table {table_name} at line {node.lineno}")
                    relations.append(IndirectCallRelation.create(
                        table=table_name, key=None, target=None, line=node.lineno,
                        grade=ClosureGrade.UNKNOWN, reason="dynamic dispatch key is outside bounded literal-key domain",
                    ))
                elif literal_key not in tables[table_name]:
                    blockers.append(f"literal dispatch key {literal_key!r} absent from table {table_name} at line {node.lineno}")
                    relations.append(IndirectCallRelation.create(
                        table=table_name, key=literal_key, target=None, line=node.lineno,
                        grade=ClosureGrade.UNKNOWN, reason="literal key is not present in the closed dispatch table",
                    ))
                else:
                    relations.append(IndirectCallRelation.create(
                        table=table_name, key=literal_key, target=tables[table_name][literal_key], line=node.lineno,
                        grade=ClosureGrade.EXACT, reason="immutable module table + literal key + unique top-level callable",
                    ))
            self.generic_visit(node)

    Calls().visit(tree)
    relations.sort(key=lambda item: (item.line, item.table, item.key or "", item.target or ""))
    if blockers or any(relation.grade is not ClosureGrade.EXACT for relation in relations):
        return _unknown(passport, digest, blockers or ("semantic relation did not close exactly",), relations=relations, operations=operations)
    return _evaluation(
        passport=passport,
        source_digest=digest,
        relations=relations,
        grade=ClosureGrade.EXACT,
        blockers=(),
        resource_exhausted=False,
        operations=operations,
    )
