"""Tree-sitter block anchors for hashline block ops (Task 14).

Resolves the syntactic block beginning at an anchor line for ``PUT N*`` /
``CUT N*`` / ``PUT >N*`` (``block=True`` insertions and pastes) using
tree-sitter grammars, with graceful degradation:

* Language is detected from the section path extension (``.py`` -> python,
  ``.ts``/``.tsx``/``.js`` -> typescript, ``.rs`` -> rust, ``.go`` -> go,
  ``.md`` -> markdown).  Unknown extensions raise :class:`BlockResolutionError`
  with guidance to use explicit line ranges.
* Tree-sitter and the grammar wheels are OPTIONAL (the ``hashline`` extra);
  when they are not installed every resolution raises
  :class:`BlockResolutionError` with install guidance — the apply engine
  wraps that into :class:`~tools.hashline.apply.ApplyError`, so a missing
  grammar never crashes the engine.
* Markdown uses ``tree-sitter-markdown`` when available, otherwise a pure
  heading heuristic: a heading at line N opens a block that runs through
  deeper subsections to the next heading of equal or higher level.

Resolution semantics (omp rules): the block STARTS at the anchor line (the
anchor must be the *opener* — the first decorator, the ``def``/``class``/
heading line — never the closer or a blank line); the highest node in the
parse tree that starts exactly on the anchor row is the block.  A node that
spans a single line is rejected with guidance, because a single line is not
a block.
"""

from __future__ import annotations

import importlib
import os
import re
from typing import Optional, Tuple

__all__ = [
    "BlockResolutionError",
    "TreeSitterUnavailable",
    "language_for_path",
    "resolve_block_range",
]

#: Extension -> tree-sitter language name (lowercased extension).
_EXT_TO_LANG = {
    ".py": "python",
    ".pyw": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "typescript",
    ".mjs": "typescript",
    ".cjs": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".md": "markdown",
}

#: ATX heading opener: 1..6 '#' followed by whitespace or end of line.
_HEADING_RE = re.compile(r"^(#{1,6})(?:\s|$)")


class BlockResolutionError(Exception):
    """Raised when a block anchor cannot be resolved to a line range.

    Every message carries guidance (install the ``hashline`` extra or use
    explicit ``N.=M`` line ranges) so callers can surface actionable text.
    """


class TreeSitterUnavailable(BlockResolutionError):
    """Raised when tree-sitter (or a needed grammar wheel) is not installed.

    Distinct from a real resolution failure so the Markdown path can fall
    back to the heading heuristic when only the grammar is missing.
    """


def language_for_path(path: str) -> str:
    """Map ``path``'s extension to a tree-sitter language name.

    Raises :class:`BlockResolutionError` for unknown extensions so the apply
    engine can reject the section with guidance instead of guessing.
    """
    ext = os.path.splitext(path)[1].lower()
    language = _EXT_TO_LANG.get(ext)
    if language is None:
        raise BlockResolutionError(
            f"cannot resolve block anchors for {path!r}: no tree-sitter "
            f"grammar is mapped for extension {ext or '(none)'!r}; use "
            "explicit line ranges (PUT N.=M: / CUT N.=M) instead"
        )
    return language


def resolve_block_range(
    source: str, line: int, language: str
) -> Tuple[int, int]:
    """Resolve the block beginning at 1-indexed ``line`` to ``(start, end)``.

    ``start`` is always the anchor ``line``; ``end`` is the last line of the
    block (1-indexed, inclusive).  Raises :class:`BlockResolutionError` when
    tree-sitter or the grammar is missing, the line is out of range, the line
    does not start a block, or the node is single-line (a closer/blank line).
    """
    language = language.lower()
    if language == "markdown":
        try:
            return _resolve_with_tree_sitter(source, line, "markdown")
        except TreeSitterUnavailable:
            # No grammar installed (or tree-sitter core missing): the heading
            # heuristic needs no native code at all.
            return _resolve_markdown_heading(source, line)
    return _resolve_with_tree_sitter(source, line, language)


# -- tree-sitter resolution --------------------------------------------------


