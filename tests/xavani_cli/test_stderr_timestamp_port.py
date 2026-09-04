import importlib


def test_stderr_timestamp_imports():
    mod = importlib.import_module("xavani_cli.stderr_timestamp")
    assert mod is not None


def test_timestamp_returns_nonempty_string():
    mod = importlib.import_module("xavani_cli.stderr_timestamp")
    ts = mod._timestamp()
    assert isinstance(ts, str)
    assert ts != ""
