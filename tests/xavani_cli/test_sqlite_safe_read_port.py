import importlib


def test_sqlite_safe_read_imports():
    mod = importlib.import_module("xavani_cli.sqlite_safe_read")
    assert mod is not None


def test_sqlite_safe_read_main_entry():
    mod = importlib.import_module("xavani_cli.sqlite_safe_read")
    assert callable(getattr(mod, "connect_tracked", None))