def _resolve_with_tree_sitter(
    source: str, line: int, language: str
) -> Tuple[int, int]:
    total = _line_count(source)
    if line < 1 or line > total:
        raise BlockResolutionError(
            f"line {line} is out of range — the file has {total} line(s)"
        )
    parser = _load_parser(language)
    tree = parser.parse(source.encode("utf-8"))
    node = _highest_starting_at(tree.root_node, line - 1)
    if node is None:
        raise BlockResolutionError(
            f"line {line} is not the start of any syntactic block in this "
            f"{language} file — anchor the block opener (def/class/heading, "
            "etc.), not a line inside it or a closer/blank line; or use "
            "explicit line ranges (PUT N.=M: / CUT N.=M)"
        )
    end = node.end_point.row + 1
    if end <= line:
        raise BlockResolutionError(
            f"line {line} starts only a single-line node ({node.type!r}) — "
            "that is the closer or a bare statement, not a block opener; "
            "anchor the opener (e.g. the def/class/heading line) or use "
            "explicit line ranges (PUT N.=M: / CUT N.=M)"
        )
    return (line, end)


def _highest_starting_at(root, row: int) -> Optional[object]:
    """Deepest-first search for the highest (outermost) node starting at ``row``.

    The root node is never returned (a whole-file match would swallow content
    the author never anchored).  Decorated definitions naturally match at the
    first decorator line because the ``decorated_definition`` node starts
    there — that is omp's "anchor at the first decorator" rule.
    """
    for child in root.children:
        if not child.is_named:
            continue
        if child.start_point.row == row:
            return child
    for child in root.children:
        if not child.is_named:
            continue
        if child.start_point.row < row <= child.end_point.row:
            found = _highest_starting_at(child, row)
            if found is not None:
                return found
    return None


def _load_parser(language: str):
    """Build a tree-sitter Parser for ``language`` or raise TreeSitterUnavailable.

    Handles both the old capsule API (``Language(capsule)`` /
    ``parser.set_language``) and the modern grammar wheels (``language()``
    returning a ``Language``, ``parser.language = ...``).
    """
    try:
        import tree_sitter
    except ImportError:
        raise TreeSitterUnavailable(
            "tree-sitter is not installed — block anchors need the optional "
            "'hashline' extra (install with `pip install "
            "'xavani-agent[hashline]'`); use explicit line ranges "
            "(PUT N.=M: / CUT N.=M) for now"
        )
    try:
        from tree_sitter import Language, Parser
    except ImportError:  # pragma: no cover - very old tree-sitter
        Language = tree_sitter.Language  # type: ignore[attr-defined]
        Parser = tree_sitter.Parser  # type: ignore[attr-defined]

    try:
        module = importlib.import_module(f"tree_sitter_{language}")
    except ImportError:
        raise TreeSitterUnavailable(
            f"the tree-sitter grammar wheel for {language!r} is not installed "
            f"— block anchors need the optional 'hashline' extra "
            f"(tree-sitter-{language}); use explicit line ranges "
            "(PUT N.=M: / CUT N.=M) for now"
        )

    lang = None
    for name in ("language", f"language_{language}", "LANGUAGE"):
        fn = getattr(module, name, None)
        if fn is None:
            continue
        try:
            raw = fn() if callable(fn) else fn
        except TypeError:
            continue
        if isinstance(raw, Language):
            lang = raw
            break
        try:
            lang = Language(raw)
            break
        except Exception:  # pragma: no cover - ABI mismatch
            continue
    if lang is None:  # pragma: no cover - unknown grammar wheel shape
        raise TreeSitterUnavailable(
            f"could not load a Language from tree_sitter_{language!r}"
        )

    parser = Parser()
    if hasattr(parser, "set_language"):  # tree-sitter < 0.22
        parser.set_language(lang)
    else:  # pragma: no cover - modern API
        parser.language = lang
    return parser


# -- markdown heading fallback -----------------------------------------------


def _resolve_markdown_heading(source: str, line: int) -> Tuple[int, int]:
    lines = _split_lines(source)
    total = len(lines)
    if line < 1 or line > total:
        raise BlockResolutionError(
            f"line {line} is out of range — the file has {total} line(s)"
        )
    match = _HEADING_RE.match(lines[line - 1])
    if match is None:
        raise BlockResolutionError(
            f"line {line} is not a Markdown heading — block anchors in .md "
            "files must point at a '#...' heading (the block opener); use "
            "explicit line ranges (PUT N.=M: / CUT N.=M) instead"
        )
    level = len(match.group(1))
    end = line
    for idx in range(line, total):  # 0-indexed scan, exclusive of the anchor
        nxt = _HEADING_RE.match(lines[idx])
        if nxt is not None and len(nxt.group(1)) <= level:
            break  # next heading of equal or higher level ends the block
        end = idx + 1
    return (line, end)


# -- helpers -----------------------------------------------------------------


def _split_lines(source: str) -> list[str]:
    """Split into lines, dropping the single trailing newline (like apply.py)."""
    lines = source.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


def _line_count(source: str) -> int:
    return len(_split_lines(source))
