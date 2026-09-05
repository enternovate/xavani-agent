import importlib


def test_agent_import_imports():
    mod = importlib.import_module("xavani_cli.agent_import")
    assert mod is not None


def test_agent_import_main_entry():
    mod = importlib.import_module("xavani_cli.agent_import")
    assert callable(mod.import_agent_command)
