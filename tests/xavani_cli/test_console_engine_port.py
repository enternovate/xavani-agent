import importlib


def test_console_engine_imports():
    mod = importlib.import_module("xavani_cli.console_engine")
    assert mod is not None


def test_console_engine_exposes_main_entry():
    mod = importlib.import_module("xavani_cli.console_engine")
    assert hasattr(mod, "XavaniConsoleEngine")


def test_split_command_line_splits_simple_command():
    from xavani_cli._subprocess_compat import split_command_line

    assert split_command_line("status --all") == ["status", "--all"]
