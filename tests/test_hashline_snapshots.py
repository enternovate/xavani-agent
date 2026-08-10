"""Tests for the hashline snapshot tag store (Task 12, omp port).

Covers tag determinism under the documented normalization (CRLF->LF, per-line
trailing whitespace stripped, final trailing newline stripped), the
SnapshotStore record/get/tag_of/verify API, content dedup, and the bounded
LRU (paths x versions) eviction behaviour.
"""

import re

import pytest

from tools.hashline.snapshots import SnapshotStore, compute_tag

TAG_RE = re.compile(r"^[0-9A-F]{4}$")


# ---------------------------------------------------------------------------
# compute_tag determinism
# ---------------------------------------------------------------------------


def test_tag_shape_and_determinism():
    t1 = compute_tag("def greet(name):\n    print('hi')\n")
    t2 = compute_tag("def greet(name):\n    print('hi')\n")
    assert t1 == t2
    assert TAG_RE.match(t1)


def test_crlf_equals_lf():
    assert compute_tag("a\r\nb\r\nc\r\n") == compute_tag("a\nb\nc\n")


def test_trailing_whitespace_ignored():
    assert compute_tag("a  \nb\t\nc   \n") == compute_tag("a\nb\nc\n")


def test_final_newline_ignored():
    assert compute_tag("a\nb\nc\n") == compute_tag("a\nb\nc")


def test_content_change_yields_different_tag():
    base = "def greet(name):\n    print('hi')\n"
    for variant in [
        "def greet2(name):\n    print('hi')\n",
        "def greet(name):\n    print('bye')\n",
        "def greet(name):\n    print('hi')\n\n",
        "def greet(name):\n     print('hi')\n",  # leading-space change
    ]:
        assert compute_tag(base) != compute_tag(variant), variant


# ---------------------------------------------------------------------------
# SnapshotStore API
# ---------------------------------------------------------------------------


def test_record_returns_tag_and_get_returns_entry():
    store = SnapshotStore()
    content = "line1\nline2\nline3\n"
    tag = store.record("app.py", content, ranges=[(1, 3)])
    assert TAG_RE.match(tag)
    entry = store.get("app.py")
    assert entry is not None
    assert entry.tag == tag
    assert entry.content == content.encode("utf-8")
    assert entry.visible_ranges == ((1, 3),)


def test_get_returns_none_for_unknown_path():
    assert SnapshotStore().get("nope.py") is None


def test_tag_of_computes_without_storing():
    store = SnapshotStore()
    tag = store.tag_of("app.py", "hello\n")
    assert tag == compute_tag("hello\n")
    assert store.get("app.py") is None  # nothing stored


def test_verify_current_tag_true():
    store = SnapshotStore()
    tag = store.record("app.py", "v1\n")
    assert store.verify("app.py", tag) is True


def test_verify_stale_or_unknown_tag_false():
    store = SnapshotStore()
    store.record("app.py", "v1\n")
    assert store.verify("app.py", "DEAD") is False
    assert store.verify("other.py", "DEAD") is False


def test_verify_fails_after_content_changes():
    store = SnapshotStore()
    old = store.record("app.py", "v1\n")
    store.record("app.py", "v2\n")
    assert store.verify("app.py", old) is False
    assert store.get("app.py").tag != old


def test_record_identical_content_reuses_version():
    store = SnapshotStore()
    t1 = store.record("app.py", "same\n", ranges=[(1, 1)])
    t2 = store.record("app.py", "same\n", ranges=[(2, 2)])
    assert t1 == t2
    entry = store.get("app.py")
    assert entry.visible_ranges == ((1, 1), (2, 2))  # ranges union


# ---------------------------------------------------------------------------
# Bounded LRU
# ---------------------------------------------------------------------------


def test_lru_evicts_least_recently_used_path():
    store = SnapshotStore(max_paths=2)
    store.record("a.py", "a\n")
    store.record("b.py", "b\n")
    assert store.get("a.py") is not None
    store.record("c.py", "c\n")  # evicts "b.py" (LRU), keeps "a.py"
    assert store.get("b.py") is None
    assert store.get("a.py") is not None


def test_lru_access_refreshes_recency():
    store = SnapshotStore(max_paths=2)
    store.record("a.py", "a\n")
    store.record("b.py", "b\n")
    store.get("a.py")  # touch a -> b becomes LRU
    store.record("c.py", "c\n")
    assert store.get("b.py") is None
    assert store.get("a.py") is not None


def test_version_history_bounded_per_path():
    store = SnapshotStore(max_versions=2)
    t1 = store.record("app.py", "v1\n")
    store.record("app.py", "v2\n")
    store.record("app.py", "v3\n")
    entry = store.get("app.py")
    assert entry.tag != t1  # oldest version evicted, head is v3
    assert store.verify("app.py", t1) is False
