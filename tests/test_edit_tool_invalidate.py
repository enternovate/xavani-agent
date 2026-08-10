"""Tests: edit tool (hashline/replace modes) invalidates the FS scan cache.

Backlog C64 completion — tools/edit_tool.py writes files directly via
open()/unlink() (hashline write/remove/move, replace rewrite) without
routing through file_ops, so those writes must invalidate the scan cache
themselves, mirroring write_file_tool/patch_tool in tools/file_tools.py.

Each test primes a cache entry with a miss (hits stays 0), performs the
edit, then asserts the next walk is ALSO a miss (hits still 0) — proving
the entry was invalidated — followed by a walk that is a hit (hits == 1),
proving the cache still works.
"""

import json

import tools.edit_tool as edit_tool
import tools.fs_scan_cache as fsc
from tools.edit_tool import _handle_edit
from tools.hashline.snapshots import default_store


def test_hashline_edit_invalidates_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    tree = tmp_path / "tree"
    tree.mkdir()
    f = tree / "greet.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    default_store.record(str(f), "a\nb\nc\n", ranges=((1, 3),))
    tag = default_store.get(str(f)).tag

    fsc.hits = 0
    fsc.walk(str(tree))  # prime the cache entry
    assert fsc.hits == 0

    payload = f"[{f}#{tag}]\nPUT 2.=3:\n+X\n+Y\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t-inv-edit")
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert f.read_text(encoding="utf-8") == "a\nX\nY\n"

    fsc.walk(str(tree))  # must be a miss: the edit invalidated the entry
    assert fsc.hits == 0
    fsc.walk(str(tree))  # now served from cache
    assert fsc.hits == 1


def test_replace_edit_invalidates_cache(tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    f = tree / "note.txt"
    f.write_text("hello world\n", encoding="utf-8")

    fsc.hits = 0
    fsc.walk(str(tree))  # prime the cache entry
    assert fsc.hits == 0

    result = _handle_edit(
        {"mode": "replace", "path": str(f), "old_string": "world", "new_string": "there"},
        task_id="t-inv-replace",
    )
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert f.read_text(encoding="utf-8") == "hello there\n"

    fsc.walk(str(tree))  # must be a miss: the rewrite invalidated the entry
    assert fsc.hits == 0
    fsc.walk(str(tree))  # now served from cache
    assert fsc.hits == 1


def test_hashline_move_invalidates_both_paths(monkeypatch, tmp_path):
    """A hashline MV must invalidate BOTH the source tree (unlink) and the
    destination tree (write) — each is cached under its own root."""
    monkeypatch.delenv("XAVANI_EDIT_MODE", raising=False)
    monkeypatch.setattr(edit_tool, "get_config_path", lambda: tmp_path / "no-such-config.yaml")

    src_tree = tmp_path / "src_tree"
    dst_tree = tmp_path / "dst_tree"
    src_tree.mkdir()
    dst_tree.mkdir()
    src = src_tree / "old.py"
    src.write_text("a\nb\nc\n", encoding="utf-8")
    default_store.record(str(src), "a\nb\nc\n", ranges=((1, 3),))
    tag = default_store.get(str(src)).tag
    dest = dst_tree / "new.py"

    fsc.hits = 0
    fsc.walk(str(src_tree))
    fsc.walk(str(dst_tree))
    assert fsc.hits == 0

    payload = f"[{src}#{tag}]\nPUT 1.=1:\n+A1\nMV {dest}\n"
    result = _handle_edit({"input": payload, "mode": "hashline"}, task_id="t-inv-mv")
    data = json.loads(result)
    assert data.get("ok") is True, data
    assert dest.read_text(encoding="utf-8") == "A1\nb\nc\n"
    assert not src.exists()

    after_src = fsc.walk(str(src_tree))
    after_dst = fsc.walk(str(dst_tree))
    assert not any(e.endswith("old.py") for e in after_src)
    assert any(e.endswith("new.py") for e in after_dst)
    # Both walks were misses: source and destination entries both dropped.
    assert fsc.hits == 0
