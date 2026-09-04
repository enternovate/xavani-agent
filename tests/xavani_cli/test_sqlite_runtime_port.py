import importlib


def test_sqlite_runtime_imports():
    mod = importlib.import_module("xavani_cli.sqlite_runtime")
    assert mod is not None


def test_version_tuple_returns_3_tuple():
    mod = importlib.import_module("xavani_cli.sqlite_runtime")
    assert mod._version_tuple(["3", "40", "1"]) == (3, 40, 1)
