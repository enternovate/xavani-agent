import importlib


def test_worktree_gc_imports():
    mod = importlib.import_module("xavani_cli.worktree_gc")
    assert mod is not None


def test_worktree_gc_main_entry():
    mod = importlib.import_module("xavani_cli.worktree_gc")
    assert callable(mod.audit_worktrees)
