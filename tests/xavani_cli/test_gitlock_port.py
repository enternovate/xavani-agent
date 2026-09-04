import importlib
from pathlib import Path


def test_gitlock_imports():
    mod = importlib.import_module("xavani_cli.gitlock")
    assert mod is not None


def test_clear_stale_git_locks_empty_dir(tmp_path: Path):
    mod = importlib.import_module("xavani_cli.gitlock")
    assert mod.clear_stale_git_locks(tmp_path) == []
