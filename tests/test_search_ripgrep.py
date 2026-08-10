# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Tests for the ripgrep fast path in search_files (backlog A19).

Pins the search output contract: the rg-backed content search and the
fallback path must return identical match lines on a deterministic
fixture tree.  Also covers rg-absent fallback, rg-path selection, and
the bad-path error contract.

The rg path is the default whenever the binary is on PATH
(``_has_command('rg')``); when absent or failing, search falls back to
the grep path, which parses match lines with the exact same format
(``path:line:content``).
"""

import json
import shutil

import pytest

import tools.file_tools as ft
from tools.environments.local import LocalEnvironment
from tools.file_operations import ShellFileOperations

RG_AVAILABLE = shutil.which("rg") is not None

requires_rg = pytest.mark.skipif(not RG_AVAILABLE, reason="ripgrep not installed")


def _build_fixture(tmp_path, with_hidden=False):
    tree = tmp_path / "tree"
    (tree / "sub").mkdir(parents=True)
    (tree / "a.txt").write_text("alpha beta\ngamma needle here\nplain\n")
    (tree / "sub" / "b.py").write_text("def f():\n    return 'needle'\n")
    (tree / "sub" / "c.md").write_text("no matches in this file\n")
    if with_hidden:
        (tree / ".hidden.txt").write_text("needle in hidden file\n")
    return tree


def _run_search(tree, monkeypatch, *, force_fallback=False, task_id="default"):
    env = LocalEnvironment(cwd=str(tree), timeout=60)
    ops = ShellFileOperations(env)
    if force_fallback:
        # Simulate rg being absent while grep (the actual fallback) stays
        # available — mirrors _search_content's rg -> grep -> error ladder.
        def _no_rg(cmd):
            return cmd != "rg"

        ops._has_command = _no_rg
    monkeypatch.setattr(ft, "_get_file_ops", lambda tid="default": ops)
    raw = ft.search_tool(
        pattern="needle", target="content", path=str(tree),
        limit=50, offset=0, output_mode="content", context=0,
        task_id=task_id,
    )
    return json.loads(raw)


def _match_lines(result_dict):
    return {
        (m["path"], m["line"], m["content"])
        for m in result_dict.get("matches", [])
    }


@requires_rg
def test_rg_and_fallback_return_identical_match_lines(tmp_path, monkeypatch):
    tree = _build_fixture(tmp_path)

    rg_result = _run_search(tree, monkeypatch, task_id="rg-eq")
    fallback_result = _run_search(tree, monkeypatch, force_fallback=True, task_id="fb-eq")

    assert rg_result.get("total_count", 0) > 0
    assert _match_lines(rg_result) == _match_lines(fallback_result)
    assert rg_result["total_count"] == fallback_result["total_count"]


@requires_rg
def test_rg_path_is_used_when_available(tmp_path, monkeypatch):
    tree = _build_fixture(tmp_path)
    env = LocalEnvironment(cwd=str(tree), timeout=60)
    ops = ShellFileOperations(env)

    def _explode(*args, **kwargs):
        raise AssertionError("grep fallback used despite rg being available")

    monkeypatch.setattr(ops, "_search_with_grep", _explode)
    monkeypatch.setattr(ft, "_get_file_ops", lambda tid="default": ops)
    raw = ft.search_tool(
        pattern="needle", target="content", path=str(tree), task_id="rg-use"
    )
    d = json.loads(raw)
    assert d.get("total_count", 0) > 0
    assert "error" not in d


@requires_rg
def test_hidden_files_excluded_by_rg_path(tmp_path, monkeypatch):
    tree = _build_fixture(tmp_path, with_hidden=True)
    rg_result = _run_search(tree, monkeypatch, task_id="rg-hid")
    assert _match_lines(rg_result)
    assert all(".hidden.txt" not in p for p, _, _ in _match_lines(rg_result))


def test_rg_absent_falls_back_to_fallback_path(tmp_path, monkeypatch):
    tree = _build_fixture(tmp_path)
    result = _run_search(tree, monkeypatch, force_fallback=True, task_id="fb-abs")
    assert result.get("total_count", 0) == 2
    assert not result.get("error")


def test_bad_path_returns_error_contract(tmp_path, monkeypatch):
    env = LocalEnvironment(cwd=str(tmp_path), timeout=60)
    ops = ShellFileOperations(env)
    monkeypatch.setattr(ft, "_get_file_ops", lambda tid="default": ops)
    raw = ft.search_tool(
        pattern="needle", target="content",
        path=str(tmp_path / "does_not_exist"), task_id="bad-path",
    )
    d = json.loads(raw)
    assert "error" in d
    assert "Path not found" in d["error"]
