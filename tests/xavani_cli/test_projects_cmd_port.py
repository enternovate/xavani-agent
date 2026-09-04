import importlib


def test_projects_cmd_imports():
    mod = importlib.import_module("xavani_cli.projects_cmd")
    assert mod is not None


def test_projects_cmd_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.projects_cmd")
    assert callable(mod.projects_command)
