import importlib


def test_worktree_cmd_imports():
    mod = importlib.import_module("xavani_cli.worktree_cmd")
    assert mod is not None


def test_worktree_cmd_main_entry():
    mod = importlib.import_module("xavani_cli.worktree_cmd")
    assert callable(mod.cmd_worktree)
