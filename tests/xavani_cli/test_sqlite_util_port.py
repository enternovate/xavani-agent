import importlib


def test_sqlite_util_imports():
    mod = importlib.import_module("xavani_cli.sqlite_util")
    assert mod is not None


def test_sqlite_util_write_txn_callable():
    mod = importlib.import_module("xavani_cli.sqlite_util")
    assert callable(mod.write_txn)
