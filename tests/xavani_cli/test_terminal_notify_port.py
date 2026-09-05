import importlib


def test_terminal_notify_imports():
    mod = importlib.import_module("xavani_cli.terminal_notify")
    assert mod is not None


def test_osc9_static():
    mod = importlib.import_module("xavani_cli.terminal_notify")
    assert mod.osc9("hi") == "\x1b]9;hi\x07"
    assert "\x00" not in mod.osc9("a\x00b")
