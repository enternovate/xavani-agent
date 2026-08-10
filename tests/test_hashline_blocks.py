"""Tests for tree-sitter block anchors for hashline block ops (Task 14).

Covers extension -> language mapping, Python block resolution (simple and
decorated functions, anchored at the first decorator per omp's rule),
single-line-statement rejection, the Markdown heading fallback (no
tree-sitter-markdown grammar needed), the graceful error when tree-sitter is
not installed, and an apply-engine integration for ``PUT N*:``.

The tree-sitter-dependent tests skip when the grammar wheels are not
installed — the graceful path and Markdown fallback must pass everywhere.
"""

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


TS = _ts_available()


# ---------------------------------------------------------------------------
# language detection
# ---------------------------------------------------------------------------


def test_language_for_path_extension_mapping():
    assert language_for_path("greet.py") == "python"
    assert language_for_path("a.ts") == "typescript"
    assert language_for_path("a.tsx") == "typescript"
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
