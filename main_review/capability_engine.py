"""Tier 1 capability engine for Sergeant.

The capability engine is static by design. It does not execute repository code.
It builds lightweight indexes that let Sergeant reason about a change set as a
system instead of a list of unrelated files.
"""

from __future__ import annotations

import ast
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .scanner import scan_repository
from .static_invariant_review import run_static_invariant_review

CapabilitySeverity = Literal["blocker", "major", "minor", "note"]
CapabilityCategory = Literal[
    "cross_file",
    "architecture",
    "data_flow",
    "call_graph",
    "security_taint",
    "performance",
    "concurrency",
    "api_contract",
    "test_impact",
    "regression",
    "language",
]

IMPORT_RE = re.compile(r"^\s*(?:import\s+([\w./@-]+)|from\s+([\w.]+)\s+import\s+)")
JS_IMPORT_RE = re.compile(r"(?:import\s+.*?from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))")
PY_CALL_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
JS_EXPORT_RE = re.compile(r"\bexport\s+(?:async\s+)?(?:function|const|class)\s+([A-Za-z_$][\w$]*)")
JS_FUNCTION_RE = re.compile(r"\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
HTTP_ROUTE_RE = re.compile(r"\b(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]")
INPUT_RE = re.compile(
    r"(?:\breq\.(?:body|query|params)\b|\brequest\.(?:json|args|form|params)\b|"
    r"\binput\s*\(|\bprocess\.env\b|\b(?:r|request)\.URL\.Query\(\)\.Get\s*\(|"
    r"\b(?:r|request)\.FormValue\s*\(|\b(?:c|ctx|context)\.(?:Query|Param|FormValue)\s*\(|"
    r"@(?:RequestParam|PathVariable)\b|\b(?:request|req)\.getParameter\s*\(|"
    r"\bparams\s*\[|\brequested\s*:\s*&(?:'\w+\s+)?str\b)",
    re.I,
)
SINK_RE = re.compile(
    r"(?:\beval\s*\(|\bexec\s*\(|\bsubprocess\.|\bos\.system\s*\(|"
    r"\bchild_process\.exec\s*\(|\bcp\.exec\s*\(|\binnerHTML\b|"
    r"\bdangerouslySetInnerHTML\b|\braw\s*\(|"
    r"\b(?:db|database|conn|connection|tx|stmt)\.(?:query|queryContext|execute|execContext)\s*\(|"
    r"(?<![.\w])(?:query|queryContext|execute|execContext)\s*\(|"
    r"\bRuntime\.getRuntime\(\)\.exec\s*\(|\bProcessBuilder\s*\(|\bProcess\.Start\s*\()",
    re.I,
)
RUBY_EACH_DO_RE = re.compile(r"\.each\s+do\s+\|[^|]+\|", re.I)
RUBY_BLOCK_OPEN_RE = re.compile(
    r"^(?:class|module|def|if|unless|case|begin|while|until|for)\b|\bdo\s*(?:\|[^|]*\|)?\s*$",
    re.I,
)
RUBY_BLOCK_END_RE = re.compile(r"^end\b", re.I)
ASYNC_SHARED_RE = re.compile(
    r"(?:\bglobal\b|\bthreading\b|\basyncio\.create_task\b|\bPromise\.all\b|"
    r"\bsetTimeout\b|\bsetInterval\b|\basync\s+Task\b|\bTask\.(?:Run|Yield|WhenAll)\b|"
    r"\bgo\s+func\b|\btokio::spawn\b|\bThread\.new\b)",
    re.I,
)
SHARED_STATE_RE = re.compile(
    r"\b(?:global[A-Za-z0-9_]*|shared[A-Za-z0-9_]*|[A-Za-z0-9_]*(?:counter|cache|state))\b",
    re.I,
)
SHARED_MUTATION_RE = re.compile(
    r"\b(?:global[A-Za-z0-9_]*|shared[A-Za-z0-9_]*|[A-Za-z0-9_]*(?:counter|cache|state))"
    r"\s*(?:\+\+|--|[+\-*/]=)",
    re.I,
)
LOCK_BLOCK_RE = re.compile(r"\block\s*\([^)]*\)\s*$|\bsynchronized\b[^{}]*\)?\s*$", re.I)
CONTROL_BLOCK_RE = re.compile(r"^(?:if|for|foreach|while|switch|catch|using|lock|synchronized)\b", re.I)
LOCK_ACQUIRE_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\.(?:lock|wait|waitasync)\s*\(|"
    r"\bMonitor\.(?:Enter|TryEnter)\s*\(",
    re.I,
)
LOCK_RELEASE_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\.(?:unlock|release)\s*\(|"
    r"\bMonitor\.Exit\s*\(",
    re.I,
)
API_KEYWORD_RE = re.compile(r"\b(api|route|client|server|handler|schema|contract|types?)\b", re.I)
EVALUATION_PREFIXES = ("review-benchmarks/", "battle-tests/")


@dataclass(frozen=True)
class CapabilityFinding:
    capability: CapabilityCategory
    severity: CapabilitySeverity
    message: str
    path: str | None = None
    evidence: str = ""
    confidence: float = 0.5
    related_paths: list[str] = field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        if self.line_start is None:
            payload.pop("line_start")
            payload.pop("line_end")
        elif self.line_end is None:
            payload["line_end"] = self.line_start
        return payload


def _is_evaluation_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized.startswith(EVALUATION_PREFIXES)


def _safe_read(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _module_name(path: str) -> str:
    p = Path(path)
    if p.name == "__init__.py":
        return ".".join(part for part in p.parent.parts if part not in {"src", "lib", "app"})
    return ".".join(part for part in p.with_suffix("").parts if part not in {"src", "lib", "app"})


def _normalize_import(current: str, target: str) -> str:
    target = target.strip()
    if not target:
        return target
    if target.startswith("."):
        base = Path(current).parent.as_posix().replace("/", ".")
        return f"{base}.{target.lstrip('.')}",
    return target


def _resolve_import(import_name: str, module_index: dict[str, str]) -> str | None:
    candidates = [import_name, import_name.replace("/", ".")]
    for candidate in candidates:
        parts = candidate.split(".")
        while parts:
            key = ".".join(parts)
            if key in module_index:
                return module_index[key]
            parts.pop()
    return None


def _extract_python_symbols(text: str) -> tuple[set[str], set[str]]:
    exports: set[str] = set()
    calls: set[str] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return exports, calls
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.add(node.name)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                calls.add(func.attr)
    return exports, calls


def _extract_text_symbols(path: str, text: str) -> tuple[set[str], set[str]]:
    if path.endswith(".py"):
        return _extract_python_symbols(text)
    exports = set(JS_EXPORT_RE.findall(text)) | set(JS_FUNCTION_RE.findall(text))
    calls = set(PY_CALL_RE.findall(text))
    return exports, calls


def _build_indexes(root: Path) -> dict[str, Any]:
    insight = scan_repository(root)
    source_files = [
        file.path
        for file in insight.files
        if file.role in {"source", "ui", "database", "config", "infrastructure"}
        and not _is_evaluation_path(file.path)
    ]
    module_index = {_module_name(path): path for path in source_files}
    imports: dict[str, set[str]] = {path: set() for path in source_files}
    reverse_imports: dict[str, set[str]] = {path: set() for path in source_files}
    exports: dict[str, set[str]] = {}
    calls: dict[str, set[str]] = {}
    routes: dict[str, set[str]] = {}
    texts: dict[str, str] = {}

    for path in source_files:
        text = _safe_read(root, path)
        texts[path] = text
        file_exports, file_calls = _extract_text_symbols(path, text)
        exports[path] = file_exports
        calls[path] = file_calls
        routes[path] = {f"{method.upper()} {route}" for method, route in HTTP_ROUTE_RE.findall(text)}
        found_imports: set[str] = set()
        for line in text.splitlines():
            match = IMPORT_RE.match(line)
            if match:
                found_imports.add(str(match.group(1) or match.group(2) or ""))
            for js_match in JS_IMPORT_RE.findall(line):
                found_imports.add(str(js_match[0] or js_match[1] or ""))
        for import_name in found_imports:
            normalized = _normalize_import(path, import_name)
            if isinstance(normalized, tuple):
                normalized = normalized[0]
            resolved = _resolve_import(normalized, module_index)
            if resolved and resolved != path:
                imports[path].add(resolved)
                reverse_imports.setdefault(resolved, set()).add(path)

    return {
        "insight": insight,
        "source_files": source_files,
        "imports": imports,
        "reverse_imports": reverse_imports,
        "exports": exports,
        "calls": calls,
        "routes": routes,
        "texts": texts,
    }


def _changed_set(changed_files: list[str] | None) -> set[str]:
    return {path.strip() for path in changed_files or [] if path.strip()}


def _cross_file_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    reverse_imports: dict[str, set[str]] = indexes["reverse_imports"]
    for path in sorted(changed):
        dependents = sorted(reverse_imports.get(path, set()))
        if dependents:
            findings.append(CapabilityFinding("cross_file", "major" if len(dependents) >= 3 else "minor", "Changed file has dependent modules that may be affected.", path, f"{len(dependents)} dependent file(s) import this file.", 0.76, dependents[:10]))
    return findings


def _architecture_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    imports: dict[str, set[str]] = indexes["imports"]
    for path in sorted(changed):
        if "/ui/" in f"/{path}" or path.startswith(("frontend/", "web/")):
            backend_deps = [dep for dep in imports.get(path, set()) if dep.startswith(("server/", "backend/", "api/"))]
            if backend_deps:
                findings.append(CapabilityFinding("architecture", "major", "UI layer imports backend/server layer directly.", path, "Layer boundary appears crossed by imports.", 0.72, backend_deps))
        if path.startswith(("src/", "app/")) and "test" in path.lower():
            continue
        if path.startswith(("scripts/", ".github/", "deploy/")):
            findings.append(CapabilityFinding("architecture", "note", "Infrastructure or automation path changed; review deployment impact.", path, "Path is in scripts, CI, or deployment surface.", 0.7))
    return findings


def _data_flow_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    return [CapabilityFinding("data_flow", "major", "User-controlled input appears near a risky sink.", path, "Input and sink patterns were both detected in the changed file.", 0.68) for path in sorted(changed) if INPUT_RE.search(indexes["texts"].get(path, "")) and SINK_RE.search(indexes["texts"].get(path, ""))]


def _call_graph_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    exports: dict[str, set[str]] = indexes["exports"]
    calls: dict[str, set[str]] = indexes["calls"]
    for path in sorted(changed):
        symbols = exports.get(path, set())
        callers = [other for other, other_calls in calls.items() if other != path and symbols & other_calls]
        if symbols and callers:
            findings.append(CapabilityFinding("call_graph", "minor" if len(callers) < 5 else "major", "Changed exported symbols are called from other files.", path, f"Detected callers for exported symbols: {', '.join(sorted(symbols)[:5])}.", 0.66, sorted(callers)[:10]))
    return findings


def _security_taint_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    return [CapabilityFinding("security_taint", "major", "Potential tainted input path needs validation review.", path, "Input source and security-sensitive operation are both present.", 0.7) for path in sorted(changed) if INPUT_RE.search(indexes["texts"].get(path, "")) and (SINK_RE.search(indexes["texts"].get(path, "")) or re.search(r"\b(sql|query|exec|eval|shell|command)\b", indexes["texts"].get(path, ""), re.I))]


def _has_nested_ruby_each(text: str) -> bool:
    """Recognize lexical Ruby block nesting without crossing a matching ``end``."""

    blocks: list[bool] = []
    for row in text.splitlines():
        code = row.split("#", 1)[0].strip()
        if not code:
            continue
        if RUBY_BLOCK_END_RE.match(code):
            if blocks:
                blocks.pop()
            continue
        each_block = bool(RUBY_EACH_DO_RE.search(code))
        if each_block and any(blocks):
            # Only an existing ``each do`` block establishes nested iteration;
            # class, method and conditional scopes merely preserve its lifetime.
            return True
        if each_block or RUBY_BLOCK_OPEN_RE.search(code):
            blocks.append(each_block)
    return False


def _brace_scopes(text: str) -> list[tuple[int, int]]:
    stack: list[int] = []
    scopes: list[tuple[int, int]] = []
    for position, character in enumerate(text):
        if character == "{":
            stack.append(position)
        elif character == "}" and stack:
            scopes.append((stack.pop(), position))
    return scopes


def _brace_header(text: str, opening: int) -> str:
    boundary = max(
        text.rfind("\n", 0, opening),
        text.rfind(";", 0, opening),
        text.rfind("{", 0, opening),
        text.rfind("}", 0, opening),
    )
    return text[boundary + 1:opening].strip()


def _mutation_is_guarded(text: str, mutation: re.Match[str], scopes: list[tuple[int, int]]) -> bool:
    containing = sorted(
        (scope for scope in scopes if scope[0] < mutation.start() < scope[1]),
        key=lambda scope: scope[1] - scope[0],
    )
    if any(LOCK_BLOCK_RE.search(_brace_header(text, opening)) for opening, _ in containing):
        return True

    # Imperative mutex APIs guard only the region after the most recent acquire
    # in the same enclosing function/block. Atomic operations are deliberately
    # excluded: one Interlocked call cannot protect another ``counter++``.
    function_scope = next(
        (
            scope
            for scope in containing
            if ")" in _brace_header(text, scope[0])
            and not CONTROL_BLOCK_RE.match(_brace_header(text, scope[0]))
        ),
        containing[0] if containing else (0, len(text)),
    )
    opening, _ = function_scope
    before = text[opening:mutation.start()]
    acquire_positions = [match.start() for match in LOCK_ACQUIRE_RE.finditer(before)]
    release_positions = [match.start() for match in LOCK_RELEASE_RE.finditer(before)]
    if acquire_positions and max(acquire_positions) > max(release_positions, default=-1):
        return True

    # Cover indentation-scoped Python/Ruby-style ``with lock`` constructs.
    lines = text[:mutation.start()].splitlines()
    mutation_indent = len(lines[-1]) - len(lines[-1].lstrip()) if lines else 0
    for row in reversed(lines[:-1]):
        if not row.strip():
            continue
        indent = len(row) - len(row.lstrip())
        if indent >= mutation_indent:
            continue
        if re.search(r"\bwith\s+[^:]*\b(?:lock|mutex|semaphore)\b[^:]*:\s*$", row, re.I):
            return True
        if indent == 0 or re.search(r"\b(?:def|function|func|Task|void|int)\b", row):
            break
    return False


def _first_unguarded_shared_mutation(text: str) -> re.Match[str] | None:
    scopes = _brace_scopes(text)
    return next(
        (
            mutation
            for mutation in SHARED_MUTATION_RE.finditer(text)
            if not _mutation_is_guarded(text, mutation, scopes)
        ),
        None,
    )


_STRING_AND_COMMENT_RE = re.compile(
    r'"""[\s\S]*?"""'
    r"|'''[\s\S]*?'''"
    r'|"(?:\\.|[^"\\\n])*"'
    r"|'(?:\\.|[^'\\\n])*'"
    r"|//[^\n]*"
    r"|/\*[\s\S]*?\*/"
)
_HASH_COMMENT_RE = re.compile(r"#[^\n]*")
_BACKTICK_TEMPLATE_RE = re.compile(r"`(?:\\.|[^`\\])*`")
#: Languages where "#" genuinely introduces a full-line comment. Everywhere
#: else (JS/TS private fields, Rust attributes, C/C++ preprocessor
#: directives, and simply languages that don't use "#" at all) "#" must be
#: left alone -- an allowlist is safer here than trying to enumerate every
#: language that does NOT use "#" as a comment marker.
_HASH_IS_COMMENT_EXTENSIONS = (".py", ".pyw", ".rb", ".sh", ".bash", ".zsh", ".ps1", ".pl", ".r", ".yml", ".yaml")


def _blank_run(chunk: str) -> str:
    return "".join("\n" if character == "\n" else " " for character in chunk)


def _find_matching_close_brace(text: str, open_index: int) -> int:
    """``open_index`` must point at a '{'. Returns the index of its
    matching '}', or ``len(text)`` if unterminated."""

    depth = 0
    index = open_index
    length = len(text)
    while index < length:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return length


def _strip_template_literal(match: "re.Match[str]") -> str:
    """A backtick template literal's own text is a string, but a
    ``${...}`` interpolation inside it is executable code (e.g.
    ``xs.map(x => ys.map(y => y))``) and must be preserved, not blanked
    along with the surrounding literal text."""

    chunk = match.group(0)
    pieces: list[str] = []
    index = 0
    length = len(chunk)
    while index < length:
        interpolation = chunk.find("${", index)
        if interpolation == -1:
            pieces.append(_blank_run(chunk[index:]))
            break
        pieces.append(_blank_run(chunk[index:interpolation]))
        open_brace = interpolation + 1
        close_brace = _find_matching_close_brace(chunk, open_brace)
        pieces.append(chunk[interpolation:close_brace + 1])
        index = close_brace + 1
    return "".join(pieces)


def _strip_comments_and_strings(text: str, path: str = "") -> str:
    """Blank out comment and string-literal spans (keeping line breaks so
    downstream line-based logic still lines up) so structural checks never
    match prose in a docstring/comment or content inside a string literal.
    A backtick template literal's own ``${...}`` interpolations are kept
    verbatim (they are executable code, not string content). "#" is only
    treated as a comment marker for languages that actually use it that
    way -- everywhere else (JS/TS private fields, Rust attributes, C/C++
    preprocessor directives, ...) it is left alone. Extension matching is
    case-insensitive, matching this repository's own language registry."""

    def _blank(match: "re.Match[str]") -> str:
        return _blank_run(match.group(0))

    text = _BACKTICK_TEMPLATE_RE.sub(_strip_template_literal, text)
    text = _STRING_AND_COMMENT_RE.sub(_blank, text)
    if path.lower().endswith(_HASH_IS_COMMENT_EXTENSIONS):
        text = _HASH_COMMENT_RE.sub(_blank, text)
    return text


_LOOP_HEADER_RE = re.compile(
    r"^(?:'?[A-Za-z_]\w*\s*:\s*)?"  # optional loop label ('outer: / outer:)
    r"(?:#\s*define\s+[A-Za-z_]\w*(?:\([^)]*\))?\s+)?"  # optional C/C++ macro-definition prefix
    r"(?:for|while)\b"
)


def _is_loop_header(header: str) -> bool:
    """A genuine loop header starts with (an optional loop label, then)
    ``for``/``while`` -- not merely contains the keyword anywhere, which
    would also match e.g. Rust's ``impl Worker for Thing``."""

    return bool(_LOOP_HEADER_RE.match(header.strip()))


def _skip_whitespace(text: str, position: int) -> int:
    length = len(text)
    while position < length and text[position].isspace():
        position += 1
    return position


def _find_header_paren_end(text: str, keyword_end: int) -> int | None:
    """``keyword_end`` is the index right after a ``for``/``while``
    keyword. If a parenthesized condition/clause directly follows (only
    whitespace in between, as in C/C++/Java/C#/JS), return the index just
    past its matching ``)``. Returns None for a paren-less header (Rust/Go
    ``for x in xs {``/``for i := 0; ...; i++ {``), which the brace-scope
    path already covers, or for a non-loop use of the keyword (e.g. Rust's
    ``impl Worker for Thing``, where no ``(`` follows at all)."""

    index = _skip_whitespace(text, keyword_end)
    if index >= len(text) or text[index] != "(":
        return None
    depth = 0
    length = len(text)
    while index < length:
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def _loop_headers_with_body_spans(stripped_text: str) -> list[tuple[int, int, int]]:
    """Every genuine C-style ``for (...)``/``while (...)`` header found
    anywhere in the text, paired with the span of its own governed body:
    a matching ``{...}`` block if one follows, or -- for a brace-less
    single-statement body -- a zero-width span placed exactly where that
    statement begins. A header starting exactly there is a directly
    chained brace-less nested loop (``for (...) for (...) work();``); a
    brace-less body reached through an intervening non-loop statement or
    an ``if`` is a further, deeper case not attempted here."""

    spans = []
    for match in re.finditer(r"\b(?:for|while)\b", stripped_text):
        header_start = match.start()
        header_end = _find_header_paren_end(stripped_text, match.end())
        if header_end is None:
            continue
        body_start = _skip_whitespace(stripped_text, header_end)
        if stripped_text[body_start:body_start + 1] == "{":
            body_end = _find_matching_close_brace(stripped_text, body_start)
        else:
            body_end = body_start
        spans.append((header_start, body_start, body_end))
    return spans


def _has_c_style_nested_loop(stripped_text: str) -> bool:
    """Covers parenthesized C-style loop headers whose nesting the
    brace-scope path can miss entirely: a brace-less single-statement
    body has no ``{``/``}`` pair to define a scope in the first place."""

    headers = _loop_headers_with_body_spans(stripped_text)
    for index, (_outer_start, body_start, body_end) in enumerate(headers):
        for other_index, (inner_start, _inner_body_start, _inner_body_end) in enumerate(headers):
            if other_index != index and body_start <= inner_start <= body_end:
                return True
    return False


class _LoopBoundaryVisitor(ast.NodeVisitor):
    """Detects a for/while loop -- or a comprehension/generator expression,
    itself an implicit loop -- reachable from the visited statements
    without crossing into a separately-invoked function/lambda body (a
    class body, unlike a function body, executes immediately and so IS
    followed into). A function/lambda/class definition's decorators,
    base classes, and default-value/annotation expressions are evaluated
    eagerly, once per enclosing loop iteration, and are always visited."""

    def __init__(self, *, annotations_are_eager: bool = True) -> None:
        self.found = False
        self._annotations_are_eager = annotations_are_eager

    def visit_For(self, node: ast.AST) -> None:
        self.found = True

    visit_AsyncFor = visit_For
    visit_While = visit_For
    visit_ListComp = visit_For
    visit_SetComp = visit_For
    visit_DictComp = visit_For
    visit_GeneratorExp = visit_For

    def _visit_eager_def_time_expressions(self, node: "ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef") -> None:
        for decorator in getattr(node, "decorator_list", ()):
            self.visit(decorator)
            if self.found:
                return
        for base in getattr(node, "bases", ()):
            self.visit(base)
            if self.found:
                return
        for keyword in getattr(node, "keywords", ()):
            self.visit(keyword)
            if self.found:
                return
        args = getattr(node, "args", None)
        if args is not None:
            eager_defaults = list(args.defaults) + [default for default in args.kw_defaults if default is not None]
            for default in eager_defaults:
                self.visit(default)
                if self.found:
                    return
            if self._annotations_are_eager:
                annotated_args = list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)
                if args.vararg is not None:
                    annotated_args.append(args.vararg)
                if args.kwarg is not None:
                    annotated_args.append(args.kwarg)
                for arg in annotated_args:
                    if arg.annotation is not None:
                        self.visit(arg.annotation)
                        if self.found:
                            return
                returns = getattr(node, "returns", None)
                if returns is not None:
                    self.visit(returns)
                    if self.found:
                        return

    def visit_FunctionDef(self, node: ast.AST) -> None:
        self._visit_eager_def_time_expressions(node)
        # The function BODY is deliberately never visited here -- it only
        # executes when the function is called, not once per enclosing
        # loop iteration.

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_ClassDef(self, node: ast.AST) -> None:
        self._visit_eager_def_time_expressions(node)
        if self.found:
            return
        # Unlike a function body, a class BODY executes immediately when
        # the `class` statement itself runs -- once per enclosing loop
        # iteration -- so it genuinely must be visited.
        for statement in node.body:
            self.visit(statement)
            if self.found:
                return

    def generic_visit(self, node: ast.AST) -> None:
        if self.found:
            return
        super().generic_visit(node)


def _body_contains_loop(statements: list[ast.stmt], *, annotations_are_eager: bool = True) -> bool:
    visitor = _LoopBoundaryVisitor(annotations_are_eager=annotations_are_eager)
    for statement in statements:
        visitor.visit(statement)
        if visitor.found:
            return True
    return False


def _comprehension_element_expressions(node: "ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp") -> list[ast.AST]:
    expressions: list[ast.AST] = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
    for generator in node.generators:
        # A filter clause (`if any(y for y in ys)`) runs once per outer
        # item just as much as the element expression does.
        expressions.extend(generator.ifs)
    return expressions


def _annotations_are_eager(tree: ast.Module) -> bool:
    """Parameter/return annotations are evaluated once per def-statement
    execution UNLESS postponed evaluation is active (``from __future__
    import annotations``), in which case they are stored as strings and
    never evaluated as real expressions."""

    for node in tree.body:
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
        ):
            return False
    return True


