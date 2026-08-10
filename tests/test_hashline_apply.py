"""Tests for the hashline apply engine (Task 13).

Covers fail-fast validation (nothing written when any section is invalid),
in-memory renumbering against ORIGINAL snapshot line numbers, register
capture/paste (anonymous + named across sections), REM / MV, byte-identical
no-op rejection, seen-line enforcement via ``visible_ranges``, fresh tag
recording, and the tree-sitter block-op error.
"""

import re

import pytest

from tools.hashline import parse
from tools.hashline.apply import ApplyError, apply_sections
from tools.hashline.snapshots import SnapshotStore, compute_tag

TAG_RE = re.compile(r"^[0-9A-F]{4}$")


def make_store(path, content, ranges):
    store = SnapshotStore()
    store.record(path, content, ranges=ranges)
    return store


def apply_edit(store, path, hunks):
    """Build a one-section patch against the store's current tag and apply it."""
    tag = store.get(path).tag
    return apply_sections(parse(f"[{path}#{tag}]\n{hunks}\n"), store)


def content_of(store, path):
    return store.get(path).content.decode("utf-8")


# ---------------------------------------------------------------------------
# basic content ops against original line numbers
# ---------------------------------------------------------------------------


def test_replace_range():
    store = make_store("greet.py", "a\nb\nc\nd\n", [(1, 4)])
    old_tag = store.get("greet.py").tag
    res = apply_edit(store, "greet.py", "PUT 2.=3:\n+X\n+Y\n")
    assert res.error is None
    (fr,) = res.results
    assert fr.path == "greet.py"
    assert fr.preview == "a\nX\nY\nd\n"
    assert store.get("greet.py").content == b"a\nX\nY\nd\n"
    assert store.get("greet.py").tag == fr.tag
    assert fr.tag != old_tag
    assert TAG_RE.match(fr.tag)


def test_insert_before_and_after():
    store = make_store("f.py", "l1\nl2\nl3\n", [(1, 3)])
    res = apply_edit(store, "f.py", "PUT <2:\n+B0\nPUT >2:\n+A2\n")
    assert res.results[0].preview == "l1\nB0\nl2\nA2\nl3\n"


def test_append_tail():
    store = make_store("f.py", "a\nb\n", [(1, 2)])
    res = apply_edit(store, "f.py", "PUT >$:\n+c\n+d\n")
    assert res.results[0].preview == "a\nb\nc\nd\n"


def test_renumbering_between_ops():
    # Line numbers keep referring to the ORIGINAL snapshot; inserts shift
    # the working copy in memory (never re-read between ops).
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    res = apply_edit(store, "f.py", "PUT >1:\n+INS\nPUT 3.=3:\n+C2\n")
    assert res.results[0].preview == "a\nINS\nb\nC2\n"


# ---------------------------------------------------------------------------
# registers
# ---------------------------------------------------------------------------


def test_cut_then_paste_anonymous_moves_lines():
    store = make_store("f.py", "one\ntwo\nthree\nfour\n", [(1, 4)])
    res = apply_edit(store, "f.py", "CUT 2.=3\nPUT >4\n")
    assert res.results[0].preview == "one\nfour\ntwo\nthree\n"


def test_named_register_across_sections():
    store = SnapshotStore()
    store.record("a.py", "x\ny\nz\n", ranges=[(1, 3)])
    store.record("b.py", "p\nq\nr\n", ranges=[(1, 3)])
    tag_a = store.get("a.py").tag
    tag_b = store.get("b.py").tag
    res = apply_sections(
        parse(
            f"[a.py#{tag_a}]\nCUT 1.=1 @keep\n"
            f"[b.py#{tag_b}]\nPUT >3 @keep\n"
        ),
        store,
    )
    assert res.error is None
    a_res, b_res = res.results
    assert a_res.preview == "y\nz\n"
    assert b_res.preview == "p\nq\nr\nx\n"
    assert store.get("b.py").content == b"p\nq\nr\nx\n"


def test_paste_from_empty_register_is_rejected():
    store = make_store("f.py", "a\nb\n", [(1, 2)])
    with pytest.raises(ApplyError, match="empty|CUT"):
        apply_edit(store, "f.py", "PUT >2\n")


# ---------------------------------------------------------------------------
# REM / MV
# ---------------------------------------------------------------------------


