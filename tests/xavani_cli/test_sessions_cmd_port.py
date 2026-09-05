import importlib


def test_sessions_cmd_imports():
    mod = importlib.import_module("xavani_cli.sessions_cmd")
    assert mod is not None


def test_sessions_cmd_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.sessions_cmd")
    assert callable(getattr(mod, "cmd_sessions", None))