def _python_has_nested_loop(text: str) -> bool | None:
    """Genuine structural check via a real parse: a for/while loop whose own
    body directly contains another for/while loop or comprehension; a
    comprehension with two or more ``for`` clauses (itself O(n*m)); a
    comprehension whose own element or filter expression contains another
    comprehension (``[[y for y in ys] for x in xs]``,
    ``[x for x in xs if any(y for y in ys)]``). Returns None on a syntax
    error so callers can fall back rather than silently treat it as False."""

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    annotations_are_eager = _annotations_are_eager(tree)
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            # `else` on a for/while runs once after normal loop completion,
            # not once per outer iteration -- only `body` is genuinely
            # repeated work.
            if _body_contains_loop(node.body, annotations_are_eager=annotations_are_eager):
                return True
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            if len(node.generators) >= 2:
                return True
            visitor = _LoopBoundaryVisitor(annotations_are_eager=annotations_are_eager)
            for element in _comprehension_element_expressions(node):
                visitor.visit(element)
            if visitor.found:
                return True
    return False


def _preceding_nonblank_line(text: str, position: int) -> str:
    """Walk backward from ``position`` past blank lines to the nearest
    non-empty line -- covers Allman-style braces (``for (...)\n{``), where
    the same-line header at the opening brace itself is empty."""

    line_start = text.rfind("\n", 0, position)
    while True:
        line = text[line_start + 1:position].strip()
        if line:
            return line
        if line_start <= 0:
            return ""
        position = line_start
        line_start = text.rfind("\n", 0, position)


