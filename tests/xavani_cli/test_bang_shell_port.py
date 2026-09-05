import importlib


def test_bang_shell_imports():
    mod = importlib.import_module("xavani_cli.bang_shell")
    assert mod is not None


def test_bang_shell_main_entry():
    mod = importlib.import_module("xavani_cli.bang_shell")
    assert callable(mod.run_bang_command)
