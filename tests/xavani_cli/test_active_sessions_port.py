import importlib


def test_active_sessions_imports():
    mod = importlib.import_module("xavani_cli.active_sessions")
    assert mod is not None


def test_format_age_nonempty_for_90_seconds():
    mod = importlib.import_module("xavani_cli.active_sessions")
    result = mod.format_age(90)
    assert isinstance(result, str)
    assert result != ""


def test_coerce_max_concurrent_sessions_none_returns_none():
    mod = importlib.import_module("xavani_cli.active_sessions")
    assert mod.coerce_max_concurrent_sessions(None) is None