def _effective_loop_header(text: str, opening: int) -> str:
    header = _brace_header(text, opening)
    if _is_loop_header(header):
        return header
    return _preceding_nonblank_line(text, opening)


def _generic_has_nested_loop(stripped_text: str) -> bool:
    """Brace-language fallback for non-Python source. Two complementary
    checks: (1) a for/while-headed brace scope (Rust/Go-style headers
    included) that itself contains ANOTHER genuinely for/while-headed
    brace scope, matched via ``_effective_loop_header`` so a brace on its
    own line (Allman style) still binds to its preceding header; and (2)
    ``_has_c_style_nested_loop`` for parenthesized C-style headers whose
    body has no brace scope at all to find (a brace-less single
    statement)."""

    scopes = _brace_scopes(stripped_text)
    loop_scope_spans = [
        (opening, closing)
        for opening, closing in scopes
        if _is_loop_header(_effective_loop_header(stripped_text, opening))
    ]
    for outer_opening, outer_closing in loop_scope_spans:
        for inner_opening, _inner_closing in loop_scope_spans:
            if inner_opening != outer_opening and outer_opening < inner_opening < outer_closing:
                return True
    return _has_c_style_nested_loop(stripped_text)


def _has_nested_loop_statement(path: str, text: str) -> bool:
    """Real nested-iteration check, replacing a former raw-text regex that
    matched any two occurrences of the word "for" within 160 characters --
    including inside comments, docstrings, and unrelated single-level
    comprehensions sitting near each other. Python files get a genuine AST
    check; other languages get a comment/string-stripped, brace-scope-aware
    check so a for/while must actually be lexically nested to count.
    Extension matching is case-insensitive."""

    if path.lower().endswith((".py", ".pyw")):
        result = _python_has_nested_loop(text)
        if result is not None:
            return result
    return _generic_has_nested_loop(_strip_comments_and_strings(text, path))


