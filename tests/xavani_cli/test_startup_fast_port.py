import importlib


def test_startup_fast_imports():
    mod = importlib.import_module("xavani_cli._startup_fast")
    assert mod is not None


def test_project_root_str_nonempty():
    mod = importlib.import_module("xavani_cli._startup_fast")
    assert isinstance(mod.project_root_str(), str)
    assert mod.project_root_str() != ""


def test_is_termux_env_returns_bool():
    mod = importlib.import_module("xavani_cli._startup_fast")
    assert isinstance(mod.is_termux_env(), bool)
