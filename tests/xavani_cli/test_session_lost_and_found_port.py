import importlib


def test_session_lost_and_found_imports():
    mod = importlib.import_module("xavani_cli.session_lost_and_found")
    assert mod is not None


def test_session_lost_and_found_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.session_lost_and_found")
    assert callable(getattr(mod, "run_cli_lost_and_found_recover", None))
