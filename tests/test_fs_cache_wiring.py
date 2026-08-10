# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Tests wiring the FS scan cache (tools/fs_scan_cache.py) into the
file tools and the terminal disk-usage walk (backlog C64).

Verifies that (a) repeated directory enumeration within the TTL is
served from the cache, and (b) file writes through the write tool
invalidate the cache so the next scan sees fresh state.
"""

import json

import pytest

import tools.file_tools as ft
import tools.fs_scan_cache as fsc
import tools.terminal_tool as tt
from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations


def _real_ops(cwd):
    return ShellFileOperations(LocalEnvironment(cwd=str(cwd), timeout=60))


def test_terminal_disk_walk_hits_cache(monkeypatch, tmp_path):
    fsc.hits = 0
    scratch = tmp_path / "scratch"
    env_dir = scratch / "xavani-demo"
    (env_dir / "sub").mkdir(parents=True)
    (env_dir / "file.txt").write_text("x" * 100)
    monkeypatch.setattr(tt, "_get_scratch_dir", lambda: scratch)

    tt._check_disk_usage_warning()
    tt._check_disk_usage_warning()

    assert fsc.hits >= 1  # second walk within TTL served from cache


def test_write_file_tool_invalidates_cache(monkeypatch, tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    monkeypatch.setattr(ft, "_get_file_ops", lambda tid="default": _real_ops(tree))

    fsc.hits = 0
    assert fsc.walk(str(tree)) == []  # prime cache on the empty tree

    new_file = tree / "fresh.txt"
    result = json.loads(
        ft.write_file_tool(path=str(new_file), content="hello world\n", task_id="wiring")
    )
    assert not result.get("error")

    after = fsc.walk(str(tree))
    assert any(e.endswith("fresh.txt") for e in after)


def test_patch_tool_invalidates_cache(monkeypatch, tmp_path):
    tree = tmp_path / "tree"
    tree.mkdir()
    target = tree / "target.txt"
    target.write_text("before\n")
    monkeypatch.setattr(ft, "_get_file_ops", lambda tid="default": _real_ops(tree))

    fsc.hits = 0
    fsc.walk(str(tree))  # prime cache

    result = json.loads(
        ft.patch_tool(
            mode="replace", path=str(target),
            old_string="before", new_string="after", task_id="wiring-patch",
        )
    )
    assert not result.get("error")

    after = fsc.walk(str(tree))
    assert any(e.endswith("target.txt") for e in after)
