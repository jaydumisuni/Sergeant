"""Preserve executable Python text while masking non-runtime fixture payloads."""

from __future__ import annotations

import ast
import io
import re
import tokenize


def _line_start_offsets(text: str) -> list[int]:
    starts = [0]
    for match in re.finditer(r"\n", text):
        starts.append(match.end())
    return starts


def _mask_range(chars: list[str], start: int, end: int) -> None:
    for index in range(max(0, start), min(end, len(chars))):
        if chars[index] not in "\r\n":
            chars[index] = " "


def _mask_token_span(
    chars: list[str],
    starts: list[int],
    start: tuple[int, int],
    end: tuple[int, int],
) -> None:
    start_offset = starts[start[0] - 1] + start[1]
    end_offset = starts[end[0] - 1] + end[1]
    _mask_range(chars, start_offset, end_offset)


def _ast_offset(text: str, starts: list[int], line: int, byte_column: int) -> int:
    line_start = starts[line - 1]
    line_end = starts[line] if line < len(starts) else len(text)
    line_text = text[line_start:line_end]
    prefix = line_text.encode("utf-8")[:byte_column].decode("utf-8", errors="ignore")
    return line_start + len(prefix)


def _mask_ast_span(chars: list[str], text: str, starts: list[int], node: ast.AST) -> None:
    required = ("lineno", "col_offset", "end_lineno", "end_col_offset")
    if not all(hasattr(node, field) for field in required):
        return
    start = _ast_offset(text, starts, int(node.lineno), int(node.col_offset))
    end = _ast_offset(text, starts, int(node.end_lineno), int(node.end_col_offset))
    _mask_range(chars, start, end)


def python_runtime_scan_text(text: str) -> str:
    """Mask comments and constant file payloads without hiding executable expressions.

    A constant string passed to ``write_text``/``write_bytes`` is data being written
    into another file, not executable source in the current Python module. F-strings
    remain visible because their expressions execute in the current module.
    Character offsets and line breaks are preserved for evidence references.
    """

    chars = list(text)
    starts = _line_start_offsets(text)

    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                _mask_token_span(chars, starts, token.start, token.end)
    except (tokenize.TokenError, IndentationError):
        pass

    try:
        tree = ast.parse(text)
    except SyntaxError:
        return "".join(chars)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"write_text", "write_bytes"} or not node.args:
            continue
        payload = node.args[0]
        if isinstance(payload, ast.Constant) and isinstance(payload.value, (str, bytes)):
            _mask_ast_span(chars, text, starts, payload)

    return "".join(chars)
