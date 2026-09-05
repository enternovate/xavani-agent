import importlib


def test_dashboard_register_imports():
    mod = importlib.import_module("xavani_cli.dashboard_register")
    assert mod is not None


def test_dashboard_register_main_entry():
    mod = importlib.import_module("xavani_cli.dashboard_register")
    assert callable(mod.cmd_dashboard_register)
