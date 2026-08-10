"""Tests for tree-sitter block anchors for hashline block ops (Task 14).

Covers extension -> language mapping, Python block resolution (simple and
decorated functions, anchored at the first decorator per omp's rule),
single-line-statement rejection, the Markdown heading fallback (no
tree-sitter-markdown grammar needed), the graceful error when tree-sitter is
not installed, and an apply-engine integration for ``PUT N*:``.

The tree-sitter-dependent tests skip when the grammar wheels are not
installed — the graceful path and Markdown fallback must pass everywhere.
"""

import importlib
import sys

import pytest

from tools.hashline import parse
from tools.hashline.apply import ApplyError, apply_sections
from tools.hashline.blocks import (
    BlockResolutionError,
    language_for_path,
    resolve_block_range,
)
from tools.hashline.snapshots import SnapshotStore

DECORATED_FN = (
    '@app.route("/greet")\n'
    "def hello():\n"
    '    return "hi"\n'
)

SIMPLE_FN = "def foo():\n    pass\n"


def _ts_available() -> bool:
    try:
        import tree_sitter  # noqa: F401
        import tree_sitter_python  # noqa: F401

        return True
    except ImportError:
        return False


def _tsx_available() -> bool:
    try:
        import tree_sitter_typescript  # noqa: F401

        return True
    except ImportError:
        return False


TS = _ts_available()
TSX = _tsx_available()


# ---------------------------------------------------------------------------
# language detection
# ---------------------------------------------------------------------------


def test_language_for_path_extension_mapping():
    assert language_for_path("greet.py") == "python"
    assert language_for_path("a.ts") == "typescript"
    assert language_for_path("a.tsx") == "tsx"
    assert language_for_path("a.js") == "typescript"
    assert language_for_path("a.rs") == "rust"
    assert language_for_path("a.go") == "go"
    assert language_for_path("notes.md") == "markdown"


def test_unknown_extension_is_error():
    with pytest.raises(BlockResolutionError, match="line ranges|extension"):
        language_for_path("notes.txt")


# ---------------------------------------------------------------------------
# graceful degradation (never crash without tree-sitter)
# ---------------------------------------------------------------------------


def test_tree_sitter_missing_graceful_error(monkeypatch):
    # Simulate tree-sitter not being installed by poisoning the import.
    monkeypatch.setitem(sys.modules, "tree_sitter", None)
    with pytest.raises(BlockResolutionError, match="tree-sitter|line ranges|install"):
        resolve_block_range(SIMPLE_FN, 1, "python")


@pytest.mark.skipif(not TS, reason="tree-sitter not installed in this env")
def test_python_simple_function_block():
    assert resolve_block_range(SIMPLE_FN, 1, "python") == (1, 2)


@pytest.mark.skipif(not TS, reason="tree-sitter not installed in this env")
def test_python_decorated_function_block_anchors_at_first_decorator():
    # omp rule: anchor at the first decorator -> decorator + def + body.
    assert resolve_block_range(DECORATED_FN, 1, "python") == (1, 3)


@pytest.mark.skipif(not TS, reason="tree-sitter not installed in this env")
def test_python_single_line_statement_rejected():
    # A bare statement (here the body `pass`) is not a block opener.
    with pytest.raises(BlockResolutionError, match="single-line|opener"):
        resolve_block_range(SIMPLE_FN, 2, "python")


# ---------------------------------------------------------------------------
# .tsx / JSX: must use the TSX grammar (language_tsx), not plain TypeScript
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not TSX, reason="tree-sitter-typescript not installed")
def test_tsx_jsx_component_block_ends_at_component_not_eof():
    # JSX is not valid TypeScript grammar: the plain TS grammar turns the
    # JSX inside App() into a top-level ERROR node that swallows everything
    # to EOF (including the sibling Other() function).  The TSX grammar must
    # end the block at App()'s closing brace, not at the end of the file.
    src = (
        "function App() {\n"
        "  return (\n"
        "    <ul>\n"
        "      {items.map((i) => <li key={i}>{i}</li>)}\n"
        "    </ul>\n"
        "  );\n"
        "}\n"
        "\n"
        "function Other() {\n"
        "  return <p>World</p>;\n"
        "}\n"
    )
    assert resolve_block_range(src, 1, "tsx") == (1, 7)


