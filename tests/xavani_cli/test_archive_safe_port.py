import importlib


def test_archive_safe_imports():
    mod = importlib.import_module("xavani_cli.archive_safe")
    assert mod is not None


def test_normalize_archive_parts_simple():
    mod = importlib.import_module("xavani_cli.archive_safe")
    assert mod.normalize_archive_parts("a/b") != []
