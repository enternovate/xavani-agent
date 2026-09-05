import importlib


def test_update_inventory_imports():
    mod = importlib.import_module("xavani_cli.update_inventory")
    assert mod is not None


def test_update_inventory_main_entry():
    mod = importlib.import_module("xavani_cli.update_inventory")
    assert callable(mod.collect_runtime_inventory)
