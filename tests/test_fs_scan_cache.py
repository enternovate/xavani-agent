# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Tests for the pure-Python filesystem scan cache (tools/fs_scan_cache.py).

The cache memoizes directory-tree listings for the file tools behind a
short TTL, keyed by (canonical root, options), with write invalidation
and bounded LRU-style capacity. All tests run against tmp_path trees so
nothing outside the test sandbox is ever scanned.
"""

import time

import pytest

import tools.fs_scan_cache as fsc
from tools.fs_scan_cache import invalidate, walk


def test_cache_hit_within_ttl_and_invalidated_on_write(tmp_path):
    fsc.hits = 0
    a = walk(str(tmp_path))
    b = walk(str(tmp_path))
    assert a == b and fsc.hits == 1
    (tmp_path / "new.txt").write_text("x")
    invalidate(str(tmp_path))
    c = walk(str(tmp_path))
    assert any(e.endswith("new.txt") for e in c)


def test_ttl_expiry_forces_rescan(monkeypatch, tmp_path):
    fsc.hits = 0
    clock = {"now": 1000.0}
    monkeypatch.setattr(fsc.time, "monotonic", lambda: clock["now"])

    a = walk(str(tmp_path))
    walk(str(tmp_path))
    assert fsc.hits == 1  # second call served from cache

    clock["now"] += 2.0  # advance past the 1.0s default TTL
    (tmp_path / "late.txt").write_text("x")
    c = walk(str(tmp_path))
    assert any(e.endswith("late.txt") for e in c)
    assert fsc.hits == 1  # expired entry did NOT count as a hit


def test_ignore_rules(tmp_path):
    # Build the tree in a subdir: the autouse conftest fixture plants a
    # fake XAVANI_HOME at tmp_path/"xavani_test", which would pollute an
    # exact-set assertion over the whole tmp_path.
    tree = tmp_path / "tree"
    tree.mkdir()
    # Common junk dirs, a hidden dir, and a hidden file must all be skipped.
    for d in (".git", "node_modules", "__pycache__", ".venv", ".hidden_dir"):
        (tree / d).mkdir()
        (tree / d / "junk.bin").write_text("x")
    (tree / ".secret").write_text("x")
    (tree / "data.txt").write_text("x")
    (tree / "src").mkdir()
    (tree / "src" / "main.py").write_text("x")

    listing = set(walk(str(tree)))
    assert listing == {"data.txt", "src", "src/main.py"}
    assert not any(e.endswith("junk.bin") for e in listing)
    assert not any(e.endswith(".secret") for e in listing)


def test_lru_eviction_caps_cache_at_16_entries(tmp_path):
    fsc.hits = 0
    roots = []
    for i in range(17):
        d = tmp_path / f"d{i}"
        d.mkdir()
        (d / f"file{i}.txt").write_text("x")
        roots.append(str(d))

    for r in roots:
        walk(r)
    assert len(fsc._cache) <= 16

    # d0 was the first inserted, so LRU eviction must have dropped it:
    walk(roots[0])
    assert fsc.hits == 0  # miss -> rescanned, no cache credit
    walk(roots[16])
    assert fsc.hits == 1  # most recently used entry still cached
