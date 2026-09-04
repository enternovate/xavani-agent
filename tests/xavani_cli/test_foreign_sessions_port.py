import importlib


def test_foreign_sessions_imports():
    m = importlib.import_module("xavani_cli.foreign_sessions")
    assert m is not None


def test_foreign_sessions_entry_callable():
    from xavani_cli import foreign_sessions as m

    assert callable(m.run_sessions_import)
