import importlib


def test_timefmt_imports():
    mod = importlib.import_module("xavani_cli.timefmt")
    assert mod is not None


def test_relative_time_static():
    mod = importlib.import_module("xavani_cli.timefmt")
    assert mod.relative_time(None) == "?"
    assert mod.relative_time(0) == "?"