def _performance_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    for path in sorted(changed):
        text = indexes["texts"].get(path, "")
        stripped = _strip_comments_and_strings(text, path)
        if (
            _has_nested_loop_statement(path, text)
            or _has_nested_ruby_each(text)
            or re.search(r"\.map\([^\)]*=>[\s\S]{0,120}\.map\(", stripped)
        ):
            findings.append(CapabilityFinding("performance", "minor", "Nested iteration pattern may create scaling risk.", path, "Nested loop/map/each pattern detected in changed file.", 0.62))
    return findings


def _concurrency_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    for path in sorted(changed):
        text = indexes["texts"].get(path, "")
        mutation = _first_unguarded_shared_mutation(text)
        if (
            ASYNC_SHARED_RE.search(text)
            and SHARED_STATE_RE.search(text)
            and mutation is not None
        ):
            findings.append(CapabilityFinding(
                "concurrency",
                "minor",
                "Concurrent work mutates shared state without a visible synchronization guard.",
                path,
                "Concurrent execution, a shared-state mutation, and no atomic/lock guard were detected.",
                0.72,
                line_start=text[:mutation.start()].count("\n") + 1,
            ))
    return findings


def _api_contract_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    for path in sorted(changed):
        routes = indexes["routes"].get(path, set())
        if routes:
            findings.append(CapabilityFinding("api_contract", "major", "API route contract changed or requires compatibility review.", path, f"Detected routes: {', '.join(sorted(routes)[:5])}.", 0.74))
        elif API_KEYWORD_RE.search(path) and path.endswith((".ts", ".tsx", ".js", ".py", ".go", ".rs", ".java", ".cs")):
            findings.append(CapabilityFinding("api_contract", "minor", "API-adjacent file changed; check callers and contracts.", path, "Path name indicates API, route, client, schema, or contract surface.", 0.58))
    return findings


