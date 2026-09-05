import importlib


def test_win_pty_bridge_imports():
    mod = importlib.import_module("xavani_cli.win_pty_bridge")
    assert mod is not None


def test_win_pty_bridge_exposes_bridge():
    mod = importlib.import_module("xavani_cli.win_pty_bridge")
    assert hasattr(mod, "WinPtyBridge")
