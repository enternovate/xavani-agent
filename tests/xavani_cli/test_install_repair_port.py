import importlib


def test_install_repair_imports():
    mod = importlib.import_module("xavani_cli._install_repair")
    assert mod is not None


def test_run_core_install_callable():
    mod = importlib.import_module("xavani_cli._install_repair")
    assert callable(mod.run_core_install)
