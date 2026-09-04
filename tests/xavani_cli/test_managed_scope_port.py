import importlib


def test_managed_scope_imports():
    mod = importlib.import_module("xavani_cli.managed_scope")
    assert mod is not None


def test_managed_scope_main_entry():
    mod = importlib.import_module("xavani_cli.managed_scope")
    assert callable(mod.get_managed_dir)
