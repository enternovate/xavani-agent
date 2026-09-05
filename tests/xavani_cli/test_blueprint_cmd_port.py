import importlib


def test_blueprint_cmd_imports():
    mod = importlib.import_module("xavani_cli.blueprint_cmd")
    assert mod is not None


def test_blueprint_cmd_main_entry():
    mod = importlib.import_module("xavani_cli.blueprint_cmd")
    assert callable(mod.handle_blueprint_command)
