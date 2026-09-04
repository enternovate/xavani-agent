import importlib


def test_session_filters_imports():
    mod = importlib.import_module("xavani_cli.session_filters")
    assert mod is not None


def test_parse_duration_seconds_static():
    mod = importlib.import_module("xavani_cli.session_filters")
    assert mod.parse_duration_seconds("5h") == 18000.0
    assert mod.parse_duration_seconds("90") == 90 * 86400