def _test_impact_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    insight = indexes["insight"]
    changed_non_tests = [path for path in changed if path not in insight.tests]
    changed_tests = [path for path in changed if path in insight.tests]
    if changed_non_tests and not changed_tests:
        return [CapabilityFinding("test_impact", "major", "Implementation changed without changed tests in the same PR.", evidence=f"Detected {len(changed_non_tests)} changed non-test file(s) and 0 changed test files.", confidence=0.78, related_paths=sorted(changed_non_tests)[:10])]
    return []


def _regression_findings(indexes: dict[str, Any], changed: set[str]) -> list[CapabilityFinding]:
    findings: list[CapabilityFinding] = []
    for path in sorted(changed):
        dependents = sorted(indexes["reverse_imports"].get(path, set()))
        if len(dependents) >= 5:
            findings.append(CapabilityFinding("regression", "major", "High blast-radius change may regress dependent behavior.", path, f"At least {len(dependents)} files depend on this file.", 0.72, dependents[:10]))
    return findings


def _finding_identity(finding: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(finding.get("root_cause") or finding.get("message") or "unknown"),
        str(finding.get("path") or ""),
        int(finding.get("line_start") or 0),
        str(finding.get("message") or ""),
    )


def run_capability_engine(root: str | Path = ".", changed_files: list[str] | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve()
    changed = _changed_set(changed_files)
    evaluation_files = sorted(path for path in changed if _is_evaluation_path(path))
    reviewable_changed = changed - set(evaluation_files)
    indexes = _build_indexes(root_path)
    base_findings: list[CapabilityFinding] = []
    for provider in (
        _cross_file_findings,
        _architecture_findings,
        _data_flow_findings,
        _call_graph_findings,
        _security_taint_findings,
        _performance_findings,
        _concurrency_findings,
        _api_contract_findings,
        _test_impact_findings,
        _regression_findings,
    ):
        base_findings.extend(provider(indexes, reviewable_changed))

    invariant_review = run_static_invariant_review(root_path, sorted(reviewable_changed))
    finding_rows: list[dict[str, Any]] = [finding.to_dict() for finding in base_findings]
    finding_rows.extend(
        dict(item)
        for item in invariant_review.get("findings", [])
        if isinstance(item, dict)
    )

    severity_rank = {"blocker": 4, "major": 3, "minor": 2, "note": 1, "advisory": 1}
    unique: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for finding in finding_rows:
        key = _finding_identity(finding)
        existing = unique.get(key)
        if existing is None:
            unique[key] = finding
            continue
        existing_score = (
            severity_rank.get(str(existing.get("severity") or "").lower(), 0),
            float(existing.get("confidence") or 0.0),
        )
        candidate_score = (
            severity_rank.get(str(finding.get("severity") or "").lower(), 0),
            float(finding.get("confidence") or 0.0),
        )
        if candidate_score > existing_score:
            unique[key] = finding

    findings = list(unique.values())
    covered = sorted(
        {
            str(finding.get("capability") or finding.get("category"))
            for finding in findings
            if str(finding.get("capability") or finding.get("category") or "")
        }
    )
    capability_status = {
        name: "active"
        for name in (
            "cross_file",
            "architecture",
            "data_flow",
            "call_graph",
            "security_taint",
            "performance",
            "concurrency",
            "api_contract",
            "test_impact",
            "regression",
        )
    }
    capability_status["language"] = "scanner-backed"
    for capability in covered:
        capability_status.setdefault(capability, "static-officer")

    strongest = max(
        (severity_rank.get(str(finding.get("severity") or "").lower(), 0) for finding in findings),
        default=0,
    )
    return {
        "verdict": "BLOCK" if strongest == 4 else "NEEDS WORK" if strongest >= 3 else "PASS",
        "changed_files": sorted(changed),
        "reviewable_changed_files": sorted(reviewable_changed),
        "evaluation_files_excluded": evaluation_files,
        "capability_status": capability_status,
        "covered_by_findings": covered,
        "finding_count": len(findings),
        "findings": findings,
        "static_invariant_review": invariant_review,
    }
