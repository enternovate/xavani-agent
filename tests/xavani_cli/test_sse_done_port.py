import importlib


def test_sse_done_imports():
    mod = importlib.import_module("xavani_cli.proxy.sse_done")
    assert mod is not None


def test_sse_done_exposes_tracker():
    mod = importlib.import_module("xavani_cli.proxy.sse_done")
    assert hasattr(mod, "SseDoneTracker")
