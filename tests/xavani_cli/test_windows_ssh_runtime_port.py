import importlib


def test_windows_ssh_runtime_imports():
    mod = importlib.import_module("xavani_cli.windows_ssh_runtime")
    assert mod is not None


def test_windows_ssh_runtime_exposes_dispatch():
    mod = importlib.import_module("xavani_cli.windows_ssh_runtime")
    assert hasattr(mod, "dispatch")
