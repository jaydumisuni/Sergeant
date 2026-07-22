"""Language-neutral semantic flow graph for static review.

The graph normalizes source syntax into engineering events: suspension points,
validity guards, publications, triggers, and resource mutations. Rules consume
these events instead of matching one repository's exact source shape.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

_SOURCE_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".dart", ".kt", ".java", ".swift"}
_BRACE_FUNCTION_PATTERNS = (
    re.compile(
        r"(?:async\s+function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)|"
        r"(?P<name_arrow>[A-Za-z_$][\w$]*)\s*=\s*async\s*\([^)]*\)\s*=>|"
        r"async\s+(?P<name_method>[A-Za-z_$][\w$]*)\s*\([^)]*\))\s*\{",
        re.M,
    ),
    re.compile(
        r"(?:Future[^\n{]*|suspend\s+fun\s+|func\s+)"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*(?:async\s*)?\{",
        re.M,
    ),
)
_USE_EFFECT_RE = re.compile(r"\buseEffect\s*\(\s*\(\s*\)\s*=>\s*\{", re.M)
_FETCH_RE = re.compile(
    r"\bfetch\s*\(\s*['\"](?P<url>[^'\"]+)['\"]\s*,?\s*(?P<options>\{[\s\S]{0,800}?\})?",
    re.M,
)
_EXPORTED_FUNCTION_RE = re.compile(
    r"export\s+(?:async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{",
    re.M,
)


@dataclass(frozen=True)
class FlowEvent:
    kind: str
    line: int
    symbol: str = ""
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FunctionFlow:
    path: str
    name: str
    language: str
    line_start: int
    line_end: int
    body: str
    body_offset: int
    lifecycle: str = "ordinary"
    trigger_count: int = 0
    dynamic_effect_trigger: bool = False
    events: list[FlowEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("body", None)
        payload.pop("body_offset", None)
        return payload


@dataclass(frozen=True)
class EndpointOperation:
    path: str
    function: str
    line: int
    method: str
    resource: str
    invalidates: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SemanticFlowGraph:
    functions: list[FunctionFlow] = field(default_factory=list)
    endpoints: list[EndpointOperation] = field(default_factory=list)
    mount_only_caches: list[dict[str, Any]] = field(default_factory=list)
    readable_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "sergeant.semantic-flow-graph.v1",
            "functions": [item.to_dict() for item in self.functions],
            "endpoints": [item.to_dict() for item in self.endpoints],
            "mount_only_caches": list(self.mount_only_caches),
            "readable_files": list(self.readable_files),
        }


def _safe_text(root: Path, relative: str) -> str:
    try:
        resolved_root = root.resolve()
        path = (resolved_root / relative).resolve()
        if not path.is_relative_to(resolved_root) or not path.is_file():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _line(text: str, offset: int) -> int:
    return text[: max(0, offset)].count("\n") + 1


def _language(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".html": "html-javascript",
        ".dart": "dart",
        ".kt": "kotlin",
        ".java": "java",
        ".swift": "swift",
    }.get(suffix, "unknown")


def _matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = opening
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
            index += 1
            continue
        if block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "/" and nxt == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and nxt == "*":
            block_comment = True
            index += 2
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def _surrounding_class_lifecycle(text: str, offset: int) -> str:
    prefix = text[:offset]
    class_match = None
    for match in re.finditer(
        r"(?:@Riverpod[^\n]*\n\s*)?class\s+[A-Za-z_][A-Za-z0-9_]*\s+extends\s+(?P<base>[^\s{]+)",
        prefix,
        re.I,
    ):
        class_match = match
    if class_match is not None:
        base = class_match.group("base").lower()
        window = prefix[max(0, class_match.start() - 120) : class_match.end()].lower()
        if "riverpod" in window or base.startswith("_$") or "notifier" in base:
            return "provider"
    return "ordinary"


def _events(body: str, full_text: str, body_offset: int) -> list[FlowEvent]:
    events: list[FlowEvent] = []
    for match in re.finditer(r"\bawait\b", body):
        events.append(FlowEvent("suspend", _line(full_text, body_offset + match.start()), detail="await"))
    for match in re.finditer(r"\.\s*(?:then|catch|finally)\s*\(", body):
        events.append(FlowEvent("suspend", _line(full_text, body_offset + match.start()), detail="promise-continuation"))

    guard_re = re.compile(
        r"if\s*\((?P<condition>[^)]*(?:mounted|active|current|request|generation|epoch|version|controller|signal|token|disposed|cancelled|canceled)[^)]*)\)\s*(?:\{\s*)?(?:return|continue|break)",
        re.I,
    )
    for match in guard_re.finditer(body):
        events.append(
            FlowEvent(
                "validity_guard",
                _line(full_text, body_offset + match.start()),
                detail=match.group("condition").strip(),
            )
        )

    publication_patterns = (
        ("provider_ref", re.compile(r"\bref\s*\.\s*(?:read|watch|invalidate|invalidateSelf|keepAlive)\s*\(")),
        ("provider_state", re.compile(r"(?<![.\w])state\s*=")),
        ("react_state", re.compile(r"\bset[A-Z][A-Za-z0-9_]*\s*\(")),
        ("dispatch", re.compile(r"\bdispatch\s*\(")),
        ("map_source", re.compile(r"\.\s*(?:setData|setPaintProperty|setLayoutProperty)\s*\(")),
        ("collection", re.compile(r"\b[A-Za-z_$][\w$]*\s*\.\s*(?:set|add|push)\s*\(")),
        ("value_write", re.compile(r"\b[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\.value\s*=")),
    )
    for symbol, pattern in publication_patterns:
        for match in pattern.finditer(body):
            events.append(FlowEvent("publication", _line(full_text, body_offset + match.start()), symbol=symbol, detail=match.group(0).strip()))

    for match in re.finditer(r"\b([A-Za-z_$][\w$]*)\s*=\s*new\s+AbortController\s*\(", body):
        events.append(FlowEvent("epoch_token", _line(full_text, body_offset + match.start()), symbol=match.group(1), detail="AbortController"))
    for match in re.finditer(r"\b([A-Za-z_$][\w$]*(?:Ref)?)\.current\s*=|\+\+\s*([A-Za-z_$][\w$]*Ref)\.current", body):
        symbol = match.group(1) or match.group(2) or "epoch"
        events.append(FlowEvent("epoch_advance", _line(full_text, body_offset + match.start()), symbol=symbol))
    return sorted(events, key=lambda item: (item.line, item.kind, item.symbol))


def _extract_functions(path: str, text: str) -> list[FunctionFlow]:
    language = _language(path)
    functions: list[FunctionFlow] = []
    seen: set[tuple[int, str]] = set()
    for pattern in _BRACE_FUNCTION_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groupdict()
            name = groups.get("name") or groups.get("name_arrow") or groups.get("name_method")
            if not name:
                continue
            opening = match.end() - 1
            if text[opening] != "{":
                continue
            closing = _matching_brace(text, opening)
            if closing is None or (opening, name) in seen:
                continue
            seen.add((opening, name))
            body_offset = opening + 1
            body = text[body_offset:closing]
            trigger_count = max(0, len(re.findall(rf"\b{re.escape(name)}\s*\(", text)) - 1)
            dynamic_effect_trigger = bool(
                re.search(
                    rf"useEffect\s*\([\s\S]{{0,1200}}\b{re.escape(name)}\s*\([\s\S]{{0,500}}\[[^\]]+\]",
                    text,
                )
            )
            functions.append(
                FunctionFlow(
                    path=path,
                    name=name,
                    language=language,
                    line_start=_line(text, match.start()),
                    line_end=_line(text, closing),
                    body=body,
                    body_offset=body_offset,
                    lifecycle=_surrounding_class_lifecycle(text, match.start()),
                    trigger_count=trigger_count,
                    dynamic_effect_trigger=dynamic_effect_trigger,
                    events=_events(body, text, body_offset),
                )
            )
    return functions


def _extract_mount_only_caches(path: str, text: str) -> list[dict[str, Any]]:
    caches: list[dict[str, Any]] = []
    for effect in _USE_EFFECT_RE.finditer(text):
        opening = effect.end() - 1
        closing = _matching_brace(text, opening)
        if closing is None:
            continue
        tail = text[closing + 1 : closing + 180]
        if re.search(r",\s*\[\s*\]\s*\)", tail) is None:
            continue
        body = text[opening + 1 : closing]
        call = re.search(r"\b(?P<fetch>[A-Za-z_$][\w$]*)\s*\(\s*\)\s*(?:\.|;)", body)
        setter = re.search(r"\b(?P<setter>set[A-Z][A-Za-z0-9_]*)\s*\(", body)
        if call is None or setter is None:
            continue
        listens = bool(re.search(r"addEventListener|subscribe|invalidate|queryClient", body))
        caches.append(
            {
                "path": path,
                "line": _line(text, effect.start()),
                "fetch_function": call.group("fetch"),
                "setter": setter.group("setter"),
                "listens_for_invalidation": listens,
            }
        )
    return caches


def _extract_endpoints(path: str, text: str) -> list[EndpointOperation]:
    operations: list[EndpointOperation] = []
    function_ranges: list[tuple[str, int, int, str]] = []
    for match in _EXPORTED_FUNCTION_RE.finditer(text):
        opening = match.end() - 1
        closing = _matching_brace(text, opening)
        if closing is not None:
            function_ranges.append((match.group("name"), opening + 1, closing, text[opening + 1 : closing]))
    for name, start, _, body in function_ranges:
        invalidates = bool(re.search(r"dispatchEvent|invalidate|queryClient|set[A-Z][A-Za-z0-9_]*\s*\(|store\.", body))
        for fetch in _FETCH_RE.finditer(body):
            options = fetch.group("options") or ""
            method_match = re.search(r"method\s*:\s*['\"](?P<method>[A-Z]+)['\"]", options, re.I)
            method = (method_match.group("method") if method_match else "GET").upper()
            operations.append(
                EndpointOperation(
                    path=path,
                    function=name,
                    line=_line(text, start + fetch.start()),
                    method=method,
                    resource=fetch.group("url"),
                    invalidates=invalidates,
                )
            )
    return operations


def build_semantic_flow_graph(
    root: str | Path,
    changed_files: Iterable[str],
) -> SemanticFlowGraph:
    root_path = Path(root).resolve()
    changed = sorted({str(item) for item in changed_files if str(item)})
    graph = SemanticFlowGraph()
    for path in changed:
        if Path(path).suffix.lower() not in _SOURCE_SUFFIXES:
            continue
        text = _safe_text(root_path, path)
        if not text:
            continue
        graph.readable_files.append(path)
        graph.functions.extend(_extract_functions(path, text))
        graph.mount_only_caches.extend(_extract_mount_only_caches(path, text))
        graph.endpoints.extend(_extract_endpoints(path, text))
    return graph
