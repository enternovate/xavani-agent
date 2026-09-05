import importlib


def test_session_recovery_imports():
    mod = importlib.import_module("xavani_cli.session_recovery")
    assert mod is not None


def test_session_recovery_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.session_recovery")
    assert callable(getattr(mod, "recover_session_database", None))
