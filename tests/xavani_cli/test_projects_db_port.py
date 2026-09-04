import importlib


def test_projects_db_imports():
    mod = importlib.import_module("xavani_cli.projects_db")
    assert mod is not None


def test_projects_db_exposes_db_path_helper():
    mod = importlib.import_module("xavani_cli.projects_db")
    assert callable(mod.projects_db_path)