@pytest.mark.skipif(not TS, reason="tree-sitter not installed in this env")
def test_tsx_loader_prefers_language_tsx(monkeypatch):
    # The tree-sitter-typescript wheel exposes BOTH language_typescript and
    # language_tsx; .tsx must pick language_tsx or JSX parses as ERROR nodes.
    # A stub module proves which accessor the loader calls — no real wheel
    # needed.  The stand-in grammar just needs to parse a two-line block.
    py_lang = importlib.import_module("tree_sitter_python").language()
    calls = []

    class _StubTypescript:
        @staticmethod
        def language():
            calls.append("language")
            raise AssertionError("plain TS grammar must never be used for .tsx")

        @staticmethod
        def language_tsx():
            calls.append("language_tsx")
            return py_lang

    monkeypatch.setitem(sys.modules, "tree_sitter_typescript", _StubTypescript())
    assert resolve_block_range("if True:\n    pass\n", 1, "tsx") == (1, 2)
    assert calls == ["language_tsx"]


def test_tsx_grammar_wheel_missing_graceful_error(monkeypatch):
    # Without the tree-sitter-typescript wheel, .tsx must degrade with the
    # install-guidance error (never silently fall back to the plain TS
    # grammar, which would mis-parse JSX).
    monkeypatch.setitem(sys.modules, "tree_sitter_typescript", None)
    with pytest.raises(BlockResolutionError, match="tree-sitter|line ranges|install"):
        resolve_block_range("function App() {}\n", 1, "tsx")


# ---------------------------------------------------------------------------
# markdown heading fallback (works without any grammar installed)
# ---------------------------------------------------------------------------


def test_markdown_heading_block_spans_to_next_same_or_higher_heading():
    src = (
        "# Title\n"
        "\n"
        "Intro paragraph.\n"
        "\n"
        "## Subsection\n"
        "\n"
        "Deeper content.\n"
        "# Next section\n"
    )
    assert resolve_block_range(src, 1, "markdown") == (1, 7)


def test_markdown_anchor_must_be_heading():
    src = "# Title\n\nbody text\n"
    with pytest.raises(BlockResolutionError, match="heading|opener"):
        resolve_block_range(src, 3, "markdown")


def test_markdown_heading_block_skips_heading_like_lines_inside_fence():
    # A line that looks like a heading INSIDE a fenced code block must not
    # truncate the block — the fence content is code, not a section boundary.
    src = (
        "# Title\n"
        "\n"
        "Some intro.\n"
        "\n"
        "```python\n"
        "# This looks like a heading but is inside a code fence\n"
        "def helper():\n"
        "    pass\n"
        "```\n"
        "\n"
        "# Real section\n"
    )
    assert resolve_block_range(src, 1, "markdown") == (1, 10)


def test_markdown_heading_block_skips_tilde_fence():
    src = (
        "# Title\n"
        "~~~\n"
        "# fake heading\n"
        "~~~\n"
        "# Real\n"
    )
    assert resolve_block_range(src, 1, "markdown") == (1, 4)


# ---------------------------------------------------------------------------
# apply-engine integration
# ---------------------------------------------------------------------------


def test_apply_put_block_integration():
    store = SnapshotStore()
    store.record("mod.py", SIMPLE_FN, ranges=[(1, 2)])
    tag = store.get("mod.py").tag
    patch = f"[mod.py#{tag}]\nPUT 1*:\n+def bar():\n+    pass\n"
    if not TS:
        # Graceful path: tree-sitter missing -> ApplyError with guidance.
        with pytest.raises(ApplyError, match="tree-sitter|line ranges"):
            apply_sections(parse(patch), store)
        return
    res = apply_sections(parse(patch), store)
    assert res.error is None
    (fr,) = res.results
    assert fr.preview == "def bar():\n    pass\n"
    assert store.get("mod.py").content == b"def bar():\n    pass\n"