def test_remove_file():
    store = make_store("gone.py", "a\nb\n", [(1, 2)])
    res = apply_edit(store, "gone.py", "REM\n")
    fr = res.results[0]
    assert fr.action == "remove"
    assert fr.preview == ""
    assert store.get("gone.py") is None


def test_move_after_edit():
    store = make_store("old.py", "a\nb\nc\n", [(1, 3)])
    res = apply_edit(store, "old.py", "PUT 1.=1:\n+A1\nMV new.py\n")
    fr = res.results[0]
    assert fr.action == "move"
    assert fr.path == "new.py"
    assert fr.preview == "A1\nb\nc\n"
    assert store.get("old.py") is None
    assert store.get("new.py").content == b"A1\nb\nc\n"


def test_move_onto_itself_is_rejected():
    store = make_store("f.py", "a\nb\n", [(1, 2)])
    with pytest.raises(ApplyError, match="itself|no-op"):
        apply_edit(store, "f.py", "MV f.py\n")


# ---------------------------------------------------------------------------
# fail-fast validation
# ---------------------------------------------------------------------------


def test_byte_identical_edit_is_error():
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    with pytest.raises(ApplyError, match="no-op"):
        apply_edit(store, "f.py", "PUT 1.=3:\n+a\n+b\n+c\n")
    assert store.get("f.py").content == b"a\nb\nc\n"  # untouched


def test_unseen_line_rejected():
    # Only lines 1..3 were visible; 4..5 were not shown to the model.
    store = make_store("f.py", "a\nb\nc\nd\ne\n", [(1, 3)])
    with pytest.raises(ApplyError, match="re-read"):
        apply_edit(store, "f.py", "PUT 4.=5:\n+X\n+Y\n")


def test_insert_anchor_outside_visible_range_rejected():
    store = make_store("f.py", "a\nb\nc\n", [(1, 2)])
    with pytest.raises(ApplyError, match="re-read"):
        apply_edit(store, "f.py", "PUT >3:\n+X\n")


def test_out_of_range_line_rejected():
    store = make_store("f.py", "a\nb\n", [(1, 2)])
    with pytest.raises(ApplyError, match="re-read|out of range"):
        apply_edit(store, "f.py", "PUT 5.=5:\n+X\n")


def test_fail_fast_second_section_invalid_leaves_first_untouched():
    store = SnapshotStore()
    store.record("one.py", "a\nb\n", ranges=[(1, 2)])
    store.record("two.py", "c\nd\n", ranges=[(1, 2)])
    tag1 = store.get("one.py").tag
    tag2 = store.get("two.py").tag
    with pytest.raises(ApplyError):
        apply_sections(
            parse(
                f"[one.py#{tag1}]\nPUT 1.=1:\n+A\n"
                f"[two.py#{tag2}]\nPUT 3.=4:\n+B\n"  # unseen + out of range
            ),
            store,
        )
    # First section's file must be byte-identical and still carry the old tag.
    assert store.get("one.py").content == b"a\nb\n"
    assert store.get("one.py").tag == tag1


def test_stale_tag_rejected():
    store = make_store("f.py", "a\nb\n", [(1, 2)])
    with pytest.raises(ApplyError, match="re-read"):
        apply_sections(parse("[f.py#FFFF]\nPUT 1.=1:\n+X\n"), store)


def test_block_op_error():
    store = make_store("f.py", "def f():\n    pass\n", [(1, 2)])
    with pytest.raises(ApplyError, match="line ranges|Task 14|tree-sitter"):
        apply_edit(store, "f.py", "PUT 1*:\n+def g():\n+    pass\n")


# ---------------------------------------------------------------------------
# result payload
# ---------------------------------------------------------------------------


def test_fresh_tag_returned_and_recorded():
    store = make_store("f.py", "hello\nworld\n", [(1, 2)])
    old = store.get("f.py").tag
    res = apply_edit(store, "f.py", "PUT 2.=2:\n+earth\n")
    fr = res.results[0]
    assert fr.tag != old
    assert fr.tag == store.get("f.py").tag
    assert fr.tag == compute_tag("hello\nearth\n")
    assert fr.action == "edit"
    assert content_of(store, "f.py") == "hello\nearth\n"
